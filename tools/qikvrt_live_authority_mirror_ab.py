#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, statistics, subprocess, tempfile, time
from pathlib import Path

MIRROR_URL="https://github.com/ingolf-lohmann/qik-vrt.git"
AUTHORITY_URL="https://github.com/Goldkelch/qik-vrt.git"
REPEATS=12

def run(*args, cwd=None, check=True):
    p=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if check and p.returncode:
        raise RuntimeError(f"{args!r}: {p.stderr.strip()}")
    return p

def head(url):
    p=run("git","ls-remote","--heads",url,"refs/heads/main",check=False)
    if p.returncode or not p.stdout.strip():
        return None, p.stderr.strip()
    return p.stdout.split()[0], None

def fetch_repo(url, sha, dest):
    run("git","init","-q",dest)
    run("git","-C",dest,"remote","add","origin",url)
    run("git","-C",dest,"fetch","-q","--no-tags","--depth=1","origin",sha)
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
    ah,aerr=head(AUTHORITY_URL); mh,merr=head(MIRROR_URL)
    result={
      "schema":"qikvrt_live_authority_mirror_ab_v1",
      "authority_url":AUTHORITY_URL,"mirror_url":MIRROR_URL,
      "authority_head":ah,"mirror_head":mh,"repeats":REPEATS,
    }
    if not ah or not mh:
        result.update({"status":"HOLD_AUTHORITY_OR_MIRROR_MAIN_UNAVAILABLE","authority_error":aerr,"mirror_error":merr})
        print(json.dumps(result,indent=2)); return 0
    with tempfile.TemporaryDirectory() as td:
        a=str(Path(td)/"a"); b=str(Path(td)/"b")
        fetch_repo(AUTHORITY_URL,ah,a); fetch_repo(MIRROR_URL,mh,b)
        # Import mirror tree into authority repo as a local read-only comparison ref.
        run("git","-C",a,"fetch","-q","--no-tags",MIRROR_URL,mh)
        run("git","-C",a,"update-ref","refs/qikvrt-bench/mirror","FETCH_HEAD")
        af=set(files(a)); bf=set(files(b)); universe=sorted(af|bf)
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
