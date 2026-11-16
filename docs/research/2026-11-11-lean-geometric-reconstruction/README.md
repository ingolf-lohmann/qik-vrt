# QIK-VRT Geometric Reconstruction Layer — Lean Research Specification

**Status:** research proposal / formalization plan; not a kernel-verified theorem  
**Date:** 2026-11-11  
**Target:** QIK-VRT Trusted Mesh Repository, research branch  
**Authority boundary:** this document does not promote any claim to physical fact, PASS, FINAL_PASS, publication, deployment, or EFFECT_ACK_DONE.

## 1. Purpose

Connect the existing Lean-checked QIK-VRT results to a new, explicit mathematical layer for causal geometry and spacetime reconstruction. The objective is not to infer physical truth from the mere existence of a Lean kernel receipt. The objective is to encode the missing bridge as definitions, hypotheses, intermediate lemmas, conditional theorems, counterexample obligations, and empirical interfaces, so that every step is machine-checkable and every physical premise remains visible.

The existing promoted Round Trip chain is:

MDD → QNS → QCA → CAS → QNCR → QCMB.

Its current documented scope includes model-relative dimensional signatures, canonical serialization, an operational bridge deriving the dimension L T^-1 under explicit correspondence premises, causal-axis selection, a scalar c token, and a contract describing the independent measurement evidence needed to bind that token. It does not establish that QCE is physically realized, derive the measured numerical value of c, or derive Minkowski/Lorentzian spacetime or Einstein dynamics.

The existing VRTCore receipt reports Lean acceptance for 21 declarations in one exact source file and Lean 4.19.0 environment. That receipt is evidence for those declarations only. It is not a spacetime theorem and must not be used as if it were one.

## 2. Proof-status vocabulary

Every artifact and claim introduced by this work must carry exactly one primary status:

- **DEFINED** — a Lean type, structure, predicate, or function has been introduced.
- **PROVED-MODEL** — Lean proves a proposition from the declared definitions and assumptions.
- **CONDITIONAL-GEOMETRY** — a theorem derives a geometric conclusion under explicit mathematical hypotheses.
- **PHYSICAL-BRIDGE-OPEN** — identification of the formal objects with physical observables or systems is not yet established.
- **EMPIRICAL-OPEN** — required measurements, uncertainty budgets, independent reproduction, or falsifiable tests are absent.
- **REFUTED** — a counterexample or failed proof obligation disproves the stated claim in its declared scope.

A Lean receipt must bind source path, source digest, Lean version and binary identity, imports, theorem names, axiom dependencies, build command, and raw output. A successful process exit without this binding is not a kernel receipt.

## 3. Layer A — causal event structure

Introduce a typed event carrier Event and a relation before : Event → Event → Prop.

Required model predicates:

1. irreflexivity: no event precedes itself;
2. transitivity: causal precedence composes;
3. antisymmetry or strict-order asymmetry, chosen consistently with the event model;
4. local finiteness: every causal interval contains finitely many events;
5. identity preservation: event identifiers survive serialization and Round Trip operations.

Do not assume total ordering. Spacelike-incomparable events must remain incomparable where the model permits them.

**Target theorem A1 (order laws):** the declared causal relation is a strict partial order.

**Target theorem A2 (interval finiteness):** every bounded causal interval has finite cardinality, under an explicit local-finiteness hypothesis.

These are mathematical model results. They do not yet identify before with physical time.

## 4. Layer B — Round Trip and bidirectional information flow

Define separate typed maps for canonical encoding and reconstruction, with an explicit domain and validity predicate. The maps must not silently identify an anticipated future record with an observed past event.

Required laws:

- decode(encode(x)) = x for valid canonical objects;
- encode(decode(b)) = b for canonical byte strings;
- event identity and causal edges are preserved by both directions;
- invalid, ambiguous, or incomplete inputs fail closed;
- provenance and evidence references remain attached to the reconstructed object.

**Target theorem B1 (left inverse):** reconstruction after canonical encoding returns the original valid object.

