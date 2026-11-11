#!/usr/bin/env python3
"""Fail closed if the dependent causal-geometry package is not registered."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "formalization/QIKVRT_Formalization_v2.0"
CORE_ENTRY = CORE / "QIKVRTEffectAck.lean"
PACKAGE = ROOT / "formalization/QIKVRT_CausalGeometry_v1"
MODULE = PACKAGE / "QIKVRTCausalGeometry/CausalGeometry.lean"
AUDIT = PACKAGE / "QIKVRTCausalGeometry/AxiomAudit.lean"
ENTRY = PACKAGE / "QIKVRTCausalGeometry.lean"

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
LOCKED_CORE_ENTRY_BLOB = "3ba05628fd377a54f71936d4bc6bfc1b969a5695"


def fail(message: str) -> None:
    print("BLOCK: " + message, file=sys.stderr)
    raise SystemExit(1)


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def main() -> int:
    for path in (CORE_ENTRY, MODULE, AUDIT, ENTRY):
        if not path.is_file():
            fail(f"required Lean integration file missing: {path.relative_to(ROOT)}")

    if git_blob_sha1(CORE_ENTRY.read_bytes()) != LOCKED_CORE_ENTRY_BLOB:
        fail("historical EFFECT_ACK entry point changed; preserve its locked bytes")

    module = MODULE.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    entry = ENTRY.read_text(encoding="utf-8")
    lakefile = (PACKAGE / "lakefile.toml").read_text(encoding="utf-8")
    toolchain = (PACKAGE / "lean-toolchain").read_text(encoding="utf-8").strip()

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

    if "import QIKVRTEffectAck.CausalDistance" not in module.splitlines():
        fail("geometry module does not import the established CausalDistance core")
    if "import QIKVRTCausalGeometry.CausalGeometry" not in entry.splitlines():
        fail("dependent package entry point omits the geometry module")
    if "import QIKVRTCausalGeometry.AxiomAudit" not in entry.splitlines():
        fail("dependent package entry point omits its axiom audit")
    if 'name = "QIKVRTFormalizationV2"' not in lakefile or 'path = "../QIKVRT_Formalization_v2.0"' not in lakefile:
        fail("geometry package is not linked to the existing formalization package")
    if toolchain != "leanprover/lean4:v4.19.0":
        fail(f"unexpected Lean toolchain: {toolchain}")

    print(
        "PASS causal-geometry registration: "
        f"{len(EXPECTED)} theorem declarations, exact axiom audit, "
        "dependent core import and historical EFFECT_ACK entry point byte-locked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
