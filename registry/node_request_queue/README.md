# QIK-VRT Open Node Request Queue

This folder is intentionally open-ended. Do not predeclare a node count.
Add future Node request rows to OPEN_NODE_REQUESTS.tsv or add additional TSV files with the same columns.
The Seed revalidation workflow reads all queue rows on each run and does not perform global scanning.

Columns:
guid<TAB>source_repo<TAB>seed_repo<TAB>request_url<TAB>node_branch<TAB>heartbeat_ttl_minutes<TAB>lifecycle_policy

Allowed lifecycle_policy values: ACTIVE, SUSPENDED, REVOKED.

## Standing invitation and 400-byte lookup

The universal Transputer, universal Terminal and Mesh Authority accept new authorized Node requests without a predeclared Node count. The standing owner requirement and connection gates are in `registry/NODE_DISCOVERY_POLICY.json#/standing_invitation`. Add a Node row and its explicit matching `registry/NODE_POLICY.tsv` row through the existing reviewed repository path; each later Seed run discovers the new rows. Retain failed or unavailable members.

An admitted S1 export publishes `GET /api/mesh/invitation`, with an independent exact policy-byte readback, and answers `POST /api/mesh/lookup?nonce=<nonce>` with the exact 400-byte canonical seed as `application/octet-stream`. The caller sends the same seed to each owner-declared or admitted endpoint. HTTP framing is outside the 400-byte seed. An answer establishes packaged compatibility only; it does not grant a role, admit a peer, execute work or establish complete native connection. The historical original owner seed remains unbound; the preserved canonical V1 bytes are not relabeled as recovered historical bytes.

An Authority role is replaceable only after predecessor writer fencing, exact confirmed-state restore, authenticated new-role/epoch admission, safe quorum and fresh successor native/public readback. An unavailable Authority does not automatically promote another Node, and predecessor acceptance cannot transfer. Existing registry, watchdog and native runtime gates remain mandatory.
