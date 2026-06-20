#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Runtime dependency discovery tests."""
from tests.helpers import repo_path, load_json

def test_runtime_manifest_and_launcher_discovery_paths():
    """Verify runtime manifest and Windows launcher contain bundled-runtime discovery."""
    manifest = load_json("runtime/RUNTIME_DEPENDENCY_MANIFEST.json")
    cmd = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore").lower()
    ps1 = repo_path("qikvrt.ps1").read_text(encoding="utf-8", errors="ignore").lower()
    assert "runtime/python/windows/python.exe" in manifest["preferred_embedded_paths"]
    assert manifest["bundled_windows_python_runtime"] is False
    assert manifest["status"] in {"BLOCKED_UNTIL_REAL_RUNTIME_BINARY_INCLUDED", "CONTINUE_DOWNLOAD_CONSENT_PATH_AVAILABLE"}
    assert "runtime\\python\\windows\\python.exe" in cmd or "runtime\python\windows\python.exe" in cmd
    assert "python runtime not found" in cmd
    assert "runtime/python/windows/python.exe" in ps1
    assert "python runtime not found" in ps1
