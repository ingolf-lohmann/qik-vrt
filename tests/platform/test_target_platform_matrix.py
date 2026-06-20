#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: Windows/macOS/Linux target matrix is real."""
from tests.helpers import repo_path, load_json

def test_target_platform_matrix_and_wrappers():
    """Verify all target platforms, wrappers and CI OS matrix."""
    matrix = load_json("platform/TARGET_PLATFORM_MATRIX.json")
    for os_name in ["windows", "macos", "linux"]:
        assert os_name in matrix["platforms"]
        assert matrix["platforms"][os_name]["launchers"]
        assert matrix["platforms"][os_name]["checks"]
    for wrapper in ["qikvrt.py", "qikvrt.sh", "qikvrt.cmd", "qikvrt.bat", "qikvrt.ps1"]:
        assert repo_path(wrapper).is_file()
    workflow_text = repo_path(".github/workflows/qikvrt_v14_matrix.yml").read_text(encoding="utf-8")
    for os_marker in ["ubuntu-latest", "windows-latest", "macos-latest"]:
        assert os_marker in workflow_text
