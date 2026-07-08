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

# QIKVRT GitHub-Compatible Repository API

The API stood already fixed in the GitHub repository. This repository therefore does not define a new `/qikvrt/...` API surface. It carries the existing QIKVRT GitHub-Compatible Repository API forward.

## Canonical contract

```text
api/qikvrt_github_api.openapi.yaml
QIKVRT GitHub-Compatible Repository API
```

Servers:

```text
http://127.0.0.1:8766
https://api.github.com
```

Endpoints:

```text
GET  /health
POST /repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST /repos/{owner}/{repo}/dispatches
```

Dispatch semantics:

```text
workflow_dispatch
repository_dispatch
identical API
```

Dispatch operations:

```text
ingest
verify
stage
release_status
```

## Identical API rule

Seed nodes and normal nodes expose the same API. The role is runtime configuration only. A seed node may satisfy additional seed assertions. A normal node may satisfy normal-node assertions. The REST API itself remains identical.

## Request response traceability

Every request must preserve traceability: operation, artifact_id, dry_run state, expected_sha256 when applicable, authorization state, result status and audit reference.

## Safety boundaries

```text
no remote mutation without authorization
no secret exposure
no unauthorized probing
no API fork
no false final pass
```


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
