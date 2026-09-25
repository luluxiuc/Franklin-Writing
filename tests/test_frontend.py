#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_frontend — 前端契约测试（静态检查）。

网页端最烦人的 bug 是"点了一下什么都没发生"：JS 里 $('#xxx') 找不到元素，
或者 fetch 打到一个不存在的接口。这类错误只在浏览器里暴露，而且不报错。
这里把常见的几类提前抓出来：

  W1  app.js 里 $('#id') 引用的元素，index.html 里必须有
  W2  index.html 里的固定 id 都被用到（没有写死的死元素）
  W3  app.js 调用的 /api 接口，服务端必须有对应路由
  W4  前端不得出现任何评分/相似度类的字段或文案
  W5  CSS 变量都定义过；页面不引用任何外部资源（要能离线用）

真正的"渲染会不会崩"在 tests/render_check.mjs 里跑（那需要 Node）。
用法：python tests/test_frontend.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
WEB = os.path.join(ROOT, 'app', 'web')

PASS, FAIL = [], []


def check(name, ok, detail=''):
    (PASS if ok else FAIL).append((name, detail))
    print(('  [OK] ' if ok else '  [!!] ') + name + (('  — ' + detail) if detail and not ok else ''))


# 由 app.js 在运行时生成的元素，静态检查时跳过
DYNAMIC = {
    # 书架
    'btn-add2', 'shelf',
    # 书内目录与提示准备
    'prepare-slot', 'prep-go', 'prep-cancel', 'prep-refresh', 'prep-set',
    'notes-slot', 'notes-block', 'notes-toggle', 'notes-export',
    'b-read', 'b-next',
    # 读书
    'r-done',
    # 等待
    'cd', 'bar', 'w-reread', 'w-other', 'w-skip',
    # 写作台
    'hint-panel', 'hint-again', 'hint-make', 'hint-off', 'hint-set', 'hint-single',
    'draft', 'wc', 'save-state', 'submit', 'reread', 'anim',
    # 单句练习
    'd-back', 'd-prev', 'd-next', 'd-wc', 'd-write',
    'note-ta', 'note-save', 'note-saved',
    # 对照
    'obs', 'obs-save', 'export', 'back', 'next',
    # 导入弹窗
    'f-title', 'f-author', 'f-size', 'f-file', 'f-text', 'f-count', 'no', 'yes',
    # 设置
    's-provider', 's-base', 's-model', 's-key', 's-delay', 's-size',
    's-save', 's-save2', 's-test', 's-clear', 's-status', 'key-hint',
    's-clear-cache',
    # 记录
    'rec-0',
    # 弹窗里的
    'go', 'later',
    # 动效档位是模板里生成的
    'anim-pick', 'anim-cur',
}

# index.html 里为了布局而存在的 id，不需要 JS 引
STRUCTURAL = {
    'main', 'nav', 'brand', 'brand-sub', 'toast', 'modal', 'modal-box',
    'shelf-lead', 'reader', 'read-title', 'book', 'practice',
    'prac-title', 'prac-meta', 'records', 'records-lead', 'settings',
    'btn-add', 'btn-font', 'btn-theme', 'read-back', 'read-prev', 'read-next',
    'prac-back',
    'view-shelf', 'view-read', 'view-book', 'view-practice', 'view-records',
    'view-settings',
}


