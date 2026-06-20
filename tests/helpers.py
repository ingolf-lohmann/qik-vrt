#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Shared helper functions for V16 semantic backfill tests."""
from __future__ import annotations
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def repo_path(relative: str) -> pathlib.Path:
    """Return a path relative to repository root."""
    return ROOT / relative

def load_json(relative: str):
    """Load a JSON file relative to repository root."""
    return json.loads(repo_path(relative).read_text(encoding="utf-8"))

def sha256_file(path: pathlib.Path) -> str:
    """Compute SHA256 for a repository file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def all_repo_files():
    """List repository files excluding cache and .git folders."""
    return sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".git" not in p.parts)

def assert_json_license(relative: str):
    """Assert that a JSON file contains embedded license metadata."""
    data = load_json(relative)
    assert isinstance(data, dict), f"{relative} root must be object"
    license_data = data.get("_license")
    assert isinstance(license_data, dict), f"{relative} missing _license"
    for key in ["copyright", "rights_holder", "license", "license_text_ref", "classification"]:
        assert license_data.get(key), f"{relative} missing _license.{key}"
    return license_data
