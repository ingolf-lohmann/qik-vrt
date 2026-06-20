#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Runtime download consent and continue path tests."""
from tests.helpers import repo_path, load_json

def test_runtime_download_consent_path_materialized():
    """Verify missing runtime offers consent-based download path."""
    manifest = load_json("runtime/RUNTIME_DEPENDENCY_MANIFEST.json")
    provenance = load_json("third_party/python/THIRD_PARTY_PYTHON_RUNTIME_PROVENANCE.json")
    cmd = repo_path("qikvrt.cmd").read_text(encoding="utf-8", errors="ignore").lower()
    ps1 = repo_path("qikvrt.ps1").read_text(encoding="utf-8", errors="ignore").lower()
    downloader = repo_path("runtime/download_python_runtime.ps1")
    assert manifest["download_consent_gate"] == "ACTIVE"
    assert provenance["user_consent"] == "ACCEPTED"
    assert downloader.is_file()
    assert "download official python runtime now" in cmd
    assert "runtime_download_consent" in cmd
    assert "download official python runtime now" in ps1
    assert "invoke-webrequest" in downloader.read_text(encoding="utf-8", errors="ignore").lower()
