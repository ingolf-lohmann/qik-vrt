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

# QIKVRT Node Onboarding

QIKVRT Node Onboarding defines the generic node profile used after bootstrap.
It replaces any person-bound default node such as an operator-specific local node profile.

Required onboarding properties:
- generic node profile: every repository starts as a neutral QIKVRT node.
- no person-bound default: operator identity is optional metadata, never the node identity.
- repository GUID: the bootstrapper persists a GUID locally.
- authorized seed graph: discovery starts from the allowed seed and authorized peers only.
- local runtime profile: runtime evidence is stored under the local repository runtime directory.
- privacy-preserved evidence: user paths and operator names are sanitized before release evidence is persisted.
- watchdog readiness: node status can be checked by authorized peers.
- selftest requestable: the onboarding sanity check is available at runtime.
- handover-ready: another operator can run the same package without renaming an Ingolf-specific node.

Forbidden behavior:
- no hard-coded personal default node.
- no hidden operator identity binding.
- no person-specific path as canonical runtime path.
- no final pass if generic onboarding and privacy-preserved evidence are missing.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
