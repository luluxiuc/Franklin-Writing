#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fk_llm — 只做一件事：把原文概括成提示。

用在哪：你读完原文、隔了几分钟要开始写的时候，原文已经看不见了。
这时候给你一张"这一段讲了什么"的提示卡，帮你想起内容，而不是替你想措辞。

三条硬规矩（写在提示词里，不是靠自觉）：

  1. 只概括**内容**，绝不引入原文没有的措辞、意象、形容词。
     否则你就不是凭记忆在写，而是在抄一份改写稿——那这个方法就废了。
  2. 不评价原文，不评价你的写作，不提任何"写法""风格""技巧"。
  3. 长度受限（默认 120 字以内），条数受限。
     提示越详细，你自己要记的东西就越少，训练就越轻。

接口按 OpenAI 兼容的 /chat/completions 写。DeepSeek、OpenAI、通义、Kimi、
智谱、OpenRouter、本地 Ollama / vLLM 都是这个协议，所以填个地址和模型就能用。
只用标准库，不引入任何依赖。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

# 常见服务商的默认值，用户选一个就等于填好地址和模型
PRESETS = [
    {'id': 'deepseek', 'name': 'DeepSeek',
     'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-chat',
     'key_url': 'https://platform.deepseek.com/api_keys'},
    {'id': 'openai', 'name': 'OpenAI',
     'base_url': 'https://api.openai.com/v1', 'model': 'gpt-4o-mini',
     'key_url': 'https://platform.openai.com/api-keys'},
    {'id': 'dashscope', 'name': '通义千问（阿里云）',
     'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
     'model': 'qwen-plus', 'key_url': 'https://bailian.console.aliyun.com/'},
    {'id': 'moonshot', 'name': 'Kimi（月之暗面）',
     'base_url': 'https://api.moonshot.cn/v1', 'model': 'moonshot-v1-8k',
     'key_url': 'https://platform.moonshot.cn/console/api-keys'},
    {'id': 'zhipu', 'name': '智谱 GLM',
     'base_url': 'https://open.bigmodel.cn/api/paas/v4', 'model': 'glm-4-flash',
     'key_url': 'https://open.bigmodel.cn/usercenter/apikeys'},
    {'id': 'openrouter', 'name': 'OpenRouter',
     'base_url': 'https://openrouter.ai/api/v1', 'model': 'openai/gpt-4o-mini',
     'key_url': 'https://openrouter.ai/keys'},
    {'id': 'ollama', 'name': '本地 Ollama（不需要 Key）',
     'base_url': 'http://127.0.0.1:11434/v1', 'model': 'qwen2.5:7b',
     'key_url': ''},
    {'id': 'custom', 'name': '其它 OpenAI 兼容接口',
     'base_url': '', 'model': '', 'key_url': ''},
]

# ── 提示词 ──────────────────────────────────────────────────────────
#
# 这里的核心是**逐句**：一句原文对应一条提示。
#
# 为什么是逐句，而不是把整段概括成几条：
#   · 富兰克林原本的做法就是 "made short hints of the sentiment of each sentence"
#     —— 逐句记要旨，搁几天，再看着这些提示把整篇重新写出来；
#   · 这个练习的目的正是"写好每一句话"，所以提示的单位就该是句子；
#   · 段落概括会把原文重新组织一遍，那个组织结构是模型的，不是你的；
#     更糟的是它很容易把原文的措辞带进来，你照着写就成了抄写。
#
# 三条不能省的约束（省掉任何一条，提示就会变成"替你写"）：
#   1. 一句一条，条数必须与句数一致 —— 否则会重新组织内容；
#   2. 不得复用原文的措辞、比喻、形容词 —— 否则你是在抄；
#   3. 不评价、不给写作建议 —— 判断是你的，不是它的。
PROMPT_VERSION = 3

SYSTEM_PROMPT = (
    '用户在做富兰克林式的写作练习：他读过一段文字，原文已收起，'
    '要凭"每句话的提示"把这段文字重新写出来。\n'
    '你的任务是给每句话配一条提示。\n'
    '必须做到：\n'
    '1. 原文有几句话，就写几条，一条不多一条不少，顺序照原文。\n'
    '2. 每条只说这句话"讲了什么"，用你自己的话，'
    '绝不能复用原文的词句、比喻、形容词或句式——他用这些提示重写时，'
    '一旦看到原文的措辞就会直接抄，练习就白做了。\n'
    '3. 不评价原文，不提风格、手法、修辞，不给任何写作建议。\n'
    '每条尽量短，像给自己留的备忘。用最普通的现代汉语。'
)

