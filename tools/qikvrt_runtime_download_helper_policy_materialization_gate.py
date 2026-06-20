#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate runtime download helper policy materialization."""
from __future__ import annotations
import json, pathlib, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
POLICY=ROOT/"runtime/download_python_runtime.policy.json"
HELPER=ROOT/"runtime/download_python_runtime.ps1"
SHA=ROOT/"SHA256SUMS.txt"
def validate_policy():
    assert HELPER.is_file(), "runtime/download_python_runtime.ps1 missing"
    assert POLICY.is_file(), "runtime/download_python_runtime.policy.json missing"
    data=json.loads(POLICY.read_text(encoding="utf-8"))
    assert data["path"]=="runtime/download_python_runtime.ps1"
    assert data["policy_path"]=="runtime/download_python_runtime.policy.json"
    assert data["classification"]=="VOLATILE_FIELD_NORMALIZED_RUNTIME_HELPER"
    assert data["excluded_from_sha256sums"] is True
    assert data["immutable_release_constant"] is False
    sha_text=SHA.read_text(encoding="utf-8") if SHA.is_file() else ""
    assert " runtime/download_python_runtime.ps1" not in sha_text
    assert " runtime/download_python_runtime.policy.json" not in sha_text
    return True
def validate_zip(zip_path):
    with zipfile.ZipFile(zip_path,"r") as z:
        names=set(i.filename for i in z.infolist())
    roots=set(name.split("/",1)[0] for name in names if "/" in name)
    assert len(roots)==1
    r=next(iter(roots))
    assert r+"/runtime/download_python_runtime.ps1" in names
    assert r+"/runtime/download_python_runtime.policy.json" in names
    return True
def main(argv=None):
    argv=argv or []
    validate_policy()
    if argv: validate_zip(pathlib.Path(argv[0]))
    print("PASS runtime download helper policy materialization gate")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv[1:]))
