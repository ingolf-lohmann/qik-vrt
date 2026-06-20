#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: dual-license structure is enforced."""
from tests.helpers import ROOT, repo_path, load_json

SOURCE_EXTS = {".py", ".sh", ".ps1", ".cmd", ".bat", ".yml", ".yaml"}

def test_dual_license_texts_and_headers():
    """Verify license texts, source headers and classification."""
    apache = repo_path("LICENSES/Apache-2.0.txt").read_text(encoding="utf-8")
    cc = repo_path("LICENSES/CC-BY-NC-ND-4.0.txt").read_text(encoding="utf-8")
    assert "Apache License" in apache
    assert "Creative Commons" in cc
    classification = load_json("LICENSE_CLASSIFICATION.json")
    by_path = {item["path"]: item for item in classification["files"]}
    assert by_path
    for path in ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        assert rel in by_path
        if path.suffix.lower() in SOURCE_EXTS:
            assert by_path[rel]["license"] == "Apache-2.0"
            assert "Licensed under the Apache License" in path.read_text(encoding="utf-8", errors="ignore")
