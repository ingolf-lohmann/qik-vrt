#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: physical payload and payload hashes are real."""
from tests.helpers import repo_path, load_json, sha256_file

def test_physical_payload_manifest_and_hashes():
    """Verify payload files exist and match manifest SHA256 values."""
    manifest = load_json("QIKVRT_MONTHLY_ARTIFACT_MANIFEST.json")
    assert manifest["artifact_count"] > 0
    assert manifest["pdf_count"] > 0
    checked = 0
    for item in manifest["items"]:
        path = repo_path(item["payload_path"])
        assert path.is_file(), item["payload_path"]
        assert path.stat().st_size == item["bytes"]
        assert sha256_file(path) == item["sha256"]
        checked += 1
    assert checked == manifest["artifact_count"]
