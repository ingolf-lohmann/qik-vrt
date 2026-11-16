# Effect Management Protocol (EMP) for Human-Authorized, Evidence-Bound Effects

Status: Internet-Draft candidate; work in progress; not submitted to IETF.
Author: Ingolf Lohmann
Date: 2026-11-10
Intended status: Experimental
Related: QIK-VRT Effect Acknowledgement Protocol (EAP), draft-lohmann-qikvrt-effect-ack-03.

## Abstract
This document proposes an Effect Management Protocol (EMP) that coordinates human-authorized objectives through planning, execution, observation, failure recovery and independent effect acknowledgement. EMP complements EAP; it does not replace EAP authorization, evidence, or effect verification.

## 1. Introduction
An effect acknowledgement protocol can establish whether an effect was independently verified but does not by itself prescribe how to attain an authorized effect. EMP defines the missing orchestration lifecycle while retaining human decision authority and fail-closed semantics.

## 2. Terminology
Principal: human authority specifying objectives and permissible effects.
Objective: desired measurable effect with acceptance predicate.
Executor: constrained agent acting within delegated authority.
Evidence: attributable, integrity-bound observation of actual state.
EAP: independent acknowledgement and verification layer.
Writer epoch: monotonic fencing identifier for a single effect writer.

## 3. Objective envelope
Each objective MUST bind: objective_id; principal_id; authorization reference; desired effect and measurable acceptance predicate; scope and target; allowed operations; forbidden operations; deadline; resource budget; policy version; immutable evidence references; stop/revoke conditions; idempotency key; writer epoch. Optional dependencies and compensation plan MUST be explicitly typed. Missing required authorization MUST prevent execution.

## 4. State machine
PROPOSED -> AUTHORIZED -> PLANNED -> EXECUTING -> OBSERVING.
OBSERVING -> VERIFIED only on independently validated EAP acknowledgement.
OBSERVING -> REPAIRING when a recoverable failure is diagnosed.
REPAIRING -> EXECUTING only after bounded corrective authorization and updated evidence.
Any active state -> BLOCKED on unresolved external dependency, or -> ABORTED on revocation/stop.
BLOCKED is not VERIFIED. A durable blocked state records reason, unblock predicate and next safe action.

## 5. Normative requirements
EMP-1: An executor MUST NOT perform effects outside the principal's authorization.
EMP-2: EMP MUST NOT report success unless the acceptance predicate and EAP verification both hold against independently observed state.
EMP-3: Implementations MUST use durable journals, idempotency keys and fencing to reject stale concurrent writers.
EMP-4: Implementations MUST preserve causally relevant evidence and must distinguish proposed, attempted, observed and verified states.
EMP-5: Retries MUST be bounded and must not silently bypass safety or governance gates.
EMP-6: A blocked dependency MUST NOT unnecessarily block independent ready objectives.
EMP-7: Cancellation and revocation MUST be checked before effectful execution and at defined checkpoints.
EMP-8: Irreversible operations MUST have explicit principal authorization and applicable governance approval.
EMP-9: For CI/CD failures in QIK-VRT integrations, TEMDD diagnosis and regression evidence MUST precede correction acceptance.
EMP-10: The protocol MUST NOT treat an LLM statement, a successful API call, or a repository commit as proof of real-world effect.

## 6. Example exchange (illustrative, not a finalized wire format)
Principal authorizes an objective to regenerate a broken document bundle and validate hashes.
EMP plans deterministic generation and independent readback.
Executor generates bundle, captures exact input revision and SHA-256.
Observer checks file bytes and source binding; EAP validates policy and acceptance.
Only then EMP marks VERIFIED. Otherwise EMP records REPAIRING or BLOCKED, with evidence.

## 7. Security and privacy considerations
Least privilege; replay prevention; writer fencing; authenticated principal identity; evidence integrity; data minimization; consent for personal digital twins; auditability; separation of duty; bounded automated actions; revocation; denial-of-service resistance.

## 8. IANA considerations
This draft requests no IANA action.

## 9. Open issues for IETF preparation
Define canonical serialization and wire messages; interoperable error codes; authentication and delegation model; EAP reference version and cryptographic evidence binding; threat model; protocol state diagrams; normative RFC references; conformance vectors; formal machine-readable schema; reference implementation; independent review.
Do not submit before patent/public-disclosure review of potentially patentable hardware or protocol inventions.

## 10. Publication gates
Convert to RFCXML v3; run xml2rfc and idnits; validate references and Internet-Draft boilerplate; obtain human publication authorization; upload through the official IETF Datatracker submission process; read back the published draft identifier and content digest.

This document is a proposal, not an implemented protocol, IETF consensus, standards-track RFC, or production deployment claim.
