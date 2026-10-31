# QIK-VRT Open Multi-Node Architecture 4AV1

4AV1 removes the fixed additional-node count from 4AV. The Seed keeps an open node registry. Future Nodes are added by appending authorized request rows under `registry/node_request_queue/*.tsv` or `registry/KNOWN_NODE_REQUESTS.tsv`.

This preserves the QIK-VRT boundary: no global scanning, no self-propagation, no foreign repository write. The Seed revalidates only known or explicitly queued Nodes.

## Exact Seed binding and requested cognitive clients (31 October 2026)

`registry/NODE_DISCOVERY_POLICY.json#/seed_binding` fixes the complete
`qikvrt-seed-binding/v1` preimage. Reuse the original Seed validator:

```sh
python3 -B tools/qikvrt_seed_common.py binding \
  --source-head 5a42baf45748e4407a8fa16aef287a77873e788d \
  --source-tree 3f6e816b6b496eeb9ce8777d8fb93d95717be9ae
```

The command reads the two JSON objects from that exact local Git commit,
checks the commit/tree and Authority/Seed identities, and hashes each with
the original `canonical_json_bytes`: sorted keys, two-space indentation,
UTF-8 without ASCII escaping, finite numbers and exactly one final LF. This
serialization is different from the EAP wire protocol's JCS. The composite
preimage has exactly `schema`, `repository`, `seed_guid`, `head`, `tree` and
`canonical_file_sha256` (full repository paths as keys). Its SHA-256 excludes
the outer `binding_sha256` field. The complete reference preimage is retained
in the existing discovery policy.

Both component hashes in the Owner-supplied Mirror report were reproduced.
The reported composite `619baa869a4d71a35a672d9fc999ac4f605debcccfe66e875148b420e4ba5ff7`
is not adopted: the report supplies no complete composite preimage. This
does not assert that the reported hash is mathematically invalid. The newly
specified version-1 preimage yields
`d74577da05d7c9dbc6cffd422aef0b8a0c1e309decd434bb1e67b2b72e6e84d3`.
It is a historical source binding; the index still records one STALE node.
An anchor does not refresh liveness. A later source commit requires its own
binding and fresh runtime evidence; it does not inherit this acceptance.

After a real HTTPS `GET https://raumzeitterminal.de/api/eap/state`, require
schema `qikvrt_eap_http_status_v1`, state `NATIVE_EAP_HTTP_READY`, and exact
`subject.repository`, `subject.head` and `subject.tree`. Check the saved
response against the exact source binding with:

```sh
python3 -B tools/qikvrt_seed_common.py binding-state-check \
  --binding-file /private/seed-binding.json --state-file /private/eap-state.json
```

This offline check rederives the binding from Git. It cannot prove response
origin, freshness, HTTP success or principal authentication. The actual
transport observation and authenticated prepare/commit/independent native
receipt readback remain necessary. Anonymous subject equality proves none
of those effects and never establishes productive `EFFECT_ACK_DONE`.

The Owner requested Codex and Claude Mirror registrations. The existing
`KNOWN_NODE_REQUESTS.tsv` and `NODE_POLICY.tsv` reserve distinct UUIDv5 IDs:

| Requested client | Reserved GUID | State |
| --- | --- | --- |
| Codex | `90c1665b-bbfb-5155-a88c-3579799ecb5d` | `PENDING_BINDING` |
| Claude Mirror | `e250ce54-85af-55f4-ad94-01b8c38a85cc` | `PENDING_BINDING` |

Their node-owned source repositories, request URLs and revisions have not
been independently bound. Those columns must stay `UNBOUND`; inventing a
repository or claiming the Authority's GUID for both clients is forbidden.
Pending rows cause no network fetch, generate no Seed-acceptance entry or
acceptance ledger event, remain visible as UNKNOWN during maintenance,
and cannot validate an onboarding request. On binding either client, the
existing continuity/watchdog declaration and receipt checks remain required
even when its row is in `KNOWN_NODE_REQUESTS.tsv`. Native identity and the
private peer channel need independent admission and readback as well.

The existing `runtime/self-host/CONFIG.example.json` now prepares the
`mirror:claude` grant using `/etc/qikvrt/owner-rest-claude.token`, with only
the existing bounded input `prepare`, `commit` and `readback` operations.
This grants no GitHub writer role. It is a template, not the live private
configuration. Provision a distinct owner-controlled 0600 key outside the
repository/package and use the existing configuration/package/volume
re-sealing and host admission procedure in `runtime/self-host/EAP_HTTP.md`.
No secret was generated or exported for a production principal. Missing
private material fails closed; a saved template cannot activate a grant.
