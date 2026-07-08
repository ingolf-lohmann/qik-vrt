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

# V2.10 Real GitHub Seed Integration Reference Result

Status: PASS_REFERENCE

Seed: `https://github.com/Goldkelch/qik-vrt`

Observed live evidence:

- GitHub repository page reachable.
- Repository visible as public template.
- Root structure includes QIKVRT-relevant folders and files.
- Raw `MANIFEST.json` reachable from `raw.githubusercontent.com`.
- Raw manifest contains `package`, `version`, `entries`, QIKVRT paths, license paths and SHA256 evidence.
- Raw `QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json` reachable.
- REST/TCPIP manifest contains `repository_capabilities`, `github_rest_workflow_dispatch`, `github_rest_repository_dispatch`, `local_tcpip_api_shim`, `openapi_contract`, `unit_tests`, and `tcpip_e2e_tests`.

Boundary:

- No global address scanning.
- No unauthorized probing.
- No self-propagation.
- No remote mutation without authorization.

Acceptance consequence:

V2.10 supersedes V2.9 as minimal regression for real GitHub seed integration.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
