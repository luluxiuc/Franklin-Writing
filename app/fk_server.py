#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk_server — 本地网页服务。书架、原文、练习、记录。

硬性约束：
  S1  只监听 127.0.0.1。不对外开。
  S2  **读完原文进入练习之后，服务端不再返回这一段原文**，
      直到你提交了稿子。写的时候页面上只有提示卡，没有原文。
  S3  概括提示只用模型做一件事：把内容说清楚。不评价、不建议、不模仿原文措辞。
  S4  所有数据只落本地 app/data 目录，不出这台机器。
  S5  除了"生成提示"这一个动作，不会调用模型。

用法：
  python app/fk_server.py                 # 127.0.0.1:8137，端口被占会自动往后找
  python app/fk_server.py --port 9000
  python app/fk_server.py --data D:\\写作存档
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import fk_llm as LLM
import fk_store as S
import fk_summary as SUM

WEB_DIR = os.path.join(HERE, 'web')
DATA_DIR = os.path.join(HERE, 'data')
DEFAULT_PORT = 8137

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.ico': 'image/x-icon',
    '.woff2': 'font/woff2',
}

_lock = threading.Lock()


class Api:
    """HTTP 语义之外的全部动作。单独可测。"""

    def __init__(self, data_dir: str, concurrency: int | None = None):
        self.store = S.Store(data_dir)
        self.warmer = SUM.Warmer(data_dir, lambda: S.Store(data_dir))
        if concurrency:
            self.warmer.concurrency = max(1, int(concurrency))

    # ─────────────────────── 设置

    def settings(self, reveal=False) -> dict:
        d = self.store.read()['settings']
        pc = self.warmer.cache.stats()
        return {
            'provider': d.get('provider', 'custom'),
            'base_url': d.get('base_url', ''),
            'model': d.get('model', ''),
            'has_key': bool((d.get('api_key') or '').strip()),
            'key_hint': LLM.key_hint(d.get('api_key', '')),
            'api_key': (d.get('api_key') or '') if reveal else '',
            'delay_min': d.get('delay_min', S.DEFAULT_DELAY_MIN),
            'passage_chars': d.get('passage_chars', S.DEFAULT_PASSAGE_CHARS),
            'presets': LLM.PRESETS,
            'data_dir': self.store.root,
            'concurrency': self.warmer.concurrency,
            'cache': {
                'cached': pc.get('cached', 0),
                'calls': pc.get('calls', 0),
                'hits': pc.get('hits', 0),
                'tokens_in': pc.get('tokens_in', 0),
                'tokens_out': pc.get('tokens_out', 0),
                'seconds': pc.get('seconds', 0),
                'without_usage': pc.get('calls_without_usage', 0),
                'file': pc.get('file', ''),
            },
        }

    def save_settings(self, b: dict) -> dict:
        data = self.store.read()
        st = data['settings']
        if 'provider' in b:
            st['provider'] = str(b['provider'])[:40]
        if 'base_url' in b and b['base_url'] is not None:
            st['base_url'] = str(b['base_url']).strip()[:300]
        if 'model' in b and b['model'] is not None:
            st['model'] = str(b['model']).strip()[:120]
        # 只有显式传了新 Key 才覆盖；空字符串 = 清空；不传 = 保持
        if b.get('api_key'):
            st['api_key'] = str(b['api_key']).strip()[:400]
        elif b.get('clear_key'):
            st['api_key'] = ''
        if b.get('delay_min') is not None and b['delay_min'] != '':
            v = float(b['delay_min'])
            if not (0 <= v <= 240):
                raise S.StoreError('延迟要在 0 到 240 分钟之间。')
            st['delay_min'] = v
        if b.get('passage_chars') is not None and b['passage_chars'] != '':
            v = int(b['passage_chars'])
            if not (80 <= v <= 2000):
                raise S.StoreError('每段字数要在 80 到 2000 之间。')
            st['passage_chars'] = v
        self.store.write(data)
        return {'ok': True, 'settings': self.settings()}

    def test_llm(self) -> dict:
        st = self.store.read()['settings']
        return LLM.test_connection(st)

    # ─────────────────────── 书架

    def shelf(self) -> dict:
        data = self.store.read()
        books = self.store.shelf(data)
        acts = data['attempts']
        return {
            'books': books,
            'counts': {
                'books': len(books),
                'passages': sum(b['counts']['total'] for b in books),
                'done': sum(b['counts']['done'] for b in books),
                'written': len([a for a in acts if a.get('draft')]),
            },
            'settings': {'delay_min': data['settings'].get('delay_min'),
                         'model': data['settings'].get('model', ''),
                         'has_key': bool((data['settings'].get('api_key') or '').strip())},
        }

    def add_book(self, b: dict) -> dict:
        text = b.get('text') or ''
        file_path = (b.get('file') or '').strip()
        if not text.strip() and file_path:
            text = _read_text_file(file_path) or ''
        text = S.tidy_whitespace(text)
        if not text:
            raise S.StoreError('没有原文。粘一段进来，或者填一个文本文件的路径。')

        title = (b.get('title') or '').strip() or _guess_title(text, file_path)
        author = (b.get('author') or '').strip()
        size = int(b.get('passage_chars') or self.store.read()['settings'].get(
            'passage_chars') or S.DEFAULT_PASSAGE_CHARS)

        chapters = S.split_chapters(text, target=max(600, size * 3), merge_small=True)
        if not chapters:
            raise S.StoreError('这段文本切不出章节。')
        for c in chapters:
            base = c.pop('_start', 0)
            c['passages'] = S.split_passages(c.pop('body'),
                                             target=size, base=base)

        data = self.store.read()
        bid = S.new_id('bk')
        book = {
            'id': bid, 'title': title[:120], 'author': author[:80],
            'added': S.now(), 'chars': S.plain_len(text),
            'note': (b.get('note') or '')[:400],
            'fingerprint': S.text_fingerprint(text),
            'chapters': chapters,
        }
        data['books'].append(book)
        self.store.save_text(bid, text)
        self.store.write(data)
        return {'book': self.store.book_view(data, bid)}

    def delete_book(self, book_id: str, confirm: str) -> dict:
        data = self.store.read()
        b = self.store.book(data, book_id)
        if confirm not in (book_id, b['title']):
            raise S.StoreError('删除要确认。带上 confirm=<书 id 或书名>。')
        data['books'] = [x for x in data['books'] if x['id'] != book_id]
        data['attempts'] = [a for a in data['attempts'] if a.get('book') != book_id]
        self.store.write(data)
        self.store.drop_text(book_id)
        return {'ok': True, 'deleted': b['title']}

    def rename_book(self, book_id: str, b: dict) -> dict:
        data = self.store.read()
        bk = self.store.book(data, book_id)
        if (b.get('title') or '').strip():
            bk['title'] = b['title'].strip()[:120]
        if b.get('author') is not None:
            bk['author'] = str(b['author']).strip()[:80]
        if b.get('note') is not None:
            bk['note'] = str(b['note'])[:400]
        self.store.write(data)
        return {'book': self.store.book_view(data, book_id)}

    def book(self, book_id: str) -> dict:
        data = self.store.read()
        view = self.store.book_view(data, book_id)
        # 目录里不出现任何原文片段——想读原文就进到那一段里去读
        for c in view['chapters']:
            for p in c['passages']:
                p.pop('preview', None)
        return view

    def chapter(self, book_id: str, chapter_no: int) -> dict:
        """读原文用。这是唯一会返回原文内容的接口。"""
        data = self.store.read()
        bk = self.store.book(data, book_id)
        ch = None
        for c in bk['chapters']:
            if c['no'] == chapter_no:
                ch = c
                break
        if ch is None:
            raise S.StoreError('没有第 %s 节。' % chapter_no, 404)
        text = self.store.chapter_body(data, book_id, chapter_no)
        return {
            'book': {'id': bk['id'], 'title': bk['title'], 'author': bk.get('author', '')},
            'chapter': {'no': ch['no'], 'title': ch['title'], 'chars': ch['chars'],
                        'total': len(bk['chapters'])},
            'text': text,
            'passages': [{'no': p['no'], 'chars': p['chars'],
                          'text': self.store.passage_text(book_id, p)}
                         for p in ch['passages']],
            'delay_min': data['settings'].get('delay_min', S.DEFAULT_DELAY_MIN),
        }

    # ─────────────────────── 练习

    def _loc(self, book_id, chapter_no, passage_no):
        data = self.store.read()
        bk, ch, ps = self.store.passage(data, book_id, chapter_no, passage_no)
        return data, bk, ch, ps

    def _attempt_for_write(self, data, book_id, chapter_no, passage_no, create=True):
        a = self.store.attempt(data, book_id, chapter_no, passage_no)
        if a is None:
            if not create:
                return None
            a = self.store.log_attempt(data, book=book_id, chapter=chapter_no,
                                       passage=passage_no)
        return a

    def start(self, book_id: str, chapter_no: int, passage_no: int, b: dict) -> dict:
        """读完原文，开始计时。这是"延迟"的起点。"""
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self._attempt_for_write(data, book_id, chapter_no, passage_no)
        if not a.get('read_at'):
            a['read_at'] = S.now()
            a['read_seconds'] = int(b.get('read_seconds') or 0) or None
        self.store.write(data)
        return {'stage': self.store.stage(data, book_id, chapter_no, passage_no),
                'remaining': self.store.remaining(data, a),
                'delay_min': data['settings'].get('delay_min')}

    def hints(self, book_id: str, chapter_no: int, passage_no: int,
              force: bool = False) -> dict:
        """要一份逐句提示。

        一句原文一条提示——这是富兰克林原本的做法（"short hints of the sentiment
        of each sentence"），也是这个练习的目的决定的：练的就是写好每一句话。

        先查缓存：同一段文字（不管在哪本书里）只花一次钱。缓存没命中才调模型。
        这是工具里唯一一次调用模型的地方。
        """
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        text = self.store.passage_text(book_id, ps)

        st = data['settings']
        ok, why = LLM.check_ready(st)
        if not ok:
            raise S.StoreError(
                '%s所以给不了提示。到「设置」里填上 API Key'
                '（DeepSeek、OpenAI、通义、Kimi 都可以），或者直接不用提示，凭记忆写。'
                % why, 400)

        out = self.warmer.cache.ensure(text, st, force=force)
        return self._hints_payload(out)

    @staticmethod
    def _hints_payload(out: dict) -> dict:
        return {
            'hints': out.get('hints', []),
            'sentences': out.get('sentences', []),
            'n_sent': out.get('n_sent', 0),
            'n_hint': out.get('n_hint', 0),
            'aligned': out.get('aligned', True),
            'dropped_echoes': out.get('dropped_echoes', []),
            'cached': out.get('cached', False),
            'from': out.get('model', ''),
            'seconds': out.get('seconds'),
            'usage': out.get('usage'),
            'truncated': out.get('truncated', False),
        }

    # ─────────────────────── 提示卡：批量与账目

    def summary_plan(self, book_id: str) -> dict:
        """先算账：这本书要做多少张提示卡、多少已在缓存里、大概多少 token。"""
        data = self.store.read()
        bk = self.store.book(data, book_id)
        texts = SUM.Warmer._book_passages(self.store, data, bk)
        est = self.warmer.cache.estimate(texts, data['settings'])
        est['book'] = {'id': bk['id'], 'title': bk['title']}
        est['stats'] = self.warmer.cache.stats()
        est['ready'] = LLM.check_ready(data['settings'])[0]
        est['job'] = self.warmer.status(book_id)
        est['concurrency'] = self.warmer.concurrency
        return est

    def summary_warm(self, book_id: str) -> dict:
        data = self.store.read()
        ok, why = LLM.check_ready(data['settings'])
        if not ok:
            raise S.StoreError('%s先到「设置」里填好。' % why, 400)
        return self.warmer.start(book_id)

    def summary_cancel(self, book_id: str) -> dict:
        return self.warmer.cancel(book_id)

    def summary_status(self, book_id: str) -> dict:
        return {'job': self.warmer.status(book_id),
                'stats': self.warmer.cache.stats()}

    def summary_clear(self, b: dict) -> dict:
        r = self.warmer.cache.clear(b.get('model') or None)
        return {'ok': True, **r, 'stats': self.warmer.cache.stats()}

    def write_view(self, book_id: str, chapter_no: int, passage_no: int) -> dict:
        """写稿页面的数据。**这里绝不包含原文。**"""
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self._attempt_for_write(data, book_id, chapter_no, passage_no)
        stage = self.store.stage(data, book_id, chapter_no, passage_no)

        if stage == 'unread':
            raise S.StoreError('还没读原文。先去读那一段。', 409)
        if stage == 'done':
            raise S.StoreError('这一段已经练完了。', 409)

        src = self.store.passage_text(book_id, ps)

        # 已经交过稿（按下交稿按钮，不是自动保存）→ 直接把对照给出去
        if a.get('wrote_at'):
            return self._compare_payload(data, bk, ch, ps, a, src)

        remaining = self.store.remaining(data, a)
        st = data['settings']
        # 逐句提示：命中缓存就直接带上，写稿页一打开就有，不用等模型。
        # 这是"提前备好"能省时间的原理——答案本来就在本地。
        cached = self.warmer.cache.get(src, (st.get('model') or '').strip(), count=False)
        payload = {
            'book': {'id': bk['id'], 'title': bk['title'], 'author': bk.get('author', '')},
            # 练习页不显示节标题：它是从原文第一句截出来的，写稿时挂在标题栏
            # 等于把这一段的开头送给你（出厂自检就是抓到这一点才拦下来的）。
            'chapter': {'no': ch['no']},
            'passage': {'no': ps['no'], 'chars': ps['chars'],
                        'sentences': len(S.nonempty_sentences(src))},
            'stage': stage,
            'delay_min': st.get('delay_min', S.DEFAULT_DELAY_MIN),
            'remaining': remaining,
            'hints': (cached or {}).get('hints', []),
            'has_hints': bool(cached),
            'hints_cached': bool(cached),
            'llm_ready': LLM.check_ready(st)[0],
            'draft': a.get('draft') or '',
            'saved_at': S.iso(a.get('draft_at')),
        }
        # 出厂自检：写稿页面上不许出现原文。
        # 这里的 min_len 放得比默认宽一点（14 字）：提示是模型写的话，
        # 偶尔有一小截正好和原文重合是正常的；整句照抄会超过这个长度，
        # 而且那种条在生成时就已被 strip_echoes 摘掉了。
        leaked = find_leak(src, payload, min_len=14, allow_summary=True)
        if leaked:
            sys.stderr.write('拒绝返回写稿数据：疑似包含原文 %r\n' % leaked[:3])
            raise S.StoreError('工具自检发现写稿页可能夹带了原文，已中止这次请求。', 500)
        return payload

    def compare_view(self, book_id, chapter_no, passage_no) -> dict:
        """看某一轮的对照。练完之后再回来翻看，走的是这个接口。"""
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self.store.attempt(data, book_id, chapter_no, passage_no)
        if not a or not a.get('wrote_at'):
            raise S.StoreError('这一段还没写过。', 404)
        return self._compare_payload(data, bk, ch, ps, a,
                                     self.store.passage_text(book_id, ps))

    def save_draft(self, book_id, chapter_no, passage_no, text) -> dict:
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self._attempt_for_write(data, book_id, chapter_no, passage_no)
        if a.get('seen_at'):
            raise S.StoreError('这一段已经练完了，不再改稿。')
        if a.get('wrote_at'):
            # 交稿之后原文已经摊开在你面前了，这时候再改稿就不是凭记忆在写了。
            raise S.StoreError('这一稿已经交了、原文也看过了，所以不再改稿。'
                               '想重写就换一段练。')
        a['draft'] = (text or '')[:60000]
        a['draft_at'] = S.now()
        if not a.get('started_write_at'):
            a['started_write_at'] = S.now()
        self.store.write(data)
        return {'ok': True, 'chars': S.plain_len(a['draft']), 'saved_at': S.iso(a['draft_at'])}

    def submit(self, book_id, chapter_no, passage_no, b) -> dict:
        """交稿。交完就把原文和自己写的并排摆出来。"""
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self._attempt_for_write(data, book_id, chapter_no, passage_no)
        if a.get('seen_at'):
            raise S.StoreError('这一段已经练完了。')
        if a.get('wrote_at'):
            raise S.StoreError('这一稿已经交过了。想重写就换一段练；'
                               '已经看过的原文不可能再收回去，所以这里不给重交。')

        draft = (b.get('draft') or '').strip()
        if not draft:
            raise S.StoreError('还没写呢。写不出来可以少写几句，但不能空着交。')

        # 延迟闸门：读完原文后要隔一会儿才让写
        left = self.store.remaining(data, a)
        if left > 0 and not b.get('force'):
            raise S.StoreError('刚读完原文，再等 %d 秒。' % left, 423)

        ws = b.get('write_seconds')
        a['draft'] = draft[:60000]
        a['wrote_at'] = S.now()
        a['prompt_used'] = bool(b.get('prompt_used'))
        a['write_seconds'] = int(ws) if ws else (
            int(S.now() - a['started_write_at']) if a.get('started_write_at') else None)
        self.store.write(data)
        return self._compare_payload(data, bk, ch, ps, a,
                                     self.store.passage_text(book_id, ps))

    def _hints_of(self, data, src: str) -> list:
        """这一段当时的逐句提示。提示存在缓存里（按原文内容算键），
        不再往每一轮的记录里抄一份——那样同一段文字会存很多遍。"""
        model = (data['settings'].get('model') or '').strip()
        item = self.warmer.cache.get(src, model, count=False)
        return (item or {}).get('hints', [])

    def _compare_payload(self, data, bk, ch, ps, a, src) -> dict:
        hints = self._hints_of(data, src)
        return {
            'book': {'id': bk['id'], 'title': bk['title'], 'author': bk.get('author', '')},
            'chapter': {'no': ch['no']},
            'passage': {'no': ps['no'], 'chars': ps['chars']},
            'stage': 'wrote' if not a.get('seen_at') else 'done',
            'source': src,
            'draft': a.get('draft') or '',
            'hints': hints,
            'has_hints': bool(hints),
            'prompt_used': a.get('prompt_used'),
            'read_seconds': a.get('read_seconds'),
            'write_seconds': a.get('write_seconds'),
            'observation': a.get('observation') or '',
            'seen_at': S.iso(a.get('seen_at')),
            'facts': fact_sheet(src, a.get('draft') or ''),
        }

    def observe(self, book_id, chapter_no, passage_no, b) -> dict:
        """看完对照，写一条整段的笔记，这一轮到此结束。

        以前这里是单独的「我的观察」字段，和逐句笔记是两个入口。
        现在合成一条 scope='passage' 的笔记——用户只需要记住一个地方。
        """
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self.store.attempt(data, book_id, chapter_no, passage_no)
        if not a or not a.get('draft'):
            raise S.StoreError('这一段的稿子还没交。')
        if a.get('seen_at'):
            raise S.StoreError('这一段已经看过了。')
        obs = (b.get('observation') or '').strip()
        if not obs:
            raise S.StoreError('留一句你看到的东西吧。一句就够，比如"我把那句问句丢了"。')
        a['observation'] = obs[:4000]
        a['seen_at'] = S.now()
        # 同时收进这本书的笔记清单
        self.store.add_note(data, bk['id'], chapter_no, passage_no, obs,
                            scope='passage', mine=a.get('draft') or '')
        self.store.write(data)
        return {'ok': True, 'stage': 'done'}

    def sentence(self, book_id, chapter_no, passage_no, sent_no) -> dict:
        """单句练习用：只取出原文的某一句。

        这是刻意开的一个小口子——你要单独练某一句时，总要能看到那一句。
        但它只给**一句**，不会顺带把整段摊开。句子的切法必须和生成提示时
        一致（都用 fk_store.nonempty_sentences），否则编号会对不上。
        """
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        src = self.store.passage_text(book_id, ps)
        sents = S.nonempty_sentences(src)
        if not (1 <= sent_no <= len(sents)):
            raise S.StoreError('这一段只有 %d 句。' % len(sents), 404)
        return {'no': sent_no, 'total': len(sents), 'sentence': sents[sent_no - 1],
                'chars': S.plain_len(sents[sent_no - 1])}

    # ─────────────────────── 笔记（跟着书走的）

    def add_note(self, book_id, chapter_no, passage_no, b) -> dict:
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        text = (b.get('text') or '').strip()
        if not text:
            raise S.StoreError('笔记是空的。一句话也行，比如"我把因果省了"。')
        # 笔记和书绑定，所以书 id 取准确的，不信前端传的
        note = self.store.add_note(data, bk['id'], chapter_no, passage_no, text,
                                   scope=b.get('scope') or 'sentence',
                                   sent_no=int(b.get('sent_no') or 0),
                                   sentence=b.get('sentence') or '',
                                   mine=b.get('mine') or '',
                                   hint=b.get('hint') or '')
        self.store.write(data)
        return {'ok': True, 'note': note}

    def notes(self, book_id) -> dict:
        data = self.store.read()
        bk = self.store.book(data, book_id)
        rows = self.store.notes_of(data, book_id)
        return {'book': {'id': bk['id'], 'title': bk['title']},
                'notes': rows, 'count': len(rows)}

    def drop_note(self, book_id, note_id) -> dict:
        data = self.store.read()
        self.store.book(data, book_id)
        ok = self.store.drop_note(data, book_id, note_id)
        if ok:
            self.store.write(data)
        return {'ok': ok}

    def skip_wait(self, book_id, chapter_no, passage_no) -> dict:
        """跳过等待。用显式标记而不是去改 read_at——否则中途改延迟设置会错位。"""
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self._attempt_for_write(data, book_id, chapter_no, passage_no)
        a['wait_skipped'] = True
        a['wait_skipped_at'] = S.now()
        self.store.write(data)
        return {'ok': True, 'stage': self.store.stage(data, book_id, chapter_no, passage_no)}

    # ─────────────────────── 记录

    def records(self, book_id: str | None = None) -> dict:
        """练习记录。

        **不返回原文**。记录会在"记录"页被一次性列出来，如果把原文捎在里面，
        等于把还没练过的段落一起摊开了。要看某一轮的原文，点开那一轮时
        再单独去取（practice/<书>/<节>/<段>/compare）。
        """
        data = self.store.read()
        titles = {b['id']: b['title'] for b in data['books']}
        rows = []
        for a in data['attempts']:
            if book_id and a.get('book') != book_id:
                continue
            src = ''
            try:
                _, _, ps = self.store.passage(data, a.get('book'), a.get('chapter'),
                                              a.get('passage'))
                src = self.store.passage_text(a.get('book'), ps)
            except S.StoreError:
                src = ''
            rows.append({
                'id': a['id'],
                'book': titles.get(a.get('book'), '（已删除的书）'),
                'book_id': a.get('book'),
                'chapter': a.get('chapter'), 'passage': a.get('passage'),
                'read_at': S.iso(a.get('read_at')),
                'read_seconds': a.get('read_seconds'),
                'wrote_at': S.iso(a.get('wrote_at')),
                'write_seconds': a.get('write_seconds'),
                'seen_at': S.iso(a.get('seen_at')),
                'prompt_used': a.get('prompt_used'),
                'chars': S.plain_len(a.get('draft') or ''),
                'draft': a.get('draft') or '',
                'hints': self._hints_of(data, src) if src else [],
                'has_hints': bool(src and self._hints_of(data, src)),
                'observation': a.get('observation') or '',
                'stage': ('done' if a.get('seen_at') else
                          'wrote' if a.get('wrote_at') else 'reading'),
            })
        rows.sort(key=lambda r: r['wrote_at'] or r['read_at'] or '', reverse=True)
        counts = {
            'records': len(rows),
            'done': len([r for r in rows if r['stage'] == 'done']),
            'wrote': len([r for r in rows if r['stage'] == 'wrote']),
            'using_prompt': len([r for r in rows if r['prompt_used']]),
        }
        return {'rows': rows, 'counts': counts,
                'books': [{'id': b['id'], 'title': b['title']} for b in data['books']]}

    def export(self, book_id, chapter_no, passage_no) -> tuple[str, str]:
        data, bk, ch, ps = self._loc(book_id, chapter_no, passage_no)
        a = self.store.attempt(data, book_id, chapter_no, passage_no)
        if not a or not a.get('draft'):
            raise S.StoreError('这一段还没写过。', 404)
        src = self.store.passage_text(book_id, ps)
        lines = [
            '# %s　%s　第 %d 段' % (bk['title'], ch['title'], ps['no']),
            '',
            '- 读完时间：%s' % (S.iso(a.get('read_at')) or '未记录'),
            '- 读原文用时：%s' % _dur(a.get('read_seconds')),
            '- 交稿时间：%s' % (S.iso(a.get('wrote_at')) or '未记录'),
            '- 写作用时：%s' % _dur(a.get('write_seconds')),
            '- 用了提示：%s' % ('是' if a.get('prompt_used') else '否'),
            '',
        ]
        hints = self._hints_of(data, src)
        if hints:
            lines += ['## 当时给的逐句提示', '']
            for h in hints:
                lines.append('%d. %s' % (h.get('no', 0), h.get('hint', '')))
            lines += ['']
        lines += ['## 原文', '', src, '', '## 我的稿子', '', a.get('draft') or '', '']
        if a.get('observation'):
            lines += ['## 我的观察', '', a['observation'], '']
        lines += ['---', '', '由富兰克林写作工具导出。原文与稿子都是你自己的记录。']
        name = '%s-%s-%d.md' % (re.sub(r'[^A-Za-z0-9_-]+', '-', bk['title'])[:20] or 'book',
                                ch['no'], ps['no'])
        utf8 = urllib.parse.quote('%s %s 第%d段.md' % (bk['title'], ch['title'], ps['no']))
        return '\n'.join(lines), 'attachment; filename="%s"; filename*=UTF-8\'\'%s' % (name, utf8)


