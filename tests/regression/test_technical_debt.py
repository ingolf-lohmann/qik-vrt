#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: technical debt cleanup is materialized."""
from tests.helpers import repo_path, load_json

def test_technical_debt_items_have_regression_tests():
    """Verify each technical debt item is backed by a real test and valid gate function."""
    debt = load_json("tests/TECHNICAL_DEBT_REGISTER.json")
    assert "JSONL_LOG_VALIDITY" in debt["status"] or "CANONICAL_CONTINUE" in debt["status"] or "GENERAL_USABILITY_LOGGING" in debt["status"] or "RUNTIME_DEPENDENCY" in debt["status"] or "CONSOLE_ASCII" in debt["status"] or "RUNTIME_DEPENDENCY" in debt["status"] or "CONSOLE_ASCII" in debt["status"] or "RUNTIME_DOWNLOAD_CONSENT" in debt["status"]
    for item in debt["debt_items"]:
        assert item["status"] == "REGRESSION_TEST_MATERIALIZED"
        assert repo_path(item["cleanup_test"]).is_file()
        assert item["gate_function"].startswith("check_") or item["gate_function"] == "run_backfill_tests"
