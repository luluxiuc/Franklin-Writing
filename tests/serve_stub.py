#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve_stub — 起一个带"假模型"的服务，专供渲染测试用。

为什么需要它：渲染测试要从真实接口拿数据（包括逐句提示），
但真调模型既慢又花钱。这个入口把 LLM.chat 换成假实现，
其余一切照旧——所以页面拿到的是真接口、真数据，只是提示是假模型写的。

用法：python tests/serve_stub.py [--port 8137] [--data <目录>]
"""
import argparse
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(ROOT, 'app'))

import fk_llm as LLM          # noqa: E402
import fk_server as SRV       # noqa: E402


def fake_chat(settings, system, user, **kw):
    """按请求里的句子编号，一句一条地回。行为上像真模型：条数跟着句数走。"""
    if '测试助手' in system:
        return {'text': '连上了', 'usage': {'in': 12, 'out': 3},
                'model': settings.get('model', '')}
    ns = [int(m.group(1)) for m in re.finditer(r'^(\d+)\. ', user, re.M)]
    body = '\n'.join('%d. 第 %d 句讲的内容提示。' % (n, n) for n in ns)
    return {'text': body, 'usage': {'in': 480 + 20 * len(ns), 'out': 12 * len(ns)},
            'model': settings.get('model', '')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8137)
    ap.add_argument('--data', default=None)
    a = ap.parse_args()

    data = a.data
    if not data:
        data = os.path.join(tempfile.gettempdir(), 'fk_render_check')
        os.makedirs(data, exist_ok=True)

    LLM.chat = fake_chat
    # 让 /api/health 自报"我是假模型服务"。测试跑器（run_all.py）靠这个字段
    # 分辨 8137 上跑的是假模型还是真服务——如果误用了真服务，提示会走真模型，
    # 既慢又可能失败，还会让渲染检查挂在一个看不出原因的地方。
    SRV.STUB = True
    print('（假模型已装好：不会联网，但接口链路是真的）', file=sys.stderr)
    return SRV.serve(data_dir=data, port=a.port, open_browser=False, quiet=True)


if __name__ == '__main__':
    sys.exit(main())
