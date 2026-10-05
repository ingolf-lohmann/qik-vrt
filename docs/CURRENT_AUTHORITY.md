<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Current authority map

QIK-VRT contains an active reference implementation and a substantial
historical research and delivery archive. This map identifies the shortest
path to the current operational authority.

## Owner-directed repository succession, 2026-10-04

Product and Code Owner Ingolf Lohmann has designated `ingolf-lohmann/qik-vrt`,
the former Mirror, as the new Authority and instructed creation of a new Mirror.
The exact directive and its distinct effect boundaries are retained in
`state/authorization/delegations/OWNER_AUTHORITY_SUCCESSION_AND_NEW_MIRROR_20261004_V1.json`.

The history-preserving PR successor binds current routing, defaults, bootstrap,
status and public interfaces to the new Authority in
`policy/CANONICAL_UPSTREAM_REMOTE_V1.json`. It is a review candidate; Main has
not been promoted and `AUTHORITY_CUTOVER_COMPLETED=false`. The separate new
Mirror contract is `state/autonomy/NEW_MIRROR_BOOTSTRAP_CONTRACT_V1.json`.
Its target is unspecified and this executing API client exposes no repository
creation operation. Therefore its exact state is
`HOLD_NEW_MIRROR_IDENTITY_AND_API_CREATION_CAPABILITY`; no Mirror was created.
Seed registration and node liveness require fresh records for the succession
epoch, rather than admission of the former Mirror's receipts. Historical
`Goldkelch/qik-vrt` release, publication and receipt bindings remain immutable.
An unavailable account is not an independent reviewer; the Authority role change
does not authorize self approval or weaker governance. The current review
identity blocker is recorded in
`state/work_units/QIKVRT_NATIVE_REVIEWER_ADMISSION_REPAIR_20261004_V1.json`.

The path and reference classifications are retained in
`state/work_units/QIKVRT_AUTHORITY_REFERENCE_CLASSIFICATION_20261004_V1.json`.
Frozen release/publication workflows remain bound to their original exact
authorization subjects. They do not grant publication authority to this cutover.

The PR's history-preserving Main integration is bound to
`86d7062f25f174039da0a5df8a856127553036f1` in the classification's
`main_lifecycle_successor` and the cutover work unit's `main_integration`.
The previous integration record remains in `main_integration_history` and its
exact predecessor commit; it supplies historical provenance, not current gates.
Main's current lifecycle projections and incoming receipts retain their exact
Main bytes. Superseded projection bytes remain bound through their original
source commit; the original classification and historical digest bindings are
unchanged. These former-Mirror lifecycle projections retain their historical
seed identity and are not fresh Authority-epoch liveness evidence. Exact-head
and synthetic-merge verification must be executed freshly for this successor.

## Active runtime

- `src/qikvrt_effect_ack.py` — five-state synchronous reference gate
- `src/qikvrt_api_handler.py` — authenticated ingest, verification, staging,
  status, transaction, provenance, and audit behavior
- `src/qikvrt_github_api_shim.py` — repository-scoped local HTTP adapter
- `scripts/qikvrt_api_client.py` — validating client
- `qikvrt.py` — authorization-before-effect launcher and publication planner
- `tools/qikvrt_subprocess.py` — bounded subprocess supervision
- `tools/qikvrt_integrity.py` — canonical content-tree integrity tooling
- `src/effect_ack_core.c` and `include/qikvrt/effect_ack.h` — strict ANSI-C90
  five-state core
- `tools/qikvrt_adaptive_runtime.sh` and `runtime/` — bounded proposal-only
  collective adaptation and exact-key verified cache reuse
- `tools/qikvrt_anticipation.py`, `anticipation/`, and
  `receipts/anticipation/` — deterministic current-status projection and
  hash-linked, effect-free closure checkpoints
- `tools/qikvrt_zenodo_actions.py` — hash-bound DOI reserve/finalize client
- `api/qikvrt_github_api.openapi.yaml` — external API contract

## Verification authority

- `tests/` — twelve Python test modules, the offline renderer, and shell/C90
  verification contracts
- `Makefile` — complete local verification entry point
- `STATUS.md` — precise demonstrated and open boundaries
- `BUILD_SUMMARY.md` — test counts and verification results
- `docs/TEST_INVENTORY.md` — test-module inventory
- `REPOSITORY_FILE_MANIFEST.json`, `SHA256SUMS.txt`, and
  `REPOSITORY_FILE_MANIFEST.json.sha256` — canonical integrity trio

## Concept and specification

- `README.md` — current technical entry point
- `docs/ARCHITECTURE.md` — runtime and deployment architecture
- `docs/BOUNDARIES.md` — operational boundaries
- `docs/QIKVRT_THREAT_MODEL.md` — threat model
- `docs/Die_Spirale_des_entscheidenden_Unterschieds.md` — full German-language
  synthesis, including the universal ontology of difference and the distinct
  proof and correspondence levels used by the work

## Release anchor

The current public release is the annotated tag
`v2026.07.22-effect-ack-universality-1.0.0` in both repositories. The working
paper is archived as `10.5281/zenodo.21498773`; the deterministic tagged source
export is archived as `10.5281/zenodo.21498774`. Exact repository-specific
commit, tree and tag-object identities are retained on the public
`qikvrt/zenodo-state` evidence branch.

Historical files remain evidence of their own time and content. They do not
override a current failure or expand the supported runtime scope.
