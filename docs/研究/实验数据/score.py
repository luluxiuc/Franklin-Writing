# -*- coding: utf-8 -*-
"""裁判结果打分。用法: python score.py judge1.json judge2.json ...
每个输入文件为裁判输出的 JSON 数组：[{no, verdict, confidence, reason, suspect_quote}, ...]
"""
import json, sys, os, io, glob
from collections import Counter, defaultdict
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:\ds harness\Fk-writing\_capability"
key = json.load(open(os.path.join(BASE, 'key.json'), encoding='utf-8'))
order = key['order']                 # 块号(1-based) -> 原始 id
A_ids = set(key['A_ids'])
B_meta = key['B']

# 每个植入缺陷所在的关键片段（用于 J5 缺陷定位判定）
DEFECT_QUOTE = {
    'B2':  ['所以邻里都信任他', '因为他说过'],
    'B4':  ['让我感到非常温暖', '最幸福的时光', '心里总是充满怀念'],
    'B6':  ['仿佛在诉说着什么', '汇成一片浑厚的轰鸣'],
    'B8':  ['心里感到一阵说不出的惆怅', '她的眼角有些湿润'],
    'B10': ['因为年代久远', '令人不禁生出几分敬畏', '仿佛那里面藏着另一个世界'],
}

files = sys.argv[1:]
if not files:
    files = sorted(glob.glob(os.path.join(BASE, 'judge*.json')))
judges = []
for f in files:
    try:
        data = json.load(open(f, encoding='utf-8'))
        judges.append((os.path.basename(f), {d['no']: d for d in data}))
    except Exception as e:
        print(f'!! 读取失败 {f}: {e}')

if not judges:
    print('没有可用的裁判结果'); sys.exit(1)

N = len(order)
print(f'裁判数 {len(judges)}   块数 {N}')
missing = [n for n in range(1, N + 1) if any(n not in j[1] for j in judges)]
if missing:
    print(f'!! 缺失块: {missing}')

# ---------- 逐块投票 ----------
votes = defaultdict(list)
detail = {}
for name, j in judges:
    for n in range(1, N + 1):
        if n in j:
            votes[n].append(j[n]['verdict'])

rows = []
for n in range(1, N + 1):
    orig = order[n - 1]
    v = votes[n]
    cnt = Counter(v)
    maj, majn = cnt.most_common(1)[0]
    truth = 'A' if orig in A_ids else 'B'
    rows.append(dict(no=n, orig=orig, truth=truth, votes=v, maj=maj,
                     majn=majn, agree=(majn > len(v) / 2), correct=(maj == truth)))

# ---------- 指标 ----------
J1 = sum(1 for r in rows if r['agree']) / N
A_rows = [r for r in rows if r['truth'] == 'A']
Bbad = [r for r in rows if r['truth'] == 'B' and B_meta[r['orig']]['quality'] == 'bad']
Bgood = [r for r in rows if r['truth'] == 'B' and B_meta[r['orig']]['quality'] == 'good']

def rate(rs, pred):
    return sum(1 for r in rs if pred(r)) / len(rs) if rs else float('nan')

J2 = rate(A_rows, lambda r: r['maj'] == 'B')          # 真实文本被判为模仿
J3 = rate(Bbad, lambda r: r['maj'] == 'B')            # 有缺陷模仿被识破
J4 = rate(Bgood, lambda r: r['maj'] == 'A')           # 无缺陷模仿被判为真实

print()
print('=' * 78)
print(f'J1 裁判间一致率（多数裁决）    : {J1:.2f}   ({sum(1 for r in rows if r["agree"])}/{N})')
print(f'J2 A类误判率（真→假，假阳性）  : {J2:.2f}   ({sum(1 for r in A_rows if r["maj"]=="B")}/{len(A_rows)})')
print(f'J3 B类bad检出率（敏感度）      : {J3:.2f}   ({sum(1 for r in Bbad if r["maj"]=="B")}/{len(Bbad)})')
print(f'J4 B类good误判率（我的模仿骗过裁判）: {J4:.2f}   ({sum(1 for r in Bgood if r["maj"]=="A")}/{len(Bgood)})')
acc = sum(1 for r in rows if r['correct']) / N
print(f'总准确率                        : {acc:.2f}   ({sum(1 for r in rows if r["correct"])}/{N})')

# ---------- 缺陷定位 J5 ----------
print()
print('-' * 78)
print('J5 缺陷定位命中（仅 B类bad）:')
hit = tot = 0
for r in Bbad:
    q = DEFECT_QUOTE.get(r['orig'], [])
    found = []
    for name, j in judges:
        s = (j.get(r['no'], {}).get('suspect_quote') or '')
        if any(k in s for k in q):
            found.append(name)
    tot += 1
    if found:
        hit += 1
    print(f'  块{r["no"]:>2} {r["orig"]:<4} 投票{"/".join(r["votes"])}  命中定位 {len(found)}/{len(judges)} 个裁判')
print(f'  → 缺陷定位命中率: {hit}/{tot}')

# ---------- 逐块明细 ----------
print()
print('-' * 78)
print('逐块明细（A=真实 B=模仿）:')
print(f'{"块":>3} {"原id":<5} {"真值":<4} {"票型":<18} {"多数":<4} {"一致":<4} {"正确"}')
for r in rows:
    print(f'{r["no"]:>3} {r["orig"]:<5} {r["truth"]:<4} {"/".join(r["votes"]):<18} '
          f'{r["maj"]:<4} {"是" if r["agree"] else "否":<4} {"√" if r["correct"] else "×"}')

# ---------- 预注册判定 ----------
print()
print('=' * 78)
print('预注册判定 D1–D5:')
res = []
if J1 < 0.70: res.append('D1 命中：任务本身不稳定 → 不做任何自动判断')
if J2 >= 0.375: res.append('D2 命中：无法可靠区分真实与模仿 → 删除反馈引擎')
if J3 >= 0.75 and J2 <= 0.20: res.append('D3 命中：可保留有界判断（仅具体偏离 + 原文证据）')
if (0.55 <= J3 < 0.75) or (0.20 < J2 < 0.375): res.append('D4 命中：判断降级为设问，不下结论')
if J4 >= 0.60: res.append('D5 区域：无缺陷模仿大量骗过裁判 → 判定依赖明显标记而非风格理解')
print('  ' + ('\n  '.join(res) if res else '无规则命中（结果落在阈值之间的其它区间）'))
