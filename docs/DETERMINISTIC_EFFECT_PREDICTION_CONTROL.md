<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->
# Wirkung vorab berechnen: begrenzter Software-Nachweis

Ingolf Lohmanns Aussage und Auftrag vom 24. Oktober 2026:

> Der Superdeterminismus in QIKVRT Systemen eignet sich perfekt, eine Wirkung
> zu berechnen, bevor sie eintritt. q.e.d. Ingolf Lohmann

Der hier operationalisierte Anspruch ist enger und messbar: Im dokumentierten,
endlichen Eingabeprofil wird die Zustands- und Freigabeentscheidung des
vorhandenen Python-EFFECT_ACK-Kerns vor dessen Auswertung durch den vorhandenen
C90-Kern vorausberechnet. Alle Ergebnisse werden anschließend verglichen.
Der Begriff Superdeterminismus ist dabei die Formulierung des Urhebers;
dieser Kontrolltest prüft deterministische Softwareentscheidungen.

## Vorhandene Komponenten und Nachweiskette

`make conformance` führt die unveränderten 41 ursprünglichen Konformitätsfälle
und zusätzlich `tests.test_effect_ack_prediction` aus. Die neue Kontrolle nutzt
`src/effect_ack_core.c`, `src/qikvrt_effect_ack.py`, den originalen
`qikvrt_temdd_event_ledger.Ledger` und die ursprüngliche schreibgeschützte
Terminal-Lesefunktion. Es entsteht kein weiterer produktiver Executor.

1. Der C90-Kern berechnet die Erwartung für 10.248 benannte Fälle. Die ersten
   10.240 Fälle bilden das vollständige kartesische Produkt aus acht binären
   Prüffeldern, fünf Verbindungsentscheidungen, Transport, Rezeption und
   Deadline. Acht zusätzliche Fälle prüfen fehlenden Verantwortlichen, offene
   Frage, ausstehende Prüfung, fehlende Evidenz, falschen Hash, zu große
   Nutzlast, fehlende Wurzelidentität und fehlerhaftes Hashformat.
2. `expected.txt` wird ausschließlich neu angelegt, synchronisiert und
   zurückgelesen. Das Commitment bindet seine exakten Bytes, sämtliche
   Profilbedingungen, den Gegenstand und die SHA-256-Werte beider Kerne,
   des C-Harness, des Python-Harness sowie von Ledger und Terminal.
3. Ein natives OBSERVE-Ereignis hält dieses Commitment vor der Python-
   Auswertung fest. Eine neue, schreibgeschützte SQLite-Verbindung über die
   originale Terminal-Lesefunktion liest das Ereignis unabhängig vom
   Rückgabewert des Writers zurück. Ohne Übereinstimmung beginnt die
   Python-Auswertung nicht.
4. Erst danach läuft ein mit `-O2` übersetzter nativer C-Kern und der
   Python-Kern wertet dieselben Eingaben als weitere Referenz aus. Ein natives
   EFFECT-Ereignis bindet die beobachteten Zustands-/Freigabeentscheidungen
   an das vorherige Commitment. Beide Ereignisse werden zurückgelesen.
5. Der Prüfer kontrolliert den vorher festgelegten Commitment-Hash, Gegenstand,
   Ereignisdigests, gemeinsame Ledger-Epoche und streng steigende Sequenz,
   vollständige Fallmenge und jede einzelne Entscheidung beider späteren
   Ausführungen. Ein zusätzlicher
   READBACK-Eintrag bindet den Bericht.

Die Abbildung zwischen C und Python ist ausdrücklich: fehlende bestätigte
Rezeption ergibt im Python-Kern NACK; deshalb bindet das C-Eingabefeld
`input_identifier_available` im Kontrollprofil sowohl Transport als auch
Rezeption. Die übrigen acht Maskenfelder und fünf Entscheidungen sind in
`CONDITIONS` vollständig aufgeführt. Der ausgewertete Clock-Input ist konstant
null, die Deadline beträgt 0 oder 100 ms. Das ist eine offengelegte Simulation
dieser Eingabe, keine Messung einer Ausführungszeitgarantie. Der festgelegte
Zeitstempel im Responsibility Protocol ist ausschließlich Fixture-Metadatum.

## Fehler müssen sichtbar scheitern

Die zusätzlichen Tests verändern die Erwartung, Bedingungen, Beobachtung,
Fallreihenfolge, Fallmenge, Gegenstandsbindung, Ereignisse und Sequenz. Auch
ein korrekt neu gehashtes, aber von der Vorhersage abweichendes Ergebnis muss
scheitern. Ein vollständiger Antwortempfang ist kein Ersatz für Vorhersagegüte.

