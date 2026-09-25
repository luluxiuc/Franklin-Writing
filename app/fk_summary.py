#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk_summary — 提示卡的缓存与批量生成。

设计目标就三条：**不重复花钱、不让你等、不假装知道花了多少**。

一、缓存
  · 键 = 原文哈希 + 模型名 + 提示词版本。
    同一段文字无论出现在哪本书、哪一节，只概括一次。
    同一段文字换模型会重新概括（不同模型的说法不一样，这是有意的）。
    提示词改版后旧缓存自动失效，不需要手工清。
  · 存在 data/summaries.json，纯文本，可以备份、可以删。
  · 删掉这个文件不会丢任何原文和稿子，只是下次要重新概括。

二、批量
  · 导入一本书之后可以在后台把整本书的提示卡先做好（"提前备好"）。
    这样练的时候不用等模型，因为答案早就在本地了。
  · 并发默认 2，可以通过环境变量 FK_LLM_CONCURRENCY 调。
    本地 Ollama 之类可以调到 4；免费额度小的接口建议保持 1。
  · 串行 + 每两条之间隔一小会儿（可关），避免触发限流。

三、token 账
  · 只记录服务商**真切报回来的** token 数（OpenAI 兼容接口都会给 usage）。
    拿不到就记 0，界面上说明"服务商没有回传"，不估算、不糊弄。
  · 估算函数只用来在**扣费之前**告诉你"大概要花多少"，并明确标注是估算。
