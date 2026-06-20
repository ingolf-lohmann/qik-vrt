#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: general usability logging and repair hints."""
import ast
from tests.helpers import repo_path

def test_general_usability_logger_and_launcher():
    """Verify central JSONL logger and launcher behavior."""
    logger = repo_path("tools/qikvrt_runtime_logger.py")
    launcher = repo_path("qikvrt.py")
    assert logger.is_file()
    assert launcher.is_file()
    logger_text = logger.read_text(encoding="utf-8")
    launcher_text = launcher.read_text(encoding="utf-8")
    assert "qikvrt_last_run.jsonl" in logger_text
    assert "write_event" in logger_text
    assert "repair_hint" in logger_text
    assert "exit_code" in logger_text
    tree = ast.parse(launcher_text)
    functions = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert {"build_parser", "run_command", "main"} <= functions
