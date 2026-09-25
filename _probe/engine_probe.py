# -*- coding: utf-8 -*-
"""v0.3 §11 反馈引擎跑测 + 代理漂移打靶
输入：候选文本（用户临摹稿 / 或原文句子做哨兵测试）
输出：四层反馈 + 假阳性标记
"""
import re, statistics as st, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

P = r"D:\ds harness\Fk-writing\_probe\corpus\wang-zengqi-duanwu.txt"
raw = open(P, encoding='utf-8').read().strip()
paras = [p for p in raw.split('\n') if p.strip()]
QUOTE_IDX = [2]
author_text = ''.join(p for i, p in enumerate(paras) if i not in QUOTE_IDX)
u = lambda p: re.sub(r'[，。！？；：、“”"（）《》…—\s]', '', p)

SENT_END = '。！？'
CLAUSE_END = '，；：、'
def sents(p):
    out, cur = [], ''
    for ch in p:
        if ch in '“”"': continue
        cur += ch
        if ch in SENT_END: out.append(cur.strip()); cur = ''
    if cur.strip(): out.append(cur.strip())
    return out
def claus(s):
    out, cur = [], ''
    for ch in s:
        cur += ch
        if ch in CLAUSE_END or ch in SENT_END: out.append(cur.strip()); cur = ''
    if cur.strip(): out.append(cur.strip())
    return out

# 连接词 / 情绪词 / 清单式起句
CONN = ['因为','所以','因此','由于','虽然','但是','然而','不过','而且','并且','于是',
        '然后','接着','首先','其次','最后','总之','尽管','即使','如果','那么','可是','而是']
EMO  = ['悲伤','难过','痛苦','孤独','寂寞','高兴','开心','快乐','愤怒','生气','忧伤',
        '惆怅','失落','幸福','思念','怀念','眷恋','亲切','厌恶','害怕','无奈','心酸','感慨']
LIST_START = ['出','有','是','要','只','就','又','还','多','少','好','不']
TONE = ['罢了','而已','吗','呢','吧','啊','呀','极了']
GRAND = ['令人','不禁','深深地','无比','十分','非常','格外','愈发','不由得','油然而生','久久']

# 作者基线（上文实测）
BASE = dict(clause_mean=7.5, clause_sd=3.8, comma=6.9, period=4.7,
            conn_density=0.74, emo_hits=2, concrete_ratio=165/13.51, sent_mean=17.8)

def fingerprint(t):
    ss = sents(t)
    cc = [c for s in ss for c in claus(s) if u(c)]
    cl = [len(u(c)) for c in cc] or [0]
    sl = [len(u(s)) for s in ss] or [0]
    n = len(u(t)) or 1
    return dict(
        chars=len(u(t)), sents=len(ss), clauses=len(cc),
        sent_mean=round(st.mean(sl),1), sent_sd=round(st.pstdev(sl),1) if len(sl)>1 else 0,
        clause_mean=round(st.mean(cl),1), clause_sd=round(st.pstdev(cl),1) if len(cl)>1 else 0,
        comma=round(t.count('，')/n*100,1), period=round(t.count('。')/n*100,1),
        conn=[(w,t.count(w)) for w in CONN if w in t],
        conn_density=round(sum(t.count(w) for w in CONN)/n*100,2),
        emo=[(w,t.count(w)) for w in EMO if w in t],
        tone=[(w,t.count(w)) for w in TONE if w in t],
        grand=[(w,t.count(w)) for w in GRAND if w in t],
        list_start=sum(1 for s in ss if u(s)[:1] in LIST_START or u(s)[:2] in ['出鸭']),
        q=sum(1 for s in ss if s.rstrip().endswith(('？','?'))),
        excl=t.count('！'),
    )

