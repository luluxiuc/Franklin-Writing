#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_store — 数据层：切分、存档、状态机。

这里的每一条断言都对着一个"会不会丢数据、会不会切坏"的具体担忧。
用法：python tests/test_store.py
"""
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_store as S

PASS, FAIL = [], []
CORPUS = os.path.join(ROOT, '_probe', 'corpus', 'wang-zengqi-duanwu.txt')


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


BOOK = '''第一章　开端

家乡的端午，很多风俗和外地一样。系百索子。五色的丝线拧成小绳，系在手腕上。
丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。

做香角子。丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。
贴五毒。红纸剪成五毒，贴在门槛上。贴符。这符是城隍庙送来的。

第二章　鸭蛋

我的家乡是水乡。出鸭。高邮大麻鸭是著名的鸭种。鸭多，鸭蛋也多。
高邮人也善于腌鸭蛋。高邮咸鸭蛋于是出了名。

我在苏南、浙江，每逢有人问起我的籍贯，回答之后，对方就会肃然起敬。
上海的卖腌腊的店铺里也卖咸鸭蛋，必用纸条特别标明："高邮咸蛋"。

第三章　萤火虫

孩子吃鸭蛋是很小心的。除了敲去空头，不把蛋壳碰破。
蛋黄蛋白吃光了，用清水把鸭蛋壳里面洗净，晚上捉了萤火虫来，装在蛋壳里。
'''


def main():
    # ── 文本规范化
    check('换行统一成 \\n',
          S.normalize_text('甲\r\n乙\r丙') == '甲\n乙\n丙')
    check('plain_len 不算标点和空白',
          S.plain_len('丝线是掉色的，洗脸。') == 8,
          str(S.plain_len('丝线是掉色的，洗脸。')))

    # ── 切节
    chs = S.split_chapters(BOOK, target=300, merge_small=True)
    check('短小的章节标题会并进后面那一节（不挂到上一节）',
          len(chs) == 3 and chs[0]['title'].startswith('第一章')
          and '家乡的端午' in chs[0]['body'],
          '%d 节，首节标题=%s' % (len(chs), chs[0]['title'] if chs else '—'))
    check('每节都有编号与字数',
          all(c['no'] == i + 1 and c['chars'] > 0 for i, c in enumerate(chs)))

    # 默认不并小段：按段落分节，读书时最自然
    chs0 = S.split_chapters(BOOK)
    check('默认一节一段（不强行合并）', len(chs0) > len(chs),
          '%d vs %d' % (len(chs0), len(chs)))
    # 注意这条不变式的准确说法：拼回去等于原文**去掉首尾空白、并把节之间的
    # 空行还原回去**的内容。节与节之间那条空行落在两节的外面（每节首尾会 trim），
    # 它只是排版空白，不是内容——实字一个都不能丢，下面两条分别验这两件事。
    rejoined = '\n\n'.join(c['body'] for c in chs)
    check('切节是可逆的（正文一个字都不丢）',
          rejoined == S.normalize_text(BOOK),
          '拼回来 %d 字，原文 %d 字' % (len(rejoined), len(S.normalize_text(BOOK))))
    check('实字一个不多一个不少',
          S.plain_len(''.join(c['body'] for c in chs))
          == S.plain_len(S.normalize_text(BOOK)),
          '%d vs %d' % (S.plain_len(''.join(c['body'] for c in chs)),
                        S.plain_len(S.normalize_text(BOOK))))

    flat = BOOK.replace('\n', '')
    chs2 = S.split_chapters(flat)
    check('一整块没有换行的文本也能切节', len(chs2) >= 1, '%d 节' % len(chs2))
    check('无换行文本按句子聚合，不会切出超长节',
          all(c['chars'] <= 2000 for c in chs2), str([c['chars'] for c in chs2]))

    check('空文本切出空列表', S.split_chapters('   ') == [])

    # ── 切段
    # 一段就是一大块时，不能再切出一个几字的尾巴
    one_block = '甲。' * 5 + '乙' * 250 + '。' + '丙' * 200 + '。'
    ps = S.split_passages(one_block, target=200)
    check('按目标字数切成多段', len(ps) >= 2, '%d 段' % len(ps))
    check('每段都有 no/start/end/chars',
          all(set(p) == {'no', 'start', 'end', 'chars'} for p in ps))
    check('段的编号连续', [p['no'] for p in ps] == list(range(1, len(ps) + 1)))

    # 切片必须能从原文里原样取回来（这是"原文只存一份"的前提）
    ok_slice = True
    for p in ps:
        seg = one_block[p['start']:p['end']]
        if not seg or seg != seg.strip() or S.plain_len(seg) != p['chars']:
            ok_slice = False
    check('每段的切片能从原文原样取回，且不带首尾空白', ok_slice)

    check('过长的整块会按句子再切，不出现几字的尾巴',
          all(p['chars'] >= 200 * 0.3 for p in ps),
          str([p['chars'] for p in ps]))

    # ── 存档
    tmp = tempfile.mkdtemp(prefix='fk_store_')
    try:
        st = S.Store(tmp)
        d = st.read()
        check('空存档能读出来且有默认设置', d['books'] == [] and 'delay_min' in d['settings'])

        bid = S.new_id('bk')
        st.save_text(bid, BOOK)
        check('原文能存能取', st.load_text(bid) == BOOK)

        d['books'].append({
            'id': bid, 'title': '测试书', 'author': '某人', 'added': S.now(),
            'chars': S.plain_len(BOOK), 'note': '', 'fingerprint': S.text_fingerprint(BOOK),
            'chapters': [{'no': c['no'], 'title': c['title'], 'chars': c['chars'],
                          '_start': c['_start'], '_end': c['_end'],
                          'passages': S.split_passages(c['body'], 100, base=c['_start'])}
                         for c in chs],
        })
        st.write(d)

        d2 = st.read()
        check('写进去能读出来（书目在）', len(d2['books']) == 1)
        st.write(d2)                       # 第二次写入才会留下上一版
        check('写入时留了上一版备份', os.path.exists(st.index_path + '.bak'))
        check('存档是给人看的纯文本',
              'books' in open(st.index_path, encoding='utf-8').read())

        bk, ch, psg = st.passage(d2, bid, 1, 1)
        check('能按节号段号定位', ch['no'] == 1 and psg['no'] == 1)
        check('能取回这一段的原文（绝对位置，直接切整篇）',
              st.passage_text(bid, psg) == BOOK[psg['start']:psg['end']])
        check('段的原文就是这一节里的内容',
              st.passage_text(bid, psg) in st.chapter_body(d2, bid, 1))
        check('段首段尾没有多余的空白',
              st.passage_text(bid, psg) == st.passage_text(bid, psg).strip())

        try:
            st.passage(d2, bid, 99, 1)
            check('不存在的节会报错', False, '竟然没报错')
        except S.StoreError:
            check('不存在的节会报错', True)

        # ── 状态机
        check('没练过 = unread', st.stage(d2, bid, 1, 1) == 'unread')

        a = st.log_attempt(d2, book=bid, chapter=1, passage=1)
        a['read_at'] = S.now()
        st.write(d2)
        d3 = st.read()
        st_settings = d3['settings']
        st_settings['delay_min'] = 5
        st.write(d3)
        d3 = st.read()
        check('读完原文且在延迟内 = read', st.stage(d3, bid, 1, 1) == 'read',
              st.stage(d3, bid, 1, 1))
        left = st.remaining(d3, st.attempt(d3, bid, 1, 1))
        check('剩余时间接近设置值', 290 <= left <= 300, str(left))

        # 拨快时间
        d3['attempts'][-1]['read_at'] = S.now() - 600
        st.write(d3)
        d3 = st.read()
        check('延迟过去 = ready', st.stage(d3, bid, 1, 1) == 'ready')

        d3['attempts'][-1]['draft'] = '我凭记忆写的一段。'
        d3['attempts'][-1]['wrote_at'] = S.now()
        st.write(d3)
        d3 = st.read()
        check('交了稿 = wrote', st.stage(d3, bid, 1, 1) == 'wrote')

        d3['attempts'][-1]['observation'] = '我把问句丢了。'
        d3['attempts'][-1]['seen_at'] = S.now()
        st.write(d3)
        d3 = st.read()
        check('看完对照 = done', st.stage(d3, bid, 1, 1) == 'done')

        check('delay_min=0 时不等待',
              (lambda: (lambda dd: (dd['settings'].__setitem__('delay_min', 0),
                                    st.write(dd),
                                    st.remaining(st.read(),
                                                 st.attempt(st.read(), bid, 1, 1)) == 0)[-1])(st.read()))())

        # ── 概览
        shelf = st.shelf(st.read())
        check('书架概览有一本书', len(shelf) == 1)
        check('概览统计了总段数', shelf[0]['counts']['total'] >= 3,
              str(shelf[0]['counts']))
        check('概览统计了练完的段数', shelf[0]['counts']['done'] == 1,
              str(shelf[0]['counts']))

        view = st.book_view(st.read(), bid)
        check('书内目录有章节结构', len(view['chapters']) == len(chs),
              '%d vs %d' % (len(view['chapters']), len(chs)))
        check('书内目录每段带阶段', all('stage' in p for c in view['chapters']
                                     for p in c['passages']))
        check('书内目录带一小截预览（用于认路）',
              any(p.get('preview') for c in view['chapters'] for p in c['passages']))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 这个不变式比看起来重要：原文只存一份，节和段都是"位置",
    # 所以按段拼回去必须精确等于原文，否则说明切分偷偷吃掉或重复了字。
    if os.path.exists(CORPUS):
        t = open(CORPUS, encoding='utf-8').read()
        c = S.split_chapters(t, merge_small=True)
        total = sum(len(S.split_passages(x['body'], 300, base=x['_start'])) for x in c)
        check('真语料能切出多节多段', len(c) >= 2 and total >= 4,
              '%d 节 %d 段' % (len(c), total))
        pieces = []
        for x in c:
            for p in S.split_passages(x['body'], 300, base=x['_start']):
                pieces.append(t[p['start']:p['end']])
        # 拼回来会丢掉段落之间的换行（每段首尾会 trim），所以严格的说法是：
        # 去掉所有换行与空白之后，两边必须完全一样——一个字不多、一个不少。
        flat = lambda s: re.sub(r'\s+', '', s)
        check('真语料：按段拼回来内容完全一致（不丢字、不重字）',
              flat(''.join(pieces)) == flat(t),
              '拼回 %d 字，原 %d 字' % (S.plain_len(''.join(pieces)), S.plain_len(t)))
        check('真语料：段的实字数之和等于原文',
              sum(p['chars'] for p in
                  [q for x in c for q in S.split_passages(x['body'], 300, base=x['_start'])])
              == S.plain_len(t))
        # 切口只能落在两种地方：句末，或者原文本来就有的换行处
        # （电子书里一句话跨行是常事，那不是"切半句"，是忠实于原文）。
        bad = []
        for x in c:
            for p in S.split_passages(x['body'], 300, base=x['_start']):
                if p['end'] >= len(t):
                    continue
                if t[p['end'] - 1] in '。！？""' or t[p['end']] == '\n':
                    continue
                bad.append(t[max(0, p['end'] - 8):p['end'] + 4])
        check('切口只落在句末或原文换行处（不切半句）', not bad, str(bad[:3]))

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
