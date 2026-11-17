# QIK-VRT — SCIENCE IS, FICTION NOT! <=> SCIENCE RULES WORLDS

**Claim identifier:** `QIKVRT-SRW-001`
**Source:** Owner manifesto, 17 November 2026
**Classification:** `FORMAL_EPISTEMIC_POLICY_EQUIVALENCE` (not empirical physics)
**Lean module:** `QIKVRTFormalization.WorldFormula.ScienceRulesWorlds`
**Toolchain:** `leanprover/lean4:v4.19.0`

## Explicit semantics and valid scope

The statement is formalized as two directions of an epistemic *admission*
policy over `FormalState` and `FormalClaim`, reusing the existing world-formula
`EpistemicRelations` structure:

* `EvidenceAdmissible relations state claim` means the existing
  `PhysicallyQualified relations claim` **and** `relations.satisfies state claim`.
* `ScienceIsFictionNot relations admitted` means an unqualified world-claim
  cannot be admitted. Here **fiction is an operational shorthand for an
  unsupported or unqualified claim, not literary fiction**.
* `ScienceRulesWorlds relations admitted` means every admitted world-claim
  is qualified and satisfied in its designated state. It is *not* a claim
  that scientific institutions cause the physical laws of worlds.

The central Lean proposition is universally quantified over relation and
admission interfaces:

```lean
ScienceIsFictionNot relations admitted ↔ ScienceRulesWorlds relations admitted
```

The two predicates are not literal type aliases: one is stated as
`¬ qualified → ¬ admitted`, the other as `admitted → qualified`.
Their equivalence follows by contraposition in classical logic. No new
project-specific axioms or missing proof placeholders are permitted.

The theorem **does not establish** that an arbitrary EAP writer, consumer,
repository, or real-world community follows this policy. It also does not
establish physical truth of a given claim: `PhysicallyQualified` must itself
be independently evidenced at its actual referent. The Lean proof is an
internal implication and equivalence, not its own empirical evidence.

## Rest-of-repository compatibility

The module imports the existing `WorldFormula.Relations` and the latter's
unchanged `FormalClaim`, `PhysicallyQualified`, `ModelEstablished`, and
`formalOnlyRelations` definitions. Existing v2 root entrypoints
`QIKVRTFormalization.lean` and `QIKVRTUniversalOntology.lean` import this
module. The source-manuscript anchors, archived v1, existing claim matrices,
release manifests, writer/lease/fencing protocol and production effect
acknowledgments are **not** changed by this candidate.

The exported `VerifiedGate` defines a deliberately strict admission interface.
Its theorem `verified_gate_science_rules_worlds` proves soundness of that
formal gate. An operational consumer may only claim adoption after actual
consumer integration, single-writer admission, exact-HEAD CI, independent
readback and a separately evidenced effect ACK.

## Verification commands (run from v2 project root)

```sh
lake build QIKVRTFormalization QIKVRTUniversalOntology
lake env lean QIKVRTFormalization/WorldFormula/ScienceRulesWorldsAxiomAudit.lean
python3 -m unittest discover -s tests -p test_science_rules_worlds.py -v
python3 scripts/audit_lean_axioms.py
```

**Verification boundary:** A static file check and a finite Boolean truth-table
control are not a kernel receipt. Only a successful execution by the pinned
Lean version against the exact candidate bytes establishes a kernel-checked
proof. Persist its exit status, toolchain digest, commit/tree and axiom output;
verify the independent exact-HEAD CI and its source hash. Neither a local
commit nor a PR is productive authorization or a deployed EAP effect.

## Non-vacuity test

`unrestricted_admission_is_not_scientific` constructs a **countermodel** using
`formalOnlyRelations` and a gate that accepts every claim. It demonstrates
that the two policy forms can both be false, despite their equivalence.
This is why an unconditional claim that the real world obeys the manifesto
cannot be inferred from its formal equivalence alone.
