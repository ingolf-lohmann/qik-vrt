<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

---
QIKVRT-Artifact: role-package-test-result
Version: 2.13.4
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
---

# Role Package Test Result

Status: PASS

```text
$ make clean
rm -rf build

EXIT=0
$ make test
mkdir -p build
cc -std=c89 -pedantic -Wall -Wextra -Iinclude -o build/qikvrt_verify src/main.c src/qikvrt.c
sh tests/run_all.sh
PASS content gates
PASS boundary gates
PASS multicast gates
PASS ontology gates
PASS governance gates
PASS active layer gates
PASS watchdog keepalive gates
PASS bootstrapper gates
PASS tcpip autonomy and damage containment gates
PASS autonomous discovery operation gates
PASS QIKVRT GitHub seed discovery selftest v2.13.4
checks=17 failures=0 articles=0
PASS real GitHub seed integration gates
PASS zip layout compatibility gates
PASS Windows Shell ZIP compatibility gates
PASS short path gate max_internal_path_len=65
PASS short path acceptance gate
PASS live evidence closure gates
PASS article claim matrix gates
PASS node onboarding gates
PASS GitHub-compatible REST API contract gates
PASS unified node core gates
PASS unified node onboarding testbed gates
PASS Windows keep-open gates
PASS license copyright header footer gates
PASS full reusable test environment gates
PASS seed node split delivery gates
PASS full requirements coverage gates
PASS full unit test layer
PASS full integration test layer
PASS hash gates
PASS full acceptance test layer
PASS full performance test layer duration_seconds=0
PASS full security test layer
PASS hash gates
PASS POSIX acceptance suite v2.13.4

EXIT=0
$ bash -lc cc -std=c89 -pedantic -Wall -Wextra -Werror -Iinclude -o /tmp/qv2122_qv2122_node src/main.c src/qikvrt.c

EXIT=0
$ bash -lc /tmp/qv2122_qv2122_node --verify-repo .
PASS QIKVRT repository GitHub seed discovery verification v2.13.4
checks=708 failures=0 articles=44

EXIT=0
$ bash -lc /tmp/qv2122_qv2122_node --selftest-full-test-env
PASS QIKVRT full reusable test environment selftest v2.13.4
checks=15 failures=0 articles=0

EXIT=0
$ bash -lc /tmp/qv2122_qv2122_node --selftest-seed-node-delivery
PASS QIKVRT seed/node split delivery selftest v2.13.4
checks=12 failures=0 articles=0

EXIT=0
$ bash -lc /tmp/qv2122_qv2122_node --selftest-license-visibility
PASS QIKVRT license and copyright visibility selftest v2.13.4
checks=10 failures=0 articles=0

EXIT=0
```

---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
