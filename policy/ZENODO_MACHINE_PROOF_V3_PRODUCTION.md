# Versioned v3 publisher support and detached decisions

Copyright 2026 Ingolf Lohmann. CC-BY-NC-ND-4.0.

The v3 production implementation is a review candidate in PR #447. Implementation
and successful technical checks do not activate it. The exact v3 policy remains
`REVIEW_REQUIRED`; no activation, Owner acceptance or upload decision is created.
All v1/v2 policy and schema bytes remain frozen, and the default v2 validator
keeps its strict original semantics.

## Explicit version selection

The existing `tools/qikvrt_zenodo_publish.py` selects v3 only for
`qikvrt_zenodo_publication_manifest_v3`. It requires the same exact metadata,
files, source head, proof and detached Owner authorization as v2, plus a detached
`contract_activation` identity. There is no fallback between versions. The v3
proof permits only `machine_proof_complete=true` in `completion_claims`.
Both values of an embedded upload-authorization field are rejected.

`validate_publication_bundle_v3` validates readiness and exact upload closure.
Its normalized receipt still says upload authorization and production mutation
authority are false. Only the separate decisions can satisfy the effect gates.
The current PR447 package intentionally contains neither decision nor a live
publish request.

## Detached reviewed-contract activation

`contract_activation` has the existing identity shape
`{path,bytes,sha256,git_blob_sha}`; its file is repository-side and control-only.
The file uses schema `qikvrt_zenodo_v3_contract_activation_v1` and exactly:

- `decision=ACTIVATE_REVIEWED_V3_PRODUCTION_CONTRACT`;
- `principal={name: Ingolf Lohmann, type: NATURAL_PERSON}`;
- `contracts`: sorted exact identities of the eight frozen v1/v2/v3
  policy/schema controls, publisher, validator and `.github/CODEOWNERS`;
- `review`: Authority repository, positive PR/review/ruleset IDs, exact reviewed
  HEAD/TREE and reviewer login;
- `authorized_at`, `exact_statement` and its UTF-8 `statement_sha256`.

The canonical activation statement binds the canonical JSON SHA-256 of those
contract identities and the repository, PR number, reviewed head and review ID.
It contains no proof self-reference. The decision may follow review without
rewriting the proof bundle. Principal names and platform attestations are not
cryptographic or biometric natural-person identity proof.

Before any consumption ref or Zenodo call, the publisher reobserves the actual
Authority PR, individual review and named ruleset through the pinned GitHub REST
origin. It requires a merged exact-head Authority PR, an undismissed APPROVED
review by a Code Owner distinct from the PR author, and activation after review
and merge. The reviewed tree, unchanged contract blobs and merged ancestry must
be present in the frozen source and clean execution scope. The active main
ruleset must enforce Code-Owner review, at least one approval, stale-review
dismissal and last-push approval, without bypass actors or excluded refs.

CODEOWNERS resolution supports the repository's default `*`, exact paths and
directory-prefix rules, in last-matching-rule order. Other glob syntax fails
closed. Missing access to the native review or governance endpoints also blocks;
the implementation supplies no administrative credential or bypass.

## Separate exact-upload decision and recovery

The existing canonical `AUTHORIZE_EXACT_UPLOAD` decision remains unchanged.
It binds the final candidate return, canonical metadata, immutable proof SHA-256,
exact upload identities and frozen source head. Its timestamp must follow both
candidate return and detached contract activation. The activation and Owner
decision must not be uploaded or overlap other execution roles.

v3 evidence uses `qikvrt_zenodo_publication_evidence_v3` and additionally binds
the detached activation. Its schema must match the selected manifest version.
The recovery phases, create-only remote Git consumption ref, decision-derived
consumption key, inventory reconciliation and public byte-exact verification
reuse the existing publisher. Replay detection spans v1/v2/v3 evidence; changing
the manifest version does not create a fresh consumption scope.

## Candidate return and open boundaries

PR447 explicitly migrates the article, PDF, source/matrix/status/return/proof and
planned fileset to v3. The accompanying change notice binds the prior candidate
and describes the migration. The detached package manifest binds the final proof
and return hashes without a self-hash cycle. That delivery is not acceptance,
contract activation, Code-Owner approval or `AUTHORIZE_EXACT_UPLOAD`.

No Zenodo effect, consumption lock, authorization record, merge or general
`EFFECT_ACK_DONE` is performed by this implementation task. Actual exact-head
CI, independent review, enforced governance, detached activation, later exact
upload authorization and usable Authority capability remain separate predicates.
