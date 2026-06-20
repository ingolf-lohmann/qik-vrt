#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Console launcher ASCII-safety tests."""
from tests.helpers import repo_path

SCRIPT_FILES = ["qikvrt.cmd", "qikvrt.bat", "qikvrt.ps1", "qikvrt.sh"]

def test_console_scripts_are_ascii_safe():
    """Verify raw console scripts avoid non-ASCII output and umlauts."""
    forbidden = "äöüÄÖÜß"
    for rel in SCRIPT_FILES:
        path = repo_path(rel)
        assert path.is_file()
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert all(ord(ch) < 128 for ch in text), rel
        assert not any(ch in text for ch in forbidden), rel
        assert "Logfile" in text or "qikvrt_last_run.jsonl" in text