def _dur(sec):
    if not sec:
        return '未记录'
    m, s = divmod(int(sec), 60)
    return ('%d 分 %d 秒' % (m, s)) if m else ('%d 秒' % s)


# ══════════════════════════════════════════════════════════════════
# 对照时给的事实：原文里有哪些连续片段没出现在你的稿子里
#
# 这是纯字符串比对的结果，不是评分：不给比率、不给等级、不说好坏。
# 只说一件事——"原文的这几个地方，你的稿子里没有"。
# 判断（是有意省略、还是真忘了、要不要紧）完全留给你。
# ══════════════════════════════════════════════════════════════════

FUNC = set(
    '的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那'
    '上下来去时么呢吧啊呀吗着过要会能可所因然并且如若则把让给向从当'
    '一二三四五六七八九十百千万两有些个只种样条张支又再才更没'
)


def content_spans(text: str, lo: int = 2, hi: int = 8) -> list[str]:
    """把文本切成"连续实义串"。

    功能字、标点、数字、拉丁字母都当边界。这样切出来的每一段要么是词，
    要么是连着的一小串词，而且**一定是原文里真实存在的连续子串**，
    所以命中判定是纯字符串比对，可复现、不含判断。
    """
    body = re.sub(r'[%s\s\dA-Za-z]' % re.escape(S.PUNCT), ' ', text or '')
    runs = []
    for seg in body.split(' '):
        cur = ''
        for ch in seg:
            if ch in FUNC:
                if cur:
                    runs.append(cur)
                    cur = ''
            else:
                cur += ch
        if cur:
            runs.append(cur)
    seen, out = set(), []
    for r in runs:
        if lo <= len(r) <= hi and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def missing_segments(source: str, draft: str, limit: int = 12) -> list[str]:
    """原文里没出现在你稿子里的连续片段，按原文顺序返回。

    把相邻的缺失片段并成一段，读起来才像"这句话我没写"，
    而不是一堆碎词。超出 limit 的截断，并如实说明还剩多少条。
    """
    spans = content_spans(source)
    miss_idx = [i for i, w in enumerate(spans) if w not in (draft or '')]
    out = []
    for i in miss_idx:
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    segs = ['、'.join(spans[a:b + 1]) for a, b in out]
    segs = [s for s in segs if s]
    return segs[:limit]


