<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Role-neutral node genesis and recovery V1

The normative Product-Owner requirement is carried by
`policy/QIKVRT_NODE_GENESIS_RECOVERY_V1.json`. A full Authority or Mirror node
can reconstruct its persisted Git state with every other remote unavailable.
The executable scope is the complete closure reachable from **all local refs
and HEAD**, including parent history, tags, tree bytes and modes, policies,
registry/lifecycle files and the integrity trio. A node cannot reconstruct
bytes it never retained. Every persisted Git object must be reachable; export
blocks on unreachable/reflog-only objects until they are pinned with retention
refs. Reflog/config metadata, dirty edits, ignored caches and remote-only state
are outside this snapshot's explicit scope.

`node.bundle` is a complete Git v2 bundle. `snapshot.json` is canonical UTF-8
JSON (sorted keys, two-space indentation, LF and one final LF). Its SHA-256 is
the independently retained recovery anchor. The detached digest in the same
directory detects inconsistency; it does not authenticate a substituted
archive. Retain the snapshot and trusted anchor on the node's durable storage.
Git configuration, credentials and hooks are never copied into the snapshot.
Git's offline-bundle format and empty-database prerequisite verification are
documented at <https://git-scm.com/docs/git-bundle>.

```sh
python3 -B tools/qikvrt_node_genesis.py export \
  --repository ingolf-lohmann/qik-vrt --destination /durable/node-snapshot
python3 -B tools/qikvrt_node_genesis.py restore \
  --snapshot /durable/node-snapshot --expect-snapshot-sha256 "$trusted_snapshot_sha" \
  --destination /durable/reconstructed-node
```

Export rejects incomplete object stores, uncommitted source state, replace
refs, grafts, alternates and active gitlinks. Restore works in a new empty
object database with only the local file protocol enabled. It checks exact
bundle coverage, full strict fsck, fresh object inventory, HEAD/tree/refs,
symbolic refs, persisted ancestry and the existing repository-integrity gate.
No successful imported check is relabelled as a fresh check. Repeating restore
on an identical destination verifies it again and creates a new observation
receipt in `.git/qikvrt-recovery.json`. A changed destination fails closed.

Byteidentity means retained Git object payloads and tracked application bytes,
modes and refs. Pack encoding and index timestamps need not match. Two
independently repacked archives may differ; the supplied archive is always
verified against its exact byte count and SHA-256. Historic evidence stays
byte-identical and historical. Runtime caches, LFS payloads beyond pointer
bytes, and external services need their separate bindings.

```sh
python3 -B tools/qikvrt_node_genesis.py genesis \
  --snapshot /durable/node-snapshot --expect-snapshot-sha256 "$trusted_snapshot_sha" \
  --expect-head "$source_head" --kind RECOVERY_AUTHORITY \
  --repository ingolf-lohmann/qik-vrt --authorize-local-candidate \
  --destination /durable/authority-candidate
```

`MIRROR` creates a new mirror identity; `CHILD` creates a new independent
project in the Goldkelch namespace. All descendants retain a cycle-free
ancestry rooted at `Goldkelch/qik-vrt` and the complete parent history.
`RECOVERY_AUTHORITY` retains the recovering repository's identity. Each local
genesis writes `policy/QIKVRT_NODE_BINDING_V1.json`, updates the candidate's
remote-role policy, regenerates only the existing integrity trio and creates
one commit on a new create-only genesis branch. Its sole parent is the exact
source head. Original refs and lifecycle bytes remain intact. Commit identity
is deterministic: the synthetic commit time is source commit time plus one
second; it is not an observation timestamp. Observation receipts use fresh UTC.

This is a **CANDIDATE_ISOLATED** role transition. Effective Mesh authority needs
an exact candidate-bound owner decision, fencing or controlled reconciliation
of old authorities, newly verified target capabilities, exact-head gates and
fresh remote readback. A failed connection does not prove that another
Authority is extinct. The existing pre-effect controller rejects every
`node_genesis_state` marker; this version implements no remote admission or
repository-creation executor. Future admission must be a separately reviewed
successor. The local authorization flag authorizes only this isolated candidate.

Secrets, OAuth/biometric/signing bindings, namespace/repository creation rights,
branch protection, Code-Owner reviews, workflow admission and deployments are
capabilities to rebind. Existing historical grants and receipts do not establish
their present availability. No platform repository is created by this tool.
Run `make node-genesis-test` for offline positive/adverse verification. A local
recovery test is evidence of that bounded implementation, not global Mesh
equality or `EFFECT_ACK_DONE`.
