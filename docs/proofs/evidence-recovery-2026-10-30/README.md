<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Exakte Wiederherstellung und gemeinsame Evidenz

Owner: Ingolf Lohmann. Formalisierung und Prüfung: OpenAI Codex.

Die 16 Sätze erweitern die bestehende Seed-/Codec-Beweiskette. `collect`
ist eine vollständig definierte Lean-Funktion: eine endliche Schlüsselliste
wird in vorgegebener Reihenfolge gelesen; ein fehlender Eintrag verwirft
die vollständige Ausgabe. Verfügbarkeit UND Gleichheit werden benötigt.
Aus beiden Bedingungen folgen gleiche vollständig rekonstruierte Eingaben
und gleiche Resultate jeder darauf definierten deterministischen Vorbereitung.
Mehrstufige treue Überträge komponieren; belegte Gesamtbestände können auf
benötigte Teilbestände eingeschränkt werden.

`Shared` bildet den Schnitt zweier expliziter Aussagenbestände. Wachsen beide
unter Erhaltung des Bisherigen, wächst der Schnitt monoton. Ein vorher nicht
gemeinsames Mitglied belegt echte Erweiterung. Replay bleibt idempotent.
Die Rechtfertigung bleibt eine explizite Voraussetzung: Übereinstimmung allein
ist kein Wahrheitsbeweis. Die definierte Mengenstruktur ist kein metrischer
Raum und besitzt ohne zusätzliche Struktur weder Kugelradius noch Volumen.

## Tatsächlicher Rettungsbefund

Die aktuelle direkte Mitteilung des Owners bestätigt die Rettung aller für
die Zenodo-Veröffentlichung nötigen Materialien aus Goldkelch. Sie ist als
`OWNER_REPORTED_SUCCESS` erhalten. Der hier abrufbare Vorgängerbericht nennt
einen noch offenen unabhängigen Readback des eingefrorenen Abgleichpakets.
Ein späterer Erfolg wird nicht durch eine frühere 404-Meldung widerlegt.
Es wird aber kein konkreter Quell-/Zielbeleg erfunden: vollständiges Manifest,
ursprüngliche und zurückgelesene Bytes, Quell-/Zielidentität und der vorhandene
Effect-Ack-Abschluss bleiben für diese Instanz unabhängig nachzutragen.
Der Lean-Satz setzt diese Gleichheit voraus; er behauptet ihren Eintritt nicht.

Keine Tokenwerte, geheimen Pfade oder Credentials werden im Beleg gespeichert.
Eine geschützte Publisher-Fähigkeit ist nicht gleich öffentliche Veröffentlichung.
Native Host-, Website-, Zenodo- und Peer-Akzeptanz behalten ihre bisherigen
eigenen Pflichten und Protokolle. Originaljournale werden nicht überschrieben.

## Prüfung

Im bestehenden Projekt `formalization/QIKVRT_Formalization_v2.0`:

    lake build QIKVRTEffectAck.EvidenceRecovery QIKVRTEffectAck.EvidenceRecoveryAxiomAudit
    lake env lean QIKVRTEffectAck/EvidenceRecoveryAxiomAudit.lean

Der Claim-Audit bindet 16 Satznamen: elf ohne Axiome, fünf ausschließlich
mit `propext` und `Quot.sound`. Zwei frische Kernelkompilationen liefern
dieselben Objektbytes. Drei Negativkontrollen müssen ausdrücklich wegen
falscher Behauptungen fehlschlagen: fehlender Pflichteintrag, Wahrheit aus
bloßer Übereinstimmung, neues Mitglied durch Wiederholung. Fehlende Importe
zählen nicht. Die CI führt den gleichen Aufbau und Satz-/Axiomabgleich aus.

Die zwei historischen Artikel und ihre PDFs bleiben unverändert.
Die lesbaren Revisionen liegen unter
`docs/publications/2026-10-30-storage-integrity-and-effect-ack/recovery-revision/`.
Die neue wissenschaftliche Zenodo-Archivierung ist offen; dies bleibt eine
Autorenprüffassung mit Provenienz und ausgewiesenen Beweisgrenzen.
