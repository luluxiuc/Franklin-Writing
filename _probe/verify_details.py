# -*- coding: utf-8 -*-
import re, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
P = r"D:\ds harness\Fk-writing\_probe\corpus\wang-zengqi-duanwu.txt"
t = open(P, encoding='utf-8').read()

print('--- 「高兴」在原文中的全部出现位置 ---')
for m in re.finditer('高兴', t):
    print('  → ...' + t[max(0, m.start()-16):m.start()+8].replace('\n', '|') + '...')

print()
print('--- 计量单位错误检验：第1段 ---')
p1 = t.split('\n')[0]
u = lambda x: re.sub(r'[，。！？；：、“”"]', '', x)
def claus(s):
    out, cur = [], ''
    for ch in s:
        cur += ch
        if ch in '，；：、。！？':
            out.append(cur.strip()); cur = ''
    if cur.strip(): out.append(cur.strip())
    return out
VERB = list('系做贴喝放点写出腌有是要挑挂装捉')
cs = [c for c in claus(p1) if u(c)]
ss = [s for s in re.split(r'(?<=[。！？])', p1) if u(s)]
vi_c = [c for c in cs if u(c)[:1] in VERB]
vi_s = [s for s in ss if u(s)[:1] in VERB]
print(f'  小句级：{len(vi_c)}/{len(cs)} = {len(vi_c)/len(cs):.0%}  举例 {[u(c)[:10] for c in vi_c[:6]]}')
print(f'  句  级：{len(vi_s)}/{len(ss)} = {len(vi_s)/len(ss):.0%}  举例 {[u(s)[:10] for s in vi_s[:6]]}')

print()
print('--- 该段最长连续短小句串（哨兵句所在环境） ---')
run = best = 0
for c in cs:
    run = run + 1 if len(u(c)) <= 6 else 0
    best = max(best, run)
print(f'  最长连续 <=6 字小句：{best} 个')
lens = [len(u(c)) for c in cs]
print(f'  小句长度序列（前32个）：{lens[:32]}')