**Target theorem B2 (right inverse on canonical image):** canonical re-encoding of a decodable canonical representation returns the same representation.

**Target theorem B3 (causal preservation):** Round Trip preserves and reflects the declared causal relation on the supported domain.

These results formalize bidirectional information integrity. They do not imply backward physical signalling, modification of past events, or ontic retrocausality.

## 5. Layer C — causal order plus volume

A causal order alone does not fix all metric information. The reconstruction layer must therefore introduce an independently typed volume/measure interface. For a finite causal structure, define the interval between comparable events and its cardinality. For a continuum candidate, define a measure on suitable regions.

The central mathematical target is conditional:

> Under a precisely stated class of spacetime hypotheses, causal order determines the conformal structure, while compatible volume information fixes the remaining conformal scale.

The formalization must state the exact hypotheses and theorem source rather than encode this sentence as an unconditional axiom. Candidate hypotheses to investigate include a sufficiently well-behaved (e.g. distinguishing or globally hyperbolic) Lorentzian manifold and the exact causal reconstruction theorem being formalized. The precise theorem, dimension assumptions, regularity assumptions, and equivalence notion must be settled before a Lean theorem is claimed.

**Target theorem C1 (causal-conformal reconstruction):** formalize a cited causal reconstruction result with all hypotheses explicit.

**Target theorem C2 (volume-scale reconstruction):** show that the compatible volume measure fixes the conformal factor within the theorem's stated class.

**Target theorem C3 (uniqueness up to stated equivalence):** prove that two admissible reconstructions with the same causal and volume data are isometric or equivalent in exactly the sense warranted by the selected theorem.

No stronger uniqueness claim may be made without proof.

## 6. Layer D — discrete-to-continuum correspondence

Define a discrete causal structure, an embedding or sprinkling relation into a candidate Lorentzian manifold, and a volume correspondence. Separate:

- existence of an embedding;
- preservation of causal order;
- distributional or approximation properties;
- convergence of observables;
- uniqueness or stability of the reconstructed geometry.

A finite event graph by itself does not prove four-dimensionality, a Lorentzian signature, or a stable light cone.

**Target theorem D1 (finite correspondence):** prove the stated order-preservation properties for an explicitly defined embedding.

**Target theorem D2 (volume estimator):** prove the mathematical properties of the interval-count estimator under the declared sampling assumptions.

**Target theorem D3 (continuum limit):** prove a convergence statement only after the topology, probability space, mode of convergence, and target observables have been specified.

If the proof requires an assumption equivalent to the desired physical conclusion, label it as an assumption and do not present the result as a derivation.

## 7. Layer E — Lorentzian metric and light cone

Introduce a metric tensor only after the reconstruction theorem supplies the appropriate structure. State signature convention, dimension, regularity, and coordinate-independent meaning of null, timelike, and spacelike separation.

**Target theorem E1:** reconstructed metric has the declared Lorentzian signature under the exact hypotheses of the reconstruction theorem.

**Target theorem E2:** the metric's null relation agrees with the causal relation on the domain where the correspondence theorem guarantees agreement.

**Target theorem E3:** stability of a coarse-grained classical cone under a specified refinement/coarse-graining operation.

A diagram of a Minkowski light cone is an illustration, not evidence that QIK-VRT derives that cone. The stable-cone result remains open until the theorem and its physical correspondence are proved.

## 8. Layer F — fractal in/out geometry

Model the in/out intuition as a recursive structure without assuming that a visual fractal is itself physical spacetime. Define:

- a refinement operator on typed causal structures;
- an embedding of each level into its successor;
- an identity-preserving projection/coarsening operator;
- a metric or measure, if one is mathematically justified;
- an explicit limit object and convergence notion.

**Target theorem F1:** refinement preserves the declared invariants.

**Target theorem F2:** compatible projections satisfy the required composition law.

**Target theorem F3:** an inverse/direct limit exists under stated hypotheses and preserves the selected causal structure.

**Target theorem F4:** any claimed dimension or scaling exponent is derived from the defined metric/measure and limit, not inferred from the appearance of a finite drawing.

