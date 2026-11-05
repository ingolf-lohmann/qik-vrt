<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Delivery reporting proof obligation

Owner: Ingolf Lohmann. Supplied analysis: Claude Mirror, delivered by the Owner;
its original bytes and SHA-256 are retained in `history/OWNER_FEHLERANALYSE.txt`.
Implementation and evidence repair: OpenAI Codex. Source carrier: existing PR546.

The policy `policy/QIKVRT_FORMAL_PROOF_OBLIGATION_V1.json` resolves all seven
checker identities. The six external names match Lean 4.35.0's bundled checker
commands; they are external recheck programs, not six remote web services.
The official distribution's CMake and Lake sources bind the checked forks and
commits. Exact upstream Git-commit GETs are retained in the history readback.
An arbitrary ancestor commit is not necessarily an advertised Git ref: use its
exact Git commit readback, rather than treating an empty `ls-remote SHA` as proof
that it does not exist. Unresolved names hold for an Owner choice; no substitution.

`QIKVRTDeliveryReporting` is a separate `lean_lib` root in the isolated
`formalization/QIKVRT_Formalization_v2.0/delivery-reporting` Lake package.
The original root `lakefile.toml` and archived
`QIKVRTEffectAck.lean` remains unchanged. New files are excluded through the
existing post-Alpha2 input list, preserving the original Alpha2 archive bytes.

T1 proves the decision/admissibility equivalence. T2 rejects local-only delivery
claims; T3 requires a matching remote HTTP200 observation within the action
window; T4 rejects repeated observation IDs. No project axiom or proof hole is
introduced. The axiom audit records `propext` for T1, `propext` and `Quot.sound`
for T2/T3, and no axioms for T4. Host classification, observation authenticity,
independence and actual clock meaning are adapter preconditions. Durable
correction, continuation and peer adoption (R3-R5) are not formalized here.

The 4.19.0 generator produced 1,152 exact-byte-pinned JSON vectors in native run
41238540287. The Python bridge exercises both `validate_client_receipt` and
the real `--client-receipt` CLI. Removing the status condition creates verdict
disagreements. These finite controls do not establish a universal refinement
theorem for Python, arbitrary prose or another node's EAP client.

The original 4.19.0 kernel builds the model and replays only declarations from
its original module payload against exact original imports. Six original 4.35.0 checker executables recheck a
fresh common export built from identical source. This is not replay of 4.19.0
oleans in 4.35.0. Their theorem and axiom inventories must agree. Compiler,
exporter and implementation dependencies are shared; independence is not assumed.

Run from the repository root after provisioning the two SHA-256-locked official
distributions:

```sh
python3 -B tools/ai_handoff.py --formal-proof-run .qikvrt/formal-receipts/DeliveryReporting \
  --own-lean-root /actual/lean-4.19.0-linux \
  --external-lean-root /actual/lean-4.35.0-linux
python3 -B tools/ai_handoff.py --formal-proof-gate .qikvrt/formal-receipts/DeliveryReporting
python3 -B -m unittest tests.test_delivery_reporting_proof
```

The output directory must be fresh. Commands, exits, original combined output,
UTC, source bundle, olean/export hashes and per-theorem axioms are retained.
Missing vectors, any missing/nonpass checker, a panic despite exit zero, wrong
source, a changed replay input or log, and inconsistent inventories all hold.
Nanoda enables its documented Nat/String extensions with the same three-axiom
allowlist; it never admits arbitrary axioms or `Lean.trustCompiler`.

The existing ontology workflow freshly executes this path. For affected change
classes, the original REST merge evaluator requires that exact-head workflow in
addition to its existing governance, source, CI and competing-writer gates.
Static receipt/log consistency alone is not authenticated execution. Workflow
source is not active Main protection; privileged external bypasses are outside
this checker. No new scheduler, executor, credential route or deployment is added.

Historical failures remain visible: the initial invalid Lean identifier;
accidental inclusion in the old Alpha2 package; the first replay's zero-exit
panic caused by replaying unrelated imported declarations; nanoda's disabled
literal extensions; and the deliberate missing-vector hold. No old PASS is
transferred to a new source bundle. Receipt success proves no Main merge,
remote client adoption, runtime admission, domain acceptance or EFFECT_ACK_DONE.
