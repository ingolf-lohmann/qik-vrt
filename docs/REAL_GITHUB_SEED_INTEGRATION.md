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

# Real GitHub Seed Integration v2.10

## Purpose

This document closes the V2.9 acceptance gap. The initial seed for QIK-VRT repository discovery is the real GitHub repository:

`https://github.com/Goldkelch/qik-vrt`

The V2.10 gate requires a live reference check against that seed and a reproducible ANSI-C/POSIX sanity check that validates the resulting seed manifest evidence.

## Real GitHub Seed Integration

The accepted live reference consists of:

1. GitHub repository page reachable.
2. Raw seed `MANIFEST.json` reachable through `raw.githubusercontent.com`.
3. Raw seed manifest parseable as a JSON object.
4. Manifest contains `package`, `version`, `entries`, `qikvrt` paths, `LICENSE` paths and `sha256` evidence.
5. REST/TCPIP capability manifest `QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json` reachable.
6. REST/TCPIP manifest parseable and containing `repository_capabilities`, `github_rest_workflow_dispatch`, `github_rest_repository_dispatch`, `local_tcpip_api_shim`, `openapi_contract`, `unit_tests`, and `tcpip_e2e_tests`.

## Runtime Model

The ANSI-C layer does not claim to implement TLS itself. Network acquisition is a transport concern. The QIK-VRT selftest boundary is:

- fetch from the single authorized GitHub seed,
- validate the received manifest text,
- reject unbounded scans,
- reject unauthorized probing,
- require audit persistence,
- require peer graph derivation only from seed manifest evidence.

## Minimal regression

V2.10 is the minimal regression point for real seed integration. Earlier V2.9 logic is insufficient where live GitHub seed acceptance is relevant.

## Boundary

Allowed: `Goldkelch/qik-vrt` as single initial seed, raw manifest validation, REST/TCPIP capability manifest validation, graph reachability within declared manifests.

Forbidden: no global address scanning, no unauthorized probing, no self-propagation, no surveillance instrument, no remote mutation without authorization.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
