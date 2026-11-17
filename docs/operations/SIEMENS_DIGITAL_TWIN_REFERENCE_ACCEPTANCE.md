<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Siemens Digital Twin: reference restoration and live acceptance

The bounded restoration reuses the reference model from Authority PR #422,
head `630fd695791da71185077fb442e0f090a8fbcb13`, without creating a second
implementation. Its original model blob is
`816d55781e53e0801390a96e8032c9fa2b327ae2`.
Main `fbc450c4d2d5045335577aa59be7509cda16adeb` imported that absent module
from `src/qikvrt_digital_twin_rest.py`; the existing REST test failed to import.
The PR #422 fixture reset and negative readback tests are retained. Additional
tests verify a separate HTTP state/receipt read, independently recomputed state
digest, stale and replay conflicts without mutation, closed schema, range
rejection and exact prepared-state binding. `make test` now includes that
existing REST suite through `digital-twin-rest-test`.

## Three distinct acceptance scopes

| Scope | Required evidence | What it does not establish |
| --- | --- | --- |
| Restored reference implementation | Exact reused model bytes; adapter imports and compiles; positive and negative reference tests | Main promotion, Siemens tenant access, a personal role model or physical actuation |
| Reference integration test | Original REST handler over real loopback HTTP; separate client process reads state and receipt; independently recomputes digest; version 7 to 8; replay returns 409 with unchanged state | A Siemens API request, production SSO, a persistent deployed runtime or vendor compatibility |
| Productive Siemens integration | Exact deployment and authorized Siemens account/partition/resource binding; authenticated real requests; independent downstream effect readback through the same native Work Unit | Other Siemens products, all API versions, certification or untested physical actions |

The model remains `reference-train-001`, with position, velocity and
temperature. It is not yet a representation of the human role. Its
`SIMULATED_REFERENCE_TRANSITION` and local `receipt.effect_ack` acknowledge
only that reference transition. `physical_effect_ack` and global
`effect_ack_done` remain false. The original REST contract and loopback-only
SSO exposure guard remain unchanged.

## Concrete missing live evidence

| Obligation | Required evidence before closure |
| --- | --- |
| Actual Siemens target | A protected binding to the intended Building X/Horizon environment, region, API version, customer tenant and partition; actual endpoint readback. A URL or OAuth audience string alone is insufficient. |
| Machine access | An existing authorized machine-user credential reference in the protected store, least-privilege API roles, actual `client_credentials` token exchange, expiry/refresh and denied-scope controls. No credential value belongs in Git, transcripts or evidence. |
| Human role | Explicit mapping from the existing QIK-VRT personal identity/capability contract to the selected Siemens resource type and tenant identifiers, with validated human SSO and authorization. Train velocity is not a human privilege. If Security Manager identity/privilege APIs are chosen, prove their licensed domain access and exact resource binding. |
| Wire adapter | A reviewed extension of the existing adapter that maps the local JSON state/versions to the selected Siemens JSON:API resources, units, timestamps and concurrency semantics. No actual Siemens transport or domain mapping is present in the restored deterministic module. Do not assume Siemens accepts the local request fields or version rule. |
| First useful round trip | Original Terminal input and admitted Transputer request with Work Unit/request hash, exact code/deployment and resource identities; before observation; authorized bounded API operation; a separate authenticated GET or event read from Siemens; independently compared requested and observed result; native event/epoch/digest and receipt readback. An HTTP success response alone is not the effect. |
| Failure and recovery | Real-target stale/conflict behavior, missing permission, expiry, ambiguous or lost response and reconciliation before retry; negative readback, restart and deduplication evidence. Choose concurrency mechanisms from the selected API version rather than assuming an ETag contract. |
| Physical action, when in scope | Dedicated safe acceptance on the actual gateway/device and independent sensor feedback, including the deployment-specific Safety/Security requirements. Point-value ingestion and simulated acknowledgements do not prove actuator motion. |
| Deployment and node return | Exact `https://raumzeitterminal.de/` TLS/application acceptance, admitted original host/writer and original Terminal readback; authenticated Mirror ACK/reply separately. Source tests and packages do not prove a running peer or adoption. |

These are open evidence obligations, not assertions that an external tenant
has no credentials or that an unavailable local CLI represents the state of
the Owner's infrastructure. Inspect only the admitted protected bindings when
resuming. Do not ask the Owner to relay packages or enter raw secrets in chat.

## Acceptance sequence through the existing native path

1. Reobserve Authority Main and the selected PR's exact head/tree, current
   checks and writer admission. Preserve PR #422 and all original journals.
2. Run `make digital-twin-rest-test digital-twin-sso-test`, the applicable
   native ledger/Terminal regressions, integrity verification and `make test`.
   Preserve failures with their actual cause; do not mock denied socket APIs.
3. Retain the bounded Owner input through the existing Terminal input contract
   and original own-session Transputer Runtime. If Unix ingress is denied,
   record that route as HOLD and use only the admitted original in-process
   API for its supported local scope. Open copied peer journals read-only.
4. Complete the authorized, scoped real Siemens round trip only after the
   protected target, role mapping, adapter and capability bindings above are
   established. Never enable remote reference access by weakening its guard.
5. Produce assessments only with the original
   `node-tools/qikvrt_mirror_emit.py assess`/`adopt` and its original outbox,
   package/send/receipt/claim procedure. If that tool or binding is unavailable,
   preserve its named source carrier as HOLD; do not invent a replacement
   assessment. Independently read back actual results and keep each scope
   separate. Claim complete compatibility only for the real tested target.

## Current Siemens primary references

Checked 19 October 2026. These describe interfaces, not a completed QIK-VRT
integration. The Building X examples use `https://horizon.siemens.com` as the
OAuth audience. Personal human SSO and machine-user service authorization are
separate obligations. The public sandbox is read-only and currently excludes
Fire, LifecycleTwin and Physical Security domain APIs; it cannot establish a
write/privilege/physical-action acceptance in those domains.

- Siemens, Building X Getting Started:
  https://developer.siemens.com/building-x-openness/dev-guide/gettingstarted.html
- Siemens, Building X Integration Guide:
  https://developer.siemens.com/building-x-openness/dev-guide/integration-guide.html
- Siemens, Building X API conventions (JSON:API):
  https://developer.siemens.com/building-x-openness/dev-guide/index.html
- Siemens, Building Operations API overview:
  https://developer.siemens.com/building-x-openness/api/building-operations/overview.html
- Siemens, Security Identities and Privileges API overview:
  https://developer.siemens.com/building-x-openness/api/security-api/piam-v1/overview.html
- Siemens, Lifecycle Twin API Quick Start (separate domain):
  https://developer.siemens.com/building-x-openness/api/lifecycletwin-api/quickstart.html

Restoration provenance and measured test results belong to
`state/work_units/QIKVRT_SIEMENS_REFERENCE_RESTORE_20261019_V1.json` and its
bound evidence. This document grants no additional external effect.
