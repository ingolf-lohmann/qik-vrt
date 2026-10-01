<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Prozessortakt und menschliche Berichtstaktung

Ingolf Lohmann verlangt die maschinelle Prüfung mit jedem Prozessortakt.
Die wöchentliche Ausgabe eines Briefings an Menschen ist eine eigene
Produktentscheidung. Sie darf die maschinelle Prüffrequenz nicht bestimmen.
Diese Anforderung gehört zur Repository-Architektur; ein Chat-Zeitplan ist
kein Nachweis ihrer Erfüllung. Der maschinenlesbare Vertrag steht in
`policy/QIKVRT_PROCESSOR_CLOCK_CONTRACT_V1.json`.

## Ausführbarer Referenzpfad

Die Erweiterung verwendet den vorhandenen synchronen ANSI-C90-Kern
`src/effect_ack_core.c` und dessen fünf EFFECT_ACK-Zustände. Es gibt keinen
zusätzlichen Scheduler und keine zweite Ausführung des Wochenbriefings.

Ein einzelner Treiber besitzt einen `qikvrt_effect_ack_clock`-Kontext und
initialisiert ihn mit `QIKVRT_EFFECT_ACK_CLOCK_INITIALIZER`. Nach überprüfter
Zulassung seiner Taktdomäne bindet er mit `qikvrt_effect_ack_clock_init`
eine von null verschiedene Epoche und den ersten Zyklus. Die Zulassung ist
eine Integrationspflicht; die C-Funktion authentifiziert den Treiber nicht.

Für jeden Zyklus ruft dieser Treiber `qikvrt_effect_ack_clock_tick` genau
einmal mit der gebundenen Epoche, der aktuellen Zyklusnummer und einem
aktuellen, überprüften Entscheidungssnapshot auf. Jede akzeptierte Flanke
bewertet den vollständigen bestehenden Kern neu. Es gibt keinen Teiler,
Timer, Cache-Hit oder übersprungenen Zyklus. Gleich gebliebene Eingangswerte
dürfen dasselbe Ergebnis erzeugen; ein früheres DONE wird nicht übernommen.

| Eingang oder Übergang | Wirkung des Referenzkerns |
| --- | --- |
| Erwartete nächste Zyklusnummer und aktuelle Eingaben | Neue Kernbewertung; Zähler steigt genau einmal |
| Fehlender Snapshot | BLOCK für diesen Zyklus; kein Wiederverwenden alter Eingaben |
| Lücke, Replay, falsche Epoche oder erschöpfter Zähler | Dauerhaftes Takt-BLOCK; bisherige Abdeckung bleibt ablesbar |
| Erneute Initialisierung desselben Kontextes | Takt-BLOCK; keine Löschung der Fehlergeschichte |
| Freigabeabfrage für andere Epoche oder anderen Zyklus | Keine Freigabe |

Der Treiber muss die aktuelle Flanke selbst beobachten und ausschließlich
`qikvrt_effect_ack_clock_ordinary_release` mit deren Epoche und Zyklusnummer
abfragen. Diese Funktion gibt nur das DONE der zuletzt akzeptierten Flanke
frei. Sie führt selbst keinen Effekt aus. Die bisherigen zustandslosen APIs
bleiben kompatibel; ihre Nutzung beweist keine Taktabdeckung.

Ein Taktfehler kann im selben Kontext nicht durch verspätetes Nachholen oder
Reset repariert werden. Eine neue Epoche erfordert eine separat zugelassene
Taktdomäne mit neuem Kontext sowie die Erhaltung des alten Fehlernachweises.
Parallelzugriffe, uninitialisierter Speicher und Manipulation des Kontextes
gehören nicht zum unterstützten C-Aufrufvertrag.

## Synthesizierbarer Clock-Carrier

`rtl/effect_ack_clock_carrier.vhd` stellt einen echten synchronen RTL-Pfad
bereit. Im frisch untersuchten Mirror-Branch und Main gab es keinen geeigneten
Hardware-Carrier; die Wiederverwendung der C-Funktion allein reicht wegen ihrer
mehreren Maschineninstruktionen nicht für eine Auswertung pro Hardwareflanke.
Die fünf Zustände und die Feldreihenfolge werden übernommen und gegen das
bereits vorhandene, unabhängig formulierte C-Orakel vollständig geprüft.

