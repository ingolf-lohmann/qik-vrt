<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. -->
# Canonical temporal memory attached to named clause evidence

The opt-in `qikvrt-canonical-clause-audit/v1` evidence profile connects the
fourteen-index example to the existing EAP consumer and temporal-memory model.
It adds no HTTP route, wire field, release state, executor or timer.

`src/qikvrt_canonical_clause_audit.py::verify_canonical_storage` receives the
original version-1 record chain, exact input bytes, trusted policy, authenticated
evaluator result, latest trusted record hash, evidence objects and trusted
predicate implementations. It recomputes the input SHA-256 and every referenced
evidence digest using the existing revision-03 canonicalizer. It requires exactly
one entry for each `c1` through `c14`, the policy's exact predicate for each ID,
typed OBSERVED/ANTICIPATED archives, and available provenance/evidence objects.
Every predicate must actually run and return the Boolean `True`. Absence,
exception, integer `1`, malformed digest, mismatching bytes or duplicate ID fails
closed. A bare `acknowledged` flag is not an accepted certificate.

The trusted policy's `canonical_storage` object contains exactly `schema`,
`audit_hash` and `predicates`. `predicates` maps all fourteen IDs to canonical
`sha256:` identifiers. `audit_hash` identifies an external evidence object with
exactly `schema`, `input_hash`, `past`, `future` and `clauses`. Each archive has
`status`, `payload` and `provenance_hash`; each clause has `id`, `predicate_hash`
and `evidence_hash`. The record's required evidence is exactly the audit, both
archive provenance objects and all clause evidence objects, deduplicated by hash.
The input hash concerns the proposed input bytes, not the audit or protocol
record; the audit contains no protocol or policy hash, avoiding a hash cycle.

The final authorization is the original
`qikvrt_effect_ack_wire.verify_release`. A policy containing `canonical_storage`
automatically selects this mandatory profile in that original consumer. A direct
consumer call without the exact bytes and trusted validators fails closed.
Passing clause checks alone cannot
replace authentication, trusted policy, chain/freshness checks, recomputed DONE
or any original release predicate. The function performs no target effect.
An independent effect readback remains a separate operation.

The fourteen labels do not define fourteen QIK-VRT specification clauses.
Each actual use must supply their source-bound meanings and audited validators.
A digest-keyed Python callback mapping does not authenticate that code or prove
its soundness. This mapping belongs to the trusted deployment boundary and must
not be accepted from request JSON. The unit-test predicates are synthetic
arithmetic fixtures, not production clause definitions or proof receipts.

`QIKVRTEffectAck.CanonicalClauseAudit` imports the original temporal-memory and
EAP models. Total `Fin 14` indexing prevents a repeated list entry from standing
in for another obligation. Its theorems establish every-index coverage,
rejection of a failed check, retention of original authorization, recorded and
recomputed DONE, and semantic conclusions conditional on evaluator soundness.
These model results do not verify SHA-256's implementation or the Python/Lean
refinement relation. They add no claim of physical retrocausality.

The source-bound starting point is Ingolf Lohmann's version-1.0.0 publication,
DOI 10.5281/zenodo.21711193, https://zenodo.org/records/21711193.
Its original nine protocol theorems and four formal claims remain unchanged.
The implementation profile uses the existing revision-03 wire adapter:
https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03.
This source repair does not assert complete discovery or adoption of all later
specifications, publication of a successor paper, or productive host admission.

Run `make conformance` for the required runtime controls and
`lake build QIKVRTEffectAck.CanonicalClauseAudit QIKVRTEffectAck.CanonicalClauseAuditAxiomAudit`
in `formalization/QIKVRT_Formalization_v2.0` with its pinned Lean 4.19.0 toolchain.
The original canonical-record profile and historical protocol hashes retain
their own encoding rules; the wire profile continues to use its existing JCS
projection. No migration between those distinct profiles is implicit.
