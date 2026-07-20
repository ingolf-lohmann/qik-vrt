# QIKVRT V2.13.4AT Seed Autonomous Mesh Operations

Seed role responsibilities:

1. Read only authorized node request URLs from `registry/KNOWN_NODE_REQUESTS.tsv`.
2. Validate node declaration and safety boundaries.
3. Persist canonical node entry under `registry/nodes/<GUID>.json`.
4. Persist central aggregate index under `registry/NODEMESH_INDEX.json`.
5. Persist liveness/status aggregate under `registry/NODEMESH_STATUS.json`.
6. Persist evidence under `evidence/seed_acceptance/` and `evidence/seed_mesh_maintenance/`.

Boundaries: no global scanning, no self propagation, no foreign repository mutation, no token persistence.
