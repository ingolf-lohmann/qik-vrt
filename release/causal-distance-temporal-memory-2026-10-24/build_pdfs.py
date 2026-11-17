from pathlib import Path
import re
from html import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, Flowable)
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output';OUT.mkdir(exist_ok=True)
FONT=Path('/usr/share/fonts/truetype/dejavu')
for name,file in [('Body','DejaVuSerif.ttf'),('Body-Bold','DejaVuSerif-Bold.ttf'),
                  ('Sans','DejaVuSans.ttf'),('Sans-Bold','DejaVuSans-Bold.ttf'),
                  ('Mono','DejaVuSansMono.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Body-Bold',italic='Body',boldItalic='Body-Bold')
pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='Sans-Bold',italic='Sans',boldItalic='Sans-Bold')
INK=colors.HexColor('#182A36');TEAL=colors.HexColor('#126C73');MUTED=colors.HexColor('#566570')
styles={
 'body':ParagraphStyle('body',fontName='Body',fontSize=10.2,leading=15.2,textColor=INK,
     alignment=TA_JUSTIFY,spaceAfter=8,splitLongWords=True),
 'prose':ParagraphStyle('prose',fontName='Body',fontSize=11.1,leading=17.2,textColor=INK,
     alignment=TA_JUSTIFY,spaceAfter=10,splitLongWords=True),
 'h':ParagraphStyle('h',fontName='Sans-Bold',fontSize=13,leading=17,textColor=TEAL,
     spaceBefore=16,spaceAfter=8,keepWithNext=True),
 'small':ParagraphStyle('small',fontName='Sans',fontSize=8.6,leading=12.2,textColor=MUTED,spaceAfter=8),
 'ref':ParagraphStyle('ref',fontName='Sans',fontSize=8.6,leading=12.5,textColor=INK,spaceAfter=10,splitLongWords=True),
 'title':ParagraphStyle('title',fontName='Body-Bold',fontSize=27,leading=33,textColor=INK,spaceAfter=18),
 'subtitle':ParagraphStyle('subtitle',fontName='Sans',fontSize=13,leading=19,textColor=MUTED,spaceAfter=22),
 'code':ParagraphStyle('code',fontName='Mono',fontSize=9,leading=14,textColor=TEAL,
     backColor=colors.HexColor('#EDF5F5'),borderPadding=10,spaceBefore=7,spaceAfter=13),
 'table':ParagraphStyle('table',fontName='Sans',fontSize=8,leading=11,textColor=INK),
}
styles['proseRef']=ParagraphStyle('proseRef',parent=styles['ref'],fontSize=8.3,leading=11.7,spaceAfter=7)

def markup(s):
    parts=re.split(r'(https?://[^\s<>]+)',s)
    out=[]
    for item in parts:
        if item.startswith(('http://','https://')):
            trail=''
            while item and item[-1] in '.,;':trail=item[-1]+trail;item=item[:-1]
            out.append('<link href="'+escape(item,quote=True)+'" color="#126C73">'+escape(item)+'</link>'+trail)
        else:out.append(escape(item))
    return re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',''.join(out))

class DependencyFigure(Flowable):
    def __init__(self):super().__init__();self.width=165*mm;self.height=111*mm
    def draw(self):
        c=self.canv;c.setFont('Sans-Bold',9);c.setFillColor(INK)
        c.drawString(0,self.height-12,'Abbildung 1: Abhängigkeiten des kontrollierten Programms')
        nodes={'O':(12,237,197,33),'F':(244,237,197,33),'G':(128,182,197,29),
               'E':(128,135,197,29),'R':(128,88,197,29),'S':(128,41,197,29)}
        labels={'O':'Beobachteter Vergangenheitsrecord','F':'Heutiger Zukunftsbedingungsrecord',
                'G':'Freigabe-Gate','E':'Beobachtete Dateiänderung','R':'Unabhängiger Readback','S':'Feedback / neue Erwartung'}
        c.setStrokeColor(TEAL);c.setLineWidth(1.1)
        def arrow(x1,y1,x2,y2):
            c.line(x1,y1,x2,y2)
            import math
            a=math.atan2(y2-y1,x2-x1);l=5
            for off in (-0.5,0.5):c.line(x2,y2,x2-l*math.cos(a+off),y2-l*math.sin(a+off))
        for src,dst in [('O','G'),('F','G'),('G','E'),('E','R'),('R','S')]:
            x,y,w,h=nodes[src];a,b,v,t=nodes[dst];arrow(x+w/2,y,a+v/2,b+t)
        for key,(x,y,w,h) in nodes.items():
            c.setFillColor(colors.HexColor('#EDF5F5'));c.roundRect(x,y,w,h,5,stroke=1,fill=1)
            c.setFillColor(INK);c.setFont('Sans',7.4);c.drawCentredString(x+w/2,y+h/2-2.4,labels[key])
        c.setFont('Sans',7.5);c.setFillColor(MUTED)
        c.drawString(5,18,'Jede Kante: eine deklarierte Abhängigkeitseinheit. Keine physische Rückwärtswirkung.')

