#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
docs_check — 文档自检。

三件事:
  1. 相对链接是否存在(README 里链接很多,写错一个就是死链)
  2. 有没有 API Key / 密钥被提交进来
  3. 实验数据里的 JSON 是否都能解析

用法：python tests/docs_check.py
退出码 0 = 全绿。

只在 git 仓库里跑得动(会用 git ls-files 确定"哪些文件会被提交")。
不是 git 仓库时退化为扫描当前目录,并跳过被忽略路径的判断。
"""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

fails = []
checks = 0


def ok(msg):
    global checks
    checks += 1
    print('  [ok] %s' % msg)


def bad(msg):
    global checks
    checks += 1
    fails.append(msg)
    print('  [!!] %s' % msg)


def tracked_files():
    """会被提交的文件列表（相对 ROOT）。

    重要：必须先确认 git 仓库的根就是 ROOT。否则在仓库子目录里跑，git ls-files
    返回的是相对仓库根的路径，拼到 ROOT 上会全部对不上，检查会静默失效。
    """
    try:
        top = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT,
                             capture_output=True, check=True)
        top = os.path.normpath(top.stdout.decode('utf-8', 'replace').strip())
        if os.path.normcase(top) == os.path.normcase(ROOT):
            out = subprocess.run(['git', 'ls-files'], cwd=ROOT,
                                 capture_output=True, check=True)
            names = out.stdout.decode('utf-8', 'replace').splitlines()
            if names:
                print('（用 git ls-files，仓库根 = 项目根）')
                return [n for n in names if n.strip()]
    except Exception:
        pass
    # 退化为扫目录：仓库根不是项目根，或者根本不在 git 里
    print('（不在本项目的 git 仓库里，退化为扫描目录）')
    skip = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, f), ROOT).replace('\\', '/'))
    return out


# ---------------------------------------------------------------- 链接检查

LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+?)(?:\s+"[^"]*")?\)')


def check_links(files):
    print('\n一、文档里的相对链接是否都存在')
    md = [f for f in files if f.lower().endswith('.md')]
    if not md:
        bad('一个 .md 都没找到，链接检查无从谈起')
        return
    checked = 0
    for rel in md:
        full = os.path.join(ROOT, rel.replace('/', os.sep))
        if not os.path.exists(full):
            continue
        try:
            text = io.open(full, encoding='utf-8').read()
        except Exception as e:
            bad('%s 读不了：%s' % (rel, e))
            continue
        for target in LINK.findall(text):
            if target.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            if target.startswith('data:'):
                continue
            path_part = target.split('#', 1)[0]
            if not path_part:
                continue
            # 相对本文档解析
            base = os.path.dirname(full)
            resolved = os.path.normpath(os.path.join(base, path_part.replace('/', os.sep)))
            checked += 1
            if not os.path.exists(resolved):
                bad('%s → 链接指向不存在的路径：%s' % (rel, target))
    ok('检查了 %d 个 .md 里的 %d 条相对链接' % (len(md), checked))


# ---------------------------------------------------------------- 密钥检查

KEY_PATTERNS = [
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), 'OpenAI 风格的密钥'),
    (re.compile(r'sk-ant-[A-Za-z0-9_\-]{20,}'), 'Anthropic 风格的密钥'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AWS Access Key ID'),
    (re.compile(r'ghp_[A-Za-z0-9]{30,}'), 'GitHub Personal Access Token'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{30,}'), 'GitHub fine-grained PAT'),
    (re.compile(r'AIza[0-9A-Za-z_\-]{30,}'), 'Google API Key'),
]

# 这些是测试用的假 Key，明确允许
ALLOW = re.compile(r'sk-(test|stub|demo)-[A-Za-z0-9]+')

TEXT_EXT = {'.py', '.js', '.mjs', '.json', '.md', '.yml', '.yaml', '.txt',
            '.html', '.css', '.cff', '.cmd', '.sh', '.cfg', '.toml', ''}


def check_secrets(files):
    print('\n二、有没有密钥被提交进来')
    hits = 0
    scanned = 0
    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in TEXT_EXT:
            continue
        full = os.path.join(ROOT, rel.replace('/', os.sep))
        if not os.path.exists(full):
            continue
        try:
            text = io.open(full, encoding='utf-8', errors='replace').read()
        except Exception:
            continue
        scanned += 1
        for pat, label in KEY_PATTERNS:
            for m in pat.finditer(text):
                frag = m.group(0)
                if ALLOW.match(frag):
                    continue
                line = text[:m.start()].count('\n') + 1
                bad('%s 第 %d 行疑似%s：%s…' % (rel, line, label, frag[:12]))
                hits += 1
    ok('扫描了 %d 个文本文件' % scanned)
    if not hits:
        ok('没有发现真实密钥（测试用的 sk-test-/sk-stub-/sk-demo- 已排除）')


def check_runtime_data(files):
    print('\n三、使用者的私人数据没有被提交')
    leaked = [f for f in files if f.startswith('app/data/')
              and not f.endswith('README.md')]
    if leaked:
        for f in leaked:
            bad('私人数据进了仓库：%s（应被 .gitignore 排除）' % f)
    else:
        ok('app/data/ 下没有私人数据被跟踪')

    corpus = [f for f in files if re.search(r'(corpus|语料)/', f)]
    if corpus:
        for f in corpus:
            bad('语料文件进了仓库：%s（受版权保护的原文不应分发）' % f)
    else:
        ok('没有语料原文被跟踪')


def check_json(files):
    print('\n四、实验数据里的 JSON 是否都能解析')
    jsons = [f for f in files if f.endswith('.json')]
    if not jsons:
        ok('没有 .json 需要检查')
        return
    for rel in jsons:
        full = os.path.join(ROOT, rel.replace('/', os.sep))
        try:
            json.load(io.open(full, encoding='utf-8'))
            ok('%s 可解析' % rel)
        except Exception as e:
            bad('%s 解析失败：%s' % (rel, e))


def check_citation(files):
    print('\n五、CITATION.cff 是否可解析')
    rel = 'CITATION.cff'
    if rel not in files:
        bad('缺少 CITATION.cff')
        return
    full = os.path.join(ROOT, rel)
    text = io.open(full, encoding='utf-8').read()
    # 极简 YAML 结构检查：顶层键在行首且不以空格开头
    top = [ln.split(':', 1)[0] for ln in text.splitlines()
           if ln and not ln[0].isspace() and ':' in ln and not ln.startswith('#')]
    required = ['cff-version', 'message', 'title', 'authors', 'license']
    missing = [k for k in required if k not in top]
    if missing:
        bad('CITATION.cff 缺少必备顶层字段：%s' % '、'.join(missing))
    else:
        ok('CITATION.cff 顶层字段齐全（%d 个）' % len(top))


def main():
    print('=' * 70)
    print('文档与仓库自检')
    print('=' * 70)
    files = tracked_files()
    print('待检查文件 %d 个（来自 git ls-files）' % len(files))
    check_links(files)
    check_secrets(files)
    check_runtime_data(files)
    check_json(files)
    check_citation(files)

    print('\n' + '=' * 70)
    print('共 %d 项检查，%d 项失败' % (checks, len(fails)))
    print('=' * 70)
    for f in fails:
        print('  - %s' % f)
    if fails:
        print('\n有 %d 项没过，别发版。' % len(fails))
        return 1
    print('\n全部通过。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
