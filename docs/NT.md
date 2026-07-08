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

# QIKVRT Node Onboarding Testbed

The Node Onboarding Testbed is a reusable architecture testbed. It starts at the Ontology of Difference, passes through the Constitution of Traceability, and verifies the same unified node core for both `normal` and `seed` runtime roles.

## Reused core chain

```text
Ontology of Difference
Constitution
Generic QIKVRT Node Onboarding
GUID bootstrap
authorized seed graph
live GitHub evidence
peer graph discovery
Unified QIKVRT Node Core
QIKVRT GitHub-Compatible Repository API
watchdog
request response traceability
security boundary
safety boundary
```

The REST API is not role-specific. It is the same `QIKVRT GitHub-Compatible Repository API` for every node. The testbed changes only role assertions.

## Role matrix

```text
normal -> same API, normal-node assertions, peer/onboarding policy
seed   -> same API, seed assertions, publication/seed-graph policy
```

## Required invariants

```text
no person-bound default
no unauthorized scanning
no remote mutation without authorization
no seed/node code split
no API fork
```

## Evidence

The testbed persists evidence and links it to Windows runtime acceptance, live GitHub seed evidence, OpenAPI alignment and reusable core selftests.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
