# QIK-VRT Evidence Compliance Record

**Record status: PENDING — full Lean axiom-audit revalidation required.**

This record is the repository's prominent, auditable statement of what has and has not been demonstrated for the Mathlib spacetime extension. It is not a self-certification of universal scientific or ontological truth.

## Normative rule

Every claim in the formalization must be identified as one of:

1. **Kernel-checked theorem** — Lean's kernel accepts the proof relative to the imported declarations and axioms.
2. **Formalized model statement** — a theorem whose scope is the definitions and assumptions encoded in Lean.
3. **Open formal obligation** — a required step not yet proved; it must not be represented as established.
4. **Interpretive claim** — a philosophical, ontological, or empirical interpretation, not a theorem merely because related mathematics is proved.

No evidence label changes the truth status of a proposition. No Lean proof alone establishes empirical truth, model completeness, or universal ontological applicability. “Monotone expansion” remains unproved until its state space, order, transition relation, and monotonicity proposition are specified and proved.

## Machine-enforced controls

The Mathlib extension contains:

- `evidence-status.json`: machine-readable status ledger;
- `RealVolumeLaw.lean`: Lean declarations for the classifications;
- `AxiomAudit.lean`: `#print axioms` audit of the classifications and named mathematical declarations;
- `scripts/check_evidence_policy.py`: CI check cross-checking the ledger, Lean declarations, audit coverage, README boundary, and absence of `sorry`, `admit`, and project-level `axiom` declarations;
- `.github/workflows/spacetime-mathlib.yml`: runs the policy check before the pinned Lean/Mathlib build and axiom audit.

The check is scoped to `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1`; it is not a claim that every file or every workflow in the entire repository has been exhaustively proved compliant.

## Current evidence ledger

| Claim | Classification | Meaning |
|---|---|---|
| Positive-real scalar scale injectivity | `kernelChecked` | A Lean theorem exists and is included in the axiom audit. |
| Smooth geometric/measure bridge | `openFormalObligation` | Not established by the scalar result. |
| Poisson normalization and moments | `openFormalObligation` | Not established by the scalar result; separate proof work remains. |
| Universal ontological applicability | `interpretiveClaim` | Not a theorem of this formalization. |

The authoritative machine-readable classifications are in `evidence-status.json`. The Lean axiom audit, not the label alone, is the evidence about dependencies.

## Verification record

- Repository: `ingolf-lohmann/qik-vrt`
- Policy branch: `policy/enforce-evidence-boundary-2026-11-11`
- Last inspected run before the current datatype-isolation correction: [GitHub Actions run #43008323505](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43008323505)
- In that run the policy script passed and the Lean/Mathlib build completed. The axiom audit then rejected generated support declarations for `EvidenceStatus` (`lcUnreachable` and `lcProof`). This is a real audit failure, not a passing proof certificate.
- The datatype has since been moved outside the audited theorem namespace to avoid auditing compiler-generated datatype support as project theorem dependencies. This correction is **not yet verified** by a completed run.

**Acceptance condition:** this record may be changed to **PASS** only after a single identified commit has a successful policy check, Lean/Mathlib build, and axiom audit, with the resulting run URL and exact commit SHA recorded here. Until then, the status remains **PENDING**.

## Governance limitation

This record and CI checks make the policy inspectable and testable. They do not, by themselves, configure GitHub branch protection, prevent an authorized administrator from bypassing checks, or compel third parties to accept the conclusions. Required status checks and bypass policy must be configured in repository settings by an authorized maintainer.