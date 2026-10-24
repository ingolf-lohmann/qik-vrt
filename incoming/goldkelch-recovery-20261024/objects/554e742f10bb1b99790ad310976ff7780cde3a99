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

# Bootstrapper GUID Layer v2.9

## Zweck
Der Bootstrapper führt bei first execution eine lokale Repository-Initialisierung durch. Er erzeugt genau eine Repository-GUID, persistiert sie lokal und nutzt diese GUID danach als stabile Knotenkennung im autorisierten QIKVRT-Repository-Netzwerk.

## Regeln
- GUID generation occurs only in the local repository root.
- Persist: `qikvrt/runtime/REPOSITORY_GUID.txt`.
- Bootstrap audit: `qikvrt/runtime/BOOTSTRAP_LEDGER.jsonl`.
- Higher services start only after GUID persistence.
- Higher services: verify, multicast, ontology, governance, active, watchdog.
- Network login is authorized network login only through opt-in manifests.
- No remote side effects without authorization.
- No unauthorized scanning, no self-propagation, no surveillance instrument, no silent mutation.

## Betriebsfolge
1. CHECK_REPOSITORY_ROOT
2. LOAD_OR_GENERATE_GUID
3. PERSIST_GUID
4. START_VERIFY_SERVICE
5. START_MULTICAST_SERVICE
6. START_ONTOLOGY_SERVICE
7. START_GOVERNANCE_SERVICE
8. START_ACTIVE_LAYER_SERVICE
9. START_WATCHDOG_KEEPALIVE_SERVICE
10. AUTHORIZED_NETWORK_LOGIN
11. EMIT_BOOTSTRAP_AUDIT

## Final-Pass-Regel
Kein Bootstrap-Final-Pass ohne GUID, Persistenz, Audit, Verfassungsgates, Multicast, Ontologie, Governance, Watchdog, Active-Layer und Autorisierung.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
