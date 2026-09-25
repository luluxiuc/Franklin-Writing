#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all — 一次跑完全部测试，并给出汇总。

用法：python tests/run_all.py
退出码 0 = 全绿。

渲染检查（render_check.mjs）需要一个正在跑的服务。这里会**自己起一个带假模型的
服务**（tests/serve_stub.py），跑完关掉——所以不依赖你手动开服务，
也不会真的去调模型花钱。
"""
import atexit
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUB_PORT = 8137
BASE = 'http://127.0.0.1:%d' % STUB_PORT

SUITES = [
    ('数据层', 'test_store.py', '切分可逆、分段兜底、存档、状态机', None),
    ('提示卡', 'test_summary.py', '逐句提示、缓存、账目、批量、照抄检查', None),
    ('服务层', 'test_server.py', '端到端 HTTP；不泄露原文、笔记挂在书上', None),
    ('前端契约', 'test_frontend.py', 'JS 与 HTML 的元素/接口对应关系', None),
    ('按钮点得动', 'ui_check.mjs', '渲染出来的按钮点了真的有反应', 'node'),
    ('输入动效', 'anim_check.mjs', '动效能挂能拆、不该触发的不触发', 'node'),
    ('前端渲染', 'render_check.mjs', '真跑一遍每个页面的渲染', 'node'),
]

_procs = []
_tmpdirs = []


def have(cmd):
    return shutil.which(cmd) is not None


def port_busy(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(('127.0.0.1', port)) == 0


def wait_up(url, timeout=12):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False


def health():
    """读 /api/health。读不到返回 None。"""
    try:
        with urllib.request.urlopen(BASE + '/api/health', timeout=2) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return None


def start_stub():
    """起一个带假模型的服务，供渲染检查用。

    端口上已经有服务时，**必须确认它是假模型服务**才能复用。
    光看"端口通不通"不够：本地开发时 8137 上常常跑着一个真服务，
    那样渲染检查会去连真模型，既慢又可能失败，而且报出来的错
    （网络错误、拿不到提示）看不出真正的原因。这个坑踩过一次，所以现在显式检查。
    """
    if port_busy(STUB_PORT):
        h = health()
        if h and h.get('tool') == 'fk' and h.get('stub'):
            print('（8137 上已经跑着假模型服务，直接用它）')
            return None
        print('  [!!] 8137 端口被占用，而且占用它的不是假模型服务，是别的东西。')
        if h and h.get('tool') == 'fk':
            print('       看起来是你自己的富兰克林写作服务（真服务，会去连真模型）。')
        print('       渲染检查需要一个假模型服务，否则会去连真模型、结果不可信。')
        print('       请先关掉它，或者让 runner 自己起：')
        print('         Windows:  Get-CimInstance Win32_Process -Filter "Name like \'%%python%%\'" |')
        print('                   ForEach-Object { Invoke-CimMethod -InputObject $_ -MethodName Terminate }')
        print('         其它:     lsof -ti tcp:%d | xargs kill' % STUB_PORT)
        print('       不放心的话，直接杀掉再重跑本脚本即可。')
        return None
    data = tempfile.mkdtemp(prefix='fk_runall_')
    _tmpdirs.append(data)
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    p = subprocess.Popen(
        [sys.executable, os.path.join(HERE, 'serve_stub.py'),
         '--port', str(STUB_PORT), '--data', data],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=ROOT)
    _procs.append(p)
    if not wait_up(BASE + '/api/health'):
        print('  [!!] 起不了测试服务，渲染检查会跳过')
        return None
    return p


def cleanup():
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    for d in _tmpdirs:
        shutil.rmtree(d, ignore_errors=True)


atexit.register(cleanup)


def count_checks(out):
    """从一套测试的输出里读它自己报的检查项数。

    各套件的收尾格式统一是「通过 N 项，失败 M 项」，所以这里读实际执行结果，
    而不是去源码里数断言 —— 后者会把被跳过的、循环里生成的都算错。
    """
    passed = total = 0
    for m in re.finditer(r'通过\s*(\d+)\s*项[，,]\s*失败\s*(\d+)\s*项', out):
        p, f = int(m.group(1)), int(m.group(2))
        passed += p
        total += p + f
    return passed, total


def main():
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    need_server = any(s[1].endswith('.mjs') for s in SUITES)
    if need_server and have('node'):
        print('准备测试服务（假模型，不联网）……')
        start_stub()

    results = []
    checks_passed = checks_total = 0
    for label, script, note, need in SUITES:
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            results.append((label, None, '缺少 %s' % script))
            print('\n%s　—　跳过：找不到 %s' % (label, script))
            continue
        if need and not have(need):
            results.append((label, None, '没装 %s' % need))
            print('\n%s　—　跳过：没装 %s' % (label, need))
            continue
        if script.endswith('.mjs') and not wait_up(BASE + '/api/health', timeout=1):
            results.append((label, None, '测试服务没起来'))
            print('\n%s　—　跳过：测试服务没起来' % label)
            continue

        print('\n' + '═' * 70)
        print('%s　—　%s' % (label, note))
        print('═' * 70)
        cmd = ['node', path] if script.endswith('.mjs') else [sys.executable, path]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, env=env, cwd=ROOT)
        out = p.stdout.decode('utf-8', 'replace')
        print(out.rstrip())
        if p.returncode != 0 and p.stderr:
            err = p.stderr.decode('utf-8', 'replace').rstrip()
            if err:
                print(err)
        passed, total = count_checks(out)
        checks_passed += passed
        checks_total += total
        results.append((label, p.returncode == 0, '%.1f 秒' % (time.time() - t0)))

    print('\n' + '═' * 70)
    print('汇总')
    print('═' * 70)
    width = max(len(x[0]) for x in results)
    bad = 0
    for label, ok, note in results:
        mark = '通过' if ok else ('跳过' if ok is None else '失败')
        if ok is False:
            bad += 1
        print('  %-*s  %s  %s' % (width + 4, label, mark, note))
    print()
    # 总检查数由各套件自己报的"通过 N 项，失败 M 项"加出来 —— 读的是实际执行结果，
    # 不是去数源码里有几个断言。README 里引用的就是这个数。
    if checks_total:
        print('检查项合计：%d 项，通过 %d 项，失败 %d 项。'
              % (checks_total, checks_passed, checks_total - checks_passed))
    if bad:
        print('有 %d 组没过，别发版。' % bad)
    else:
        print('全部通过。')
    cleanup()
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
