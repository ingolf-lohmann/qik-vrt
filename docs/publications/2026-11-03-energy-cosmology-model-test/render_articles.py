# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Extend the existing QIK-VRT reportlab Markdown renderer for this experiment.

Reused basis: docs/publications/2026-10-30-storage-integrity-and-effect-ack/
recovery-revision/render_articles.py, Git blob d990e64d41a82ae2ff598720c744f97ea30f7d29.
Additions: tables, figure, formula blocks, source attachments, current date.
"""
from pathlib import Path
import csv
import json
import math
import re
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader, PdfWriter

ROOT=Path(__file__).resolve().parent
FONT=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
pdfmetrics.registerFont(TTFont('QIKBody',str(FONT)))
pdfmetrics.registerFont(TTFont('QIKBold',str(FONT.with_name('DejaVuSans-Bold.ttf'))))
STYLES={
 'body':ParagraphStyle('body',fontName='QIKBody',fontSize=9.5,leading=13.7,spaceAfter=8,splitLongWords=True,allowWidows=0,allowOrphans=0),
 'title':ParagraphStyle('title',fontName='QIKBold',fontSize=22,leading=27,spaceAfter=15,textColor=HexColor('#153b49')),
 'head':ParagraphStyle('head',fontName='QIKBold',fontSize=12.2,leading=16.5,spaceBefore=13,spaceAfter=8,keepWithNext=True,textColor=HexColor('#153b49')),
 'formula':ParagraphStyle('formula',fontName='QIKBody',fontSize=10,leading=15,spaceBefore=4,spaceAfter=11,leftIndent=10,borderPadding=7,backColor=HexColor('#edf3f5')),
 'table':ParagraphStyle('table',fontName='QIKBody',fontSize=8.2,leading=11,splitLongWords=True),
 'caption':ParagraphStyle('caption',fontName='QIKBody',fontSize=8.1,leading=11,textColor=HexColor('#50636a'),spaceAfter=10),
}

def inline(text):
    text=escape(text)
    return re.sub(r'https://[^\s]+',lambda m:'<link href="'+m[0].rstrip('.')+'" color="#165b72">'+m[0].rstrip('.')+'</link>'+('.' if m[0].endswith('.') else ''),text)


def footer(canvas,doc):
    canvas.saveState();canvas.setFont('QIKBody',7.2);canvas.setFillColor(HexColor('#50636a'))
    canvas.drawString(50,29,'QIK-VRT · 03.11.2026 · Arbeitsfassung zur Prüfung')
    canvas.drawRightString(A4[0]-50,29,str(doc.page));canvas.restoreState()


def figure():
    with (ROOT/'results/closed_mixed_trajectory.csv').open() as f:
        rows=list(csv.DictReader(f))
    data={k:[float(r[k]) for r in rows] for k in rows[0]}
    t,a=data['proper_time'],data['a'];v0=2*math.pi**2/(0.1**1.5)
    em=[v0*x**3*r for x,r in zip(a,data['rho_m'])]
    er=[v0*x**3*r for x,r in zip(a,data['rho_r'])]
    ev=[v0*x**3*r for x,r in zip(a,data['rho_v'])]
    total=[x+y+z for x,y,z in zip(em,er,ev)]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#263d49','text.color':'#263d49','axes.titleweight':'bold'})
    fig,axs=plt.subplots(2,2,figsize=(9.5,6.2),layout='constrained')
    colors=['#165b72','#e58d27','#8d4a82']
    axs[0,0].plot(t,a,color=colors[0],lw=2);axs[0,0].set(title='Dynamische Geometrie',ylabel='Skalenfaktor a')
    for values,label,col in zip([em,er,ev],['Materie','Strahlung','Vakuum'],colors):
        axs[0,1].plot(t,[x/values[0] for x in values],label=label,color=col,lw=1.8)
    axs[0,1].set(yscale='log',title='Energiebeiträge',ylabel='E / eigener Anfangswert');axs[0,1].legend(frameon=False,fontsize=8)
    axs[1,0].plot(t,[x-total[0] for x in total],label='Änderung der Materialenergie',color=colors[0],lw=2)
    axs[1,0].plot(t,data['integrated_minus_p_dV'],label='Integral von -p dV',color=colors[1],ls='--',lw=1.6)
    axs[1,0].set(title='Integrierte Bilanz',ylabel='Normierte Energieeinheiten');axs[1,0].legend(frameon=False,fontsize=7.6)
    axs[1,1].plot(t,[x/10 for x in data['photon_energy']],label='Photonenergie / Anfangswert',color=colors[0],lw=2)
    axs[1,1].plot(t,[1/x for x in a],label='1 / a',color=colors[1],ls='--',lw=1.5)
    axs[1,1].set(title='Rotverschiebung',ylabel='Relativer Wert');axs[1,1].legend(frameon=False,fontsize=7.6)
    for ax in axs.flat:ax.set_xlabel('Mitbewegte Eigenzeit τ (normiert)');ax.grid(alpha=.18)
    fig.savefig(ROOT/'results/model_overview.png',dpi=210,metadata={'Software':'QIK-VRT reproducible FLRW model experiment'})
    plt.close(fig)


def make(source,target):
    text=(ROOT/source).read_text();text=re.sub(r'<!--.*?-->','',text,flags=re.S)
    blocks=re.split(r'\n\s*\n',text.strip());story=[]
    for block in blocks:
        if block in ('## Quellenanhang', '## Quellen'):
            story.append(PageBreak())
        if block.startswith('ABBILDUNG: '):
            story.append(Image(str(ROOT/block.removeprefix('ABBILDUNG: ')),width=A4[0]-100,height=(A4[0]-100)*6.2/9.5))
            story.append(Paragraph('Abbildung 1. Geschlossenes illustratives FLRW-Modell; keine astronomischen Messdaten. Durchgezogene und gestrichelte Kurven der Bilanz bzw. Rotverschiebung liegen innerhalb der angegebenen Residuen übereinander.',STYLES['caption']));continue
        if block.startswith('|'):
            lines=[x for x in block.splitlines() if not re.match(r'^\|[- :|]+\|$',x)]
            cells=[[Paragraph(inline(c.strip()),STYLES['table']) for c in x.strip('|').split('|')] for x in lines]
            table=Table(cells,colWidths=[130,92,92,A4[0]-414],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#e5eef1')),('LINEBELOW',(0,0),(-1,0),.7,HexColor('#77929c')),('LINEBELOW',(0,1),(-1,-1),.25,HexColor('#d6e1e5')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story.extend([table,Spacer(1,11)]);continue
        if block.startswith('# '):style,block='title',block[2:]
        elif block.startswith('## '):style,block='head',block[3:]
        elif block.startswith('FORMEL: '):style,block='formula',block[8:]
        else:style='body'
        chosen=STYLES[style]
        if source=='PROSAARTIKEL.md' and style=='body':chosen=ParagraphStyle('prosa',parent=chosen,fontSize=10.5,leading=15.4,spaceAfter=10)
        story.append(Paragraph(inline(' '.join(block.splitlines())),chosen))
    dest=ROOT/target
    doc=SimpleDocTemplate(str(dest),pagesize=A4,leftMargin=50,rightMargin=50,topMargin=47,bottomMargin=51,
        title=blocks[0].removeprefix('# '),author='Ingolf Lohmann (Fragestellung); OpenAI Codex (Ausarbeitung)')
    doc.build(story,onFirstPage=footer,onLaterPages=footer,canvasmaker=lambda *a,**k:Canvas(*a,**(k|{'invariant':1})))
    reader=PdfReader(dest);writer=PdfWriter();writer.clone_document_from_reader(reader)
    for name in [source,'run_experiment.py','results/RESULTS.json','formal_evidence/SOURCE_LOCK.json','formal_evidence/THEOREM_INVENTORY.json','formal_evidence/RECEIPT.json','formal_evidence/PlanckRealEnergyDomain.lean','formal_evidence/RealErasureBudget.lean','formal_evidence/RealEnergyStatements.lean']:
        writer.add_attachment(Path(name).name,(ROOT/name).read_bytes())
    with dest.open('wb') as f:writer.write(f)
    print(target,'pages',len(PdfReader(dest).pages),'bytes',dest.stat().st_size)


if __name__=='__main__':
    figure()
    make('FACHARTIKEL.md','QIKVRT_Energie_Raumzeit_Forschungsnotiz.pdf')
    make('PROSAARTIKEL.md','QIKVRT_Virtuelles_Universum_Prosa.pdf')
