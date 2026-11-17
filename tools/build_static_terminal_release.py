#!/usr/bin/env python3
"""Deterministic, fail-closed static client release packaging."""
import argparse,hashlib,json,pathlib,shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCHEMA="qikvrt.client.release.v1"
def package(source,output,version):
    raw=source.read_bytes()
    if not raw or b"<html" not in raw.lower(): raise ValueError("HTML_ASSET_REQUIRED")
    digest=hashlib.sha256(raw).hexdigest()
    dest=output/"releases"/digest/"index.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and dest.read_bytes()!=raw: raise ValueError("IMMUTABLE_ASSET_COLLISION")
    dest.write_bytes(raw)
    manifest={"schema":SCHEMA,"version":version,"admission":"BLOCKED","ci":"UNVERIFIED","governance":"UNVERIFIED","integrity":"UNVERIFIED","asset":"./releases/"+digest+"/index.html","sha256":"sha256:"+digest}
    (output/"client-release.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    shutil.copyfile(ROOT/"interfaces"/"zero_admin_bootstrap.html",output/"index.html")
    verify(output)
    return manifest
def verify(output):
    m=json.loads((output/"client-release.json").read_text(encoding="utf-8"))
    if m["schema"]!=SCHEMA:raise ValueError("SCHEMA_MISMATCH")
    digest=m["sha256"].removeprefix("sha256:")
    if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):raise ValueError("DIGEST_INVALID")
    if m["asset"]!="./releases/"+digest+"/index.html":raise ValueError("ASSET_PATH_MISMATCH")
    asset=output/"releases"/digest/"index.html"
    if hashlib.sha256(asset.read_bytes()).hexdigest()!=digest:raise ValueError("ASSET_DIGEST_MISMATCH")
    if any(m[k]=="PASSED" for k in ("admission","ci","governance","integrity")):raise ValueError("UNATTESTED_RELEASE_GATE")
    return True
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",type=pathlib.Path,default=ROOT/"interfaces"/"devops_terminal_client.html");p.add_argument("--output",type=pathlib.Path,required=True);p.add_argument("--version",default="candidate");a=p.parse_args()
    print(json.dumps(package(a.source,a.output,a.version),sort_keys=True))
