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
content retention. It does not establish the latest complete Authority recovery point or live
role takeover. The frozen working-parent comparison is historical; it must not
be substituted for the current Mirror Main or current PR subject.

The fresh 2026-10-02 API reobservation confirms that installation `147849532`
for `Goldkelch` selects all repositories and lists `Goldkelch/qik-vrt` with
repository ID `1271407206`, `pull=true` and `push=true`. Generic name, stable-ID,
Main-ref, ref-inventory and content reads still return HTTP 404. This is an
installation/content-routing or carrier boundary in the current execution; it
is not evidence that the Authority repository does not exist or is globally
unreachable. The root cause inside the router or platform is not established.

The exposed connector has installation-bound listing/search, but no content,
commit, tree or ref read accepts an installation ID or selected installation
credential. No unsupported installation parameter is substituted into a
generic read. The first causal acceptance blocker is therefore
`AUTHORITY_INSTALLATION_CONTENT_ROUTING_CARRIER_UNAVAILABLE`. The next action
is to expose and use an authorized content carrier explicitly bound to this
installation and repository, freshly read Main/HEAD/TREE and all required
refs/objects/source closure, and compare that exact Authority subject with the
retained historical tree and the reobserved Mirror. The first source-acceptance
gate remains BLOCK until this closure is verified. The next external boundary is an authenticated writer
that can create and populate a new repository. Reported `push=true` does not
establish repository-creation capability. The currently callable GitHub
connector has no repository-creation or dispatch operation, and the existing
Mesh API supports ingest/verify/stage/release_status only.

A neutral child must receive a distinct GUID, its own target and state, retained
licenses and historical provenance, a fresh continuity receipt, actual Seed
acknowledgement and heartbeat. Role-local personal runtime state and credentials
are not inherited. A prepared target/GUID is not an existing repository.
Native full builds, independent current-head review/protection, role-epoch
fencing and actual effect readbacks remain mandatory before live acceptance.

All predecessor checks remain bound to their original subjects. The direct
PR #444 successor requires fresh complete-checkout validation. Historical
retention, generic transport responses and successful tests do not themselves
accept live stand-in Authority takeover or neutral-Mirror creation.

## 2026-10-03 recovery continuation

PR #444 integrates Mirror Main `8153c4e69a6245aadf67f0741fb50d9707c19e34`
over input `380fb965a184ee6137bc98ea58868eb8b59ecbce`, preserving both
histories and every parent path. Ten role-local paths include all three new
heartbeat/registration event pairs. The same Mirror GUID remains unchanged;
the previously expired heartbeat now uses Main's scheduled producer
`37120239456-1`, with recorded expiry `2026-10-04T12:37:33Z`.
These timestamps establish the stored lifecycle at observation time, not
end-to-end runtime availability or Authority-role acceptance.

The existing fixed Authority probe in PR #446 ran as `37086743407` on
`7ed957669a8f6f0e03c62cff7787a45cfaceab12`. Its native artifact was downloaded
and its ZIP and readback digests verified. It records
`AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED`: the existing direct-token
and App inputs were absent in that exact runner, while the Mirror control
read succeeded. This does not establish global credential absence or the
cause of the Authority's 404. It supplies no gate for PR #444.

The smallest source-closure continuation remains an authorized Authority
content carrier, or delivery of an existing Authority-read credential into
that fixed probe followed by a new initial exact-ref invocation. This client
has no secret-binding, initial-dispatch or repository-creation operation.
Fresh candidate CI, native protection and independent exact-head review
remain separate from complete Authority source and observed role effects.