USER_TEMPLATE = (
    '下面这段原文共 {n_sent} 句（已按句号、问号、叹号分好，见编号）。\n'
    '请为每一句写一条提示：\n'
    '· 严格 {n_sent} 条，每行一条，行首写句子编号，如 "3. ..."；\n'
    '· 每条不超过 {max_chars} 字；\n'
    '· 每条只讲那一句的内容，不要合并、不要拆分、不要补充原文没有的信息；\n'
    '· 用词必须和原文明显不同。\n'
    '\n'
    '{numbered}\n'
)

# 原文超过这个长度就截断再生成。再长下去，多出来的字基本只增加成本，
# 对"想起这一段讲了什么"没有帮助。
MAX_INPUT_CHARS = 2200


def numbered_sentences(text: str) -> list[str]:
    """把原文按句切开并编号。这是"一句一条提示"的基准。

    用 fk_store.nonempty_sentences：**两边必须是同一个函数**，
    否则提示的条数会和界面上的句子对不上——网页复制来的文章常带空格，
    用裸的 split_sentences 会数出"空句子"，编号就飘了。
    """
    import fk_store as _S
    return _S.nonempty_sentences(text or '')


class LlmError(Exception):
    def __init__(self, message, code=502, hint=''):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint


def _endpoint(base_url: str) -> str:
    base = (base_url or '').strip().rstrip('/')
    if not base:
        raise LlmError('还没有填接口地址。', 400,
                       '到「设置」里选一个服务商，或者填自己的 OpenAI 兼容地址。')
    if base.endswith('/chat/completions'):
        return base
    return base + '/chat/completions'


def check_ready(settings: dict) -> tuple[bool, str]:
    """能不能调用。返回 (可以吗, 不能的原因)。

    顺手挡住 Key 里的非法字符：HTTP 头只能是 latin-1，Key 里混进中文或者
    全角空格（从网页复制时很常见）会在发请求时炸在编码上，报出来的错
    和"Key 不对"完全不像，很难查。在这里拦住，说人话。
    """
    base = settings.get('base_url') or ''
    key = (settings.get('api_key') or '').strip()
    model = (settings.get('model') or '').strip()
    if not model:
        return False, '还没有填模型名。'
    if not base:
        return False, '还没有填接口地址。'
    if key:
        bad = [c for c in key if ord(c) > 126 or ord(c) < 33]
        if bad:
            return False, ('API Key 里有不合法字符（%s…）。'
                           '多半是从网页复制时带了中文或者空格，请重新复制一次。'
                           % ''.join(bad[:3]))
    if not key and 'localhost' not in base and '127.0.0.1' not in base:
        return False, '还没有填 API Key。'
    return True, ''


def chat(settings: dict, system: str, user: str, timeout: int = 90,
         max_tokens: int = 600, temperature: float = 0.3) -> dict:
    """调一次对话接口。

    返回 {'text', 'usage', 'model'}。usage 里是服务商报的 token 数
    （OpenAI 兼容接口都会给），拿不到就返回 None——**不估算、不假装知道**。
    """
    base = settings.get('base_url') or ''
    key = (settings.get('api_key') or '').strip()
    model = (settings.get('model') or '').strip()
    ok, why = check_ready(settings)
    if not ok:
        raise LlmError(why, 400, '到「设置」里填上，Key 只存在这台机器上。')

    body = {
        'model': model,
        'messages': [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': user}],
        'temperature': temperature,
        'max_tokens': max_tokens,
        'stream': False,
    }
    req = urllib.request.Request(
        _endpoint(base), data=json.dumps(body).encode('utf-8'), method='POST')
    req.add_header('Content-Type', 'application/json')
    if key:
        req.add_header('Authorization', 'Bearer ' + key)
    req.add_header('User-Agent', 'fk-writing-tool/2')

    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:400]
        hint = {
            401: 'Key 不对或者过期了。',
            403: '这个 Key 没有调用该模型的权限。',
            404: '接口地址或模型名不对。检查一下 base_url 和 model。',
            429: '被限流了。等一会儿再试，或者把批量生成的并发调低。',
        }.get(e.code, '')
        raise LlmError('模型接口返回 %s：%s' % (e.code, detail), 502, hint)
    except urllib.error.URLError as e:
        raise LlmError('连不上模型接口：%s' % (e.reason,), 502,
                       '检查网络、代理，以及 base_url 是否写对。')
    except TimeoutError:
        raise LlmError('模型接口超时了。', 504, '网络慢或者原文太长，可以少选一点再试。')

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise LlmError('接口返回的不是 JSON：%s' % raw[:200], 502)

    if isinstance(data, dict) and data.get('error'):
        err = data['error']
        msg = err.get('message') if isinstance(err, dict) else str(err)
        raise LlmError('模型接口报错：%s' % msg, 502)

    try:
        choices = data['choices']
        msg = choices[0]['message']
        text = msg.get('content')
        if text is None and msg.get('reasoning_content'):
            text = msg['reasoning_content']
        text = (text or '').strip()
    except (KeyError, IndexError, TypeError):
        raise LlmError('接口返回的结构看不懂：%s' % raw[:200], 502)

    if not text:
        raise LlmError('模型返回了空内容。', 502, '换个模型试试。')

    usage = data.get('usage') if isinstance(data, dict) else None
    if isinstance(usage, dict):
        usage = {'in': usage.get('prompt_tokens'),
                 'out': usage.get('completion_tokens')}
        if usage['in'] is None and usage['out'] is None:
            usage = None
    else:
        usage = None

    return {'text': text, 'usage': usage, 'model': model}


