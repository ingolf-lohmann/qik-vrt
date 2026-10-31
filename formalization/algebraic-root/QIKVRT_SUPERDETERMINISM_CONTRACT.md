# QIK-VRT Superdeterminism: normative mathematical contract (31 October 2026)

**Owner's project-specific definition.** Superdeterminism in QIK-VRT means
reversible, reproducible transformations from a completely specified initial
state to a completely specified final state; preservation of the information
needed to recover the initial state; and exact equality of canonical
consolidation with sequential computation, within specified spatial, temporal
and technical operating limits. It is **not** the physical interpretation of
superdeterminism and does **not** assert zero thermodynamic entropy.

## Formal source and scope

`paranoid/QIKVRTSuperdeterminism.lean` defines
`QIKVRTSuperdeterminism State` as a pair of two-sided inverse functions,
proves injectivity (no *logical* information collapse), both recovery laws,
deterministic evaluation, and exact equality and recovery of independent
parallel tasks with a complete bijective delivery schedule.

`ParallelConsolidation.lean` handles threads, processes, interrupts and
networks as abstract execution-domain labels. These are not proofs of
operational delivery, absence of races, reliable clocks, deterministic
interrupt handling, or authenticated remote effects.

**Crucial proof obligation:** A *full state* includes any history, logs,
side effects, nondeterministic inputs and environment needed for inverse
reconstruction. A noninjective application function does not become
reversible merely by calling it reversible; the information must be retained.

The phrase "absence of entropy" is formalized solely as injectivity and
recoverability of the logical state. No thermodynamic claim follows.

## Future persistence gate

The independently checked mathematics is the intended approval authority
for repository-generated work. Every producing workflow must bind the
candidate's exact bytes and the applicable mathematical specification to
a separately executed verifier verdict. Rejection must return actionable
feedback to the producer; no approval means no publication. GitHub branch
protection, required status checks and write-token scoping must enforce
this for *all* repository write paths. Until those controls and concrete
runtime refinement proofs are present, this is a **target contract**, not
a claim that all GitHub writes are already gated.

The current `math_gate.py` is an interface and bounded retry mechanism.
Its test verifier is a mock, **not** the independent Lean mathematical
kernel; successful contract tests cannot authorize arbitrary code or
mathematical claims. The six-kernel CI independently checks the formal
theorems, not arbitrary generated candidate outputs.

The later implementation of the EAP/Trusted Mesh runtime, authentication,
physical transport, effect observation, delivery guarantees and
host/domain deployment is deliberately out of scope here.
