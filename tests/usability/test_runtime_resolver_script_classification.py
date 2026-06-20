#!/usr/bin/env python3
from tests.helpers import load_json, repo_path
def test_runtime_resolver_gate_exists():
    gate=load_json("canonical/RUNTIME_RESOLVER_SCRIPT_CLASSIFICATION_GATE_V44.json")
    assert gate["gate_id"]=="RUNTIME_RESOLVER_SCRIPT_CLASSIFICATION_GATE"
    assert "RUNTIME_RESOLVE_DEPENDENCY_PY_HASH_MISMATCH_AFTER_FIELD_RUN" in gate["error_classes"]
    assert "runtime/resolve_dependency.py" in gate["runtime_helper_files"]
def test_runtime_resolver_policy():
    policy=load_json("runtime/resolve_dependency.policy.json")
    assert repo_path("runtime/resolve_dependency.py").is_file()
    assert policy["path"]=="runtime/resolve_dependency.py"
    assert policy["classification"]=="VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER"
    assert policy["excluded_from_sha256sums"] is True
def test_runtime_resolver_not_in_sha256sums():
    sha=repo_path("SHA256SUMS.txt").read_text(encoding="utf-8")
    assert " runtime/resolve_dependency.py" not in sha
    assert " runtime/resolve_dependency.policy.json" not in sha
