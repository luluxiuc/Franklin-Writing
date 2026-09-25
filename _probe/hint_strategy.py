#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比几种提示挑选策略在真实段落上的产出。看的是"这清单能不能当重构的抓手"。"""
import os
import re
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
import fk_core as C

CORPUS = os.path.join(HERE, 'corpus', 'wang-zengqi-duanwu.txt')


def strategy_A(text, limit):
    """现状：频次>=2 + 被更长的候选吃掉。"""
    return C.select_hints(text, limit)['hints']


def strategy_B(text, limit):
    """去掉频次门槛，长串优先，子串被更长的候选吃掉。"""
    raw = C.content_spans(text)
    order = sorted(range(len(raw)), key=lambda i: (-len(raw[i]), i))
    picked, taken = [], []
    for i in order:
        p = raw[i]
        if any(p != q and p in q for q in taken):
            continue
        taken.append(p)
        picked.append(p)
    picked = sorted(picked, key=lambda p: text.find(p))
    return picked[:limit]


def strategy_C(text, limit):
    """频次>=2 只用来排序，不用来过滤；长串优先。"""
    raw = C.content_spans(text)
    freq = collections.Counter(C.spans(text))
    ranked = sorted(raw, key=lambda p: (-freq[p], -len(p), text.find(p)))
    picked, taken = [], []
    for p in ranked:
        if any(p != q and p in q for q in taken):
            continue
        taken.append(p)
        picked.append(p)
    picked = sorted(picked, key=lambda p: text.find(p))
    return picked[:limit]


def strategy_D(text, limit):
    """整段实义串（runs）当候选，不做 2–4 字切段。

    理由：切段切在哪里都是切在词的中间，中文里 2–4 字的固定切法必然产生
    "姐姐用彩""色丝线打"这类半截东西。整段实义串本身就是功能字划出的边界，
    至少保证切口落在虚词上，比按字数硬切合理。
    """
    rs = C.runs(text)
    cand = sorted(set(rs), key=lambda p: (-len(p), text.find(p)))
    return sorted(cand[:limit], key=lambda p: text.find(p))


def strategy_E(text, limit):
    """整段实义串 + 频次只用来排序（出现过的说法优先）。"""
    rs = C.runs(text)
    freq = collections.Counter(rs)
    cand = sorted(set(rs), key=lambda p: (-freq[p], -len(p), text.find(p)))
    return sorted(cand[:limit], key=lambda p: text.find(p))


def strategy_F(text, limit):
    """整段实义串 + 频次>=2 过滤（原来的门槛，但候选换成整串）。"""
    rs = C.runs(text)
    keep, seen = [], set()
    for r in rs:
        if rs.count(r) >= 2 and r not in seen:
            seen.add(r)
            keep.append(r)
    return sorted(keep, key=lambda p: text.find(p))[:limit]


def main():
    text = open(CORPUS, encoding='utf-8').read().strip()
    chunks = C.split_units(text, target=150)
    limit = 28
    for idx in (0, 1, 5):
        seg = chunks[idx]
        print('\n' + '#' * 74)
        print('# 第 %d 段（%d 字）' % (idx + 1, C.plain_len(seg)))
        print('#' * 74)
        print(seg[:74] + '…')
        for name, fn in (('A 现状（2–4字切段+频次门槛）', strategy_A),
                         ('C 2–4字切段+频次排序', strategy_C),
                         ('D 整段实义串，长串优先', strategy_D),
                         ('E 整段实义串+频次排序', strategy_E),
                         ('F 整段实义串+频次>=2', strategy_F)):
            got = fn(seg, limit)
            raw_n = len(C.content_spans(seg))
            cov = sum(1 for h in got if h in seg)
            print('\n%s  → %d 条（候选 %d 条，全部命中原文 %d）' % (name, len(got), raw_n, cov))
            for i in range(0, len(got), 9):
                print('   ' + '／'.join(got[i:i + 9]))
        print('\n原文原样（前两句）：')
        print('   ' + C.split_sentences(seg)[0])


if __name__ == '__main__':
    main()
