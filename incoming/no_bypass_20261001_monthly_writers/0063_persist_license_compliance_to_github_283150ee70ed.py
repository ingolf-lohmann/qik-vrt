#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See LICENSES/Apache-2.0.txt.
from __future__ import annotations
import argparse, pathlib, shutil, subprocess, sys
PACKAGE_ROOT=pathlib.Path(__file__).resolve().parents[1]
FILES_TO_PERSIST=[
"LICENSE_NOTICE.md",
"acceptance/COPYRIGHT_LICENSE_COMPLIANCE_ACCEPTANCE_TEST.md",
"legal/RIGHTS_AND_LICENSE_POLICY.md",
"legal/THIRD_PARTY_CONTENT_DECLARATION.json",
"audit/V6_COPYRIGHT_LICENSE_LAYER_GAP_FINDING.json",
"tools/verify_license_compliance.py",
"tools/persist_license_compliance_to_github.py"]
def run(cmd,cwd): print("+ "+" ".join(cmd)); subprocess.run(cmd,cwd=cwd,check=True)
def copy_files(repo):
    for rel in FILES_TO_PERSIST:
        src=PACKAGE_ROOT/rel; dst=repo/rel
        if not src.is_file(): raise FileNotFoundError(rel)
        dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
def main():
    parser=argparse.ArgumentParser(description="Persist QIKVRT copyright/license compliance gate into a GitHub repository.")
    g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--repo"); g.add_argument("--remote")
    parser.add_argument("--workdir",default="QIKVRT_LICENSE_COMPLIANCE_GITHUB_WORKDIR")
    parser.add_argument("--branch",default="main")
    parser.add_argument("--message",default="Persist QIKVRT copyright and license compliance gate")
    parser.add_argument("--no-push",action="store_true")
    args=parser.parse_args()
    if args.repo:
        repo=pathlib.Path(args.repo).resolve()
        if not (repo/".git").exists(): print("FAIL target --repo is not a Git repository", file=sys.stderr); return 1
    else:
        repo=pathlib.Path(args.workdir).resolve()
        if repo.exists(): shutil.rmtree(repo)
        run(["git","clone",args.remote,str(repo)], pathlib.Path.cwd())
    run(["git","checkout",args.branch], repo)
    copy_files(repo)
    verifier=repo/"tools"/"verify_license_compliance.py"
    if verifier.is_file(): run([sys.executable,str(verifier.relative_to(repo))], repo)
    run(["git","add"]+FILES_TO_PERSIST, repo)
    status=subprocess.run(["git","status","--porcelain"],cwd=repo,text=True,capture_output=True,check=True).stdout.strip()
    if status: run(["git","commit","-m",args.message], repo)
    if args.no_push:
        print("PASS local GitHub license compliance persistence prepared; push skipped.")
        return 0
    run(["git","push","origin",args.branch], repo)
    print("PASS license compliance gate persisted to GitHub remote")
    return 0
if __name__=="__main__": raise SystemExit(main())
