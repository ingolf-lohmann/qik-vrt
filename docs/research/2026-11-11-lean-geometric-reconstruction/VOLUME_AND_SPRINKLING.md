# Volume law and Poisson sprinkling — analytic specification

Status: an exact discrete scale-identifiability lemma and a reproducible numerical sprinkling reference implementation have been added. The continuum measure-theoretic formalization and stochastic convergence theorem remain open.

## 1. Continuum conformal volume law

Let (M,g) be a d-dimensional Lorentzian manifold and let g' = Ω²g for a smooth, strictly positive function Ω:M→(0,∞). In local coordinates,

[
det(g')=det(Omega^2g)=Omega^{2d}det(g),
qquad
sqrt{|det(g')|}=Omega^dsqrt{|det(g)|}.
]

Consequently dVol(g') = Ω^d dVol(g). This is a local density law, not merely an equality of total volumes for one region.

If the two volume measures agree on every measurable subset, uniqueness of Radon–Nikodym densities implies Ω^d=1 almost everywhere. Since Ω is continuous and strictly positive and d≥1, Ω=1 everywhere. If the measures are known only on a restricted family of regions, that family must determine the measure (for example, a generating π-system under standard finiteness assumptions). Equality of one global integral is insufficient.

Thus a fully calibrated local volume measure removes the positive conformal-scale ambiguity, subject to the regularity and domain assumptions above.

### Lean status

The module QIKVRT.SpacetimeBridge.V1.VolumeLaw proves in Lean's kernel the injectivity of Ω ↦ Ω^d for natural-number-valued Ω and d>0, the unit-factor result, and cancellation of a positive integer calibration density. This is an exact arithmetic lemma. It is NOT a formalization over positive real-valued smooth functions, determinants, or Radon–Nikodym derivatives. The continuum formula above is a standard coordinate-algebra and measure-theory argument, not a claim that this Lean module formalizes differential geometry.

## 2. Poisson sprinkling model

Use 1+1-dimensional Minkowski spacetime with null coordinates u=t−x and v=t+x. The Alexandrov diamond 0≤u≤L, 0≤v≤L has spacetime volume V=L²/2. Set L=√2, so V=1. A homogeneous Poisson sprinkling of density ρ has

[
Pr[N=n]=e^{-ho}rac{ho^n}{n!},quad n=0,1,2,ldots,
qquad mathbb E[N]=ho,quad operatorname{Var}(N)=ho.
]

Conditional on N=n, the n events are independent and uniform in the null-coordinate square [0,√2]². The induced strict causal order is

[
(u_i,v_i)prec(u_j,v_j)
iff u_ile u_j, v_ile v_j, (u_i,v_i)
e(u_j,v_j).
]

The order is irreflexive and transitive; coordinate coincidences have probability zero under the continuous sampling measure. Every finite realization is therefore a finite causal set almost surely.

## 3. Statistical error, not exact equality

For a region of volume V, N/ρ is an unbiased estimator of V. Its relative standard deviation is 1/√(ρV). Chebyshev's inequality yields

[
Pr!left(|N-ho V|geepsilonho Vight)
le min!left(1,rac{1}{epsilon^2ho V}ight).
]

For disjoint regions, Poisson counts are independent. This bound is conservative; sharper Poisson Chernoff bounds exist. A high-density limit must specify the observables and whether convergence is in probability, almost surely, or in distribution. Concentration for one fixed region does not by itself prove convergence of reconstructed metric, curvature, or topology.

## 4. Executable reference experiment

The script tools/causal_sprinkling_demo.py implements inverse-CDF Poisson sampling (rate restricted to 0<ρ≤100 for floating-point stability), uniform sprinkling into the unit-volume 1+1D diamond, induced causal relations, and sample mean/variance/tail diagnostics. It checks strict partial-order properties on the first generated sprinkle.

Run:

```bash
python3 tools/causal_sprinkling_demo.py --density 20 --trials 2000 --epsilon 0.25 --seed 20261111
python3 -m unittest discover -s tools -p 'test_causal_sprinkling_demo.py'
```

This is a reproducible numerical sanity check. It is not a formal proof, a test of Lorentz invariance in arbitrary dimension, or evidence that generic causal sets are manifold-like.

## 5. What remains open

1. Formalize the continuum determinant identity and positive-real power injectivity in a suitable Lean library (for example Mathlib's real analysis and multilinear algebra), including smoothness and measure-theoretic hypotheses.
2. Formalize the Poisson PMF normalization, first and second factorial moments, and Chebyshev bound in a probability library.
3. Establish a stated convergence theorem for observables on sprinkled causal diamonds; control boundary effects and discretization scale.
4. Show that QIK-VRT graph semantics map to the causal relation of the target continuum model. The simulator starts from Minkowski spacetime and does not derive that correspondence from QIK-VRT.
5. Test curved spacetimes, dimensions beyond 1+1, and dimension/curvature estimators with error bars and preregistered acceptance criteria.

## 6. References

- F. Dowker, “Causal sets and an emerging continuum,” General Relativity and Gravitation 56, 95 (2024). https://doi.org/10.1007/s10714-024-03281-1
- S. Surya, “The causal set approach to quantum gravity,” Living Reviews in Relativity 22, 5 (2019). https://doi.org/10.1007/s41114-019-0023-1
- L. Bombelli, J. Lee, D. Meyer, R. Sorkin, “Space-time as a causal set,” Physical Review Letters 59, 521 (1987). https://doi.org/10.1103/PhysRevLett.59.521
