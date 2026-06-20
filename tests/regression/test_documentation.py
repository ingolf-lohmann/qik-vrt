#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: documentation is present and references real commands."""
from tests.helpers import repo_path

DOCS = ["QUICKSTART", "ARCHITECTURE", "TESTING", "CLEAN_CODE_GUIDE", "CONTRIBUTING", "CLI_REFERENCE", "ACCEPTANCE_TEST_MATRIX", "TEST_FIRST_LEDGER", "RED_GREEN_REFACTOR_RECORD", "TECHNICAL_DEBT_REGISTER", "REAL_TEST_ASSERTION_SEMANTICS"]

def test_documentation_files_and_cli_commands():
    """Verify documentation files have meaningful content and command references."""
    combined = ""
    for doc in DOCS:
        path = repo_path(f"docs/{doc}.md")
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert len(text) > 180
        combined += text
    for command in ["python tools/qikvrt_master_acceptance_gate.py", "python qikvrt.py master-gate", "python qikvrt.py cicd-publish"]:
        assert command in combined
