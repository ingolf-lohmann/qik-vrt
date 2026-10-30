# QIK-VRT Autonomous Mesh Operations

4AV1 adds lifecycle hardening: renewal, heartbeat expiry, Seed status aggregation, Seed audit export, and a human readable dashboard.

Core boundary: every repository writes only to itself. The Seed reads only authorized known Node URLs listed in `registry/KNOWN_NODE_REQUESTS.tsv`.

# Seed identity and acceptance repair (2026-10-09)

The node handshake, current registration request, Seed allowlist and executing
Seed repository must describe the same identity. The lifecycle generator runs
`tools/qikvrt_seed_common.py config-check` before writing health or renewal
files. Changing only a repository label or URL is not a completed migration.

The current request and handshake use `ingolf-lohmann/qik-vrt` as Seed. The
previous Goldkelch acknowledgement is retained under `previous_acceptance`;
the new identity starts as `PENDING_SEED_ACCEPTANCE`. Historical registry
entries, aggregates and ledger records are preserved until fresh execution
produces successor evidence. No July acceptance is relabelled as an October
acceptance by another Seed.

The existing acceptance workflow validates the current request, maintains
and revalidates its output, and reuses the lifecycle Git Data publisher to
create a reviewed Draft. That path requires native Code Owner enforcement,
checks current Main before writes, permits only generated registry/evidence
paths and the full integrity trio, creates a candidate ref without force,
and reads back its exact commit/tree/PR. Artifacts and Drafts are not Main
publication. Generated pending acknowledgement remains CONTINUE.

After reviewed Seed output is published on Main, the existing node lifecycle
workflow executes `tools/qikvrt_seed_common.py acknowledge`. This performs
bounded GETs of the Seed Main ref, index and node entry at that exact commit,
then reads the ref again. It rejects wrong identities, legacy schemas,
duplicate node entries, a mismatched request hash, stale/future observations
and ref drift before changing the acknowledgement. The resulting v2 record
binds the accepted entry/index hashes and the actual acceptance run. Seed
maintenance checks the acknowledgement against its current accepted entry;
an invented status string does not activate a node.

Lifecycle telemetry uses the existing `qikvrt/node-lifecycle` transport and
separate reviewed persistence. It never pushes Main directly. Source and
historical evidence remain digest-bound in the unchanged integrity generator;
scheduled observations no longer invalidate Main by an unreviewed write.
The regression suite includes stale/copy/repoint/drift controls, proof-hash
and acceptance-run mismatch, no-write governance failures, replay, exact-tree
Draft readback, unrelated-path rejection and ambiguous-response handling.

These controls protect the tested execution paths. Privileged manual changes,
future defects, provider outages and missing review/admission cannot be ruled
out universally. A Mesh registration does not establish a running transputer,
public domain delivery, or general EFFECT_ACK_DONE.