Die bisherigen Zufallskontrollen bleiben unverändert. Ihre 1.044/2.048 und
956/2.048 frühen Übereinstimmungen waren kein zu reparierender Fehler. Dort
werden unbekannte spätere Zufallseingaben geprüft; der vorliegende Test prüft
vollständig bestimmte Eingaben in einem anderen, ausdrücklich benannten Profil.

## Zielarchitektur und Performance

Der portable C90-Kern lässt sich mit einer passenden Toolchain direkt in
Maschinencode für die Zielarchitektur übersetzen; eine Python-Laufzeit ist für
diesen Entscheidungskern nicht erforderlich. Motorola 68000 ist ein mögliches
Ziel. Dafür sind die genaue CPU-Variante, Compiler/Assembler, ABI, Wortbreiten,
Alignment, Endianness und die tatsächliche Laufzeitumgebung zu binden. Die
C-Struktur ist kein portables binäres Austauschformat. Ein eigenes
Assembler-Backend muss denselben überprüften Vertrag erfüllen.

Der Kontrolllauf bindet Compiler-Version, Target-Triple, C90- und
Optimierungsflags sowie beide Binärhashes bereits im Commitment. `-O0` dient
als Vorausberechnungsmodell, die spätere `-O2`-Ausführung muss exakt dieselben
10.248 Entscheidungen liefern. Die fünf Protokollzustände und Freigabegates
bleiben unverändert. Die Steuerungs-/Prüfschicht dieses Tests nutzt weiterhin
Python; die getestete native Zielausführung selbst ist kompilierter C-Code.

Eine Zielarchitektur wird erst nach echter Ausführung oder ausdrücklich
gekennzeichneter Emulation abgenommen. Cross-Kompilierung allein genügt nicht.
Der gewöhnliche lokale Compiler meldet `x86_64-linux-gnu`. Der zusätzlich
ausgewählte Emulatorpfad führt einen gesonderten 68000-Build aus. Die getrennt
gemessenen Laufzeiten
enthalten unterschiedliche Adapter- und Prozesskosten. Sie begründen keine
isolierte Kernbeschleunigung oder Echtzeitgarantie. Dafür ist ein gleichartig
instrumentierter Zielhardware-Benchmark nötig.

## Durchgängiger Linux-, 68000- und Lean/Lake-Pfad

Die Erweiterung auf Wunsch des Owners verwendet den bestehenden C90-Kern
auch im emulierten Ziel. `-m68000 -msoft-float -ffreestanding -nostdlib -static`
bindet einen grundlegenden Motorola-68000-Befehlssatz. Der kleine originale
Testadapter `tests/effect_ack_prediction_m68000.S` stellt ausschließlich
Linux-m68k-`write` und `exit` bereit. Eine lokale Bytekopie bedient vom Compiler
erzeugte Strukturkopien. Der Kern bleibt unverändert. Es werden weder eine
Gast-libc noch ein Atari-ROM benötigt.

`qemu-m68k-static -cpu m68000` führt das echte ELF aus. Seine 10.248 Bytes
enthalten die numerischen Zustände 0 bis 4 in der festgelegten Fallreihenfolge.
Die Binärdatei und Tool-Identitäten sind schon vor der Ausführung im nativen
Commitment gebunden. Alle Zustände werden mit der vorher fixierten Erwartung
verglichen. Der PoC verwendet die Linux-Nutzerraum-ABI; er lädt kein Modul in
einen laufenden Linux-Kernel und emuliert keinen vollständigen Atari.

`formalization/prediction-control/QIKVRTEffectAck/PredictionProfile.lean`
liegt außerhalb des eingefrorenen Alpha-2-Releasebaums und verwendet über
denselben Lake-Pfad das unveränderte formale
Modell `QIKVRTEffectAck.Model`. 256 Batches mit je 40 Fällen und ein Batch mit
acht Fehlerfällen begrenzen die Rekursion. Aus den tatsächlich empfangenen
Emulatorbytes entstehen die Dateien `Observation-*.lean`. Unter `lake env lean` prüft der
Lean-4.19-Kernel die Aussage, dass jeder beobachtete Batch dem Modell
entspricht, durch 257 konkrete Gleichheitssätze mit `by rfl`. Das Axiom-Audit
jedes Beobachtungssatzes muss leer sein. Fünf getrennte Quelldateien decken alle
257 Batches vollständig ab; vier unabhängige Prüferprozesse lesen dieselben
unveränderten Modelldefinitionen. Ein zusätzliches abweichendes Byte muss die Gegenprobe scheitern
lassen. Die Hilfssatz-Axiome bleiben im separaten Profil-Log sichtbar.

