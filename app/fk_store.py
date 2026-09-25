#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk_store — 书架的数据层。

一件事：让你导入的书和写过的字**一直在这儿**。

设计取舍（都是为了让数据"能一直在"）：
  · 目录里放两样东西：index.json（书目、章节、练习记录）+ texts/*.txt（原文，一篇一个文件）。
  · 全部是纯文本，你自己能打开、能复制、能备份、能搬到别的机器。
  · 每次写入先写临时文件再原子替换，中途断电不会把存档写坏。
  · 写入前会留一份上一版（index.json.bak），改坏了还能退回去。
  · 不依赖任何服务或云。删掉这个目录就等于没用过。

数据结构（schema 2）：
  index.json
    schema      2
    books[]     {id, title, author, added, chars, chapters[], note, cover}
    attempts[]  {id, book, chapter, passage, ...}
    settings    {provider, base_url, model, api_key, delay_min, ...}

  chapters[]    {no, title, chars, passages[]}
  passages[]    {no, start, end, chars}       # 位置索引，原文只存一份
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import uuid

SCHEMA = 2
DEFAULT_PASSAGE_CHARS = 300
DEFAULT_DELAY_MIN = 3


class StoreError(Exception):
    """预期内的用户级错误，接口层转成 4xx。"""

    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


def now() -> float:
    return time.time()


def iso(ts) -> str | None:
    if not ts:
        return None
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))


def new_id(prefix: str) -> str:
    return '%s-%s' % (prefix, uuid.uuid4().hex[:10])


class Store:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.index_path = os.path.join(self.root, 'index.json')
        self.texts_dir = os.path.join(self.root, 'texts')

    # ─────────────────────────── 读写

    def _empty(self) -> dict:
        return {
            'schema': SCHEMA,
            'books': [],
            'attempts': [],
            'settings': {
                'provider': 'deepseek',
                'base_url': 'https://api.deepseek.com/v1',
                'model': 'deepseek-chat',
                'api_key': '',
                'delay_min': DEFAULT_DELAY_MIN,
                'passage_chars': DEFAULT_PASSAGE_CHARS,
            },
        }

    def read(self) -> dict:
        if not os.path.exists(self.index_path):
            return self._empty()
        try:
            with open(self.index_path, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            bak = self.index_path + '.bak'
            if os.path.exists(bak):
                raise StoreError(
                    '存档读取失败（%s）。上一版备份还在：%s，把它改名成 index.json 就能退回。'
                    % (e, bak), 500)
            raise StoreError('存档读取失败：%s' % e, 500)
        for k, v in self._empty().items():
            data.setdefault(k, v)
        if not isinstance(data.get('settings'), dict):
            data['settings'] = self._empty()['settings']
        for k, v in self._empty()['settings'].items():
            data['settings'].setdefault(k, v)
        if data.get('schema') != SCHEMA:
            data['schema'] = SCHEMA
        return data

    def write(self, data: dict) -> None:
        os.makedirs(self.root, exist_ok=True)
        tmp = self.index_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(self.index_path):
            try:
                shutil.copyfile(self.index_path, self.index_path + '.bak')
            except OSError:
                pass
        os.replace(tmp, self.index_path)

    # ─────────────────────────── 原文文件

    def text_path(self, book_id: str) -> str:
        return os.path.join(self.texts_dir, book_id + '.txt')

    def save_text(self, book_id: str, text: str) -> None:
        os.makedirs(self.texts_dir, exist_ok=True)
        p = self.text_path(book_id)
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            f.write(text)
        os.replace(tmp, p)

    def load_text(self, book_id: str) -> str | None:
        p = self.text_path(book_id)
        if not os.path.exists(p):
            return None
        with open(p, encoding='utf-8') as f:
            return f.read()

    def drop_text(self, book_id: str) -> None:
        p = self.text_path(book_id)
        if os.path.exists(p):
            os.remove(p)

    # ─────────────────────────── 找东西

    def book(self, data: dict, book_id: str) -> dict:
        for b in data['books']:
            if b['id'] == book_id:
                return b
        raise StoreError('书架上没有这本书。', 404)

    def passage(self, data: dict, book_id: str, chapter_no: int, passage_no: int):
        """返回 (book, chapter, passage)。"""
        b = self.book(data, book_id)
        ch = None
        for c in b['chapters']:
            if c['no'] == chapter_no:
                ch = c
                break
        if ch is None:
            raise StoreError('这本书里没有第 %s 节。' % chapter_no, 404)
        ps = None
        for p in ch['passages']:
            if p['no'] == passage_no:
                ps = p
                break
        if ps is None:
            raise StoreError('第 %s 节里没有第 %s 段。' % (chapter_no, passage_no), 404)
        return b, ch, ps

    def passage_text(self, book_id: str, passage: dict) -> str:
        """取一段的原文。段的位置是**相对整篇原文**的绝对位置。"""
        text = self.load_text(book_id)
        if text is None:
            raise StoreError('这本书的原文文件丢了。', 500)
        return text[passage['start']:passage['end']]

    def chapter_body(self, data: dict, book_id: str, chapter_no: int) -> str:
        text = self.load_text(book_id)
        if text is None:
            raise StoreError('这本书的原文文件丢了。', 500)
        bk = self.book(data, book_id)
        for c in bk['chapters']:
            if c['no'] == chapter_no:
                if '_start' in c and '_end' in c:
                    return text[c['_start']:c['_end']]
                if c['passages']:
                    return text[c['passages'][0]['start']:c['passages'][-1]['end']]
                return ''
        raise StoreError('这本书里没有第 %s 节。' % chapter_no, 404)

    @staticmethod
    def attempts_of(data: dict, book_id: str, chapter_no: int, passage_no: int) -> list[dict]:
        return [a for a in data['attempts']
                if a['book'] == book_id and a['chapter'] == chapter_no
                and a['passage'] == passage_no]

    def attempt(self, data: dict, book_id: str, chapter_no: int, passage_no: int):
        rows = self.attempts_of(data, book_id, chapter_no, passage_no)
        return rows[-1] if rows else None

    # ─────────────────────────── 状态

    def stage(self, data: dict, book_id: str, chapter_no: int, passage_no: int) -> str:
        """这一段走到哪一步了。

        unread  还没读过原文
        read    读过了，在延迟里（还不能写）
        ready   可以写
        wrote   交稿了，等你看对照
        done    对照也看过了

        注意：自动保存的草稿不算"交稿"。只有真的按下交稿才算——
        否则你只是随手存了两句，页面就会跳到对照去，把原文摊开在你面前。
        """
        a = self.attempt(data, book_id, chapter_no, passage_no)
        if not a:
            return 'unread'
        if a.get('seen_at'):
            return 'done'
        if a.get('wrote_at'):
            return 'wrote'
        if not a.get('read_at'):
            return 'unread'
        if self.remaining(data, a) > 0:
            return 'read'
        return 'ready'

    def remaining(self, data: dict, attempt: dict) -> int:
        if attempt.get('wait_skipped'):
            return 0
        delay = int(float(data['settings'].get('delay_min') or 0) * 60)
        if not delay or not attempt.get('read_at'):
            return 0
        return max(0, int(attempt['read_at'] + delay - now()))

    # ─────────────────────────── 概览

    def shelf(self, data: dict) -> list[dict]:
        out = []
        for b in data['books']:
            total = sum(len(c['passages']) for c in b['chapters'])
            counts = {'total': total, 'done': 0, 'wrote': 0, 'reading': 0, 'ready': 0}
            for c in b['chapters']:
                for p in c['passages']:
                    st = self.stage(data, b['id'], c['no'], p['no'])
                    if st == 'done':
                        counts['done'] += 1
                    elif st == 'wrote':
                        counts['wrote'] += 1
                    elif st == 'read':
                        counts['reading'] += 1
                    elif st == 'ready':
                        counts['ready'] += 1
            out.append({
                'id': b['id'], 'title': b['title'], 'author': b.get('author', ''),
                'chars': b['chars'], 'chapters': len(b['chapters']),
                'added': iso(b['added']), 'counts': counts,
                'note': b.get('note', ''),
            })
        out.sort(key=lambda x: x['added'] or '', reverse=True)
        return out

    def add_note(self, data: dict, book_id: str, chapter_no: int, passage_no: int,
                 text: str, scope: str = 'sentence', sent_no: int = 0,
                 sentence: str = '', mine: str = '', hint: str = '') -> dict:
        """记一条笔记。笔记跟着**这本书**走，不属于某一轮练习。

        scope='sentence' 落在某一句上（单句练习里记的）；
        scope='passage'  落在整段上（写完对照后记的整体印象）。
        两者存在同一张清单里——用户只需要记住一个入口。
        """
        a = self.attempt(data, book_id, chapter_no, passage_no)
        if a is None:
            a = self.log_attempt(data, book=book_id, chapter=chapter_no,
                                 passage=passage_no)
        note = {
            'id': new_id('n'),
            'at': now(),
            'scope': 'passage' if scope == 'passage' else 'sentence',
            'chapter': chapter_no,
            'passage': passage_no,
            'sent_no': int(sent_no or 0),
            'sentence': (sentence or '')[:500],
            'mine': (mine or '')[:500],
            'hint': (hint or '')[:200],
            'text': (text or '').strip()[:2000],
        }
        a.setdefault('notes', []).append(note)
        return note

    def notes_of(self, data: dict, book_id: str) -> list[dict]:
        """这本书的全部笔记，按时间倒序。

        「我的观察」不再单独存一份：写完整段后的那一段话，就是一条 scope='passage'
        的笔记。统一之后只有一个入口，用户翻笔记时也能看到当时整体在想什么。
        """
        out = []
        for a in data['attempts']:
            if a.get('book') != book_id:
                continue
            # 老存档里观察是单独一个字段，读的时候补成一条笔记，不丢
            obs = (a.get('observation') or '').strip()
            if obs and not any((n.get('scope') == 'passage'
                                and n.get('text') == obs) for n in (a.get('notes') or [])):
                out.append({
                    'id': 'obs-%s' % a.get('id', ''), 'at': a.get('seen_at'),
                    'scope': 'passage', 'chapter': a.get('chapter'),
                    'passage': a.get('passage'), 'sent_no': 0,
                    'sentence': '', 'mine': a.get('draft') or '', 'hint': '',
                    'text': obs, 'legacy': True,
                })
            for n in a.get('notes') or []:
                out.append({**n, 'book': book_id})
        out.sort(key=lambda x: x.get('at') or 0, reverse=True)
        return out

    def drop_note(self, data: dict, book_id: str, note_id: str) -> bool:
        for a in data['attempts']:
            if a.get('book') != book_id:
                continue
            notes = a.get('notes') or []
            keep = [n for n in notes if n.get('id') != note_id]
            if len(keep) != len(notes):
                a['notes'] = keep
                return True
        return False

    def book_view(self, data: dict, book_id: str) -> dict:
        b = self.book(data, book_id)
        chapters = []
        for c in b['chapters']:
            ps = []
            for p in c['passages']:
                a = self.attempt(data, book_id, c['no'], p['no'])
                st = self.stage(data, book_id, c['no'], p['no'])
                row = {'no': p['no'], 'chars': p['chars'], 'stage': st,
                       'preview': self._preview(book_id, p),
                       'have_hints': bool(a and a.get('hints'))}
                if a and st in ('read', 'ready'):
                    row['remaining'] = self.remaining(data, a)
                if a and a.get('draft'):
                    row['draft_chars'] = len(a['draft'])
                ps.append(row)
            chapters.append({'no': c['no'], 'title': c['title'], 'chars': c['chars'],
                             'passages': ps})
        return {
            'id': b['id'], 'title': b['title'], 'author': b.get('author', ''),
            'note': b.get('note', ''), 'chars': b['chars'], 'added': iso(b['added']),
            'chapters': chapters,
            'counts': next(x['counts'] for x in self.shelf(data) if x['id'] == book_id),
        }

    def _preview(self, book_id: str, passage: dict, n: int = 34) -> str:
        """段首一小截，用于目录里认路。只在书内页出现。"""
        try:
            t = self.passage_text(book_id, passage)
        except StoreError:
            return ''
        t = t.strip()
        return t[:n] + ('…' if len(t) > n else '')

    def log_attempt(self, data: dict, **kw) -> dict:
        a = {
            'id': new_id('a'), 'created': now(),
            'read_at': None, 'read_seconds': None, 'wait_skipped': False,
            'summary': '', 'summary_from': '', 'prompt_used': False,
            'hints': [], 'hints_at': None, 'notes': [],
            'started_write_at': None, 'write_seconds': None,
            'draft': '', 'draft_at': None, 'wrote_at': None,
            'seen_at': None, 'observation': '',
            'book': '', 'chapter': 0, 'passage': 0,
        }
        a.update(kw)
        data['attempts'].append(a)
        return a


# ══════════════════════════════════════════════════════════════════
# 切分：把一本书切成 节 → 段
# ══════════════════════════════════════════════════════════════════

SENT_END = '。！？'
PUNCT = '，。！？；：、“”"（）《》…—'


def plain_len(s: str) -> int:
    return len(re.sub(r'[%s\s]' % re.escape(PUNCT), '', s or ''))


def split_sentences(text: str):
    """按句末标点切句。

    **刻意不 strip 空白**：真实范文里常有段落换行，切句如果把它吃掉，
    切分就不再可逆——"拼回去等于原文"这条性质是测试要保证的，
    也是"原文只存一份、按需切回来"这个设计成立的前提。

    要"能拿去编号、显示、练的句子"，用 nonempty_sentences()。
    """
    out, cur = [], ''
    for ch in text:
        cur += ch
        if ch in SENT_END:
            out.append(cur)
            cur = ''
    if cur.strip():
        out.append(cur)
    return out


def nonempty_sentences(text: str) -> list[str]:
    """能拿去编号、显示、练的句子：压掉多余空白、去掉只剩空白的。

    为什么单独一个函数：从网页复制来的文章，行首行尾常带空格，
    还可能出现"整行只有空白"的空句子——它们会让提示的编号和页面上
    的句子对不上，也会在句子列表里留下难看的空档。
    而 split_sentences 必须保持无损，所以过滤放在这一层。
    """
    out = []
    for s in split_sentences(text or ''):
        t = re.sub(r'[ \t\u3000]+', ' ', s).strip()
        if t:
            out.append(t)
    return out


def tidy_whitespace(text: str) -> str:
    """导入时把空白理一遍：行内多余空白压成一个，连续空行最多留一个。

    只动空白，不碰任何实字和标点。这样"带空格的行"不会在切分时
    留下一堆没内容的碎片。
    """
    t = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    t = re.sub(r'[ \t\u3000]+', ' ', t)          # 行内空白压缩
    t = re.sub(r' *\n *', '\n', t)               # 行首行尾的空白去掉
    t = re.sub(r'\n{2,}', '\n\n', t)             # 连续空行最多留一个
    return t.strip()


def _split_regions(text: str) -> list[tuple[int, int, str]]:
    """把文本切成"自然区块"。

    空行一定断开。没有空行的连续几行也断开——一行一段的电子书就是这样，
    如果把它们粘成一块，后面就会在段落中间下刀（实测会切出"我看后却"这种半句）。

    返回 [(起点, 终点, 原文)]，位置是相对传入文本的。
    """
    out = []
    for m in re.finditer(r'[^\n]+(?:\n(?![ \t]*\n)[^\n]+)*', text):
        g = m.group()
        if not g.strip():
            continue
        if '\n' in g:
            # 这一段里只有单换行 → 逐行当区块
            off = m.start()
            for line in g.split('\n'):
                if line.strip():
                    s = off + len(line) - len(line.lstrip())
                    e = off + len(line.rstrip())
                    out.append((s, e, text[s:e]))
                off += len(line) + 1
        else:
            out.append((m.start(), m.end(), g))
    return out


def _looks_like_title(s: str) -> bool:
    """很短、没有句末标点的一行，多半是章节名而不是正文。

    这是形态判断，不是语义判断：只看长度和末尾有没有句号。
    """
    t = s.strip()
    if not t or '\n' in t:
        return False
    if len(t) > 20 or t[-1] in '。！？；':
        return False
    if re.match(r'^\s*(第\s*[0-9一二三四五六七八九十百零]+\s*[章节回卷篇部]|序|前言|后记|尾声|附录)',
                t):
        return True
    return len(t) <= 14


def split_chapters(text: str, target: int = 900, merge_small: bool = False) -> list[dict]:
    """切成"节"。节是阅读单位，段是练习单位。

    规则（都是规模与换行的事实，没有语义判断）：
      1. 空行分段：连续两个以上换行才算一个段落边界。单换行留在正文里，
         切段时当软边界用——所以原文一个字都不会丢。
      2. 标题会并进它下面的正文，绝不挂到上一节末尾。
      3. merge_small=True 时把小段并成接近 target 的节，适合目录太长的情况；
         默认不并——"按段落分节"才是读书时最自然的样子，而且切段本来就
         会把相邻的短段合并，不需要在节这一层再并一次。
      4. "按段拼回去等于原文"这条不变式在 tests/test_store.py 里有断言。
    """
    text = (text or '').replace('\r\n', '\n').replace('\r', '\n')
    first = len(text) - len(text.lstrip())
    last = len(text.rstrip())
    text = text[first:last]          # 掐掉整体首尾空白，保证拼回去精确等于原文
    if not text.strip():
        return []

    paras = _split_regions(text)
    if not paras:
        return []

    # 归并（累加器式）：
    #   · 遇到标题 → 当前节收尾，从标题重新开始。标题因此永远跟着下面的正文。
    #   · merge_small 时，当前节还不够大（< 六成 target）就继续往里加。
    # 全程只记位置，空行原样保留，所以切分是可逆的。
    floor = max(60, int(target * 0.6))
    merged: list[list[int]] = []
    for (s, e, raw) in paras:
        is_title = _looks_like_title(raw)
        if merged and not is_title:
            cur_body = text[merged[-1][0]:merged[-1][1]]
            if _looks_like_title(cur_body) or (merge_small and plain_len(cur_body) < floor):
                merged[-1][1] = e
                continue
        merged.append([s, e])

    # 末尾孤块并进上一块。门槛保守：只有"很短、而且根本没成句"的尾巴才并，
    # 那多半是版面残留；已经成句的末节哪怕短，也是完整的一节（宁短勿吞）。
    if merge_small and len(merged) > 1:
        last_body = text[merged[-1][0]:merged[-1][1]]
        tail_floor = max(20, int(target * 0.15))
        if (not _looks_like_title(last_body)
                and plain_len(last_body) < tail_floor
                and last_body.strip()[-1:] not in '。！？'):
            merged[-2][1] = merged[-1][1]
            merged.pop()

    chapters = []
    i = 0
    for (s, e) in merged:
        while s < e and text[s] in ' \t\n':
            s += 1
        while e > s and text[e - 1] in ' \t\n':
            e -= 1
        body = text[s:e]
        i += 1
        chapters.append({'no': i, 'title': _chapter_title(body, i),
                         'chars': plain_len(body), 'body': body,
                         '_start': s, '_end': e})   # 内部用；入库时换成绝对位置
    return chapters


def _chapter_title(block: str, no: int) -> str:
    first = split_sentences(block)
    head = (first[0] if first else block).strip()
    head = re.sub(r'\s+', '', head)
    if len(head) > 18:
        head = head[:18] + '…'
    return head or ('第 %d 节' % no)


def _split_long_run(body: str, s: int, e: int, target: int, hard: int) -> list[tuple[int, int]]:
    """一段里有一句长得离谱（网页复制来的整段常常没有句读），在它内部切开。

    先在逗号、分号这类顿挫上切；一个顿挫都没有（整块汉字），
    只能按字数硬切——硬切出来的片段不好看，但总比让你一次背 2000 字强。
    """
    seg = body[s:e]
    soft = '，、；：,;'
    out = []
    cur_s, cur_n = 0, 0
    for m in re.finditer(r'[^%s]*[%s]?' % (re.escape(soft), re.escape(soft)), seg):
        piece = m.group()
        if not piece:
            continue
        cur_n += plain_len(piece)
        if cur_n >= target:
            out.append((s + cur_s, s + m.end()))
            cur_s, cur_n = m.end(), 0
    if cur_s < len(seg):
        tail = (s + cur_s, s + len(seg))
        if out and plain_len(body[tail[0]:tail[1]]) < target * 0.3:
            out[-1] = (out[-1][0], tail[1])      # 尾巴太短，并进前一片
        else:
            out.append(tail)

    # 硬切兜底：还有超长的就按字数切开
    final = []
    for (a, b) in out:
        while plain_len(body[a:b]) > hard:
            cut = a
            n = 0
            while cut < b and n < target:
                if body[cut] not in ' \t\n':
                    n += 1
                cut += 1
            if cut <= a:
                break
            final.append((a, cut))
            a = cut
        if b > a:
            final.append((a, b))
    return final


def split_passages(chapter_body: str, target: int = DEFAULT_PASSAGE_CHARS,
                   base: int = 0) -> list[dict]:
    """把一节切成段。段就是一次练习的量。

    一条铁律：**切口只能落在句子末尾**。半句话拿去练记忆没有意义，
    而且对照的时候看不出"我漏了哪句"。

    做法分三层：
      1. 先按空行切成"块"——空行是作者自己划的段落边界，比字数更可信。
      2. 块内按句子累加到 target 字就断。
      3. 一个块明显长于 target（电子书常见：一整节就是一大段）就在块内
         按句子再切；一个块太短就跟相邻的块合并。

    base 是这一节在整篇原文里的起点。加上它之后，段的 start/end 就是绝对位置，
    取原文时直接 text[start:end] 即可。
    """
    target = max(80, min(2000, int(target or DEFAULT_PASSAGE_CHARS)))
    body = chapter_body

    # ① 按空行切块（保留原始偏移）
    blocks = []
    for m in re.finditer(r'[^\n]+(?:\n(?![ \t]*\n)[^\n]+)*', body):
        if m.group().strip():
            blocks.append((m.start(), m.end()))
    if not blocks:
        if not body.strip():
            return []
        blocks = [(0, len(body))]

    # ② 块内切到不超过 target。
    #
    # 顺序很重要，而且**必须有最后一道硬切兜底**：
    #   1) 优先切在句末——半句话拿去练记忆没有意义；
    #   2) 一句就超过整段额度时（网页复制来的长文常常整段没有句读），
    #      在这一句内部按标点切；
    #   3) 连标点都没有（一整块汉字），只能按字数硬切。
    #
    # 少了第 2、3 步会出一个很难发现的 bug：粘 2000 字没有句读的内容进去，
    # 整块被当成"一段"，练一次要背 2000 字。实测复现过。
    hard = int(target * 1.3)
    raw_pieces: list[list[int]] = []
    for (bs, be) in blocks:
        seg = body[bs:be]
        if plain_len(seg) <= hard:
            raw_pieces.append([bs, be])
            continue
        cur_s, cur_n, off = 0, 0, 0

        def flush(a, b):
            """把 [a,b) 收成一段。若它自己还是超长（一大块没有句读），
            就在标点上切、再不行按字数切。"""
            if plain_len(body[a:b]) <= hard:
                raw_pieces.append([a, b])
                return
            for piece in _split_long_run(body, a, b, target, hard):
                raw_pieces.append([piece[0], piece[1]])

        for sent in split_sentences(seg):
            s_len = plain_len(sent)
            s_start, s_end = bs + off, bs + off + len(sent)
            off += len(sent)
            if cur_n == 0 and s_len >= hard:
                # 这一句自己就超了，而且当前没攒东西 → 直接切它
                flush(s_start, s_end)
                cur_s = off
                continue
            cur_n += s_len
            if cur_n >= target:
                flush(bs + cur_s, s_end)
                cur_s, cur_n = off, 0
        if cur_s < len(seg):
            flush(bs + cur_s, bs + len(seg))

    # ③ 累加到接近 target 就断。
    # 关键：段落边界不是硬边界——一整节就是一大段时，②已经在句末切好了；
    # 反过来，短的一块（节标题、一句收尾）要跟相邻的并成一段，
    # 否则会出现"6 个字的练习段"，而且标题会和它的正文被人为拆开。
    # 判据是"并进来会不会明显超过 target"，而不是"这块短不短"。
    limit = int(target * 1.3)
    merged: list[list[int]] = []
    for pc in raw_pieces:
        if not merged:
            merged.append(list(pc))
            continue
        cand = plain_len(body[merged[-1][0]:pc[1]])
        if cand <= limit:
            merged[-1][1] = pc[1]
        else:
            merged.append(list(pc))

    # 收尾：去掉首尾空白，保证边界落在实字上
    out = []
    for (s, e) in merged:
        while s < e and body[s] in ' \t\n':
            s += 1
        while e > s and body[e - 1] in ' \t\n':
            e -= 1
        if e - s <= 0:
            continue
        out.append({'no': len(out) + 1, 'start': s + base, 'end': e + base,
                    'chars': plain_len(body[s:e])})
    return out


def normalize_text(text: str) -> str:
    return (text or '').replace('\r\n', '\n').replace('\r', '\n').strip()


def text_fingerprint(text: str) -> str:
    return hashlib.md5(normalize_text(text).encode('utf-8')).hexdigest()[:10]