"""
from __future__ import annotations

import json
import os
import threading
import time

import fk_llm as LLM

CACHE_NAME = 'summaries.json'
SCHEMA = 1
DEFAULT_CONCURRENCY = 2

# 汉字折算 token 的经验值。只用于"做之前先告诉你大概多少"，不用于记账。
CHARS_PER_TOKEN = 1.35
SYSTEM_TOKENS_EST = 220


def _est_tokens(text: str) -> int:
    return int(len(text or '') / CHARS_PER_TOKEN)


def text_key(text: str) -> str:
    """一段原文的稳定标识。只跟内容有关，跟它在哪本书里无关。"""
    import hashlib
    t = (text or '').strip()
    return hashlib.sha1(t.encode('utf-8')).hexdigest()[:20]


def cache_key(text: str, model: str) -> str:
    return '%s|%s|v%d' % (text_key(text), (model or '').strip(), LLM.PROMPT_VERSION)


def strip_echoes(hints: list[dict], source: str, min_run: int = 8) -> tuple[list[dict], list[dict]]:
    """把"照抄原文"的那几条提示摘出来，返回 (留下的, 摘掉的)。

    为什么必须摘掉：提示是拿来帮你想起来的，不是拿来抄的。模型偶尔会偷懒，
    直接把原文那一句搬进来——那一句你自己也想得起来，留着反而害你照着抄。

    判据是机械的：这一条里出现一段长度 >= min_run（8 字）的原文连续片段。
    8 字已经很宽松：正常转述（"系百索子、做香角子"这种列举事物）通常不会
    连续 8 字与原文逐字相同，而照搬一整个短句一定会超过。

    注意这里是**逐条**处理：一条照抄不该牵连其他条。摘掉的条不删，
    而是单独还回去——界面上要说清楚"这一句的提示被丢掉了，因为它在照抄"，
    比悄悄消失诚实。
    """
    if not source or not hints:
        return list(hints), []
    flat = _flat(source)
    keep, dropped = [], []
    for h in hints:
        f = _flat(h.get('hint', ''))
        echoed = False
        for i in range(0, max(0, len(f) - min_run + 1)):
            if f[i:i + min_run] in flat:
                echoed = True
                break
        (dropped if echoed else keep).append(h)
    return keep, dropped


def _flat(s: str) -> str:
    import re
    return re.sub(r'[，。！？；：、“”"（）《》…—\s]', '', s or '')


class SummaryCache:
    """线程安全的摘要缓存。后台批量生成是并发的，所以锁在这里。"""

    def __init__(self, root: str):
        self.path = os.path.join(root, CACHE_NAME)
        self._lock = threading.RLock()
        self._data = None

    # ── 读写

    def _load(self) -> dict:
        if self._data is not None:
            return self._data
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = None
        if not isinstance(self._data, dict):
            self._data = {'schema': SCHEMA, 'items': {}, 'stats': {}}
        self._data.setdefault('schema', SCHEMA)
        self._data.setdefault('items', {})
        self._data.setdefault('stats', {})
        for k, v in (('calls', 0), ('tokens_in', 0), ('tokens_out', 0),
                     ('hits', 0), ('misses', 0), ('seconds', 0.0)):
            self._data['stats'].setdefault(k, v)
        return self._data

    def _save(self) -> None:
        d = self._data
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    # ── 查询

    def get(self, text: str, model: str, count: bool = True) -> dict | None:
        """取缓存。

        count=False 用于"只是顺路看一眼"的场景（比如打开写稿页时把已有的提示卡
        一起带上），不计入命中率——否则统计会被页面浏览刷得没有意义。
        """
        with self._lock:
            d = self._load()
            item = d['items'].get(cache_key(text, model))
            if count:
                if item:
                    d['stats']['hits'] += 1
                else:
                    d['stats']['misses'] += 1
            return item

    def has(self, text: str, model: str) -> bool:
        with self._lock:
            return cache_key(text, model) in self._load()['items']

    def put(self, text: str, model: str, result: dict) -> dict:
        with self._lock:
            d = self._load()
            item = {
                'hints': result.get('hints', []),
                'sentences': result.get('sentences', []),
                'n_sent': result.get('n_sent', 0),
                'n_hint': result.get('n_hint', 0),
                'aligned': result.get('aligned', True),
                'dropped_echoes': result.get('dropped_echoes', []),
                'model': model,
                'at': result.get('at') or time.strftime('%Y-%m-%d %H:%M:%S'),
                'seconds': result.get('seconds'),
                'usage': result.get('usage'),
                'prompt_version': LLM.PROMPT_VERSION,
                'chars': len(text or ''),
            }
            d['items'][cache_key(text, model)] = item
            st = d['stats']
            st['calls'] += 1
            st['seconds'] = round(float(st.get('seconds') or 0)
                                  + float(result.get('seconds') or 0), 1)
            u = result.get('usage') or {}
            st['tokens_in'] += int(u.get('in') or 0)
            st['tokens_out'] += int(u.get('out') or 0)
            if u.get('in') is None and u.get('out') is None:
                st['calls_without_usage'] = st.get('calls_without_usage', 0) + 1
            self._save()
            return item

    def clear(self, model: str | None = None) -> dict:
        """清缓存。只清某个模型的，或者全清。"""
        with self._lock:
            d = self._load()
            if model:
                before = len(d['items'])
                d['items'] = {k: v for k, v in d['items'].items()
                              if v.get('model') != model}
                removed = before - len(d['items'])
            else:
                removed = len(d['items'])
                d['items'] = {}
            self._save()
            return {'removed': removed, 'left': len(d['items'])}

    def stats(self) -> dict:
        with self._lock:
            d = self._load()
            st = dict(d['stats'])
            st['cached'] = len(d['items'])
            st['chars_cached'] = sum(int(v.get('chars') or 0)
                                     for v in d['items'].values())
            st['file'] = self.path
            return st

    # ── 生成

    def ensure(self, text: str, settings: dict, force: bool = False) -> dict:
        """要一份逐句提示：有缓存就用缓存，没有才调模型。

        拿到结果先过"照抄检查"：哪一条在照搬原文就摘掉哪一条（逐条，不牵连）。
        全被摘光说明这次基本是在抄，重来一次（最多一次，不和模型的犟劲耗钱）。
        """
        model = (settings.get('model') or '').strip()
        if not force:
            hit = self.get(text, model)
            if hit:
                return {**hit, 'cached': True}

        out = LLM.hints_raw(settings, text)
        keep, dropped = strip_echoes(out.get('hints') or [], text)
        if dropped and not keep:
            out = LLM.hints_raw(settings, text)
            keep, dropped = strip_echoes(out.get('hints') or [], text)
        out['hints'] = keep
        out['dropped_echoes'] = dropped

        item = self.put(text, model, out)
        return {**item, 'cached': False, 'truncated': out.get('truncated', False),
                'dropped_echoes': dropped}

    # ── 估算：做之前先告诉你要花多少

    def estimate(self, passages: list[str], settings: dict) -> dict:
        """算这次要花多少。同一段文字出现多次只算一次——缓存就是按内容算键的。"""
        model = (settings.get('model') or '').strip()
        seen, uniq = set(), []
        for t in passages:
            k = text_key(t)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(t)
        todo, cached = [], 0
        for t in uniq:
            if self.has(t, model):
                cached += 1
            else:
                todo.append(t)

        def out_tokens(t: str) -> int:
            n = len(LLM.numbered_sentences(t))
            return int(n * LLM.per_hint_chars(n) / 1.35)     # 一句一条，单条有上限

        tin = sum(_est_tokens(t[:LLM.MAX_INPUT_CHARS]) + SYSTEM_TOKENS_EST for t in todo)
        tout = sum(out_tokens(t) for t in todo)
        return {
            'total': len(uniq),
            'duplicates': len(passages) - len(uniq),
            'cached': cached,
            'todo': len(todo),
            'est_tokens_in': tin,
            'est_tokens_out': tout,
            'est_tokens': tin + tout,
            'model': model,
            'note': '这是估算值（按汉字折算 token，再加系统提示的开销）。'
                    '真实用量以服务商返回的 usage 为准，生成之后会记在下面。',
        }


# ══════════════════════════════════════════════════════════════════
# 后台批量生成
# ══════════════════════════════════════════════════════════════════

class WarmJob:
    """把一本书的提示卡提前做好。可以取消，可以看进度。"""

    def __init__(self, book_id: str, book_title: str, total: int):
        self.book_id = book_id
        self.book_title = book_title
        self.total = total
        self.done = 0
        self.skipped = 0
        self.failed = 0
        self.errors: list[str] = []
        self.state = 'running'          # running | done | cancelled | error
        self.started = time.time()
        self.stop = threading.Event()
        self.last_error = ''

    def snapshot(self) -> dict:
        return {
            'book_id': self.book_id, 'book_title': self.book_title,
            'state': self.state, 'total': self.total,
            'done': self.done, 'skipped': self.skipped, 'failed': self.failed,
            'finished': self.done + self.skipped + self.failed,
            'elapsed': round(time.time() - self.started, 1),
            'last_error': self.last_error,
            'errors': self.errors[-3:],
        }


class Warmer:
    """管理后台批量任务。同一本书同时只跑一个。"""

    def __init__(self, data_dir: str, store_factory):
        self.data_dir = data_dir
        self.store_factory = store_factory     # () -> Store，线程各用各的
        self.cache = SummaryCache(data_dir)
        self._lock = threading.RLock()
        self._jobs: dict[str, WarmJob] = {}
        self._threads: dict[str, threading.Thread] = {}
        self.concurrency = max(1, int(os.environ.get('FK_LLM_CONCURRENCY',
                                                     DEFAULT_CONCURRENCY)))

    # ── 任务管理

    def status(self, book_id: str) -> dict | None:
        with self._lock:
            j = self._jobs.get(book_id)
            return j.snapshot() if j else None

    def cancel(self, book_id: str) -> dict:
        with self._lock:
            j = self._jobs.get(book_id)
        if not j:
            return {'ok': False, 'reason': '没有正在跑的任务'}
        j.stop.set()
        return {'ok': True}

    def start(self, book_id: str) -> dict:
        with self._lock:
            j = self._jobs.get(book_id)
            if j and j.state == 'running':
                return {'ok': True, 'already': True, 'job': j.snapshot()}
            store = self.store_factory()
            data = store.read()
            bk = store.book(data, book_id)
            texts = self._book_passages(store, data, bk)
            only_new = [t for t in texts
                        if not self.cache.has(t, data['settings'].get('model', ''))]
            job = WarmJob(book_id, bk['title'], len(texts))
            job.skipped = len(texts) - len(only_new)
            self._jobs[book_id] = job
            th = threading.Thread(target=self._run, args=(job, only_new),
                                  daemon=True, name='fk-warm-%s' % book_id)
            self._threads[book_id] = th
            th.start()
            return {'ok': True, 'job': job.snapshot()}

    @staticmethod
    def _book_passages(store, data, bk) -> list[str]:
        out = []
        for c in bk['chapters']:
            for p in c['passages']:
                t = store.passage_text(bk['id'], p)
                if t and len(t.strip()) >= 40:      # 太短的段不值得花 token
                    out.append(t)
        return out

    def _run(self, job: WarmJob, texts: list[str]) -> None:
        from concurrent.futures import ThreadPoolExecutor

        def why(e: Exception) -> str:
            """把异常说成人话。批量任务里最怕的就是只报一句 'error'，
            用户拿着它没法判断是 Key 错了、没钱了、还是被限流了。"""
            if isinstance(e, LLM.LlmError):
                return e.message + (('　' + e.hint) if e.hint else '')
            return '%s: %s' % (type(e).__name__, e)

        def one(t: str) -> bool:
            if job.stop.is_set():
                return False
            store = self.store_factory()            # 每个线程自己读设置
            settings = store.read()['settings']
            try:
                self.cache.ensure(t, settings)
                return True
            except Exception as e:
                job.last_error = why(e)
                job.errors.append(job.last_error)
                return False

        try:
            with ThreadPoolExecutor(max_workers=self.concurrency) as ex:
                for ok in ex.map(one, texts):
                    if job.stop.is_set():
                        continue        # 已经决定停下了，剩下的结果不再计入
                    if ok:
                        job.done += 1
                    else:
                        job.failed += 1
                    # 一条都没成功却已经错了 3 次，基本可以断定是配置或额度问题，
                    # 再打下去只是白费请求（还可能把账号打到限流）。
                    # 如果已经有成功的，说明接口是通的，就继续做完，不要因噎废食。
                    # 全书只有一两段时这个门槛够不着，所以补一条：全失败就算错。
                    if job.done == 0 and (job.failed >= 3
                                          or job.failed >= job.total):
                        job.state = 'error'
                        job.last_error = (job.last_error or '') + \
                            '　（一条都没成功，已停下。先检查 Key、余额和限流。）'
                        job.stop.set()
            if job.state == 'running':
                job.state = 'cancelled' if job.stop.is_set() else 'done'
        except Exception as e:
            job.state = 'error'
            job.last_error = why(e)