def main():
    js = open(os.path.join(WEB, 'app.js'), encoding='utf-8').read()
    html = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()
    css = open(os.path.join(WEB, 'style.css'), encoding='utf-8').read()
    srv = open(os.path.join(ROOT, 'app', 'fk_server.py'), encoding='utf-8').read()

    html_ids = set(re.findall(r'id="([^"]+)"', html))
    js_ids = set(re.findall(r"\$\('#([A-Za-z0-9_-]+)'", js))
    js_ids |= set(re.findall(r'\$\("#([A-Za-z0-9_-]+)"', js))
    # 模板拼接出来的 id（'#rec-body-' + i）在运行期才有，静态检查时去掉尾部的空片段
    js_ids = {i for i in js_ids if not i.endswith('-')}

    missing = sorted(i for i in js_ids if i not in html_ids and i not in DYNAMIC)
    check('W1 app.js 引用的元素都在 index.html 里', not missing, '缺：%s' % missing)

    dead = sorted(i for i in html_ids
                  if i not in js_ids and i not in STRUCTURAL and i not in DYNAMIC)
    check('W2 index.html 里没有没人用的固定元素', not dead, '多余：%s' % dead)

    # 路由与接口
    used = set()
    for m in re.finditer(r"""api\(\s*[`'"]([^`'"]+)""", js):
        used.add(m.group(1))
    heads = set()
    for p in used:
        p = p.split('?')[0].strip('/')
        if p.startswith('api/'):
            p = p[4:]
        head = p.split('/')[0]
        head = re.sub(r'\$\{.*', '', head).strip()
        if head:
            heads.add(head)
    known = {'health', 'shelf', 'settings', 'records', 'books', 'practice', 'export',
             'llm', 'summaries', 'notes'}
    unknown = sorted(h for h in heads if h not in known)
    check('W3 app.js 只调用已知接口', not unknown, '未知：%s' % unknown)

    routes_ok = []
    for h in sorted(known):
        if ("'%s'" % h) not in srv:
            routes_ok.append(h)
    check('W3 服务端覆盖前端用到的全部接口', not routes_ok, '缺：%s' % routes_ok)

    # 方法要对得上
    put_calls = re.findall(r"api\(\s*`([a-z]+)/[^`]*`\s*,\s*\{\s*method:\s*'([A-Z]+)'", js)
    check('W3 草稿用 PUT 保存', ('practice', 'PUT') in put_calls, str(put_calls))
    check('W3 交稿/观察用 POST', 'submit' in js and 'observe' in js)

    # W4 评价性用语
    banned = ['相似度', '评分', '得分', '保真度', 'score', 'similarity', 'rating',
              '更像作者', '不像作者', '写得好', '写得差', '命中率']
    found = [b for b in banned if b in js]
    check('W4 app.js 里没有评价性措辞或字段', not found, '发现：%s' % found)
    calc = re.findall(r'(score|similarity|rating)\s*[:=]', js)
    check('W4 app.js 里没有在算任何评分', not calc, str(calc))

    html_banned = [b for b in banned if b in html]
    check('W4 页面文案里没有评价性措辞', not html_banned, '发现：%s' % html_banned)

    # W5 样式
    defined = set(re.findall(r'^\s*(--[a-z0-9-]+)\s*:', css, re.M))
    usedvars = set(re.findall(r'var\((--[a-z0-9-]+)', css))
    undef = sorted(usedvars - defined)
    check('W5 CSS 里用到的变量都定义过', not undef, '未定义：%s' % undef)

    ext_css = re.findall(r'url\(\s*["\']?https?://', css) + re.findall(r'@import', css)
    check('W5 样式表不引用外部资源（可离线）', not ext_css, str(ext_css))
    ext_html = re.findall(r'(?:src|href)="https?://', html)
    check('W5 页面不引用外部资源（可离线）', not ext_html, str(ext_html))

    # 交互的骨架必须在
    for name, pat in (
            ('顶栏页签都能点', r"\$\$?\('\.navlink'\)\.forEach"),
            ('导入弹窗有入口', r"function openImport"),
            ('练习页路由在', r"page === 'practice'"),
            ('读书页路由在', r"page === 'read'"),
            ('书内目录路由在', r"page === 'book'"),
            ('单句练习在', r"function startDrill"),
            ('对照是逐句配对的', r"function pairUp"),
            ('输入动效是 canvas 叠加，不动 textarea 里的字',
             r"function attachLive" and r"anim-layer"),
            ('动效有档位选择并能关掉', r"ANIM_NAME" and r"bindAnimPick"),
            ('笔记挂在书上', r"function loadNotes"),
            ('字体可切换', r"btn-font"),
    ):
        check('W6 ' + name, bool(re.search(pat, js)))

    print('\n' + '─' * 62)
    print('通过 %d 项，失败 %d 项' % (len(PASS), len(FAIL)))
    for n, d in FAIL:
        print('  失败：%s %s' % (n, d))
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