def budget(text: str) -> tuple[int, int]:
    """按这一段的长度决定**每条提示**的字数上限。返回 (条数上限, 每条多少字)。

    条数上限只是防止模型话痨的保险，真正的条数由句子数决定（一句一条）。
    单条要短：提示像给自己留的备忘，写得越详尽，你自己要记的就越少。
    这也是省钱的地方——输出 token 直接由"句数 × 单条上限"封顶。
    """
    return 0, 0


def per_hint_chars(n_sent: int) -> int:
    """一句提示最多多少字。句子多的时候给得紧一点。"""
    if n_sent <= 4:
        return 22
    if n_sent <= 8:
        return 18
    return 15


def _split_points(out: str) -> list[str]:
    """把模型输出拆成一条条。行首的编号、"1." "·" "-" 都去掉。"""
    points = []
    for line in (out or '').split('\n'):
        s = line.strip()
        if not s:
            continue
        s = re.sub(r'^\s*(?:[-*·•]|\(?\d+[.、)）]|第[一二三四五六七八九十]+[、.]?)\s*', '', s)
        s = s.strip()
        if s:
            points.append(s)
    return points


def hints_raw(settings: dict, text: str, timeout: int = 120) -> dict:
    """真的去调一次模型，拿逐句提示。缓存那一层在 fk_summary.py 里。

    返回 {'hints': [{'no','hint'}...], 'sentences': [...], ...}。
    条数和句数对不上时**如实报出来**（对齐情况放在 'aligned' 里），
    由界面决定怎么显示，而不是假装没这回事。
    """
    text = (text or '').strip()
    if not text:
        raise LlmError('这一段是空的。', 400)

    sents = numbered_sentences(text)
    if not sents:
        raise LlmError('这一段切不出句子。', 400)

    capped = text[:MAX_INPUT_CHARS]
    capped_sents = numbered_sentences(capped)
    n = len(capped_sents)
    max_chars = per_hint_chars(n)
    numbered = '\n'.join('%d. %s' % (i + 1, s) for i, s in enumerate(capped_sents))

    t0 = time.time()
    out = chat(settings, SYSTEM_PROMPT,
               USER_TEMPLATE.format(n_sent=n, numbered=numbered, max_chars=max_chars),
               timeout=timeout, max_tokens=n * max_chars * 2 + 100)
    secs = round(time.time() - t0, 1)

    raw_points = _split_points(out['text'])
    hints = []
    for i, h in enumerate(raw_points[:n]):
        hints.append({'no': i + 1, 'hint': h})
    return {
        'hints': hints,
        'sentences': capped_sents,
        'n_sent': n,
        'n_hint': len(raw_points),
        'aligned': len(raw_points) == n,
        'model': out.get('model', ''),
        'usage': out.get('usage'),
        'seconds': secs,
        'at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'truncated': len(text) > MAX_INPUT_CHARS,
    }


def test_connection(settings: dict) -> dict:
    """设置页的"测试连接"。用一次极短的调用确认地址、Key、模型都对。"""
    t0 = time.time()
    out = chat(settings, '你是测试助手。',
               '只回答两个字：连上了', timeout=30, max_tokens=16)
    return {'ok': True, 'reply': out['text'].strip()[:40],
            'model': settings.get('model', ''),
            'usage': out.get('usage'),
            'seconds': round(time.time() - t0, 1)}


def key_hint(key: str) -> str:
    """只用来在界面上显示"已填的 Key 长什么样"，不泄露完整 Key。"""
    k = (key or '').strip()
    if not k:
        return ''
    if len(k) <= 10:
        return k[:2] + '…'
    return '%s…%s（%d 位）' % (k[:5], k[-4:], len(k))
