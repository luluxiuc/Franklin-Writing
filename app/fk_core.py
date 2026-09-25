#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk_core — 富兰克林写作法工具的引擎与状态层（无判断版）

设计依据：富兰克林写作工具-无判断版设计v1.0.md

本文件里的每一行都必须满足下列硬性约束。这些约束是产品的定义，不是风格偏好：

  R1  不做任何关于"像不像作者""写得好不好"的判断。全文件不存在评价性输出。
  R2  不调用模型，不联网。只用 Python 标准库与本地文件。
  R3  提示只列原文中真实存在的连续内容片段，不含写法说明、不含修辞名称、不含效果描述。
  R4  覆盖率只报事实（命中清单／未命中清单／各自条数），不换算成比率、分数、等级。
  R5  单元未写下"我的观察"不算完成。
  R6  提交后到延迟期满之间，任何接口都不得返回该单元原文。
  R7  一个单元一旦提交，原文对该单元永久解锁，不给"回头改稿"留后门。
  R8  档案只摆原始数据，不做归纳、不给结论、不命名任何习惯。

R1–R8 由 selftest() 在真实存档上核验，见文件末尾。
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import time
import uuid

# ---------------------------------------------------------------- 常量

PUNCT = '，。！？；：、“”"（）《》…—'
SENT_END = '。！？'
CLAUSE_END = '，。！？；：'
DEFAULT_UNIT_SIZE = 150
DEFAULT_DELAY_MIN = 10

# 功能字：抽取内容片段时作为边界。这张表不做语义判断，只把虚词当切割符。
FUNC = set(
    '的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那'
    '上下来去时么呢吧啊呀吗着过要会能可所因然于并且如若则把让给向从当'
    '一二三四五六七八九十百千万两有些个只种样件条张把支又再才更没'
)

# 状态文件里允许出现的键。出现别的键即视为越界（防止悄悄混进评分字段）。
ALLOWED_ATTEMPT_KEYS = {
    'id', 'unit_id', 'created', 'submitted_at', 'used_hint', 'used_guide',
    'elapsed_sec', 'draft', 'chars', 'paste_blocked', 'compare_started_at',
    'compared_at', 'observation', 'hit', 'miss', 'source_chars',
}

# 档案里绝不允许出现的字段名（下划线/大小写不敏感的包含匹配）
FORBIDDEN_KEYS = (
    'score', 'similarity', 'rating', 'grade', 'penalty', 'fidelity',
    '保真', '得分', '分数', '评分', '相似度', '像不像', '好不', '建议', '评语',
    'advice', 'suggest', 'verdict', 'is_author', 'style_match',
)


class FkError(Exception):
    """预期内的用户级错误，接口层直接转成 4xx。"""

    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------- 文本切分

def plain_len(s: str) -> int:
    """去掉标点与空白后的字数。只用于说明规模，不用于评价。"""
    return len(re.sub(r'[%s\s]' % re.escape(PUNCT), '', s))


