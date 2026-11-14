# QIK-VRT Evidence Compliance Record

**Record status: PASS — Mathlib extension evidence controls passed on exact commit `89653507bf8d6d6da28cf3a80dc6ee9cdd6b83ae` in workflow [#43215557270](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43215557270).**

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
- Pull request: [#746](https://github.com/ingolf-lohmann/qik-vrt/pull/746) (draft; not merged at time of verification)
- Policy branch: `policy/enforce-evidence-boundary-2026-11-11`
- Exact verified commit: `065ad950c541ab8fbf862ad39601e3ddb44459e3`
- Successful workflow: [Spacetime Mathlib extension run #43013144965](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43013144965)
- The single job `mathlib-build-and-axiom-audit` completed successfully. Its individual steps show:
  1. **Evidence policy check — success.**
  2. **Pinned Lean toolchain and dependency installation — success.**
  3. **Lean/Mathlib build — success** (`Build completed successfully.`).
  4. **Axiom audit — success** (`audited 33 declaration(s) under 'QIKVRTSpacetimeBridgeMathlib'; all within the allowlist [propext, Classical.choice, Quot.sound]`).
- The four evidence metadata declarations were each reported as having no axiom dependencies. The three mathematical declarations were reported with the allowlisted dependencies `propext`, `Classical.choice`, and `Quot.sound`.
- This resolves the earlier audit failure caused by generated inductive support declarations: the evidence labels now use string-backed categories, and the axiom-audit tool accepted all 33 declarations in the audited package.
- A separate general workflow, [QIKVRT CI run #43013144967](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43013144967), failed at `Enforce terminal tested-fixpoint disposition`; its preceding full compile, launcher, protocol, handler, security and TCP/IP tests passed. This separate workflow is not one of the three Mathlib-extension acceptance checks above and is not represented as passing.
- Earlier failed audit run: [#43012119174](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43012119174), on the prior commit, rejected generated `EvidenceStatus` support declarations. It is retained here as historical failure evidence, not hidden.
- **Scope of PASS:** only the controls and declarations under `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1` covered by this workflow. This is not a repository-wide proof of compliance.

The three acceptance checks were completed successfully on the same exact commit and in the same workflow run. The PASS designation above records that bounded CI result; it does not certify empirical claims, completeness of the physical model, or universal ontological applicability.

## Governance limitation

This record and CI checks make the policy inspectable and testable. They do not, by themselves, configure GitHub branch protection, prevent an authorized administrator from bypassing checks, or compel third parties to accept the conclusions. Required status checks and bypass policy must be configured in repository settings by an authorized maintainer.

## Latest exact-head verification — 2026-11-11

- Repository: `ingolf-lohmann/qik-vrt`
- Pull request: [#746](https://github.com/ingolf-lohmann/qik-vrt/pull/746) (open, draft, not merged at verification time)
- Branch: `policy/enforce-evidence-boundary-2026-11-11`
- Exact verified commit: `99a293e1bce94f57eb82020009775b4137e9c3ba`
- Root tree: `f17e3256a9d660531b473c2be5bd247440bd8f53`
- Successful workflow: [Spacetime Mathlib extension run #43016983959](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43016983959)
- Job: `mathlib-build-and-axiom-audit` — success. The job and its logs were inspected.
- **Evidence policy check — success.** The log reports: “Evidence policy check passed: ledger, Lean metadata, axiom audit, normative README boundary, and no placeholders/project axioms.”
- **Pinned toolchain/dependencies — success.** Lean `v4.19.0`; Mathlib checked out at `c44e0c8ee63ca166450922a373c7409c5d26b00b`; the Lean action is pinned to commit `bd5cb0b830eda614ce3fc186d8429b9409b16c47` (v1.7.0).
- **Lean/Mathlib build — success.** The job log reports `Build completed successfully.`
- **Axiom audit — success.** The audit reports 33 declarations under `QIKVRTSpacetimeBridgeMathlib`, all within `[propext, Classical.choice, Quot.sound]`; the audit command completed successfully.
- The workflow executes the policy check, pinned Lean/Mathlib build, and axiom audit in the same job on this exact commit. All three acceptance checks therefore pass together on `99a293e1bce94f57eb82020009775b4137e9c3ba`.

### Separate repository-wide CI status (not part of the three Mathlib checks)

- [QIKVRT CI run #43016983665](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43016983665), also on `99a293e1bce94f57eb82020009775b4137e9c3ba`, failed in its general test job at `tools/qikvrt_integrity.py verify`: “BLOCK repository manifest differs from deterministic regeneration.”
- The diagnostic identifies an added `EVIDENCE_COMPLIANCE.md` entry and changed manifest records for `README.md`, `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1/QIKVRTSpacetimeBridgeMathlib/RealVolumeLaw.lean`, and `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1/README.md`. The terminal tested-fixpoint disposition consequently failed.
- This separate repository-integrity failure is not one of the three checks in `spacetime-mathlib.yml`; it is recorded transparently and is **not** represented as passing. No repository-wide PASS is claimed.

The PASS designation remains strictly limited to the Mathlib extension paths and declarations exercised by this workflow. It does not prove empirical truth, universal ontology, complete physical-model validity, GitHub branch protection, or acceptance by third parties.


## Latest exact-head verification — 2026-11-12

- Repository: `ingolf-lohmann/qik-vrt`
- Pull request: [#746](https://github.com/ingolf-lohmann/qik-vrt/pull/746) (open, draft, not merged at verification time)
- Branch: `policy/enforce-evidence-boundary-2026-11-11`
- Exact verified commit: `89653507bf8d6d6da28cf3a80dc6ee9cdd6b83ae`
- Root tree: `f7d84d99379b68cd8960e8994d2353b9a09e6dc8`
- Successful workflow: [Spacetime Mathlib extension run #43215557270](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43215557270)
- Job: `mathlib-build-and-axiom-audit` (job ID `131173762344`) — success. The job steps and full log were inspected; the workflow checked out the exact commit above.
- **Evidence policy check — success.** Log: “Evidence policy check passed: ledger, Lean metadata, axiom audit, normative README boundary, and no placeholders/project axioms.”
- **Pinned Lean toolchain and dependency installation — success.** Lean `v4.19.0`; Mathlib revision `c44e0c8ee63ca166450922a373c7409c5d26b00b`; `leanprover/lean-action` pinned to `bd5cb0b830eda614ce3fc186d8429b9409b16c47`.
- **Lean/Mathlib build — success.** Log: `Build completed successfully.`
- **Axiom audit — success.** Log: `axiom-audit: audited 33 declaration(s) under 'QIKVRTSpacetimeBridgeMathlib'; all within the allowlist [propext, Classical.choice, Quot.sound].` The audit command completed successfully.
- The policy check, pinned build, and axiom audit all ran in the same job on this same exact commit. The three requested acceptance checks therefore pass together on `89653507bf8d6d6da28cf3a80dc6ee9cdd6b83ae`.

### Separate repository-wide CI status on this commit

- [QIKVRT CI run #43215557245](https://github.com/ingolf-lohmann/qik-vrt/actions/runs/43215557245) failed in job `test`. The full compile, launcher, protocol, handler, security, and TCP/IP tests passed, but `tools/qikvrt_integrity.py verify` reported: `BLOCK repository manifest differs from deterministic regeneration`.
- The log reports `added=["EVIDENCE_COMPLIANCE.md"]` and stale stored manifest records for `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1/QIKVRTSpacetimeBridgeMathlib/RealVolumeLaw.lean` and `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1/README.md`. The terminal tested-fixpoint disposition then failed. This is a separate repository-integrity issue, not one of the three Mathlib-extension checks; it is not represented as passing.
- **Scope of PASS:** only the controls and declarations under `formalization/QIKVRT_SpacetimeBridge_Mathlib_v1` exercised by this workflow. This does not establish repository-wide compliance.

The PASS designation is limited to the Mathlib extension. It does not prove empirical truth, universal ontology, complete physical-model validity, GitHub branch protection, or acceptance by third parties.


## Proof-preservation contract for autonomous execution and context transitions (2026-11-14)

**Purpose:** Preserve the exact logical obligations behind the Owner's completed
operational specification across ChatGPT context switches, repository writers,
CI runners, and native runtime restarts. This section is a proof-obligation
register, **not** a claim that the obligations below have been discharged by
the Lean kernel.

**Authority and scope:** `ingolf-lohmann/qik-vrt` only. The already established
Mathlib proof and axiom-audit evidence above remains scoped to its exact commit;
changing this document does not extend that proof to the new commit.

### Abstract transition system to formalize in Lean

Define a state `S` with a finite or otherwise well-founded set of persistent
work units, immutable evidence references, a repository exact HEAD/TREE,
exclusive writer identity and fencing epoch, admitted capabilities, durable
continuation receipts, effect receipts, and independent readback observations.
Define `Step : S → S → Prop`, `Crash : S → S → Prop`, and
`Recover : S → S → Prop` with explicitly specified atomicity and durability
assumptions. Separate **requested**, **prepared**, **executed**,
**independently acknowledged**, and **closed** states.

Required properties (formal statements must be fixed before proofs):

1. **Safety / no false completion.** For every reachable state and work unit,
   `Closed(w)` implies an admitted execution receipt, independently matched
   effect/readback evidence for the same work unit and exact version, and
   satisfied governance/CI/host gates. A stored instruction, issue, PR, or
   D1 observation alone cannot satisfy this implication.
2. **Single writer / fencing.** No two conflicting effects may be committed
   under the same admitted writer epoch; any stale or mismatched epoch is
   rejected. This requires an explicit atomic compare-and-swap or equivalent
   serialization assumption at the authoritative effect boundary.
3. **Crash-safe continuation.** For every durable active work unit, a crash
   followed by recovery reconstructs either its unique next idempotent step
   or an explicit blocked state with a recoverable dependency; a context
   switch cannot silently turn `Active` into `Closed`.
4. **Replay safety.** Re-execution of an admitted idempotency key cannot
   produce a second distinct externally visible effect. Distinguish
   at-least-once dispatch from exactly-once *effect* semantics; the latter
   requires downstream deduplication or transactional acknowledgment.
5. **Version binding.** An effect receipt for one HEAD/TREE, work-unit
   revision, or fencing epoch cannot discharge an obligation for another.
6. **Dependency and priority discipline.** A work unit is eligible only if
   its dependencies and writer gate are satisfied. P0 preempts P1–P4,
   except where a higher-priority unit is blocked; fair scheduling among
   eligible equal-priority units requires an explicit fairness assumption.
7. **Conditional progress.** Under stated assumptions of recurring scheduler
   activation, durable storage, eventually available admitted capabilities,
   and eventual completion of external dependencies, every continuously
   eligible work unit eventually progresses to a verified fixed point.
   **Unconditional liveness is not derivable** when CI approval, Site editor,
   original host, Mesh endpoint, or third-party acknowledgment is unavailable.

### Required refinement / traceability

For each property, retain a stable specification identifier, exact Lean
declaration path, theorem statement, imported axiom audit, toolchain and
dependency pin, Exact-HEAD/TREE, successful CI run and job IDs, executable
negative/crash-restart/replay tests, and a mapping to the concrete repository
and original-host state transitions. Mark any missing link **OPEN**.

A successful Lean kernel check proves only the encoded proposition relative
to its axioms and imports. Proving that the concrete Python, GitHub Actions,
REST, EMP and EAP implementation refines the Lean transition system requires
a separate, reviewable refinement argument and executable evidence. Neither
kernel acceptance nor a test suite by itself proves the whole production
system correct.

**Current disposition:** The seven obligations above are specified here as
proof targets; **no new Lean theorem, kernel acceptance, refinement proof,
repository-wide CI pass, deployment, or EFFECT_ACK_DONE is asserted** by this
documentation change. Preserve all earlier exact-commit evidence unchanged.
Regenerate repository integrity artifacts only using the canonical generator
after all tracked changes and cache coverage updates, then independently
verify the resulting exact HEAD.