Der autorisierte Admission-Controller legt eine von null verschiedene Epoche
einmalig an. Die Admission-Flanke wird nicht als Auswertungsflanke gezählt.
An jeder folgenden steigenden `clk`-Flanke wird das gesamte `clock_input_t`
in einem Ereignis abgetastet und `evaluate` genau einmal ausgeführt. Der
Zykluszähler entsteht in Hardware. Snapshot-Epoche und Snapshot-Zyklus müssen
zur gebundenen Epoche und zum Hardwarezähler passen. Lücke, Replay, erneute
Admission, Soft-Reset und Zählererschöpfung verriegeln die Freigabe. Die
Auswertung läuft nach einem Fehler weiter; sie kann den Fehler nicht löschen.

`present` und `verified` sind pro Zyklus erforderlich. Sie authentifizieren
selbst keine Daten: Der vorgeschaltete, autorisierte Verifier muss Fakten,
Effekt-Payload und Kennungen gemeinsam an diese Taktdomäne liefern. Alle
Eingänge einschließlich Admission und Readback müssen die Setup-/Hold-Zeiten
einhalten. Ein asynchroner Bus darf nicht durch einzelne Bit-Synchronizer
angebunden werden; ein geprüfter gebündelter CDC-Adapter wäre ein eigener
Integrationsschritt. Unbekannte Simulationswerte blockieren den Effekt.

Der einzige geschützte Ausgang ist ein registrierter 32-Bit-Payload mit
`effect_commit`. Die Freigabe entsteht ausschließlich aus dem Snapshot dieser
Flanke. `sink_ready` reserviert die bedingungslose Übernahme im folgenden
Ausgangsintervall. Das Interface ist ein Strobe mit vorheriger Reservierung;
ein AXI-Ready/Valid-Empfänger braucht einen eigenen Adapter. Fehlende Reservierung
blockiert den aktuellen Effekt. Es gibt weder Nachholen noch Wiederholen eines
alten DONE. Vollständige Vermittlung aller Firefox-/Systemeffekte ist damit
noch nicht belegt.

`rtl/effect_ack_coverage_witness.vhd` zählt Flanken in einem separaten
sequentiellen Prozess, unabhängig vom Auswertungspuls. An der nächsten Flanke
vergleicht er den vorherigen Auswertungspuls und Zähler mit seiner eigenen
Abdeckung. Auslassung, doppelte Meldung und Replay verriegeln seinen Fehler.
Die Unabhängigkeit betrifft Implementierungslogik, nicht Oszillator oder
Stromversorgung. Wenn die ganze Taktdomäne stehen bleibt, braucht es weiterhin
einen externen Zeit-/Oszillator-Witness.

Ein `readback_request` mit frischer Challenge in `readback_nonce` übernimmt
Epoche, beide Zähler, Fehler, Zustand und letzten Snapshot als einen stabilen
Registerblock. Er beschreibt die unmittelbar vorher vollständig abgeschlossene
Flanke: Bei `evaluated=N` muss `snapshot.cycle=N-1` gelten. `readback_valid`
gilt einen Zyklus; der Registerblock bleibt bis zum nächsten Request unverändert.
Auch dieser Bus braucht außerhalb der Domäne einen gebündelten Transfer.

`tools/qikvrt_effect_ack_clock_readback.py` verlangt vom Leser erwartete
Challenge, Epoche und Fensterende; es lehnt fehlende, widersprüchliche,
zurückgesetzte oder nichtkanonische Telemetrie ab. Selbst kohärente DONE-
Telemetrie ergibt in V1 Exit 20 / `HOLD_PHYSICAL_BINDING_OPEN`,
`ordinary_release=false` und `effect_ack_done=false`. Frei gesetzte
`board_verified`-Felder werden nicht als Beleg akzeptiert.

