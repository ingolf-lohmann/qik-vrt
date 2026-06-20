#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate qikvrt.py repo-root sys.path bootstrap before tools imports."""
from __future__ import annotations
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
QIKVRT = ROOT / "qikvrt.py"

def validate_qikvrt_py():
    """Validate qikvrt.py bootstraps sys.path before tools import."""
    text = QIKVRT.read_text(encoding="utf-8")
    assert "ROOT = pathlib.Path(__file__).resolve().parent" in text, "ROOT bootstrap missing"
    assert "sys.path.insert(0, ROOT_STR)" in text, "sys.path insert missing"
    tools_import_index = text.find("from tools import")
    root_index = text.find("ROOT = pathlib.Path(__file__).resolve().parent")
    insert_index = text.find("sys.path.insert(0, ROOT_STR)")
    assert tools_import_index > insert_index > root_index >= 0, "tools import occurs before repo-root sys.path bootstrap"
    assert (ROOT / "tools" / "__init__.py").is_file(), "tools/__init__.py missing"
    ast.parse(text)

def main(argv=None):
    """Run gate."""
    validate_qikvrt_py()
    print("PASS qikvrt.py repo-root sys.path bootstrap gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
