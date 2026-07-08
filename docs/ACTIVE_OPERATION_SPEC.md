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

# Active Operation Specification

Active operation lifecycle:

1. LOAD_SEEDS: read authorized seed registry.
2. LOAD_MANIFEST: read QIKVRT manifest for candidate repository.
3. CHECK_AUTHORIZATION: require opt-in and scope.
4. CHECK_BOUNDARY: require no surveillance, no official legal effect claim, no third-party guilt claim.
5. CHECK_HASH: verify declared artifact hash where artifact is local or provided.
6. CHECK_GOVERNANCE: require roles, proof status, privacy, proportionality, correction and nonregression gates.
7. CHECK_MULTICAST: require zuständige Knoten, delivery, feedback and trace.
8. CHECK_ONTOLOGY: require Unterschied -> Information -> Kausalität -> Verantwortung -> Verifikation -> Rückkopplung -> Traceability.
9. OPERATE_LOCAL: run verifier and acceptance suite only in the authorized local context.
10. EMIT_AUDIT: append immutable event summary.
11. PROPOSE_EVOLUTION: write proposal, never silent mutation.

Active layer statuses:

- BLOCK_UNAUTHORIZED,
- BLOCK_UNTRACEABLE,
- BLOCK_BOUNDARY_FAILURE,
- BLOCK_NONREGRESSION_FAILURE,
- READY_TO_VERIFY,
- READY_TO_OPERATE_LOCAL,
- PROPOSAL_READY,
- GOVERNANCE_REVIEW_REQUIRED,
- ACCEPTED_BY_GOVERNANCE.

No status may be treated as FINAL unless traceability, authorization, boundary, multicast, ontology and governance gates pass.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
