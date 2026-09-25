# -*- coding: utf-8 -*-
"""全篇节号顺序重排 + 修正正文中的交叉引用。"""
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r"D:\ds harness\Fk-writing\AI富兰克林写作训练系统-核心方法-v0.3.md"
text = open(P, encoding='utf-8').read()
lines = text.split('\n')

n = 0
mapping = []
out = []
for ln in lines:
    m = re.match(r'^### (\d+)\. (.*)$', ln)
    if m:
        old = int(m.group(1))
        n += 1
        mapping.append((old, n, m.group(2)))
        ln = f'### {n}. {m.group(2)}'
    out.append(ln)

# 旧节号 → 新节号（用于修正交叉引用）
old2new = {o: nw for o, nw, _ in mapping}

# 修正正文交叉引用
refs = {
    '见 §4.5': '见第二部分',
    '（算法见第 6 节）': f'（算法见第 {old2new[6]} 节）',
    '（算法见第 6 节，': f'（算法见第 {old2new[6]} 节，',
    '算法见第 6 节': f'算法见第 {old2new[6]} 节',
    '见第 6 节': f'见第 {old2new[6]} 节',
    '见第 7 节': f'见第 {old2new[7]} 节',
    '第 9 节约束': f'第 {old2new[9]} 节约束',
    '第 11 节': f'第 {old2new[11]} 节',
    '第 13 节': f'第 {old2new[13]} 节',
    '第 6/10/11 节': f'第 {old2new[6]}/{old2new[10]}/{old2new[11]} 节',
}
new_text = '\n'.join(out)
for a, b in refs.items():
    if a in new_text and a != b:
        new_text = new_text.replace(a, b)

open(P, 'w', encoding='utf-8').write(new_text)

print('节号映射（旧 → 新）：')
for o, nw, t in mapping:
    flag = '  ← 改了' if o != nw else ''
    print(f'  {o:>2} → {nw:>2}  {t}{flag}')
print()
print('正文交叉引用现状（含 "见第 / §" 的行）：')
for ln in new_text.split('\n'):
    if re.search(r'(见第|§|见第二部分)', ln) and not ln.startswith('### '):
        print('  ' + ln.strip()[:110])
