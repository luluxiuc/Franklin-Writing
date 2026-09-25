# -*- coding: utf-8 -*-
"""原型自测：不进入交互，直接检验各模块输出。"""
import json, os, sys, io, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fk

lib = fk.load_lib()
if not lib['works']:
    print('!! 范文库为空，先运行 import'); sys.exit(1)
w = lib['works'][0]
print(f'作品：{w["title"]}  {w["chars"]} 字  {len(w["units"])} 单元')
print()
print('=== 提示抽取（这是上一版的 bug 所在）===')
for u in w['units'][:4]:
    print(f'单元{u["no"]}（{u["chars"]}字）')
    print('  提示：' + ' / '.join(u['keywords']))
    print('  原文：' + u['text'][:58] + ('…' if len(u['text']) > 58 else ''))
    print()

print('=== 覆盖率机械比对（用单元1原文当"用户稿"，应几乎全命中）===')
src = w['units'][0]['text']
hit, miss = fk.coverage(src, src)
print(f'  命中 {len(hit)}：' + '、'.join(hit[:20]))
print(f'  未出现 {len(miss)}：' + ('、'.join(miss[:20]) if miss else '（无）'))
print()

print('=== 覆盖率：用一个刻意写坏的稿子 ===')
bad = '家乡的端午，很多风俗和外地一样。因为要系百索子，所以人们把五色的丝线拧成小绳，系在手腕上，让我感到非常温暖。'
hit2, miss2 = fk.coverage(src, bad)
print(f'  命中 {len(hit2)}：' + '、'.join(hit2[:20]))
print(f'  未出现 {len(miss2)}：' + '、'.join(miss2[:20]))
print()

print('=== 并置对照渲染（前 8 行）===')
import contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    fk.side_by_side(src, bad, width=30)
for ln in buf.getvalue().split('\n')[:10]:
    print('  ' + ln)
print()

print('=== 约束自检 ===')
_src = open(os.path.join(HERE, 'fk.py'), encoding='utf-8').read()
_cc = _src.split('def cmd_compare')[1][:3000]
checks = []
checks.append(('不调用任何模型', not any(k in _src for k in ('openai', 'requests', 'urllib', 'http.client'))))
checks.append(('不输出任何分数', not any(k in _cc for k in ('score', 'similarity', '评分', '接近度'))))
checks.append(('覆盖率只列事实', '只列事实' in _cc and '不换算' in _src))
checks.append(('强制"我的观察"', '没有写下观察，本单元不算完成' in _src))
checks.append(('延迟约束存在', '还在延迟期内' in _cc))
checks.append(('提交后默认不可覆盖', '默认不允许覆盖' in _src))
checks.append(('档案不做归纳（无能力结论）',
               not any(k in _src for k in ('习惯性遗忘', '你总是', '你经常', '已掌握'))))
for name, ok in checks:
    print(f'  [{"OK" if ok else "!!"}] {name}')
print()
print('  → 全部通过' if all(o for _, o in checks) else '  → 有不通过项')
