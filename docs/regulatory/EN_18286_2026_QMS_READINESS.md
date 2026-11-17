# EN 18286:2026 / EU AI Act — QIK-VRT readiness assessment

**Document status:** initial assessment template; not approved; classification OPEN  
**Assessment date:** 2026-10-21  
**Accountable owner:** to be appointed by the product/provider entity  
**Review cadence:** on material product change and at least quarterly until classification closes  
**Authority:** this document does not replace the full legal text or the licensed standard.

## 1. Purpose and legal baseline

Commission Implementing Decision (EU) 2026/2274 published the reference to EN 18286:2026, *Artificial intelligence — Quality management system for EU AI Act regulatory purposes*, in the Official Journal on 14 October 2026. The decision entered into force on publication. Under AI Act Article 40, conformity with a cited harmonised standard supports a presumption of conformity only for the requirements covered by that standard.

AI Act Article 17 requires providers of high-risk AI systems to establish a quality management system. The use of EN 18286:2026 is voluntary; the applicable statutory obligation is not made voluntary by choosing not to use the standard. Neither this readiness assessment nor a repository workflow constitutes certification or proves conformity.

Official texts:
- Decision: https://eur-lex.europa.eu/eli/dec_impl/2026/2274/oj
- AI Act: https://eur-lex.europa.eu/eli/reg/2024/1689/oj
- Commission explanation: https://digital-strategy.ec.europa.eu/de/library/first-harmonised-standard-supporting-ai-act-published-official-journal

## 2. Classification is a prerequisite, not an assumption

SSO is an architecture pattern, not a high-risk category in itself. Before deciding whether Article 17 and EN 18286 apply, the responsible entity must complete and approve the following.

### 2.1 Intended purpose and system boundary

- [ ] Describe each intended use and reasonably foreseeable misuse.
- [ ] Identify the actual AI-enabled functions, if any; distinguish deterministic software, identity federation, authentication, authorization, policy gating, and AI inference.
- [ ] Identify the product/version and whether QIK-VRT is itself placed on the market or put into service as an AI system.
- [ ] Draw a data-flow / trust-boundary diagram covering browser, operating system, identity provider, OAuth/OIDC endpoints, QIK-VRT services, storage, model/API providers, and downstream consumers.
- [ ] Identify who chooses the means and purpose of processing, who controls updates, and who makes the system available under which name.
- [ ] Distinguish local 1:1 biometric verification (confirming a claimed identity) from remote biometric identification, categorisation, or other biometric processing.
- [ ] Record the data categories, including whether biometric data are processed by QIK-VRT or only by a separate device/identity provider. Do not infer this from UI wording alone.

### 2.2 Legal classification memorandum

The owner and qualified reviewer must assess, with reasons and source citations:

1. AI Act Article 3(1): whether the actual product meets the AI-system definition.
2. Article 6 and Annex I: whether any product-safety-law route applies.
3. Article 6(2) and Annex III: whether a listed use case applies, including the exact function and intended purpose.
4. Annex III point 1(a): whether a biometric function is only 1:1 verification of a claimed identity and whether the stated exclusion applies to the actual system.
5. Any other relevant AI Act provisions, exclusions, role-specific obligations, and transitional/application dates.
6. Whether the entity is a provider, deployer, importer, distributor, product manufacturer, or more than one role.
7. Whether any material modification or change of intended purpose affects the role/classification.

**Decision field:** OPEN until an accountable owner signs the memorandum and a qualified reviewer records the conclusion. Possible outcomes: HIGH_RISK, NOT_HIGH_RISK_ON_RECORDED_FACTS, or MORE_FACTS_REQUIRED. The last two outcomes must not be represented as blanket exemption from other laws or AI Act obligations.

## 3. Article 17 / EN 18286 QMS workstream

If the approved classification concludes that QIK-VRT is a provider of a high-risk AI system, establish and operate the applicable QMS. The following is a starter control register, not a substitute for reviewing the complete EN 18286 text.

