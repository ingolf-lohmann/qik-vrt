#!/usr/bin/env python3
"""Run Lean's axiom printer and reject undeclared proof dependencies."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT_AUDIT_SOURCE = (
    ROOT / "QIKVRTFormalization" / "Claims" / "AxiomAuditAll.lean"
)
MANUSCRIPT_EXPECTED = {
    "QIKVRT.V2.Class.SET001_checked",
    "QIKVRT.V2.Class.MAP001_checked",
    "QIKVRT.V2.QUA003A_prefix_checked",
    "QIKVRT.V2.Class.SET003_checked",
    "QIKVRT.V2.Class.MAP003_checked",
    "QIKVRT.V2.GAT004_checked",
    "QIKVRT.V2.GAT005_checked",
    "QIKVRT.V2.GAT006_checked",
    "QIKVRT.V2.RET011_checked",
    "QIKVRT.V2.GAT002_checked",
    "QIKVRT.V2.DIM006A_additive_checked",
    "QIKVRT.V2.DIM007A_countermodel_checked",
    "QIKVRT.V2.OperationalContinuation.FIT001_checked",
    "QIKVRT.V2.ConnectabilitySimulation.FIT002_checked",
    "QIKVRT.V2.ConnectabilitySimulation.FIT003_checked",
    "QIKVRT.V2.WeightedConnectability.MAT001_checked",
    "QIKVRT.V2.WeightedConnectability.MAT002_checked",
}
WORLD_FORMULA_AUDIT_SOURCE = (
    ROOT / "QIKVRTFormalization" / "WorldFormula" / "AxiomAudit.lean"
)
WORLD_FORMULA_EXPECTED = {
    "QIKVRT.V2.WorldFormula.every_stage_has_a_successor",
    "QIKVRT.V2.WorldFormula.closedGenerative_iff_executableWorldFormula",
    "QIKVRT.V2.WorldFormula.unitArchitecture_executable",
    "QIKVRT.V2.WorldFormula.physicallyQualified_implies_formallyEstablished",
    "QIKVRT.V2.WorldFormula.physicallyQualified_implies_referenceBound",
    "QIKVRT.V2.WorldFormula.formalDerivability_not_sufficient_for_physicalQualification",
    "QIKVRT.V2.WorldFormula.ArtifactIdentity.complete_implies_sourceCommit",
}
EFFECT_ACK_AUDIT_SOURCE = ROOT / "QIKVRTEffectAck" / "AxiomAudit.lean"
EFFECT_ACK_MATRIX = ROOT / "effect_ack" / "DRAFT01_CLAIM_MATRIX.json"
FOUNDATIONAL_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}
MEASUREMENT_AUDIT_SOURCE = (
    ROOT.parents[1] / "docs/publications/2026-08-12-observer-relative-retrocausality"
    / "experiment-2026-10-15/AxiomAudit.lean"
)
MEASUREMENT_EXPECTED = {
    "QIKVRT.V2.Physics.MeasurementTransfer.exact_readout_is_within",
    "QIKVRT.V2.Physics.MeasurementTransfer.error_budgets_compose",
    "QIKVRT.V2.Physics.MeasurementTransfer.separated_readback_enclosures_establish_order",
    "QIKVRT.V2.Physics.MeasurementTransfer.admitted_run",
    "QIKVRT.V2.Physics.MeasurementTransfer.bound_runs_correspond",
    "QIKVRT.V2.Physics.MeasurementTransfer.bounded_prediction_transfers",
    "QIKVRT.V2.Physics.MeasurementTransfer.order_alone_does_not_identify_clock_scale",
    "QIKVRT.V2.Physics.MeasurementTransfer.exact_inertial_segment_example",
    "QIKVRT.V2.Physics.MeasurementTransfer.same_coordinate_duration_allows_different_proper_durations",
    "QIKVRT.V2.Physics.MeasurementTransfer.finite_calibration_does_not_force_next_prediction",
}
EFFECT_ACK_SUPPLEMENTAL = {
    "QIKVRT.EffectAck.V1.Claims.claimIds_count": set(),
    "QIKVRT.EffectAck.V1.Claims.claimIds_pairwise": set(),
}

SUCCESSION_AUDIT_SOURCE = ROOT / "QIKVRTFormalization/Hardware/AxiomAudit.lean"
SUCCESSION_EXPECTED = {
    "QIKVRT.V2.AuthoritySuccession." + name for name in (
        "majority_overlap", "majority_intersection", "same_epoch_election_unique",
        "one_effective_writer", "stale_epoch_rejected", "expired_lease_rejected",
        "no_quorum_holds_writes", "step_preserves_invariant", "step_retirement_persists",
        "step_epoch_monotone", "run_preserves_invariant", "run_retirement_persists",
        "run_epoch_monotone", "retirement_irreversible", "retired_never_authority",
        "retired_repromotion_impossible", "qualified_successor_can_write",
        "independent_carriers_split_brain",
    )
}


def require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def effect_ack_policy() -> dict[str, set[str]]:
    matrix = require_object(
        json.loads(EFFECT_ACK_MATRIX.read_text(encoding="utf-8")),
        "claim matrix",
    )
    claims = matrix.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim matrix claims must be an array")
    constants: set[str] = set()
    for index, raw_claim in enumerate(claims):
        claim = require_object(raw_claim, f"claim {index}")
        raw_constants = claim.get("proof_constants", [])
        if not isinstance(raw_constants, list):
            raise ValueError(f"claim {index} proof_constants must be an array")
        claim_constants = list(raw_constants)
        registry = claim.get("registry_constant")
        if registry is not None:
            claim_constants.append(registry)
        for constant in claim_constants:
            if not isinstance(constant, str) or not constant:
                raise ValueError(f"claim {index} contains an invalid constant")
            constants.add(constant)
    constants.update(EFFECT_ACK_SUPPLEMENTAL)

    raw_axiom_policy = require_object(
        matrix.get("axiom_policy"),
        "axiom_policy",
    )
    foundational = raw_axiom_policy.get("foundational_allowlist")
    if not isinstance(foundational, list) or set(foundational) != FOUNDATIONAL_AXIOMS:
        raise ValueError("foundational_allowlist does not match the locked policy")
    raw_default = raw_axiom_policy.get("default_expected_axioms")
    if not isinstance(raw_default, list) or not all(
        isinstance(item, str) and item for item in raw_default
    ):
        raise ValueError("default_expected_axioms must be an array of strings")
    default = set(raw_default)
    if default - FOUNDATIONAL_AXIOMS:
        raise ValueError("default_expected_axioms contains forbidden axioms")
    raw_overrides = require_object(
        raw_axiom_policy.get("per_constant_expected_axioms"),
        "per_constant_expected_axioms",
    )
    unknown_constants = set(raw_overrides) - constants
    if unknown_constants:
        raise ValueError(
            f"axiom policy names unknown constants {sorted(unknown_constants)}"
        )
    policy: dict[str, set[str]] = {}
    for constant in constants:
        raw_allowed = raw_overrides.get(constant, raw_default)
        if not isinstance(raw_allowed, list) or not all(
            isinstance(item, str) and item for item in raw_allowed
        ):
            raise ValueError(f"{constant} axiom policy must be strings")
        allowed = set(raw_allowed)
        unknown = allowed - FOUNDATIONAL_AXIOMS
        if unknown:
            raise ValueError(f"{constant} declares forbidden axioms {sorted(unknown)}")
        policy[constant] = allowed

    expected_lines = {f"#print axioms {name}" for name in policy}
    actual_lines = {
        line.strip()
        for line in EFFECT_ACK_AUDIT_SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#print axioms ")
    }
    if actual_lines != expected_lines:
        missing = sorted(expected_lines - actual_lines)
        extra = sorted(actual_lines - expected_lines)
        raise ValueError(
            f"generated EFFECT_ACK audit drift; missing={missing}, extra={extra}"
        )
    return policy


def validate_world_formula_audit_source() -> None:
    expected_lines = {f"#print axioms {name}" for name in WORLD_FORMULA_EXPECTED}
    actual_lines = {
        line.strip()
        for line in WORLD_FORMULA_AUDIT_SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("#print axioms ")
    }
    if actual_lines != expected_lines:
        missing = sorted(expected_lines - actual_lines)
        extra = sorted(actual_lines - expected_lines)
        raise ValueError(
            f"world-formula audit drift; missing={missing}, extra={extra}"
        )


def parse_axiom_reports(output: str) -> list[tuple[str, set[str]]]:
    """Lean wraps long dependency lists; preserve every reported dependency."""
    pattern = re.compile(
        r"^'(?P<name>[^']+)' (?:does not depend on any axioms|"
        r"depends on axioms: \[(?P<axioms>[^]]*)\])$",
        re.MULTILINE,
    )
    return [
        (match.group("name"), {
            item.strip() for item in (match.group("axioms") or "").split(",")
            if item.strip()
        })
        for match in pattern.finditer(output)
    ]


def main() -> int:
    try:
        effect_policy = effect_ack_policy()
        validate_world_formula_audit_source()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: invalid axiom policy: {exc}", file=sys.stderr)
        return 1
    manuscript_policy = {
        name: set(FOUNDATIONAL_AXIOMS) for name in MANUSCRIPT_EXPECTED
    }
    world_formula_policy = {name: set() for name in WORLD_FORMULA_EXPECTED}
    measurement_policy = {
        name: set(FOUNDATIONAL_AXIOMS) for name in MEASUREMENT_EXPECTED
    }
    succession_policy = {name: set(FOUNDATIONAL_AXIOMS) for name in SUCCESSION_EXPECTED}
    audits = (
        (MANUSCRIPT_AUDIT_SOURCE, manuscript_policy, False),
        (EFFECT_ACK_AUDIT_SOURCE, effect_policy, True),
        (WORLD_FORMULA_AUDIT_SOURCE, world_formula_policy, True),
        (MEASUREMENT_AUDIT_SOURCE, measurement_policy, False),
        (SUCCESSION_AUDIT_SOURCE, succession_policy, False),
    )
    seen: set[str] = set()
    violations: list[str] = []
    expected = set().union(*(policy for _, policy, _ in audits))
    for audit_source, audit_policy, require_exact in audits:
        result = subprocess.run(
            ["lake", "env", "lean", str(audit_source)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            print(output, file=sys.stderr)
            return result.returncode
        for name, axioms in parse_axiom_reports(output):
            if name not in audit_policy:
                continue
            seen.add(name)
            unexpected = axioms - audit_policy[name]
            if unexpected:
                violations.append(
                    f"{name}: forbidden axioms {sorted(unexpected)}"
                )
            elif require_exact and axioms != audit_policy[name]:
                violations.append(
                    f"{name}: actual axioms {sorted(axioms)} do not equal "
                    f"declared {sorted(audit_policy[name])}"
                )

    missing = expected - seen
    if missing:
        violations.append(f"missing axiom reports: {sorted(missing)}")
    if violations:
        for violation in violations:
            print(f"ERROR: {violation}", file=sys.stderr)
        return 1

    print(
        f"PASS axiom audit: {len(expected)} checked theorems; "
        f"{len(effect_policy)} EFFECT_ACK constants use per-claim policies; "
        f"{len(world_formula_policy)} world-formula theorems are axiom-free; "
        f"{len(measurement_policy)} scoped measurement-transfer theorems checked; "
        f"{len(succession_policy)} conditional authority-succession theorems checked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
