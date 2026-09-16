#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""One exact-bound administrative credential adapter; only pinned Main may PUT."""
from __future__ import annotations
import argparse, base64, importlib.util, json, os, re, subprocess, tempfile, time, urllib.error, urllib.request
from pathlib import Path
from typing import Any
AUTHORITY="Goldkelch/qik-vrt"; CARRIER="ingolf-lohmann/qik-vrt"; BRANCH="ops/ruleset-admin-bridge-20260915"
MAIN="a86054139b49c13c5cd344753b248b46b5daf66f"; MAIN_TREE="feff1cae2401a3df83febc3b9458de70d79b818e"; REPO_ID=1271407206; RULESET=19344903
class Hold(RuntimeError): pass
def require(ok:bool,code:str)->None:
    if not ok: raise Hold(code)
def validate_event(event:dict[str,Any],env:dict[str,str])->None:
    require(env.get("GITHUB_REPOSITORY")==CARRIER,"WRONG_CARRIER_REPOSITORY"); require(env.get("GITHUB_RUN_ATTEMPT")=="1","RERUN_FORBIDDEN"); head=env.get("CARRIER_HEAD") or env.get("GITHUB_SHA",""); require(bool(re.fullmatch(r"[0-9a-f]{40}",head)),"INVALID_CARRIER_SHA"); name=env.get("GITHUB_EVENT_NAME")
    if name=="push":
        require(env.get("GITHUB_ACTOR")=="ingolf-lohmann","OWNER_PUSH_REQUIRED"); require(env.get("GITHUB_REF")=="refs/heads/"+BRANCH,"WRONG_CARRIER_REF"); require(event.get("after")==head and bool(re.fullmatch(r"[0-9a-f]{40}",str(event.get("before", "")))),"PUSH_BINDING_MISMATCH"); require(event.get("forced") is False and event.get("created") is False and event.get("deleted") is False,"EXISTING_NONFORCE_PUSH_REQUIRED")
    elif name=="repository_dispatch":
        require(event.get("action")=="qikvrt-ruleset-reconcile","WRONG_REPOSITORY_DISPATCH"); p=event.get("client_payload") or {}; require(p.get("head_sha")==head and p.get("repository")==AUTHORITY,"REPOSITORY_DISPATCH_BINDING_MISMATCH")
    else: raise Hold("UNSUPPORTED_ADMIN_EVENT")
def config(env):
    client=env.get("QIKVRT_RULESET_APP_CLIENT_ID","").strip(); app=env.get("QIKVRT_RULESET_APP_ID","").strip(); key=env.get("QIKVRT_RULESET_APP_PRIVATE_KEY",""); require(bool((client or app) and key.strip()),"RULESET_APP_CONFIGURATION_MISSING"); require(not app or bool(re.fullmatch(r"[1-9][0-9]*",app)),"RULESET_APP_ID_INVALID"); require(not client or bool(re.fullmatch(r"[A-Za-z0-9_]+",client)),"RULESET_CLIENT_ID_INVALID"); return client,app,key
def validate_app(v,client,app_id):
    require(type(v.get("id")) is int and v["id"]>0,"APP_IDENTITY_INVALID"); require(not app_id or str(v["id"])==app_id,"APP_IDENTITY_MISMATCH"); require(not client or v.get("client_id")==client,"APP_CLIENT_ID_MISMATCH"); return v["id"]
def validate_installation(v,app_id):
    require(type(v.get("id")) is int and v["id"]>0,"INSTALLATION_ID_INVALID"); require(v.get("app_id")==app_id,"INSTALLATION_APP_MISMATCH"); require((v.get("account") or {}).get("login")=="Goldkelch","INSTALLATION_OWNER_MISMATCH"); require(v.get("suspended_at") is None,"INSTALLATION_SUSPENDED"); require((v.get("permissions") or {}).get("administration")=="write","ADMINISTRATION_WRITE_MISSING"); return v["id"]
def validate_repositories(values,count):
    require(type(count) is int and count==1 and isinstance(values,list) and len(values)==1,"TOKEN_REPOSITORY_SCOPE_INVALID"); r=values[0]; require(isinstance(r,dict) and r.get("id")==REPO_ID and r.get("full_name")==AUTHORITY,"TOKEN_REPOSITORY_MISMATCH")
def validate_grant(v,now):
    require(isinstance(v.get("token"),str) and bool(v["token"]),"INSTALLATION_TOKEN_MISSING"); p=v.get("permissions") or {}; require(p.get("administration")=="write","TOKEN_ADMINISTRATION_WRITE_MISSING"); require(set(p)<={"administration","metadata"} and p.get("metadata","read")=="read","TOKEN_EXCESS_PERMISSIONS"); validate_repositories(v.get("repositories"),len(v.get("repositories") or []))
    try:
        from datetime import datetime
        d=datetime.fromisoformat(v["expires_at"].replace("Z","+00:00")); require(d.tzinfo is not None,"TOKEN_EXPIRY_INVALID"); expiry=d.timestamp()
    except (KeyError,AttributeError,TypeError,ValueError): raise Hold("TOKEN_EXPIRY_INVALID") from None
    require(0<expiry-now<=3660,"TOKEN_NOT_SHORT_LIVED")
