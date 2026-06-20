#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Unit test: master gate function inventory is complete."""
import ast
from tests.helpers import repo_path

def test_master_gate_has_all_required_check_functions():
    """Verify the V16 master gate exposes the expected check functions."""
    gate_path = repo_path("tools/qikvrt_master_acceptance_gate.py")
    assert gate_path.is_file()
    source = gate_path.read_text(encoding="utf-8")
    assert "def check_test_body_semantics" in source
    tree = ast.parse(source)
    funcs = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    expected = {"check_required_files", "check_content_payload", "check_json_embedded_license", "check_dual_license", "check_platform_matrix", "check_documentation", "check_test_body_semantics", "run_backfill_tests"}
    assert expected <= funcs
