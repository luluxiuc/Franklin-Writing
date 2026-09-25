# -*- coding: utf-8 -*-
"""核对:实验一 5 位裁判的汇总数字,以及哪些裁判的逐块判定有留档。"""
import io
import json
import os

B = r'D:\ds harness\Fk-writing\_capability'
key = json.load(io.open(os.path.join(B, 'key.json'), encoding='utf-8'))
order, A = key['order'], set(key['A_ids'])
GOOD = {oid for oid, v in key['B'].items() if v['quality'] == 'good'}

# 裁判 2 / 4 的裁决转录自报告表格(原始逐块文件未留存)
REPORT = {
    'J2': {1: 'B', 2: 'A', 3: 'A', 4: 'A', 5: 'A', 6: 'B', 7: 'B', 8: 'B', 9: 'A',
           10: 'A', 11: 'B', 12: 'A', 13: 'B', 14: 'B', 15: 'A', 16: 'B', 17: 'A', 18: 'A'},
    'J4': {1: 'B', 2: 'A', 3: 'A', 4: 'A', 5: 'A', 6: 'B', 7: 'A', 8: 'B', 9: 'A',
           10: 'A', 11: 'A', 12: 'A', 13: 'A', 14: 'B', 15: 'A', 16: 'B', 17: 'A', 18: 'A'},
}
V, archived = {}, {}
for n in ('judge1', 'judge3', 'judge5'):
    j = n.upper().replace('JUDGE', 'J')
    V[j] = {r['no']: r['verdict'] for r in
            json.load(io.open(os.path.join(B, n + '.json'), encoding='utf-8'))}
    archived[j] = True
for j, d in REPORT.items():
    V[j] = d
    archived[j] = False

print('%-6s %-10s %-8s %-8s %-8s %-8s' % ('裁判', '逐块留档', '真A判A', '真B判B', 'good识破', '总正确'))
print('-' * 60)
tot_err = 0
for j in sorted(V):
    v = V[j]
    aa = sum(1 for i in range(1, 19) if order[i - 1] in A and v[i] == 'A')
    bb = sum(1 for i in range(1, 19) if order[i - 1] not in A and v[i] == 'B')
    good = sum(1 for i in range(1, 19) if order[i - 1] in GOOD and v[i] == 'B')
    ok = aa + bb
    tot_err += 18 - ok
    print('%-6s %-10s %-8s %-8s %-8s %-8s' % (
        j, '是' if archived[j] else '否(见报告)', '%d/8' % aa, '%d/10' % bb, '%d/5' % good, '%d/18' % ok))
print()
print('5 位裁判合计判错 %d 次；其中 3 位（留档者）合计判错 %d 次。' % (
    tot_err, sum(18 - (sum(1 for i in range(1, 19) if order[i - 1] in A and V[j][i] == 'A')
                       + sum(1 for i in range(1, 19) if order[i - 1] not in A and V[j][i] == 'B'))
                for j in ('J1', 'J3', 'J5'))))
print()
print('全同一致的块：', end='')
unanim = [i for i in range(1, 19) if len(set(V[j][i] for j in V)) == 1]
split = [i for i in range(1, 19) if len(set(V[j][i] for j in V)) > 1]
print('%d 块 %s' % (len(unanim), unanim))
print('出现分歧的块：%d 块 %s' % (len(split), split))
print('分歧块的真值类型：', [('真实' if order[i - 1] in A else ('good' if order[i - 1] in GOOD else 'bad'))
                             for i in split])
print('一致率 %d/18 = %.0f%%' % (len(unanim), 100.0 * len(unanim) / 18))
