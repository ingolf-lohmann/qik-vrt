#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Regression test: current license acceptance is persisted."""
from tests.helpers import load_json
def test_current_license_acceptance_record():
    record = load_json("LICENSE_ACCEPTANCE_RECORD.json")
    assert record["schema"] == "qikvrt_license_acceptance_record_v40"
    assert record["status"] == "ACCEPTED_AND_PERSISTED_IN_V40_FIRST_SUBSEQUENT_PERSISTENCE"
    assert record["product_owner"] == "Ingolf Lohmann"
    assert "volatile runtime state persisted in delivery ZIP" in record["accepted_scope"]
