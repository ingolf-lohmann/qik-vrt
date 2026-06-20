#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
"""Validate runtime attempt/state volatile classification without treating helper policy JSON as runtime state."""
from __future__ import annotations
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
SHA=ROOT/"SHA256SUMS.txt"
def is_runtime_state(rel):
    up=rel.upper()
    return rel.startswith("runtime/") and rel.endswith(".json") and not rel.endswith(".policy.json") and ("ATTEMPT" in up or "STATE" in up or "DEPENDENC" in up)
def validate_runtime_attempt_state_classification():
    sha_text=SHA.read_text(encoding="utf-8") if SHA.is_file() else ""
    for path in (ROOT/"runtime").glob("*.json"):
        rel=path.relative_to(ROOT).as_posix()
        if is_runtime_state(rel):
            data=json.loads(path.read_text(encoding="utf-8"))
            assert data.get("classification")=="VOLATILE_RUNTIME_STATE", rel+" not volatile runtime state"
            assert data.get("excluded_from_sha256sums") is True, rel+" not excluded"
            assert (" "+rel) not in sha_text, rel+" present in SHA256SUMS"
    return True
def main(argv=None):
    validate_runtime_attempt_state_classification()
    print("PASS runtime attempt/state volatile classification gate")
    return 0
if __name__=="__main__": raise SystemExit(main(sys.argv[1:]))