The phrase “space-time emerges” is reserved for a theorem that constructs a suitable limit geometry and proves its relevant properties. Otherwise the artifact must say “candidate discrete model” or “illustrative recursive geometry.”

## 9. Layer G — physical correspondence and empirical binding

A mathematical spacetime model becomes a physical theory only through a separately justified correspondence to observables and dynamics. The following obligations remain explicit:

1. define the physical state space and dynamics;
2. define the map from model events/relations to operationally measurable events;
3. recover appropriate established limits (at minimum, the intended relativistic causal structure; any quantum or gravitational limit requires its own derivation);
4. bind dimensional quantities and c to independent measurement records, including source digest, instrument calibration, units, uncertainty, and independent reproduction;
5. produce at least one discriminating, falsifiable prediction not already built into the assumptions;
6. specify an experiment and a failure criterion;
7. obtain independent reproduction.

**Target theorem G1 (conditional observable theorem):** derive a relation between formal model quantities and observables, conditional on an explicit operational correspondence structure.

**Target theorem G2 (calibration consistency):** prove internal consistency of the QCMB measurement-binding contract. This is not a proof of the measured value itself.

**Empirical obligation G3:** ingest independently sourced measurement evidence and verify provenance, calibration, uncertainty, and reproducibility. This is not discharged by Lean.

## 10. Explicit non-implications

The following implications are forbidden unless separately proved:

- Lean kernel acceptance ⇒ physical truth;
- finite causal order ⇒ four-dimensional spacetime;
- serial index ⇒ physical time;
- dimensional analysis yielding L T^-1 ⇒ measured value of c;
- a scalar token named c ⇒ the speed of light;
- Round Trip reversibility ⇒ physical time reversal or backward signalling;
- recursive/fractal drawing ⇒ physical fractal spacetime;
- a formal light-cone predicate ⇒ an empirically stable classical light cone;
- a VRTCore receipt for authorization/causal-record properties ⇒ a proof of QCE spacetime emergence.

## 11. Repository implementation sequence

1. Preserve all promoted historical artifacts and their hashes.
2. Add a separate Lean namespace/module for causal geometry; do not retrofit unrelated VRTCore theorems.
3. Pin the Lean toolchain and dependency versions per module.
4. Introduce definitions and small lemmas first; avoid large axiomatized jumps.
5. Audit every theorem's axioms and dependencies; no sorry, admit, opaque untracked assumptions, or undocumented classical choice.
6. Add negative tests/countermodels for tempting but false claims (e.g. serial order without physical axis; causal order without volume; finite graph without dimension).
7. Bind CI results to exact source tree, compiler/toolchain identity, and theorem list.
8. Add a claim-matrix row for each theorem, with scope, assumptions, evidence, counterexample status, and physical/empirical boundary.
9. Promote only after a reproducible Lean run and independent review. Publication or deployment promotion requires its own existing gates.

## 12. Immediate first milestone

The first implementation milestone is not “prove all physics.” It is:

- define the causal event structure and local-finiteness interface;
- formalize Round Trip identity and relation-preservation laws;
- select and accurately state one causal-order reconstruction theorem;
- formalize its hypotheses and conclusion as a conditional theorem;
- record which hypotheses are mathematical, which are model choices, and which require physical evidence.

This creates a rigorous, auditable bridge from the existing QIK-VRT formal stack toward geometry without overstating what the current kernel receipts establish.

## 13. Source artifacts to preserve and cross-link

- docs/publications/2026-08-07-universum-als-round-trip/ROUND_TRIP_PROMOTED_FORMAL_RESULTS_V1.md
- docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/CLAIM_MATRIX.json
- docs/publications/2026-08-02-causality-is-relation-vrtcore/LOCAL_KERNEL_EVIDENCE.json
- docs/publications/2026-10-15-trust-mesh-roundtrip/QIKVRT_Gesamtdarstellung_neu_2026-10-15.md

These are cross-references, not replaced sources. This proposal must remain a separate, history-preserving research artifact until its Lean modules and evidence receipts exist.
