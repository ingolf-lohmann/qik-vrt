#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See LICENSES/Apache-2.0.txt.
from __future__ import annotations
import argparse,json,os,pathlib,sys,urllib.error,urllib.parse,urllib.request
from common_qikvrt_update import discover_artifacts,load_config,parse_date,scientific_pdf_filter
ZENODO_API='https://zenodo.org/api'; ZENODO_SANDBOX_API='https://sandbox.zenodo.org/api'
def auth_headers(token): return {'Authorization':'Bearer'+' '+token}
def request_json(method,url,token,payload=None):
    data=None; headers=auth_headers(token)
    if payload is not None: data=json.dumps(payload).encode('utf-8'); headers['Content-Type']='application/json'
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=120) as resp:
        raw=resp.read().decode('utf-8'); return json.loads(raw) if raw else {}
def upload_file(bucket_url,token,path):
    url=bucket_url.rstrip('/')+'/'+urllib.parse.quote(path.name); req=urllib.request.Request(url,data=path.read_bytes(),headers=auth_headers(token),method='PUT')
    with urllib.request.urlopen(req,timeout=300) as resp:
        raw=resp.read().decode('utf-8'); return json.loads(raw) if raw else {}
def metadata_for_pdf(a,cfg):
    title=pathlib.Path(a.relative_path).stem.replace('_',' ').replace('-',' ')
    return {'metadata':{'title':title,'upload_type':cfg['zenodo']['default_upload_type'],'publication_type':cfg['zenodo']['default_publication_type'],'description':'Wissenschaftliches PDF aus der QIKVRT-Erkenntnisarbeit des angegebenen Monats. Einzeldeposit.\n\nq.e.d. Ingolf Lohmann','creators':[{'name':'Lohmann, Ingolf','affiliation':'Independent researcher'}],'license':cfg['zenodo']['license'],'keywords':['QIKVRT','Quantengravitation','Quantenphysik','Raumzeit','Wissenschaftliches PDF'],'notes':'Einzeldeposit. Veröffentlichung nur durch explizites --publish.'}}
def main():
    ap=argparse.ArgumentParser(description='Upload scientific PDFs from QIKVRT monthly work to Zenodo as individual deposits.'); ap.add_argument('--source',required=True); ap.add_argument('--since'); ap.add_argument('--until'); ap.add_argument('--config'); ap.add_argument('--include-all',action='store_true'); ap.add_argument('--all-pdfs',action='store_true'); ap.add_argument('--sandbox',action='store_true'); ap.add_argument('--token-env',default='ZENODO_TOKEN'); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--publish',action='store_true'); ap.add_argument('--output',default='QIKVRT_ZENODO_MONTHLY_PDF_UPLOAD_RESULT.json')
    a=ap.parse_args(); cfg=load_config(a.config); since=parse_date(a.since,cfg['default_since']); until=parse_date(a.until,cfg['default_until']); source=pathlib.Path(a.source).resolve()
    if not source.is_dir(): print('FAIL source folder missing',file=sys.stderr); return 1
    arts=discover_artifacts(source,since,until,cfg,include_all=a.include_all); selected=[x for x in arts if x.artifact_class=='pdf'] if a.all_pdfs else [x for x in arts if scientific_pdf_filter(x,cfg)]
    if not selected: print('FAIL no scientific PDFs selected for Zenodo',file=sys.stderr); return 1
    plan={'schema':'qikvrt_monthly_zenodo_scientific_pdf_plan_v1','since':since.date().isoformat(),'until':until.date().isoformat(),'separate_deposit_per_pdf':True,'publish':a.publish,'sandbox':a.sandbox,'pdf_count':len(selected),'pdfs':[{'source_path':str(x.source_path),'relative_path':x.relative_path,'bytes':x.size_bytes,'sha256':x.sha256,'metadata':metadata_for_pdf(x,cfg)} for x in selected]}
    if a.dry_run: print('DRY-RUN: no Zenodo request will be sent.'); print(json.dumps(plan,ensure_ascii=False,indent=2)); return 0
    token=os.environ.get(a.token_env,'')
    if not token: print(f'FAIL missing token environment variable: {a.token_env}',file=sys.stderr); return 1
    api=ZENODO_SANDBOX_API if a.sandbox else ZENODO_API; results={'api':api,'sandbox':a.sandbox,'published':a.publish,'deposits':[]}
    for item in plan['pdfs']:
        pdf=pathlib.Path(item['source_path']); created=request_json('POST',api+'/deposit/depositions',token,{}); dep_id=created['id']; bucket=created['links']['bucket']; uploaded=upload_file(bucket,token,pdf); updated=request_json('PUT',api+f'/deposit/depositions/{dep_id}',token,item['metadata']); rec={'deposition_id':dep_id,'source_path':item['source_path'],'sha256':item['sha256'],'links':updated.get('links',{}),'upload_response':uploaded}
        if a.publish:
            published=request_json('POST',api+f'/deposit/depositions/{dep_id}/actions/publish',token,None); rec['published_response']=published; rec['doi']=published.get('doi'); rec['record_url']=published.get('links',{}).get('html')
        results['deposits'].append(rec)
    pathlib.Path(a.output).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8'); print('PASS Zenodo scientific PDF individual upload operation completed: '+a.output); return 0
if __name__=='__main__': raise SystemExit(main())
