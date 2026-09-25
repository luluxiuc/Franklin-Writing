#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_core — 引擎测试：切分、机械抽取、覆盖率、状态机。

这里测的是"算得对不对"，不涉及服务的 HTTP 层（那在 test_server.py）。
每条断言都尽量对着真实语料，而不是编出来的假数据。

用法：python tests/test_core.py
"""
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_core as C

PASS, FAIL = [], []
CORPUS = os.path.join(ROOT, '_probe', 'corpus', 'wang-zengqi-duanwu.txt')

SAMPLE = (
    '家乡的端午，很多风俗和外地一样。系百索子。五色的丝线拧成小绳，系在手腕上。'
    '丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。做香角子。'
    '丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。贴五毒。'
    '红纸剪成五毒，贴在门槛上。贴符。这符是城隍庙送来的。'
    '城隍庙的老道士还是我的寄名干爹，他每年端午节前就派小道士送符来，还有两把小纸扇。'
    '符送来了，就贴在堂屋的门楣上。一尺来长的黄色、蓝色的纸条，上面用朱笔画些莫名其妙的道道，'
    '这就能避邪吗？喝雄黄酒。用酒和的雄黄在孩子的额头上画一个王字，这是很多地方都有的。'
)


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


def main():
    # ── 字数与切分
    check('plain_len 不算标点',
          C.plain_len('丝线是掉色的，洗脸时沾了水。') == 12,
          str(C.plain_len('丝线是掉色的，洗脸时沾了水。')))

    sents = C.split_sentences('甲。乙！丙？丁')
    check('按句号问号叹号切句', sents == ['甲。', '乙！', '丙？', '丁'], str(sents))
    cls = C.split_clauses('甲，乙。丙；丁')
    check('按逗号分号冒号切小句', cls == ['甲，', '乙。', '丙；', '丁'], str(cls))

    chunks = C.split_units(SAMPLE, target=80)
    check('按规模切段', len(chunks) >= 2, '%d 段' % len(chunks))
    check('切段后拼回来等于原文', ''.join(chunks) == SAMPLE)
    check('每段字数都在合理范围',
          all(40 <= C.plain_len(c) <= 260 for c in chunks),
          str([C.plain_len(c) for c in chunks]))
    check('切换行时段落换行不会丢（切分可逆）',
          ''.join(C.split_sentences('甲。\n乙。\n丙。')) == '甲。\n乙。\n丙。')

    # ── 抽取：机械、可复现、不切词
    rs = C.runs('五色的丝线拧成小绳，系在手腕上。')
    check('实义串按功能字切边界',
          '丝线拧成小绳' in rs and '手腕' in rs, str(rs))
    check('功能字不会出现在实义串里',
          not any(ch in r for r in rs for ch in '的了在是'),
          str([r for r in rs if any(ch in r for ch in '的了在是')]))

    sp = C.content_spans(SAMPLE)
    check('每条内容片段都是原文的真实子串', all(p in SAMPLE for p in sp),
          str([p for p in sp if p not in SAMPLE][:3]))
    check('内容片段不含单字', all(len(p) >= 2 for p in sp), str([p for p in sp if len(p) == 1]))
    check('内容片段不超过 6 字', all(len(p) <= 6 for p in sp), str([p for p in sp if len(p) > 6]))
    check('抽取可复现（两次结果一致）', C.content_spans(SAMPLE) == sp)

    # 不许出现半截词——这是之前实测踩过的坑
    bad_frag = [p for p in sp if p in ('姐姐用彩', '色丝线打', '子蠢', '定真凑足')]
    check('抽取不会切出半截词', not bad_frag, str(bad_frag))

    hx = C.select_hints(SAMPLE)
    check('提示条数不超过上限', hx['shown_count'] <= 26, str(hx['shown_count']))
    check('提示里每条都在候选集合里', all(h in set(hx['raw']) for h in hx['hints']))
    check('提示按原文出现顺序排列',
          hx['hints'] == sorted(hx['hints'], key=lambda p: SAMPLE.find(p)))
    check('提示里没有互相包含的条目',
          not any(a != b and a in b for a in hx['hints'] for b in hx['hints']),
          str([(a, b) for a in hx['hints'] for b in hx['hints'] if a != b and a in b][:3]))

    # ── 覆盖率：只报事实
    cov = C.coverage(SAMPLE, '家乡的端午，很多风俗和外地一样。系百索子。丝线拧成小绳。')
    check('覆盖率把命中与未命中分开', cov['hit_count'] > 0 and cov['miss_count'] > 0)
    check('命中数 + 未命中数 = 总数',
          cov['hit_count'] + cov['miss_count'] == cov['total_count'])
    check('命中的确实出现在稿子里', all(h in '家乡的端午，很多风俗和外地一样。系百索子。丝线拧成小绳。'
                                     for h in cov['hit']))
    check('未命中的确实不在稿子里', all(h not in '家乡的端午，很多风俗和外地一样。系百索子。丝线拧成小绳。'
                                     for h in cov['miss']))
    check('覆盖率没有任何比率字段',
          not any(k in cov for k in ('rate', 'ratio', 'percent', 'score', 'pct')))

    # ── 骨架
    go = C.guide_outline(SAMPLE)
    check('骨架句数与切句一致', go['sentence_count'] == len(C.split_sentences(SAMPLE)))
    check('骨架不带任何原文文字',
          not any('家乡' in str(r) or '丝线' in str(r) for r in go['rows']))

    # ── 规模统计
    ds = C.describe(SAMPLE)
    check('规模统计给出句数与小句数',
          ds['sentences'] == len(C.split_sentences(SAMPLE)) and ds['clauses'] > ds['sentences'])
    check('规模统计答对了问号数（这段有 1 个）', ds['questions'] == 1, str(ds['questions']))

    # ── 泄露自检
    check('find_leak 抓得住整段泄露', bool(C.find_leak(SAMPLE, {'x': SAMPLE})))
    # 先造一段确定 8 字以上的连续片段（去标点后），再验泄露
    probe = SAMPLE[:0]
    for ch in SAMPLE:
        if ch not in C.PUNCT:
            probe += ch
        if len(probe) >= 9:
            break
    check('find_leak 抓得住 9 字片段',
          bool(C.find_leak(SAMPLE, {'x': probe})), '探针=%r' % probe)
    check('find_leak 不误报', not C.find_leak(SAMPLE, {'x': '我今天没有写任何和原文一样的话。'}))
    check('find_leak 不看标点差异',
          bool(C.find_leak(SAMPLE, {'x': C.plain_len(SAMPLE) and SAMPLE[5:20].replace('，', '')})))

    # ── 状态机
    tmp = tempfile.mkdtemp(prefix='fk_coretest_')
    try:
        store = C.Store(tmp)
        # 状态机要用够长的文本，才切得出多个单元；有真语料就用真语料
        long_text = open(CORPUS, encoding='utf-8').read().strip() if os.path.exists(CORPUS) \
            else SAMPLE * 4
        r = C.import_text(store, long_text, '测试用', 150, author='某人')
        wid = r['work']['id']
        data = store.read()
        w = data['works'][0]
        check('状态机用的文本切出了多个单元', len(w['units']) >= 2,
              '%d 个' % len(w['units']))
        u1, u2 = w['units'][0], w['units'][1]

        check('导入后单元状态都是 todo',
              all(store.status(data, u) == 'todo' for u in w['units']))
        check('原文被单独存成文件', C.load_source(store, wid) == long_text)
        check('原文按单元切回来和切分一致',
              C.source_of_unit(store, wid, u1) == C.split_units(long_text, 150)[0])

        # 提交 → 等待 → 到期 → 对照 → 观察
        C.submit(store, wid, u1['id'], '家乡的端午，风俗和外地一样。系百索子。',
                 used_hint=False, used_guide=False, elapsed_sec=200)
        data = store.read()
        check('提交后进入 waiting', store.status(data, u1) == 'waiting')
        check('延迟剩余时间接近设置值',
              590 < store.remaining(data, store.attempt(data, u1['id'])) <= 600)

        try:
            C.start_compare(store, wid, u1['id'])
            check('延迟内拒绝打开原文', False, '竟然放行')
        except C.FkError as e:
            check('延迟内拒绝打开原文', e.code == 423, str(e.code))

        # 拨快时间
        data = store.read()
        store.attempt(data, u1['id'])['submitted_at'] = time.time() - 3600
        store.write(data)
        data = store.read()
        check('到期后状态变为 ready', store.status(data, u1) == 'ready')

        cv = C.start_compare(store, wid, u1['id'])
        check('对照返回原文与稿子', cv['source'] == C.split_units(long_text, 150)[0]
              and '系百索子' in cv['draft'])
        check('对照带了观察问题', len(cv['prompts']) >= 5)

        try:
            C.save_observation(store, wid, u1['id'], '  ')
            check('空观察被拒绝', False, '竟然接受')
        except C.FkError:
            check('空观察被拒绝', True)

        C.save_observation(store, wid, u1['id'], '我把问句丢了。')
        data = store.read()
        check('写下观察后状态变为 done', store.status(data, u1) == 'done')
        a = store.attempt(data, u1['id'])
        check('完成时落了命中与未命中清单',
              isinstance(a['hit'], list) and isinstance(a['miss'], list))

        try:
            C.submit(store, wid, u1['id'], '我想改一改', False, False, None)
            check('完成后拒绝收新稿', False, '竟然接受')
        except C.FkError:
            check('完成后拒绝收新稿', True)

        try:
            C.resplit(store, wid, 300)
            check('有稿子时拒绝重切', False, '竟然接受')
        except C.FkError:
            check('有稿子时拒绝重切', True)

        # 未写过的单元可以重切
        tmp2 = tempfile.mkdtemp(prefix='fk_coretest2_')
        try:
            s2 = C.Store(tmp2)
            r2 = C.import_text(s2, SAMPLE, '测试用2', 100)
            w2 = s2.read()['works'][0]
            n_before = len(w2['units'])
            r3 = C.resplit(s2, w2['id'], 300)
            check('没写过时可以重切', len(r3['work']['units']) < n_before,
                  '%d → %d' % (n_before, len(r3['work']['units'])))
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

        # 进度只记动作
        p = store.progress(store.read(), w)
        check('进度里有"没用提示"的计数', 'no_hint' in p)
        check('进度里没有任何能力/水平字段',
              not any(k in p for k in ('score', 'level', 'ability', 'accuracy')))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ── 真语料回归：汪曾祺那篇的规模
    if os.path.exists(CORPUS):
        t = open(CORPUS, encoding='utf-8').read().strip()
        chunks = C.split_units(t, 150)
        check('真语料能切成 5 段以上', len(chunks) >= 5, '%d 段' % len(chunks))
        check('真语料切段后拼回原文', ''.join(chunks) == t)
        ds = C.describe(t)
        check('真语料句数在合理范围', 60 <= ds['sentences'] <= 90, str(ds['sentences']))
        hint_all = [C.select_hints(c) for c in chunks]
        check('每段至少能抽出一条提示',
              all(h['shown_count'] >= 1 for h in hint_all),
              str([h['shown_count'] for h in hint_all]))

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
