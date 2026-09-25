#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest — 把 fk_core 的 R1–R8 硬性约束在**真实存档**上核验一遍。

这不是功能测试（那些在 test_core.py），这是约束测试：
它检查工具没有偷偷变成"会评价的东西"。

用法：python tests/selftest.py [存档目录]
退出码 0 = 全部通过。
"""
import json
import os
import re
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'app'))
sys.path.insert(0, os.path.join(HERE, '..'))

import fk_core as C

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


SAMPLE = (
    '家乡的端午，很多风俗和外地一样。系百索子。五色的丝线拧成小绳，系在手腕上。'
    '丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。做香角子。'
    '丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。贴五毒。'
    '红纸剪成五毒，贴在门槛上。贴符。这符是城隍庙送来的。'
    '城隍庙的老道士还是我的寄名干爹，他每年端午节前就派小道士送符来，还有两把小纸扇。'
    '符送来了，就贴在堂屋的门楣上。一尺来长的黄色、蓝色的纸条，上面用朱笔画些莫名其妙的道道，'
    '这就能避邪吗？喝雄黄酒。用酒和的雄黄在孩子的额头上画一个王字，这是很多地方都有的。'
    '有一个风俗不知别处有不：放黄烟子。黄烟子是大小如北方的麻雷子的炮仗，'
    '只是里面灌的不是硝药，而是雄黄。点着后不响，只是冒出一股黄烟，能冒好一会。'
    '把点着的黄烟子丢在橱柜下面，说是可以熏五毒。小孩子点了黄烟子，'
    '常把它的一头抵在板壁上写虎字。写黄烟虎字笔画不能断，'
    '所以我们那里的孩子都会写草书的"一笔虎"。'
)


def build_store(root):
    """造一份真实存档：一个单元完成、一个单元在等待期。"""
    store = C.Store(root)
    r = C.import_text(store, SAMPLE, title='约束测试用', unit_size=100, author='测试')
    wid = r['work']['id']
    data = store.read()
    u1 = data['works'][0]['units'][0]
    u2 = data['works'][0]['units'][1] if len(data['works'][0]['units']) > 1 else None

    C.submit(store, wid, u1['id'], '家乡的端午，风俗和外地一样。系百索子，五色的丝线拧成小绳，'
                                   '系在手腕上。做香角子，挂在帐钩上。贴五毒，贴在门槛上。'
                                   '贴符，这符是城隍庙送来的。喝雄黄酒。',
             used_hint=True, used_guide=True, elapsed_sec=420)
    # 把提交时间往前推，让它过了延迟
    data = store.read()
    a = store.attempt(data, u1['id'])
    a['submitted_at'] = time.time() - 3600
    store.write(data)
    C.start_compare(store, wid, u1['id'])
    C.save_observation(store, wid, u1['id'], '我把"莫名其妙"那句问句丢了。原文短句多。')

    if u2:
        C.submit(store, wid, u2['id'], '我的家乡是水乡，出鸭。高邮大麻鸭是著名的鸭种。',
                 used_hint=False, used_guide=False, elapsed_sec=300)
    return store, wid


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else None
    tmp = None
    if not root:
        tmp = tempfile.mkdtemp(prefix='fk_selftest_')
        root = tmp
    store, wid = build_store(root)
    data = store.read()

    print('\n存档目录：%s' % root)
    print('存档文件：%s\n' % store.path)

    # ---- R1：全库不得存在任何评价性字段
    blob = json.dumps(data, ensure_ascii=False)
    bad = [k for k in C.FORBIDDEN_KEYS if k.lower() in blob.lower()]
    check('R1 存档中不含评价性字段', not bad, '发现：%s' % bad)

    keys = set()
    for a in data['attempts']:
        keys |= set(a.keys())
    check('R1 稿件记录的字段全在允许清单内', keys <= C.ALLOWED_ATTEMPT_KEYS,
          '越界字段：%s' % sorted(keys - C.ALLOWED_ATTEMPT_KEYS))

    # ---- R1 续：源码里不得出现评价词
    src = open(os.path.join(HERE, '..', 'app', 'fk_core.py'), encoding='utf-8').read()
    code = re.sub(r'"""(?:.|\n)*?"""', '', src)          # 去掉文档字符串
    code = re.sub(r'#.*', '', code)
    # FORBIDDEN_KEYS 这张表本身列出违禁词，是防御清单，不算违规
    code = re.sub(r'FORBIDDEN_KEYS\s*=\s*\((?:.|\n)*?\n\)', '', code)
    hits = [w for w in ('得分', '评分', '分数', '相似度', '保真度', '建议改',
                        '写得好', '写得差', '更像作者', '不像作者') if w in code]
    check('R1 引擎代码中不含评价性用语', not hits, '发现：%s' % hits)

    # ---- R2：不得联网、不得调用模型
    net = [w for w in ('urllib', 'requests', 'http.client', 'socket', 'openai',
                       'anthropic', 'api_key', 'model=') if w in code]
    check('R2 引擎不联网、不调用模型', not net, '发现：%s' % net)
    imports = set(re.findall(r'^\s*(?:import|from)\s+([a-zA-Z_][\w.]*)', src, re.M))
    allowed = {'collections', 'hashlib', 'json', 'os', 're', 'time', 'uuid',
               'http.server', 'http', 'socketserver', 'mimetypes', 'webbrowser',
               'threading', 'urllib.parse', 'argparse', 'sys', 'io', 'typing',
               '__future__', 'string', 'shutil', 'tempfile', 'subprocess', 'pathlib',
               'datetime', 'random', 'math', 'statistics', 'textwrap', 'glob', 'csv'}
    outside = sorted(i for i in imports if i.split('.')[0] not in
                     {a.split('.')[0] for a in allowed})
    check('R2 引擎只用标准库', not outside, '第三方：%s' % outside)

    # ---- R3：提示必须是原文的连续子串，且不含标点/写法词
    all_ok = True
    for w in data['works']:
        for u in w['units']:
            src_unit = C.source_of_unit(store, w['id'], u)
            for h in u['hint']:
                if h not in src_unit:
                    all_ok = False
    check('R3 每条提示都是原文的真实连续子串', all_ok)

    guide_words = ('短句', '长句', '节奏', '留白', '白描', '修辞', '比喻', '排比',
                   '口语化', '文风', '语气', '效果', '手法', '技巧', '应该', '建议')
    leaked = []
    for w in data['works']:
        for u in w['units']:
            leaked += [h for h in u['hint'] if any(g in h for g in guide_words)]
    check('R3 提示中不含写法/修辞/建议类词', not leaked, '发现：%s' % leaked)

    punct_leak = []
    for w in data['works']:
        for u in w['units']:
            punct_leak += [h for h in u['hint'] if any(c in C.PUNCT for c in h)]
    check('R3 提示中不含标点（即不含成句的措辞）', not punct_leak, '发现：%s' % punct_leak)

    # ---- R4：覆盖率只报事实，不出现比率或等级
    cov_fields = set()
    for a in data['attempts']:
        if a.get('hit') is not None:
            cov_fields |= {'hit', 'miss'}
    check('R4 覆盖率只落盘命中/未命中清单', cov_fields <= {'hit', 'miss'}, str(cov_fields))
    probe = C.coverage('丝线系在手腕上，红纸剪成五毒。', '丝线系在手腕上。')
    check('R4 覆盖率结果里没有任何比率字段',
          not any(k in probe for k in ('rate', 'ratio', 'score', 'percent', 'pct')),
          str(sorted(probe.keys())))

    # ---- R5：没有观察就不算完成
    done = [a for a in data['attempts'] if a.get('compared_at')]
    check('R5 每个已完成单元都有非空观察',
          all((a.get('observation') or '').strip() for a in done))

    data2 = store.read()
    u_open = None
    for w in data2['works']:
        for u in w['units']:
            a = store.attempt(data2, u['id'])
            if a and not a.get('compared_at'):
                u_open = (w['id'], u['id'])
    if u_open:
        try:
            C.save_observation(store, u_open[0], u_open[1], '   ')
            check('R5 空观察被拒绝', False, '竟然接受了')
        except C.FkError:
            check('R5 空观察被拒绝', True)

    # ---- R6：延迟期内不得返回原文
    if u_open:
        wid2, uid2 = u_open
        data3 = store.read()
        a = store.attempt(data3, uid2)
        left = store.remaining(data3, a)
        if left > 0:
            try:
                C.start_compare(store, wid2, uid2)
                check('R6 延迟期内拒绝打开原文', False, '竟然放行了')
            except C.FkError as e:
                check('R6 延迟期内拒绝打开原文', e.code == 423, '错误码 %s' % e.code)
            # 单元列表视图里不得带任何原文片段
            ws = C.workspace(store)
            s = json.dumps(ws, ensure_ascii=False)
            _, uu = store.locate(store.read(), wid2, uid2)
            src_unit = C.source_of_unit(store, wid2, uu)
            first_sentence = C.split_sentences(src_unit)[0]
            check('R6 等待期内的单元列表不泄露原文',
                  first_sentence not in s and src_unit[:12] not in s)
        else:
            check('R6 延迟期内拒绝打开原文', True, '（本次没有处于等待期的单元，跳过）')

    # ---- R6 续：等待期内的单元视图不得带原文
    print('\n  · 逐个接口检查原文泄露：')
    for w in data['works']:
        for u in w['units']:
            a = store.attempt(data, u['id'])
            st = store.status(data, u)
            if st in ('todo', 'waiting'):
                payload = json.dumps(
                    {'unit': {'id': u['id'], 'no': u['no'], 'chars': u['chars'],
                              'hint': u['hint'], 'status': st},
                     'attempt': {k: v for k, v in (a or {}).items() if k != 'draft'}},
                    ensure_ascii=False)
                _, uu = store.locate(data, w['id'], u['id'])
                src_unit = C.source_of_unit(store, w['id'], uu)
                sents = C.split_sentences(src_unit)
                leaked_s = [s for s in sents if C.plain_len(s) > 8 and s in payload]
                check('    单元 %s（%s）不泄露原文' % (u['no'], st), not leaked_s,
                      str(leaked_s[:2]))

    # ---- R7：提交后不给回头改稿
    if u_open:
        wid2, uid2 = u_open
        try:
            data4 = store.read()
            a = store.attempt(data4, uid2)
            if a.get('compared_at'):
                pass
        except Exception:
            pass
    data5 = store.read()
    for w in data5['works']:
        for u in w['units']:
            a = store.attempt(data5, u['id'])
            if a and a.get('compared_at'):
                try:
                    C.submit(store, w['id'], u['id'], '想改一改', False, False, None)
                    check('R7 已完成对照的单元拒绝收回新稿', False, '竟然收下了')
                except C.FkError:
                    check('R7 已完成对照的单元拒绝收回新稿', True)
                break
        else:
            continue
        break

    # ---- R8：档案不做归纳
    ws = C.workspace(store)
    s = json.dumps(ws, ensure_ascii=False)
    banned = ('习惯性', '你总是', '你的弱项', '你应该', '建议你', '倾向于', '说明你',
              '平均水平', '优于', '落后')
    hit8 = [b for b in banned if b in s]
    check('R8 档案输出里没有归纳性结论', not hit8, '发现：%s' % hit8)

    # ---- 通例：工具不得为"用户稿子"生成任何文字
    check('R0 引擎中不存在生成用户稿内容的代码路径',
          not re.search(r'(def\s+\w*(generate|rewrite|suggest|fix)\w*\s*\()', code))

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    if tmp:
        print('（临时存档：%s）' % tmp)
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
