# -*- coding: utf-8 -*-
"""关键分析：三位裁判的真实分歧结构，以及本材料设计的致命缺陷（长度混淆）。"""
import json, re, io, sys, statistics as st
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

B = r"D:\ds harness\Fk-writing\_capability"
key = json.load(open(B + r'\key.json', encoding='utf-8'))
blocked = json.load(open(B + r'\blocked.json', encoding='utf-8'))
order, A_ids = key['order'], set(key['A_ids'])
texts = {b['no']: b['text'] for b in blocked}

V = {
 'J1': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 'J3': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'B',10:'A',11:'B',12:'A',13:'B',14:'B',15:'B',16:'B',17:'A',18:'A'},
 'J5': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
}
u = lambda s: re.sub(r'[，。！？；：、“”"（）《》…—\s/]', '', s)

print('=' * 96)
print('逐块：真值 × 三裁判裁决')
print('=' * 96)
print(f'{"块":>3} {"原id":<5} {"真值":<4} {"类型":<10} {"J1":<3} {"J3":<3} {"J5":<3} {"一致":<5} {"字数":>4}')
unanim, split = [], []
for n in range(1, len(order) + 1):
    oid = order[n - 1]
    truth = 'A' if oid in A_ids else 'B'
    kind = '真实' if truth == 'A' else ('模仿-good' if key['B'][oid]['quality'] == 'good' else '模仿-bad')
    vs = [V[k][n] for k in ('J1', 'J3', 'J5')]
    same = len(set(vs)) == 1
    (unanim if same else split).append(n)
    print(f'{n:>3} {oid:<5} {truth:<4} {kind:<10} {vs[0]:<3} {vs[1]:<3} {vs[2]:<3} '
          f'{"全同" if same else "分歧":<5} {len(u(texts[n])):>4}')

print()
print('全同一致的块（%d）: %s' % (len(unanim), unanim))
print('出现分歧的块（%d）: %s' % (len(split), split))
print()
print('>> 分歧块的全部类型：')
for n in split:
    oid = order[n - 1]
    print(f'   块{n} {oid}  {key["B"][oid]["quality"] if oid not in A_ids else "真实"}')

# 裁判两两一致率
print()
print('裁判两两一致率:')
for a in ('J1', 'J3', 'J5'):
    row = []
    for b in ('J1', 'J3', 'J5'):
        agree = sum(1 for n in range(1, 19) if V[a][n] == V[b][n])
        row.append(f'{agree}/18')
    print(f'  {a}: ' + '  '.join(row))

print()
print('=' * 96)
print('材料设计缺陷：长度混淆')
print('=' * 96)
for label, sel in (
    ('A 真实', lambda n: order[n-1] in A_ids),
    ('B-good（我未植入缺陷）', lambda n: order[n-1] not in A_ids and key['B'][order[n-1]]['quality'] == 'good'),
    ('B-bad（我植入缺陷）', lambda n: order[n-1] not in A_ids and key['B'][order[n-1]]['quality'] == 'bad'),
):
    ls = [len(u(texts[n])) for n in range(1, 19) if sel(n)]
    print(f'  {label:<24} n={len(ls)}  字数 {min(ls)}–{max(ls)}  均值 {st.mean(ls):.0f}')

print()
print('>> 关键：B-bad 的篇幅与 A 真实段相当，但 B-good 明显更短。')
print('   裁判区分 A/B 时，可利用的不只是风格，还有「这一段是不是太短、太薄」。')
print('   → 本实验无法把「风格判断能力」与「篇幅/信息量判断」分离开。这是设计缺陷，不是结论。')