def footer(label):
    def render(c,doc):
        w,h=A4;c.saveState();c.setStrokeColor(colors.HexColor('#D4DEDF'));c.setLineWidth(.5)
        c.line(21*mm,18*mm,w-21*mm,18*mm)
        c.setFont('Sans',7.6);c.setFillColor(MUTED)
        c.drawString(21*mm,13*mm,'QIKVRT · '+label+' · Autorenfassung 24.10.2026')
        c.drawRightString(w-21*mm,13*mm,str(doc.page))
        if doc.page>1:
            c.setFont('Sans',7.8);c.drawString(21*mm,h-13*mm,'Ingolf Lohmann · Kausale Distanz und doppelkanonischer Speicher')
        c.restoreState()
    return render

def cover(title,subtitle,kind):
    return [Spacer(1,16*mm),Paragraph('QIKVRT / '+kind,styles['h']),Spacer(1,9*mm),
            Paragraph(markup(title),styles['title']),Paragraph(markup(subtitle),styles['subtitle']),
            Paragraph('Ingolf Lohmann<br/>Independent Researcher<br/>24. Oktober 2026 · Version 1.0.0',styles['small']),
            Spacer(1,6*mm),Paragraph(markup('Anschluss an DOI 10.5281/zenodo.21711193\nhttps://zenodo.org/records/21711193').replace('\n','<br/>'),styles['small']),
            Spacer(1,6*mm),Paragraph('Lokaler Software-Nachweis und definierte Graphdistanz. Physische Retrokausalität, biologische Kognition und produktive Mesh-Abnahme sind eigene, hier nicht abgeschlossene Nachweisfragen.',styles['small']),
            Paragraph('Publikationskandidat: Der neue Zenodo-Status wird ausschließlich durch öffentlichen Record und bytegleichen Redownload bestätigt.',styles['small'])]

def technical():
    raw=(ROOT/'Fachartikel.md').read_text()
    content=raw[raw.index('## Zusammenfassung'):]
    story=cover('Kausale Distanz im doppelkanonischen QIKVRT-Speicher',
          'Eine evidenzgebundene Pfadgeometrie zwischen Beobachtung, Antizipation und bestätigter Wirkung','FACHARTIKEL')
    story.append(PageBreak())
    lines=content.splitlines();i=0;references=False
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('Schlüsselwörter:'):
            story.append(KeepTogether([Paragraph(markup(line),styles['small'])]));i+=1;continue
        if line.startswith('## '):
            heading=line[3:]
            if heading=='Quellen und Begleitmaterial':story.append(PageBreak());references=True
            story.append(Paragraph(markup(heading),styles['h']))
            if heading.startswith('8. '):story.extend([DependencyFigure(),Spacer(1,5)])
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[x.strip()for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+',x)for x in cells):rows.append([Paragraph(markup(x),styles['table'])for x in cells])
                i+=1
            t=Table(rows,colWidths=[28*mm,73*mm,29*mm,34*mm],repeatRows=1,hAlign='LEFT')
            t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E4EFEF')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,TEAL),
                ('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DDE5E5')),
                ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
            story.extend([t,Spacer(1,9)]);continue
        if lines[i].startswith('    '):story.append(Paragraph(markup(line),styles['code']));i+=1;continue
        block=[line];i+=1
        while i<len(lines)and lines[i].strip()and not lines[i].startswith(('## ','|','    ')):
            block.append(lines[i].strip());i+=1
        story.append(Paragraph(markup(' '.join(block)),styles['ref' if references else 'body']))
    target=OUT/'QIKVRT_Kausale_Distanz_Fachartikel.pdf'
    SimpleDocTemplate(str(target),pagesize=A4,rightMargin=22*mm,leftMargin=22*mm,
        topMargin=23*mm,bottomMargin=24*mm,title='Kausale Distanz im doppelkanonischen QIKVRT-Speicher',author='Ingolf Lohmann').build(story,onFirstPage=footer('Fachartikel'),onLaterPages=footer('Fachartikel'))
    return target

def prose():
    raw=(ROOT/'Prosaartikel.txt').read_text();body=raw[raw.index('Wenn wir fragen'):]
    story=cover('Wie weit ist eine Wirkung entfernt?',
            'Vergangenheit, Zukunft und der prüfbare Weg dazwischen','PROSA / VORLESETEXT')
    story.append(Paragraph('Ein ausführlicher Prosabegleiter. Der Quellenanhang steht getrennt hinter dem fließenden Vorlesetext.',styles['small']))
    story.append(PageBreak());refs=False
    for block in body.split('\n\n'):
        s=block.strip()
        if not s:continue
        if s.startswith('QUELLENANHANG'):
            story.extend([PageBreak(),Paragraph('Quellenanhang',styles['h'])]);refs=True;continue
        if refs:
            story.append(Paragraph(markup(s).replace('\n','<br/>'),styles['proseRef']))
        else:story.append(Paragraph(markup(s).replace('\n','<br/>'),styles['prose']))
    target=OUT/'QIKVRT_Wie_weit_ist_eine_Wirkung_Prosa.pdf'
    SimpleDocTemplate(str(target),pagesize=A4,rightMargin=24*mm,leftMargin=24*mm,
        topMargin=23*mm,bottomMargin=24*mm,title='Wie weit ist eine Wirkung entfernt?',author='Ingolf Lohmann').build(story,onFirstPage=footer('Prosa'),onLaterPages=footer('Prosa'))
    return target

if __name__=='__main__':
    print(technical());print(prose())
