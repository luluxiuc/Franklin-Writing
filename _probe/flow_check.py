#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flow_check — 拿真实语料走完一整轮，把中间产物全部打出来。

这不是测试（测试在 tests/），而是"这工具到底给了用户什么、花了多少钱"的
肉眼检查：导入 → 算账 → 提前备好 → 读 → 等 → 写 → 对照 → 观察 → 账目。

模型调用换成一个假接口（不联网），但它会回传 usage，
所以缓存、记账、批量生成这条链路都是真的走了一遍。

跑在**本进程**里，不起 HTTP：因为后台批量生成是另一个线程在调模型，
跨进程打桩打不中，那样一跑就会真的去连网。

用法：python _probe/flow_check.py [--keep]
"""
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_llm as LLM
import fk_server as SRV
import fk_store as S

CORPUS = os.path.join(HERE, 'corpus', 'wang-zengqi-duanwu.txt')

FAKE_SUMMARY = (
    '1. 讲家乡端午的几样风俗。\n'
    '2. 系百索子、做香角子、贴五毒、贴符。\n'
    '3. 符是城隍庙送来的，老道士是寄名干爹。\n'
    '4. 还有喝雄黄酒、放黄烟子。\n'
    '5. 午饭要吃"十二红"，作者只记得其中三样。'
)


def rule(t):
    print('\n' + '═' * 72)
    print(t)
    print('═' * 72)


def main():
    keep = '--keep' in sys.argv
    text = open(CORPUS, encoding='utf-8').read().strip()

    data_dir = tempfile.mkdtemp(prefix='fk_flow_')
    api = SRV.Api(data_dir)
    n_calls = {'n': 0}

    def fake_chat(settings, system, user, **kw):
        n_calls['n'] += 1
        return {'text': FAKE_SUMMARY, 'usage': {'in': 520, 'out': 78},
                'model': settings.get('model', '')}

    LLM.chat = fake_chat
    print('本次跑测用一个临时书架：%s' % data_dir)
    print('模型调用走假接口，不联网；跑完就删。')

    rule('① 配置模型（Key 只存本机）')
    api.save_settings({'provider': 'deepseek', 'base_url': 'https://api.deepseek.com/v1',
                       'model': 'deepseek-chat', 'api_key': 'sk-demo-not-a-real-key',
                       'delay_min': 3})
    print('已配置。')

    rule('② 导入：一篇没有章节标记的文章')
    r = api.add_book({'title': '端午的鸭蛋', 'author': '汪曾祺', 'text': text,
                      'passage_chars': 300})
    bid = r['book']['id']
    print('书名：%s　%s' % (r['book']['title'], r['book']['author']))
    print('全文 %d 字，切成 %d 节、%d 段：'
          % (r['book']['chars'], len(r['book']['chapters']), r['book']['counts']['total']))
    for c in r['book']['chapters']:
        print('   第 %d 节　%-22s %4d 字　%d 段'
              % (c['no'], c['title'][:20], c['chars'], len(c['passages'])))

    rule('③ 先算账：提前备好整本书的提示卡要花多少')
    plan = api.summary_plan(bid)
    print('这本书 %d 段' % plan['total'])
    print('已有缓存：%d 段　　还要做：%d 段' % (plan['cached'], plan['todo']))
    print('预计消耗：输入约 %s token，输出约 %s token（合计 %s）'
          % (plan['est_tokens_in'], plan['est_tokens_out'], plan['est_tokens']))
    print('　%s' % plan['note'])
    print('并发数：%d（环境变量 FK_LLM_CONCURRENCY 可以调）' % plan['concurrency'])
    print('　短于 40 字的段落会被跳过——那种段花 token 做提示卡不划算。')

    rule('④ 提前备好（后台批量，练的时候就不用等模型）')
    api.summary_warm(bid)
    job = None
    for _ in range(200):
        job = api.warmer.status(bid)
        if job and job['state'] != 'running':
            break
        time.sleep(0.05)
    print('批量结果：%s　成功 %d　跳过（已有缓存）%d　失败 %d　用了 %s 秒'
          % (job['state'], job['done'], job['skipped'], job['failed'], job['elapsed']))
    print('实际调用模型次数：%d' % n_calls['n'])
    st = api.warmer.cache.stats()
    print('累计真实用量：输入 %d token，输出 %d token（服务商回传的数字）'
          % (st['tokens_in'], st['tokens_out']))
    if job['last_error']:
        print('　错误：%s' % job['last_error'])

    rule('⑤ 读原文：整节都在眼前')
    ch = api.chapter(bid, 1)
    print('第 1 节　%d 字' % ch['chapter']['chars'])
    print('　' + ch['text'][:120].replace('\n', ' ') + '…')
    src = ch['passages'][0]['text']
    print()
    print('这一节分 %d 段，第 1 段 %d 字：' % (len(ch['passages']), ch['passages'][0]['chars']))
    print('　' + src[:100].replace('\n', ' ') + '…')

    rule('⑥ 读完了，开始练习（延迟从这里算起）')
    d = api.start(bid, 1, 1, {'read_seconds': 65})
    print('状态：%s　剩余：%s 秒' % (d['stage'], d['remaining']))

    rule('⑦ 写稿页：原文看不见，提示卡已经在本地了')
    wv = api.write_view(bid, 1, 1)
    leak = SRV.find_leak(src, wv)
    print('本段原文 %d 字，写稿页里能看到的只有：' % wv['passage']['chars'])
    print('   · 书名、第几节、第几段')
    print('   · 这一段多少字')
    print('   · 提示卡（已经在缓存里：%s）' % ('是' if wv['summary_cached'] else '否'))
    print()
    print('出厂自检：拿原文所有 8 字以上片段反查写稿页 → %s'
          % ('干净，一个字都没有' if not leak else '泄露！%s' % leak[:3]))
    print()
    print('提示卡内容（打开页面就有，没有等模型）：')
    for p in wv['summary_points']:
        print('   · %s' % p)

    rule('⑧ 缓存：同一段再要一次，不再花钱')
    before = n_calls['n']
    sm2 = api.summary(bid, 1, 1)
    print('再要一次 → 走缓存：%s　模型调用次数：%d → %d'
          % (sm2['cached'], before, n_calls['n']))
    print('提示卡里含原文 8 字以上片段？%s'
          % ('没有' if not SRV.find_leak(src, {'s': sm2['summary']}) else '有！'))

    rule('⑨ 交稿：原文和我的稿子同时出现')
    draft = ('家乡的端午，风俗和外地一样。系百索子，五色的丝线拧成小绳，系在手腕上。'
             '做香角子，挂在帐钩上。贴五毒，贴在门槛上。')
    try:
        cmp_ = api.submit(bid, 1, 1, {'draft': draft, 'prompt_used': True,
                                      'write_seconds': 372})
    except S.StoreError as e:
        print('被延迟闸门拦下了（%s），先跳过等待再交。' % e.message)
        api.skip_wait(bid, 1, 1)
        cmp_ = api.submit(bid, 1, 1, {'draft': draft, 'prompt_used': True,
                                      'write_seconds': 372})
    f = cmp_['facts']
    print('原文 %d 字　　我的稿子 %d 字' % (len(cmp_['source']), len(cmp_['draft'])))
    print('读原文用了 %s 秒，写作用了 %s 秒' % (cmp_['read_seconds'], cmp_['write_seconds']))
    print()
    print('原文里有、我没写到的片段（%d 处）：' % len(f['segments']))
    for seg in f['segments']:
        print('   ○ %s' % seg)
    print()
    print('按词看：原文 %d 条片段，写到 %d 条，没写到 %d 条'
          % (f['total'], f['hit_count'], f['miss_count']))
    print('   %s' % f['note'])

    rule('⑩ 写下观察，这一轮结束')
    obs = ('提示卡说"系百索子、做香角子、贴五毒、贴符"，我就照着这几个动作写了，'
           '但具体的东西全省了：五色的、红一道绿一道、香面、帐钩、门槛。'
           '那句"这就能避邪吗"我完全没想起来。')
    api.observe(bid, 1, 1, {'observation': obs})
    print('已记录。')
    print('　' + obs)

    rule('⑪ 账目：全程只花了这些')
    c = api.settings()['cache']
    print('缓存里 %d 张提示卡　实际调用模型 %d 次　命中缓存 %d 次'
          % (c['cached'], c['calls'], c['hits']))
    print('累计真实用量：输入 %d token，输出 %d token，模型用时 %.1f 秒'
          % (c['tokens_in'], c['tokens_out'], c['seconds']))
    print('缓存文件：%s' % c['file'])
    print()
    print('同一段文字第二次要用时，调用次数不会增加——这就是"不重复花钱"。')
    print('换模型或者改提示词会让旧缓存失效（不同模型的说法不一样，这是有意的）。')

    rule('⑫ 练习记录')
    rec = api.records()
    cc = rec['counts']
    print('一共 %d 轮，练完 %d 轮，用了提示 %d 轮'
          % (cc['records'], cc['done'], cc['using_prompt']))
    for row in rec['rows']:
        print('   %s　%s 第 %d 节第 %d 段　写了 %d 字　用时 %s 秒　%s'
              % (row['wrote_at'], row['book'], row['chapter'], row['passage'],
                 row['chars'], row['write_seconds'],
                 '用了提示' if row['prompt_used'] else '凭记忆'))
    print('　（记录接口不返回原文——否则列表一打开就把没练过的段落摊开了。）')

    rule('⑬ 收尾')
    if keep:
        print('保留了这次跑测的书架：%s' % data_dir)
    else:
        shutil.rmtree(data_dir, ignore_errors=True)
        print('已删掉这次跑测的临时书架。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
