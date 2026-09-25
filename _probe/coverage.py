# -*- coding: utf-8 -*-
"""并置对照：机械比对原文与用户稿中的具体名物，只报告事实，不作判断。
用法: python coverage.py <原文文件> <用户稿文件>
"""
import sys, re, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

STOP = set('的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那有一个'
           '上下来去时时候么呢吧啊呀吗着过要会能可所因为所以不过然后于是')

def tokens(text):
    """抽取候选具体名物：2-4 字的名词性片段 + 单字实词。
    这不是词法分析，是启发式清点，只用于列清单，不用于打分。"""
    text = re.sub(r'[，。！？；：、“”"（）《》…—\s]', ' ', text)
    # 优先多字词
    cands = set()
    for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', text):
        w = m.group(0)
        if w not in STOP and not all(c in STOP for c in w):
            cands.add(w)
    return cands

def keywords(text):
    """从原文抽出重复出现或具名性强的词作为提示/比对词表"""
    text_c = re.sub(r'[，。！？；：、“”"（）《》…—\s]', ' ', text)
    freq = {}
    for m in re.finditer(r'[\u4e00-\u9fff]{2,4}', text_c):
        w = m.group(0)
        if w in STOP: continue
        freq[w] = freq.get(w, 0) + 1
    # 具名性：出现次数高，或含专名/器物特征
    return freq

def main(src_path, draft_path):
    src = open(src_path, encoding='utf-8').read()
    draft = open(draft_path, encoding='utf-8').read()

    freq = keywords(src)
    # 原文具体名物清单：出现 >=1 且长度 >=2，按出现次数降序
    names = [w for w, c in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0])) if len(w) >= 2]

    hit, miss = [], []
    for w in names:
        (hit if w in draft else miss).append(w)

    print('=' * 70)
    print('并置对照（机械比对，仅列事实，不作判断）')
    print('=' * 70)
    print(f'原文 {len(re.sub(r"\\s", "", src))} 字   你的稿子 {len(re.sub(r"\\s", "", draft))} 字')
    print()
    print(f'原文具体名物候选 {len(names)} 个，其中你的稿子里出现 {len(hit)} 个：')
    print('  命中：' + ('、'.join(hit[:60]) if hit else '（无）'))
    if len(hit) > 60: print(f'  …… 另有 {len(hit)-60} 个')
    print()
    print(f'未出现 {len(miss)} 个：')
    print('  缺失：' + ('、'.join(miss[:60]) if miss else '（无）'))
    if len(miss) > 60: print(f'  …… 另有 {len(miss)-60} 个')
    print()
    print('-' * 70)
    print('提示用关键词（机械抽取，最多 12 个，可自行取舍）:')
    print('  ' + ' / '.join(names[:12]))
    print()
    print('※ 本工具不判断写得好坏、也不判断像不像作者。差异请自行阅读原文后判断。')

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python coverage.py <原文文件> <用户稿文件>'); sys.exit(1)
    main(sys.argv[1], sys.argv[2])
