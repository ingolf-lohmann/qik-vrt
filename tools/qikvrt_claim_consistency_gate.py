#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# See LICENSES/Apache-2.0.txt.
"""Check claim consistency against known open conditions."""
from __future__ import annotations
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
KNOWN = ROOT / "canonical" / "KNOWN_OPEN_CONDITIONS_REGISTER_V27.json"
VERDICT = ROOT / "publication" / "DELIVERY_VERDICT_V27.json"

def load_json(path):
    """Load JSON."""
    return json.loads(path.read_text(encoding="utf-8"))

def check_claims():
    """Check that delivery verdict does not falsely claim green."""
    known = load_json(KNOWN)
    verdict = load_json(VERDICT)
    open_count = int(known.get("known_open_condition_count", 0))
    if open_count > 0:
        assert verdict.get("overall_green") is False, "known open conditions require overall_green=false"
        assert verdict.get("allowed_user_facing_summary") == known.get("allowed_completion_phrase")
        assert verdict.get("forbidden_user_facing_summary") in known.get("forbidden_completion_phrases")
    for condition in known["conditions"]:
        assert condition["status"] in {"PASS", "CONTINUE", "BLOCK", "ISOLATE"}, "invalid condition status"
        assert condition.get("blocking_false_claims"), "condition lacks false-claim blockers"
    return True

def main():
    """Run gate."""
    check_claims()
    print("PASS reflexive usability known-open-conditions claim gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
