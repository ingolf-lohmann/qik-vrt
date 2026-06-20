#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Check assistant delivery response consistency against known open conditions."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
GATE = ROOT / "canonical" / "ASSISTANT_DELIVERY_RESPONSE_CONSISTENCY_GATE_V28.json"
VERDICT = ROOT / "publication" / "DELIVERY_VERDICT_V28.json"

def load_json(path):
    """Load JSON."""
    return json.loads(path.read_text(encoding="utf-8"))

def normalize(text):
    """Normalize response text for phrase checks."""
    return " ".join(text.lower().replace("`", " ").split())

def check_response_text(text):
    """Check candidate response text."""
    gate = load_json(GATE)
    verdict = load_json(VERDICT)
    norm = normalize(text)
    if verdict.get("overall_green") is False or int(verdict.get("known_open_condition_count", 0)) > 0:
        required = gate["required_status_when_open"].lower()
        assert required in norm, "required limited status missing"
        for phrase in gate["forbidden_unqualified_phrases_when_open"]:
            if phrase.lower() in norm:
                raise AssertionError("forbidden unqualified phrase with open conditions: " + phrase)
        assert "overall_green=false" in norm, "overall_green=false missing"
        assert "known_open_condition_count=3" in norm, "known_open_condition_count missing"
    return True

def main(argv=None):
    """Run gate."""
    if argv:
        text = pathlib.Path(argv[0]).read_text(encoding="utf-8") if pathlib.Path(argv[0]).is_file() else " ".join(argv)
    else:
        text = "LOCAL_SCOPE_PASS_WITH_KNOWN_OPEN_CONDITIONS_CONTINUE overall_green=false known_open_condition_count=3"
    check_response_text(text)
    print("PASS assistant delivery response consistency gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
