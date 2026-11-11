#!/usr/bin/env python3
"""Fail CI if the Mathlib extension drifts from its evidence contract."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "formalization/QIKVRT_SpacetimeBridge_Mathlib_v1"
POLICY = PACKAGE / "evidence-status.json"
SOURCE = PACKAGE / "QIKVRTSpacetimeBridgeMathlib/RealVolumeLaw.lean"
AUDIT = PACKAGE / "QIKVRTSpacetimeBridgeMathlib/AxiomAudit.lean"
README = PACKAGE / "README.md"


def fail(message: str) -> None:
    print(f"EVIDENCE POLICY FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


policy = json.loads(POLICY.read_text(encoding="utf-8"))
source = SOURCE.read_text(encoding="utf-8")
audit = AUDIT.read_text(encoding="utf-8")
readme = README.read_text(encoding="utf-8")

if policy.get("schema_version") != 1:
    fail("unsupported evidence-status.json schema_version")

# Every ledger entry must match an actual Lean metadata declaration.
for declaration, status in policy["statuses"].items():
    expected = (
        rf"def\s+{re.escape(declaration)}\s*:\s*EvidenceStatus\s*:=\s*"
        rf"\.({re.escape(status)})\b"
    )
    if not re.search(expected, source):
        fail(f"{declaration} is absent or does not match ledger status {status}")
    if f"#print axioms QIKVRT.SpacetimeBridge.MathlibV1.{declaration}" not in audit:
        fail(f"{declaration} is missing from AxiomAudit.lean")

for declaration in policy["axiom_audit_required"]:
    if f"#print axioms QIKVRT.SpacetimeBridge.MathlibV1.{declaration}" not in audit:
        fail(f"{declaration} is missing from the required axiom audit")

# Require the normative boundary to remain documented.
for phrase in (
    "It does not by itself establish",
    "Open formal obligation",
    "Interpretive claim",
    "must first be specified and proved",
):
    if phrase not in readme:
        fail(f"README.md is missing normative evidence-boundary text: {phrase!r}")

# No unfinished proof placeholders or project axioms are permitted in this
# package. Strip Lean line and block comments before scanning source tokens.
for path in PACKAGE.rglob("*.lean"):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"/-.*?-/", "", text, flags=re.S)
    text = re.sub(r"--[^\n]*", "", text)
    if re.search(r"\b(sorry|admit)\b", text):
        fail(f"unfinished proof placeholder found in {path.relative_to(ROOT)}")
    if re.search(r"^\s*axiom\s+", text, flags=re.M):
        fail(f"project axiom declaration found in {path.relative_to(ROOT)}")

print("Evidence policy check passed: ledger, Lean metadata, axiom audit,")
print("normative README boundary, and no placeholders/project axioms.")
