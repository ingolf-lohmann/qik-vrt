#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate volatile runtime state materialization and delivery ZIP persistence."""
from __future__ import annotations
import importlib.util
import json
import pathlib
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOT = ROOT / "tools" / "qikvrt_pre_required_files_runtime_state_bootstrap_gate.py"
GATE = ROOT / "canonical" / "VOLATILE_RUNTIME_STATE_PERSISTED_IN_DELIVERY_ZIP_GATE_V40.json"
SHA = ROOT / "SHA256SUMS.txt"

def load_boot():
    spec = importlib.util.spec_from_file_location("qikvrt_pre_required_files_runtime_state_bootstrap_gate_v41", BOOT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def required_files():
    if GATE.is_file():
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        return gate.get("required_runtime_state_files", load_boot().REQUIRED_RUNTIME_STATE)
    return load_boot().REQUIRED_RUNTIME_STATE

def validate_materialization():
    boot = load_boot()
    boot.bootstrap(ROOT)
    sha_text = SHA.read_text(encoding="utf-8") if SHA.is_file() else ""
    for rel in required_files():
        path = ROOT / rel
        assert path.is_file(), "volatile runtime file missing: " + rel
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("classification") == "VOLATILE_RUNTIME_STATE", rel + " not volatile"
        assert data.get("excluded_from_sha256sums") is True, rel + " not excluded"
        assert data.get("immutable_release_constant") is False, rel + " still immutable"
        assert (" " + rel) not in sha_text, rel + " present in SHA256SUMS"
    return True

def validate_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as z:
        names = set(i.filename for i in z.infolist())
    roots = set(name.split("/", 1)[0] for name in names if "/" in name)
    assert len(roots) == 1, "expected one top-level root"
    root_name = next(iter(roots))
    for rel in required_files():
        arc = root_name + "/" + rel
        assert arc in names, "delivery ZIP missing volatile runtime file: " + arc
    return True

def main(argv=None):
    argv = argv or []
    validate_materialization()
    if argv:
        validate_zip(pathlib.Path(argv[0]))
    print("PASS volatile runtime state persisted in delivery ZIP gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
