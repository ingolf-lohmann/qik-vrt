# Algebraic root: independent verification candidate

Copyright (c) 2026 Ingolf Lohmann. SPDX-License-Identifier: CC-BY-NC-ND-4.0.

The identities `a + 0 = a` and `a * 1 = a` do not entail distributivity. The Lean file provides an explicit Bool model with distinct identities, using AND as addition (zero=true) and XOR as multiplication (one=false), and a concrete failed distributivity equation.

## Proof gate (not yet passed)
1. Execute pinned Lean 4.19.0 kernel check of Root.lean on exact commit.
2. Check theorem and axiom inventories; no sorry, admit, or extra axiom.
3. Independently recheck the same theorem statement and assumptions using a distinct Lean checker (e.g. nanoda if toolchain-compatible); record exact versions and source SHA.
4. Optionally check the finite countermodel exhaustively with an independently implemented evaluator. This does not substitute for kernel checking.
5. Persist complete stdout/stderr, tool versions, commit/tree hashes, and independent comparison in an immutable evidence record.

Do not infer linear algebra, computability, QIK-VRT correctness, host operation, or EFFECT_ACK_DONE from these elementary results. The repository's existing science charter and admission rules remain in force.
