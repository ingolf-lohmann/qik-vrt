# Volume law and Poisson sprinkling — analytic specification

## Continuum conformal volume law

Let (M,g) be a d-dimensional Lorentzian manifold and g'=Ω²g for smooth Ω:M→(0,∞). In local coordinates,

[
det(g')=Omega^{2d}det(g),qquad
sqrt{|det(g')|}=Omega^dsqrt{|det(g)|},
]
so dVol(g')=Ω^d dVol(g).

If the two measures agree on every measurable subset, uniqueness of Radon–Nikodym densities gives Ω^d=1 almost everywhere. Continuity and strict positivity of Ω, together with d≥1, upgrade this to Ω=1 everywhere. Equality of one total volume is not enough; the measured regions must determine the local measure.

### Lean scope

The Lean module QIKVRT.SpacetimeBridge.V1.VolumeLaw proves injectivity of Ω↦Ω^d for natural-number scales and positive integer dimension, plus unit-scale recovery and cancellation of a positive integer calibration count. It does not formalize positive-real smooth functions, determinants, or Radon–Nikodym derivatives. This is an exact arithmetic lemma, not a formal differential-geometric proof.

## Poisson sprinkling

In 1+1D Minkowski spacetime, use null coordinates u=t−x and v=t+x. The Alexandrov diamond 0≤u,v≤L has spacetime volume V=L²/2. Choosing L=√2 gives V=1. A homogeneous Poisson sprinkling of density ρ has

[
P(N=n)=e^{-ho}rac{ho^n}{n!},quad n=0,1,ldots.
]

The moments follow from the first two factorial moments:
[
egin{aligned}
E[N]&=e^{-ho}sum_{nge1}nrac{ho^n}{n!}
=ho e^{-ho}sum_{mge0}rac{ho^m}{m!}=ho,\
E[N(N-1)]&=e^{-ho}sum_{nge2}n(n-1)rac{ho^n}{n!}
=ho^2 e^{-ho}sum_{mge0}rac{ho^m}{m!}=ho^2,\
Var(N)&=E[N(N-1)]+E[N]-E[N]^2=ho.
end{aligned}
]

Conditional on N=n, events are iid uniform in [0,√2]² in null coordinates. The induced order is
[
(u_i,v_i)prec(u_j,v_j)iff u_ile u_j, v_ile v_j, (u_i,v_i)
e(u_j,v_j).
]
It is a strict partial order almost surely (coordinate coincidences have probability zero).

## Statistical accuracy

N/ρ is an unbiased estimator of V, with relative standard deviation 1/√(ρV). Chebyshev gives
[
P(|N-ho V|geepsilonho V)lemin(1,1/(epsilon^2ho V)).
]
This is a finite-density bound, not an exact count-volume identity. A continuum limit must specify observables and convergence mode; concentration for one region does not prove metric, curvature, or topology convergence.

## Executable reference experiment

tools/causal_sprinkling_demo.py implements inverse-CDF Poisson sampling (0<ρ≤100 for floating-point stability), unit-volume diamond sprinkling, induced causal order, and empirical mean/variance/tail diagnostics. It is a numerical reference model only, not a proof of manifold-likeness or continuum convergence.

Run:
```bash
python3 tools/causal_sprinkling_demo.py --density 20 --trials 2000 --epsilon 0.25 --seed 20261111
python3 -m unittest discover -s tools -p 'test_causal_sprinkling_demo.py'
```

## Open obligations

1. Formalize the continuum determinant identity and positive-real power injectivity with a suitable Lean real-analysis/multilinear-algebra library.
2. Formalize the Poisson PMF normalization, factorial moments, and Chebyshev bound in a probability library.
3. Prove convergence for specified observables on sprinkled diamonds, including boundary and discretization errors.
4. Derive the QIK-VRT-to-continuum causal correspondence rather than assuming a Minkowski background.
5. Test curved spacetimes, dimensions beyond 1+1, and dimension/curvature estimators with preregistered error criteria.

## References

- F. Dowker, “Causal sets and an emerging continuum,” GRG 56, 95 (2024), https://doi.org/10.1007/s10714-024-03281-1
- S. Surya, “The causal set approach to quantum gravity,” Living Reviews in Relativity 22, 5 (2019), https://doi.org/10.1007/s41114-019-0023-1
- L. Bombelli, J. Lee, D. Meyer, R. Sorkin, “Space-time as a causal set,” PRL 59, 521 (1987), https://doi.org/10.1103/PhysRevLett.59.521
