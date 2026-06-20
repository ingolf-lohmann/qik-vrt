#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for shift-left root-cause regression and canonical run_end finalization."""
from tests.helpers import repo_path, load_json

def test_canonical_run_end_schema_requires_single_final_event():
    """Verify canonical run_end schema blocks wrapper-only finalization."""
    schema = load_json("canonical/CANONICAL_RUN_END_EVENT_SCHEMA_V25.json")
    assert schema["exactly_one_final_run_end_required"] is True
    assert "cmd_wrapper_end" in schema["adapter_end_events_are_not_final"]
    assert "continue_path" in schema["required_fields"]
    assert "repair_hint" in schema["required_fields"]

def test_launchers_emit_run_end_after_wrapper_end():
    """Verify CMD/PS1/SH include canonical run_end after adapter end."""
    for rel, wrapper in [("qikvrt.cmd","cmd_wrapper_end"),("qikvrt.ps1","ps1_wrapper_end"),("qikvrt.sh","sh_wrapper_end")]:
        text = repo_path(rel).read_text(encoding="utf-8", errors="ignore")
        assert f'"event":"{wrapper}"' in text
        assert '"event":"run_end"' in text

def test_shift_left_policy_blocks_manual_field_test_dependency():
    """Verify policy names the root cause and required scenarios."""
    policy = load_json("canonical/SHIFT_LEFT_ROOT_CAUSE_REGRESSION_POLICY_V25.json")
    assert "manual_field_test_required_to_find_basic_launcher_error" in policy["forbidden"]
    assert "python_target_nonzero_produces_wrapper_end_and_run_end" in policy["required_scenarios"]
    assert "single_canonical_run_end" in policy["required_scenarios"]
    assert "CI_DEVOPS_SHIT_LEFT_INSTEAD_OF_SHIFT_LEFT" in policy["forbidden"]
    assert "implicit_python_package_import_in_harness" in policy["forbidden"]

def test_shift_left_regression_harness_present_and_self_contained():
    """Verify self-contained executable harness exists."""
    text = repo_path("tools/qikvrt_shift_left_launcher_regression.py").read_text(encoding="utf-8")
    assert "scenario_bad_wrapper_without_run_end" in text
    assert "from tools" not in text
    assert "subprocess" not in text
    assert "PASS shift-left launcher regression harness" in text