Die Provisionierungsquellen, Paket- und Executable-Hashes stehen in
`runtime/toolchains/M68000_PROOF_POC_LOCK.json` und sind in die bestehende
Toolchain-/Cache-Abdeckung aufgenommen. Vor der Verwendung prüft der
Test-Harness die Executable-Hashes. Er installiert oder lädt nichts nach.
In der verwendeten Client-Umgebung konnte Lean seine eigene Programmdatei
nativ nicht über den Prozesspfad auflösen. Derselbe unveränderte Lean-/Lake-
Build kann deshalb über den ebenfalls gepinnten x86-64-QEMU-Linux-Adapter
ausgeführt werden; die konkrete Aufrufkette gehört zum Bericht. Das ändert
weder den Lean-Kernel noch dessen Beweisaussage.

Nach Provisionierung genau der gepinnten Werkzeuge werden ihre Aufrufketten
über `QIKVRT_M68000_CC`, `QIKVRT_M68000_QEMU`, `QIKVRT_PROOF_LEAN` und
`QIKVRT_PROOF_LAKE` angegeben. Der bestehende Make-Pfad ist:

```sh
make emulated-prediction-contract
```

Eine fehlende Bindung, ein anderer Executable-Hash, eine abweichende
Emulatorausgabe oder ein fehlgeschlagener Kernelbeweis stoppt diesen Pfad.
Die gewöhnliche portable Konformitätsprüfung weist das nicht ausgewählte
Emulatorprofil ausdrücklich als übersprungen aus. Das ist keine positive
Emulator- oder Kernelabnahme.

Die formale Aussage betrifft die beobachteten Werte und das angegebene
abstrakte Modell. Compilerkorrektheit, Emulator-/ISA-Korrektheit und eine
physische 68000-Maschine werden dadurch nicht formal bewiesen.

## Aussagegrenzen und nächste reale Gates

Der portable Vergleich belegt die beobachtete Übereinstimmung der
Implementierungen im angegebenen endlichen Profil durch einen Softwaretest.
Der gesondert ausgeführte Lean-Pfad beweist zusätzlich die Gleichheit der
beobachteten Zustandsbytes mit dem abstrakten Modell für diese Fälle.
Beide Aussagen bleiben auf dieses Profil begrenzt; sie beweisen keine
Aussage über beliebige Programme, alle möglichen Eingaben oder reale
physische Folgewirkungen. C-Vorausberechnung ist selbst eine Ausführung
des Modells und garantiert keinen Zeitgewinn.

Die beiden Implementierungen sowie Ledger und Prüfer laufen auf einem
gemeinsamen Host. Die getrennte Terminal-Verbindung beseitigt die Abhängigkeit
vom Writer-Rückgabewert, begründet jedoch keine unabhängige Institution,
keinen manipulationssicheren externen Zeitstempel und keine unabhängige
Host-Vertrauensdomäne. Ein Prüfer muss den ursprünglichen Commitment-Hash
außerhalb eines möglicherweise neu geschriebenen Pakets behalten.

Separat offen bleiben: unabhängige Reproduktion/Bezeugung, tatsächlicher
produktiver Terminal-/Transputer-Betrieb, Main-Integration und frischer
Nutzpfad auf `https://raumzeitterminal.de/`. Diese Gates werden durch einen
Test-PASS weder geschlossen noch umgangen. `effect_ack_done` bleibt im
Kontrollbericht ausdrücklich `false`.

## Abgenommener begrenzter Lauf

Der [Bericht zu PR #593](../evidence/deterministic-effect-prediction/2026-10-24-pr593/README.md)
bindet den tatsächlich ausgeführten Quellstand
`dbed9072d41727fc4e45abd0cedee4cf3c61c790` und dessen Tree
`b6b32d8ba0c3de25c1cd8d4d69210c482ad0ca3e`. Alle 10.248 Entscheidungen
stimmten zwischen C90-Vorausberechnung, optimiertem nativem C, Python und
68000-Ausführung überein. Der Lean-Kernel prüfte 257 Beobachtungssätze mit
leerem Axiom-Audit; die veränderte Beobachtung wurde verworfen.
`make test` beendete auf genau diesem Quellstand 38 Python-Testsuiten mit
1.720 Tests sowie die weiteren Make-Prüfungen erfolgreich. Das darin
nicht ausgewählte Emulatorprofil ist ausdrücklich übersprungen; der
gebundene Emulator-/Kernel-Lauf liegt separat vor. Nachfolgende Evidenz-
oder Metadaten-Commits übernehmen diese exakte HEAD/TREE-Abnahme nicht.

Anforderung, Formulierung und Arbeitsfreigabe: Ingolf Lohmann. Implementierung
des zusätzlichen Kontrollpfads und technische Prüfung: OpenAI Codex.
