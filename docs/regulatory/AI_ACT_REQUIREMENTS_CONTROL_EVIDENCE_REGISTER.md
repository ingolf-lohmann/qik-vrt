# QIK-VRT — AI Act requirements, controls, and evidence register

**Revision date:** 2026-10-21  
**Change authority:** Product Owner approval was explicitly communicated in the project conversation on 2026-10-21. This records that instruction; it is not a cryptographic signature or independent identity-verification record.  
**Regulatory classification:** `MORE_FACTS_REQUIRED` — Product Owner approval does not substitute for the legal classification decision or qualified legal review.  
**Evidence rule:** A source file or a green test is evidence only for the exact property it actually checks. No PASS is inferred from documentation, source presence, CI status on another commit, or a transport acknowledgement.

## 1. Applicability and disposition vocabulary

- **CONDITIONAL** — requirement applies only if the cited legal trigger is established.
- **OPEN** — facts or accountable decision are missing.
- **PARTIAL** — repository artefact describes a control, but implementation/deployment effectiveness is not independently evidenced.
- **NOT_EVIDENCED** — no qualifying implementation, test, or operational evidence was identified in this workstream.
- **N/A** — permitted only after a reasoned, signed applicability decision with supporting facts; not used as a shortcut.

This register maps obligations to controls and evidence needed. It is not a completed conformity assessment and does not replace the full AI Act, applicable implementing acts, notified-body route where relevant, or the licensed EN 18286:2026 text.

## 2. Applicability gate — required before final legal assignment

| Gate | Decision required | Existing repository lead | Evidence to close | Current state |
|---|---|---|---|---|
| G-01 | Article 3(1): identify whether each scoped product/feature is an AI system | `src/qikvrt_personal_auth.py`; product capability specifications | Versioned function inventory, model-vs-deterministic component boundary, documented Article 3(1) analysis | OPEN |
| G-02 | Intended purpose and reasonably foreseeable misuse | `docs/regulatory/system-boundary.md` | Product Owner-approved versioned statement and prohibited-use list tied to release/configuration | PARTIAL — approval communicated; durable signed artifact not established |
| G-03 | Legal entity and role for each edition/deployment | System-boundary and product documentation | Entity/contract/labeling/market-placement evidence; provider/deployer/importer/distributor/product-manufacturer role decision | OPEN |
| G-04 | Article 6(1) / Annex I product-safety route | No conclusive product-law mapping identified | Applicable product legislation and intended-purpose analysis | OPEN |
| G-05 | Article 6(2) / Annex III use case | No evidence that SSO alone triggers Annex III | Criterion-by-criterion Annex III analysis against actual features, context and intended purpose | OPEN |
| G-06 | Biometric scope, including Annex III 1(a) distinction | `spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md` says verification is delegated to IdP/device | Runtime data-flow test, configuration evidence, contract review, exact 1:1 verification vs identification/categorisation determination | PARTIAL |
| G-07 | Classification and any resulting conformity-assessment route | `docs/regulatory/classification-memorandum.md` | Signed decision with evidence references and qualified legal review | OPEN — `MORE_FACTS_REQUIRED` |

**Rule:** Do not mark any conditional obligation N/A, and do not claim Article 17 applicability or non-applicability, until G-01–G-07 are closed by accountable reviewers.

## 3. Requirement-to-control traceability

