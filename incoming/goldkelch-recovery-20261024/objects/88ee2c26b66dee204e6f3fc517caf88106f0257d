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

# Watchdog Keepalive Layer

Purpose: authorized repositories can report regular keepalive status to connected repositories. This is an opt-in, authorization-bound, traceable safety layer, not an internet scanner.

Core concepts:

- authorized heartbeat: every participating repository emits a heartbeat only to explicitly configured peer repositories.
- watchdog interval: each node declares an expected keepalive interval.
- last_seen_epoch: the last verified heartbeat timestamp for a node.
- observed_epoch: the local verifier timestamp used to evaluate node state.
- node lost: if no valid heartbeat arrives within the allowed interval, the node is marked LOST_PENDING_REVIEW.
- location hint: when data allows, the last known privacy-preserved location hint is recorded; exact personal geolocation is forbidden unless explicitly lawful, authorized, necessary and proportionate.
- traceability: every status transition records cause, timestamp, node id, previous status, new status and evidence class.

Gates:

- WATCHDOG_KEEPALIVE_OK requires opt-in, authorization, traceability, interval, heartbeat validity check, privacy-preserved location handling, and nonregression of node-loss events.
- No unauthorized probing.
- No unauthorized scanning.
- No self-propagation.
- No surveillance instrument.
- No silent removal of a lost-node event.

States:

- NODE_ONLINE: heartbeat valid and within interval.
- NODE_STALE: heartbeat late but not yet confirmed lost.
- NODE_LOST_PENDING_REVIEW: heartbeat missing beyond interval.
- NODE_RECOVERED: node returns with valid heartbeat and traceable recovery event.

The watchdog layer informs the QIKVRT repository network when a node is lost, when data supports that conclusion, and records the best available timestamp and privacy-preserved location hint.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