def sign_jwt(issuer,key,now):
    b64=lambda raw:base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii"); payload={"iat":int(now)-60,"exp":int(now)+540,"iss":issuer}; unsigned=b64(b'{"alg":"RS256","typ":"JWT"}')+"."+b64(json.dumps(payload).encode())
    try:
        with tempfile.TemporaryDirectory(prefix="qikvrt-jwt-public-") as root:
            path=Path(root)/"claims"; path.write_text(unsigned,encoding="ascii"); r=subprocess.run(["openssl","dgst","-sha256","-sign","/dev/stdin",str(path)],input=key.encode(),capture_output=True,timeout=15,check=False,env={k:os.environ[k] for k in ("PATH","LANG","LC_ALL","LD_LIBRARY_PATH") if k in os.environ})
        require(r.returncode==0 and bool(r.stdout),"APP_KEY_SIGNING_FAILED")
    except (OSError,subprocess.SubprocessError): raise Hold("APP_SIGNING_RUNTIME_FAILED") from None
    return unsigned+"."+b64(r.stdout)
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): raise Hold("API_REDIRECT_FORBIDDEN")
def request(method,path,token,payload=None):
    allowed=(method=="GET" and (path=="/app" or path=="/installation/repositories?per_page=100" or path.startswith("/repos/"))) or (method=="POST" and re.fullmatch(r"/app/installations/[1-9][0-9]*/access_tokens",path)) or (method=="DELETE" and path=="/installation/token"); require(bool(allowed),"ADAPTER_OPERATION_FORBIDDEN"); h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"qikvrt-ruleset-admin-bridge","Authorization":"Bearer "+token}; data=None if payload is None else json.dumps(payload).encode()
    if data is not None:h["Content-Type"]="application/json"
    try:
        with urllib.request.build_opener(NoRedirect()).open(urllib.request.Request("https://api.github.com"+path,data=data,headers=h,method=method),timeout=30) as response:
            require(not response.headers.get("Link"),"API_PAGINATION_UNEXPECTED"); raw=response.read(2_000_001); require(len(raw)<=2_000_000,"API_RESPONSE_TOO_LARGE"); value=json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc: raise Hold("API_HTTP_"+str(exc.code)) from None
    except (OSError,ValueError): raise Hold("API_READ_FAILED") from None
    require(isinstance(value,dict),"API_OBJECT_REQUIRED"); return value
def bind(api,read_token,head):
    get=lambda path:api("GET","/repos/"+path,read_token); carrier=get(CARRIER+"/pulls/381"); require(carrier.get("state")=="open" and (carrier.get("head") or {}).get("sha")==head and (carrier.get("head") or {}).get("ref")==BRANCH,"CARRIER_PR_DRIFT"); require(get(CARRIER+"/git/ref/heads/"+BRANCH).get("object",{}).get("sha")==head,"CARRIER_REF_DRIFT"); commit=get(CARRIER+"/git/commits/"+head); require(get(AUTHORITY+"/git/ref/heads/main").get("object",{}).get("sha")==MAIN,"AUTHORITY_MAIN_DRIFT"); require(get(AUTHORITY+"/git/commits/"+MAIN).get("tree",{}).get("sha")==MAIN_TREE,"AUTHORITY_TREE_DRIFT"); tree=commit.get("tree",{}).get("sha",""); require(bool(re.fullmatch(r"[0-9a-f]{40}",tree)),"CARRIER_TREE_INVALID"); parents=[p.get("sha") for p in commit.get("parents",[])]; require(len(parents)==1 and bool(re.fullmatch(r"[0-9a-f]{40}",parents[0] or "")),"CARRIER_ANCESTRY_INVALID"); return {"carrier_head":head,"carrier_tree":tree,"carrier_parent":parents[0],"authority_main":MAIN,"authority_main_tree":MAIN_TREE}
