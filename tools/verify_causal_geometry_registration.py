#!/usr/bin/env python3
"""Fail closed if the causal-geometry source is not wired into the Lean core."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
MODULE = PROJECT / "QIKVRTEffectAck/CausalGeometry.lean"
AUDIT = PROJECT / "QIKVRTEffectAck/CausalGeometryAxiomAudit.lean"
ENTRY = PROJECT / "QIKVRTEffectAck.lean"

EXPECTED = {
    "before_transitive",
    "before_irreflexive",
    "before_asymmetric",
    "causalOrder_strictPartialOrder",
    "causalInterval_membership",
    "causalInterval_finite",
    "roundTrip_leftInverse",
    "roundTrip_rightInverse_onCanonical",
    "roundTrip_encode_injective",
    "roundTrip_relation_iff",
    "roundTrip_relation_preserved",
    "emptyGraph_path_endpoints",
    "emptyGraph_distinct_events_incomparable",
}
NAMESPACE = "QIKVRT.CausalGeometry.V1"


def fail(message: str) -> None:
    print("BLOCK: " + message, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    for path in (MODULE, AUDIT, ENTRY):
        if not path.is_file():
            fail(f"required Lean integration file missing: {path.relative_to(ROOT)}")

    module = MODULE.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")

    declarations = set(re.findall(r"^theorem ([A-Za-z_][A-Za-z0-9_]*)", module, re.M))
    if declarations != EXPECTED:
        fail(
            "theorem inventory mismatch; "
            f"missing={sorted(EXPECTED - declarations)}, "
            f"extra={sorted(declarations - EXPECTED)}"
        )

    expected_audit = {f"#print axioms {NAMESPACE}.{name}" for name in EXPECTED}
    actual_audit = {
        line.strip()
        for line in audit.splitlines()
        if line.strip().startswith("#print axioms ")
    }
    if actual_audit != expected_audit:
        fail(
            "axiom-audit inventory mismatch; "
            f"missing={sorted(expected_audit - actual_audit)}, "
            f"extra={sorted(actual_audit - expected_audit)}"
        )

    required_imports = {
        "import QIKVRTEffectAck.CausalGeometry",
        "import QIKVRTEffectAck.CausalGeometryAxiomAudit",
    }
    imports = set(entry.splitlines())
    if not required_imports <= imports:
        fail(f"Lean library entry point omits imports: {sorted(required_imports - imports)}")

    toolchain = (PROJECT / "lean-toolchain").read_text(encoding="utf-8").strip()
    if toolchain != "leanprover/lean4:v4.19.0":
        fail(f"unexpected Lean toolchain: {toolchain}")

    print(
        "PASS causal-geometry registration: "
        f"{len(EXPECTED)} theorem declarations, exact axiom audit, "
        "both root imports and Lean 4.19.0 pinned"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
