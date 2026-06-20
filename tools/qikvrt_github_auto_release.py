#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
ACCEPTANCE=ROOT/"state/launcher_acceptance_record.json"
REPORT=ROOT/"audit/GITHUB_AUTOMATED_RELEASE_ATTEMPT_V45.json"
def run(cmd):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
    return {"cmd":cmd,"returncode":p.returncode,"stdout":p.stdout[-4000:],"stderr":p.stderr[-4000:]}
def report(status,reason,steps):
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    data={"_license":{"copyright":"Copyright 2026 Ingolf Lohmann","rights_holder":"Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","license_text_ref":"LICENSES/CC-BY-NC-ND-4.0.txt","classification":"github_release_attempt_report_json"},"schema":"qikvrt_github_automated_release_attempt_v45","created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"status":status,"reason":reason,"steps":steps,"external_evidence_claims":status=="PASS_RELEASE_CREATED"}
    REPORT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(data,ensure_ascii=False,indent=2))
    return 0 if status=="PASS_RELEASE_CREATED" else 20
def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--branch",default="main"); ap.add_argument("--tag",default="qikvrt-v45"); ap.add_argument("--release-title",default="QIK-VRT V45"); ap.add_argument("--asset",default="")
    a=ap.parse_args(argv); steps=[]
    if not ACCEPTANCE.is_file(): return report("BLOCK_ACCEPTANCE_REQUIRED","No persisted acceptance record. Run qikvrt.cmd and type JA first.",steps)
    steps.append(run(["git","--version"]))
    if steps[-1]["returncode"]!=0: return report("BLOCK_GIT_NOT_AVAILABLE","git executable is not available.",steps)
    steps.append(run(["git","rev-parse","--is-inside-work-tree"]))
    if steps[-1]["returncode"]!=0: return report("BLOCK_NOT_A_GIT_REPOSITORY","This extracted ZIP is not inside a Git repository. Copy into the real repo first.",steps)
    steps.append(run(["git","remote","-v"]))
    if steps[-1]["returncode"]!=0 or not steps[-1]["stdout"].strip(): return report("BLOCK_GIT_REMOTE_MISSING","No Git remote configured; cannot push or release.",steps)
    steps.append(run(["gh","--version"]))
    if steps[-1]["returncode"]!=0: return report("BLOCK_GH_CLI_NOT_AVAILABLE","GitHub CLI is not available.",steps)
    steps.append(run(["gh","auth","status"]))
    if steps[-1]["returncode"]!=0: return report("BLOCK_GITHUB_AUTH_MISSING","GitHub authentication missing; cannot create release.",steps)
    for cmd in [["git","checkout",a.branch],["git","pull","--ff-only","origin",a.branch],["git","add","-A"],["git","commit","-m","QIK-VRT V45 acceptance-before-effect and GitHub automation gate"],["git","push","origin",a.branch],["git","tag","-f",a.tag],["git","push","origin",a.tag,"--force"]]:
        steps.append(run(cmd))
        if steps[-1]["returncode"]!=0 and "nothing to commit" not in (steps[-1]["stdout"]+steps[-1]["stderr"]).lower(): return report("BLOCK_GIT_COMMAND_FAILED","Git command failed before release.",steps)
    rel=["gh","release","create",a.tag,"--title",a.release_title,"--notes","QIK-VRT V45 acceptance-before-effect and GitHub automation release."]
    if a.asset: rel.append(a.asset)
    steps.append(run(rel))
    if steps[-1]["returncode"]!=0: return report("BLOCK_GITHUB_RELEASE_FAILED","gh release create failed.",steps)
    return report("PASS_RELEASE_CREATED","GitHub release created by gh CLI.",steps)
if __name__=="__main__": raise SystemExit(main(sys.argv[1:]))
