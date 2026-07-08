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


# Full Reusable Test Environment

This document defines the full reusable test environment from the Ontology of Difference to the GitHub-compatible REST API.

## Required Layers

- Ontology of Difference tests: difference, information, causality, responsibility, verification, feedback and traceability.
- Requirements coverage tests: every requirement class must map to an executable or gate-level test.
- Unit tests: C selftests for ontology, multicast, governance, active layer, watchdog, bootstrap, discovery, REST API, unified node core and onboarding.
- Integration tests: unified node core, role configuration, seed role, normal role, manifest validation, live GitHub seed reference and GitHub-compatible API contract.
- Acceptance tests: POSIX/Sandbox acceptance suite and Windows acceptance runner with external evidence import.
- Performance tests: bounded local runtime, selftest duration, manifest parse duration and package path-length constraints.
- Security tests: no unauthorized scanning, no self-propagation, no surveillance instrument, no remote mutation without authorization, no path traversal and no secret exposure.
- Runtime REST API tests: canonical OpenAPI contract, local shim 127.0.0.1:8766, GitHub REST compatibility, `/health`, `workflow_dispatch`, `repository_dispatch`, `ingest`, `verify`, `stage`, `release_status`.

## Reusable Architecture

Seed node and normal node use one identical QIKVRT Node Core and one identical REST API. The role is selected only by runtime configuration. Seed-specific and node-specific checks are assertions, not separate architecture.

## Final-Pass Rule

No full test environment final pass is valid unless ontology, requirements, unit, integration, acceptance, performance, security and REST API test classes are present and executed.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
