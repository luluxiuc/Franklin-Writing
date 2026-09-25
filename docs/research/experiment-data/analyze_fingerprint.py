# -*- coding: utf-8 -*-
"""富兰克林法 v0.3 第1层（统计指纹）真实跑测
对《端午的鸭蛋》计算可复现特征。不调用任何模型。
"""
import re, json, statistics as st, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PATH = r"D:\ds harness\Fk-writing\_probe\corpus\wang-zengqi-duanwu.txt"
raw = open(PATH, encoding='utf-8').read().strip()
paras = [p for p in raw.split('\n') if p.strip()]

# 标注：袁枚引文段不属于汪曾祺行文
QUOTE_IDX = [2]
author_paras = [(i, p) for i, p in enumerate(paras) if i not in QUOTE_IDX]

SENT_END = '。！？'
CLAUSE_END = '，；：、'

def sentences(p):
    out, cur = [], ''
    for ch in p:
        if ch in '“”"':
            continue
        cur += ch
        if ch in SENT_END:
            out.append(cur.strip()); cur = ''
    if cur.strip():
        out.append(cur.strip())
    return out

def clauses(s):
    out, cur = [], ''
    for ch in s:
        cur += ch
        if ch in CLAUSE_END or ch in SENT_END:
            out.append(cur.strip()); cur = ''
    if cur.strip():
        out.append(cur.strip())
    return out

def clean(s):
    return re.sub(r'[。！？，；：、“”"（）《》…—\s]', '', s)

def stats(v):
    if not v: return {}
    return {
        'n': len(v),
        'mean': round(st.mean(v), 1),
        'median': round(st.median(v), 1),
        'sd': round(st.pstdev(v), 1),
        'min': min(v), 'max': max(v),
        'p25': round(sorted(v)[len(v)//4], 1),
        'p75': round(sorted(v)[len(v)*3//4], 1),
    }

# ---------- 句 / 小句 / 段 ----------
all_text = ''.join(p for _, p in author_paras)
all_sents = []
for i, p in author_paras:
    all_sents += [(i, s) for s in sentences(p)]
slen = [len(clean(s)) for _, s in all_sents]

all_clauses = []
for _, s in all_sents:
    all_clauses += clauses(s)
clen = [len(clean(c)) for c in all_clauses if clean(c)]

plen = [len(clean(p)) for _, p in author_paras]

report = {}
report['段落数（作者行文，不含引文段）'] = len(author_paras)
report['总字数（去标点）'] = len(clean(all_text))
report['句子数'] = len(all_sents)
report['小句数'] = len(clen)
report['句长'] = stats(slen)
report['小句长'] = stats(clen)
report['段长'] = stats(plen)

# ---------- 标点节奏 ----------
def count(ch, t=all_text): return t.count(ch)
report['标点密度/百字'] = {
    '逗号': round(count('，') / len(clean(all_text)) * 100, 1),
    '句号': round(count('。') / len(clean(all_text)) * 100, 1),
    '感叹号': count('！'),
    '问号': count('？'),
    '顿号': count('、'),
    '分号': count('；'),
    '引号对': count('“'),
    '破折号': count('—') // 2,
}
report['逗号句号比'] = round(count('，') / count('。'), 2)

# ---------- 句长分布 ----------
bins = [(0, 6), (7, 10), (11, 15), (16, 20), (21, 30), (31, 999)]
report['句长分布'] = {
    f'{a}-{b if b<999 else "+"}字': sum(1 for x in slen if a <= x <= b)
    for a, b in bins
}

# 连续短句（<=8字）最长串
run = best = 0
for x in slen:
    run = run + 1 if x <= 8 else 0
    best = max(best, run)
report['最长连续短句串(<=8字)'] = best
run2 = best2 = 0
for x in slen:
    run2 = run2 + 1 if x <= 10 else 0
    best2 = max(best2, run2)
report['最长连续短句串(<=10字)'] = best2

# ---------- 情绪词（直接命名情绪） ----------
EMO = ['悲伤','难过','痛苦','孤独','寂寞','高兴','开心','快乐','愤怒','生气',
       '忧伤','忧愁','哀伤','激动','温暖','感动','惆怅','失落','幸福','凄凉',
       '思念','怀念','眷恋','亲切','厌恶','讨厌','害怕','恐惧','无奈','心酸',
       '兴奋','失落','感慨','难过']
hits = {w: all_text.count(w) for w in set(EMO) if all_text.count(w) > 0}
report['直接命名情绪的词汇'] = hits if hits else '（0 次）'

# ---------- 连接词（显性逻辑关系） ----------
CONN = ['因为','所以','因此','由于','虽然','但是','然而','不过','而且','并且',
        '于是','然后','接着','首先','其次','最后','总之','尽管','即使','如果',
        '那么','可是','而是','不仅','无论','从而','因而']
chits = {w: all_text.count(w) for w in CONN if all_text.count(w) > 0}
report['显性连接词'] = chits
report['连接词密度/百字'] = round(sum(chits.values()) / len(clean(all_text)) * 100, 2)

# ---------- 人称代词密度 ----------
PRON = ['我','我们','你','你们','他','他们','她','它']
phits = {w: len(re.findall(w, all_text)) for w in PRON}
phits = {k: v for k, v in phits.items() if v}
tot_pron = sum(phits.values())
report['人称代词'] = phits
report['人称代词密度/百字'] = round(tot_pron / len(clean(all_text)) * 100, 2)
report['"我"占比'] = round(phits.get('我', 0) / tot_pron * 100, 1) if tot_pron else 0

# ---------- 具体名物密度（专名 + 具体名词，粗略） ----------
CONCRETE = ['鸭蛋','咸鸭蛋','高邮','丝线','小绳','手腕','香角子','粽子','香面','帐钩',
            '红纸','五毒','门槛','符','城隍庙','道士','小纸扇','门楣','纸条','朱笔',
            '雄黄','雄黄酒','额头','黄烟子','炮仗','硝药','橱柜','板壁','虎字','苋菜',
            '油爆虾','鸭','麻鸭','腌腊','店铺','双黄','络子','纽扣','蛋壳','萤火虫',
            '薄罗','石灰','筷子','红油','朱砂豆腐','豆腐','卷子']
ch2 = {w: all_text.count(w) for w in CONCRETE if all_text.count(w) > 0}
report['具体名物（出现次数>=1的种类数）'] = len(ch2)
report['具体名物总出现次数'] = sum(ch2.values())

# ---------- 留白 / 疑而未答 ----------
qs = [s for _, s in all_sents if s.rstrip().endswith('？')]
report['问句数'] = len(qs)
report['问句清单'] = [clean(s) for s in qs]
para_end_q = []
for i, p in author_paras:
    ss = sentences(p)
    if ss and ss[-1].rstrip().endswith('？'):
        para_end_q.append(i + 1)
report['以问句收束的段（段号）'] = para_end_q

# 自我承认不确定 / 记不清
UNCERTAIN = ['不知','记不清','数不出','也许','不一定','大概','好像','似乎','据说','说是','听说']
uhits = {w: all_text.count(w) for w in UNCERTAIN if all_text.count(w) > 0}
report['不确定表达'] = uhits

# 雅俗落差：雅词后接俗语
report['雅词位置'] = {w: all_text.count(w) for w in ['曾经沧海难为水','所食鸭蛋多矣','肃然起敬'] if all_text.count(w)}
print(json.dumps(report, ensure_ascii=False, indent=2))
