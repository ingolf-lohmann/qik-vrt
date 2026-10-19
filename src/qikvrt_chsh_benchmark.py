# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic CHSH reference calculations, not a QIK derivation or experiment.

Run ``python3 -B -m src.qikvrt_chsh_benchmark`` from the repository root.
Only the Python standard library is required. Every box lists all 16
conditional probabilities, including zeros. Settings are conditioned on;
they are not inferred from a simulated random sample.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

SETTINGS = tuple(itertools.product((0, 1), repeat=2))
OUTCOMES = tuple(itertools.product((-1, 1), repeat=2))
TOLERANCE = 1e-12
TSIRELSON = 2 * math.sqrt(2)
Box = dict[tuple[int, int], dict[tuple[int, int], float]]


def validate_box(box: Mapping) -> None:
    """Require complete, finite, nonnegative, normalized conditional tables.

    Tolerance is for normalization/arithmetic, never a negative-probability
    allowance. No clipping, renormalization, or missing-zero imputation occurs.
    """
    def exact_keys(keys, expected):
        return (set(keys) == set(expected) and all(
            type(k) is tuple and len(k) == 2 and all(type(v) is int for v in k)
            for k in keys))

    if not isinstance(box, Mapping) or not exact_keys(box, SETTINGS):
        raise ValueError("all four integer setting pairs are required")
    for setting, row in box.items():
        if not isinstance(row, Mapping) or not exact_keys(row, OUTCOMES):
            raise ValueError(f"all four integer outcome pairs required at {setting}")
        if any(type(p) not in (float, int) or not 0 <= p <= 1 or not math.isfinite(p)
               for p in row.values()):
            raise ValueError("probabilities must be finite real numbers in [0,1]")
        if abs(math.fsum(row.values()) - 1) > TOLERANCE:
            raise ValueError(f"probabilities are not normalized at {setting}")


def no_signalling_residuals(box: Mapping) -> dict[str, float]:
    """Maximum remote-setting dependence of each party's marginal."""
    validate_box(box)
    alice = max(abs(math.fsum(box[x, 0][a, b] for b in (-1, 1))
                    - math.fsum(box[x, 1][a, b] for b in (-1, 1)))
                for x in (0, 1) for a in (-1, 1))
    bob = max(abs(math.fsum(box[0, y][a, b] for a in (-1, 1))
                  - math.fsum(box[1, y][a, b] for a in (-1, 1)))
              for y in (0, 1) for b in (-1, 1))
    return {"alice": alice, "bob": bob}


def correlations(box: Mapping) -> dict[tuple[int, int], float]:
    validate_box(box)
    return {xy: math.fsum(a * b * p for (a, b), p in box[xy].items())
            for xy in SETTINGS}


def chsh(box: Mapping) -> float:
    """Signed S=E00+E01+E10-E11; inequalities apply to |S|."""
    e = correlations(box)
    return math.fsum((e[0, 0], e[0, 1], e[1, 0], -e[1, 1]))


def chsh_facets(box: Mapping) -> list[float]:
    """All eight CHSH sign patterns, product(signs)=-1.

    Inspecting one oriented S alone can miss a relabelled violation.
    This is a ceiling test, not a certificate of quantum realizability.
    """
    e = correlations(box)
    return [math.fsum(s * e[xy] for s, xy in zip(signs, SETTINGS))
            for signs in itertools.product((-1, 1), repeat=4)
            if math.prod(signs) == -1]


def require_chsh_ceiling(box: Mapping, ceiling: float) -> None:
    """Reject signalling or any CHSH facet above the stated necessary bound."""
    if type(ceiling) not in (int, float) or not 0 <= ceiling <= 4 or not math.isfinite(ceiling):
        raise ValueError("finite CHSH ceiling in [0,4] required")
    if max(no_signalling_residuals(box).values()) > TOLERANCE:
        raise ValueError("no-signalling violated")
    if max(map(abs, chsh_facets(box))) > ceiling + TOLERANCE:
        raise ValueError("CHSH ceiling violated")


def box_from_records(records: list[dict]) -> Box:
    """Input adapter for a future QIK law: 16 records with x,y,a,b,p fields.

    These are model probabilities, not detector counts. Duplicate/missing
    cells, coercion and silent renormalization are deliberately forbidden.
    """
    if not isinstance(records, list) or len(records) != 16:
        raise ValueError("exactly sixteen conditional-probability records required")
    box = {xy: {} for xy in SETTINGS}
    for r in records:
        if (not isinstance(r, dict) or set(r) != {"x", "y", "a", "b", "p"}
                or any(type(r[k]) is not int for k in ("x", "y", "a", "b"))
                or (r["x"], r["y"]) not in SETTINGS
                or (r["a"], r["b"]) not in OUTCOMES):
            raise ValueError("invalid conditional-probability record")
        row, ab = box[r["x"], r["y"]], (r["a"], r["b"])
        if ab in row:
            raise ValueError("duplicate probability cell")
        row[ab] = r["p"]
    validate_box(box)
    return box


def candidate_report(box: Mapping) -> dict:
    e = correlations(box)
    residuals = no_signalling_residuals(box)
    maximum = max(map(abs, chsh_facets(box)))
    return {
        "schema": "qikvrt-chsh-candidate/1", "S": chsh(box),
        "correlations": {f"E{x}{y}": e[x, y] for x, y in SETTINGS},
        "max_abs_CHSH_facet": maximum, "no_signalling_residuals": residuals,
        "no_signalling": max(residuals.values()) <= TOLERANCE,
        "within_local_CHSH_ceiling": maximum <= 2 + TOLERANCE,
        "within_quantum_CHSH_ceiling": maximum <= TSIRELSON + TOLERANCE,
        "quantum_membership": "NOT_DECIDED_BY_THIS_BENCHMARK",
        "qik_derivation": False, "empirical_measurement": False,
    }


