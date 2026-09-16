#!/usr/bin/env python3
"""Normalize an already verified carrier admission without mutating GitHub GITHUB_* defaults."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
from tools import qikvrt_ruleset_admin_bridge as bridge

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('--authority-root',type=Path,required=True); p.add_argument('--receipt',type=Path,required=True); a=p.parse_args()
    head=os.environ.get('CARRIER_HEAD','')
    env=dict(os.environ)
    env['GITHUB_EVENT_NAME']='repository_dispatch'
    synthetic={'action':'qikvrt-ruleset-reconcile','client_payload':{'repository':bridge.AUTHORITY,'head_sha':head}}
    try:
        result=bridge.execute(synthetic,env,bridge.load_pinned(a.authority_root.resolve()))
    except Exception:
        result={'schema':'qikvrt_ruleset_admin_reentry_v1','state':'HOLD_UNVERIFIED','first_blocker':'REENTRY_PREFLIGHT_FAILED','mutation':'NONE','effect_observed':False,'evidence_transfer':False,'effect_ack_done':False}
    raw=json.dumps(result,sort_keys=True,indent=2)+'\n'; a.receipt.parent.mkdir(parents=True,exist_ok=True); a.receipt.write_text(raw,encoding='utf-8'); print(raw,end=''); return 0 if result.get('state')=='RULESET_CURRENT' else 2
if __name__=='__main__': raise SystemExit(main())
