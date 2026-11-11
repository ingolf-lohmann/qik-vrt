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

Poisson normalization and the first two real-valued raw moments are now
formalized in `PoissonMoments.lean`: the weighted-series expectation is
`r`, the second raw moment is `r^2 + r`, and the variance computed from
these raw moments is `r`. The exact-head CI status is tracked in PR #744.
A full random-variable model, Chebyshev bounds, and sprinkling convergence
remain subsequent milestones.

## Verification

Run from this directory:

```bash
lake update
lake exe cache get
lake build
```

The dedicated exact-head GitHub Actions run #43000271891 succeeded on commit
`55c3b3f8f4031b989776d76057bda551d113a999`: `lake build` passed and the
kernel axiom audit checked all four package declarations, each within the
foundational allowlist (`propext`, `Classical.choice`, `Quot.sound`). This
verifies the scalar real-power and density results only. The smooth-metric
determinant identity, Radon–Nikodym steps, Poisson moments, and continuum
convergence remain open. The PR remains a draft pending review.
