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

# Service Startup Order v2.9

Der Bootstrapper startet die höheren Services in deterministischer Reihenfolge.

## Service startup order
1. verify service: Dokument-, Hash- und Verfassungsgates.
2. multicast service: Zustellgruppe, Payload, Rückkopplung, Spur.
3. ontology service: Unterschied -> Information -> Kausalität -> Verantwortung -> Verifikation -> Rückkopplung -> Traceability.
4. governance service: Rollen, Beweisgrade, Datenschutz, Verhältnismäßigkeit, Korrektur, Nichtregression.
5. active service: autorisierte Manifestauflösung, keine unautorisierte Suche, keine Selbstverbreitung.
6. watchdog service: Keepalive, Node-Loss-Erkennung, Datenschutz bei Ortshinweisen.

## Betriebsgrenzen
- Kein Dienst darf vor GUID-Persistenz final starten.
- Kein Netzwerkbeitritt ohne authorized manifest.
- Kein Dienst darf eigenmächtig fremde Repositories verändern.
- Jeder Dienst muss Audit-Ereignisse erzeugen.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
