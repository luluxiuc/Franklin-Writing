# -*- coding: utf-8 -*-
"""冒烟测试：从空状态跑通一次最小训练，验证"拿到仓库即可用"。
退出码 0 = 通过。可放进 CI。
"""
import json, os, shutil, subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
CORPUS = os.path.join(ROOT, '_probe', 'corpus', 'wang-zengqi-duanwu.txt')

def run(args, stdin=None):
    p = subprocess.run([sys.executable, os.path.join(HERE, 'fk.py')] + args,
                       input=stdin, capture_output=True, text=True, encoding='utf-8', env=ENV)
    return p.returncode, (p.stdout or '') + (p.stderr or '')

fails = []
def check(cond, label):
    print(f'  [{"OK" if cond else "!!"}] {label}')
    if not cond: fails.append(label)

shutil.rmtree(os.path.join(HERE, 'state'), ignore_errors=True)

# 空状态
code, out = run(['status'])
check(code == 0 and '空的' in out, '空状态给出正确引导')

# 导入
src = CORPUS if os.path.exists(CORPUS) else os.path.join(HERE, 'corpus-test.txt')
if not os.path.exists(src):
    print('!! 找不到测试语料，跳过'); sys.exit(1)
code, out = run(['import', src, '--title', '冒烟测试', '--size', '60'])
check(code == 0 and '切分为' in out, 'import 成功并切分')
wid = [l for l in out.split('\n') if '作品 id' in l][0].split('：')[1].strip()

# 提示必须是原文连续子串（关键的"不猜词"约束）
lib = json.load(open(os.path.join(HERE, 'state', 'library.json'), encoding='utf-8'))
u1 = lib['works'][0]['units'][0]
check(all(k in u1['text'] for k in u1['keywords']),
      f'提示全部是原文连续子串（{len(u1["keywords"])} 个）')

# 写
code, out = run(['write', wid, '1'], stdin='家乡的端午，很多风俗和外地一样。系百索子。\nEND\n')
check(code == 0 and '原文已被隐藏' in out, 'write 隐藏原文并收稿')
check('已收下' in out, 'write 收下不完整的稿子（不给提示）')

# 延迟
code, out = run(['compare', wid, '1'], stdin='END\n')
check(code == 1 and '还在延迟期内' in out, 'compare 被延迟拦住')

# 无观察不得完成
code, out = run(['compare', wid, '1', '--skip-delay'], stdin='END\n')
check(code == 1 and '不算完成' in out, '无观察不得完成单元')

# 正常完成
code, out = run(['compare', wid, '1', '--skip-delay'], stdin='我漏掉了后半段。\nEND\n')
check(code == 0 and '本单元完成' in out, '写下观察后完成单元')
check('未出现' in out and '只列事实' in out, '覆盖率只列事实')

# 不可覆盖
code, out = run(['write', wid, '1'], stdin='x\nEND\n')
check(code == 1 and '默认不允许覆盖' in out, '提交后默认不可覆盖')

# 无评分字段
u = json.load(open(os.path.join(HERE, 'state', 'library.json'), encoding='utf-8'))['works'][0]['units'][0]
check(not any(k for k in u if 'score' in k.lower() or 'similarity' in k.lower()),
      '落库数据不含任何评分字段')

print()
if fails:
    print(f'失败 {len(fails)} 项：')
    for f in fails: print('  - ' + f)
    sys.exit(1)
print('冒烟测试全部通过')
sys.exit(0)
