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

## Mandatory dependency order: full QIK-VRT mathematics before C90

The complete agreed QIK-VRT Lean model and its requirements/features must be inventoried and formalized first: metatransistor, compositional cascade, serializability, universal transputer, universal terminal, universal data processing, double-canonical storage, Trusted Mesh and Effect Acknowledgement Protocol. Every claim must bind to its exact formal definition, explicit assumptions, theorem, dependency closure, and reproducible external-kernel result. Unknown, unspecified, unproved or merely empirically tested claims must remain OPEN; universality claims require a precise computational semantics and scope. No abstract proxy theorem can be represented as proving the production architecture.

Only after this foundation is proven and independently checked may implementation of the QIK-VRT-compliant C90 Lean-compatible compiler/kernel be accepted as derived from that foundation. A standalone narrow toy calculus is not a substitute for this gate. The C90 implementation must support the required architecture properties and demonstrate semantics preservation, independently checked proof certificates, reproducible compilation, serializable and composable evidence, and performance improvement without weakening correctness. Proof search, compilation, kernel checking and observed physical effects remain distinct trust boundaries.

## Current gate

No C90 theorem kernel, soundness theorem for its implementation, lossless Lean exporter or cross-kernel equivalence proof is currently established by this document. All remain OPEN. The four newly added EAP/integrity Lean statements are conditional statements over abstract models, not proof of productive EAP.