def fact_sheet(source: str, draft: str) -> dict:
    spans = content_spans(source)
    hit = [w for w in spans if w in (draft or '')]
    miss = [w for w in spans if w not in (draft or '')]
    return {
        'hit': hit,
        'miss': miss,
        'hit_count': len(hit),
        'miss_count': len(miss),
        'total': len(spans),
        'segments': missing_segments(source, draft),
        'note': '上面这些是原文里有、你的稿子里没有的片段。'
                '没出现不等于写得不好——可能你有意省略，也可能换了说法，'
                '也可能原文那一处本来就无关紧要。要不要紧，你自己看原文判断。',
    }


def find_leak(source: str, payload, min_len: int = 8,
              allow_summary: bool = False) -> list[str]:
    """检查一段待发数据里是否夹带了原文的长片段。

    写稿页绝不能把原文发出去。与其相信调用方记得住，不如每次发之前机械扫一遍。

    allow_summary=True 时放宽到 min_len：提示卡是模型写的话，偶尔会有一小截
    正好和原文重合（"符是城隍庙送来的"这种），这不算泄露；但整句照抄会超过
    这个长度，仍然拦得住。提示卡里真正的照抄在生成那一步就会被丢掉，
    见 fk_summary.strip_echoes()。
    """
    blob = json.dumps(payload, ensure_ascii=False)
    flat = re.sub(r'[%s\s]' % re.escape(S.PUNCT), '', source or '')
    grams = set()
    for i in range(0, max(0, len(flat) - min_len + 1)):
        grams.add(flat[i:i + min_len])
    if not allow_summary:          # 整句比对只对非模型文本有意义
        for s in S.split_sentences(source or ''):
            if S.plain_len(s) >= min_len:
                grams.add(s)
                grams.add(re.sub(r'[%s\s]' % re.escape(S.PUNCT), '', s))
    return sorted(g for g in grams if g in blob)