def local_deterministic(values: Sequence[int]) -> Box:
    """A0,A1,B0,B1 in {-1,+1}; 16 vertices of the local (2,2,2) polytope."""
    if len(values) != 4 or any(type(v) is not int or v not in (-1, 1) for v in values):
        raise ValueError("four deterministic binary responses required")
    return {(x, y): {(a, b): float((a, b) == (values[x], values[2 + y]))
                      for a, b in OUTCOMES} for x, y in SETTINGS}


def classical_reference() -> Box:
    """Unbiased shared bit: a=b=lambda, P(lambda=+/-1)=1/2, independent of x,y."""
    return {xy: {(a, b): 0.5 if a == b else 0.0 for a, b in OUTCOMES}
            for xy in SETTINGS}


def quantum_reference(
    alice_angles: Sequence[float] = (0.0, math.pi / 2),
    bob_angles: Sequence[float] = (math.pi / 4, -math.pi / 4),
) -> Box:
    """Born probabilities for |Phi+> and real XZ-plane spin observables.

    Imported QM assumptions: H=C^2 tensor C^2, |Phi+>=(|00>+|11>)/sqrt(2),
    O(theta)=cos(theta) Z+sin(theta) X; P_a=(I+a O)/2.
    Compute ||(P_a tensor P_b)|Phi+>||^2, equal to the Born expectation
    for projectors, without inserting a target CHSH value. Squared norms
    avoid cancellation into negative roundoff at zero-probability cells.
    The angles are mathematical settings in radians.
    """
    if any(len(angles) != 2 or any(type(t) not in (int, float)
           or not math.isfinite(t) for t in angles)
           for angles in (alice_angles, bob_angles)):
        raise ValueError("two finite angles per party required")

    def projector(theta, outcome):
        c, s = math.cos(theta), math.sin(theta)
        return (((1 + outcome * c) / 2, outcome * s / 2),
                (outcome * s / 2, (1 - outcome * c) / 2))

    # Only |00> and |11> are nonzero in this normalized reference state.
    state = ((0, 0, 1 / math.sqrt(2)), (1, 1, 1 / math.sqrt(2)))
    box = {}
    for x, y in SETTINGS:
        row = {}
        for a, b in OUTCOMES:
            pa = projector(alice_angles[x], a)
            pb = projector(bob_angles[y], b)
            row[a, b] = math.fsum(
                math.fsum(cj * pa[i][j] * pb[k][l] for j, l, cj in state) ** 2
                for i, k in itertools.product((0, 1), repeat=2))
        box[x, y] = row
    validate_box(box)
    return box


def pr_reference() -> Box:
    """PR box: a*b=(-1)^(x*y), equivalently alpha XOR beta=x*y."""
    return {(x, y): {(a, b): 0.5 if a * b == (-1) ** (x * y) else 0.0
                      for a, b in OUTCOMES} for x, y in SETTINGS}


def reference_report() -> dict:
    cases = []
    for name, box, expected in (
        ("local_shared_bit", classical_reference(), 2.0),
        ("quantum_born_phi_plus", quantum_reference(), TSIRELSON),
        ("no_signalling_pr_box", pr_reference(), 4.0),
    ):
        residuals = no_signalling_residuals(box)
        e = correlations(box)
        maximum = max(map(abs, chsh_facets(box)))
        cases.append({
            "name": name, "evidence_class": "DETERMINISTIC_REFERENCE_CALCULATION",
            "probabilities": [{"x": x, "y": y, "a": a, "b": b, "p": box[x, y][a, b]}
                              for x, y in SETTINGS for a, b in OUTCOMES],
            "correlations": {f"E{x}{y}": e[x, y] for x, y in SETTINGS},
            "S": chsh(box), "abs_S": abs(chsh(box)),
            "expected_abs_S": expected,
            "reference_error": abs(abs(chsh(box)) - expected),
            "max_abs_CHSH_facet": maximum,
            "no_signalling_residuals": residuals,
            "no_signalling": max(residuals.values()) <= TOLERANCE,
            "within_local_CHSH_ceiling": maximum <= 2 + TOLERANCE,
            "within_quantum_CHSH_ceiling": maximum <= TSIRELSON + TOLERANCE,
            "quantum_membership_certified_by_ceiling": False,
            "qik_derivation": False,
        })
    vertices = [local_deterministic(v) for v in itertools.product((-1, 1), repeat=4)]
    return {
        "schema": "qikvrt-chsh-reference/1", "tolerance": TOLERANCE,
        "formula": "S=E00+E01+E10-E11; E_xy=sum_ab(a*b*P(a,b|x,y))",
        "setting_distribution_for_future_trials": "independent uniform P(x,y)=1/4",
        "method": "complete conditional probability tables; no random sampling",
        "cases": cases,
        "local_vertices_enumerated": len(vertices),
        "local_vertex_max_abs_CHSH": max(abs(chsh(v)) for v in vertices),
        "qik_R1_status": "REFERENCE_BENCHMARK_ONLY_QIK_CORRELATION_LAW_OPEN",
        "empirical_measurement": False, "formal_kernel_proof": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path,
                        help="JSON array of 16 x,y,a,b,p records from a candidate model")
    args = parser.parse_args()
    try:
        report = (candidate_report(box_from_records(json.loads(args.candidate.read_text(encoding="utf-8"))))
                  if args.candidate else reference_report())
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True,
                     indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
