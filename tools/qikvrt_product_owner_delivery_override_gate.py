#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Validate Product Owner final artifact delivery override."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "canonical" / "PRODUCT_OWNER_FINAL_ARTIFACT_DELIVERY_OVERRIDE_GATE_V31.json"
VERDICT = ROOT / "publication" / "FINAL_ARTIFACT_DELIVERY_VERDICT_V31.json"

def load_json(path):
    """Load JSON."""
    return json.loads(path.read_text(encoding="utf-8"))

def main(argv=None):
    """Run gate."""
    gate = load_json(GATE)
    verdict = load_json(VERDICT)
    assert gate["product_owner_override"] is True, "product owner override missing"
    assert gate["artifact_delivery_allowed"] is True, "delivery not allowed"
    assert gate["external_evidence_claims"] is False, "false external claims enabled"
    assert gate["no_false_external_claims"] is True, "false-claim guard not active"
    assert verdict["delivery_status"] == "FINAL_ARTIFACT_DELIVERY_AUTHORIZED_BY_PRODUCT_OWNER_OVERRIDE"
    assert verdict["artifact_delivery_allowed"] is True
    assert verdict["product_owner_override"] is True
    assert verdict["external_evidence_claims"] is False
    assert verdict["no_false_external_claims"] is True
    print("PASS product owner final artifact delivery override gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
