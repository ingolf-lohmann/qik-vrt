#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations
import argparse,json,subprocess,sys

def api_json(path,*extra):
    return json.loads(subprocess.check_output(["gh","api",path,*extra],text=True))

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--repository",required=True);p.add_argument("--pr",required=True,type=int);p.add_argument("--expected-head",required=True);a=p.parse_args()
    pr=api_json(f"repos/{a.repository}/pulls/{a.pr}")
    if pr.get("state")!="open": raise SystemExit("HOLD: pull request is not open")
    head=pr.get("head",{});base=pr.get("base",{})
    if head.get("repo",{}).get("full_name")!=a.repository: raise SystemExit("HOLD: cross-repository head is forbidden")
    if head.get("sha")!=a.expected_head: raise SystemExit("HOLD: exact head moved")
    branch=head.get("ref")
    if not isinstance(branch,str) or not branch or branch==base.get("ref"): raise SystemExit("HOLD: base/default branch carrier is forbidden")
    commit=api_json(f"repos/{a.repository}/git/commits/{a.expected_head}");tree=commit.get("tree",{}).get("sha")
    if not isinstance(tree,str) or len(tree)!=40: raise SystemExit("HOLD: exact tree unavailable")
    runs=api_json(f"repos/{a.repository}/actions/runs?head_sha={a.expected_head}&per_page=100").get("workflow_runs",[])
    if not any(r.get("conclusion")=="action_required" for r in runs if isinstance(r,dict)): raise SystemExit("HOLD: action_required is not established on exact head")
    payload=json.dumps({"message":"chore(actions): trusted tree-identical verification carrier","tree":tree,"parents":[a.expected_head]})
    created=json.loads(subprocess.check_output(["gh","api","-X","POST",f"repos/{a.repository}/git/commits","--input","-"],input=payload,text=True));new=created.get("sha")
    if not isinstance(new,str) or len(new)!=40: raise SystemExit("BLOCK: carrier commit creation returned no SHA")
    subprocess.check_output(["gh","api","-X","PATCH",f"repos/{a.repository}/git/refs/heads/{branch}","--input","-"],input=json.dumps({"sha":new,"force":False}),text=True)
    readback=api_json(f"repos/{a.repository}/git/commits/{new}")
    if readback.get("tree",{}).get("sha")!=tree: raise SystemExit("BLOCK: carrier tree changed")
    print(json.dumps({"state":"TRUSTED_TREE_IDENTICAL_CARRIER_CREATED","previous_head":a.expected_head,"new_head":new,"tree":tree,"branch":branch,"force_push":False,"fresh_exact_head_gates_required":True,"completion_claims":{"PASS":False,"FINAL_PASS":False,"EFFECT_ACK_DONE":False}},sort_keys=True));return 0
if __name__=="__main__": sys.exit(main())
