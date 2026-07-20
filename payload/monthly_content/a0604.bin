#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See LICENSES/Apache-2.0.txt.
from __future__ import annotations
import argparse, pathlib, shutil, subprocess, sys
from common_qikvrt_update import discover_artifacts,load_config,parse_date,safe_copy_artifacts,verify_staging,write_sha256sums,write_staging_manifest

def run(cmd,cwd): print('+ '+' '.join(cmd)); subprocess.run(cmd,cwd=cwd,check=True)
def write_staging_files(staging):
    (staging/'README.md').write_text('# QIKVRT Monthly Knowledge Update\n\nAutomatisch erzeugtes Monatsupdate.\n',encoding='utf-8')
    wf=staging/'.github'/'workflows'/'verify-monthly-update.yml'; wf.parent.mkdir(parents=True,exist_ok=True)
    wf.write_text("name: verify-monthly-update\non: [push, pull_request, workflow_dispatch]\njobs:\n  verify:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.12'\n      - run: python tools/verify_monthly_update_payload.py\n",encoding='utf-8')
    td=staging/'tools'; td.mkdir(exist_ok=True)
    (td/'verify_monthly_update_payload.py').write_text("from pathlib import Path\nimport hashlib,json,sys\nROOT=Path(__file__).resolve().parents[1]\ndef sha(p):\n h=hashlib.sha256()\n with p.open('rb') as f:\n  [h.update(c) for c in iter(lambda:f.read(1024*1024), b'')]\n return h.hexdigest()\nm=json.loads((ROOT/'QIKVRT_MONTHLY_ARTIFACT_MANIFEST.json').read_text(encoding='utf-8'))\nif not m.get('artifacts'): sys.exit('FAIL no artifacts')\nfor a in m['artifacts']:\n p=ROOT/a['payload_path']\n if not p.is_file(): sys.exit('FAIL missing '+a['payload_path'])\n if sha(p)!=a['sha256']: sys.exit('FAIL hash '+a['payload_path'])\nprint('PASS monthly update payload verification')\n",encoding='utf-8')
def main():
    ap=argparse.ArgumentParser(description='Create and optionally push a QIKVRT monthly GitHub update repository.')
    ap.add_argument('--source',required=True); ap.add_argument('--staging',required=True); ap.add_argument('--since'); ap.add_argument('--until'); ap.add_argument('--config'); ap.add_argument('--include-all',action='store_true'); ap.add_argument('--remote'); ap.add_argument('--branch',default='main'); ap.add_argument('--message',default='QIKVRT monthly knowledge update'); ap.add_argument('--no-push',action='store_true')
    a=ap.parse_args(); cfg=load_config(a.config); since=parse_date(a.since,cfg['default_since']); until=parse_date(a.until,cfg['default_until']); source=pathlib.Path(a.source).resolve(); staging=pathlib.Path(a.staging).resolve()
    if not source.is_dir(): print('FAIL MONTHLY_UPDATE_SOURCE_NOT_INVENTORIZED: source folder missing',file=sys.stderr); return 1
    arts=discover_artifacts(source,since,until,cfg,include_all=a.include_all)
    if not arts: print('FAIL MONTHLY_UPDATE_SOURCE_NOT_INVENTORIZED: no matching artifacts found',file=sys.stderr); return 1
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True); safe_copy_artifacts(arts,source,staging); write_staging_manifest(staging,arts,since.date().isoformat(),until.date().isoformat()); write_staging_files(staging); write_sha256sums(staging)
    ok,msg=verify_staging(staging)
    if not ok: print('FAIL '+msg,file=sys.stderr); return 1
    print('PASS local monthly GitHub update staging'); print(f'Artifacts: {len(arts)}'); print(f'PDFs: {sum(1 for x in arts if x.artifact_class=="pdf")}'); print(f'Research work: {sum(1 for x in arts if x.artifact_class=="research_work")}')
    if a.no_push: print('GitHub push skipped because --no-push was set.'); return 0
    if not a.remote: print('FAIL --remote required unless --no-push',file=sys.stderr); return 1
    run(['git','init'],staging); run(['git','checkout','-B',a.branch],staging); run(['git','remote','add','origin',a.remote],staging); run(['git','add','.'],staging); run(['git','commit','-m',a.message],staging); run(['git','push','-u','origin',a.branch],staging); print('PASS GitHub monthly update pushed'); return 0
if __name__=='__main__': raise SystemExit(main())
