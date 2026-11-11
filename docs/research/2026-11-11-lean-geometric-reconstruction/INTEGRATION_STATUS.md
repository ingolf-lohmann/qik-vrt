# Causal geometry integration — implementation and process audit

Date: 2026-11-11

## Result

The first implementation tranche is proposed in PR #740:

- `QIKVRTEffectAck.CausalGeometry` is imported by the existing EFFECT_ACK
  library root.
- Its axiom inventory is explicit in
  `QIKVRTEffectAck/CausalGeometryAxiomAudit.lean`.
- `tools/verify_causal_geometry_registration.py` checks that declarations,
  axiom-audit entries and root imports remain synchronized.
- `.github/workflows/qikvrt_causal_geometry_integration.yml` runs on changes
  to the research specification as well as the formal Lean source, builds the
  integrated library, rejects proof escapes and checks the exact theorem
  inventory and allowed foundational axioms.

This is a proposal pending CI and review. It is not yet a kernel-verified
receipt and is not merged into main.

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

The new workflow watches both the research specification and the formalization
source paths. Its registration verifier fails closed if the geometry module,
the root imports, the theorem inventory or the axiom audit are missing or
diverge. A research-only change in this scoped workstream can no longer pass
the geometry gate as if the corresponding Lean integration existed.

The control verifies source registration and CI execution. It does not
automatically author proofs, choose physical assumptions, or promote physical
claims. Future geometry work must still be encoded, reviewed and kernel-checked.

## Formal scope now covered by the implementation tranche

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
