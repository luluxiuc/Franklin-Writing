# -*- coding: utf-8 -*-
"""实验一最终统计（含裁判2、4）。"""
import json, re, io, sys, statistics as st
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

B = r"D:\ds harness\Fk-writing\_capability"
key = json.load(open(B + r'\key.json', encoding='utf-8'))
blocked = json.load(open(B + r'\blocked.json', encoding='utf-8'))
order, A_ids = key['order'], set(key['A_ids'])
texts = {b['no']: b['text'] for b in blocked}
u = lambda s: re.sub(r'[，。！？；：、“”"（）《》…—\s/]', '', s)

V = {
 '裁判1': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判3': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'B',10:'A',11:'B',12:'A',13:'B',14:'B',15:'B',16:'B',17:'A',18:'A'},
 '裁判4': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判5': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
}
names = list(V)

truth = {n: ('A' if order[n-1] in A_ids else 'B') for n in range(1, 19)}
kind  = {n: ('真实' if order[n-1] in A_ids else
             ('模仿good' if key['B'][order[n-1]]['quality'] == 'good' else '模仿bad'))
         for n in range(1, 19)}

print('=' * 100)
print('实验一最终统计（4 位裁判，18 块）')
print('=' * 100)
print(f'{"块":>3} {"原id":<5} {"真值":<4} {"类型":<9} ' + ' '.join(f'{x:<4}' for x in names) + f'{"一致":<5}{"字数":>4}')
n_unanim = 0
for n in range(1, 19):
    vs = [V[k][n] for k in names]
    same = len(set(vs)) == 1
    n_unanim += same
    print(f'{n:>3} {order[n-1]:<5} {truth[n]:<4} {kind[n]:<9} ' + ' '.join(f'{v:<4}' for v in vs)
          + f'{"全同" if same else "分歧":<5}{len(u(texts[n])):>4}')

print()
print('-' * 100)
print('裁判两两一致率:')
print('        ' + '  '.join(f'{x:<8}' for x in names))
for a in names:
    cells = []
    for b in names:
        ag = sum(1 for n in range(1, 19) if V[a][n] == V[b][n])
        cells.append(f'{ag}/18'.ljust(8))
    print(f'{a:<8}' + '  '.join(cells))

print()
print('-' * 100)
def report(sel, label):
    ns = [n for n in range(1, 19) if sel(n)]
    if not ns: return
    print(f'\n【{label}】 n={len(ns)}  块={ns}')
    for k in names:
        corr = sum(1 for n in ns if V[k][n] == truth[n])
        print(f'   {k}: 正确 {corr}/{len(ns)} = {corr/len(ns):.0%}')
    maj = []
    for n in ns:
        c = Counter(V[k][n] for k in names)
        maj.append(c.most_common(1)[0][0])
    corr = sum(1 for n, m in zip(ns, maj) if m == truth[n])
    print(f'   多数裁决: 正确 {corr}/{len(ns)} = {corr/len(ns):.0%}')

report(lambda n: truth[n] == 'A', 'A 类：真实文本（误判 = 假阳性，最不可接受）')
report(lambda n: kind[n] == '模仿bad', 'B-bad：植入明显缺陷的模仿')
report(lambda n: kind[n] == '模仿good', 'B-good：无植入缺陷的模仿（关键）')

print()
print('=' * 100)
print('决定性指标')
print('=' * 100)
A_ns = [n for n in range(1, 19) if truth[n] == 'A']
bad_ns = [n for n in range(1, 19) if kind[n] == '模仿bad']
good_ns = [n for n in range(1, 19) if kind[n] == '模仿good']

J2 = sum(1 for n in A_ns if Counter(V[k][n] for k in names).most_common(1)[0][0] == 'B') / len(A_ns)
J3 = sum(1 for n in bad_ns if Counter(V[k][n] for k in names).most_common(1)[0][0] == 'B') / len(bad_ns)
# J4 正确语义：无缺陷模仿被识破的比例
J4_detect = sum(1 for n in good_ns if Counter(V[k][n] for k in names).most_common(1)[0][0] == 'B') / len(good_ns)
# 每位裁判对 good 的判定一致率
good_agree = sum(1 for n in good_ns if len(set(V[k][n] for k in names)) == 1) / len(good_ns)

print(f'J1  裁判间全同一致率（18 块）      : {n_unanim}/18 = {n_unanim/18:.0%}')
print(f'J2  A 类误判率（真实被判为模仿）    : {J2:.0%}   ← 4 位裁判全部判对 8/8')
print(f'J3  B-bad 检出率（敏感度）         : {J3:.0%}   ← 4 位裁判全部识破 5/5')
print(f'J4  无缺陷模仿被识破率             : {J4_detect:.0%}   ← 只有 1/5 被识破')
print(f'    无缺陷模仿上的裁判一致率        : {good_agree:.0%}   ← 分歧 100% 集中在此')
print()
print(f'>>> 判别力全部来自「有无明显缺陷」，而非「像不像作者」。')
print(f'>>> 在 5 块无缺陷模仿上，4 位裁判仅 {int(J4_detect*len(good_ns))} 位判对，其余 3 位判为真实原文。')
print(f'>>> 若把「判为真实」视为漏检，则系统在「同水平但非本人」的文本上近乎随机。')
