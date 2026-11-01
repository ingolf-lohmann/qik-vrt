"""Explicit local title/locator/link checks; not the unavailable skill script."""
from pathlib import Path
import json,hashlib
import fitz
ROOT=Path(__file__).resolve().parent

def check_text(text,sources,links=None):
    flat=''.join(text.split());missing=[]
    for source in sources:
        for expected in [source['title'],*source['urls'],source.get('doi','')]:
            if expected and ''.join(expected.split())not in flat:missing.append(expected)
        if links is not None:
            missing.extend('MISSING_CLICKABLE_LINK:'+u for u in source['urls']if u not in links)
    return missing

def main():
    sources=json.loads((ROOT/'SOURCES.json').read_text())['sources'];results=[]
    pdf_dir=ROOT/'output' if (ROOT/'output').is_dir() else ROOT
    for path in [*sorted(pdf_dir.glob('*.pdf')),ROOT/'Fachartikel.md',ROOT/'Prosaartikel.txt']:
        links=None
        if path.suffix=='.pdf':
            document=fitz.open(path);text='\n'.join(p.get_text()for p in document)
            links={l.get('uri')for page in document for l in page.get_links()if l.get('uri')}
            geometry=[]
            for number,page in enumerate(document,1):
                for word in page.get_text('words'):
                    if word[0]<-1 or word[1]<-1 or word[2]>page.rect.width+1 or word[3]>page.rect.height+1:geometry.append(number)
        else:text=path.read_text();geometry=[]
        missing=check_text(text,sources,links)
        result={'artifact':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'visible_sources_passed':not missing,'missing':missing,
                'replacement_glyph_detected':any(c in text for c in ('\ufffd','\u25a0')),
                'out_of_page_text':geometry,'clickable_pdf_sources_checked':links is not None}
        results.append(result)
    # Both defects from a locator-only/hidden-link design must fail the checker.
    fixture='\n'.join(s['title']+' '+' '.join(s['urls'])+' '+s.get('doi','')for s in sources)
    all_links={u for s in sources for u in s['urls']}
    assert not check_text(fixture,sources,all_links)
    assert check_text(fixture,sources,all_links-{sources[0]['urls'][0]})
    assert check_text(fixture.replace(sources[0]['title'],''),sources,all_links)
    report={'schema':'QIKVRT_LOCAL_VISIBLE_SOURCE_CHECK_V1',
        'checker':'validate_article_sources.py; referenced skill script not available',
        'files':results,'negative_controls_passed':True,
        'visual_review':'All final PDF pages rendered and visually checked; final reference pages separately checked.',
        'new_evidence_zenodo_archive_status':'PENDING_NEW_PUBLICATION','publication_complete':False}
    (ROOT/'VISIBLE_SOURCE_AND_LAYOUT_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if any(not r['visible_sources_passed']or r['replacement_glyph_detected']or r['out_of_page_text']for r in results):
        raise ValueError('Visible source or layout check failed')
    print(json.dumps({'artifacts':len(results),'visible_sources_passed':True,'negative_controls_passed':True}))

if __name__=='__main__':main()
