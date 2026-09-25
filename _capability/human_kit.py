# -*- coding: utf-8 -*-
"""人工标注工具包：测「合格读者之间的一致率」，即 LLM 一致率的分母。
用法:
  python human_kit.py materials     生成标注材料（不含答案）
  python human_kit.py score <标注文件...>   计算人类一致率，并与 LLM 裁判对比
"""
import json, os, sys, io, itertools, statistics as st
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

# 5 位 LLM 裁判的判定（用于对比）
LLM = {
 '裁判1': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判2': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'A',10:'A',11:'B',12:'A',13:'B',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判3': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'B',10:'A',11:'B',12:'A',13:'B',14:'B',15:'B',16:'B',17:'A',18:'A'},
 '裁判4': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判5': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
}

def load():
    key = json.load(open(os.path.join(BASE, 'key.json'), encoding='utf-8'))
    blocked = json.load(open(os.path.join(BASE, 'blocked.json'), encoding='utf-8'))
    return key, blocked

def materials():
    key, blocked = load()
    out = []
    out.append('# 人工标注材料（合格读者用）\n')
    out.append('## 任务说明\n')
    out.append('下面 18 个文本块混合了两种情况：')
    out.append('- **A**：某一篇真实已发表散文的段落（同一篇作品的连续段落）')
    out.append('- **B**：由 AI 模仿该作者风格新写的段落\n')
    out.append('对每一块判断属于 A 还是 B。规则：')
    out.append('1. 不要检索、不要查证出处——**只凭文本本身判断**。一旦检索，"判断"就变成了"查证"。')
    out.append('2. 判断依据请指向具体语言事实（词、句法、标点、节奏、收尾方式）。')
    out.append('3. 允许回答「无法判断」，并请如实使用它——**这个选项本身是重要的数据**。')
    out.append('4. 每块给 1-5 的把握度。\n')
    out.append('> 填写方式：复制本文件为 `标注-你的名字.md`，把每块末尾的 `判断：___  把握：___` 填上。\n')
    out.append('---\n')
    for b in blocked:
        out.append(f'### 块 {b["no"]}\n')
        out.append(b['text'].replace('/', ' '))
        out.append('')
        out.append('判断：___（A / B / 无法判断）　把握：___（1-5）　依据：')
        out.append('')
        out.append('---\n')
    return '\n'.join(out)

def parse(path):
    """解析一份标注文件，返回 {块号: (判断, 把握)}"""
    txt = open(path, encoding='utf-8').read()
    res = {}
    cur = None
    for ln in txt.split('\n'):
        s = ln.strip()
        if s.startswith('### 块'):
            try: cur = int(s.replace('### 块', '').strip())
            except ValueError: cur = None
        elif cur and ('判断：' in s or '判断:' in s):
            body = s.split('：', 1)[-1] if '：' in s else s.split(':', 1)[-1]
            v = None
            for cand in ('无法判断', 'A', 'B', 'a', 'b'):
                if body.strip().startswith(cand):
                    v = '无法判断' if cand == '无法判断' else cand.upper()
                    break
            conf = None
            for tok in body.replace('　', ' ').split():
                if tok.isdigit() and 1 <= int(tok) <= 5:
                    conf = int(tok); break
            if v: res[cur] = (v, conf)
    return res

def score(files):
    key, blocked = load()
    order, A_ids = key['order'], set(key['A_ids'])
    truth = {n: ('A' if order[n-1] in A_ids else 'B') for n in range(1, 19)}
    kind = {n: ('真实' if order[n-1] in A_ids else
                ('good' if key['B'][order[n-1]]['quality'] == 'good' else 'bad')) for n in range(1, 19)}

    humans = {}
    for f in files:
        r = parse(f)
        if r: humans[os.path.basename(f)] = r
    if not humans:
        print('没有解析到任何标注。'); return

    print('=' * 92)
    print(f'人工标注：{len(humans)} 位读者')
    print('=' * 92)
    for name, r in humans.items():
        corr = sum(1 for n, (v, _) in r.items() if v == truth.get(n))
        unres = sum(1 for _, (v, _) in r.items() if v == '无法判断')
        good_det = sum(1 for n, (v, _) in r.items() if kind.get(n) == 'good' and v == 'B')
        good_un = sum(1 for n, (v, _) in r.items() if kind.get(n) == 'good' and v == '无法判断')
        print(f'  {name:<26} 标注 {len(r)}/18  正确 {corr}/{len(r)}  '
              f'「无法判断」{unres}  good识破 {good_det}  good弃权 {good_un}')

    # 人类两两一致率
    names = list(humans)
    if len(names) >= 2:
        print()
        print('人工读者两两一致率（仅统计两人都标注的块）:')
        pairs = []
        for a, b in itertools.combinations(names, 2):
            common = set(humans[a]) & set(humans[b])
            if not common: continue
            ag = sum(1 for n in common if humans[a][n][0] == humans[b][n][0])
            pairs.append(ag / len(common))
            print(f'  {a[:14]} × {b[:14]}: {ag}/{len(common)} = {ag/len(common):.0%}')
        print(f'  → 人类平均两两一致率: {st.mean(pairs):.0%}')

    print()
    print('- ' * 46)
    print('LLM 裁判对照（同一材料、同一任务）:')
    for nm, t in LLM.items():
        corr = sum(1 for n in range(1, 19) if t[n] == truth[n])
        good_det = sum(1 for n in range(1, 19) if kind[n] == 'good' and t[n] == 'B')
        print(f'  {nm:<8} 正确 {corr}/18   其中 good 识破 {good_det}/5')

    print()
    print('=' * 92)
    print('判读要点')
    print('=' * 92)
    print('  1. 若人类一致率本身很低（<70%），说明该任务对合格读者也不稳定——')
    print('     那么模型与任何人一致都无意义，自动判断在原理上就不成立。')
    print('  2. 若人类一致率很高，而模型对 good 块识破率≈0，')
    print('     说明模型缺少人类共有的那种辨识力，同样不支持自动判断。')
    print('  3. 若人类也大量使用「无法判断」，这一项应当成为产品的正式输出选项，')
    print('     而不是被逼成 A/B 二选一。')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == 'materials':
        p = os.path.join(BASE, '人工标注材料.md')
        open(p, 'w', encoding='utf-8').write(materials())
        print(f'已生成：{p}')
        print('把它发给若干位合格读者，收回后用 score 子命令计算一致率。')
    elif cmd == 'score':
        score(sys.argv[2:])
    else:
        print(__doc__)
