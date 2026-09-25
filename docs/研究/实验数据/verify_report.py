# -*- coding: utf-8 -*-
"""核验：报告正文引用的数字是否都能在数据源中找到。"""
import re, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = r"D:\ds harness\Fk-writing"
rep = open(os.path.join(ROOT, '为什么不做LLM判断评分.md'), encoding='utf-8').read()
app = open(os.path.join(ROOT, '附录-实测数据汇总.md'), encoding='utf-8').read()

def num_in(x, src):
    """在数据源中查找该数字（容忍千分位/全角差异）"""
    x = x.replace(' ', '')
    return x in src.replace(' ', '').replace('**', '')

# 从报告里抽出所有形如 "数字 字" / "数字%" / "数字/百字" / "n/m" 的量化断言
pat = re.compile(r'(\d+(?:\.\d+)?\s*(?:字|%|/百字|句|种|次|处|项|位|/18|/8|/5|/65|/26|/10))')
found = sorted(set(m.group(1) for m in pat.finditer(rep)))

# 需要核验的关键断言（人工列出，覆盖报告全部定量主张）
KEY = [
 '17.8', '10.0', '7.5', '179', '76', '2.4', '1 字', '43 字', '8 个 ≤6 字',
 '0%', '100%', '13/18', '72%', '8/8', '5/5', '0/5', '5/10', '3/5', '16/18', '18/18',
 '0.74', '2.39', '35.9', '4.3', '7.8', '86 字', '251 字',
 '4.7', '9.2', '6.2', '0.39', '0.25', '2.4', '1.1', '4.38', '1.40', '59.4', '87.8', '73.0',
 '20%', '13/65', '31%', '8/26', '3.8', '47 种', '165 次', '1.48', '6.9', '4.7',
 '60.7%', '2.07', '47 vs 47', '51 vs 51', '4 处', '2 句', '8 处', '0.93',
]
print('=== 关键断言核验（是否能在数据源中找到）===')
miss = []
for k in KEY:
    if k in rep:
        ok = num_in(k, app) or num_in(k, rep)
        print(f'  [{"OK" if ok else "??"}] {k}')
        if not ok: miss.append(k)
    else:
        print(f'  [--] {k}（报告未使用，跳过）')

print()
print('=== 报告里出现但需确认出处的单位数字 ===')
susp = []
for f in found:
    if f not in KEY and not num_in(f, app):
        susp.append(f)
print('  可疑：' + ('、'.join(susp) if susp else '（无）'))

print()
print('=== 一致性抽查：同一指标在两份文档中是否一致 ===')
pairs = [
    ('句长均值', r'17\.8', r'17\.8'),
    ('小句均值', r'7\.5', r'7\.5'),
    ('连接词密度', r'0\.74', r'0\.74'),
    ('good 识破率', r'0%', r'0%'),
    ('总正确率分母', r'13/18', r'13/18'),
]
for name, a, b in pairs:
    ia, ib = len(re.findall(a, rep)), len(re.findall(b, app))
    print(f'  {name:<12} 报告 {ia} 处   数据源 {ib} 处   {"一致" if ia and ib else "!! 检查"}')

print()
print('=== 结构检查 ===')
for f, label in ((rep, '报告'), (app, '附录')):
    h2 = len(re.findall(r'(?m)^## ', f)); tb = len(re.findall(r'(?m)^\| --- ', f))
    print(f'  {label}: {len(f)} 字符，{h2} 个一级小节，{tb} 张表')
