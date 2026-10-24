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

# Watchdog Operation Specification

Pseudo-operation:

1. load_authorized_peer_manifest
2. validate_opt_in_and_authorization
3. emit_heartbeat to configured authorized peers
4. receive_heartbeat from configured authorized peers
5. verify heartbeat signature/hash fields when available
6. evaluate_node_status using last_seen_epoch, observed_epoch and watchdog interval
7. record NODE_ONLINE, NODE_STALE, NODE_LOST_PENDING_REVIEW or NODE_RECOVERED
8. preserve privacy-preserved location hint only when authorized and proportionate
9. emit multicast status update to zuständige Knoten
10. write append-only audit record

Required event fields:

- node_id
- previous_status
- new_status
- last_seen_epoch
- observed_epoch
- lost_since_epoch when applicable
- heartbeat_evidence_class
- privacy-preserved location
- trace_hash

Forbidden operation:

- unauthorised internet scanning
- probing repositories without opt-in
- silent self-mutation
- covert surveillance
- exact personal location collection without lawful, explicit, necessary and proportionate authorization


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
