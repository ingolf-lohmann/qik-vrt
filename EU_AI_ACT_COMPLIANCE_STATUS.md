# EU AI Act compliance status — QIK-VRT

**Status as of 2026-10-21: CLASSIFICATION OPEN · COMPLIANCE NOT ESTABLISHED**

This file is the prominent entry point for the QIK-VRT assessment prompted by Commission Implementing Decision (EU) 2026/2274 and harmonised standard EN 18286:2026. It is a controlled engineering assessment, not a declaration of conformity, legal opinion, certification, or proof that the product is a high-risk AI system.

## Decision that must not be skipped

Providing Single Sign-On (SSO) or an authentication method does **not by itself** make a product a high-risk AI system under Regulation (EU) 2024/1689. Classification depends on the actual intended purpose, the AI Act definition of an AI system, the provider/deployer role, and the relevant Article 6 / Annex I / Annex III criteria. In particular, Annex III point 1(a) excludes AI systems intended to be used for biometric verification whose sole purpose is to confirm that a specific natural person is the person they claim to be. This exclusion is conditional on the actual function and does not settle the classification of other QIK-VRT functionality.

QIK-VRT must therefore document what it itself provides and controls, versus an operating-system authenticator, identity provider, browser, OAuth/OIDC service, or other external component. No conclusion is made here that QIK-VRT is or is not high-risk.

## Immediate repository actions

1. Use [the EN 18286 readiness assessment](docs/regulatory/EN_18286_2026_QMS_READINESS.md) to record the intended purpose, system boundary, role allocation, classification rationale, and Article 17 QMS gap assessment.
2. Use [the node rollout and evidence procedure](docs/regulatory/NODE_ROLLOUT_CHECKLIST.md) for any authorized node-level adoption. A repository commit does not prove that a connected node has received, read, or implemented the documents.
3. Record every claim against an artifact, version, owner, verification method, and result. Unknowns remain OPEN; do not convert missing evidence into PASS.
4. Obtain review from a qualified EU AI Act legal/compliance specialist and the responsible product owner before making a classification or conformity claim.

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

**No compliance PASS is claimed by this file or by the existence of these templates.**