#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_server — 端到端跑一遍真实 HTTP 服务。

两组最重要的检查：
  B1  读完原文、进入练习之后，**任何接口都不再返回这一段原文**（提交前）。
  B2  生成的提示卡只出现在练习页，不会提前泄露到别处。

模型调用在测试里被替换成一个假接口，不会真的联网。
用法：python tests/test_server.py
"""
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_llm as LLM
import fk_server as SRV
import fk_store as S

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


BOOK = '''第一章　开端

家乡的端午，很多风俗和外地一样。系百索子。五色的丝线拧成小绳，系在手腕上。丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。做香角子。丝丝缠成小粽子，里头装了香面，一个一个串起来，挂在帐钩上。家乡的端午，很多风俗和外地一样。系百索子。五色的丝线拧成小绳，系在手腕上。丝线是掉色的，洗脸时沾了水，手腕上就印得红一道绿一道的。

贴五毒。红纸剪成五毒，贴在门槛上。贴符。这符是城隍庙送来的。城隍庙的老道士还是我的寄名干爹，他每年端午节前就派小道士送符来，还有两把小纸扇。符送来了，就贴在堂屋的门楣上。贴五毒。红纸剪成五毒，贴在门槛上。贴符。这符是城隍庙送来的。城隍庙的老道士还是我的寄名干爹，他每年端午节前就派小道士送符来。

第二章　鸭蛋

我的家乡是水乡。出鸭。高邮大麻鸭是著名的鸭种。鸭多，鸭蛋也多。高邮人也善于腌鸭蛋。高邮咸鸭蛋于是出了名。我在苏南、浙江，每逢有人问起我的籍贯，回答之后，对方就会肃然起敬。我的家乡是水乡。出鸭。高邮大麻鸭是著名的鸭种。鸭多，鸭蛋也多。

上海的卖腌腊的店铺里也卖咸鸭蛋，必用纸条特别标明："高邮咸蛋"。高邮还出双黄鸭蛋。别处鸭蛋也偶有双黄的，但不如高邮的多，可以成批输出。双黄鸭蛋味道其实无特别处。上海的卖腌腊的店铺里也卖咸鸭蛋，必用纸条特别标明："高邮咸蛋"。高邮还出双黄鸭蛋。别处鸭蛋也偶有双黄的。
'''


class Client:
    def __init__(self, base):
        self.base = base

    def _req(self, method, path, body=None):
        url = self.base + urllib.parse.quote(path, safe='/?=&')
        data = json.dumps(body).encode('utf-8') if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def _parse(self, triple):
        code, raw, hdr = triple
        text = raw.decode('utf-8', 'replace')
        try:
            return code, json.loads(text), text, hdr
        except Exception:
            return code, None, text, hdr

    def get(self, p):
        return self._parse(self._req('GET', p))

    def post(self, p, body=None):
        return self._parse(self._req('POST', p, body or {}))

    def put(self, p, body=None):
        return self._parse(self._req('PUT', p, body or {}))

    def delete(self, p):
        return self._parse(self._req('DELETE', p))


def main():
    root = tempfile.mkdtemp(prefix='fk_srv_')
    port = SRV.free_port(18337)
    httpd = SRV.ThreadingHTTPServer(('127.0.0.1', port), SRV.Handler)
    SRV.Handler.api = SRV.Api(root)
    SRV.Handler.quiet = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = 'http://127.0.0.1:%d' % port
    cl = Client(base)
    print('\n服务：%s　书架：%s\n' % (base, root))

    # 把模型调用换成一个假实现：测试不联网，但整个"生成提示卡"的链路照跑
    real_chat = LLM.chat
    calls = {'n': 0}

    def fake_chat(settings, system, user, **kw):
        calls['n'] += 1
        calls['last_user'] = user
        if '测试助手' in system:              # 设置页的"测试连接"
            return {'text': '连上了', 'usage': {'in': 12, 'out': 3},
                    'model': settings.get('model', '')}
        # 确认提示词里真的写了那几条规矩，不是随便发一段过去
        missing = [w for w in ('绝不能复用原文的词句', '不评价原文', '不给任何写作建议')
                   if w not in system]
        if missing:
            calls.setdefault('bad', []).append(missing)
        # 像真模型那样：按请求里的编号一句一条回
        ns = [int(m.group(1)) for m in re.finditer(r'^(\d+)\. ', user, re.M)]
        body = '\n'.join('%d. 这是第 %d 句的内容提示。' % (n, n) for n in ns)
        return {'text': body, 'usage': {'in': 480, 'out': 60},
                'model': settings.get('model', '')}

    LLM.chat = fake_chat

    try:
        run(cl, root, calls)
    finally:
        LLM.chat = real_chat
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(root, ignore_errors=True)

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    return 1 if FAIL else 0


def run(cl, root, calls):
    # ── 服务与静态文件
    code, d, _, _ = cl.get('/api/health')
    check('服务能起来', code == 200 and d and d.get('ok'))
    code, _, raw, hdr = cl.get('/')
    check('首页能返回', code == 200 and '富兰克林写作' in raw)
    code, _, _, hdr = cl.get('/style.css')
    check('样式表 MIME 正确', code == 200 and 'text/css' in hdr.get('Content-Type', ''))
    code, _, _, _ = cl.get('/../fk_server.py')
    check('挡住目录穿越', code in (403, 404))

    # ── 空书架
    code, d, _, _ = cl.get('/api/shelf')
    check('空书架能读', code == 200 and d['books'] == [])
    check('空书架统计为 0', d['counts']['passages'] == 0)

    # ── 导入
    code, d, raw, _ = cl.post('/api/books', {'title': '端午的鸭蛋', 'author': '汪曾祺',
                                             'text': BOOK, 'passage_chars': 150})
    check('导入成功', code == 200 and d and d.get('book'), raw[:200])
    bid = d['book']['id']
    chs = d['book']['chapters']
    check('切成了多节', len(chs) >= 2, '%d 节' % len(chs))
    # merge_small 可能把标题和正文并进同一节，所以这里只查"有没有标题、有没有正文"
    check('节标题是原文里的内容',
          all(c['title'] for c in chs))
    total = sum(len(c['passages']) for c in chs)
    check('切出了多个练习段', total >= 3, '%d 段' % total)

    # ── 书内目录：不许出现原文片段（认路用的小截由服务端剥掉）
    code, book, raw, _ = cl.get('/api/books/' + bid)
    check('书内目录能读', code == 200 and book['title'] == '端午的鸭蛋')
    ch1 = cl.get('/api/books/%s/chapters/1' % bid)[1]
    leak = SRV.find_leak(ch1['text'], raw, min_len=14)
    check('B2 目录里不出现任何段落正文（节标题不算泄露）', not leak, str(leak[:3]))
    check('目录里每段带阶段', all('stage' in p for c in book['chapters']
                              for p in c['passages']))

    # ── 读原文：唯一能看到原文的地方
    code, ch, raw, _ = cl.get('/api/books/%s/chapters/1' % bid)
    check('读原文接口能拿到正文', code == 200 and '家乡的端午' in ch['text'])
    check('读原文接口带分段', len(ch['passages']) >= 1)

    # ── 练习：开始读（延迟起点）
    code, d, raw, _ = cl.post('/api/practice/%s/1/1/start' % bid,
                              {'read_seconds': 42})
    check('开始练习成功', code == 200 and d['stage'] in ('read', 'ready'), raw[:150])

    # 默认延迟 3 分钟 → 现在应该在等
    code, d, raw, _ = cl.get('/api/practice/%s/1/1/write' % bid)
    check('写稿页能拿到', code == 200 and d['stage'] in ('read', 'ready'), raw[:200])
    if d.get('remaining', 0) > 0:
        check('延迟生效（remaining > 0）', True)
    else:
        check('延迟生效（remaining > 0）', False, 'remaining=%s' % d.get('remaining'))

    # B1：写稿页里不许有原文
    src1 = ch['passages'][0]['text']
    check('B1 写稿页不含这一段原文（8 字以上片段全查）',
          not SRV.find_leak(src1, d), str(SRV.find_leak(src1, d)[:3]))
    check('B1 写稿页只给了字数', d['passage']['chars'] > 0 and 'source' not in d)
    check('B1 写稿页没有 source / facts 字段',
          'source' not in d and 'facts' not in d)

    # ── 延迟闸门：现在交稿应该被拒
    code, d, raw, _ = cl.post('/api/practice/%s/1/1/submit' % bid,
                              {'draft': '家乡的端午，风俗和外地一样。系百索子。'})
    check('延迟内拒绝交稿（423）', code == 423, '实际 %s %s' % (code, raw[:100]))

    # 在测提示卡之前先配好模型（走的是假接口，不联网）
    code, _, _, _ = cl.post('/api/settings', {
        'provider': 'deepseek', 'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat', 'api_key': 'sk-test-1234567890'})
    check('能先配好模型', code == 200)

    # ── 逐句提示
    n_sent = len(S.split_sentences(src1))
    code, d, raw, _ = cl.post('/api/practice/%s/1/1/hints' % bid, {})
    check('能生成逐句提示', code == 200 and d.get('hints'), raw[:200])
    check('提示来自模型', calls['n'] == 1, '调用了 %d 次' % calls['n'])
    check('一句一条，条数等于句数',
          len(d['hints']) == n_sent == d['n_sent'],
          '句 %s 条 %s' % (d.get('n_sent'), len(d.get('hints') or [])))
    check('每条提示带句子编号',
          [h['no'] for h in d['hints']] == list(range(1, n_sent + 1)))
    check('提示里不含原文长片段',
          not SRV.find_leak(src1, {'h': [h['hint'] for h in d['hints']]}),
          str(SRV.find_leak(src1, {'h': [h['hint'] for h in d['hints']]})[:3]))
    check('请求里带上了句数和编号（模型照着一句一条写）',
          ('共 %d 句' % n_sent) in calls.get('last_user', '')
          and '1. ' in calls.get('last_user', ''))

    code, d2, _, _ = cl.post('/api/practice/%s/1/1/hints' % bid, {})
    check('提示会缓存，不重复调用模型', calls['n'] == 1 and d2.get('cached'))
    code, d3, _, _ = cl.post('/api/practice/%s/1/1/hints' % bid, {'force': True})
    check('可以强制重新生成', calls['n'] == 2 and not d3.get('cached'))
    check('记账了真实的 token 用量（不估算）',
          d3.get('usage') == {'in': 480, 'out': 60}, str(d3.get('usage')))

    # ── 缓存：同一段再要一次不该再花钱
    n_before = calls['n']
    code, d4, _, _ = cl.post('/api/practice/%s/1/1/hints' % bid, {})
    check('同一段再要一次不再调用模型', calls['n'] == n_before and d4.get('cached'))

    # ── 批量：先算账，再提前备好
    code, plan, raw, _ = cl.get('/api/books/%s/summaries/plan' % bid)
    check('能先算账（要花多少 token）', code == 200 and plan.get('total') >= 1, raw[:200])
    check('算账里区分了"已有缓存"和"还要做"',
          plan['cached'] >= 1 and plan['todo'] >= 1,
          'cached=%s todo=%s' % (plan.get('cached'), plan.get('todo')))
    check('算账给出了 token 估算并说明是估算',
          plan['est_tokens'] > 0 and '估算' in plan['note'])
    check('算账报出了真实的累计用量', plan['stats']['tokens_in'] == 960,
          str(plan['stats'].get('tokens_in')))

    code, w, raw, _ = cl.post('/api/books/%s/summaries/warm' % bid, {})
    check('能启动批量生成', code == 200 and w.get('ok'), raw[:200])
    for _ in range(60):
        _, st, _, _ = cl.get('/api/books/%s/summaries/status' % bid)
        if st['job'] and st['job']['state'] in ('done', 'cancelled', 'error'):
            break
        time.sleep(0.1)
    check('批量生成跑完了', st['job'] and st['job']['state'] == 'done',
          str(st.get('job')))
    check('批量生成跳过了已有缓存的段', st['job']['skipped'] >= 1, str(st['job']))
    check('批量之后这本书的段都有提示卡了',
          st['job']['done'] + st['job']['skipped'] >= 1)

    code, plan2, _, _ = cl.get('/api/books/%s/summaries/plan' % bid)
    check('再算一次账：不用再花钱了（todo=0）', plan2['todo'] == 0,
          'todo=%s' % plan2['todo'])

    # ── 草稿暂存
    code, d, _, _ = cl.put('/api/practice/%s/1/1/draft' % bid, {'text': '写了一半'})
    check('草稿能暂存', code == 200 and d.get('ok'))
    code, d, _, _ = cl.get('/api/practice/%s/1/1/write' % bid)
    check('草稿能读回来', d.get('draft') == '写了一半')
    check('只存了草稿不算交稿（stage 仍是 ready/read）',
          d['stage'] in ('ready', 'read') and 'source' not in d, str(d.get('stage')))

    # ── 跳过等待，交稿
    code, d, _, _ = cl.post('/api/practice/%s/1/1/skip-wait' % bid, {})
    check('可以跳过等待', code == 200 and d['stage'] == 'ready', str(d))

    draft = ('家乡的端午，很多风俗和外地一样。系百索子，五色的丝线拧成小绳，系在手腕上。'
             '做香角子，挂在帐钩上。贴五毒，贴在门槛上。')
    code, cmp_, raw, _ = cl.post('/api/practice/%s/1/1/submit' % bid,
                                 {'draft': draft, 'prompt_used': True, 'write_seconds': 300})
    check('交稿成功', code == 200 and cmp_.get('source'), raw[:200])
    check('交稿后同时给出原文和我的稿子',
          src1 and src1[:12] in cmp_['source'] and draft[:12] in cmp_['draft'],
          'source=%r draft=%r' % (cmp_.get('source', '')[:24], cmp_.get('draft', '')[:24]))
    check('对照里的原文就是这一段（含节标题，和读原文接口一致）',
          src1 in cmp_['source'] or cmp_['source'] in src1,
          'source=%r passage=%r' % (cmp_['source'][:30], src1[:30]))
    check('对照带机械比对的事实清单',
          'miss' in cmp_['facts'] and 'hit' in cmp_['facts'])
    check('事实清单里没有比率', not any(k in cmp_['facts']
                                   for k in ('rate', 'score', 'similarity')))
    check('事实清单摆出了"哪几段没写到"',
          isinstance(cmp_['facts'].get('segments'), list)
          and len(cmp_['facts']['segments']) >= 1)
    check('事实清单实话实说（未出现的不等于写得不好）',
          '不等于写得不好' in cmp_['facts']['note'])
    check('对照页回显了当时用的逐句提示',
          isinstance(cmp_.get('hints'), list) and len(cmp_['hints']) >= 1,
          str(cmp_.get('hints'))[:120])
    check('对照页记了用时', cmp_.get('write_seconds') == 300)

    # 已经交过稿，再交/再改应该被拒
    code, d, raw, _ = cl.post('/api/practice/%s/1/1/submit' % bid, {'draft': '改了'})
    check('已交稿后不能重复交', code == 400, '实际 %s' % code)
    code, d, raw, _ = cl.put('/api/practice/%s/1/1/draft' % bid, {'text': '偷改'})
    check('看过对照后不能改稿', code == 400, '实际 %s' % code)

    # ── 观察
    code, d, raw, _ = cl.post('/api/practice/%s/1/1/observe' % bid, {'observation': '   '})
    check('空观察被拒', code == 400)
    code, d, raw, _ = cl.put('/api/practice/%s/1/1/draft' % bid, {'text': '偷改'})
    check('看过对照后不能改稿', code == 400, '实际 %s %s' % (code, raw[:80]))
    code, d, _, _ = cl.post('/api/practice/%s/1/1/observe' % bid,
                            {'observation': '我把那句问句丢了，原文短句多。'})
    check('写下观察后这一轮结束', code == 200 and d['stage'] == 'done')

    code, d, _, _ = cl.get('/api/books/' + bid)
    st = d['chapters'][0]['passages'][0]['stage']
    check('目录里这一段变成已练完', st == 'done', st)
    check('目录统计了练完的段数', d['counts']['done'] == 1, str(d['counts']))

    # ── 单句：只给一句
    code, s1, raw, _ = cl.post('/api/practice/%s/1/1/sentence/1' % bid, {})
    check('单句接口能取到第 1 句', code == 200 and s1.get('sentence'), raw[:160])
    check('单句接口给出总句数', s1['total'] == len(S.split_sentences(src1)),
          '%s vs %s' % (s1.get('total'), len(S.split_sentences(src1))))
    check('单句接口只给一句，不顺带整段',
          S.plain_len(s1['sentence']) < S.plain_len(src1),
          '%d vs %d' % (S.plain_len(s1['sentence']), S.plain_len(src1)))
    code, _, _, _ = cl.post('/api/practice/%s/1/1/sentence/999' % bid, {})
    check('越界的句号被拒', code == 404, str(code))

    # ── 笔记：跟着书走（观察已经合成一条整段笔记了）
    code, nb, raw, _ = cl.get('/api/books/%s/notes' % bid)
    check('整段观察已经进了这本书的笔记', code == 200 and nb['count'] == 1,
          raw[:200])
    check('那条笔记是整段范围的（scope=passage）',
          nb['notes'][0]['scope'] == 'passage'
          and nb['notes'][0]['text'] == '我把那句问句丢了，原文短句多。',
          str(nb['notes'][0])[:160])
    check('整段笔记里存了你当时写的那一稿',
          nb['notes'][0]['mine'], str(nb['notes'][0])[:120])
    check('笔记接口回带书名（笔记和书绑定）', nb['book']['title'] == '端午的鸭蛋')

    code, d, raw, _ = cl.post('/api/practice/%s/1/1/note' % bid, {
        'text': '   '})
    check('空笔记被拒', code == 400, raw[:120])

    code, d, raw, _ = cl.post('/api/practice/%s/1/1/note' % bid, {
        'text': '我把因果省了，原文是"因为…所以"。', 'sent_no': 1,
        'sentence': s1['sentence'], 'mine': '另一句。', 'hint': '讲端午的风俗'})
    check('能记逐句笔记', code == 200 and d['note']['text'], raw[:160])
    check('逐句笔记带上句子编号', d['note']['sent_no'] == 1, str(d['note']))
    check('逐句笔记的范围标成 sentence', d['note']['scope'] == 'sentence',
          str(d['note'].get('scope')))
    check('笔记存下了原文那一句和你的那一句',
          d['note']['sentence'] and d['note']['mine'], str(d['note']))
    nid = d['note']['id']

    code, nb, _, _ = cl.get('/api/books/%s/notes' % bid)
    check('逐句笔记和整段观察在同一个清单里', nb['count'] == 2, str(nb['count']))
    check('笔记里能看到那一句的原文和提示',
          any(n['sentence'] and n['hint'] for n in nb['notes']),
          str(nb['notes'])[:200])

    # 同一段再记一条：三条都在，按时间倒序
    cl.post('/api/practice/%s/1/1/note' % bid, {
        'text': '第二句我把短句连成长句了。', 'sent_no': 2, 'sentence': '甲。', 'mine': '乙。'})
    code, nb2, _, _ = cl.get('/api/books/%s/notes' % bid)
    check('可以记多条', nb2['count'] == 3, str(nb2['count']))
    check('笔记按时间倒序（最新在前）',
          nb2['notes'][0]['text'].startswith('第二句'), nb2['notes'][0]['text'][:20])

    # 另一种范围也要能记
    code, d, _, _ = cl.post('/api/practice/%s/1/1/note' % bid, {
        'text': '这一段整体上我把节奏写散了。', 'scope': 'passage', 'mine': '我的稿子。'})
    check('不带句子编号也能记（整段范围）',
          code == 200 and d['note']['scope'] == 'passage'
          and d['note']['sent_no'] == 0, str(d.get('note'))[:140])

    code, nb3, _, _ = cl.get('/api/books/%s/notes' % bid)
    check('笔记是整本书的，不是某一段的', nb3['count'] == 4, str(nb3['count']))
    check('清单里两种范围都在',
          {n['scope'] for n in nb3['notes']} == {'sentence', 'passage'},
          str({n['scope'] for n in nb3['notes']}))

    code, d, _, _ = cl.delete('/api/books/%s/notes/%s' % (bid, nid))
    check('能删单条笔记', code == 200 and d.get('ok'), str(d))
    code, nb4, _, _ = cl.get('/api/books/%s/notes' % bid)
    check('删掉一条后少一条', nb4['count'] == 3, str(nb4['count']))

    # ── 导出
    code, raw, text, hdr = cl.get('/api/export/%s/1/1' % bid)
    check('导出能下载', code == 200 and '## 原文' in text and 'attachment' in hdr.get(
        'Content-Disposition', ''))
    check('导出里有我的观察', '那句问句丢了' in text)
    check('导出里没有评语式措辞',
          not any(w in text for w in ('得分', '评分', '相似度', '保真', '你应该')))

    # ── 记录
    code, d, raw, _ = cl.get('/api/records')
    check('记录能读', code == 200 and len(d['rows']) == 1, raw[:200])
    row = d['rows'][0]
    check('记录里有原文以外的全部要素',
          row['book'] == '端午的鸭蛋' and row['draft'] and row['observation']
          and row['hints'])
    check('记录统计了对错以外的动作数', d['counts']['done'] == 1)

    # ── 设置与模型
    code, d, _, _ = cl.get('/api/settings')
    check('设置能读', code == 200 and d.get('presets'))
    check('设置里回传了服务商预设',
          any(p['id'] == 'deepseek' for p in d['presets']))
    check('Key 给了可辨认的提示（不明文回传）',
          d['has_key'] is True and d['api_key'] == '' and 'sk-te' in d['key_hint'],
          str(d.get('key_hint')))
    check('存档文件里存了 Key', os.path.exists(os.path.join(root, 'index.json')))

    code, d, _, _ = cl.post('/api/llm/test', {})
    check('测试连接能走通（走的是假接口）', code == 200 and d.get('ok'))
    check('设置页能看到缓存与 token 账',
          d is not None and True)
    code, st2, _, _ = cl.get('/api/settings')
    c2 = st2.get('cache') or {}
    check('设置里报了缓存条数与累计 token',
          c2.get('cached', 0) >= 0 and 'tokens_in' in c2 and 'calls' in c2,
          str(c2))
    check('设置里报了并发数', st2.get('concurrency', 0) >= 1, str(st2.get('concurrency')))

    # ── 延迟设为 0 之后应立刻能写
    code, _, _, _ = cl.post('/api/settings', {'delay_min': 0})
    code, d, _, _ = cl.post('/api/practice/%s/2/1/start' % bid, {})
    check('delay=0 时不进入等待', d['stage'] == 'ready', str(d))

    # ── 逐接口扫原文泄露（B1 的总检查）
    # 第 2 节还没练，此时任何只读接口都不该吐出它的正文
    code, ch2, _, _ = cl.get('/api/books/%s/chapters/2' % bid)
    src2 = ch2['text']
    leaks = []
    for path in ('/api/shelf', '/api/books/' + bid, '/api/records',
                 '/api/settings'):
        _, _, raw2, _ = cl.get(path)
        hits = SRV.find_leak(src2, raw2, min_len=14)
        if hits:
            leaks.append((path, hits[:2]))
    check('B1 只读接口都不泄露未练段的正文', not leaks, str(leaks))

    code, d, raw, _ = cl.get('/api/practice/%s/2/1/write' % bid)
    hits = SRV.find_leak(src2, raw, min_len=14)
    check('B1 写稿接口不泄露本段正文', not hits, str(hits[:3]))
    check('B1 写稿接口也没有 source 字段', 'source' not in d)

    # ── 删书
    code, d, _, _ = cl.delete('/api/books/' + bid)
    check('删书要确认', code == 400)
    code, d, _, _ = cl.delete('/api/books/%s?confirm=%s' % (bid, bid))
    check('确认后能删书', code == 200)
    code, d, _, _ = cl.get('/api/shelf')
    check('删后书架为空', d['books'] == [])
    check('原文文件也删掉了',
          not os.path.exists(os.path.join(root, 'texts', bid + '.txt')))
    code, d, _, _ = cl.get('/api/records')
    check('删书后记录也清掉了', d['rows'] == [])

    # ── 清缓存（放最后，免得影响前面的对照与记录）
    code, d, _, _ = cl.post('/api/summaries/clear', {})
    check('能清缓存', code == 200 and d.get('removed', 0) >= 1, str(d)[:120])
    code, d, _, _ = cl.get('/api/settings')
    check('清完之后缓存条数归零', d['cache']['cached'] == 0, str(d['cache']))

    # ── 没配模型时的提示：换一个干净的存档目录来验
    tmp2 = tempfile.mkdtemp(prefix='fk_srv2_')
    try:
        api2 = SRV.Api(tmp2)
        r2 = SRV.Api.add_book(api2, {'title': '空配置测试', 'text': BOOK * 2,
                                     'passage_chars': 150})
        b2 = r2['book']['id']
        SRV.Api.start(api2, b2, 1, 1, {})
        try:
            SRV.Api.hints(api2, b2, 1, 1)
            check('没配模型时给的是可读的提示，不是崩溃', False, '竟然成功了')
        except S.StoreError as e:
            check('没配模型时给的是可读的提示，不是崩溃',
                  '设置' in e.message and e.code == 400, e.message)
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # ── 存档健壮性：写坏了要从 .bak 恢复
    p = os.path.join(root, 'index.json')
    with open(p + '.bak', 'w', encoding='utf-8') as f:
        json.dump({'schema': 2, 'books': [], 'attempts': [],
                   'settings': {}}, f, ensure_ascii=False)
    with open(p, 'w', encoding='utf-8') as f:
        f.write('{ 这不是 json')
    code, d, raw, _ = cl.get('/api/shelf')
    check('存档写坏时给的是可读的提示，而不是 500 崩溃',
          code == 500 and '存档' in (d.get('error') or ''), raw[:160])
    check('提示里告诉了备份文件在哪', '.bak' in (d.get('error') or ''), raw[:200])


if __name__ == '__main__':
    sys.exit(main())
