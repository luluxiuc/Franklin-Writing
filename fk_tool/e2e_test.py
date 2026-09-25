# -*- coding: utf-8 -*-
"""原型端到端测试：跑通 import → write → compare 的约束链。"""
import json, os, subprocess, sys, io, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, PYTHONIOENCODING='utf-8')

def run(args, stdin=None):
    p = subprocess.run([sys.executable, os.path.join(HERE, 'fk.py')] + args,
                       input=stdin, capture_output=True, text=True, encoding='utf-8', env=ENV)
    return p.returncode, (p.stdout or '') + (p.stderr or '')

# 干净开始
shutil.rmtree(os.path.join(HERE, 'state'), ignore_errors=True)
code, out = run(['import', os.path.join(HERE, 'corpus-test.txt'), '--title', '端到端测试', '--size', '60'])
print('【1】import →', 'OK' if code == 0 else 'FAIL')
wid = [ln for ln in out.split('\n') if '作品 id' in ln][0].split('：')[1].strip()
print('    作品 id =', wid)

draft = ('家乡的端午，很多风俗和外地一样。系百索子。因为要用五色的丝线，所以人们把它拧成小绳，'
         '系在手腕上，让我感到非常温暖。做香角子。\nEND\n')
code, out = run(['write', wid, '1'], stdin=draft)
print('\n【2】write →', 'OK' if code == 0 else 'FAIL')
print('    提示行：', [ln for ln in out.split('\n') if ln.strip().startswith(('家乡', '　'))][0].strip()[:60] if '　' in out else '')
print('    是否隐藏原文：', 'OK（提示：原文已被隐藏）' if '原文已被隐藏' in out else '!! 未隐藏')

code, out = run(['compare', wid, '1'], stdin='END\n')
print('\n【3】compare 立刻执行（应被延迟拦住）→', 'returncode', code)
print('    ', 'OK 被拦住' if '还在延迟期内' in out else '!! 没拦住')
print('    ', [ln.strip() for ln in out.split('\n') if '剩余' in ln][0] if '剩余' in out else '')

code, out = run(['compare', wid, '1', '--skip-delay'], stdin='END\n')
print('\n【4】compare --skip-delay 且不写观察（应拒绝完成）→ returncode', code)
print('    ', 'OK 拒绝完成' if '不算完成' in out else '!! 竟然完成了')

code, out = run(['compare', wid, '1', '--skip-delay'], stdin='我看到我把三句短句合并成了一句长的。\nEND\n')
print('\n【5】compare 并写下观察 → returncode', code)
ok_cmp = '并置对照' in out or '原　文' in out
print('    并置渲染：', 'OK' in out and 'OK' or ('OK' if ok_cmp else '!!'))
print('    覆盖清单：', 'OK' if '未出现' in out else '!!')
print('    记录完成：', 'OK' if '本单元完成' in out else '!!')

code, out = run(['list', wid])
print('\n【6】list →', 'OK' if code == 0 and '我的观察' in out else 'FAIL')
print('    ' + '\n    '.join([l for l in out.split('\n') if '观察' in l][:2]))

# 复查落库内容
lib = json.load(open(os.path.join(HERE, 'state', 'library.json'), encoding='utf-8'))
u = lib['works'][0]['units'][0]
print('\n【7】落库字段：')
for k in ('draft', 'submitted_at', 'coverage', 'observation', 'compared_at'):
    v = u.get(k)
    s = ('已记录' if v else '空') if k in ('submitted_at', 'compared_at') else (f'{len(v)} 项' if isinstance(v, (list, dict)) else ('已记录' if v else '空'))
    print(f'    {k:<14} {s}')
print('    是否写入任何评分字段：', '!! 有' if any('score' in k or 'similarity' in k.lower() for k in u) else 'OK 无')
