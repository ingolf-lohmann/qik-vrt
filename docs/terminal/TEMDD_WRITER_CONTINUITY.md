<!-- SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 -->
# TEMDD writer continuity

A copied SQLite epoch and a copied `owner.lock` do not convey write authority.
A filesystem lock excludes writers of that physical lock only. Native schema 2
therefore binds its writer to the Linux boot identity and the physical directory,
SQLite file and lock inodes. Construction and every append recheck this seal.
The original event bodies, sequence numbers, native-input digests and receipts
retain their existing representation. Old schema-1 code rejects schema 2.

A fresh physical store can be initialized once. A process restart on the same
physical store during the same boot preserves its epoch and deduplication.
Copied stores, replacement lock files, a host reboot, or legacy stores without
writer provenance require explicit fenced admission; they are never silently
blessed as writers. `Ledger(..., read_only=True)` reads original schema 1 or 2
histories and cannot append. This does not assert active-host or quorum status.

`restore-state` still restores pinned original bytes create-only. It grants no
writer admission. For a quiescent same-host schema-2 relocation, the existing
self-host CLI offers `transfer-local-writer`, with the pinned package/config,
`--source-state-dir` of the actual original store and `--frontier-sha256`.
`Ledger.history_frontier()` verifies all original rows and computes this pin.
The source and destination rows and metadata must agree exactly. Both native
writer locks and any node locks must be available. The source revocation commits
with SQLite FULL durability before the target seal is admitted. An interruption
between these commits leaves both sides unable to append. Recover this ambiguity
by inspecting the original stores and revocation intent, never by resetting the
epoch, creating another writer, or retrying an external effect.

This local handoff is neither cross-host fencing nor production-host admission.
An unreachable original writer, an unsealed legacy store, or an existing fork
remains HOLD until the original protected admission and distributed exclusion
are evidenced. A reboot similarly requires that protected recovery; no automatic
reboot takeover is claimed. Portable and browser representations remain readable.
A copied portable image cannot acquire a native writer merely by being restored.

For the 18 October fork, common events 1–23 and both conflicting suffixes must be
retained with original `(id, ledger_digest)` pairs and original bytes. An event-ID
collision cannot be repaired by deleting, renumbering or relabeling acknowledged
events, or by declaring one copied branch authoritative. Reconciliation evidence
must preserve every branch, qualify conflicting receipts by their original
digest, and separately establish the next admitted writer.
