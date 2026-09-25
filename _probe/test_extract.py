#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比两种机械抽取方案在真实语料上的表现。不做判断，只看"抽出来的东西像不像名物"。"""
import re, sys, os, collections

PUNCT = '，。！？；：、“”"（）《》…—'
FUNC = set('的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那'
           '上下来去时么呢吧啊呀吗着过要会能可所因然于并且如若则把让给向从当'
           '一二三四五六七八九十百千万两有些个只种样件条张把支')

def plain(t):
    return re.sub(r'[%s\s]' % re.escape(PUNCT), '', t)

def spans_old(text, lo=2, hi=4):
    body = re.sub(r'[%s\s\dA-Za-z]' % re.escape(PUNCT), ' ', text)
    out = []
    for seg in body.split(' '):
        i, n = 0, len(seg)
        while i < n:
            if seg[i] in FUNC:
                i += 1; continue
            j = i
            while j < n and seg[j] not in FUNC:
                j += 1
            run = seg[i:j]; k = 0
            while k < len(run):
                take = min(hi, len(run) - k)
                piece = run[k:k+take]
                if len(piece) < lo and out: break
                if len(piece) >= lo: out.append(piece)
                k += take
            i = j
    seen, res = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    return res

def runs(text):
    """连续实义汉字串（功能字为界），这是最自然的切分。"""
    body = re.sub(r'[%s\s\dA-Za-z]' % re.escape(PUNCT), ' ', text)
    res = []
    for seg in body.split(' '):
        cur = ''
        for ch in seg:
            if ch in FUNC:
                if cur: res.append(cur); cur = ''
            else:
                cur += ch
        if cur: res.append(cur)
    return res

def spans_new(text, min_count=2, lo=2, hi=6):
    """整串优先 + 频次过滤。只保留在全文出现>=min_count次的实义串。"""
    cnt = collections.Counter(runs(text))
    out, seen = [], set()
    for r in runs(text):
        if cnt[r] >= min_count and lo <= len(r) <= hi:
            if r not in seen:
                seen.add(r); out.append(r)
    return out

def report(name, items, source):
    print(f'\n=== {name} ===  {len(items)} 项')
    print('  ' + '　'.join(items[:40]))
    seg = [w for w in items if len(w) == 2]
    print(f'  二字项占比 {len(seg)}/{len(items)}')

if __name__ == '__main__':
    files = sys.argv[1:]
    if not files:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'corpus')
        files = [os.path.join(base, f) for f in os.listdir(base)]
    for f in files:
        text = open(f, encoding='utf-8').read().strip()
        print('#' * 70)
        print('#', os.path.basename(f), f'全文 {len(plain(text))} 字')
        # 用最小单元（约150字）来测，因为提示是按单元给的
        from importlib import util
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fk_tool'))
        import fk
        units = fk.split_units(text, target=150)
        for i, u in enumerate(units[:3], 1):
            print(f'\n--- 单元 {i}（{len(plain(u))} 字）---')
            print(u[:80].replace('\n', ' ') + ('…' if len(u) > 80 else ''))
            report('旧：切段 2-4 字', spans_old(u), u)
            for mc in (2, 3):
                report(f'新：整串+频次>={mc}', spans_new(u, min_count=mc), u)
