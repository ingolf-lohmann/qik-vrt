# C90 independent proof kernel — acceptance boundary

This module is a **new proof checker**, not a Lean replacement. It must not be described as proving arbitrary Lean theorems. A checker verifies a supplied proof certificate; proof search is a separate, untrusted producer.

## Mandatory architecture

1. Pin every source file and proof certificate by SHA-256 in the CI evidence.
2. Export the *same exact Lean proposition* to a documented, lossless intermediate representation (IR), including universe levels, dependent types, inductive definitions, equality, reductions, and trusted constants. Reject unsupported constructs; never approximate.
3. Implement a C90 proof certificate checker that independently validates every IR inference step. Never accept a theorem because another checker accepted it.
4. Bind each C90 result to the Lean declaration name, exact expression and full transitive dependency closure. Explicitly enumerate permitted axioms.
5. Run Lean default, Lean paranoid, lean4lean, nanoda, con-leche and con-ron on the exact same source. Independently run the C90 checker on the corresponding losslessly exported theorem. A C90 PASS is not comparable until equivalence of export is established.
6. Supply negative controls (mutated propositions, proof terms, missing dependencies and forged acknowledgements). A checker that accepts a negative control fails the gate.
7. Make the whole pipeline reproducible on an exact Git commit/tree; persist logs and artifact hashes. CI PASS is distinct from deployment, physical effects, or Effect Acknowledgement.

## First C90 implementation milestone

Start with a deliberately small, explicitly delimited calculus: propositional implication with K and S axiom schemas and modus ponens, using fully parsed proof certificates and structural equality of formulas. Prove soundness of the rules in Lean, then test C90 acceptance and rejection against a generated corpus. This milestone **cannot** certify the existing algebraic or EAP Lean theorems until a complete, independently validated translation of their dependent type-theoretic content is available.

## Current gate

No C90 theorem kernel, soundness theorem for its implementation, lossless Lean exporter or cross-kernel equivalence proof is currently established by this document. All remain OPEN. The four newly added EAP/integrity Lean statements are conditional statements over abstract models, not proof of productive EAP.
