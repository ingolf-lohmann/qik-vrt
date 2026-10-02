<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Current authority map

QIK-VRT contains an active reference implementation and a substantial
historical research and delivery archive. This map identifies the shortest
path to the current operational authority.

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

## Owner-requested stand-in Authority recovery acceptance

The 2026-10-02 owner request authorizes lossless recovery into the adjacent
Mirror, functional stand-in acceptance, then one neutral Mesh repository mirror.
The recovery acceptance record is
`evidence/receipts/authority-recovery-20261002/ACCEPTANCE.json`; its exact tree
inventories are reconstructed with `tools/qikvrt_integrity.py` rather than
trusting a truncated API list or transferring historical PASS claims.

The complete 2026-08-16 Authority content tree is retained under
`qikvrt/retained-authority/20260816-d18af01d` in `ingolf-lohmann/qik-vrt`. Its
3,781 blobs and exact tree identity are verified against the historical
reciprocal receipt. All paths still exist in the working Mirror; 44 changed
versions remain available in the retained source. This establishes historical
content retention. It does not establish the inaccessible Authority's final
complete recovery point or live role takeover.

The first acceptance gate remains BLOCK until the complete final Authority
source closure is bound. The next external boundary is an authenticated writer
that can create and populate a new repository: the currently callable GitHub
connector has no repository-creation or dispatch operation, and the existing
Mesh API supports ingest/verify/stage/release_status only.

A neutral child must receive a distinct GUID, its own target and state, retained
licenses and historical provenance, a fresh continuity receipt, actual Seed
acknowledgement and heartbeat. Role-local personal runtime state and credentials
are not inherited. A prepared target/GUID is not an existing repository.
Native full builds, independent current-head review/protection, role-epoch
fencing and actual effect readbacks remain mandatory before live acceptance.
