#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, re, statistics, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.qikvrt_authority_credentials import credential, CREDENTIALS

MIRROR_URL="https://github.com/ingolf-lohmann/qik-vrt.git"
AUTHORITY_URL="https://github.com/Goldkelch/qik-vrt.git"
REPEATS=12

def run(*args, cwd=None, check=True, env=None):
    p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,timeout=120)
    if check and p.returncode:
        # Never persist arbitrary subprocess diagnostics or command arguments.
        raise RuntimeError("GIT_OPERATION_FAILED")
    return p

def network_environment(url, token=""):
    if url not in {AUTHORITY_URL, MIRROR_URL}:
        raise ValueError("FIXED_REPOSITORY_SCOPE_REQUIRED")
    env={k:v for k,v in os.environ.items() if not k.startswith("GIT_") and k not in CREDENTIALS
         and k not in {"QIKVRT_RULESET_APP_PRIVATE_KEY", "GH_TOKEN"}}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    settings=[("credential.helper", ""), ("http.followRedirects", "false")]
    if url == AUTHORITY_URL:
        if not token:
            raise ValueError("AUTHORITY_CREDENTIAL_REQUIRED")
        header="AUTHORIZATION: basic "+base64.b64encode(("x-access-token:"+token).encode()).decode()
        settings.append(("http."+AUTHORITY_URL+".extraheader", header))
    env["GIT_CONFIG_COUNT"]=str(len(settings))
    for i,(key,value) in enumerate(settings):
        env[f"GIT_CONFIG_KEY_{i}"]=key; env[f"GIT_CONFIG_VALUE_{i}"]=value
    return env

def head(url, token=""):
    p=run("git","ls-remote","--heads",url,"refs/heads/main",check=False,
          env=network_environment(url,token))
    if p.returncode or not p.stdout.strip():
        return None, "MAIN_READ_FAILED"
    sha=p.stdout.split()[0]
    return (sha,None) if re.fullmatch(r"[0-9a-f]{40}",sha) else (None,"INVALID_MAIN_SUBJECT")

def fetch_repo(url, sha, dest, token=""):
    run("git","init","-q",dest)
    run("git","-C",dest,"remote","add","origin",url)
    run("git","-C",dest,"fetch","-q","--no-tags","--depth=1","origin",sha,
        env=network_environment(url,token))
    run("git","-C",dest,"checkout","-q","--detach","FETCH_HEAD")

def files(repo):
    return run("git","-C",repo,"ls-files").stdout.splitlines()

def hash_path(repo,path):
    p=run("git","-C",repo,"show",f"HEAD:{path}",check=False)
    if p.returncode: return None
    return hashlib.sha256(p.stdout.encode("utf-8",errors="surrogateescape")).digest()

def full_compare(a,b, universe):
    different=[]
    for path in universe:
        if hash_path(a,path)!=hash_path(b,path):
            different.append(path)
    return different

def delta_compare(a,b):
    p=run("git","--no-pager","diff","--no-renames","--name-only","HEAD",cwd=a,check=False)
    # not used: repos are separate; build exact tree diff using temporary refs in a
    return p

def main():
    # Reuse #446's resolver; the Mirror GITHUB_TOKEN is never Authority evidence.
    token,source,present=credential({k:os.environ.get(k,"") for k in CREDENTIALS if k != "GITHUB_TOKEN"})
    result={
      "schema":"qikvrt_live_authority_mirror_ab_v1",
      "authority_url":AUTHORITY_URL,"mirror_url":MIRROR_URL,
      "authority_head":None,"mirror_head":None,"repeats":REPEATS,
      "credential_source":source,"credential_names_present":present,
      "speedup_claim":False,"effect_ack_done":False,"predecessor_evidence_transfer":False,
      "executor_head":run("git","rev-parse","HEAD").stdout.strip(),
      "executor_tree":run("git","rev-parse","HEAD^{tree}").stdout.strip(),
      "run_id":os.environ.get("GITHUB_RUN_ID"),"run_attempt":os.environ.get("GITHUB_RUN_ATTEMPT"),
    }
    if not token:
        result["status"]="HOLD_AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED"
        print(json.dumps(result,indent=2)); return 0
    ah,aerr=head(AUTHORITY_URL,token); mh,merr=head(MIRROR_URL)
    result.update(authority_head=ah,mirror_head=mh)
    if not ah or not mh:
        result.update({"status":"HOLD_AUTHORITY_OR_MIRROR_MAIN_UNAVAILABLE","authority_error":aerr,"mirror_error":merr})
        print(json.dumps(result,indent=2)); return 0
    with tempfile.TemporaryDirectory() as td:
        a=str(Path(td)/"a"); b=str(Path(td)/"b")
        fetch_repo(AUTHORITY_URL,ah,a,token); fetch_repo(MIRROR_URL,mh,b)
        # Import mirror tree into authority repo as a local read-only comparison ref.
        run("git","-C",a,"fetch","-q","--no-tags",MIRROR_URL,mh,env=network_environment(MIRROR_URL))
        run("git","-C",a,"update-ref","refs/qikvrt-bench/mirror","FETCH_HEAD")
        af=set(files(a)); bf=set(files(b)); universe=sorted(af|bf)
        result.update(authority_tree=run("git","-C",a,"rev-parse","HEAD^{tree}").stdout.strip(),
                      mirror_tree=run("git","-C",b,"rev-parse","HEAD^{tree}").stdout.strip())
        changed=run("git","-C",a,"diff","--no-renames","--name-only","HEAD","refs/qikvrt-bench/mirror").stdout.splitlines()
        full_samples=[]; delta_samples=[]
        full_out=delta_out=None
        for _ in range(REPEATS):
            t=time.perf_counter(); full_out=full_compare(a,b,universe); full_samples.append(time.perf_counter()-t)
            t=time.perf_counter()
            # Git tree-delta discovery + content read only for changed subjects.
            ch=run("git","-C",a,"diff","--no-renames","--name-only","HEAD","refs/qikvrt-bench/mirror").stdout.splitlines()
            for path in ch:
                hash_path(a,path); hash_path(b,path)
            delta_out=ch; delta_samples.append(time.perf_counter()-t)
        if set(full_out)!=set(delta_out):
            result.update({"status":"FAIL_RESULT_MISMATCH","full_count":len(full_out),"delta_count":len(delta_out)})
        else:
            fm=statistics.median(full_samples); dm=statistics.median(delta_samples)
            result.update({
              "status":"PASS",
              "authority_file_count":len(af),"mirror_file_count":len(bf),
              "union_file_count":len(universe),"changed_file_count":len(changed),
              "changed_fraction":len(changed)/len(universe) if universe else 0,
              "full_median_s":fm,"delta_median_s":dm,
              "wall_speedup_x":fm/dm if dm else None,
              "comparison_work_avoided_fraction":1-(len(changed)/len(universe)) if universe else 0,
              "full_samples_s":full_samples,"delta_samples_s":delta_samples
            })
        print(json.dumps(result,indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
