# IETF protocol disposition: truthfulness / epistemic-status result

Date: 2026-10-03
Base protocol: `draft-lohmann-qikvrt-effect-ack-03`

## Decision

A revision of the core EFFECT_ACK wire protocol is **not required** by the QIK-VRT truthfulness invariant.

The active base draft already states that EFFECT_ACK:
- separates transport receipt from downstream-effect authorization;
- binds policy and evidence references;
- does not establish the truth of external evidence; and
- requires a consumer to validate rather than trust evidence-reference presence.

Changing the closed version-1 wire record solely to encode the new truthfulness interpretation would therefore mix two different responsibilities and create unnecessary version churn.

A **separate companion Internet-Draft is technically useful** because the new result concerns epistemic-status claims made by cognition systems, not the authorization state of a downstream effect.

## Companion scope

Candidate name:

`draft-lohmann-qikvrt-epistemic-status-00`

The companion profile defines:
1. a closed vocabulary for epistemic claim status;
2. provenance/evidence bindings for claims;
3. the invariant that a claim MUST NOT be represented with a stronger status than its bound evidence permits;
4. the distinction between object truth and epistemic truthfulness;
5. self-application to claims emitted by the evaluator itself; and
6. mapping to EFFECT_ACK without changing EFFECT_ACK version 1.

## Core-protocol non-change

No change is proposed to the five EFFECT_ACK v1 states or their DONE predicate.

The profile is additive and MUST NOT be interpreted as IETF endorsement, consensus, or proof that all assertions made by an implementation are true.

## Publication status

Repository staging candidate only. Not submitted to the IETF Datatracker by this commit.
