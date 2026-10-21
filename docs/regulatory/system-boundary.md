# QIK-VRT system boundary and intended-purpose record

**Assessment status:** FACTS PARTIALLY RECORDED · APPROVAL OPEN  
**As-of date:** 2026-10-21  
**Product/version scope:** QIK-VRT repository state referenced by PR #567; branch and release identity must be bound at approval  
**Owner / approver:** OPEN — must be assigned by the legal product/provider entity

## 1. Evidence basis

This record distinguishes repository evidence from assumptions about production operation.

| Fact | Evidence inspected | What it supports | What it does not prove |
|---|---|---|---|
| QIK-VRT architecture uses explicit evidence, authorization, execution, effect observation/read-back, comparison, and acceptance gates | Existing project context and repository architecture/work-unit artifacts | Intended engineering emphasis on provenance and effect-bound acceptance | Legal classification or conformity |
| Personal Firefox capability boundary separates Standard and opt-in Personal editions | `spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md` | Product-edition separation and credential/data-flow constraints described by the repository | Complete inventory of all deployed configurations |
| Personal authentication is an opt-in OIDC integration using Authorization Code with PKCE S256, state/nonce, issuer/audience/subject/token-lifetime validation | `src/qikvrt_personal_auth.py` and capability-boundary specification | A documented identity-provider integration in the Personal path | Successful live SSO operation on every platform or any AI Act status |
| The spec delegates passkeys/WebAuthn and biometric verification to the registered identity provider/device and says no biometric templates or modality assertions are collected | `spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md` | Documented design boundary for the described path | Independent confirmation of all builds, devices, IdPs, or runtime behavior |
| OIDC identity is separate from model API entitlement | `src/qikvrt_personal_auth.py` module documentation and capability-boundary specification | Identity login is not itself proof of model entitlement | Provider contract/production entitlement state |
| Repository registry permits only declared/queued node discovery, no global scanning, no self-propagation, and no foreign repository writes | `docs/QIKVRT_OPEN_MULTI_NODE_ARCHITECTURE.md`, `registry/NODEMESH_INDEX.json` | Existing distribution/authority constraints | That all remote nodes have current artifacts or acknowledge this assessment |
| Current node index shows one registered node with stale lifecycle evidence and missing health/ack/renewal hashes | `registry/NODEMESH_INDEX.json`, generated 2026-10-18T05:30:39Z | The index's recorded state at its generation time | Current remote runtime state; fresh API checks are required |

## 2. Provisional intended-purpose description

The repository describes QIK-VRT as an evidence-bound human–AI collaboration and execution framework. Its documented patterns emphasize provenance, contradiction preservation, explicit authorization, execution, observation of effects, fresh read-back, comparison, acceptance, and correction. It also contains a distinct opt-in Personal Firefox authentication/runtime integration.

This is a **provisional engineering description**, not yet an approved legal intended-purpose statement. The accountable product owner must confirm:
- intended users and customer/deployment contexts;
- intended tasks and prohibited uses;
- whether QIK-VRT makes or materially influences decisions about natural persons;
- whether it is intended for employment, education, essential services, law enforcement, migration, justice, or other Annex III contexts;
- whether any model component qualifies as an AI system under Article 3(1);
- whether the product is placed on the market / put into service and by which legal entity;
- which edition, build, and component set the statement covers.

## 3. Component and responsibility boundary

| Component | Provisional responsibility boundary | Verification still required |
|---|---|---|
| QIK-VRT core / execution and evidence gates | Coordinates declared workflow, authorization, effect observation, read-back, and acceptance according to repository contracts | Map each released executable/service and its actual AI/non-AI functions |
| AI model/provider or connected AI client | Supplies model/service behavior under the selected integration | Inventory providers, model versions, processing locations, contracts, intended uses, and provider obligations |
| Personal Firefox adapter / local terminal | Optional client integration and local orchestration in the documented Personal edition | Bind assessment to exact release, platforms, build/test results, and actual deployment |
| OIDC identity provider | Authenticates account identity through configured issuer and protocol; not equivalent to model/API entitlement | Identify each supported production issuer/configuration and contracts |
| OS/browser authenticator / passkey / WebAuthn / biometric modality | According to the current specification, delegated to the device or IdP; QIK-VRT specification says it does not collect biometric templates | Verify implementation and data flows on each supported device/IdP; confirm whether QIK-VRT receives biometric data or only an authentication result |
| Repository/registry/node system | Governs declared node identity, authorized source changes, and evidence read-back | Reconcile stale registry evidence and obtain node-specific current receipts |
| End user / deployer / operator | Chooses configuration and interacts with connected services; precise legal role depends on facts and contracts | Identify legal entity, role, training, oversight, and operational control |

## 4. Authentication and biometric data boundary

The current repository specification says:
- OIDC login is a distinct identity function;
- identity SSO does not grant model API entitlement;
- passkeys/WebAuthn and biometric verification are delegated to the registered IdP/device;
- no biometric templates or modality assertions are collected by the described QIK-VRT integration.

These are **design claims in repository artifacts**, not yet independent runtime findings. Required validation:
1. Trace the full authentication and model invocation flow for each supported edition.
2. Inspect browser/client/server request and storage behavior without recording credentials or biometric material.
3. Verify whether QIK-VRT receives only OIDC claims/tokens and an authentication result, or any biometric data.
4. Record exact supported platforms, IdP profiles, build IDs, and test fixture boundaries.
5. Capture sanitized test results and fresh read-back hashes. Never store access tokens, refresh tokens, passkey material, biometric templates, or session secrets in the repository.

## 5. AI-system and high-risk decision

No classification conclusion is made in this file. The presence of SSO, OAuth/OIDC, an identity provider, or an AI model integration is not by itself sufficient to conclude that the entire QIK-VRT product is a high-risk AI system. The responsible legal entity must assess Article 3(1), provider/deployer roles, Article 6, Annex I, Annex III, intended purpose, and any other relevant provisions. The classification decision is recorded separately in `classification-memorandum.md`.

## 6. Approval checklist

- [ ] Product owner confirms intended-purpose statement and covered edition/release.
- [ ] Architecture owner maps all executable components and AI-enabled functions.
- [ ] Security owner verifies identity, token, secret-store, and model-entitlement boundaries.
- [ ] Privacy/data-protection reviewer verifies data categories, recipients, retention, and lawful basis where applicable.
- [ ] Legal/compliance reviewer approves role allocation and AI Act classification.
- [ ] Release identity, test evidence, and current node status are bound to immutable refs.
- [ ] Any unsupported or unverified facts remain explicitly OPEN.

**Overall status: OPEN.** This document is an evidence map and does not itself prove conformity or runtime behavior.