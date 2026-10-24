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

# QIKVRT Multicast-Protokoll V2.2

## Ziel

Dieses Protokoll macht `TCP-IP Multicast <=> Gerechtigkeit` anschlussfähig, ohne TCP/IP moralisch zu überdehnen. Es überträgt das technische Prinzip definierter Gruppenadressierung auf eine defensive Informations- und Verantwortungsordnung.

## Begriffe

- Sender: Knoten, der einen Payload erzeugt oder weitergibt.
- Payload: relevante Information, Spur, Warnung, Entscheidung oder Beleg.
- Empfängergruppe: zuständige Knoten, nicht beliebige Öffentlichkeit.
- Zustellung: Payload erreicht zuständige Knoten.
- Rückkopplung: Empfänger können prüfen, bestätigen, widersprechen oder korrigieren.
- Spur: Erzeugung, Zustellung und Rückkopplung bleiben nachvollziehbar.

## Protokollregeln

1. Jeder erhebliche Payload muss einen Unterschied benennen.
2. Jeder erhebliche Payload muss eine zuständige Empfängergruppe definieren.
3. Die Empfängergruppe darf nicht privat monopolisiert werden.
4. Die Empfängergruppe darf nicht durch chaotischen Broadcast ersetzt werden.
5. Jeder zuständige Knoten muss adressierbar sein oder sein Ausschluss muss begründet werden.
6. Jede Zustellung muss Rückkopplung ermöglichen.
7. Jede erhebliche Zustellung muss eine Spur hinterlassen.
8. Kein Final-Pass ohne Payload, Empfängergruppe, Rückkopplung und Traceability.

## Implementierter Minimaltest

Der ANSI-C-Verifier enthält einen Multicast-Selftest:

- drei zuständige Knoten,
- ein relevanter Payload,
- Zustellung an alle zuständigen Knoten,
- Rückkopplung von allen zuständigen Knoten,
- Traceability vorhanden.

Dieser Test ist kein Netzwerkstack. Er ist das kleinste ausführbare Modell des Protokollprinzips.

## Fehlklassen

- `MULTICAST_EMPTY_GROUP`: keine zuständige Empfängergruppe.
- `MULTICAST_MISSING_DELIVERY`: zuständiger Knoten wurde nicht erreicht.
- `MULTICAST_MISSING_FEEDBACK`: Rückkopplung fehlt.
- `MULTICAST_MISSING_TRACE`: Spur fehlt.
- `UNICAST_PRIVILEGE_AS_JUSTICE`: ein einzelner Knoten monopolisiert relevante Information.
- `BROADCAST_CHAOS_AS_JUSTICE`: undifferenzierte Öffentlichkeit ersetzt Zuständigkeit.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
