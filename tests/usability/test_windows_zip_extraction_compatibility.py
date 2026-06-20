#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for Windows ZIP extraction compatibility."""
from tests.helpers import load_json, repo_path

def test_windows_zip_gate_materialized():
    """Verify V36 Windows ZIP gate exists."""
    gate = load_json("canonical/WINDOWS_ZIP_EXTRACTION_COMPATIBILITY_GATE_V36.json")
    assert gate["gate_id"] == "WINDOWS_ZIP_EXTRACTION_COMPATIBILITY_GATE"
    assert gate["zip_filename_required"] == "QV36_WINZIP_OK.zip"
    assert gate["top_level_directory_required"] == "QV36"
    assert gate["max_internal_zip_path_length"] <= 120

def test_repo_paths_are_short_for_windows_zip():
    """Verify repo paths fit under short QV36 root."""
    max_len = 0
    max_name = ""
    for path in repo_path(".").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
            rel = path.relative_to(repo_path(".")).as_posix()
            arc = "QV36/" + rel
            if len(arc) > max_len:
                max_len = len(arc)
                max_name = arc
            assert len(arc) <= 120
            assert len(path.name) <= 96
    assert max_len <= 120
    assert max_name.startswith("QV36/")

def test_no_path_traversal_or_absolute_paths():
    """Verify no unsafe repo-relative file paths."""
    for path in repo_path(".").rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and ".git" not in path.parts:
            rel = path.relative_to(repo_path(".")).as_posix()
            assert not rel.startswith("/")
            assert ".." not in rel.split("/")
