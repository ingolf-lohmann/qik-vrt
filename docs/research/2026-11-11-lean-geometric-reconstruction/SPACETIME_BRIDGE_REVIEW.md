# Causal order, volume, continuum and empirical bridge — review dossier

Status: formal interface added; physical reconstruction and empirical validation remain open.
Scope: conditional reconstruction only. This is not a claim that QIK-VRT has derived general relativity.

## 1. What is established mathematically

The existing geometry package derives a strict partial order from positive directed paths under an explicit acyclicity hypothesis. Local finiteness is supplied as a finite-interval witness. Round-Trip laws establish information preservation only for the stated canonical domain.

The new package QIKVRT_SpacetimeBridge_v1 proves a compositional uniqueness result:

1. a continuum causal-isomorphism premise identifies the conformal class;
2. equality of the full region-volume signature, at fixed conformal class, identifies the remaining scale;
3. conformal class plus scale identifies the metric in the chosen model class.

The Lean theorem causal_volume_reconstruct composes these three implications. It does not prove any of the three geometric/physical premises from the QIK-VRT graph. Those premises are explicit fields of CausalVolumeReconstruction.

## 2. Continuum causal reconstruction: correct theorem boundary

The relevant HKM/Malament family of results concerns Lorentzian spacetimes, not arbitrary directed graphs. A representative statement is that a causal/chronological isomorphism between sufficiently regular, future- and past-distinguishing spacetimes in dimension greater than two determines a conformal isometry. The causal order therefore determines the conformal geometry under those hypotheses, not the absolute metric scale.

Required hypotheses must be checked on both spacetimes:
- Lorentzian manifold structure and compatible time orientation;
- dimension greater than two;
- future distinction and past distinction (or a theorem-specific stronger condition);
- a bijective causal/chronological order isomorphism, not merely a graph homomorphism or preservation in one direction.

The exact version and regularity assumptions must be pinned to the cited theorem before replacing the abstract Lean premise with a concrete formalization. A graph path relation does not by itself supply a manifold, differentiable structure, causal curves, or the hypotheses of HKM/Malament.

## 3. Volume is not one scalar

The scale datum must be a volume measure on the relevant measurable regions (or an equivalent local volume density), not merely the total volume of the whole universe or one interval count. In a conformal class, the Lorentzian volume density changes with the conformal factor; equality of the full volume signature is what can fix that factor when the measure and regularity assumptions are appropriate.

For a d-dimensional metric transformation g' = Ω²g, the volume density transforms by Ω^d. Recovering Ω from volume therefore requires:
- d known and positive;
- Ω positive;
- a specified measure on the same measurable regions;
- equality/identifiability of the local density, not just an aggregate;
- compatible units and calibration.

The current Lean interface deliberately abstracts this as sameVolumeSignature and volumeDeterminesScale. A future analytic module should instantiate the density law and prove injectivity of Ω ↦ Ω^d for Ω > 0, rather than adding it as an undocumented axiom.

## 4. Discrete-to-continuum bridge

For a causal-set-style discretization, the candidate construction is:
1. choose a Lorentzian spacetime and its volume measure;
2. Poisson-sprinkle events at density ρ;
3. inherit the continuum causal order on sprinkled points;
4. identify finite order intervals and their cardinalities;
5. compare cardinality/ρ with continuum interval volumes;
6. establish convergence in a stated topology/probability mode as density grows.

This is a sampling model, not a deterministic consequence of local finiteness. A finite locally finite poset need not be manifold-like. Most finite posets do not approximate a physically reasonable continuum. The continuum-limit claim therefore needs a specified random process, probability space, observables, convergence mode, and error bounds. It must also state how dimension and curvature estimators behave and at what scales they are reliable.

No convergence theorem is claimed in the present Lean package. The missing theorem is a probability/measure-theoretic result, not something that can be filled by asserting that finite cardinality equals continuum volume.

## 5. Physical and empirical bridge

The physical interpretation needs an operational map from QIK-VRT events/edges to measurable events and causal influence. It must specify:
- what constitutes an event and an edge in an experiment;
- how direction is assigned without assuming the conclusion;
- how timestamps, clock synchronization, detector latency and uncertainty are handled;
- which observables are predicted, with units and calibration;
- which existing theory is the null/baseline model;
- a preregistered discrepancy statistic, tolerance and rejection rule;
- independent replication and controls for selection effects.

The Lean EmpiricalTest type captures only the software-level prediction/discrepancy/threshold interface. It proves no experiment has passed, and no physical data are currently certified by this package. A test is falsifiable only when predictions and thresholds are fixed before inspecting the relevant outcomes.

## 6. Required next formal milestones

| Milestone | Required proof/evidence | Current state |
|---|---|---|
| Graph order | transitivity; acyclicity for irreflexivity | formalized |
| Local finiteness | explicit finite interval witness | interface formalized |
| Continuum causal theorem | instantiate HKM/Malament with all hypotheses | open |
| Volume scale | local density law and positive-factor injectivity | interface only |
| Discrete limit | Poisson process + convergence theorem + error bounds | open |
| Lorentzian signature | derive or independently justify signature (−,+,…,+) | open |
| Physical bridge | operational event/edge map and calibration | open |
| Empirical validation | preregistered tests, raw data, uncertainty, replication | open |

## 7. Scientific references

- S. W. Hawking, A. R. King, P. J. McCarthy (1976), “A new topology for curved space-time which incorporates the causal, differential, and conformal structures,” Journal of Mathematical Physics. https://doi.org/10.1063/1.522874
- D. B. Malament (1977), “The class of continuous timelike curves determines the topology of spacetime,” Journal of Mathematical Physics 18, 1399–1404. https://doi.org/10.1063/1.523436
- L. Bombelli, J. Lee, D. Meyer, R. Sorkin (1987), “Space-time as a causal set,” Physical Review Letters 59, 521–524. https://doi.org/10.1103/PhysRevLett.59.521
- F. Dowker (2013), “Introduction to causal sets and their phenomenology,” General Relativity and Gravitation 45, 1651–1667. https://doi.org/10.1007/s10714-013-1569-y
- S. Carlip (2024), “Causal sets and an emerging continuum,” General Relativity and Gravitation 56, 95. https://doi.org/10.1007/s10714-024-03281-1

## 8. Review rule

A CI pass certifies only that the checked Lean source compiles and that the audited declarations use no unapproved project axioms. It is not a peer review, a proof of the external geometric premises, a validation of the QIK-VRT physical interpretation, or empirical confirmation.
