# QIK-VRT AI Act classification memorandum

**Status:** DRAFT — NO LEGAL CLASSIFICATION CONCLUSION  
**Assessment date:** 2026-10-21  
**Product scope:** QIK-VRT core and the opt-in Personal Firefox / OIDC integration described in repository artifacts  
**Decision owner:** OPEN  
**Qualified legal reviewer:** OPEN  
**Evidence cut-off:** Repository files inspected for PR #567; live node state not verified

## 1. Executive decision

**Current result: MORE_FACTS_REQUIRED.**

The available repository evidence does not support the claim that QIK-VRT is a high-risk AI system merely because it provides SSO methodology or integrates OIDC authentication. The available evidence also does not support a final conclusion that the complete product is outside the AI Act's high-risk regime. Classification depends on the actual system functions, intended purpose, provider/deployer role, deployment context, and applicable Article 6 / Annex I / Annex III criteria.

Accordingly:
- Article 17 QMS applicability is **OPEN** pending the classification and role decision.
- EN 18286:2026 is retained as a candidate harmonised QMS route if the legal criteria make it applicable.
- No declaration of conformity, high-risk designation, certification, or overall AI Act compliance is made.
- No blanket change to Firefox, OAuth/OIDC, or authentication architecture is authorized by this memorandum.

## 2. Source facts and limits

### 2.1 Facts found in repository artifacts

1. `spec/firefox/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.md` describes separation between the Standard Firefox edition and an opt-in Personal Edition, and states that personal capabilities/credentials/state must not leak into the Standard edition.
2. The same specification describes the Personal integration as an authenticated external service path and says identity SSO does not grant model API entitlement.
3. The specification states that passkeys/WebAuthn and biometric verification are delegated to the registered identity provider/device, and that no biometric templates or modality assertions are collected by the described integration.
4. `src/qikvrt_personal_auth.py` documents an opt-in OIDC authentication integration and separation between OIDC identity and model API entitlement.
5. `docs/QIKVRT_OPEN_MULTI_NODE_ARCHITECTURE.md` and `registry/NODEMESH_INDEX.json` document a bounded node registry and prohibit global scanning, self-propagation, and unauthorized foreign repository writes. The index generated on 2026-10-18 records one node as STALE and missing health/acknowledgement/renewal hashes.

These are repository-documentation facts. They are not a substitute for verification against the exact released binary, deployed service, actual configuration, contracts, and runtime data flows.

### 2.2 Critical unknowns

- Whether every QIK-VRT edition/function under consideration meets the AI-system definition in Article 3(1).
- The final approved intended-purpose statement and prohibited uses.
- Whether QIK-VRT itself provides, places on the market, or puts into service an AI system, and which legal entity does so.
- Whether QIK-VRT is the provider, deployer, importer, distributor, product manufacturer, or multiple roles for each deployment.
- Whether any actual intended use falls within Article 6 / Annex I or an Annex III use case.
- Whether QIK-VRT makes or materially influences decisions concerning natural persons in an Annex III context.
- Whether biometric data are processed by QIK-VRT, merely by an external device/IdP, or not at all in the specific configuration.
- The production deployment contexts, customer instructions, downstream integration, and any material modification or change of intended purpose.
- The current state and configuration of each authorized node.

## 3. Preliminary assessment by legal question