Power-Reset löscht volatile Register. Vor neuer Admission müssen frühere
Epochen und Fehler extern erhalten und Epochenwiederholung verhindert werden.
Eine reine RTL-Testfixture, die Reset setzt, beweist diese Persistenz nicht.

### Reproduzierbare Prüfung

```sh
sh tools/bootstrap-runtime.sh --profile clock --install --accept-third-party
make effect-ack-clock-carrier-test
```

Der bestehende Bootstrap-/Cache-Pfad wird um das SHA-256-gebundene GHDL 6.0.0
für Ubuntu 24.04 x86_64 erweitert. Jede Nutzung vergleicht alle installierten
Dateien mit dem verifizierten Archiv. Installation erfolgt gestuft und wird
bei fehlgeschlagener Endprüfung zurückgenommen. Fehlendes GHDL ist im Boot-
Check CONTINUE, im verpflichtenden Carrier-Test BLOCK. CI provisioniert es
ausdrücklich vor `make test`; ein fehlender Simulator überspringt keinen Test.
GHDL-Synthese liefert eine generische Netzliste; sie ersetzt keinen Board-
Timing-Nachweis. Primärquelle: https://ghdl.github.io/ghdl/using/Synthesis.html

## Noch offene physische Bindung

Die C-Erweiterung ist ein ausführbares Modell aufeinanderfolgender Flanken.
Ihre Ausführung auf einer CPU benötigt mehrere Maschineninstruktionen.
Numerische Zykluslabels oder erfolgreiche Softwaretests beweisen deshalb
keine Prüfung an jeder physischen CPU-Flanke. Ein Timer, Betriebssystemtask,
Browser-Event-Loop, GitHub-Workflow oder ChatGPT-Zeitplan erfüllt die
Prozessortaktanforderung nicht durch eine höhere Abruffrequenz.

Für eine produktive Bindung sind weiterhin erforderlich:

1. Identität, Zulassung, Reset- und Epochenregeln der tatsächlichen Taktdomäne.
2. Ein an jede relevante Hardwareflanke gebundener Prüfpfad mit
   Timing-Nachweis; der RTL-Pfad stellt die Logik bereit, aber noch keine
   Board-/Pin-Bindung, Platzierung, STA oder Programmer-Rücklesung.
3. Atomar aktuelle, authentifizierte Eingaben und vollständige Vermittlung
   jedes geschützten Effekts durch die aktuelle Freigabe.
4. Ein unabhängiger Abdeckungsnachweis für das beanspruchte Zyklusfenster,
   der auch ausbleibende Aufrufe, Taktverlust und Neustarts erkennt.

Diese Bindung ist für den Firefox-MVP in diesem Kandidaten OPEN. Der
Referenzkern kann eine erst beim nächsten Aufruf sichtbare Lücke erkennen;
ohne unabhängigen Treiber kann er einen vollständig ausbleibenden Aufruf
nicht beobachten. Weder die gesamte MVP-Laufzeit noch ein physischer
Prozessortakt wird hier als DONE ausgegeben.

## Prüfung und Herkunft

`make effect-ack-core-test` kompiliert unter strict ANSI-C90 und prüft alle
19 booleschen Eingangsfelder mit allen fünf Entscheidungen gegen den
vorhandenen unabhängigen Zustandsorakel. Dabei wird ein zusammenhängendes,
synthetisches Fenster von 2.621.440 Zyklen durchlaufen. Zusätzliche Fälle
prüfen neue Eingaben, fehlende Eingaben, Replay, Lücken, Epoche und Überlauf.
`tests.test_effect_ack_conformance` schützt die bestehende Referenzsemantik.
Der konkrete Quellstand und die Ergebnisse sind in
`state/work_units/QIKVRT_PROCESSOR_CLOCK_CORE_V1.json` gebunden.

Der Kalender-/Digital-Twin-Pfad aus Mirror-PR #426 ist ein separater
Ausgabepfad. Dieser Kandidat setzt ihn nicht voraus und verändert ihn nicht.
Er entstand auf dem überprüften Mirror-Quellstand; er behauptet weder
Authority-Promotion noch Gleichheit zwischen Authority und Mirror.
