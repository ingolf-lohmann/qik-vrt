<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Gebundener 68000-/Lean-Nachweis zu PR #593

Quellgegenstand: `ingolf-lohmann/qik-vrt`, PR #593,
HEAD `dbed9072d41727fc4e45abd0cedee4cf3c61c790`,
TREE `b6b32d8ba0c3de25c1cd8d4d69210c482ad0ca3e`.
`source-commit-github.json` und `source-pr-github.json` sind die unveränderten
JSON-Antwortinhalte des GitHub-Connectors. Transportheader standen darüber
nicht zur Verfügung. Ein späterer Commit bewahrt diese Quellenbindung und
erhält dadurch keine eigene funktionale HEAD/TREE-Abnahme.

## Ergebnis und genaue Aussage

`report.json` hält 10.248/10.248 identische Softwareentscheidungen fest.
Die C90-Vorausberechnung wurde vor der Ausführung der optimierten C-Version,
der Python-Referenz und des echten 68000-ELF fixiert. Der originale lokale
Ledger hielt das Commitment fest; die originale Terminal-Funktion las es über
eine getrennte schreibgeschützte SQLite-Verbindung zurück. Die Ereignisse
`OBSERVE`, `EFFECT`, `READBACK` sind in `native-events.json` exportiert.

`commitment.json` bindet Eingaben, Quellen, Compiler, Flags und Binärhashes.
Sein kanonischer SHA-256-Anker ist
`edfc255a5acf30d8a32f5a082aeeb0856d43a8a019a919b6a57a5be6ad2389dc`.
Die Datei enthält zusätzlich einen abschließenden Zeilenumbruch; ihr
Dateihash ist deshalb vom kanonischen Anker zu unterscheiden.

| Beobachtung | Ergebnis |
| --- | --- |
| Native C90-Vorausberechnung, optimiertes C und Python | Alle 10.248 Fälle identisch |
| Tatsächliche QEMU-CPU | `m68000`, Linux-Nutzerraum-ABI |
| `m68000-observed.bin` | 10.248 Zustandsbytes, SHA-256 `ccf64a7685f4227b60b4ae72fab387a8a101d30ca5483948fd078271870fa7b4` |
| `prediction-m68000.elf` | SHA-256 `b6a9690f563da92be51880af1c940463d4ac650d4c76b554f1b390813247ea5b` |
| Lean-Kernel über Lake | 257 konkrete Batch-Gleichheiten, alle 10.248 Zustände |
| Axiom-Audit dieser Beobachtungssätze | Jeweils leer |
| Absichtlich geändertes erstes Zustandsbyte | Lean verwirft die Gegenprobe |
| Vollständiges `make test` auf dem genannten Quellstand | Exit 0; 38 Python-Suiten mit 1.720 Tests plus weitere Make-Prüfungen |

Das nicht ausgewählte Emulatorprofil wird innerhalb der portablen
`make test`-Strecke ausdrücklich übersprungen. Der hier separat ausgeführte,
quellgebundene Lauf enthält die echte Emulator- und Kernelprüfung.
`validation.json` und `make-test-source.log` binden die lokale Testabnahme.
Die CI-Beobachtungen sind zeitgebundene Zusatzbelege; ein noch laufender
Workflow ist kein vollständiger CI-PASS.

Das Feld `build.m68000_execution_verified: false` stammt aus dem unveränderten
Commitment **vor** der Ausführung. Das Ergebnisfeld
`report.m68000_execution_verified: true` beschreibt die spätere erfolgreiche
Ausführung. `proof_class` bezeichnet den Implementierungsvergleich;
`kernel_receipt` enthält gesondert die formale Aussage zur endlichen
Beobachtungsgleichheit.

## Artefakte unabhängig prüfen

`ARTIFACT_MANIFEST.json` zählt die Dateien dieses Ordners mit Größe und
SHA-256 auf und schließt sich selbst aus. Das übergeordnete Repository-
Integritätsmanifest bindet wiederum dieses Manifest. Die unveränderten
Commitment-, Ereignis-, Ausgabe- und Beweisdigests wurden nach dem Kopieren
erneut geprüft. Die drei gleichlautenden Textausgaben sind absichtlich als
getrennte Beobachtungen aufbewahrt; Git dedupliziert deren Inhalt.

Die fünf `Observation-*.lean` entstehen aus den tatsächlichen Emulatorbytes.
Ihre Logs enthalten zusammen 257 leere Axiom-Audits. `lean-model.log` und
`lean-profile.log` dokumentieren die Modell-/Profilübersetzung;
`RejectedObservation.lean` und `lean-negative.log` die gescheiterte Gegenprobe.
Die Hilfssatz-Axiome des Profils stehen separat im Profil-Log und werden
nicht als leere Axiomliste umgedeutet.

Reproduktion: Den genannten Quellstand auschecken, die Werkzeuge gemäß
`runtime/toolchains/M68000_PROOF_POC_LOCK.json` provisionieren und die vier
Aufrufketten aus der zugehörigen Dokumentation setzen. Dann
`make emulated-prediction-contract` ausführen. Dieser Make-Pfad prüft das
Profil als ausdrücklich benannte Fixture. Für einen echten Repository-
Gegenstand muss `run_profile` zusätzlich einen frisch ermittelten
`exact_subject` erhalten; genau das wurde im gespeicherten Lauf getan.
Der Harness prüft die gepinnten Executable-Hashes, bevor er diese startet.

## Offene Grenzen und Produktivgates

Die Messung läuft auf einem gemeinsamen Host mit bekannten Eingaben und
kontrollierter Uhr. Die Zeitstempel sind lokale Beobachtungen. Sie ersetzen
keinen unabhängig verwahrten externen Zeitanker und keinen unabhängigen Host.
Compiler-, Emulator- oder ISA-Korrektheit, ein physischer Effekt, ein
Geschwindigkeitsgewinn und die Vorhersage unbekannter Zufallseingaben sind
hierdurch nicht bewiesen. Die historischen Zufallskontrollen bleiben erhalten.

`delivery-snapshot.json` wurde über den vorhandenen öffentlichen Monitor
beobachtet und anhand der exakten gespeicherten Bytes zurückgelesen;
`delivery-readback.json` bindet den SHA-256-Wert
`80753360c0a92546bd0af8d2314710003cfc953f52ccff4b0509ba1c21b45a59`.
Am 24. Oktober 2026 um 00:14:44 UTC lieferte `raumzeitterminal.de` HTTP 525.
Die Mesh-Runtime ist weiterhin `UNKNOWN`; es ist kein Runtime-Endpunkt
veröffentlicht. Historische Zugriffsfehler im Snapshot sind als solche
erhalten, einschließlich ihrer ursprünglichen Zeiten und nicht wiederholten
Anfragen. Identität des privaten aktuellen Aufrufers und lokale Writer-
Metadaten wurden nicht in diese öffentliche Evidenz übernommen.

Main-Integration, unabhängige Reproduktion, produktiver Mesh-Betrieb und
exakte Domain-Auslieferung bleiben getrennte offene Gates.
`effect_ack_done` bleibt ausdrücklich `false`.

Anforderung und Freigabe: Ingolf Lohmann.
Implementierung und technische Prüfung: OpenAI Codex.
