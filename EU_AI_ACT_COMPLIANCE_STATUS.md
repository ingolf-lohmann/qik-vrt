# EU AI Act compliance status — QIK-VRT

**Status as of 2026-10-21: CLASSIFICATION OPEN · COMPLIANCE NOT ESTABLISHED**

This file is the prominent entry point for the QIK-VRT assessment prompted by Commission Implementing Decision (EU) 2026/2274 and harmonised standard EN 18286:2026. It is a controlled engineering assessment, not a declaration of conformity, legal opinion, certification, or proof that the product is a high-risk AI system.

## Decision that must not be skipped

Providing Single Sign-On (SSO) or an authentication method does **not by itself** make a product a high-risk AI system under Regulation (EU) 2024/1689. Classification depends on the actual intended purpose, the AI Act definition of an AI system, the provider/deployer role, and the relevant Article 6 / Annex I / Annex III criteria. In particular, Annex III point 1(a) excludes AI systems intended to be used for biometric verification whose sole purpose is to confirm that a specific natural person is the person they claim to be. This exclusion is conditional on the actual function and does not settle the classification of other QIK-VRT functionality.

QIK-VRT must therefore document what it itself provides and controls, versus an operating-system authenticator, identity provider, browser, OAuth/OIDC service, or other external component. No conclusion is made here that QIK-VRT is or is not high-risk.

## Current evidence-based classification result

The repository specification `spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md` describes OIDC authentication as separate from model/API entitlement and says passkeys/WebAuthn and biometric verification are delegated to the registered device/identity provider, with no biometric templates or modality assertions collected by the described integration. These are documented design claims, not independent proof of every runtime configuration.

The preliminary result is **MORE_FACTS_REQUIRED**. The system boundary and classification memorandum now record these facts, limits, and closure requirements:
- [System boundary and intended-purpose record](docs/regulatory/system-boundary.md)
- [AI Act classification memorandum](docs/regulatory/classification-memorandum.md)
- [Requirement-to-control and evidence register](docs/regulatory/AI_ACT_REQUIREMENTS_CONTROL_EVIDENCE_REGISTER.md)

The current node index generated on 2026-10-18 records one node as `STALE`, with health, acknowledgement, and renewal evidence unavailable. Node rollout remains unverified; no remote-node persistence is claimed.

## Immediate repository actions

1. Use [the EN 18286 readiness assessment](docs/regulatory/EN_18286_2026_QMS_READINESS.md) to record the intended purpose, system boundary, role allocation, classification rationale, and Article 17 QMS gap assessment.
2. Use [the node rollout and evidence procedure](docs/regulatory/NODE_ROLLOUT_CHECKLIST.md) for any authorized node-level adoption. A repository commit does not prove that a connected node has received, read, or implemented the documents.
3. Record every claim against an artifact, version, owner, verification method, and result. Unknowns remain OPEN; do not convert missing evidence into PASS.
4. Product Owner approval was communicated on 2026-10-21; durable signed approval and release binding remain to be recorded. Obtain qualified EU AI Act legal/compliance review before making a classification or conformity claim. The requirement register currently remains HOLD with implementation, test and operational evidence gaps.

## Regulatory references

- Commission Implementing Decision (EU) 2026/2274, Official Journal of the European Union, 14 October 2026: https://eur-lex.europa.eu/eli/dec_impl/2026/2274/oj
- Regulation (EU) 2024/1689 (AI Act), consolidated/current versions should be checked at decision time: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- European Commission announcement on EN 18286:2026, 19 October 2026: https://digital-strategy.ec.europa.eu/de/library/first-harmonised-standard-supporting-ai-act-published-official-journal
- CEN-CENELEC standard information: https://www.cencenelec.eu/

EN 18286:2026 is a voluntary harmonised route to a presumption of conformity only for the requirements it covers. It does not, by itself, prove overall AI Act conformity, correct product classification, or compliance with requirements outside its scope. If Article 17 applies, the provider's QMS obligation is mandatory even where use of this particular standard is voluntary.

## Evidence status

| Control | Current status | Required closure evidence |
|---|---|---|
| Intended purpose and product boundary | OPEN | Approved intended-purpose statement and architecture/data-flow boundary |
| AI-system qualification | OPEN | Documented assessment against Article 3(1), based on actual functionality |
| Provider/deployer/importer/distributor roles | OPEN | Named legal entities and role rationale |
| Article 6 and Annex I/III classification | OPEN | Signed classification memorandum with each applicable criterion assessed |
| Biometric processing / identity verification boundary | OPEN | Data-flow and component responsibility evidence; identify 1:1 verification versus identification |
| Article 17 QMS applicability | OPEN | Classification/role decision and documented applicability analysis |
| EN 18286 gap assessment | NOT STARTED | Licensed standard reviewed clause-by-clause by accountable owner; no standard text copied into this repository |
| Risk management, data governance, technical documentation, logging, human oversight, accuracy/robustness/cybersecurity | OPEN | Applicable requirement-by-requirement evidence and test records |
| Post-market monitoring, serious-incident handling, corrective action | OPEN | Approved procedures, responsibilities, records, and exercised tests |
| Node rollout and persistence | NOT VERIFIED | Node-specific receipt plus read-back and hash verification for every explicitly authorized node |
| Independent review / conformity assessment | OPEN | Review outcome and any applicable conformity-assessment records |

## Controlled gap-closure candidate — 2026-10-22

The Principal instructed implementation of the remaining gaps and continuity
across internal and external change. The existing evidence gate now supports
typed source/context bindings, rejects changed bytes, mismatched assessment
contexts, expired/future receipts and unsupported N/A dispositions, and retains
unresolved original artifacts as OPEN. Its captured context is a baseline, not
live model/host discovery. A successful audit process does not close its OPEN
findings or establish conformity.

- [Controlled risk, data, oversight, retention and change procedure](docs/regulatory/CONTROLLED_ASSESSMENT_PROCEDURE.md)
- [Initial exact-subject evidence and risk inventory](docs/regulatory/AI_ACT_EVIDENCE_BUNDLE.json)
- [Captured assessment context](docs/regulatory/ASSESSMENT_CONTEXT.json)

Documentation and binding validation are implemented candidate contributions.
The actual model/data/deployment inventory, original HTML versions, accountable
classification and role decisions, control-effectiveness and operational
acceptance remain OPEN. No signed acceptance, live native execution, statutory
QMS acceptance or conformity assessment is inferred from these additions.

**No compliance PASS is claimed by this file or by the existence of these templates.**
