<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

---
QIKVRT-Artifact: license-header
Version: 2.13.4
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; no final pass without evidence.
---

# Unified QIKVRT Node Core

This document corrects the runtime architecture: every QIKVRT repository node uses one identical inner build, one identical API, and one reusable testbed core. The role is runtime configuration, not a fork of the implementation.

## Core rule

```text
Unified QIKVRT Node Core = one identical API + one identical runtime core + role configuration.
```

Allowed roles:

```text
normal
seed
```

A seed node is not a different API. A normal node is not a different API. Both roles use the same GitHub-compatible OpenAPI contract, the same local TCP/IP shim on `127.0.0.1:8766`, the same `workflow_dispatch` semantics, the same `repository_dispatch` semantics, and the same operation enum.

## Canonical API source

The API is not re-invented here. It is aligned to the GitHub repository contract:

```text
api/qikvrt_github_api.openapi.yaml
QIKVRT GitHub-Compatible Repository API
http://127.0.0.1:8766
https://api.github.com
/health
workflow_dispatch
repository_dispatch
operation = ingest | verify | stage | release_status
```

## Role configuration

Runtime role is stored as configuration, for example:

```text
qikvrt/config/ROLE.json
role = normal | seed
```

Seed-specific and node-specific differences are limited to assertions, policy, publication and peer-graph expectations. They do not create a second API, a second verifier, or a second testbed.

## Hard boundaries

```text
no API fork
no seed/node code split
no hidden person-bound default
no unauthorized scanning
no self-propagation
no remote mutation without authorization
```

## Testbed consequence

The testbed is reusable. It runs the same core tests for both roles and only switches the role-assertion matrix. This preserves the Ontologie des Unterschieds: difference is represented as runtime role data, not as divergent architecture.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
