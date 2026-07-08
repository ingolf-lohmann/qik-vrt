# QIKVRT V2.13.4AT Node Autonomous Mesh Operations

Node role responsibilities:

1. Publish node heartbeat under `qikvrt/runtime/onboarding/NODE_HEALTH.json`.
2. Read the public seed index under `registry/NODEMESH_INDEX.json`.
3. Read its own accepted seed registry entry under `registry/nodes/<GUID>.json`.
4. Persist node acknowledgement under `qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json`.
5. Persist evidence under `evidence/node_health/` and `evidence/node_seed_link_status.json`.

Boundaries: no global scanning, no self propagation, no foreign repository mutation, no token persistence.
