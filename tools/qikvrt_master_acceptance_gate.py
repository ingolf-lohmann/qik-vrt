#!/usr/bin/env python3
from __future__ import annotations
import ast, hashlib, importlib.util, json, pathlib, re, sys, warnings
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME_HELPERS={"runtime/download_python_runtime.ps1","runtime/resolve_dependency.py"}
RUNTIME_HELPER_POLICIES={"runtime/download_python_runtime.policy.json","runtime/resolve_dependency.policy.json"}
def is_runtime_state(rel):
    up=rel.upper()
    return rel in {"logs/qikvrt_last_run.jsonl","logs/target_stdout.txt","logs/target_stderr.txt","evidence/target_process_failure_root_cause.json","state/launcher_acceptance_record.json","runtime/DEPENDENCIES.json"} or (rel.startswith("runtime/") and rel.endswith(".json") and not rel.endswith(".policy.json") and ("ATTEMPT" in up or "STATE" in up or "DEPENDENC" in up))
def is_runtime_helper(rel):
    lower=rel.lower()
    return rel in RUNTIME_HELPERS or rel in RUNTIME_HELPER_POLICIES or (rel.startswith("runtime/") and rel.endswith((".ps1",".cmd",".bat",".sh",".py")) and ("download" in lower or "runtime" in lower or "resolve_dependency" in lower or "dependency" in lower))
def excluded(rel): return is_runtime_state(rel) or is_runtime_helper(rel)
def read(path): return path.read_text(encoding="utf-8",errors="ignore")
def sha256_file(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def files(): return sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts)
def fail(message): print("FAIL "+message,file=sys.stderr); return 1
def load_gate(rel,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/rel); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def pre_required_files_bootstrap():
    mod=load_gate("tools/qikvrt_pre_required_files_runtime_state_bootstrap_gate.py","pre_required_files_runtime_state_bootstrap_gate"); mod.bootstrap(ROOT); return True,"pre-required-files runtime state/helper-policy bootstrap ok"
def check_required_files():
    required=["canonical/INTERACTIVE_ACCEPTANCE_BEFORE_EFFECT_GATE_V45.json","canonical/GITHUB_AUTOMATED_MERGE_COMMIT_PUSH_RELEASE_GATE_V45.json","tools/qikvrt_interactive_acceptance_before_effect_gate.py","tools/qikvrt_github_auto_release.py","tools/qikvrt_github_automation_gate.py","qikvrt.cmd","runtime/resolve_dependency.py","runtime/resolve_dependency.policy.json","runtime/download_python_runtime.ps1","runtime/download_python_runtime.policy.json","runtime/DEPENDENCIES.json","runtime/PYTHON_RUNTIME_BUNDLING_ATTEMPT_V24.json","runtime/RUNTIME_DEPENDENCY_MANIFEST.json","LICENSE_ACCEPTANCE_RECORD.json","SHA256SUMS.txt"]
    for rel in required:
        if not (ROOT/rel).is_file(): return False,"missing "+rel
    return True,"required files present"
def check_json_embedded_license():
    for path in files():
        if path.suffix.lower()==".json":
            try: data=json.loads(read(path))
            except Exception as e: return False,"json parse failure "+path.relative_to(ROOT).as_posix()+" "+repr(e)
            if not isinstance(data,dict) or not isinstance(data.get("_license"),dict): return False,"_license missing "+path.relative_to(ROOT).as_posix()
    return True,"JSON licenses ok"
def run_gate(rel,name):
    if not (ROOT/rel).is_file(): return True,name+" absent ok"
    mod=load_gate(rel,name)
    if mod.main([])!=0: return False,name+" failed"
    return True,name+" ok"
def check_test_body_semantics():
    tests=list((ROOT/"tests").rglob("test_*.py")) if (ROOT/"tests").exists() else []
    if not tests: return False,"no tests"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",SyntaxWarning)
        for path in tests:
            text=read(path)
            if re.search(r"assert\s+True\b",text): return False,"placeholder assert in "+path.relative_to(ROOT).as_posix()
            tree=ast.parse(text)
            if len([n for n in ast.walk(tree) if isinstance(n,ast.Assert)])<2: return False,"too few assertions in "+path.relative_to(ROOT).as_posix()
    return True,"test body semantics ok"
def check_hashes():
    sums={}
    for line in read(ROOT/"SHA256SUMS.txt").splitlines():
        if line.strip():
            digest,rel=line.split(maxsplit=1); sums[rel.strip()]=digest
    for rel,digest in sums.items():
        if excluded(rel): return False,"volatile runtime/helper/policy listed "+rel
        path=ROOT/rel
        if not path.is_file() or sha256_file(path)!=digest: return False,"hash mismatch "+rel
    return True,"hashes ok"
def main():
    checks=[pre_required_files_bootstrap,check_required_files,check_json_embedded_license,
        lambda: run_gate("tools/qikvrt_interactive_acceptance_before_effect_gate.py","interactive acceptance before effect gate"),
        lambda: run_gate("tools/qikvrt_github_automation_gate.py","GitHub automated merge/commit/push/release gate"),
        lambda: run_gate("tools/qikvrt_runtime_resolver_classification_gate.py","runtime resolver script classification gate"),
        lambda: run_gate("tools/qikvrt_runtime_download_helper_policy_materialization_gate.py","runtime download helper policy materialization gate"),
        lambda: run_gate("tools/qikvrt_runtime_download_helper_classification_gate.py","runtime download helper script classification gate"),
        lambda: run_gate("tools/qikvrt_pre_required_files_runtime_state_bootstrap_gate.py","pre-required-files runtime state bootstrap gate"),
        lambda: run_gate("tools/qikvrt_volatile_runtime_state_delivery_zip_gate.py","volatile runtime state persisted in delivery ZIP gate"),
        lambda: run_gate("tools/qikvrt_cmd_wrapper_interpreter_probe_gate.py","CMD wrapper interpreter probe and 9009 capture gate"),
        lambda: run_gate("tools/qikvrt_runtime_attempt_state_classification_gate.py","runtime attempt state classification gate"),
        check_test_body_semantics,check_hashes]
    for check in checks:
        ok,msg=check()
        if not ok: return fail(msg)
        print("PASS",msg)
    print("PASS QIKVRT V45 master acceptance gate")
    return 0
if __name__=="__main__": raise SystemExit(main())