def execute(event,env,reconciler,api=request,signer=sign_jwt,clock=time.time):
    head=env.get("CARRIER_HEAD") or env.get("GITHUB_SHA",""); receipt={"schema":"qikvrt_ruleset_admin_bridge_v4","repository":AUTHORITY,"carrier_repository":CARRIER,"carrier_head":head,"run_id":env.get("GITHUB_RUN_ID"),"ruleset_id":RULESET,"scope":"APPLY_EXISTING_MAIN_RULESET_POLICY_ONLY","state":"HOLD_UNVERIFIED","mutation":"NONE","effect_observed":False,"ruleset_current":False,"continuation_required":True,"review_submission":False,"source_promotion":False,"deployment":False,"evidence_transfer":False,"effect_ack_done":False,"event_name":env.get("GITHUB_EVENT_NAME"),"configuration_presence":{k:bool(env.get(k,"").strip()) for k in ("QIKVRT_RULESET_APP_CLIENT_ID","QIKVRT_RULESET_APP_ID","QIKVRT_RULESET_APP_PRIVATE_KEY")}}; minted=""; read_token=env.get("GH_TOKEN","")
    try:
        validate_event(event,env); require(bool(read_token),"READ_TOKEN_MISSING"); binding=bind(api,read_token,head); receipt.update(binding); require(env.get("GITHUB_EVENT_NAME")!="push" or event.get("before")==binding["carrier_parent"],"PUSH_PARENT_MISMATCH"); policy=reconciler.load_policy(); path="/repos/"+AUTHORITY+"/rulesets/"+str(RULESET); before=reconciler.evaluate(api("GET",path,read_token),policy); receipt["pre_ruleset_state"]=before["state"]
        if before["state"]!="CURRENT":
            client,app_id,key=config(env); jwt=signer(client or app_id,key,clock()); del key; identity=validate_app(api("GET","/app",jwt),client,app_id); installation=validate_installation(api("GET","/repos/"+AUTHORITY+"/installation",jwt),identity); grant=api("POST",f"/app/installations/{installation}/access_tokens",jwt,{"repository_ids":[REPO_ID],"permissions":{"administration":"write"}}); minted=grant.get("token",""); validate_grant(grant,clock()); access=api("GET","/installation/repositories?per_page=100",minted); validate_repositories(access.get("repositories"),access.get("total_count")); receipt.update(installation_id=installation,token_scope_verified=True); require(bind(api,read_token,head)["carrier_tree"]==receipt["carrier_tree"],"CARRIER_TREE_DRIFT"); receipt["mutation"]="UNKNOWN"; applied=reconciler.reconcile(minted,policy); receipt["mutation"]=applied["mutation"]; require(applied["state"]=="CURRENT","PINNED_RECONCILIATION_NOT_CURRENT")
        final=reconciler.evaluate(api("GET",path,read_token),policy); require(final["state"]=="CURRENT","INDEPENDENT_RULESET_READBACK_NOT_CURRENT"); require(bind(api,read_token,head)["carrier_tree"]==receipt["carrier_tree"],"POST_EFFECT_SUBJECT_DRIFT"); receipt.update(state="RULESET_CURRENT",ruleset_current=True,effect_observed=receipt["mutation"]=="PUT",first_blocker=None,next_action="REOBSERVE_NATIVE_REVIEW_AND_MAIN_ADMISSION",ruleset_digest=final["pre_state_sha256"])
    except Hold as exc: receipt.update(first_blocker=str(exc),next_action="BIND_EXISTING_RULESET_APP_CONFIGURATION_IN_CARRIER_ACTIONS" if str(exc)=="RULESET_APP_CONFIGURATION_MISSING" else "REPAIR_BOUND_ADMINISTRATIVE_CARRIER")
    except Exception: receipt.update(first_blocker="ADAPTER_OR_PINNED_TOOL_FAILED",next_action="INSPECT_BOUND_ADAPTER_FAILURE")
    finally:
        if minted:
            try: api("DELETE","/installation/token",minted); receipt["token_revoked"]=True
            except Exception: receipt.update(token_revoked=False,cleanup_blocker="TOKEN_REVOCATION_UNCONFIRMED",state="HOLD_UNVERIFIED",first_blocker=receipt.get("first_blocker") or "TOKEN_REVOCATION_UNCONFIRMED")
    return receipt
def load_pinned(root):
    checks=[(("rev-parse","HEAD"),MAIN),(("rev-parse","HEAD^{tree}"),MAIN_TREE),(("hash-object","tools/qikvrt_ruleset_reconcile.py"),"98947b7c11c31c2d078db1d08b6128c7ef49d237"),(("hash-object","policy/GITHUB_MAIN_RULESET_V1.json"),"0d89056d4d745a2c77e7de1f9b9e512dbc43a1e3")]
    for args,value in checks:
        r=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,timeout=15); require(r.returncode==0 and r.stdout.strip()==value,"PINNED_AUTHORITY_BYTES_MISMATCH")
    spec=importlib.util.spec_from_file_location("pinned_ruleset",Path(root)/"tools/qikvrt_ruleset_reconcile.py"); require(spec is not None and spec.loader is not None,"PINNED_TOOL_LOAD_FAILED"); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
def main():
    p=argparse.ArgumentParser(); p.add_argument("--authority-root",type=Path,required=True); p.add_argument("--receipt",type=Path,required=True); a=p.parse_args(); env=dict(os.environ)
    try: event=json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8")); result=execute(event,env,load_pinned(a.authority_root.resolve()))
    except Exception: result={"schema":"qikvrt_ruleset_admin_bridge_v4","state":"HOLD_UNVERIFIED","first_blocker":"ADAPTER_PREFLIGHT_FAILED","mutation":"NONE","effect_observed":False,"evidence_transfer":False,"effect_ack_done":False}
    raw=json.dumps(result,sort_keys=True,indent=2)+"\n"; a.receipt.parent.mkdir(parents=True,exist_ok=True); a.receipt.write_text(raw,encoding="utf-8"); print(raw,end=""); return 0 if result["state"]=="RULESET_CURRENT" else 2
if __name__=="__main__": raise SystemExit(main())
