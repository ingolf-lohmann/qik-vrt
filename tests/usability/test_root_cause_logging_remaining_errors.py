#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for root-cause logging of remaining target-process errors."""
from tests.helpers import repo_path, load_json
def test_root_cause_schema_requires_stdout_stderr_and_target_context():
    """Verify target failure schema requires root-cause fields."""
    schema=load_json("canonical/PYTHON_LAUNCHER_TARGET_FAILURE_ROOT_CAUSE_SCHEMA_V26.json")
    required=" ".join(schema["required_on_nonzero_target_process"])
    assert "stdout" in required
    assert "stderr" in required
    assert "target_script" in required
    assert "working_directory" in required
    assert schema["collector_error_forbidden_without_underlying_cause"] is True
def test_qikvrt_py_records_target_process_result():
    """Verify qikvrt.py records target process result."""
    text=repo_path("qikvrt.py").read_text(encoding="utf-8")
    logger=repo_path("tools/qikvrt_root_cause_logger.py").read_text(encoding="utf-8")
    assert "record_target_process_result" in text
    assert "stdout" in text
    assert "stderr" in text
    assert "target_process_result" in logger
def test_volatile_runtime_policy_excludes_logs_from_static_hash_manifest():
    """Verify volatile runtime artifacts are separated."""
    policy=load_json("canonical/VOLATILE_RUNTIME_ARTIFACT_POLICY_V26.json")
    sums=repo_path("SHA256SUMS.txt").read_text(encoding="utf-8") if repo_path("SHA256SUMS.txt").is_file() else ""
    assert "logs/qikvrt_last_run.jsonl" in policy["volatile_runtime_paths"]
    assert "evidence/target_process_failure_root_cause.json" in policy["volatile_runtime_paths"]
    assert "logs/qikvrt_last_run.jsonl" not in sums
def test_runtime_logger_pass_run_end_has_required_fields():
    """Verify PASS run_end uses same canonical fields."""
    schema=load_json("canonical/CANONICAL_RUN_END_EVENT_SCHEMA_V26.json")
    logger=repo_path("tools/qikvrt_runtime_logger.py").read_text(encoding="utf-8")
    assert "pass_run_end_required_values" in schema
    assert '"error_class": "NONE"' in logger
    assert '"continue_path": "NONE"' in logger
    assert '"repair_hint": "NONE"' in logger
