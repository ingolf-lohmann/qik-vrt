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

# Formales Modell V2.2: Multicast bis zur Ontologie des Unterschieds

## 1. Grundobjekte

Ein System wird als gerichteter Graph `G = (V, E)` modelliert.

- `V`: Knoten, also Menschen, Geräte, Institutionen, Dokumente, Prüfer, Zeugen oder Zustände.
- `E`: Kanten, also Kommunikation, Zugriff, Weiterleitung, Prüfung, Rückkopplung oder Verantwortungsbezug.
- `P`: Payload, also eine relevante Information, Aussage, Spur, Entscheidung oder Warnung.
- `R(P)`: zuständige Empfängergruppe für Payload `P`.
- `D(P)`: tatsächlich erreichte Empfängergruppe.
- `T(P)`: Traceability-Nachweis für Erzeugung, Zustellung, Prüfung und Rückkopplung.

## 2. Multicast-Anschlussfähigkeit

Multicast ist hier streng gemeint:

`sender -> P -> R(P)`

Eine relevante Information ist multicastfähig, wenn sie nicht privat monopolisiert und nicht chaotisch an alle gebroadcastet wird, sondern an die zuständigen Knoten zustellbar, prüfbar, rückkoppelbar und spurfähig ist.

Formal:

`MULTICAST_OK(P) := R(P) != empty AND D(P) covers R(P) AND T(P) exists`

Nicht jeder muss alles wissen. Aber kein zuständiger Knoten darf systematisch außerhalb des Zustellpfads liegen.

## 3. QIKVRT-Mapping

- `Q`: Ein Unterschied `d` wird messbar oder markierbar.
- `I`: Aus `d` entsteht Information `i`.
- `K`: `i` erzeugt oder erklärt Wirkung `k`.
- `V`: Zuständige Knoten prüfen `i` und `k`.
- `R`: Rückkopplung korrigiert, bestätigt oder begrenzt die Wirkung.
- `T`: Jeder erhebliche Übergang hinterlässt eine Spur.

## 4. Ontologie des Unterschieds

Minimalaxiom:

`Ohne Unterschied keine Information.`

Folgekette:

`Unterschied -> Information -> Kausalität -> Verantwortung -> Verifikation -> Rückkopplung -> Traceability`

Die Ontologie ist nicht Schmuck. Sie ist der unterste Implementierungsgrund:

- Ein Payload ohne Unterschied ist leer.
- Eine Information ohne Träger ist nicht zustellbar.
- Eine Wirkung ohne Spur ist nicht verantwortbar.
- Eine Zustellung ohne zuständige Empfänger ist kein gerechter Multicast.
- Ein Prüfsystem ohne Rückkopplung ist nicht lernfähig.

## 5. Gerechtigkeitsformel

`QIKVRT <=> Multicast <=> Gerechtigkeit`

Diese Formel bedeutet nicht, dass TCP/IP selbst Moral erzeugt. Sie bedeutet: Das Protokollprinzip definierter Gruppenadressierung ist die technische Strukturform einer gerechten Informationsordnung: relevante Information an zuständige Knoten, mit Prüfung, Rückkopplung und Spur.

## 6. Verbotene Kurzschlüsse

- Kein Broadcast-Chaos als Gerechtigkeit.
- Kein Unicast-Monopol als Wahrheit.
- Kein Payload ohne Herkunft.
- Keine Wirkung ohne Verantwortungsprüfung.
- Kein Final-Pass ohne Traceability.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
