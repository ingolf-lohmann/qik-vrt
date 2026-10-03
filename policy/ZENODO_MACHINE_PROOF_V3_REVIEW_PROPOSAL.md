# Immutable proof readiness and detached upload authorization: v3 review proposal

Copyright 2026 Ingolf Lohmann. CC-BY-NC-ND-4.0.

This is a review candidate in PR #447. It does not activate a production policy,
authorize an upload, create an owner decision, or change the returned publication
candidate. The active v2 policy, both v2 schemas, and the historical v1 contracts
remain byte-for-byte unchanged.

## Exact defect and versioned correction

The v2 bundle schema and validator require
`completion_claims.zenodo_upload_authorized=true`. The publisher separately
requires an owner decision whose canonical `AUTHORIZE_EXACT_UPLOAD` statement
binds the SHA-256 of the exact bundle bytes. The PR447 publication candidate
truthfully contains `zenodo_upload_authorized=false`: it has not received that
decision. Flipping the flag after the decision changes the approved hash;
flipping it beforehand misstates authorization.

The proposed v3 bundle contains only `machine_proof_complete=true` in
`completion_claims`. It forbids either value of an embedded upload-authorization
flag. All other proof constraints remain: exact policy/schema bytes, complete
claim inventory and matrix, classification and wording, evidence references,
formal kernel receipts, boundary tests, changed-content chain, exact candidate
return, and exact upload-set closure.

The existing repository-side owner authorization is the intended later layer.
It already binds the returned candidate, canonical metadata, exact proof hash,
upload identities, principal, source head, allowed effects, and one-time remote
Git consumption ref. Writing that detached decision must not rewrite the frozen
proof bundle. Its hash stays identical before and after the decision.

## Implemented review surface and production boundary

`validate_prepublication_bundle` and the explicit CLI option
`--prepublication-v3` reuse the existing proof validator. They verify the proposed
v3 policy and schema and the frozen v2/v1 contracts. A successful result means
`prepublication_ready_review_required`; upload authorization and production
mutation authority remain false.

The production `validate_bundle` entry point and generic publisher retain their
strict v2 contract. A proposed v3 manifest is rejected before GitHub consumption
or Zenodo transport, even if a synthetic detached decision is present. Tests
use temporary fixtures; they are not an owner authorization record.

The PR447 v2 PDF, claim matrix, proof bundle, return receipt, metadata, and fileset
are preserved. Their existing v2 HOLD is not promoted to a v3 publication pass.
The v3 policy explicitly records `REVIEW_REQUIRED`, no owner activation, and no
production mutation authorization. No predecessor CI, kernel, credential, or
publication evidence transfers to a successor head.

## Required continuation after review

1. Obtain the separate owner/code-owner review of this versioned contract.
2. Activate reviewed production v3 support in the existing publisher, preserving
   the detached canonical decision and remote one-time consumption gate.
3. Migrate the publication package explicitly, update its visible change notice,
   regenerate proof and file hashes, and return the final exact package and
   immutable bundle SHA-256 to Ingolf Lohmann.
4. Obtain the later candidate-specific `AUTHORIZE_EXACT_UPLOAD` decision binding
   those final bytes. Do not edit the proof bundle after that decision.
5. Establish native evidence for the actual execution head and the required
   Authority capability before any authorized effect; verify public bytes and
   reciprocal repository evidence after an effect.

The independent live Authority credential delivery HOLD remains open. This
proposal supplies no credential, workflow dispatch, approval, merge, publication,
or reciprocal-pair acknowledgment.
