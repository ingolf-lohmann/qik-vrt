# QIK-VRT Spacetime Bridge — Mathlib extension v1

## Isolation boundary

This is a separate Lean package from `QIKVRT_SpacetimeBridge_v1`.
It pins Lean `leanprover/lean4:v4.19.0` and Mathlib `v4.19.0`.
The existing Mathlib-free package and its successful CI evidence are not
changed or reinterpreted by this extension.

## Formalized here

- `realVolumeDensity Ω d := Ω ^ d` as the scalar real-valued density factor.
- Positivity of this factor for positive Ω.
- Injectivity of Ω ↦ Ω^d for positive real d and positive real Ω.
- A named local-density equality interface reusing the proved injectivity.

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

```bash
lake update
lake exe cache get
lake build
```

The dedicated GitHub Actions workflow runs the package build and kernel axiom
audit on the exact pull-request head. Until that exact workflow succeeds,
this extension is an unverified draft.
