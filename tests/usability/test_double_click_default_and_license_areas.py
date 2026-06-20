#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for double-click default behavior and three license areas."""
import ast
from tests.helpers import repo_path, load_json

def test_python_launcher_defaults_to_master_gate_without_arguments():
    """Verify qikvrt.py has optional command defaulting to master-gate."""
    source = repo_path("qikvrt.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert 'DEFAULT_COMMAND = "master-gate"' in source
    assert 'nargs="?"' in source
    assert "default=DEFAULT_COMMAND" in source
    assert "argparse" in source

def test_windows_wrappers_default_to_master_gate_and_download_runtime():
    """Verify CMD/BAT/PS1 default to master-gate and invoke runtime download flow."""
    cmd = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore")
    bat = repo_path("qikvrt.bat").read_text(encoding="utf-8", errors="ignore")
    ps1 = repo_path("qikvrt.ps1").read_text(encoding="utf-8", errors="ignore")
    assert "DEFAULT_COMMAND=master-gate" in cmd
    assert 'if "%ARGS%"=="" set "ARGS=%DEFAULT_COMMAND%"' in cmd
    assert "download_python_runtime.ps1" in cmd
    assert "Default command: master-gate" in bat
    assert '$DefaultCommand = "master-gate"' in ps1
    assert "download_python_runtime.ps1" in ps1

def test_three_license_areas_are_separated():
    """Verify Python, Apache and CC license areas are materialized separately."""
    areas = load_json("LICENSE_AREAS_V22.json")
    names = {area["area"]: area for area in areas["areas"]}
    assert "third_party_python_runtime" in names
    assert "qikvrt_source_code" in names
    assert "qikvrt_non_source_content" in names
    assert names["third_party_python_runtime"]["license"] == "Python Software Foundation License Version 2"
    assert names["qikvrt_source_code"]["license"] == "Apache-2.0"
    assert names["qikvrt_non_source_content"]["license"] == "CC-BY-NC-ND-4.0"
    assert repo_path("third_party/python/THIRD_PARTY_PYTHON_RUNTIME_PROVENANCE.json").is_file()