def _read_text_file(p: str) -> str | None:
    p = os.path.abspath(os.path.expanduser(p.strip().strip('"')))
    if not os.path.isfile(p):
        return None
    if os.path.splitext(p)[1].lower() not in ('.txt', '.md', '.text', ''):
        return None
    for enc in ('utf-8', 'utf-8-sig', 'gb18030'):
        try:
            with open(p, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


def _guess_title(text: str, file_path: str) -> str:
    if file_path:
        base = os.path.splitext(os.path.basename(file_path))[0].strip()
        if base:
            return base
    first = S.split_sentences(text)
    head = re.sub(r'\s+', '', first[0]) if first else ''
    return (head[:20] + '…') if len(head) > 20 else (head or '未命名')


# ══════════════════════════════════════════════════════════════════
# HTTP
# ══════════════════════════════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    server_version = 'fk/2.0'
    api: Api = None
    quiet = False

    def log_message(self, fmt, *args):
        if not self.quiet:
            sys.stderr.write('  %s\n' % (fmt % args))

    def _send(self, code, body: bytes, ctype: str, extra=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode('utf-8'),
                   MIME['.json'])

    def _err(self, message, code=400, hint=''):
        self._json({'error': message, 'code': code, 'hint': hint}, code)

    def do_GET(self):
        self._route('GET')

    def do_HEAD(self):
        self._route('GET')

    def do_POST(self):
        self._route('POST')

    def do_PUT(self):
        self._route('PUT')

    def do_DELETE(self):
        self._route('DELETE')

    def _body(self):
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0:
            return {}
        raw = self.rfile.read(n)
        if n > 6_000_000:
            raise S.StoreError('请求体太大了。')
        try:
            return json.loads(raw.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise S.StoreError('请求体不是合法 JSON。')

    def _route(self, method):
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        query = urllib.parse.parse_qs(parsed.query)
        try:
            if path.startswith('/api/'):
                with _lock:
                    self._api(method, path[5:].strip('/').split('/'), query)
            else:
                self._static(path)
        except S.StoreError as e:
            self._err(e.message, e.code)
        except LLM.LlmError as e:
            self._err(e.message, e.code, e.hint)
        except BrokenPipeError:
            pass
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._err('工具内部出错了：%s' % e, 500)

    def _api(self, method, parts, query):
        api = self.api
        head = parts[0] if parts else ''
        q = lambda k, d=None: query.get(k, [d])[0]

        if method == 'GET':
            if head == 'health':
                return self._json({'ok': True, 'tool': 'fk', 'version': 2,
                                   # 测试跑器靠 STUB 分辨"这个 8137 是不是假模型服务"。
                                   # 真服务永远是 False，见 tests/serve_stub.py。
                                   'stub': bool(getattr(sys.modules[__name__], 'STUB', False)),
                                   'time': time.time()})
            if head == 'shelf':
                return self._json(api.shelf())
            if head == 'settings':
                return self._json(api.settings())
            if head == 'records':
                return self._json(api.records(q('book')))
            if head == 'books' and len(parts) == 2:
                return self._json(api.book(parts[1]))
            if head == 'books' and len(parts) == 3 and parts[2] == 'notes':
                return self._json(api.notes(parts[1]))
            if head == 'books' and len(parts) == 4 and parts[2] == 'summaries':
                if parts[3] == 'plan':
                    return self._json(api.summary_plan(parts[1]))
                if parts[3] == 'status':
                    return self._json(api.summary_status(parts[1]))
            if head == 'books' and len(parts) == 4 and parts[2] == 'chapters':
                return self._json(api.chapter(parts[1], int(parts[3])))
            if head == 'practice' and len(parts) == 5:
                bid, cno, pno = parts[1], int(parts[2]), int(parts[3])
                if parts[4] == 'write':
                    return self._json(api.write_view(bid, cno, pno))
                if parts[4] == 'compare':
                    return self._json(api.compare_view(bid, cno, pno))
            if head == 'export' and len(parts) == 4:
                body, disp = api.export(parts[1], int(parts[2]), int(parts[3]))
                return self._send(200, body.encode('utf-8'),
                                  'text/markdown; charset=utf-8',
                                  {'Content-Disposition': disp})

        if method == 'POST':
            b = self._body()
            # 注意：每一条都要连长度一起判，否则 /api/books/<id>/summaries/warm
            # 会被 '/api/books' 这条先接住，变成一次莫名其妙的导入。
            if head == 'books' and len(parts) == 1:
                return self._json(api.add_book(b))
            if head == 'settings' and len(parts) == 1:
                return self._json(api.save_settings(b))
            if head == 'llm' and len(parts) == 2 and parts[1] == 'test':
                return self._json(api.test_llm())
            if head == 'summaries' and len(parts) == 2 and parts[1] == 'clear':
                return self._json(api.summary_clear(b))
            if head == 'books' and len(parts) == 4 and parts[2] == 'summaries':
                if parts[3] == 'warm':
                    return self._json(api.summary_warm(parts[1]))
                if parts[3] == 'cancel':
                    return self._json(api.summary_cancel(parts[1]))
            if head == 'practice' and len(parts) == 5:
                bid, cno, pno, act = parts[1], int(parts[2]), int(parts[3]), parts[4]
                if act == 'start':
                    return self._json(api.start(bid, cno, pno, b))
                if act == 'hints':
                    return self._json(api.hints(bid, cno, pno, bool(b.get('force'))))
                if act == 'submit':
                    return self._json(api.submit(bid, cno, pno, b))
                if act == 'observe':
                    return self._json(api.observe(bid, cno, pno, b))
                if act == 'skip-wait':
                    return self._json(api.skip_wait(bid, cno, pno))
                if act == 'note':
                    return self._json(api.add_note(bid, cno, pno, b))
            if head == 'practice' and len(parts) == 6 and parts[4] == 'sentence':
                return self._json(api.sentence(parts[1], int(parts[2]), int(parts[3]),
                                               int(parts[5])))

        if method == 'PUT':
            b = self._body()
            if head == 'books' and len(parts) == 2:
                return self._json(api.rename_book(parts[1], b))
            if head == 'practice' and len(parts) == 5 and parts[4] == 'draft':
                return self._json(api.save_draft(parts[1], int(parts[2]),
                                                 int(parts[3]), b.get('text')))

        if method == 'DELETE':
            if head == 'books' and len(parts) == 2:
                return self._json(api.delete_book(parts[1], q('confirm', '')))
            if head == 'books' and len(parts) == 4 and parts[2] == 'notes':
                return self._json(api.drop_note(parts[1], parts[3]))

        return self._err('没有这个接口：%s' % self.path, 404)

    def _static(self, path):
        if path in ('/', ''):
            path = '/index.html'
        rel = os.path.normpath(path.lstrip('/\\'))
        if rel.startswith('..') or os.path.isabs(rel):
            return self._err('路径不合法。', 403)
        full = os.path.join(WEB_DIR, rel)
        if not os.path.isfile(full):
            return self._err('没有这个文件：%s' % rel, 404)
        with open(full, 'rb') as f:
            body = f.read()
        self._send(200, body, MIME.get(os.path.splitext(full)[1].lower(),
                                       'application/octet-stream'))


def free_port(preferred=DEFAULT_PORT, tries=25):
    for p in range(preferred, preferred + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(('127.0.0.1', p))
                return p
            except OSError:
                continue
    raise SystemExit('从 %d 起找不到可用端口。' % preferred)


def serve(data_dir=DATA_DIR, port=None, open_browser=True, quiet=False):
    api = Api(data_dir)
    port = port or free_port()
    Handler.api = api
    Handler.quiet = quiet
    httpd = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    url = 'http://127.0.0.1:%d/' % port
    print('富兰克林写作工具')
    print('  地址：%s' % url)
    print('  书架：%s' % api.store.root)
    print('  只监听本机。原文和你的稿子都留在这台机器上。')
    print('  按 Ctrl+C 结束。')
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止。')
    finally:
        httpd.server_close()
    return 0


def main():
    ap = argparse.ArgumentParser(description='富兰克林写作工具（本地服务）')
    ap.add_argument('--port', type=int, default=None)
    ap.add_argument('--data', default=DATA_DIR, help='书架目录')
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    return serve(a.data, a.port, not a.no_browser, a.quiet)


if __name__ == '__main__':
    sys.exit(main())
