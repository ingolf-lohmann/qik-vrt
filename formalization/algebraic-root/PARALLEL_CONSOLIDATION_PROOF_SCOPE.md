# Parallel consolidation: proof scope and non-proven obligations

The file `paranoid/ParallelConsolidation.lean` provides a finite, pure
functional model. The independently checked theorem
`consolidation_equals_sequential` proves that a complete, nonduplicating
permutation of task indices, followed by inverse-index consolidation, returns
exactly the same indexed results as sequential evaluation of independent
deterministic tasks. `domain_independent_consolidation` proves this for
thread, process, interrupt and network *labels*. The proof does not rely on
the location of execution.

`Reversible` separately proves forward/backward round trips **given**
two-sided inverse laws. It does not prove that arbitrary computations are
reversible, nor any physical claim about retrocausality or superdeterminism.

## Explicit assumptions / proof boundary

1. The transport/scheduler implements `CompleteSchedule`: no lost,
   duplicated, forged or unboundedly delayed task results, and correct
   identity binding. The model does not establish those properties for a
   real network or runtime.
2. Every task is a pure deterministic function with no shared mutable state,
   side effects or order-dependent interactions. General parallel programs
   are **not** sequentially equivalent without additional conditions such as
   linearizability/serializability.
3. Consolidation retains the complete indexed result vector. A lossy
   aggregation, e.g. a checksum alone, does not satisfy this guarantee.
4. EAP acknowledgements and the storage gate require independent runtime
   refinement proofs binding observed effects, complete delivery, authenticated
   identities and persistence to the abstract model.
5. A separate mathematical kernel and an independently validated verifier
   implementation remain integration obligations. Acceptance by six Lean
   checkers confirms the stated conditional theorems, not the operational
   assumptions or production deployment.

## Negative controls to formalize next

Missing result, duplicated result, conflicting result for an index, reordered
noncommutative side effects, tampered payload, malicious acknowledgement,
interrupted persistence and replay across epochs must be rejected by a
concrete refinement model before a universal losslessness claim is warranted.

The repository may persist the *formal source and its evidence* on a review
branch. This does **not** constitute mathematical approval for automatically
persisting arbitrary operational work products to GitHub.
