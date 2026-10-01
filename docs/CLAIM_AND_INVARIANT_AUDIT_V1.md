<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Claim and invariant audit v1

Ingolf Lohmann's requirement of 1 October 2026 adds an auditable epistemic layer
to the existing Global Claim Inventory. `tools/qikvrt_global_completion.py audit`
reads its 92 registered claims without rewriting their historical classifications,
proof maps or receipts. A new `qikvrt_claim_audit_input_v1` registry can instead
supply `claims`, `invariants` and structured `relations` arrays.

Each claim supplies `claim_id`, `claim_statement`, `epistemic_domain`,
`claim_class`, `sources` and `evidence`. References contain repository-relative
`path`, exact `sha256`, declared `source` and typed `kind`. Documentary source,
formal proof, simulation and observation remain distinct. Paths cannot escape the
repository or traverse symlinks. All supplied hashes are recomputed from bytes.
A declared source is traceability metadata; it does not authenticate its author
or establish the truth of its contents.

The auditor computes the claim, evidence, verification and epistemic checklists.
It computes forbidden implications through the entire structured graph, including
indirect paths. `INV_REALITY_001` is always included and cannot be overridden.
Formal-model claims from the historical protocol inventory retain their original
category explicitly; their mapped FORMAL audit domain covers only that model.
A registered source is not automatically primary empirical evidence.

Invariants support `SET_SUBSET` over two byte-bound JSON snapshots and
`NON_IMPLICATION` over structured edges. For example, an invariant can declare:

```json
{
  "invariant_id": "INV_NODES_001",
  "class": "STRUCTURAL",
  "statement": "OLD_NODES ⊆ NEW_NODES",
  "predicate": {
    "type": "SET_SUBSET",
    "field": "nodes",
    "old": {"path": "old.json", "sha256": "<exact SHA-256>", "source": "bound old snapshot"},
    "new": {"path": "new.json", "sha256": "<exact SHA-256>", "source": "bound new snapshot"}
  }
}
```

The engine neither executes arbitrary rules nor decides unrestricted prose truth.
An undeclared or unsupported invariant evaluator remains HOLD. `runtime_audit`
records whether one of the admitted predicates actually executed. Bound
`observed_reality` references for `predicted`, `executed`, `observed` and `readback`
can be displayed, but missing stages remain null and `effect_ack` stays false.
No input-provided PASS, verification flag, peer-review label or ACK grants trust.
The first admitted independent verifier is `INDEPENDENT_LEAN_KERNEL_V1`, limited
to primary registered FORMAL model claims. Empirical, peer-review and reproduction
adapters remain unadmitted and their verification flags remain false. Requests
for those verifiers (`required_verifiers`) retain HOLD even if a formal model
proof is independently checked. Appendix aliases and unregistered assertions
cannot inherit primary proof verification.
Existing historical verified dispositions are preserved independently.

PASS means the stated audit checks passed in their declared scope. It does not
mean empirical truth, generic semantic validity, scientific consensus, product
acceptance or EFFECT_ACK. Missing independent verification yields HOLD. Malformed
claims, invalid source bindings, category errors and forbidden deductions yield
FAIL. Source traceability and category checks have explicit bounded scope.

Run and independently recheck a report:

```bash
python3 -B tools/qikvrt_global_completion.py audit > /tmp/claim-audit.json
python3 -B tools/qikvrt_global_completion.py verify-audit --report /tmp/claim-audit.json
```

Use `--input` for another registry. `--require-verified` returns exit 3 if a HOLD
remains. Exit 2 reports an encoded audit failure; exit 1 reports malformed input
or failed meta-audit. Ordinary exit 0 can retain HOLD and permits no release.
The meta-audit recomputes the complete report once, rereads bound sources and
compares every field; merely recalculating a tampered report hash cannot pass.
This finite check does not claim an infinite regress has been proved away.

For the admitted formal path, the executor supplies the exact expected candidate
HEAD, TREE and an invocation identifier independently of the report:

```bash
python3 -B tools/qikvrt_global_completion.py audit \
  --formal-verifier lean-kernel --expected-head "$EXPECTED_HEAD" \
  --expected-tree "$EXPECTED_TREE" --execution-id "$AUDIT_EXECUTION_ID" \
  > /tmp/claim-audit.json
python3 -B tools/qikvrt_global_completion.py verify-audit \
  --formal-verifier lean-kernel --expected-head "$EXPECTED_HEAD" \
  --expected-tree "$EXPECTED_TREE" --execution-id "$AUDIT_EXECUTION_ID" \
  --report /tmp/claim-audit.json
```

The adapter recomputes the inventory and every native-kernel receipt from the
current registries and actual source bytes. It checks the frozen historical tag
commit/tree and exact source equality, rather than transferring its disposition.
It extracts Lean source/configuration from the immutable candidate commit into a
new directory, builds without project proof caches, and hashes the fresh source
and compiled proof/registry modules. A preexisting object with different bytes is
rejected. Candidate, tag and receipt bindings are checked again after execution.
Twelve frozen manuscript receipts have a null compiled-object field. Their new
runtime receipts bind the actual compiled source module freshly; the null field
does not count as object evidence and historical records remain unchanged.

A separate Lean process loads project objects as data with project initializers
and extensions disabled. The upstream replay routine reconstructs every safe
project declaration through the native kernel at trust level zero in a separately
loaded Lean/Std base, including inductives and their generated constructors and
recursors. Compiler-only unsafe/partial auxiliaries are excluded from logical
replay and cannot be selected as proof, statement or registry constants. Proof
constants must be actual theorems. All selected constants must be present and
originate from their exact registered source modules;
their transitive axioms must be within `Classical.choice`, `Quot.sound`, `propext`.

The existing locked Linux x64 Lean 4.19.0 runtime is bound by exact version,
source commit, native executable and kernel-library SHA-256. The upstream replay
source is vendored with its pinned commit, original digest, attribution and
Apache-2.0 license under `third_party/lean4checker/PROVENANCE.json`. This reuses
the existing Lean runtime; it adds no external verification service or toolchain
downgrade. Other platforms remain outside this initial admission.

The audit report binds each admitted claim to its source, proof/statement/registry
constants, compiled objects, transitive axiom observations, recomputed registered
receipt, native kernel result, expected candidate and invocation. `verify-audit`
rejects changed candidate, input or invocation and repeats the build/replay.
Rehashing a modified report does not restore acceptance. Caller-supplied
`verified` and other verification flags never enter this decision.

Independence here means recomputation in a separate native-kernel process, not
another human, organization or typechecker implementation. The locked Lean
kernel and bundled Lean/Std base remain trusted computing components. Formal
derivability is limited to the exact Lean statements and assumptions; prose
equivalence, physical truth, peer review, reproduction and external effects
remain outside its proof. `audit_pass_is_claim_truth`, `external_effect` and
`effect_ack_done` remain false.

The existing global-completion workflow stores the report as an Action artifact.
The mandatory existing global-completion test block includes real-kernel positive
and negative controls for modified Lean source (even with resealed metadata),
stale tags/receipts, wrong proof/registry constants, changed objects, nonallowed
axioms, missing native proof constants and report replay. This workflow requires
the locked Lean runtime; its native tests cannot skip. No new workflow, writer, provider credential or publication path
is introduced. The policy and schema files define the durable contract.