| ID | Workstream | Minimum evidence expected | State |
|---|---|---|---|
| QMS-01 | Governance and accountability | Approved quality policy, accountable roles, authority, resources, management review | OPEN |
| QMS-02 | Regulatory compliance strategy | Applicability register, standards register, conformity-assessment route, change monitoring | OPEN |
| QMS-03 | Design and development | Requirements, design reviews, traceability, architecture and interface records | OPEN |
| QMS-04 | Risk management | Hazard/use-case register, risk evaluation, mitigations, residual-risk approval | OPEN |
| QMS-05 | Data governance | Data provenance, suitability, quality, preparation, bias and limitation controls where applicable | OPEN |
| QMS-06 | Verification and validation | Version-bound plans, datasets/test fixtures, acceptance criteria, reproducible results, independent review | OPEN |
| QMS-07 | Configuration and change control | Approved changes, impact analysis, review, rollback/recovery, release identity | OPEN |
| QMS-08 | Supplier and component control | Identity-provider/model/provider inventory, contracts, versioning, security and change monitoring | OPEN |
| QMS-09 | Technical documentation | System description, intended purpose, limitations, design, evaluation, instructions and traceability | OPEN |
| QMS-10 | Logging and records | Defined event scope, retention, access, integrity, privacy controls, and evidence retrieval | OPEN |
| QMS-11 | Human oversight | Operator roles, intervention mechanisms, limitations, training, override and escalation records | OPEN |
| QMS-12 | Accuracy, robustness and cybersecurity | Applicable requirements, threat model, test results, vulnerabilities and corrective actions | OPEN |
| QMS-13 | Post-market monitoring | Monitoring plan, signals, metrics, review cadence, owner and escalation thresholds | OPEN |
| QMS-14 | Serious incidents and corrective action | Triage, reporting decision tree, deadlines, root-cause analysis, CAPA and effectiveness check | OPEN |
| QMS-15 | Complaints and communication | Intake, traceability, response ownership, customer/operator communication records | OPEN |
| QMS-16 | Internal audit and management review | Audit schedule, findings, decisions, actions, due dates and closure evidence | OPEN |
| QMS-17 | Document and record control | Versioning, approval, access, retention, integrity and supersession | OPEN |
| QMS-18 | Competence and training | Role-based competence criteria, training records, evaluation and renewal | OPEN |

For every control, record: owner, applicability rationale, procedure ID/version, implementation artifact, verification method, result, exceptions, approver, approval date, and next review date. A control is PASS only when the evidence has been inspected against a predefined acceptance criterion; a document existing in Git is not proof that a process operates effectively.

## 4. Required evidence bundle

Create and maintain these records as the assessment proceeds:

- intended-purpose.md — approved use, non-use, limitations, target users, deployment contexts.
- system-boundary.md — components, data flows, trust boundaries, external providers, AI functions.
- classification-memorandum.md — Article 3/6, Annex I/III, roles, rationale, reviewer sign-off.
- requirements-traceability.csv — each applicable legal requirement mapped to implementation and test evidence.
- risk-register.csv — risk, cause, affected party, severity/likelihood rationale, mitigation, residual risk, owner.
- verification-validation-plan.md and versioned result records.
- change-control.md — approval, impact assessment, test gates, rollback, release linkage.
- post-market-monitoring-plan.md — signals, owners, cadence, thresholds, incident and corrective-action links.
- supplier-component-register.csv — identity provider, browser/OS APIs, model/API services, versions and trust assumptions.
- training-and-competence.md, internal-audit.md, and management-review.md.

Do not populate these with invented approvals, test outcomes, owners, or deployment facts. Use OPEN, NOT_APPLICABLE_WITH_RATIONALE, IN_PROGRESS, PASS_WITH_EVIDENCE, or FAIL; every PASS_WITH_EVIDENCE must link to immutable/versioned evidence.

## 5. Technical implications for QIK-VRT

No blanket change to Firefox, OAuth, OIDC, SSO, or the authenticator is implied by Decision (EU) 2026/2274. Changes are selected only after the system boundary and risk assessment identify a concrete requirement or risk. Preserve the distinction between:
- identity proofing / authentication by an external provider or operating system;
- QIK-VRT authorization and effect-release decisions;
- any QIK-VRT-owned biometric or AI processing;
- evidence that the integration behaves as specified.

Avoid collecting or storing biometric templates merely to create compliance evidence. Prefer architecture evidence and provider documentation where sufficient, and apply data minimisation, access control, retention limits, and applicable data-protection obligations.

## 6. Acceptance gates

- **Gate A — boundary:** intended purpose, component map and data flows approved.
- **Gate B — classification:** signed legal classification memorandum and role allocation.
- **Gate C — applicability:** Article 17/QMS applicability decision and, if applicable, EN 18286 clause-level gap assessment by a competent reviewer using the licensed standard.
- **Gate D — operation:** QMS procedures implemented, records populated from real operations, audits run, findings addressed.
- **Gate E — conformity:** applicable conformity assessment and other required legal steps completed; only then may an approved, scoped conformity statement be considered.

Until each applicable gate has verifiable evidence, overall status remains OPEN.