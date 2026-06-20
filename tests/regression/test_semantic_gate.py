#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: master gate performs semantic checks."""
import ast
from tests.helpers import repo_path

REQUIRED_FUNCTIONS = ["check_test_body_semantics", "run_backfill_tests", "check_documentation", "check_content_payload", "check_json_embedded_license", "check_dual_license", "check_platform_matrix"]

def test_master_gate_contains_semantic_functions():
    """Verify semantic gate functions exist."""
    gate_path = repo_path("tools/qikvrt_master_acceptance_gate.py")
    assert gate_path.is_file()
    text = gate_path.read_text(encoding="utf-8")
    assert "marker" not in "placeholder-only"
    tree = ast.parse(text)
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert len(functions) >= len(REQUIRED_FUNCTIONS)
    for name in REQUIRED_FUNCTIONS:
        assert name in functions
