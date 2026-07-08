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

# Article Claim Matrix

Every article-level property must be classified before it may be treated as an operative repository property.

Allowed evidence classes:

- `IMPLEMENTED_AND_LOCAL_TESTED`
- `LIVE_TEST_REQUIRED`
- `SOAK_TEST_REQUIRED`
- `EXTERNALLY_REPRODUCED_REQUIRED`
- `FUTURE_APPLICATION`
- `CONCEPTUAL_NOT_OPERATIONAL`
- `NOT_CLAIMED`

Hard rule: `NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE`.

Current classification summary:

| Claim | Class | Status |
| --- | --- | --- |
| Local repository selftests | IMPLEMENTED_AND_LOCAL_TESTED | evidenced by make test |
| GitHub seed repository visibility | LIVE_TEST_REQUIRED | web reference available, external C/POSIX live fetch still required |
| Peer graph from seed | LIVE_TEST_REQUIRED | requires live peer manifest graph |
| Watchdog/keepalive | IMPLEMENTED_AND_LOCAL_TESTED | live multi-peer operation still requires external setup |
| Windows extraction | EXTERNALLY_REPRODUCED_REQUIRED | owner TSV required |
| Global biometric SSO | FUTURE_APPLICATION | not implemented here |
| Kognitiv selbstverbessernde KI | FUTURE_APPLICATION | governance model only, no productive AI engine |
| Glauben/Aberglauben/Wissen/Wissenschaft distinction | CONCEPTUAL_NOT_OPERATIONAL | article framework, not runtime proof |
| Retrokausalitaet as proof duty | CONCEPTUAL_NOT_OPERATIONAL | risk-governance concept, not time-travel claim |

This matrix prevents mixing vision, architecture, implementation, live operation, and externally reproduced evidence.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
