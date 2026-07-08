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

# Live Evidence Closure

V2.11 closes the article/evidence gap by making live evidence an explicit gate.

Seed: `Goldkelch/qik-vrt`.

Required markers:

- `GITHUB_WEB_VISIBILITY_PASS`
- `RAW_MANIFEST_REFERENCE_PASS`
- `REST_TCPIP_MANIFEST_REFERENCE_PASS`
- `SANDBOX_DNS_BLOCK_RECORDED`
- `EXTERNAL_LIVE_FETCH_REQUIRED`
- `NO_FALSE_LIVE_PASS`
- `NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE`

Boundary: this repository may validate evidence and references locally, but a full C/POSIX live GitHub fetch requires an execution environment with DNS and HTTPS access to GitHub. If such an environment is missing, the result is BLOCK/PENDING, not PASS.

No hidden discovery service is allowed. GitHub is the single initial seed. No global address scanning, no unauthorized probing, no self propagation, no surveillance instrument, and no remote mutation without authorization are allowed.

## External live runner

`tools/gh_live_fetch.sh <repo-root>` is the owner-side or CI-side live evidence runner. It downloads the raw GitHub seed manifests, validates them through the C verifier, and writes external evidence under `qikvrt/evidence/`. This script is intentionally not treated as PASS in a DNS-blocked sandbox. It is the required external step for full live GitHub acceptance.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
