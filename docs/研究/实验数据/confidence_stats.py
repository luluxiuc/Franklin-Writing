# -*- coding: utf-8 -*-
"""
confidence_stats — 裁判自报置信度与判对与否的关系。

发现:判错并不是犹豫出来的。10 次判错全部是置信度 >= 4,其中 1 次是满分 5。

用法：python docs/研究/实验数据/confidence_stats.py
需要 judge*.json 与 key.json 在同一目录。
"""
import glob
import io
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    key = json.load(io.open(os.path.join(HERE, 'key.json'), encoding='utf-8'))
    verdicts, confs = {}, {}
    for f in sorted(glob.glob(os.path.join(HERE, 'judge*.json'))):
        name = os.path.splitext(os.path.basename(f))[0]
        rows = json.load(io.open(f, encoding='utf-8'))
        verdicts[name] = {r['no']: r['verdict'] for r in rows}
        confs[name] = {r['no']: r.get('confidence') for r in rows}
    return key, verdicts, confs


def band_of(oid, a_ids, key):
    if oid in a_ids:
        return 'A', 'A 真实'
    q = key['B'][oid]['quality']
    return ('Bgood' if q == 'good' else 'Bbad'), \
           ('B 无缺陷模仿' if q == 'good' else 'B 有缺陷模仿')


def main():
    key, verdicts, confs = load()
    order, a_ids = key['order'], set(key['A_ids'])
    judges = sorted(verdicts)

    print('裁判：%s' % '、'.join(judges))
    print('（注意：只有 3 位裁判的原始判定被逐块留存。裁判 2、4 的判定见研究报告中的表格，'
          '未逐块留档。）')
    print()

    head = '%-4s %-6s %-5s %-12s ' % ('块', '原id', '真值', '类型')
    print(head + '  '.join('%-8s' % j for j in judges))
    print('-' * (len(head) + 10 * len(judges)))

    bands = {}
    for n in range(1, len(order) + 1):
        oid = order[n - 1]
        band, label = band_of(oid, a_ids, key)
        truth = 'A' if band == 'A' else 'B'
        cells = []
        for j in judges:
            v, c = verdicts[j][n], confs[j][n]
            ok = (v == truth)
            cells.append('%s%s/%s' % (v, '' if ok else '*', c))
            bands.setdefault(band, []).append((j, n, ok, c, truth, v))
        print('%-4d %-6s %-5s %-12s ' % (n, oid, truth, label) + '  '.join('%-8s' % c for c in cells))

    print()
    print('* = 判错    /n = 裁判自报置信度（1–5）')
    print()
    print('=' * 78)
    print('分组统计')
    print('=' * 78)
    for band in ('A', 'Bgood', 'Bbad'):
        rows = bands.get(band, [])
        if not rows:
            continue
        label = {'A': 'A 真实', 'Bgood': 'B 无缺陷模仿', 'Bbad': 'B 有缺陷模仿'}[band]
        right = [r for r in rows if r[2]]
        wrong = [r for r in rows if not r[2]]
        print('%-16s n=%-4d 正确 %2d/%-3d  判对时平均置信 %s   判错时平均置信 %s' % (
            label, len(rows), len(right), len(rows),
            '%.2f' % st.mean([r[3] for r in right]) if right else '—',
            '%.2f (n=%d)' % (st.mean([r[3] for r in wrong]), len(wrong)) if wrong else '—'))

    print()
    print('=' * 78)
    print('判错且置信度 >= 4 的明细')
    print('=' * 78)
    hits = 0
    for band in ('A', 'Bgood', 'Bbad'):
        for (j, n, ok, c, truth, v) in bands.get(band, []):
            if not ok and c >= 4:
                hits += 1
                print('  %s  块%-4d(原%-4s)  真值 %s → 判成 %s   置信 %d' % (
                    j, n, order[n - 1], truth, v, c))
    total_wrong = sum(1 for b in bands.values() for r in b if not r[2])
    print()
    print('判错共 %d 次，其中置信度 >= 4 的 %d 次，满分 5 的 %d 次。' % (
        total_wrong, hits,
        sum(1 for b in bands.values() for r in b if not r[2] and r[3] == 5)))
    print()
    print('>> 结论：判错不是犹豫出来的，说反了也一样笃定。')
    print('>> 注意：置信度是模型自报的，未经独立校准。它足以说明"不是低置信度的取舍"，')
    print('   但不能当作模型有良好校准的证据。')


if __name__ == '__main__':
    main()
