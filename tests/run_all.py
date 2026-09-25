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
# 优先用 8137（和真服务同端口，便于对照）。被占用就往后找 —— 不要为了一个
# 端口去打断使用者正开着的服务，那既粗鲁又容易在"杀了进程但端口还没释放"的
# 时序上翻车（踩过：连跑两次，第一次刚 kill 完，第二次就失败）。
PREFERRED_PORT = 8137
PORT_TRIES = 20

SUITES = [
    ('数据层', 'test_store.py', '切分可逆、分段兜底、存档、状态机', None),
    ('提示卡', 'test_summary.py', '逐句提示、缓存、账目、批量、照抄检查', None),
    ('服务层', 'test_server.py', '端到端 HTTP；不泄露原文、笔记挂在书上', None),
    ('前端契约', 'test_frontend.py', 'JS 与 HTML 的元素/接口对应关系', None),
    ('按钮点得动', 'ui_check.mjs', '渲染出来的按钮点了真的有反应', 'node'),
    ('输入动效', 'anim_check.mjs', '动效能挂能拆、不该触发的不触发', 'node'),
    ('前端渲染', 'render_check.mjs', '真跑一遍每个页面的渲染', 'node'),
]

# 这两个套件用的是假 DOM，不需要服务。
NO_SERVER = {'ui_check.mjs', 'anim_check.mjs'}

STUB_PORT = PREFERRED_PORT
BASE = 'http://127.0.0.1:%d' % STUB_PORT

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
    """起一个带假模型的服务，供渲染检查用。返回 True 表示"可用"。

    策略：先看首选端口。上面如果已经跑着**假模型服务**，直接复用；
    跑着别的东西（比如使用者自己的真服务）或者干脆起不来，就**换一个空闲端口**，
    而不是打断使用者、也不是跳过检查。只有连一个端口都占不到才返回 False。

    为什么要这么绕：
      1. 真服务也能让 /api/health 返回 200。套件照跑的话会去连真模型，
         然后在"能拿到逐句提示"那里失败 —— 看起来像功能坏了，其实是环境不对。
      2. 反过来"先杀进程再跑"也不行：连跑两次时，第一次刚杀完、端口还没释放，
         第二次就失败。这个偶发红灯折腾过很久，根因就是这个时序。
         所以最终方案是**不去动别人的进程，自己换个端口**。
    """
    global STUB_PORT, BASE
    for port in range(PREFERRED_PORT, PREFERRED_PORT + PORT_TRIES):
        STUB_PORT = port
        BASE = 'http://127.0.0.1:%d' % port
        if port_busy(port):
            h = health()
            if h and h.get('tool') == 'fk' and h.get('stub'):
                print('（%d 上已经跑着假模型服务，直接用它）' % port)
                return True
            # 端口被别的东西占着 —— 不打扰它，试下一个
            continue
        data = tempfile.mkdtemp(prefix='fk_runall_')
        _tmpdirs.append(data)
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        p = subprocess.Popen(
            [sys.executable, os.path.join(HERE, 'serve_stub.py'),
             '--port', str(port), '--data', data],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=ROOT)
        _procs.append(p)
        if wait_up(BASE + '/api/health'):
            if port != PREFERRED_PORT:
                print('（%d 被占用，假模型服务改用端口 %d）' % (PREFERRED_PORT, port))
            return True
        # 这个端口起不来，继续往下试
        try:
            p.terminate()
        except Exception:
            pass

    print('  [!!] 从 %d 起试了 %d 个端口都起不了假模型服务，需要服务的那几个套件会跳过。'
          % (PREFERRED_PORT, PORT_TRIES))
    return False


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
    stub_ok = True
    # 只有 render_check 需要服务；另外两个 .mjs 用假 DOM，自己就能跑。
    if have('node'):
        print('准备测试服务（假模型，不联网）……')
        stub_ok = start_stub()

    results = []
    checks_passed = checks_total = 0
    for label, script, note, need in SUITES:
        path = os.path.join(HERE, script)
        if not os.path.exists(path):
            results.append((label, None, '缺少 %s' % script))
            print('\n%s　—　跳过：找不到 %s' % (label, script))
            continue
        if need and not have(need):
            results.append((label, None, '跳过：没装 %s' % need))
            print('\n%s　—　跳过：没装 %s' % (label, need))
            continue
        wants_server = script.endswith('.mjs') and script not in NO_SERVER
        if wants_server and not stub_ok:
            results.append((label, None, '没有假模型服务，跳过'))
            print('\n%s　—　跳过：起不了假模型服务（见上面的说明）' % label)
            continue
        if wants_server and not wait_up(BASE + '/api/health', timeout=1):
            results.append((label, None, '测试服务没起来'))
            print('\n%s　—　跳过：测试服务没起来' % label)
            continue

        print('\n' + '═' * 70)
        print('%s　—　%s' % (label, note))
        print('═' * 70)
        if script.endswith('.mjs'):
            cmd = ['node', path]
            # render_check 支持传服务地址；端口是动态选的，必须传进去。
            if wants_server:
                cmd.append(BASE)
        else:
            cmd = [sys.executable, path]
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
