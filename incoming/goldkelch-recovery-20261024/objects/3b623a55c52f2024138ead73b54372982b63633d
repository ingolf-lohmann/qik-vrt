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

# Short Path Package Compatibility v2.11.1

Status: PATH_LENGTH_ACCEPTANCE_FAILURE repaired.

This release is distributed as `qv211.zip` intentionally. The archive basename is short, root content is flat, and internal ZIP path lengths are kept below the repository-defined limit.

Policy:
- NO_LONG_ARCHIVE_BASENAME: archive basename should stay <= 16 characters.
- MAX_INTERNAL_PATH_LEN: internal paths must stay <= 80 characters.
- NO_WRAPPER_DIRECTORY: root files such as README.md, Makefile and SHA256SUMS.txt must be visible directly after extraction.
- NO_ABSOLUTE_PATHS, NO_DRIVE_LETTERS, NO_PARENT_TRAVERSAL.
- NO_SHORT_PATH_FINAL_PASS_WITHOUT_EVIDENCE.

Rationale: Windows runners may combine download directory, archive basename, extraction directory and internal ZIP path. Long release names can make otherwise valid payloads look empty or inaccessible in a shell-based acceptance runner.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
