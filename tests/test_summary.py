#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_summary — 提示卡的缓存、账目、批量与"照抄检查"。

这一组测的都是钱和体验：会不会重复花钱、账目是不是真的、
批量生成中途出错会不会失控、模型照抄原文时拦不拦得住。

模型调用全部替换成假接口，不联网。
用法：python tests/test_summary.py
"""
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_llm as LLM
import fk_summary as SUM

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


SETTINGS = {'provider': 'deepseek', 'base_url': 'https://api.deepseek.com/v1',
            'model': 'deepseek-chat', 'api_key': 'sk-test-abcdefghij'}

SRC = '家乡的端午，很多风俗和外地一样。系百索子，五色的丝线拧成小绳。'


def main():
    real_chat = LLM.chat
    calls = {'n': 0, 'last_user': ''}
    reply = {'text': '1. 讲家乡端午的风俗。\n2. 列举系百索子等几样做法。'}

    def fake(settings, system, user, **kw):
        calls['n'] += 1
        calls['last_user'] = user
        calls['last_kw'] = kw
        return {'text': reply['text'], 'usage': {'in': 500, 'out': 60},
                'model': settings.get('model', '')}

    LLM.chat = fake
    tmp = tempfile.mkdtemp(prefix='fk_sum_')
    try:
        # ── 提示词的硬约束：逐句、不照抄、不评价
        check('系统提示要求一句一条', '几句' in LLM.SYSTEM_PROMPT
              and '就写几条' in LLM.SYSTEM_PROMPT, LLM.SYSTEM_PROMPT[:60])
        check('系统提示要求不得复用原文词句',
              '绝不能复用原文的词句' in LLM.SYSTEM_PROMPT)
        check('系统提示说明了为什么不能照抄（否则会直接抄）',
              '练习就白做了' in LLM.SYSTEM_PROMPT)
        check('系统提示不评价、不建议',
              '不评价原文' in LLM.SYSTEM_PROMPT
              and '不给任何写作建议' in LLM.SYSTEM_PROMPT)
        check('系统提示不长（每次调用都要重发，省 token）',
              len(LLM.SYSTEM_PROMPT) < 260, '%d 字' % len(LLM.SYSTEM_PROMPT))

        # ── 单条提示的字数上限：句子越多给得越紧，但都有上限
        check('句子少时单条可以长一点', LLM.per_hint_chars(3) == 22,
              str(LLM.per_hint_chars(3)))
        check('句子多时单条收紧', LLM.per_hint_chars(20) == 15,
              str(LLM.per_hint_chars(20)))
        check('单条上限始终存在（提示越细，练习越轻）',
              all(LLM.per_hint_chars(n) <= 22 for n in range(1, 200)))

        # ── 切句：必须和写稿、对照用同一套规则
        sents = LLM.numbered_sentences('甲。乙！丙？丁，戊')
        check('切句把没句号的尾巴也算一句', len(sents) == 4, str(sents))
        check('切句去掉空句', all(s.strip() for s in sents))

        # ── Key 的合法性检查
        ok, why = LLM.check_ready(SETTINGS)
        check('配置齐全时可用', ok, why)
        ok, why = LLM.check_ready({**SETTINGS, 'api_key': 'sk-中文密钥'})
        check('Key 里有中文会被拦住并说人话',
              not ok and '不合法字符' in why, why)
        ok, why = LLM.check_ready({**SETTINGS, 'api_key': 'sk-a b'})
        check('Key 里有空格会被拦住', not ok, why)
        ok, why = LLM.check_ready({**SETTINGS, 'api_key': ''})
        check('没填 Key 会被拦住', not ok, why)
        ok, why = LLM.check_ready({**SETTINGS, 'api_key': '',
                                   'base_url': 'http://127.0.0.1:11434/v1'})
        check('本地服务不需要 Key', ok, why)

        # ── hints_raw：条数与句数对齐
        calls['n'] = 0
        r = LLM.hints_raw(SETTINGS, SRC)
        check('提示条数由句子数决定', r['n_sent'] == 2 and r['n_hint'] == 2,
              '句 %s 条 %s' % (r['n_sent'], r['n_hint']))
        check('对齐时 aligned 为真', r['aligned'] is True)
        check('每条提示带句子编号',
              [h['no'] for h in r['hints']] == [1, 2], str(r['hints']))
        check('请求里带了句数和编号', '共 2 句' in calls['last_user']
              and '1. ' in calls['last_user'], calls['last_user'][:80])
        check('请求里带了单条字数上限',
              str(LLM.per_hint_chars(2)) in calls['last_user'],
              calls['last_user'][:120])
        check('输出额度按句数算（一句一条，单条封顶）',
              calls['last_kw'].get('max_tokens') == 2 * LLM.per_hint_chars(2) * 2 + 100,
              str(calls['last_kw'].get('max_tokens')))

        # 模型少给/多给时要如实报出来
        reply['text'] = '1. 只有一条。'
        r2 = LLM.hints_raw(SETTINGS, SRC)
        check('模型少给了就如实报不对齐',
              r2['n_hint'] == 1 and r2['aligned'] is False, str(r2))
        reply['text'] = '1. 一。\n2. 二。\n3. 三。\n4. 四。'
        r3 = LLM.hints_raw(SETTINGS, SRC)
        check('模型多给了就截到句数', r3['n_hint'] == 4 and len(r3['hints']) == 2,
              str(r3['n_hint']))
        reply['text'] = '1. 讲家乡端午的风俗。\n2. 列举系百索子等几样做法。'

        # ── 缓存
        cache = SUM.SummaryCache(tmp)
        check('缓存键只跟内容有关（跟位置无关）',
              SUM.cache_key(SRC, 'm1') == SUM.cache_key(SRC, 'm1'))
        check('不同模型是不同的缓存键',
              SUM.cache_key(SRC, 'm1') != SUM.cache_key(SRC, 'm2'))
        check('缓存键带提示词版本（改提示词就失效）',
              str(LLM.PROMPT_VERSION) in SUM.cache_key(SRC, 'm1'))

        calls['n'] = 0
        r1 = cache.ensure(SRC, SETTINGS)
        check('第一次要提示会调用模型', calls['n'] == 1 and not r1['cached'])
        r2 = cache.ensure(SRC, SETTINGS)
        check('第二次要同一段走缓存，不再调用', calls['n'] == 1 and r2['cached'])
        check('缓存里取出来的内容一样',
              [h['hint'] for h in r1['hints']] == [h['hint'] for h in r2['hints']])
        r3 = cache.ensure(SRC, SETTINGS, force=True)
        check('可以强制重新生成', calls['n'] == 2 and not r3['cached'])

        # 换模型 → 重新生成
        r4 = cache.ensure(SRC, {**SETTINGS, 'model': 'other-model'})
        check('换模型会重新生成（不同模型说法不一样）',
              calls['n'] == 3 and not r4['cached'])

        check('缓存条数按"内容+模型"算', cache.stats()['cached'] == 2,
              str(cache.stats()['cached']))
        check('缓存落盘了', os.path.exists(os.path.join(tmp, 'summaries.json')))

        # ── 账目：只记真实数字
        st = cache.stats()
        check('记账用的是服务商回传的 token 数', st['tokens_in'] == 1500,
              str(st['tokens_in']))
        check('记账了调用次数', st['calls'] == 3, str(st['calls']))
        check('记账了命中次数', st['hits'] == 1, str(st['hits']))

        # 服务商不回传 usage 时：如实记 0，并标记出来，不估算
        def fake_nousage(settings, system, user, **kw):
            calls['n'] += 1
            return {'text': '1. 没有用量的返回。', 'usage': None,
                    'model': settings.get('model', '')}
        LLM.chat = fake_nousage
        cache.ensure('另一段完全不同的原文内容，用来测没有 usage 的情况。', SETTINGS)
        st2 = cache.stats()
        check('服务商不回传用量时如实记 0 并标记',
              st2.get('calls_without_usage', 0) == 1
              and st2['tokens_in'] == 1500, str(st2))
        LLM.chat = fake

        # ── 照抄检查（逐条，不牵连）
        echo = [{'no': 1, 'hint': '讲端午的风俗。'},
                {'no': 2, 'hint': '系百索子，五色的丝线拧成小绳'},
                {'no': 3, 'hint': '还提到系百索子。'}]
        keep, dropped = SUM.strip_echoes(echo, SRC)
        check('照抄原文的那一条会被摘掉',
              len(dropped) == 1 and dropped[0]['no'] == 2, str([h['no'] for h in dropped]))
        check('老实转述的那两条不受牵连',
              [h['no'] for h in keep] == [1, 3], str([h['no'] for h in keep]))
        keep2, dropped2 = SUM.strip_echoes([{'no': 1, 'hint': '列举了系百索子之类的做法。'}], SRC)
        check('正常转述（列举事物）不会被误杀', not dropped2, str(dropped2))
        keep3, d3 = SUM.strip_echoes([], SRC)
        check('空列表不报错', keep3 == [] and d3 == [])

        # 全被摘光时应该重来一次。
        # 拿来测的这段原文必须和 SRC 没有任何 8 字以上重合，
        # 否则重试时输出照样会被判为照抄，就不是在测"重试"了。
        novel = '海边的渔村在清晨醒来，潮水退去以后滩涂上留下了许多贝类和海藻。'
        calls['n'] = 0
        reply['text'] = '1. 潮水退去以后滩涂上留下了许多贝类。'   # 整句照抄 novel
        r5 = cache.ensure(novel, SETTINGS, force=True)
        check('整条照抄时会重试一次', calls['n'] == 2, str(calls['n']))
        check('两次都在照抄时，宁可一条不给（不把原文塞回给你）',
              (r5.get('hints') or []) == [], str(r5.get('hints')))
        check('照抄的条数如实报出来，不假装成功',
              len(r5.get('dropped_echoes') or []) >= 1,
              str(r5.get('dropped_echoes')))

        reply['text'] = '讲家乡端午的几样风俗。\n系百索子、做香角子、贴五毒、贴符。'

        # ── 估算
        cache.clear()
        texts = [SRC, SRC, '这一段是新的，缓存里没有。']
        est = cache.estimate(texts, SETTINGS)
        check('估算区分了缓存与待做', est['cached'] == 0 and est['todo'] == 2, str(est))
        check('同一段文字在估算里只算一次钱',
              est['total'] == 2 and est['duplicates'] == 1, str(est))
        cache.ensure(SRC, SETTINGS)
        est2 = cache.estimate(texts, SETTINGS)
        check('做过之后再来算，已缓存的不再计费',
              est2['cached'] == 1 and est2['todo'] == 1, str(est2))
        check('估算给出 token 数量', est['est_tokens'] > 0)
        check('估算明确标注是估算', '估算' in est['note'])

        # ── 清缓存
        cache.clear()
        cache.ensure(SRC, SETTINGS)
        cache.ensure(SRC, {**SETTINGS, 'model': 'other-model'})
        before = cache.stats()['cached']
        r = cache.clear('other-model')
        check('可以只清某个模型的缓存',
              r['removed'] == 1 and r['left'] == before - 1, str(r))
        check('清掉一个模型后，另一个模型的缓存还在',
              cache.has(SRC, SETTINGS['model']), '')
        r = cache.clear()
        check('可以全清', r['left'] == 0 and cache.stats()['cached'] == 0, str(r))

        # ── 批量生成（在真 Store 上跑）
        import fk_store as S
        import fk_server as SRV
        tmp2 = tempfile.mkdtemp(prefix='fk_sum2_')
        try:
            api = SRV.Api(tmp2)
            api.save_settings(SETTINGS)
            # 造一本段落多、而且**每段内容都不同**的书：
            # 内容相同的段会命中缓存（这是对的），但那样就测不出"连败即停"。
            paras = []
            for i in range(14):
                paras.append('第%d节　甲%d\n\n家乡的端午，很多风俗和外地一样，第%d种说法。'
                             '系百索子，五色的丝线拧成小绳，系在手腕上。做香角子。'
                             % (i + 1, i + 1, i + 1)
                             + '贴五毒，红纸剪成五毒，贴在门槛上。第%d家如此。' % (i + 1))
            book = '\n\n'.join(paras) + '\n'
            r = api.add_book({'title': '批量测试', 'text': book, 'passage_chars': 150})
            bid = r['book']['id']
            check('测试用书够长（不然测不出连败即停）',
                  r['book']['counts']['total'] >= 8, str(r['book']['counts']['total']))

            calls['n'] = 0
            plan = api.summary_plan(bid)
            check('算账列出了全部段数', plan['total'] >= 1, str(plan['total']))
            check('算账时还没有缓存', plan['cached'] == 0 and plan['todo'] == plan['total'],
                  str(plan))

            api.summary_warm(bid)
            job = None
            for _ in range(300):
                job = api.warmer.status(bid)
                if job and job['state'] != 'running':
                    break
                time.sleep(0.02)
            check('批量生成能跑完', job['state'] == 'done', str(job))
            check('批量生成把所有段都做了', job['done'] + job['skipped'] == plan['total'],
                  str(job))
            check('批量生成只调用了必要次数', calls['n'] == job['done'],
                  'calls=%s done=%s' % (calls['n'], job['done']))

            plan2 = api.summary_plan(bid)
            check('再算账：一段也不用再做', plan2['todo'] == 0, str(plan2['todo']))
            calls['n'] = 0
            api.summary_warm(bid)
            time.sleep(0.2)
            check('再批量一次不花钱（全在缓存里）', calls['n'] == 0, str(calls['n']))

            # 失败要能被看见、而且连败会停
            def broken(settings, system, user, **kw):
                raise LLM.LlmError('Key 不对或者过期了。', 401, '去设置里重新填一个。')
            LLM.chat = broken
            api.summary_clear({})
            calls['n'] = 0
            api.summary_warm(bid)
            job2 = None
            for _ in range(300):
                job2 = api.warmer.status(bid)
                if job2 and job2['state'] != 'running':
                    break
                time.sleep(0.02)
            check('批量遇到硬错误会停下（不硬撑到底）',
                  job2['state'] == 'error', str(job2['state']))
            check('错误信息是可读的中文，不是异常类名',
                  'Key' in (job2.get('last_error') or ''), str(job2.get('last_error')))
            check('连败时没有把每一段都试一遍',
                  job2['failed'] < plan2['total'] + 1, str(job2))
            LLM.chat = fake
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)
    finally:
        LLM.chat = real_chat
        shutil.rmtree(tmp, ignore_errors=True)

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