def feedback(name, t, authentic=False):
    f = fingerprint(t)
    F = []   # (级别, 维度, 原文证据标准, 说明)
    # 谓词化短句节奏
    if f['clause_mean'] > BASE['clause_mean'] + 3:
        F.append(('核心','小句节奏',
                  f"小句均长 {f['clause_mean']} 字 vs 作者 {BASE['clause_mean']} 字",
                  '作者以 3~10 字小句连缀推进，你的小句被拉长，逐项陈列的节奏消失'))
    if f['clause_sd'] < BASE['clause_sd'] - 1.2:
        F.append(('重要','节奏起伏',
                  f"小句长标准差 {f['clause_sd']} vs 作者 {BASE['clause_sd']}",
                  '小句长度过于均匀，缺少作者那种短促与舒展的交替'))
    # 显性连接词
    if f['conn_density'] > BASE['conn_density'] * 1.8:
        F.append(('重要','衔接方式',
                  f"显性连接词密度 {f['conn_density']}/百字 vs 作者 {BASE['conn_density']}/百字；出现 {f['conn']}",
                  '作者几乎不写逻辑连接词，靠并置让关系自明；你补上了议论文式的胶水'))
    # 直接命名情绪
    if len(f['emo']) > 0:
        F.append(('核心','情绪表达',
                  f"出现直接情绪词 {f['emo']}；原文 1351 字中仅「高兴」2 次",
                  '作者不命名情绪，用具体名物与动作承担情感；你直接说出了感受'))
    # 清单式起句
    ratio = f['list_start'] / max(f['sents'],1)
    if ratio < 0.25:
        F.append(('重要','句法骨架',
                  f"清单式起句 {f['list_start']}/{f['sents']} 句（{ratio:.0%}）vs 作者约 30~40%",
                  '作者大量省略主语、以谓词或属项起句（系百索子／出鸭／鸭多，鸭蛋也多）；你的句子主语完整，读起来是"描述"而不是"陈列"'))
    # 夸张修饰
    if f['grand']:
        F.append(('次要','修饰习惯',
                  f"出现强调修饰 {f['grand']}",
                  '作者只在极少数处用「好看极了」这类直白感叹，不堆叠程度副词'))
    # 语气词／口语收束
    if not f['tone']:
        F.append(('次要','口语性',
                  '未出现「罢了／吗／呢／极了」一类口语收束',
                  '作者频繁以口语反问或直白感叹收束，语气是"说话"而非"作文"'))
    # 问句
    if f['q'] == 0:
        F.append(('次要','疑而未答',
                  '未出现问句；原文 76 句中有 4 处自问',
                  '作者常自问而不作答（这就能避邪吗／这有什么好看呢），用疑问句完成留白'))
    # 具体名物密度（粗测：非虚词音节占总音节）
    conc = len(re.findall(r'[鸭蛋丝线绳腕香角粽面帐钩纸毒槛符庙道士扇楣笔雄黄酒额炮硝橱壁虎苋虾腌腊铺络纽壳萤虫罗灰筷油腐卷]', t))
    if conc / max(f['chars'],1) < 0.06:
        F.append(('核心','具体性',
                  f"名物字符占比 {conc/max(f['chars'],1):.1%} vs 原文约 12%",
                  '作者每 8 个字就落在一个实物上；你的文本里抽象表述偏多，物不落地'))

    print('='*74)
    print(f'【{name}】' + ('  ← 原文原句（哨兵测试：此处任何"偏离"都是假阳性）' if authentic else ''))
    print(f'  指纹: {f["chars"]}字 {f["sents"]}句 句长{f["sent_mean"]}±{f["sent_sd"]} '
          f'小句{f["clause_mean"]}±{f["clause_sd"]} 逗{f["comma"]} 句{f["period"]} '
          f'连接{f["conn_density"]} 情绪词{len(f["emo"])} 问句{f["q"]}')
    if not F:
        print('  → 未检出偏离')
    else:
        lv = {'核心':0,'重要':1,'次要':2}
        F.sort(key=lambda x: lv[x[0]])
        cur = None
        for l, dim, ev, why in F:
            if l != cur: print(f'  [{l}问题]'); cur = l
            print(f'    - {dim}：{ev}')
            print(f'      为什么不像：{why}')
    return F, f

# ---------- 1. 用户临摹稿（AI 泛化文风：平滑、解释、连接词充足） ----------
imitation = (
"我的家乡高邮是一个水乡，因为盛产鸭子而闻名。这里出产的高邮大麻鸭是非常著名的品种，"
"由于鸭子很多，所以鸭蛋的产量也十分丰富。高邮人善于腌制鸭蛋，因此高邮咸鸭蛋逐渐出了名。"
"每当我在外地被问起籍贯时，对方听说我是高邮人，都会立刻变得肃然起敬，因为大家都知道那里出咸鸭蛋。"
"双黄鸭蛋是高邮的特产，切开之后里面有两个圆圆的蛋黄，令人感到十分惊奇。"
"我对别人总是称赞高邮鸭蛋这件事感到有些不快，仿佛我们那个贫穷的地方只出鸭蛋似的。"
"不过说实话，高邮的咸鸭蛋确实非常好，我去过很多地方，吃过很多鸭蛋，但都无法与家乡的相比，"
"这让我深深地感到，他乡的咸鸭蛋实在不值得一吃。"
)

# ---------- 2. 作者原文原句（哨兵：最"作者"的句子） ----------
sentinel = (
"系百索子。五色的丝线拧成小绳，系在手腕上。丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。"
"做香角子。丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。贴五毒。红纸剪成五毒，贴在门槛上。"
)

# ---------- 3. 我自己写的"像作者"的临摹（按实测特征刻意构造） ----------
my_imitation = (
"家乡的鸭蛋，是端午的事。挑蛋。要淡青壳的。二要样子好看。壳有白的，有淡青的。"
"有的蠢，有的秀气。挑好了，装进络子，挂在大襟的纽扣上。挂了多半天。孩子一高兴，掏出来，吃了。"
"新腌不久，只一点淡淡的咸味。白嘴吃，也可以。"
)

for nm, tx, au in [('用户临摹稿（AI 泛化文风）', imitation, False),
                   ('原文原句（哨兵）', sentinel, True),
                   ('临摹稿（按实测指纹构造）', my_imitation, False)]:
    feedback(nm, tx, au)