| Question | Preliminary finding | Status | Closure evidence |
|---|---|---|---|
| AI Act Article 3(1): is the scoped product an AI system? | Repository includes AI collaboration/integration capabilities, but product/system boundary and relevant model functionality must be mapped per edition and deployment | OPEN | Component/function inventory, intended-purpose statement, technical assessment against Article 3(1) |
| Article 6 / Annex I product-safety route | No evidence sufficient to decide applicability | OPEN | Applicable-product-law and intended-purpose analysis |
| Article 6(2) / Annex III use case | SSO by itself is not an Annex III use case; actual intended use and system functions remain to be assessed | OPEN | Criterion-by-criterion Annex III memorandum |
| Annex III 1(a) biometric identification | Repository spec says biometric verification is delegated to device/IdP and no templates/modality assertions are collected by the described integration | PARTIALLY DOCUMENTED | Runtime/data-flow verification; determine whether the function is 1:1 verification or another biometric use |
| Provider role | Cannot be determined solely from source repository ownership or the presence of an integration | OPEN | Entity, product name, placing-on-market/putting-into-service facts, contractual and control analysis |
| Deployer role | Depends on each deployment and who uses/operates the system | OPEN | Deployment model, instructions, operator and customer contracts |
| Article 17 QMS obligation | Depends on whether the responsible entity is a provider of a high-risk AI system under the applicable rules | OPEN | Signed classification and role decision |
| EN 18286:2026 route | Candidate only if relevant obligations apply; standard coverage and clause-level mapping must be reviewed | CONDITIONAL | Licensed standard, applicability matrix, clause-by-clause gap assessment |
| Conformity assessment / declaration | No basis to claim complete conformity now | NOT ESTABLISHED | Applicable conformity-assessment records and approved scoped statement |

## 4. Specific SSO / biometric analysis

SSO and OAuth/OIDC are identity federation/authentication mechanisms. Their presence alone does not establish high-risk AI classification. An AI feature connected to an authenticated account must be assessed separately from the authentication protocol.

The repository specification's statement that biometric verification is delegated to an operating system/device or identity provider and that QIK-VRT does not collect biometric templates is relevant evidence about the intended component boundary. It does not alone establish the scope of every build or integration. The implementation must be checked to determine what information actually crosses the boundary.

Annex III point 1(a) includes biometric identification uses and excludes biometric verification whose sole purpose is to confirm that a specific natural person is the person they claim to be, including for access to a service or device unlocking, subject to the exact legal text and actual use. This specific exclusion must not be generalized to other biometric or AI functions.

## 5. Required decision procedure

1. **Freeze the assessed scope:** identify edition, release commit, build digest, configuration, target users, and deployment context.
2. **Approve intended purpose:** specify functions, use cases, users, limitations, reasonably foreseeable misuse, and prohibited uses.
3. **Map the system:** identify each AI system/component, external model, identity provider, OS/browser authenticator, data flow, decision, and responsible entity.
4. **Verify runtime boundary:** test whether biometric data/templates are ever received or stored by QIK-VRT, and distinguish login/identity assertions from model/API entitlement.
5. **Assign legal roles:** document provider, deployer, importer, distributor, and manufacturer roles for the actual supply chain and each deployment.
6. **Apply the law:** assess Article 3(1), Article 6, Annex I, Annex III and relevant exceptions/obligations against the scoped product and purpose.
7. **Independent review:** have a qualified EU AI Act reviewer approve the rationale and record the applicable law/version/date.
8. **Decide QMS scope:** only after steps 1–7, decide Article 17 applicability and perform a clause-level EN 18286:2026 gap analysis if applicable.
9. **Maintain change control:** reassess when intended purpose, model/function, integration, customer context, or deployment changes.

## 6. Outcome fields — intentionally unsigned

- Product scope and release: OPEN
- Intended purpose approved by product owner: OPEN
- Provider legal entity and role: OPEN
- Deployer role(s): OPEN
- Article 3(1) conclusion: OPEN
- Article 6 / Annex I conclusion: OPEN
- Annex III conclusion and criterion-by-criterion rationale: OPEN
- Biometric boundary verified at runtime: OPEN
- Article 17 applicability: OPEN
- EN 18286 gap assessment: NOT STARTED
- Qualified legal reviewer: OPEN
- Approval date and signature/traceable approval record: OPEN

**Do not change the result from MORE_FACTS_REQUIRED until the evidence above is complete and the accountable owner and qualified reviewer have approved the decision.**