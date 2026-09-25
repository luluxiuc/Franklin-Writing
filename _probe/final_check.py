# -*- coding: utf-8 -*-
"""终检：标题结构、节号连续性、交叉引用、表格完整性。"""
import io, sys, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r"D:\ds harness\Fk-writing\AI富兰克林写作训练系统-核心方法-v0.3.md"
t = open(P, encoding='utf-8').read()
L = t.split('\n')

print(f'总行数 {len(L)}  字符数 {len(t)}')
print()
heads = [l for l in L if l.startswith('#')]
print(f'标题总数 {len(heads)}')

nums = [int(re.match(r'^### (\d+)\.', h).group(1)) for h in L if re.match(r'^### \d+\.', l := h) if re.match(r'^### (\d+)\.', h)]
# 上面写法易错，重写：
nums = []
for h in L:
    m = re.match(r'^### (\d+)\. ', h)
    if m:
        nums.append(int(m.group(1)))
print('节号序列：', nums)
print('连续且无重复：', nums == list(range(1, len(nums)+1)))

print()
print('重复的部分标题：')
parts = [h for h in L if h.startswith('## ')]
from collections import Counter
for k, v in Counter(parts).items():
    if v > 1:
        print(f'  !! 重复 ×{v}：{k}')

print()
print('交叉引用（应全部指向存在的节号）：')
ok = True
for i, ln in enumerate(L, 1):
    for m in re.finditer(r'见第 (\d+) 节|第 (\d+) 节约束|受第 (\d+) 节', ln):
        n = int(next(g for g in m.groups() if g))
        exists = n in nums
        if not exists:
            ok = False
        print(f'  L{i}: 第 {n} 节  {"OK" if exists else "!! 不存在"}')
print('交叉引用全部有效：', ok)

print()
print('表格：')
for i, ln in enumerate(L, 1):
    if re.match(r'^\| --- ', ln):
        print(f'  L{i} 表头：{L[i-2][:80]}')

print()
print('残留占位/异常：')
for i, ln in enumerate(L, 1):
    if re.search(r'TODO|TBD|XXX|三层作者模型|V0\.3\.1', ln):
        print(f'  L{i}: {ln.strip()[:100]}')
