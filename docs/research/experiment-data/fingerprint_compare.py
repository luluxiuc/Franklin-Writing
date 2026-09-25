# -*- coding: utf-8 -*-
"""关键对照（修正版）：18 块量化，检验裁判的区分依据。
修正了两个上次失效的指标：
  1) 名物密度归一化后分母几乎恒定 → 换成信息量指标（可核验具体项数 / 百字）
  2) agg() 误用了硬编码 J3 字典 → 改为传入投票表，输出各裁判交叉表
"""
import json, re, io, sys, statistics as st
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r"D:\ds harness\Fk-writing\_capability"
key = json.load(open(BASE + r'\key.json', encoding='utf-8'))
blocked = json.load(open(BASE + r'\blocked.json', encoding='utf-8'))
order, A_ids = key['order'], set(key['A_ids'])
texts = {b['no']: b['text'] for b in blocked}

V = {
 '裁判1': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判2': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'A',10:'A',11:'B',12:'A',13:'B',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判3': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'B',8:'B',9:'B',10:'A',11:'B',12:'A',13:'B',14:'B',15:'B',16:'B',17:'A',18:'A'},
 '裁判4': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
 '裁判5': {1:'B',2:'A',3:'A',4:'A',5:'A',6:'B',7:'A',8:'B',9:'A',10:'A',11:'A',12:'A',13:'A',14:'B',15:'A',16:'B',17:'A',18:'A'},
}
u = lambda s: re.sub(r'[，。！？；：、“”"（）《》…—\s/]', '', s)
truth = {n: ('A' if order[n-1] in A_ids else 'B') for n in range(1, 19)}
kind = {n: ('真实' if order[n-1] in A_ids else
            ('good' if key['B'][order[n-1]]['quality'] == 'good' else 'bad')) for n in range(1, 19)}

# 信息量指标：可核验的具体项 —— 器物/动作/工序类实词（人工枚举自 18 块，去重）
CONCRETE = set("""八仙桌 丝线 小绳 手腕 香角子 粽子 香面 帐钩 红纸 五毒 门槛 符 城隍庙 道士 小纸扇
门楣 纸条 朱笔 雄黄 雄黄酒 额头 黄烟子 炮仗 硝药 橱柜 板壁 虎字 苋菜 油爆虾 鸭蛋 麻鸭 腌腊 店铺
双黄 络子 纽扣 蛋壳 萤火虫 薄罗 石灰 筷子 红油 朱砂豆腐 豆腐 卷子 车胤 练囊 井台 青石 井沿
水光 缸 藕节 荷叶 青苔 缸壁 顶针 木轴 黑线 白线 剪子 张小泉 纽扣 花纹 自行车 链条盒 铁皮 棉垫
豆浆铺 石磨 磨盘 裂纹 铁箍 浆 碗 肥皂 藕 荷 修鞋摊 鞋 工具 刀 针 线""".split())

def feats(t):
    ss = [s for s in re.split(r'(?<=[。！？])', t) if u(s)]
    cc = []
    for s in ss:
        cur = ''
        for ch in s:
            cur += ch
            if ch in '，；：、。！？':
                if u(cur): cc.append(u(cur))
                cur = ''
        if u(cur): cc.append(u(cur))
    n = len(u(t)) or 1
    conc = sum(1 for w in CONCRETE if w in t)
    verbs = len(re.findall(r'[系做贴喝放点写腌挑挂装捉敲洗净糊骑磨舀压绑丢掏扑摊撑溢淌]', t))
    return dict(
        chars=n, sents=len(ss), clauses=len(cc),
        cl_mean=round(st.mean([len(c) for c in cc]), 1) if cc else 0,
        cl_sd=round(st.pstdev([len(c) for c in cc]), 1) if len(cc) > 1 else 0,
        conn=round(sum(t.count(w) for w in ['因为','所以','因此','由于','而且','于是','然后','接着','至今','仍然','仿佛','不禁','令人']) / n * 100, 2),
        emo=len(re.findall(r'惆怅|温暖|幸福|怀念|敬畏|湿润|孤独|悲伤|高兴|快乐|激动|感动|失落|心酸|热闹', t)),
        conc=conc, conc_density=round(conc / n * 100, 1),
        verbs=verbs, verb_density=round(verbs / n * 100, 1),
    )

rows = []
for n in range(1, 19):
    f = feats(texts[n]); f.update(no=n, oid=order[n-1], truth=truth[n], kind=kind[n]); rows.append(f)

print('=' * 104)
print('18 块量化（关键指标：可核验具体项密度、动词密度、连接词密度、情绪词）')
print('=' * 104)
print(f'{"块":>3} {"原id":<5} {"真值":<4} {"类型":<5} {"字":>4} {"具体项":>5} {"具体密度":>7} {"动词密度":>7} {"连接词":>6} {"情绪":>4}')
for r in rows:
    print(f'{r["no"]:>3} {r["oid"]:<5} {r["truth"]:<4} {r["kind"]:<5} {r["chars"]:>4} {r["conc"]:>5} '
          f'{r["conc_density"]:>7} {r["verb_density"]:>7} {r["conn"]:>6} {r["emo"]:>4}')

def agg(rs, label):
    if not rs: return
    print(f'{label:<26} n={len(rs):>2}  具体密度={st.mean([r["conc_density"] for r in rs]):>5.1f}  '
          f'动词密度={st.mean([r["verb_density"] for r in rs]):>5.1f}  '
          f'连接词={st.mean([r["conn"] for r in rs]):>5.2f}  '
          f'情绪词={st.mean([r["emo"] for r in rs]):>4.2f}  '
          f'字数={st.mean([r["chars"] for r in rs]):>5.1f}')

print()
print('-' * 104)
agg([r for r in rows if r['kind'] == '真实'], 'A 真实（8 段）')
agg([r for r in rows if r['kind'] == 'good'], 'B-good 无缺陷模仿（5 段）')
agg([r for r in rows if r['kind'] == 'bad'], 'B-bad 植入缺陷（5 段）')

print()
print('=' * 104)
print('各裁判交叉表（真值 × 裁判）—— 分歧全部落在 good 上')
print('=' * 104)
for name, t in V.items():
    c = Counter((truth[n], t[n]) for n in range(1, 19))
    good_right = sum(1 for n in range(1, 19) if kind[n] == 'good' and t[n] == 'B')
    print(f'{name}: 真A判A={c[("A","A")]}/8  真A判B={c[("A","B")]}/8 | '
          f'真B判B={c[("B","B")]}/10  真B判A={c[("B","A")]}/10 | '
          f'good 识破 {good_right}/5 | 总正确 {sum(1 for n in range(1,19) if t[n]==truth[n])}/18')

print()
print('=' * 104)
print('关键问题：裁判区分 A 与 good 时，能用的是具体项密度吗？')
print('=' * 104)
A_d = [r['conc_density'] for r in rows if r['kind'] == '真实']
G_d = [r['conc_density'] for r in rows if r['kind'] == 'good']
A_c = [r['chars'] for r in rows if r['kind'] == '真实']
G_c = [r['chars'] for r in rows if r['kind'] == 'good']
print(f'  具体项密度：A 真实 {st.mean(A_d):.1f}   good {st.mean(G_d):.1f}   差 {st.mean(A_d)-st.mean(G_d):+.1f}')
print(f'  字数      ：A 真实 {st.mean(A_c):.0f}   good {st.mean(G_c):.0f}   差 {st.mean(A_c)-st.mean(G_c):+.0f}')
print()
print('  → 若具体项密度相近而字数差异大，说明裁判可利用的混淆变量主要是「篇幅/信息量」。')
