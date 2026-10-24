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

# Traceability Matrix

| Requirement | Evidence | Test/Gate |
|---|---|---|
| REQ-001 | docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md | ARTICLE_COUNT_44 |
| REQ-002 | docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md, docs/FORMAL_MODEL.md | QIKVRT_TERMS |
| REQ-003 | Article 2 | EVENT_DISPLAY_INTERPRETATION |
| REQ-004 | Articles 3, 4, 13 | TRACE_AND_COUNTERCHECK |
| REQ-005 | Article 7 | NETWORK_RESPONSIBILITY |
| REQ-006 | Article 8 | FALSE_CERTAINTY_BOUNDARY |
| REQ-007 | Article 9 | NON_TRIVIALIZATION_BOUNDARY |
| REQ-008 | Articles 10, 23, 33 | PROPORTIONALITY_EMERGENCY |
| REQ-009 | Article 11 | INNER_SPACE_BOUNDARY |
| REQ-010 | Articles 12, 27, 28, 29 | TECH_ACCOUNTABILITY |
| REQ-011 | Articles 14, 15 | CORRECTION_NONREGRESSION |
| REQ-012 | Article 21 | ASSERTION_CLASSES |
| REQ-013 | Articles 24, 25 | PRIVACY_MISUSE_BOUNDARY |
| REQ-014 | Articles 26, 27 | TECH_MINIMUM_STANDARDS |
| REQ-015 | Articles 30, 31 | POWER_VULNERABILITY |
| REQ-016 | Articles 33-36 | EMERGENCY_DOCUMENTATION_SANCTION |
| REQ-017 | Article 37 | MEMORY_FORGETTING_BALANCE |
| REQ-018 | Articles 38-40 | INTERDISCIPLINARY_EDUCATION_INTERNATIONAL |
| REQ-019 | Article 41 | SECURITY_ABUSE_LIMIT |
| REQ-020 | Article 42 | REVISION |
| REQ-T001 | src/, Makefile | BUILD_ANSI_C_POSIX |
| REQ-T002 | src/qikvrt.c | RUN_VERIFIER |
| REQ-T003 | tests/*.sh | RUN_POSIX_TESTS |
| REQ-T004 | ZIP inspection | ZIP_DIRECTORY_ENTRIES_ZERO |
| REQ-T005 | ZIP inspection | ZIP_DUPLICATES_ZERO |
| REQ-T006 | SHA256SUMS.txt | HASH_COMPLETE_MATCH |
| REQ-T007 | qikvrt/gates/*.json | JSON_PARSE_AND_REQUIRED_GATES |
| REQ-T008 | qikvrt/manifests/MANIFEST.json | MANIFEST_PARSE |
| REQ-T009 | grep scan | NO_ABSOLUTE_LOCAL_PATHS |
| REQ-T010 | gates and reports | NO_TRACEABILITY_NO_FINAL_PASS |


## V2.2 Multicast/Ontologie Traceability

| Requirement | Evidence | Gate |
|---|---|---|
| REQ-M001 | docs/MULTICAST_PROTOCOL.md, docs/FORMAL_MODEL.md | MULTICAST_MODEL_PRESENT |
| REQ-M002 | src/qikvrt.c, include/qikvrt.h, tests/test_multicast.sh | RUN_MULTICAST_SELFTEST |
| REQ-M003 | docs/MULTICAST_PROTOCOL.md, tests/test_multicast.sh | NO_METAPHOR_ONLY_MULTICAST |
| REQ-O001 | docs/ONTOLOGIE_DES_UNTERSCHIEDS.md | ONTOLOGY_DOCUMENT_PRESENT |
| REQ-O002 | docs/ONTOLOGIE_DES_UNTERSCHIEDS.md, src/qikvrt.c, tests/test_ontology.sh | ONTOLOGY_CHAIN_PRESENT |
| REQ-O003 | qikvrt/gates/MULTICAST_ONTOLOGY_GATES.json, src/qikvrt.c | NO_FINAL_PASS_WITHOUT_MULTICAST_ONTOLOGY |

## V2.3 constitutional governance traceability

| Requirement | Evidence | Gate/Test |
|---|---|---|
| REQ-G001 | docs/GOVERNANCE_PROCESS.md, docs/CASE_LIFECYCLE.md | RUN_GOVERNANCE_SELFTEST |
| REQ-G002 | docs/EVIDENCE_AND_ASSERTION_CLASSES.md | ASSERTION_CLASSES_PRESENT |
| REQ-G003 | qikvrt/gates/CONSTITUTIONAL_GOVERNANCE_GATES.json | GOVERNANCE_GATES_JSON_VALID |
| REQ-G004 | src/qikvrt.c qikvrt_selftest_governance | RUN_C_GOVERNANCE_SELFTEST |
| REQ-G005 | tests/test_governance.sh | RUN_POSIX_GOVERNANCE_TEST |
| REQ-G006 | V2.1/V2.2 gates retained | NO_REGRESSION_V21_V22 |


## V2.5 Active Layer Traceability

REQ-A001 -> docs/DISCOVERY_AUTHORIZATION.md, qikvrt/gates/ACTIVE_LAYER_GATES.json, qikvrt_selftest_active -> AUTHORIZED_DISCOVERY_OK.
REQ-A002 -> docs/ACTIVE_LAYER.md, tests/test_active_layer.sh -> NO_UNAUTHORIZED_SCANNING_OK and NO_SELF_PROPAGATION_OK.
REQ-A003 -> docs/ACTIVE_OPERATION_SPEC.md -> OPERATE_LOCAL and EMIT_AUDIT.
REQ-A004 -> docs/EVOLUTION_POLICY.md -> GOVERNANCE_REVIEW_REQUIRED.
REQ-A005 -> docs/COGNITIVE_IMPROVEMENT.md -> NONREGRESSION and metric preservation.


## V2.5 Watchdog Traceability

REQ-WD-001 -> docs/WATCHDOG_KEEPALIVE.md, qikvrt/manifests/WATCHDOG_PEERS_MANIFEST.json -> OPT_IN_PEERS_ONLY
REQ-WD-002 -> src/qikvrt.c, include/qikvrt.h, tests/test_watchdog.sh -> RUN_WATCHDOG_SELFTEST
REQ-WD-003 -> qikvrt/ledger/WATCHDOG_KEEPALIVE_LEDGER.jsonl -> NODE_LOSS_STATUS_RECORDED
REQ-WD-004 -> qikvrt/gates/WATCHDOG_KEEPALIVE_GATES.json, docs/WATCHDOG_OPERATION_SPEC.md -> WATCHDOG_BOUNDARY_GATES
REQ-WD-005 -> release/REFERENCE_TEST_RESULT.md -> REFERENCE_TEST_RESULT_PERSISTED

## V2.7 Bootstrapper Traceability

| Requirement | Artifact | Test/Gate |
|---|---|---|
| REQ-B001 | src/qikvrt.c, include/qikvrt.h | BUILD_ANSI_C_POSIX |
| REQ-B002 | qikvrt_bootstrap_ensure_guid | test_bootstrapper.sh |
| REQ-B003 | qikvrt/runtime/REPOSITORY_GUID.txt | BOOTSTRAPPER_GUID_GATES |
| REQ-B004 | --bootstrap idempotence | GUID_REUSED_AFTER_FIRST_EXECUTION |
| REQ-B005 | docs/SERVICE_STARTUP.md | HIGHER_SERVICES_START_AFTER_GUID |
| REQ-B006 | docs/BOOTSTRAPPER_GUID.md | AUTHORIZED_NETWORK_LOGIN_ONLY |
| REQ-B007 | BOOTSTRAP_LEDGER.jsonl | BOOTSTRAP_AUDIT_APPEND_ONLY |
| REQ-B008 | BOOTSTRAPPER_GUID_GATES.json | NO_UNAUTHORIZED_SCANNING / NO_SELF_PROPAGATION |


## V2.7 Traceability additions

REQ-TCP-001 -> src/qikvrt.c:qikvrt_loopback_exchange, CLI --selftest-tcpip-autonomy, tests/test_tcpip_autonomy.sh
REQ-TCP-002 -> struct qikvrt_tcpip_selftest_request, qikvrt_tcpip_selftest_request_validate, TCPIP_AUTONOMY_SANITY_GATES.json
REQ-TCP-003 -> CLI --selftest-tcpip-autonomy and --selftest-damage-containment
REQ-TCP-004 -> struct qikvrt_damage_containment_event, qikvrt_damage_containment_validate
REQ-TCP-005 -> docs/DAMAGE_CONTAINMENT.md, TCPIP_AUTONOMY_REFERENCE_LEDGER.jsonl
REQ-TCP-006 -> docs/TCPIP_AUTONOMY_SANITY.md, gates blocks list

## V2.9 GitHub Seed Discovery Traceability

REQ-GSD-001 -> docs/GITHUB_SEED_DISCOVERY.md, qikvrt/manifests/GITHUB_SEED_DISCOVERY_MANIFEST.json -> GITHUB_SEED_IS_GOLDKELCH_QIKVRT
REQ-GSD-002 -> src/qikvrt.c:qikvrt_github_seed_discovery_validate -> GRAPH_REACHABILITY_MODEL
REQ-GSD-003 -> qikvrt/gates/GITHUB_SEED_DISCOVERY_GATES.json -> PEER_MANIFEST_AND_GUID_REQUIRED
REQ-GSD-004 -> tests/test_github_seed_discovery.sh -> NO_GLOBAL_ADDRESS_SCANNING / NO_UNAUTHORIZED_PROBING
REQ-GSD-005 -> docs/GITHUB_SEED_DISCOVERY.md -> PEER_REQUESTABLE_SANITY / WATCHDOG_KEEPALIVE
REQ-GSD-006 -> src/qikvrt.c:qikvrt_selftest_github_seed_discovery -> NO_FINAL_PASS_WITHOUT_GITHUB_SEED_DISCOVERY


## V2.10 Real GitHub Seed Integration

V2.10 defines `https://github.com/Goldkelch/qik-vrt` as the real, tested initial seed. Acceptance requires live seed reachability evidence, raw `MANIFEST.json` validation, REST/TCPIP capability manifest validation, no global address scanning, no unauthorized probing, and persisted reference results. The runtime sanity path is implemented by `--selftest-real-github-seed-integration` and `--validate-github-seed-manifest`. V2.10 is the minimal regression point for this capability.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
