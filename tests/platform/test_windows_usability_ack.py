#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: Windows wrappers hold UI and show log/exit code."""
from tests.helpers import repo_path

def test_windows_wrappers_hold_until_user_acknowledgement():
    """Verify CMD/BAT/PowerShell wrappers expose log and require acknowledgement."""
    cmd = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore").lower()
    bat = repo_path("qikvrt.bat").read_text(encoding="utf-8", errors="ignore").lower()
    ps1 = repo_path("qikvrt.ps1").read_text(encoding="utf-8", errors="ignore").lower()
    assert "qikvrt_last_run.jsonl" in cmd
    assert "exit-code" in cmd
    assert "pause" in cmd
    assert "qikvrt.cmd" in bat
    assert "read-host" in ps1
    assert "exit-code" in ps1
    assert "qikvrt_last_run.jsonl" in ps1
