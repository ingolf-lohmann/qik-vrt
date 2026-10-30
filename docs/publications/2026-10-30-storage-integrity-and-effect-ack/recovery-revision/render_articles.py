# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Reproduce the two review PDFs from the adjacent exact Markdown sources."""
from pathlib import Path
import re
from xml.sax.saxutils import escape
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parent
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
pdfmetrics.registerFont(TTFont('QIKBody', str(FONT)))
pdfmetrics.registerFont(TTFont('QIKBold', str(FONT.with_name('DejaVuSans-Bold.ttf'))))
STYLES = {
    'body': ParagraphStyle('body', fontName='QIKBody', fontSize=10,
        leading=14.2, spaceAfter=8, alignment=TA_LEFT, splitLongWords=True),
    'title': ParagraphStyle('title', fontName='QIKBold', fontSize=21,
        leading=27, spaceAfter=19, textColor=HexColor('#123946')),
    'head': ParagraphStyle('head', fontName='QIKBold', fontSize=13,
        leading=18, spaceBefore=14, spaceAfter=8, keepWithNext=True,
        textColor=HexColor('#123946')),
}

def inline(text):
    text = escape(text)
    return re.sub(r'https://[^\s]+',
        lambda m: '<link href="'+m[0].rstrip('.')+'" color="#165b72">'+m[0].rstrip('.')+'</link>'+('.' if m[0].endswith('.') else ''), text)

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('QIKBody', 7.3)
    canvas.setFillColor(HexColor('#50636a'))
    canvas.drawString(50, 30, 'Autorenprüffassung · 30.10.2026 · Ingolf Lohmann')
    canvas.drawRightString(A4[0]-50, 30, str(doc.page))
    canvas.restoreState()

def make(name, filename):
    text = (ROOT/name).read_text(encoding='utf-8')
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    blocks = re.split(r'\n\s*\n', text.strip())
    story = []
    for block in blocks:
        if block.startswith('# '): style, block = 'title', block[2:]
        elif block.startswith('## '): style, block = 'head', block[3:]
        else: style = 'body'
        chosen = STYLES[style]
        if name == 'PROSAARTIKEL.md' and style == 'body':
            chosen = ParagraphStyle('prosa', parent=chosen, fontSize=10.8,
                leading=16, spaceAfter=11)
        story.append(Paragraph(inline(' '.join(block.splitlines())), chosen))
    doc = SimpleDocTemplate(str(ROOT/filename), pagesize=A4, leftMargin=50,
        rightMargin=50, topMargin=49, bottomMargin=52,
        title=blocks[0].removeprefix('# '), author='Ingolf Lohmann; OpenAI Codex')
    doc.build(story, onFirstPage=footer, onLaterPages=footer,
        canvasmaker=lambda *a, **k: Canvas(*a, **(k | {'invariant': 1})))

if __name__ == '__main__':
    make('FACHARTIKEL.md', 'QIKVRT_Rekonstruktion_Fachartikel.pdf')
    make('PROSAARTIKEL.md', 'QIKVRT_Hier_und_Jetzt_Prosaartikel.pdf')
