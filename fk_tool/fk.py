#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk — 富兰克林写作法工具（无判断版）

设计依据：富兰克林写作工具-无判断版设计v1.0.md
核心约束（硬性，不是建议）：
  1. 本工具不做任何关于"像不像作者""写得好不好"的判断。
  2. 不调用任何模型。全部为本地机械计算，可离线运行。
  3. 提示只抽取具体名物与动作，不描述写法、不描述效果、不含修辞名称。
  4. 覆盖率只报事实（命中/未命中的词），不换算成分数、不做评价。
  5. 对照阶段强制用户自己写下"我的观察"——理解由用户完成。

用法：
  python fk.py import <原文文件> --title 标题
  python fk.py status
  python fk.py write <单元号>
  python fk.py submit <单元号>
  python fk.py compare <单元号>
  python fk.py list
"""
import os, sys, re, json, time, argparse, io, textwrap, hashlib

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state')
SCHEMA = 1

# ---------------------------------------------------------------- 基础工具

def _p(*a):
    print(*a)

def store_path():
    return os.path.join(ROOT, 'library.json')

def load_lib():
    if not os.path.exists(store_path()):
        return {'schema': SCHEMA, 'works': []}
    with open(store_path(), encoding='utf-8') as f:
        return json.load(f)

def save_lib(lib):
    os.makedirs(ROOT, exist_ok=True)
    tmp = store_path() + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(lib, f, ensure_ascii=False, indent=1)
    os.replace(tmp, store_path())

def find_work(lib, wid):
    for w in lib['works']:
        if w['id'] == wid or w['title'] == wid:
            return w
    return None

# ---------------------------------------------------------------- 切分

PUNCT = '，。！？；：、“”"（）《》…—'
SENT_END = '。！？'

def plain_len(s):
    return len(re.sub(r'[%s\s]' % re.escape(PUNCT), '', s))

def split_sentences(text):
    out, cur = [], ''
    for ch in text:
        cur += ch
        if ch in SENT_END:
            out.append(cur.strip()); cur = ''
    if cur.strip():
        out.append(cur.strip())
    return out

def split_units(text, target=150, tol=0.35):
    """按规模切训练单元。这是纯粹的规模切分，不含任何'表达动作'判断。

    规则：贪心累积句子，直到达到 target 字数；若加入下一句会超过 target*(1+tol)
    且当前已不低于 target*(1-tol)，则断句。
    """
    sents = split_sentences(text)
    units, cur, cur_len = [], [], 0
    lo, hi = target * (1 - tol), target * (1 + tol)
    for s in sents:
        L = plain_len(s)
        if cur and cur_len + L > hi and cur_len >= lo:
            units.append(''.join(cur)); cur, cur_len = [], 0
        cur.append(s); cur_len += L
    if cur:
        if units and cur_len < target * 0.5:
            units[-1] += ''.join(cur)          # 尾块过短则并入前一块
        else:
            units.append(''.join(cur))
    return units

# ---------------------------------------------------------------- 提示抽取（机械）

# 功能字
FUNC = set('的了在是我他她它们和与及或但而就不都很也还又把被从对为以之其此这那'
           '上下来去时么呢吧啊呀吗着过要会能可所因然于并且如若则把让给向从当'
           '一二三四五六七八九十百千万两有些个只种样件条张把支')

def _spans(text, lo=2, hi=4):
    """贪心片段覆盖：横跨扫描，取整段连续汉字，标记已覆盖，永不切断。

    这样抽出的每一段都必然是原文中真实存在的**完整连续子串**，
    不会出现"丝线拧成小"这类被切断的非词片段。
    不依赖词典，也不做任何语义判断。
    """
    body = re.sub(r'[%s\s\dA-Za-z]' % re.escape(PUNCT), ' ', text)
    spans = []
    for seg in body.split(' '):
        i, n = 0, len(seg)
        while i < n:
            if seg[i] in FUNC:
                i += 1; continue
            # 向前吃到功能字为止，得到一段纯实义连续串
            j = i
            while j < n and seg[j] not in FUNC:
                j += 1
            run = seg[i:j]
            k = 0
            while k < len(run):
                take = min(hi, len(run) - k)
                piece = run[k:k + take]
                if len(piece) < lo and spans:
                    break
                if len(piece) >= lo:
                    spans.append(piece)
                k += take
            i = j
    # 去重并保持首次出现顺序
    seen, out = set(), []
    for s in spans:
        if s not in seen:
            seen.add(s); out.append(s)
    return out

def keywords(text, limit=12):
    """机械抽取内容片段。只列原文中真实存在的连续子串，不含任何写法说明。"""
    spans = _spans(text)
    return spans[:limit], spans

def coverage(src, draft):
    """覆盖率：机械子串比对。只报事实，不换算成分数。"""
    all_kw = _spans(src)
    hit = [w for w in all_kw if w in draft]
    miss = [w for w in all_kw if w not in draft]
    return hit, miss

# ---------------------------------------------------------------- 展示

def rule(ch='─', n=78):
    _p(ch * n)

def wrap(s, width=34):
    return textwrap.wrap(s, width=width) or ['']

def side_by_side(src, draft, width=34):
    """并置对照：原文与用户稿逐句对齐，同屏同宽。"""
    sa, sb = split_sentences(src), split_sentences(draft)
    left, right = [], []
    for s in sa:
        left += wrap(s, width)
    # 用空行对齐两侧块数（简单实现：分别 wrap 后再按行交替输出）
    for s in sb:
        right += wrap(s, width)
    n = max(len(left), len(right))
    left += [''] * (n - len(left))
    right += [''] * (n - len(right))
    rule('=')
    _p(f'{"原　文":<{width}}│{"你的稿子":<{width}}')
    rule('=')
    for a, b in zip(left, right):
        _p(f'{a:<{width}}│{b:<{width}}')
    rule('=')

# ---------------------------------------------------------------- 命令

def cmd_import(args):
    path = args.file
    if not os.path.exists(path):
        _p(f'找不到文件：{path}'); return 1
    text = open(path, encoding='utf-8').read().strip()
    if not text:
        _p('文件是空的。'); return 1
    title = args.title or os.path.splitext(os.path.basename(path))[0]
    units = split_units(text, target=args.size)
    lib = load_lib()
    base = re.sub(r'\W+', '-', title)[:20] or 'work'
    wid = base + '-' + hashlib.md5(text.encode('utf-8')).hexdigest()[:6]
    work = {
        'id': wid, 'title': title, 'source_file': os.path.abspath(path),
        'created': time.strftime('%Y-%m-%d %H:%M:%S'),
        'chars': plain_len(text),
        'unit_target': args.size,
        'units': [{'no': i + 1, 'text': u, 'chars': plain_len(u),
                   'keywords': keywords(u, limit=12)[0],
                   'draft': None, 'submitted': None, 'submitted_at': None,
                   'observation': None, 'compared_at': None,
                   'coverage': None} for i, u in enumerate(units)],
    }
    lib['works'] = [w for w in lib['works'] if w['id'] != wid] + [work]
    save_lib(lib)
    _p(f'已导入：{title}')
    _p(f'  作品 id：{wid}')
    _p(f'  全文 {plain_len(text)} 字，切分为 {len(units)} 个训练单元：')
    for u in work['units']:
        _p(f'    单元 {u["no"]:>2}  {u["chars"]:>4} 字')
    _p('')
    _p('  注意：切分只按规模，不判断"表达动作"。若切得不合适，用 --size 调整后重新导入。')
    _p(f'  下一步：python {os.path.basename(__file__)} write {wid} 1')
    return 0

def cmd_status(args):
    lib = load_lib()
    if not lib['works']:
        _p('范文库是空的。先 import 一篇。'); return 0
    for w in lib['works']:
        done = sum(1 for u in w['units'] if u['compared_at'])
        _p(f'[{w["id"]}] {w["title"]}  {w["chars"]} 字  {len(w["units"])} 单元，已完成 {done}')
        for u in w['units']:
            if u['compared_at']:
                st = '已完成对照'
            elif u['submitted']:
                st = '已提交，待对照'
            else:
                st = '未开始'
            _p(f'    单元 {u["no"]:>2}  {u["chars"]:>4} 字  {st}')
    return 0

def _get_unit(lib, wid, no):
    w = find_work(lib, wid)
    if not w:
        _p(f'找不到作品：{wid}'); return None, None
    for u in w['units']:
        if u['no'] == no:
            return w, u
    _p(f'找不到单元 {no}（该作品共 {len(w["units"])} 个单元）')
    return None, None

def cmd_write(args):
    lib = load_lib()
    w, u = _get_unit(lib, args.work, args.unit)
    if not u: return 1
    if u['submitted'] and not args.force:
        _p('这个单元已经提交过了。为防止看到原文后再改，默认不允许覆盖。')
        _p('如确需重来，加 --force（会清除该单元的提交记录）。')
        return 1
    rule('=')
    _p(f'{w["title"]}　单元 {u["no"]}／{len(w["units"])}　{u["chars"]} 字')
    rule('=')
    _p('')
    _p('【重构提示】只列出原文中的具体名物，不含写法说明。')
    _p('')
    for i in range(0, len(u['keywords']), 6):
        _p('   ' + '　'.join(u['keywords'][i:i + 6]))
    _p('')
    _p('（提示可以不用。想凭记忆写就直接写。）')
    _p('')
    rule()
    _p('原文已被隐藏。请凭记忆重写这一段。')
    _p('写完粘贴进来，空行后输入 END 结束：')
    _p('')
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln.strip() == 'END':
            break
        lines.append(ln)
    draft = '\n'.join(lines).strip()
    if not draft:
        _p('没有收到内容，已放弃。')
        return 1
    u['draft'] = draft
    u['submitted'] = True
    u['submitted_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_lib(lib)
    _p('')
    _p(f'已收下（{plain_len(draft)} 字）。记不清的地方就空着，不必补。')
    _p('')
    _p(f'下一步：等待 {args.delay} 分钟后运行 compare，才会显示原文。')
    _p('  （延迟是富兰克林方法的核心动作，不要跳过。）')
    _p(f'  python {os.path.basename(__file__)} compare {w["id"]} {u["no"]}')
    return 0

def cmd_compare(args):
    lib = load_lib()
    w, u = _get_unit(lib, args.work, args.unit)
    if not u: return 1
    if not u['submitted']:
        _p('这个单元还没提交过稿子。先 write。'); return 1

    # 延迟强制
    elapsed = (time.time() - time.mktime(time.strptime(u['submitted_at'], '%Y-%m-%d %H:%M:%S'))) / 60.0
    wait = args.delay
    if elapsed < wait and not args.skip_delay:
        left = wait - elapsed
        _p(f'还在延迟期内，剩余 {left:.1f} 分钟。')
        _p('延迟的作用是让记忆脱离短时缓冲，这是这个方法里最关键的一步。')
        _p('如确要跳过，加 --skip-delay。')
        return 1

    src = u['text']
    draft = u['draft']
    hit, miss = coverage(src, draft)
    u['coverage'] = {'hit': hit, 'miss': miss}
    side_by_side(src, draft)
    _p('')
    _p('【具体名物】以下是机械比对结果，只列事实，不评价。')
    _p('')
    _p(f'  出现（{len(hit)}）：' + ('、'.join(hit[:40]) if hit else '（无）'))
    _p(f'  未出现（{len(miss)}）：' + ('、'.join(miss[:40]) if miss else '（无）'))
    _p('')
    _p('  未出现不等于写得不好——可能是有意省略。判断在你自己。')
    _p('')
    rule()
    _p('【我的观察】请写下你自己看到的差异。系统不会替你判断。')
    _p('看不出差别也可以，但必须写出来。输入 END 结束：')
    _p('')
    lines = []
    while True:
        try:
            ln = input()
        except EOFError:
            break
        if ln.strip() == 'END':
            break
        lines.append(ln)
    obs = '\n'.join(lines).strip()
    if not obs:
        _p('')
        _p('没有写下观察，本单元不算完成。')
        _p('（这一条是硬性的：去掉 AI 判断之后，观察就是唯一的学习动作。）')
        return 1
    u['observation'] = obs
    u['compared_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    save_lib(lib)
    _p('')
    _p('本单元完成。已记录：你的稿子、覆盖率清单、你的观察。')
    nxt = u['no'] + 1
    if nxt <= len(w['units']):
        _p(f'  下一个：python {os.path.basename(__file__)} write {w["id"]} {nxt}')
    else:
        _p('  这是最后一个单元。')
    return 0

def cmd_list(args):
    lib = load_lib()
    w = find_work(lib, args.work) if args.work else None
    if not w:
        _p('用法：list <作品id>'); return 1
    _p(f'{w["title"]}　{w["chars"]} 字　{len(w["units"])} 单元')
    rule()
    for u in w['units']:
        _p(f'单元 {u["no"]:>2}　{u["chars"]:>4} 字　'
           f'{"完成" if u["compared_at"] else ("待对照" if u["submitted"] else "未开始")}')
        if u['compared_at']:
            c = u.get('coverage') or {}
            _p(f'      名物 命中{len(c.get("hit", []))}／未出现{len(c.get("miss", []))}')
            obs = (u['observation'] or '').strip().replace('\n', ' ')
            _p(f'      我的观察：{obs[:60]}{"…" if len(obs) > 60 else ""}')
    return 0

# ---------------------------------------------------------------- 入口

def main():
    ap = argparse.ArgumentParser(description='富兰克林写作法工具（无判断版）')
    sub = ap.add_subparsers(dest='cmd')

    p = sub.add_parser('import', help='导入范文并按规模切分训练单元')
    p.add_argument('file'); p.add_argument('--title'); p.add_argument('--size', type=int, default=150)
    p.set_defaults(fn=cmd_import)

    p = sub.add_parser('status', help='查看范文库与进度'); p.set_defaults(fn=cmd_status)

    p = sub.add_parser('write', help='进入临摹：显示机械提示、隐藏原文')
    p.add_argument('work'); p.add_argument('unit', type=int)
    p.add_argument('--force', action='store_true'); p.add_argument('--delay', type=int, default=10)
    p.set_defaults(fn=cmd_write)

    p = sub.add_parser('compare', help='并置对照，并强制写下你的观察')
    p.add_argument('work'); p.add_argument('unit', type=int)
    p.add_argument('--delay', type=int, default=10); p.add_argument('--skip-delay', action='store_true')
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser('list', help='列出某篇作品的单元与观察记录')
    p.add_argument('work'); p.set_defaults(fn=cmd_list)

    args = ap.parse_args()
    if not getattr(args, 'fn', None):
        ap.print_help(); return 0
    return args.fn(args)

if __name__ == '__main__':
    sys.exit(main())
