#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: every JSON file has embedded license terms."""
from tests.helpers import ROOT, assert_json_license

def test_every_json_file_embeds_license_object():
    """Parse all JSON files and verify their _license object."""
    json_files = [p for p in ROOT.rglob("*.json") if "__pycache__" not in p.parts and ".git" not in p.parts]
    assert len(json_files) > 0
    for path in json_files:
        assert path.is_file()
        assert path.suffix == ".json"
        license_data = assert_json_license(path.relative_to(ROOT).as_posix())
        assert license_data["rights_holder"] == "Ingolf Lohmann"
        assert "license_text_ref" in license_data
