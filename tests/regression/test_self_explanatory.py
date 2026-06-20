#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: central tools are self-explanatory and documented."""
import ast
from tests.helpers import repo_path

def test_central_tools_have_docstrings_and_named_functions():
    """Verify module/function docstrings and function inventory."""
    for rel in ["tools/qikvrt_master_acceptance_gate.py", "tools/qikvrt_cicd_publish.py"]:
        tree = ast.parse(repo_path(rel).read_text(encoding="utf-8"))
        assert ast.get_docstring(tree), rel
        funcs = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        assert len(funcs) >= 5
        missing = [fn.name for fn in funcs if not ast.get_docstring(fn)]
        assert not missing, f"{rel}: {missing}"
