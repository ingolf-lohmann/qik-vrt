#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: CI/CD runner is non-recursive and writes evidence."""
import ast
from tests.helpers import repo_path

def test_cicd_runner_is_non_recursive_and_evidence_based():
    """Verify no subprocess import and evidence writer exists."""
    text = repo_path("tools/qikvrt_cicd_publish.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    assert "subprocess" not in imports
    assert "importlib.util" in text
    assert "write_evidence" in text
