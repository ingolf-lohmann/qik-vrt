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

# Technical Implementation Specification

## ANSI-C/POSIX scope
The verifier is written in C89-compatible ANSI C and built with POSIX `cc` through a POSIX Makefile.

## Implemented selftests
- document verification
- repository verification
- multicast selftest
- ontology selftest
- governance selftest

## Governance data model
`struct qikvrt_case` models:
- assertion class
- evidence class
- traceability
- multicast delivery
- feedback
- privacy check
- proportionality check
- emergency check
- correction path
- nonregression

## Mandatory fail conditions
- no trace
- no assertion class
- no responsible recipient group
- missing feedback
- missing privacy/proportionality gate
- final-pass requested without complete gates

## No hidden dependencies
No external libraries are required beyond ISO C/POSIX shell tools used by tests.


## V2.7 TCP/IP selftest clean-code interfaces

- `struct qikvrt_tcpip_selftest_request` models authorized peer selftest request.
- `qikvrt_tcpip_selftest_request_validate()` validates opt-in, authorization, traceability, no-scan and no-remote-mutation gates.
- `qikvrt_selftest_tcpip_autonomy()` runs a local TCP loopback request/response exchange.
- `struct qikvrt_damage_containment_event` models non-destructive containment.
- `qikvrt_damage_containment_validate()` requires quarantine-required status and authorized multicast notice on failed selftest.
- `qikvrt_selftest_damage_containment()` is the runtime sanity check for containment behavior.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
