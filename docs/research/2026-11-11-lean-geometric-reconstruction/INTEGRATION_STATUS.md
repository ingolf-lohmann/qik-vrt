# Causal geometry integration — implementation and process audit

Date: 2026-11-11

## Current implementation

The first implementation tranche is proposed in PR #740 as a separate
dependent Lean package:

- Package: `formalization/QIKVRT_CausalGeometry_v1`
- Entry point: `QIKVRTCausalGeometry.lean`
- Geometry module: `QIKVRTCausalGeometry/CausalGeometry.lean`
- Axiom inventory: `QIKVRTCausalGeometry/AxiomAudit.lean`
- Dependency: the existing `QIKVRT_Formalization_v2.0` package, specifically
  its established `QIKVRTEffectAck.CausalDistance` module.

The original EFFECT_ACK entry point is restored byte-for-byte to its
historically bound Git blob
`3ba05628fd377a54f71936d4bc6bfc1b969a5695`. The original Lake project,
CausalDistance source and historical kernel receipts are not rewritten.

An earlier iteration imported the new module directly into the old EFFECT_ACK
entry point. Although its Lean build and 13-theorem axiom audit succeeded, the
repository-wide historical CausalDistance verifier correctly rejected the
changed entry-point hash. That iteration is superseded. The current separate
package preserves the old source boundary while depending on the same checked
core module.

Exact-head verification of the separate-package layout succeeded on commit
`a0b858c664c22639be4e355855e223e28ccdd9df`, dedicated workflow run
`42996066793` (QIK-VRT causal geometry integration, run #36):
- dependent package build: success;
- source registration and historical entry-point byte-lock: success;
- `hasSorry` check: success;
- axiom audit: 13 theorem declarations, foundational axioms only, no
  project-defined axioms.

The PR remains draft and is not merged into main. CI success is not human
mathematical review, merge authorization, publication, or physical validation.

## Why the work did not happen automatically before

The repository inspection identified four separate boundaries:

1. PR #739 changed only a document under
   `docs/research/2026-11-11-lean-geometric-reconstruction/`. The existing
   manuscript proof workflow's path filters covered the formalization tree and
   selected publication directories, but not this research directory. The
   research-only PR therefore did not invoke that Lean build workflow.
2. The VRTCore relational-causality candidate is preserved under
   `docs/publications/2026-08-02-causality-is-relation-vrtcore/`. Its
   publication workflow compiles it through a separate LEAN_PATH invocation;
   it is not a module imported by the EFFECT_ACK Lake library root.
3. The weighted graph/path distance module already was part of the EFFECT_ACK
   library. Its successful kernel receipt covered its own declared theorem
   inventory, not the additional event-order, Round-Trip, or spacetime claims
   described later in a research proposal.
4. No process can safely translate a prose research plan into mathematical
   definitions and proofs without explicit design decisions. CI can build and
   audit encoded Lean declarations; it cannot infer the intended theorem,
   choose its hypotheses, or establish empirical correspondence from prose.

The mismatch was therefore a workflow/registration gap plus an expectation
that a research proposal would itself trigger implementation. It was not
evidence that the Lean kernel had silently omitted already-encoded theorems.

## Preventive control

The new workflow watches the research specification and the dependent package
source paths. Its registration verifier checks the exact theorem inventory,
the matching axiom audit, the import of CausalDistance, the local Lake
dependency, the pinned Lean version, and the unchanged historical EFFECT_ACK
entry-point blob. The workflow builds the dependent package, rejects proof
escapes and checks the axiom inventory on the exact PR head.

A research-only change in this scoped workstream now invokes the geometry gate,
and it cannot pass if the dependent Lean package or its source/audit
registration is absent. The guard also blocks future edits that silently
change the hash-locked original EFFECT_ACK entry point.

The control verifies source registration and CI execution. It does not
automatically author proofs, choose physical assumptions, or promote physical
claims. Future geometry work must still be encoded, reviewed and kernel-checked.

## Formal scope proposed in the implementation tranche

- strict precedence from positive directed paths;
- transitivity without assuming a total order;
- irreflexivity and asymmetry under explicit graph acyclicity;
- a local-finiteness interface with finite interval witnesses;
- Round-Trip left inverse and canonical right inverse;
- injectivity of encoding;
- preservation and reflection of a typed relation;
- an empty-graph countermodel for total-order assumptions.

Still open: a cited and precisely hypothesized causal-order reconstruction
theorem, volume-scale reconstruction, discrete-to-continuum convergence,
Lorentzian metric and null-cone correspondence, and physical/empirical
binding. No claim in this file promotes those open obligations.