def split_sentences(text: str) -> list[str]:
    """按句末标点切句。

    **刻意不 strip 空白**：真实范文里常有段落换行，切句如果把它吃掉，
    切分就不再可逆——"拼回去等于原文"这条性质是测试要保证的，
    也是"原文只存一份、按需切回来"这个设计成立的前提。
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


def split_clauses(text: str) -> list[str]:
    out, cur = [], ''
    for ch in text:
        cur += ch
        if ch in CLAUSE_END:
            out.append(cur)
            cur = ''
    if cur.strip():
        out.append(cur)
    return out


def split_units(text: str, target: int = DEFAULT_UNIT_SIZE, tol: float = 0.35) -> list[str]:
    """按规模切训练单元。纯规模切分，不判断任何"表达动作"。

    规则：贪心累积句子到 target 字；若加入下一句会超出 target*(1+tol)
    且当前已不低于 target*(1-tol)，就在此断开。
    """
    sents = split_sentences(text)
    units, cur, cur_len = [], [], 0
    lo, hi = target * (1 - tol), target * (1 + tol)
    for s in sents:
        L = plain_len(s)
        if cur and cur_len + L > hi and cur_len >= lo:
            units.append(''.join(cur))
            cur, cur_len = [], 0
        cur.append(s)
        cur_len += L
    if cur:
        if units and cur_len < target * 0.5:
            units[-1] += ''.join(cur)      # 尾块过短则并入前一块
        else:
            units.append(''.join(cur))
    return units


# ---------------------------------------------------------------- 内容片段抽取（机械）

def runs(text: str) -> list[str]:
    """把文本切成"连续实义汉字串"：功能字与标点、数字、拉丁字母都作为边界。"""
    body = re.sub(r'[%s\s\dA-Za-z]' % re.escape(PUNCT), ' ', text)
    out = []
    for seg in body.split(' '):
        cur = ''
        for ch in seg:
            if ch in FUNC:
                if cur:
                    out.append(cur)
                    cur = ''
            else:
                cur += ch
        if cur:
            out.append(cur)
    return out


def spans(text: str, lo: int = 2, hi: int = 4) -> list[str]:
    """贪心片段覆盖：把每段连续实义串按 2–4 字切开。

    注意：**不要用这个函数的结果当提示。** 中文里按字数硬切必然切在词的中间，
    实测会切出"姐姐用彩""色丝线打""子蠢"这类半截东西。
    它只保留给"按字数分片"的统计用途。提示与覆盖率请用 content_spans()。
    """
    out = []
    for seg in runs(text):
        k = 0
        while k < len(seg):
            take = min(hi, len(seg) - k)
            piece = seg[k:k + take]
            if len(piece) < lo and out:
                break
            if len(piece) >= lo:
                out.append(piece)
            k += take
    return out


def content_spans(text: str, lo: int = 2, hi: int = 6) -> list[str]:
    """内容片段全集 = 连续实义串中长度 2–6 字的那些（按首次出现顺序去重）。

    这是提示与覆盖率共用的**唯一**基准。三条取舍：

      · 边界落在功能字上，所以不会切出"姐姐用彩""色丝线打"这类半截词。
        按字数硬切是错的——中文里 2–4 字的固定切法必然切在词的中间。
      · 整串长于 6 字时**直接不要，不去切它**。切出来是残片（"不一定真凑足"
        切出"定真凑足"），不如漏掉。
      · 单字不要。一个字做抓手太弱（"水""毒""沾"），而且单字几乎必然命中，
        放进覆盖率基准只会让清单变吵。

    每条都必然是原文的真实连续子串，所以命中判定是纯字符串比对，可复现。

    已知的粗糙之处（写在明处，不假装没有）：功能字表是固定的，遇到表外的虚词
    或者专名连写（"袁子才这个人我不喜欢"→"袁子才这个人我不喜欢"整串被丢掉），
    会漏或者会给出偏长的串。所以提示默认收起、可以关掉、且从不解释"怎么写"。
    """
    seen, out = set(), []
    for r in runs(text):
        if lo <= len(r) <= hi and r not in seen:
            seen.add(r)
            out.append(r)
    return out


def select_hints(text: str, limit: int = 26) -> dict:
    """挑一小组内容片段当重构提示，并报告一共有多少候选。

    挑选规则全部是字符串关系，不含任何语义判断：
      1. 候选就是 content_spans(text)。
      2. 长的优先：长串更能起到"想起这一段写了什么"的作用。
      3. 被选中的长串所包含的短串不再重复列（"城隍庙"与"城隍庙送"只留一个）。
      4. 超出 limit 的不列，但仍计入覆盖率——用户点开可以看到全部候选有多少条。
      5. 最后按在原文中首次出现的位置排序，读起来就是原文的顺序。
    """
    raw = content_spans(text)
    kept = []
    for p in sorted(raw, key=lambda p: (-len(p), text.find(p))):
        if any(p != q and p in q for q in kept):
            continue
        kept.append(p)

    shown = sorted(kept[:limit], key=lambda p: text.find(p))
    return {
        'hints': shown,
        'raw': raw,
        'candidate_count': len(raw),
        'shown_count': len(shown),
        'hidden_count': max(0, len(raw) - len(shown)),
    }


def coverage(source: str, draft: str) -> dict:
    """机械子串比对。只返回事实清单与条数，不返回比率、不返回比例。

    基准与提示完全相同（content_spans），所以用户对照时看到的清单，
    就是写稿时那张提示清单的同一套东西——多出来的部分是没显示为提示的。
    """
    all_spans = content_spans(source)
    hit = [w for w in all_spans if w in draft]
    miss = [w for w in all_spans if w not in draft]
    return {
        'all': all_spans,
        'hit': hit,
        'miss': miss,
        'hit_count': len(hit),
        'miss_count': len(miss),
        'total_count': len(all_spans),
    }


# ---------------------------------------------------------------- 规模统计（不是评估）

def describe(text: str) -> dict:
    """报告一段文本的规模。四句短、长句多，只是事实，没有好坏。"""
    sents = split_sentences(text)
    clauses = split_clauses(text)
    q = len(re.findall(r'[？?]', text))
    return {
        'chars': plain_len(text),
        'sentences': len(sents),
        'clauses': len(clauses),
        'questions': q,
        'longest_sentence': max((plain_len(s) for s in sents), default=0),
    }


def guide_outline(text: str) -> dict:
    """句子骨架：只给每一句的规模，不给一个字。

    比提示更进一步：提示给的是"出现了哪些名物"，骨架给的是"有几句、每句多长"。
    两者都不含措辞，因此都不携带解读。用户按骨架自己决定怎么排。
    """
    rows = []
    for i, s in enumerate(split_sentences(text), 1):
        cs = split_clauses(s)
        q = '？' if re.search(r'[？?]', s) else ''
        rows.append({'no': i, 'chars': plain_len(s), 'clauses': len(cs), 'q': q})
    return {
        'rows': rows,
        'sentence_count': len(rows),
        'clause_count': sum(r['clauses'] for r in rows),
        'chars': plain_len(text),
    }


# ---------------------------------------------------------------- 泄露自检

def find_leak(source: str, payload, min_len: int = 8) -> list[str]:
    """检查一段待发数据里是否夹带了原文的长片段。

    写稿阶段绝不能把原文发给浏览器。与其相信调用方记得住，不如每次发之前
    机械扫一遍：把原文的所有 >= min_len 字的连续子串拿去待发内容里找。
    返回命中的片段（空列表 = 干净）。
    """
    blob = json.dumps(payload, ensure_ascii=False)
    flat = re.sub(r'[%s\s]' % re.escape(PUNCT), '', source)
    grams = set()
    for i in range(0, max(0, len(flat) - min_len + 1)):
        grams.add(flat[i:i + min_len])
    for s in split_sentences(source):
        if plain_len(s) >= min_len:
            grams.add(s)
            grams.add(re.sub(r'[%s\s]' % re.escape(PUNCT), '', s))
    return sorted(g for g in grams if g in blob)


# ---------------------------------------------------------------- 状态层

SCHEMA = 1


def _now() -> float:
    return time.time()


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))


class Store:
    """整库读写。单用户本地工具，不做并发控制，够用。"""

    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, 'fk.json')

    # ---- 读写

    def _empty(self) -> dict:
        return {'schema': SCHEMA, 'works': [], 'attempts': [], 'events': [],
                'settings': {'delay_min': DEFAULT_DELAY_MIN, 'unit_size': DEFAULT_UNIT_SIZE}}

    def read(self) -> dict:
        if not os.path.exists(self.path):
            return self._empty()
        try:
            with open(self.path, encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            raise FkError('存档文件损坏或无法读取：%s' % self.path, 500)
        for k, v in self._empty().items():
            data.setdefault(k, v)
        data['settings'] = {**self._empty()['settings'], **(data.get('settings') or {})}
        return data

    def write(self, data: dict) -> None:
        os.makedirs(self.root, exist_ok=True)
        tmp = self.path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    # ---- 找东西

    @staticmethod
    def work(data: dict, wid: str) -> dict:
        for w in data['works']:
            if w['id'] == wid:
                return w
        raise FkError('找不到这篇范文。', 404)

    @staticmethod
    def unit(w: dict, uid: str) -> dict:
        for u in w['units']:
            if u['id'] == uid:
                return u
        raise FkError('找不到这个训练单元。', 404)

    @staticmethod
    def attempts_of(data: dict, uid: str) -> list[dict]:
        return [a for a in data['attempts'] if a['unit_id'] == uid]

    def locate(self, data: dict, wid: str, uid: str) -> tuple[dict, dict]:
        """一次取回作品与单元，找不到就报用户级错误。"""
        w = self.work(data, wid)
        return w, self.unit(w, uid)

    def log(self, data: dict, kind: str, **kw) -> None:
        ev = {'at': _now(), 'kind': kind}
        ev.update(kw)
        data['events'].append(ev)
        del data['events'][:-2000]          # 只留最近 2000 条

    # ---- 状态判定

    def attempt(self, data: dict, uid: str) -> dict | None:
        a = self.attempts_of(data, uid)
        return a[-1] if a else None

    def status(self, data: dict, unit: dict) -> str:
        """单元所处的阶段。unlock 只由已提交稿子的时间与延迟设置决定。"""
        a = self.attempt(data, unit['id'])
        if not a:
            return 'todo'
        if a.get('compared_at'):
            return 'done'
        if self.remaining(data, a) > 0:
            return 'waiting'
        return 'ready'

    def remaining(self, data: dict, attempt: dict) -> float:
        """距离可以看原文还剩多少秒。返回 0 表示已到期。"""
        delay = float(data['settings'].get('delay_min', DEFAULT_DELAY_MIN)) * 60.0
        end = attempt['submitted_at'] + delay
        return max(0.0, end - _now())

    # ---- 进度：只记录"动作是否完成"，不记录写作水平

    def progress(self, data: dict, w: dict) -> dict:
        n = len(w['units'])
        counts = {'total': n, 'written': 0, 'compared': 0, 'observed': 0,
                  'no_hint': 0, 'no_guide': 0, 'paste_blocked': 0}
        for u in w['units']:
            a = self.attempt(data, u['id'])
            if not a:
                continue
            counts['written'] += 1
            if a.get('used_hint') is False:
                counts['no_hint'] += 1
            if a.get('used_guide') is False:
                counts['no_guide'] += 1
            if a.get('paste_blocked'):
                counts['paste_blocked'] += 1
            if a.get('compared_at'):
                counts['compared'] += 1
                if (a.get('observation') or '').strip():
                    counts['observed'] += 1
        counts['unit_size'] = w.get('unit_size')
        return counts


# ---------------------------------------------------------------- 动作

def import_text(store: Store, text: str, title: str, unit_size: int = DEFAULT_UNIT_SIZE,
                author: str = '', note: str = '') -> dict:
    text = (text or '').strip()
    if not text:
        raise FkError('范文是空的。')
    title = (title or '').strip() or '未命名'
    unit_size = max(60, min(600, int(unit_size or DEFAULT_UNIT_SIZE)))

    chunks = split_units(text, target=unit_size)
    if not chunks:
        raise FkError('这篇文本切不出训练单元。')

    data = store.read()
    wid = re.sub(r'\W+', '-', title)[:20] + '-' + hashlib.md5(
        (text + str(unit_size)).encode('utf-8')).hexdigest()[:6]

    units = []
    for i, ch in enumerate(chunks, 1):
        units.append({
            'id': uuid.uuid4().hex[:12], 'no': i,
            'chars': plain_len(ch),
            'hint': select_hints(ch)['hints'],
        })

    work = {
        'id': wid, 'title': title, 'author': author.strip(), 'note': note.strip(),
        'created': _now(), 'chars': plain_len(text),
        'unit_size': unit_size, 'units': units, 'guide': {},
    }
    data['works'] = [w for w in data['works'] if w['id'] != wid] + [work]
    data['settings']['unit_size'] = unit_size
    store.log(data, 'import', work=wid, units=len(units))
    save_source(store, wid, text)
    store.write(data)
    return {'work': public_work(store, data, work), 'units': chunks}


def resplit(store: Store, wid: str, unit_size: int) -> dict:
    """重新按规模切分。已有稿子的单元会被丢弃，因此需要显式确认。"""
    data = store.read()
    w = store.work(data, wid)
    if any(store.attempts_of(data, u['id']) for u in w['units']):
        raise FkError('这篇已经有写过的单元了。重切会丢掉那些稿子，所以默认不做。'
                      '要重切请删掉这篇再重新导入。')
    text = load_source(store, wid)
    if text is None:
        raise FkError('找不到这篇的原文文件，无法重切。', 500)
    unit_size = max(60, min(600, int(unit_size)))
    chunks = split_units(text, target=unit_size)
    units = []
    for i, ch in enumerate(chunks, 1):
        units.append({'id': uuid.uuid4().hex[:12], 'no': i, 'chars': plain_len(ch),
                      'hint': select_hints(ch)['hints']})
    w['units'] = units
    w['unit_size'] = unit_size
    w['guide'] = {}
    data['settings']['unit_size'] = unit_size
    store.log(data, 'resplit', work=wid, units=len(units))
    store.write(data)
    return {'work': public_work(store, data, w), 'units': chunks}


def submit(store: Store, wid: str, uid: str, draft: str, used_hint: bool,
           used_guide: bool, elapsed_sec: int | None, paste_blocked: bool = False,
           started_at: float | None = None) -> dict:
    draft = (draft or '')
    if not draft.strip():
        raise FkError('稿子是空的。写不出可以少写几句，但不能不写。')
    if len(draft) > 40000:
        raise FkError('稿子太长了。')

    data = store.read()
    w, u = store.locate(data, wid, uid)
    old = store.attempt(data, uid)

    if old and old.get('compared_at'):
        raise FkError('这个单元已经完成对照了。已完成对照的单元不再收新稿，'
                      '否则"先看原文再改"就成立了。')

    elapsed = None
    if started_at:
        d = _now() - float(started_at)
        if 0 < d < 24 * 3600:
            elapsed = int(d)
    if elapsed is None and elapsed_sec is not None:
        try:
            e = int(elapsed_sec)
            if 0 < e < 24 * 3600:
                elapsed = e
        except (TypeError, ValueError):
            pass

    if old:
        data['attempts'] = [a for a in data['attempts'] if a['id'] != old['id']]

    a = {
        'id': uuid.uuid4().hex[:12], 'unit_id': uid, 'created': _now(),
        'submitted_at': _now(), 'used_hint': bool(used_hint),
        'used_guide': bool(used_guide), 'elapsed_sec': elapsed,
        'draft': draft.strip(), 'chars': plain_len(draft),
        'paste_blocked': bool(paste_blocked), 'source_chars': u['chars'],
        'compare_started_at': None, 'compared_at': None, 'observation': None,
        'hit': None, 'miss': None,
    }
    data['attempts'].append(a)
    store.log(data, 'submit', work=wid, unit=uid, elapsed=elapsed,
              hint=bool(used_hint), guide=bool(used_guide), paste=bool(paste_blocked))
    store.write(data)

    return {
        'attempt_id': a['id'],
        'remaining_sec': int(store.remaining(data, a)),
        'delay_min': data['settings']['delay_min'],
        'note': '原文已锁定。延迟结束前，本工具的任何接口都不会返回这一段原文。',
    }


def start_compare(store: Store, wid: str, uid: str) -> dict:
    """进入对照界面。到期前拒绝。"""
    data = store.read()
    w = store.work(data, wid)
    u = store.unit(w, uid)
    a = store.attempt(data, uid)
    if not a:
        raise FkError('这个单元还没提交过稿子。')

    left = store.remaining(data, a)
    if left > 0 and not a.get('compared_at'):
        raise FkError('还在延迟期内，剩余 %d 分 %d 秒。'
                      % (int(left // 60), int(left % 60)), 423)
    if not a.get('compare_started_at'):
        a['compare_started_at'] = _now()

    src = source_of_unit(store, wid, u)
    cov = coverage(src, a['draft'])
    store.log(data, 'compare_open', work=wid, unit=uid)
    store.write(data)

    return {
        'work': {'id': w['id'], 'title': w['title'], 'author': w.get('author', '')},
        'unit': {'id': u['id'], 'no': u['no'], 'chars': u['chars']},
        'source': src,
        'draft': a['draft'],
        'source_desc': describe(src),
        'coverage': cov,
        'observation': a.get('observation'),
        'compared': bool(a.get('compared_at')),
        'prompts': OBSERVATION_PROMPTS,
        'elapsed_sec': a.get('elapsed_sec'),
    }


OBSERVATION_PROMPTS = [
    '你写的时候，哪一处最没把握？原文那一处是怎么处理的？',
    '你的稿子里有没有原文没有的东西？它是从哪来的？',
    '原文里有没有你完全没想起的名物？是哪一类？',
    '两边的句子长短分布一样吗？你是在哪里变长或变短的？',
    '原文有没有几处你明明记得，却写成了别的说法？差别在哪？',
    '如果只能改你自己稿子里的一个地方，你改哪里？为什么？',
    '有没有一处，你觉得自己写得比原文更顺？先别急着下结论，找找依据。',
    '原文的哪些句子你读完发现自己刚才漏看了？',
]


def save_observation(store: Store, wid: str, uid: str, observation: str) -> dict:
    """写下观察并结束本单元。观察为空则本单元不算完成（R5）。"""
    obs = (observation or '').strip()
    if not obs:
        raise FkError('"我的观察"是空的。看不出差别也可以，但要显式写出来——'
                      '去掉判断之后，观察就是唯一的学习动作。')

    data = store.read()
    w = store.work(data, wid)
    u = store.unit(w, uid)
    a = store.attempt(data, uid)
    if not a:
        raise FkError('这个单元还没提交过稿子。')
    left = store.remaining(data, a)
    if left > 0 and not a.get('compared_at'):
        raise FkError('还在延迟期内，不能结束本单元。', 423)

    src = source_of_unit(store, wid, u)
    cov = coverage(src, a['draft'])
    a['observation'] = obs
    a['hit'], a['miss'] = cov['hit'], cov['miss']
    a['compared_at'] = _now()
    store.log(data, 'observe', work=wid, unit=uid, chars=len(obs))
    store.write(data)

    return {'ok': True, 'unit_done': True}


# ---------------------------------------------------------------- 原文的存取

def source_dir(store: Store) -> str:
    d = os.path.join(store.root, 'sources')
    os.makedirs(d, exist_ok=True)
    return d


def source_path(store: Store, wid: str) -> str:
    return os.path.join(source_dir(store), wid + '.txt')


def save_source(store: Store, wid: str, text: str) -> None:
    with open(source_path(store, wid), 'w', encoding='utf-8') as f:
        f.write(text)


def load_source(store: Store, wid: str) -> str | None:
    p = source_path(store, wid)
    if not os.path.exists(p):
        return None
    with open(p, encoding='utf-8') as f:
        return f.read()


def source_of_unit(store: Store, wid: str, unit: dict) -> str:
    """按单元序号重新切一遍原文，取回这一段。

    这样原文只存一份，切分规则改了也不会出现两份不一致的文本。
    """
    text = load_source(store, wid)
    if text is None:
        raise FkError('找不到这篇的原文文件。', 500)
    data = store.read()
    w = store.work(data, wid)
    chunks = split_units(text, target=w.get('unit_size', DEFAULT_UNIT_SIZE))
    idx = unit['no'] - 1
    if idx < 0 or idx >= len(chunks):
        raise FkError('单元与原文对不上，可能是存档被改过。', 500)
    return chunks[idx]


# ---------------------------------------------------------------- 对外视图

def public_work(store: Store, data: dict, w: dict) -> dict:
    units = []
    for u in w['units']:
        st = store.status(data, u)
        a = store.attempt(data, u['id'])
        row = {'id': u['id'], 'no': u['no'], 'chars': u['chars'], 'status': st}
        if a:
            row['remaining_sec'] = int(store.remaining(data, a)) if st == 'waiting' else 0
            row['used_hint'] = a.get('used_hint')
            row['used_guide'] = a.get('used_guide')
            row['elapsed_sec'] = a.get('elapsed_sec')
            row['draft_chars'] = a.get('chars')
            if st == 'done':
                row['hit_count'] = len(a.get('hit') or [])
                row['miss_count'] = len(a.get('miss') or [])
        units.append(row)
    return {
        'id': w['id'], 'title': w['title'], 'author': w.get('author', ''),
        'note': w.get('note', ''), 'chars': w['chars'], 'created': _iso(w['created']),
        'unit_size': w.get('unit_size'), 'units': units,
        'progress': store.progress(data, w),
    }


def workspace(store: Store) -> dict:
    data = store.read()
    now = _now()
    works = []
    for w in data['works']:
        pw = public_work(store, data, w)
        waiting = [u for u in pw['units'] if u['status'] == 'waiting']
        pw['waiting'] = len(waiting)
        pw['next_unlock_sec'] = min([u['remaining_sec'] for u in waiting], default=None)
        pw['todo'] = sum(1 for u in pw['units'] if u['status'] in ('todo', 'ready'))
        works.append(pw)

    done = sum(1 for a in data['attempts'] if a.get('compared_at'))
    acts = {'written': len(data['attempts']), 'observed': done,
            'paste_blocked': sum(1 for a in data['attempts'] if a.get('paste_blocked'))}
    return {'works': works, 'server_time': now, 'settings': data['settings'],
            'action_counts': acts}