| Requirement / trigger | Intended control and implementation mapping | Required test evidence | Required operational evidence | Current evidence disposition |
|---|---|---|---|---|
| AI Act Art. 9 — risk management, if high-risk | Establish lifecycle risk process, hazard/use-case register, mitigation owners, residual-risk approval. No complete implementation artefact evidenced by this register. | Risk-control traceability tests; mitigation effectiveness and residual-risk tests against release-bound requirements | Versioned risk register, incident/review updates, signed residual-risk decisions | CONDITIONAL; NOT_EVIDENCED |
| Art. 10 — data and data governance, if applicable high-risk system | Inventory training/validation/testing data and data-processing boundaries; justify quality/relevance and governance appropriate to system | Data quality, representativeness, leakage/bias and provenance checks as applicable to actual system | Dataset/version lineage, access logs, retention and change records | CONDITIONAL; NOT_EVIDENCED |
| Art. 11 + Annex IV — technical documentation, if high-risk | Versioned technical file bound to exact product/release and conformity route | Completeness/consistency checks against implementation and release manifest | Approved technical-file revisions and retention/access controls | CONDITIONAL; PARTIAL — boundary/memo are preliminary only |
| Art. 12 — record-keeping/logging, if high-risk | Identify legally required event records and logging capabilities; do not conflate QIK-VRT TEMDD receipts with full AI Act logging coverage | Tests for event coverage, timestamp/identity integrity, retention, export, access controls and failure modes | Production log-retention configuration, access review, sampled read-back and incident evidence | CONDITIONAL; NOT_EVIDENCED for statutory coverage |
| Art. 13 — transparency/instructions, if high-risk | User-facing instructions, capabilities/limitations, intended purpose, risks and human oversight information | Content-to-build traceability and usability/comprehension checks | Released instructions, locale/version inventory, change approval | CONDITIONAL; NOT_EVIDENCED |
| Art. 14 — human oversight, if high-risk | Define oversight measures, intervention/override, stop/reversal and automation-bias safeguards appropriate to use | Human-oversight scenarios, escalation/override and fail-safe tests | Training records, role/access evidence, monitoring and incident drills | CONDITIONAL; NOT_EVIDENCED |
| Art. 15 — accuracy, robustness, cybersecurity, if high-risk | Define measurable requirements and threat model for the actual intended purpose | Reproducible accuracy/robustness/security test reports tied to exact release and acceptance thresholds | Vulnerability monitoring, patching, incident response, production metrics and change records | CONDITIONAL; NOT_EVIDENCED |
| Art. 16 — provider obligations, if provider of high-risk system | Assign accountable provider; satisfy applicable design, conformity, registration, corrective-action and post-market obligations | Release-gate evidence and applicable conformity-assessment records | Signed EU declaration of conformity where required, registration where required, corrective-action and regulator-contact records | CONDITIONAL; NOT_EVIDENCED |
| Art. 17 — QMS, if provider of high-risk system | Establish controlled QMS covering applicable statutory elements; assess EN 18286:2026 clauses using licensed text | Internal audit, process conformance, corrective-action closure and management-review evidence | Approved QMS, controlled procedures, records, management reviews and audit trail | CONDITIONAL; NOT_EVIDENCED; readiness template is not a QMS |
| Art. 18 — document retention, if applicable provider | Define retention of required documentation, declaration and authority-access material | Retention/access/retrieval tests | Retention schedule, access controls and retrievable records | CONDITIONAL; NOT_EVIDENCED |
| Art. 19 — automatically generated logs, if applicable provider | Determine which logs must be retained and for how long under applicable rules | Retention expiry, export, integrity and access tests | Production retention configuration and sample read-back | CONDITIONAL; NOT_EVIDENCED |
| Art. 20 — corrective actions and duty to inform, if applicable provider | Issue triage, nonconformity, correction, withdrawal/recall and notification workflow as legally applicable | Tabletop/functional exercises with timestamped records | Incident register, corrective-action closure and notifications where triggered | CONDITIONAL; NOT_EVIDENCED |
| Art. 21–22 — cooperation / authorised representative, where applicable | Map authority requests, cooperation and representative obligations by role | Retrieval and escalation exercise | Named contacts, authorisation and request-response records | CONDITIONAL; NOT_EVIDENCED |
| Art. 26 — deployer obligations, if QIK-VRT is a deployer of a high-risk system | Determine deployer duties separately from provider duties; implement instructions, human oversight, input-data and monitoring duties where applicable | Deployment/configuration validation and oversight tests | Deployment records, monitoring, incident and suspension records | CONDITIONAL; role not determined |
| Art. 27 — fundamental-rights impact assessment, where applicable | Assess whether the deployer/use falls within Article 27 triggers; record rationale | Review checklist validation | Completed assessment and updates where required | CONDITIONAL; NOT_EVIDENCED |
| Art. 40 — harmonised standards presumption, if relying on EN 18286:2026 | Map each applicable requirement to the exact covered standard clauses; standard use remains voluntary | Clause-level evidence and gap closure, independently reviewed | Licensed standard/version record, applicability rationale and controlled evidence set | Candidate route only; clause-by-clause mapping NOT_EVIDENCED |
| Art. 43 / applicable conformity route | Select correct procedure after classification and system/role determination | Required assessment records and test reports for chosen procedure | Completed conformity-assessment file; notified-body evidence if required | OPEN; NOT_EVIDENCED |
| Art. 49 / applicable registration | Determine whether EU database registration is required for the final category and role | Registration-field consistency review | Actual registration receipt/identifier, if required | OPEN; NOT_EVIDENCED |
| Security and identity boundary (supporting control; not itself proof of AI Act classification) | OIDC authentication is distinct from model API entitlement; delegated device/IdP biometric processing must be verified in the actual configuration | Authentication/authorization negative tests, token validation, tenant and privilege isolation, data-flow tests | Production configuration, key/issuer/audience rotation evidence, access review and incident logs | Source-level description exists; release/runtime evidence NOT_EVIDENCED |
| Multi-node governance (supporting operational control) | Registry-scoped authorized nodes only; no global scanning, self-propagation or unauthorised foreign writes | Tests for registry filtering, identity binding, denial of unregistered destinations, exact hash/read-back comparison | Per-node authorization, target-bound receipts, fresh health/ack/renewal read-backs | NOT_EVIDENCED as current fleet-wide rollout; current registry index reports one node STALE and three HTTP 404 lifecycle references |

