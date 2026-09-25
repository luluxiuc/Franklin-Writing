# -*- coding: utf-8 -*-
"""把 run_all.py 的输出摘出关键行,方便在编码混乱的控制台里查看。

用法：python tests/summarize_run.py [输出文件]
默认读 tests/_r1.txt,写到同目录的 _summary.txt。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

KEYS = ('[!!]', '合计', '全部通过', '没过', '跳过')


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '_r1.txt')
    raw = open(src, 'rb').read()
    text = None
    for enc in ('utf-8', 'utf-16', 'gbk', 'cp936'):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = raw.decode('utf-8', 'replace')

    keep = [ln for ln in text.splitlines() if any(k in ln for k in KEYS)]
    dst = os.path.join(HERE, '_summary.txt')
    io.open(dst, 'w', encoding='utf-8', newline='\n').write('\n'.join(keep) + '\n')
    print('wrote %s (%d lines)' % (dst, len(keep)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
