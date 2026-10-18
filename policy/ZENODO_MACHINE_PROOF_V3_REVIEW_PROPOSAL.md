# Immutable proof readiness and detached upload authorization: v3 review proposal

Copyright 2026 Ingolf Lohmann. CC-BY-NC-ND-4.0.

This remains a review candidate in PR #447. The versioned production implementation and explicit candidate migration are now materialized for review. They do not activate v3, authorize an upload or create either detached decision. The active v2 policy, both v2 schemas, and the historical v1 contracts
remain byte-for-byte unchanged.

## Exact defect and versioned correction

The v2 bundle schema and validator require
`completion_claims.zenodo_upload_authorized=true`. The publisher separately
requires an owner decision whose canonical `AUTHORIZE_EXACT_UPLOAD` statement
binds the SHA-256 of the exact bundle bytes. The PR447 publication candidate
previously truthfully contained `zenodo_upload_authorized=false`: it had not received that decision. The explicitly migrated v3 candidate contains no embedded upload-authority field. Flipping the flag after the decision changes the approved hash;
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

The default `validate_bundle` entry point retains its strict v2 contract. The
existing publisher now has an explicit versioned v3 manifest route and matching
v3 evidence/recovery binding; neither manifest nor proof schema falls back to a
different version. `validate_publication_bundle_v3` preserves readiness-only
semantics. Every v3 effect additionally requires detached reviewed-contract
activation, live native exact-head Code-Owner review/governance readback, and the
later unchanged canonical `AUTHORIZE_EXACT_UPLOAD` decision. See
`policy/ZENODO_MACHINE_PROOF_V3_PRODUCTION.md` for the exact interface.

The PR447 package is explicitly migrated, including article/PDF, claim/source
bindings, change notice, status, proof, return and exact planned fileset. Its
review, activation and exact-upload HOLD is not promoted to an effect pass.
The policy/schema bytes and REVIEW_REQUIRED proposal remain unchanged. No
predecessor CI, kernel, credential or publication evidence transfers to the new
head. Synthetic decisions exist only in temporary regression fixtures.

## Required continuation after review

1. Obtain the separate owner/code-owner review of this versioned contract.
2. Record the separate reviewed-contract activation for the exact publisher, validator and policy/schema bytes; native Authority review and Code-Owner enforcement must be observable before any effect.
3. Verify the explicitly migrated final package and its regenerated bindings on the actual new Exact Head. Return its exact bytes and immutable bundle SHA-256 to Ingolf Lohmann.
4. Obtain the later candidate-specific `AUTHORIZE_EXACT_UPLOAD` decision binding
   those final bytes. Do not edit the proof bundle after that decision.
5. Establish native evidence for the actual execution head and the required
   Authority capability before any authorized effect; verify public bytes and
   reciprocal repository evidence after an effect.

The independent live Authority credential delivery HOLD remains open. This
proposal supplies no credential, workflow dispatch, approval, merge, publication,
or reciprocal-pair acknowledgment.
