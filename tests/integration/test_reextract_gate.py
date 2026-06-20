#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Integration test: package includes re-extract verification evidence in docs."""
from tests.helpers import repo_path

def test_reextract_gate_is_documented_and_required():
    """Verify re-extract verification is documented as release condition."""
    text = repo_path("docs/RED_GREEN_REFACTOR_RECORD.md").read_text(encoding="utf-8") + repo_path("README.md").read_text(encoding="utf-8")
    assert "Re-Extract" in text or "re-extract" in text
    assert "Master" in text or "master" in text
