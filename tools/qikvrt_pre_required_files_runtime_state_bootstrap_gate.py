#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, pathlib, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
REQUIRED_RUNTIME_STATE=["runtime/DEPENDENCIES.json","runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json","runtime/RUNTIME_DEPENDENCY_MANIFEST.json"]
RUNTIME_HELPERS=["runtime/download_python_runtime.ps1","runtime/resolve_dependency.py"]
RUNTIME_HELPER_POLICIES=["runtime/download_python_runtime.policy.json","runtime/resolve_dependency.policy.json"]
def sha256_file(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()
def license_obj(classification):
    return {"copyright":"Copyright 2026 Ingolf Lohmann","rights_holder":"Ingolf Lohmann","license":"CC-BY-NC-ND-4.0","license_text_ref":"LICENSES/CC-BY-NC-ND-4.0.txt","classification":classification}
def load_or_empty(path):
    if path.exists():
        try:
            data=json.loads(path.read_text(encoding="utf-8")); return data if isinstance(data,dict) else {"payload":data}
        except Exception: return {"parse_status":"PREVIOUS_CONTENT_NOT_JSON"}
    return {}
def bootstrap(root=ROOT):
    root=pathlib.Path(root)
    for rel in REQUIRED_RUNTIME_STATE:
        path=root/rel; path.parent.mkdir(parents=True,exist_ok=True)
        data=load_or_empty(path) or {"stub_state":True}
        data.update({"_license":license_obj("runtime_volatile_state_json"),"schema":"qikvrt_runtime_state_pre_required_files_bootstrap_v44","path":rel,"classification":"VOLATILE_RUNTIME_STATE","immutable_release_constant":False,"excluded_from_sha256sums":True,"must_exist_before_required_files_check":True,"last_bootstrap_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for helper_rel in RUNTIME_HELPERS:
        helper=root/helper_rel; helper.parent.mkdir(parents=True,exist_ok=True)
        if not helper.exists(): helper.write_text("# Runtime helper placeholder.\n",encoding="utf-8")
        policy_rel=helper_rel[:-4]+".policy.json" if helper_rel.endswith(".ps1") else helper_rel[:-3]+".policy.json"
        policy=root/policy_rel
        data=load_or_empty(policy)
        data.update({"_license":license_obj("runtime_helper_policy_json"),"schema":"qikvrt_runtime_helper_policy_v44","path":helper_rel,"policy_path":policy_rel,"classification":"VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER","immutable_release_constant":False,"excluded_from_sha256sums":True,"must_exist_before_required_files_check":True,"must_exist_in_delivery_zip":True,"current_helper_sha256":sha256_file(helper),"last_bootstrap_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
        policy.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return True
def main(argv=None):
    bootstrap(ROOT)
    for rel in REQUIRED_RUNTIME_STATE+RUNTIME_HELPERS+RUNTIME_HELPER_POLICIES:
        assert (ROOT/rel).is_file(), "pre-required-files bootstrap failed: "+rel
    print("PASS pre-required-files runtime state/helper-policy bootstrap gate")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv[1:]))
