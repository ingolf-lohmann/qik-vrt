# QIK-VRT Spacetime Bridge — Mathlib extension v1

> **Repository evidence record:** [QIK-VRT Evidence Compliance Record](../../../EVIDENCE_COMPLIANCE.md). Consult this record for current verification status; a pending or failed CI run is not a pass.


## Evidence boundary (normative)

The Lean kernel checks formal derivations relative to the declarations and
axioms in the imported environment. A successful kernel check establishes the
formal theorem stated in the source, under those dependencies. It does not by
itself establish that the chosen model captures physical reality, that every
modeling assumption is empirically true, or that an ontological interpretation
is universally applicable.

This repository distinguishes four levels:
1. **Kernel-checked theorem:** a proposition with a proof accepted by Lean's
   kernel, relative to its imported environment and axioms.
2. **Formalized model statement:** a theorem about definitions and assumptions
   explicitly encoded in Lean. Its scope is exactly that formal model.
3. **Open formal obligation:** a mathematical or modeling step not yet proved
   in the package. It must not be described as established.
4. **Interpretive claim:** a philosophical, ontological, or empirical reading
   that is not a theorem merely because related mathematics has been checked.

This distinction is part of the project's technical contract. The inductive
EvidenceStatus metadata in RealVolumeLaw.lean makes the classification
machine-readable and is itself included in the kernel axiom audit. These
metadata labels classify project claims; they do not prove or disprove the
interpretive claim.

The phrase “monotone expansion” is not a Lean theorem in this package.
To make it one, a state space, an order relation, a transition/evolution
relation, and the exact monotonicity proposition must first be specified and
proved. A metaphorical description of an expanding evidence sphere must not
be presented as a proved dynamical law.

## Isolation boundary

This is a separate Lean package from QIKVRT_SpacetimeBridge_v1.
It pins Lean leanprover/lean4:v4.19.0 and Mathlib v4.19.0.
The existing Mathlib-free package and its successful CI evidence are not
changed or reinterpreted by this extension.

## Formalized here

- realVolumeDensity Ω d := Ω ^ d as the scalar real-valued density factor.
- Positivity of this factor for positive Ω.
- Injectivity of Ω ↦ Ω^d for positive real d and positive real Ω.
- A named local-density equality interface reusing the proved injectivity.

These are statements in the encoded scalar-real model. They do not establish
the unformalized geometric, measure-theoretic, physical, or ontological steps.

## Explicitly not formalized here

This package does not yet formalize the determinant identity for a smooth
Lorentzian metric, smoothness/pointwise density fields, Radon–Nikodym
uniqueness, or the passage from almost-everywhere equality to everywhere
equality. The scalar density definition is a separate formal step, not a
claim that those measure-theoretic obligations have been discharged.

Poisson PMF normalization, factorial moments, expectation, variance,
Chebyshev bounds, and sprinkling convergence are subsequent milestones.
They must be proved from Mathlib probability/measure APIs without project
axioms or placeholders; no such result is claimed here.

## Verification

Run from this directory:

    lake update
    lake exe cache get
    lake build

The dedicated exact-head GitHub Actions run #43000271891 succeeded on commit
55c3b3f8f4031b989776d76057bda551d113a999: lake build passed and the
kernel axiom audit checked the scalar real-power and density declarations,
each within the foundational allowlist (propext, Classical.choice,
Quot.sound). This verifies those formal results only. The smooth-metric
determinant identity, Radon–Nikodym steps, Poisson moments, and continuum
convergence remain open. The PR remains a draft pending review.
