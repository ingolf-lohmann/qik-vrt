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

# Discovery and Authorization Protocol

QIKVRT active discovery is not internet wandering. It is authorized manifest resolution.

Allowed discovery channels:

- Local seed registry supplied by an authorized operator.
- Public repository file: `.well-known/qikvrt-repository.json`.
- Repository root manifest: `qikvrt/manifests/MANIFEST.json`.
- Signed or hash-bound release metadata supplied by the repository owner.

Forbidden discovery behavior:

- port scanning,
- vulnerability probing,
- credential guessing,
- scraping private data,
- evading rate limits,
- bypassing robots, access controls or terms,
- self-deployment into remote systems,
- contact enumeration of persons.

Minimum manifest fields:

- repository_id,
- owner,
- version,
- artifact_name,
- sha256,
- license,
- opt_in_active_layer,
- authorization_scope,
- public_contact_or_issue_channel,
- boundary_statement,
- nonregression_anchor,
- verification_command.

A manifest may be public and still not authorized. Authorization must be explicit.

If authorization is absent, stale, ambiguous or contradicted by boundary policy, the only permitted result is BLOCK.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
