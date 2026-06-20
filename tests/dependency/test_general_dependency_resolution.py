#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Tests for platform-general dependency resolution."""
from tests.helpers import repo_path, load_json

def test_general_dependency_contract_exists_and_is_platform_general():
    """Verify dependency resolution is not Windows-only."""
    contract = load_json("canonical/GENERAL_DEPENDENCY_RESOLUTION_CONTRACT.json")
    assert contract["gate_id"] == "GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE"
    assert "windows_cmd_bat" in contract["applies_to"]
    assert "unix_macos_shell" in contract["applies_to"]
    assert "python_launcher" in contract["applies_to"]
    assert "ci" in contract["applies_to"]
    assert "windows_only_dependency_policy" in contract["forbidden"]

def test_dependency_matrix_maps_all_adapters_to_general_contract():
    """Verify Windows, PowerShell, Unix/macOS, Python, CI/container/IDE adapters are mapped."""
    matrix = load_json("canonical/DEPENDENCY_RESOLUTION_MATRIX_V23.json")
    adapters = matrix["adapters"]
    assert "windows_cmd" in adapters
    assert "powershell" in adapters
    assert "unix_macos_shell" in adapters
    assert "python_launcher" in adapters
    assert "ci_container_ide" in adapters
    assert all(adapter["status"] == "GENERAL_CONTRACT_ADAPTER" for adapter in adapters.values())

def test_dependency_manifest_has_continue_license_provenance_and_hash_fields():
    """Verify dependency manifest has general canonical fields."""
    deps = load_json("runtime/DEPENDENCIES.json")
    dep = deps["dependencies"][0]
    required = load_json("canonical/GENERAL_DEPENDENCY_RESOLUTION_CONTRACT.json")["required_dependency_resolution_fields"]
    for field in required:
        assert field in dep
    assert dep["license_area"] == "third_party_python_runtime"
    assert dep["download_allowed_after_consent"] is True
    assert "SHA256" in dep["hash_requirement"]

def test_platform_adapters_reference_general_dependency_contract():
    """Verify launchers and adapters carry general contract marker."""
    for rel in ["qikvrt.cmd", "qikvrt.ps1", "qikvrt.sh", "qikvrt.py"]:
        text = repo_path(rel).read_text(encoding="utf-8", errors="ignore")
        assert "GENERAL_DEPENDENCY_RESOLUTION_CONSENT_AND_CONTINUE_PATH_GATE" in text
    assert repo_path("runtime/resolve_dependency.py").is_file()
    assert repo_path("runtime/download_python_runtime.sh").is_file()
    assert repo_path("runtime/download_python_runtime.ps1").is_file()
