#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: test-first deviation has real backfill mapping."""
from tests.helpers import repo_path, load_json

def test_test_first_backfill_ledger_and_mapping():
    """Verify every blocker maps to a real regression test and gate function."""
    ledger = load_json("tests/RETROACTIVE_TEST_BACKFILL_LEDGER.json")
    mapping = load_json("tests/ACCEPTANCE_TEST_MAPPING.json")
    assert ledger["test_first_deviation_acknowledged"] is True
    assert len(ledger["blockers"]) >= 10
    mapped = {(item["test_file"], item["master_gate_function"]) for item in mapping["mappings"]}
    for blocker in ledger["blockers"]:
        assert repo_path(blocker["regression_test"]).is_file()
        assert (blocker["regression_test"], blocker["gate_function"]) in mapped
