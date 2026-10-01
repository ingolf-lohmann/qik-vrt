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
Independent kernel, empirical, peer-review and reproduction adapters are not yet
admitted by this first audit layer, so their verification flags remain false.
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

The existing global-completion workflow stores the report as an Action artifact.
The mandatory existing global-completion test block includes positive and negative
audit controls. No new workflow, writer, provider credential or publication path
is introduced. The policy and schema files define the durable contract.
