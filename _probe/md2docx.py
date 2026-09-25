# -*- coding: utf-8 -*-
"""极简 Markdown → docx（无需第三方库）。支持 #/##/###/####、段落、引用、表格、
代码块、无序/有序列表、粗体、行内代码、水平线。
用法: python md2docx.py <in.md> <out.docx>
"""
import sys, re, zipfile, io, os

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
CN = '微软雅黑'
EN = 'Calibri'

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def rpr(sz=21, b=False, mono=False, color=None):
    f = f'<w:rFonts w:ascii="{sys.intern("Consolas" if mono else EN)}" w:eastAsia="{CN}" w:hAnsi="{sys.intern("Consolas" if mono else EN)}"/>'
    x = f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    if b: x += '<w:b/>'
    if color: x += f'<w:color w:val="{color}"/>'
    return '<w:rPr>' + f + x + '</w:rPr>'

def para(text, sz=21, b=False, style=None, indent=None, shade=None, mono=False):
    ppr = ''
    inner = ''
    if style: inner += f'<w:pStyle w:val="{style}"/>'
    if indent: inner += f'<w:ind w:left="{indent}"/>'
    if shade: inner += f'<w:shd w:val="clear" w:fill="{shade}"/>'
    if inner: ppr = '<w:pPr>' + inner + '</w:pPr>'
    # 行内解析：`code` 与 **bold**
    runs, rest = '', text
    toks = re.split(r'(\*\*.+?\*\*|`[^`]+`)', rest)
    for tk in toks:
        if not tk: continue
        if tk.startswith('**') and tk.endswith('**') and len(tk) > 4:
            runs += f'<w:r>{rpr(sz, True)}<w:t xml:space="preserve">{esc(tk[2:-2])}</w:t></w:r>'
        elif tk.startswith('`') and tk.endswith('`') and len(tk) > 2:
            runs += f'<w:r>{rpr(sz-2, mono=True)}<w:t xml:space="preserve">{esc(tk[1:-1])}</w:t></w:r>'
        else:
            runs += f'<w:r>{rpr(sz, b, mono)}<w:t xml:space="preserve">{esc(tk)}</w:t></w:r>'
    return f'<w:p>{ppr}{runs}</w:p>'

def table(rows):
    out = ['<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>'
           + ''.join(f'<w:{s} w:val="single" w:sz="4" w:color="AAAAAA"/>'
                     for s in ('top','left','bottom','right','insideH','insideV'))
           + '</w:tblBorders></w:tblPr>']
    for ri, r in enumerate(rows):
        out.append('<w:tr>')
        for c in r:
            shd = '<w:shd w:val="clear" w:fill="F2F2F2"/>' if ri == 0 else ''
            out.append('<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/>' + shd + '</w:tcPr>'
                       + para(c, sz=19, b=(ri == 0)) + '</w:tc>')
        out.append('</w:tr>')
    out.append('</w:tbl>' + para(''))
    return ''.join(out)

def convert(src, dst):
    lines = open(src, encoding='utf-8').read().split('\n')
    body, i, in_code, code_buf = [], 0, False, []
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith('```'):
            if in_code:
                for cl in code_buf:
                    body.append(para(cl if cl.strip() else ' ', sz=18, mono=True, shade='F5F5F5'))
                code_buf, in_code = [], False
            else:
                in_code = True
            i += 1; continue
        if in_code:
            code_buf.append(ln); i += 1; continue

        if re.match(r'^\s*\|', ln):
            rows = []
            while i < len(lines) and re.match(r'^\s*\|', lines[i]):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not re.match(r'^[\s\-:|]+$', lines[i].strip().strip('|')):
                    rows.append(cells)
                i += 1
            if rows: body.append(table(rows))
            continue

        m = re.match(r'^(#{1,6})\s+(.*)$', ln)
        if m:
            lvl, txt = len(m.group(1)), m.group(2)
            style = {1: 'Title', 2: 'Heading1', 3: 'Heading2'}.get(lvl, 'Heading3')
            body.append(para(txt, sz=26 if lvl == 1 else 23 if lvl == 2 else 21,
                             b=True, style=style))
            i += 1; continue

        if re.match(r'^\s*(---|\*\*\*|___)\s*$', ln):
            body.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:color="BBBBBB"/></w:pBdr></w:pPr></w:p>')
            i += 1; continue

        m = re.match(r'^>\s?(.*)$', ln)
        if m:
            body.append(para(m.group(1), sz=20, indent=240))
            i += 1; continue

        m = re.match(r'^(\s*)[-*]\s+(.*)$', ln)
        if m:
            depth = len(m.group(1)) // 2
            body.append(para('• ' + m.group(2), indent=240 + depth * 240))
            i += 1; continue

        m = re.match(r'^(\s*)(\d+)\.\s+(.*)$', ln)
        if m:
            body.append(para(f'{m.group(2)}. {m.group(3)}', indent=240))
            i += 1; continue

        if ln.strip() == '':
            i += 1; continue

        body.append(para(ln))
        i += 1

    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<w:document xmlns:w="{W}"><w:body>' + ''.join(body) +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
           '<w:pgMar w:top="1418" w:right="1418" w:bottom="1418" w:left="1418"/></w:sectPr>'
           '</w:body></w:document>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
    tmp = dst + '.tmp'
    if os.path.exists(tmp): os.remove(tmp)
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', doc)
    try:
        os.replace(tmp, dst)
    except PermissionError:
        print(f'!! 目标被占用，已写入 {os.path.basename(tmp)}（关闭 Word 后改名即可）')
        return len(doc), tmp
    return len(doc), dst

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    n, real = convert(src, dst)
    print(f'OK  {os.path.basename(real)}  document.xml={n} chars  size={os.path.getsize(real)} bytes')
