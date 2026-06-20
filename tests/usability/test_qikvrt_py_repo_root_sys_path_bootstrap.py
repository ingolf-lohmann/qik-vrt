#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for qikvrt.py repo root sys.path bootstrap."""
from tests.helpers import load_json, repo_path

def test_bootstrap_gate_materialized():
    """Verify V34 bootstrap gate exists."""
    gate = load_json("canonical/QIKVRT_PY_REPO_ROOT_SYS_PATH_BOOTSTRAP_GATE_V34.json")
    assert gate["gate_id"] == "QIKVRT_PY_REPO_ROOT_SYS_PATH_BOOTSTRAP_GATE"
    assert "QIKVRT_PY_CANNOT_IMPORT_TOOLS_UNDER_WINDOWS_RUNTIME" in gate["error_classes"]
    assert "sys.path" in gate["rule"]

def test_qikvrt_py_imports_tools_after_sys_path_bootstrap():
    """Verify qikvrt.py bootstraps repo root before tools import."""
    text = repo_path("qikvrt.py").read_text(encoding="utf-8")
    assert "ROOT = pathlib.Path(__file__).resolve().parent" in text
    assert "sys.path.insert(0, ROOT_STR)" in text
    assert text.index("ROOT = pathlib.Path(__file__).resolve().parent") < text.index("sys.path.insert(0, ROOT_STR)") < text.index("from tools import")

def test_tools_package_init_exists():
    """Verify tools package init exists."""
    init = repo_path("tools/__init__.py")
    assert init.is_file()
    text = init.read_text(encoding="utf-8")
    assert "QIK-VRT local tools package" in text