## 4. Evidence contract for every claimed PASS

Each control must have a separate record containing at least:

1. Requirement ID and legal applicability rationale.
2. Control owner and implementation location (path, symbol, configuration identifier, or operational procedure).
3. Exact source commit SHA and tree SHA; build/release identity where applicable.
4. Test ID, exact test command/workflow run and job, result, timestamps, logs/artifact identifiers and cryptographic digests.
5. Production environment/configuration identity, observation time, source of evidence and independent read-back where the claim is operational.
6. Known limitations, exceptions, residual risk, approver and review date.

A test PASS is bounded to the tested code/configuration and does not prove deployed operation. A repository commit proves repository state only. A node acknowledgement is not a verified effect unless fresh node-side read-back matches the target and expected hash. A successful node does not prove fleet-wide completion.

## 5. Required next gates

- [ ] Attach a durable Product Owner-approved intended-purpose statement and exact product/release scope.
- [ ] Close G-01–G-07 with accountable product and qualified legal reviewers.
- [ ] Obtain and review the licensed EN 18286:2026 text clause-by-clause if using that standard.
- [ ] Implement controls required by the signed applicability decision; create a control-to-code/test/operations evidence bundle per row.
- [ ] Run tests against the exact candidate commit and retain actual workflow/job receipts and artifacts.
- [ ] Verify deployment/read-back per authorised node. Do not infer fleet coverage from the registry count or a local repository write.
- [ ] Complete independent conformity assessment and all applicable registration/declaration steps before making any conformity claim.

## 6. Current disposition

**Overall: HOLD — NO FULL CONFORMITY CLAIM.**  
**Classification: MORE_FACTS_REQUIRED.**  
**Implementation evidence: incomplete. Test evidence: not linked comprehensively to requirement IDs. Operational evidence: not established fleet-wide.**  
**Main merge, node distribution and full conformity must each be separately evidenced; none follows from Product Owner approval or this register.**

## 7. Proposed cluetec reciprocal audit pilot

The owner-authorized requirement is prepared in
`state/work_units/QIKVRT_CLUETEC_RECIPROCAL_AI_ACT_PILOT_20261023_V1.json`
with its human-readable contract at
`docs/regulatory/pilots/cluetec/REQUIREMENTS_DE.md`.
It preserves this register and the existing EAP, native runtime, review and
continuation contracts. The package specifies 42 requirements and 42 planned
acceptance cases; it does not establish implementation, partner acceptance,
neutral human review, legal conformity or authority submission. Classification
remains MORE_FACTS_REQUIRED and compliance remains COMPLIANCE NOT ESTABLISHED.
The current official legal inventory must be resolved through every applicable
subdivision before an operational coverage or conformity conclusion.
