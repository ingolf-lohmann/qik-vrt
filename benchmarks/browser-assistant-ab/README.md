<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Persönlicher Browserassistent: Unterbrechungs-A/B-Vertrag

Produkt unter Prüfung: **Universales Raumzeit-Terminal** (technischer Name,
freigegeben durch Product Owner Ingolf Lohmann am 2026-10-05). Der persönliche
Browserassistent bleibt der konkrete Anwendungsfall dieses A/B-Vertrags.
Die Benennung ändert weder Messvertrag noch ausstehende Produktmessungen.

**Stand dieses Nachfolgers: Harness, synthetische Fixtures und opt-in
Personal-Quelladapter vorhanden;
produktnaher End-to-End-Lauf nicht ausgeführt; Kundennutzen offen.**

Der Versuch soll die offene Produktfrage beantworten: Kann ein persönlicher
Browserassistent eine unterbrochene Recherche-/Dokumentationsaufgabe mit weniger
Zeit, erneutem Kontext, falschen Abschlüssen und menschlichen Eingriffen
fortsetzen? Ein erfolgreicher Zustandsabgleich beantwortet diese Frage allein
nicht. Eine technische Referenzmessung oder eine geskriptete Harness-Übung
belegt weder diesen Produktvorteil noch Kaufwürdigkeit.

## Vorhandenes wiederverwenden

Der Standard-Firefox-Client `browser/firefox/qikvrt-terminal/` bleibt unverändert.
`src/qikvrt_effect_ack_http_terminal.py` erhält einen opt-in Adapter auf demselben
Server: `src/qikvrt_personal_assistant.py`, Oberfläche `/personal/` und Manifest
`personal/ingolf-lohmann/firefox-assistant/CAPABILITIES.json`.
Der isolierte `terminal-smoke` prüft Discovery → Prepare → vollständigen
Record-Readback → Commit → frischen State-Readback → Replay-Verweigerung.
Er führt eine lokale Terminaleingabe aus, keine Recherche oder Fortsetzung.
Die Erweiterung speichert Personalisierung und Repository-Beobachtungen; daraus
folgt kein ausführbarer persönlicher Rechercheassistent. Der bestehende
Personal-Vertrag verlangt ein Capability-Manifest und authentifizierten
Runtime-Readback. Das Manifest ist im Nachfolger materialisiert; eine echte
authentifizierte Ausführung bleibt offen. Der Quelladapter verwendet die
OpenAI API mit bereitgestellten Backend-Zugangsdaten, keinen behaupteten
ChatGPT-Pro-/SSO-Pfad. Seine technischen Tests verwenden Transport-Doubles
und bleiben außerhalb der Produkttrials.

Suche vor Erstellung: Main `86d7062f25f174039da0a5df8a856127553036f1`,
Tree `5421dceb17f1ecc0fd3f5c12891ca9c1a12e7cf2`, insbesondere `browser/`,
`src/`, `tools/`, `tests/`, `policy/`, Terminal-Workflow und Personal-Vertrag.
Kein vorhandener Harness verband unterbrochene Browseraufgaben mit allen vier
Produktmetriken. PR #445 ergänzt Gesprächs-/Arbeitskontinuität als Protokoll,
keinen ausführbaren Browserbenchmark. Deshalb ist dieses ergänzende
Messwerkzeug erforderlich. Es ersetzt keinen Produktadapter.

## Design und Ausführungsgrenze

`contract.json` ist der eingefrorene Messvertrag. Der Standardplan umfasst
zwei Aufgaben mit je sechs Paaren, also 24 geplante Einzelversuche. Jedes Paar
enthält dieselbe vollständige Aufgabe, dieselben Quellen und denselben
gespeicherten Zwischenstand einmal als Baseline und einmal als QIK-VRT-Arm.
Die Reihenfolge AB/BA ist pro Aufgabe ausgeglichen und über den festen Seed
reproduzierbar. Unterbrechungsklassen sind Verlust des Assistentenprozesses und
Zurücksetzen des Gesprächskontexts. Die Unterbrechung dauert in beiden Armen
60 Sekunden; das Beobachtungsfenster ab Wiederaufnahmesignal 180 Sekunden.

**Der Fixture-Zwischenstand ist ein kontrollierter Versuchsinput, kein
Nachweis eines bereits ausgeführten Vorlaufs oder eines produktseitigen
Checkpoints.** Für einen späteren Produktlauf müssen beide Vorläufe mit
äquivalenter tatsächlich beobachteter Arbeit und Verlust-/Restart-Belegen
gebunden werden. Eine Konsoleingabe `interruption_observed` ersetzt diese
Belege nicht. In dieser Version bleibt jeder Lauf deshalb eine Harness-Übung.

Vor einem Produktlauf sind Firefox-Build, Erweiterungspaket, OS/Host,
Assistent/Modell, Parameter, Werkzeuge und Cache-/Netzpolitik identisch zu
binden. Die implementierte gewöhnliche Baseline ist derselbe Quelladapter im
normalen Gesprächsmodus: gleiche Provider-Conversations, vollständige lokale
Historie, gespeicherte Antworten und Restore. Eine reale Baseline-Laufzeit
samt Provider-Retention-Readback ist weiterhin nicht gebunden.
Sie muss ihre tatsächlich vorhandenen normalen Restore-Tabs, gespeicherten
Dokumente und Chat-Historie behalten dürfen. Keinen absichtlich geschwächten
Vergleich herstellen. Nur die deklarierte Fortsetzungsfunktion unterscheidet
die Arme. Produktseitig erzeugte Fortsetzung und deren Aufwand sind zu
protokollieren, nicht vom Harness aus den Bewertungsantworten zu erzeugen.

Jeder Lauf verwendet frische isolierte Browser-/Assistentenprofile. Das Oracle
darf dem Assistenten nicht zugänglich sein. Die HTTP-Aufgabenansicht lässt es
weg; für reale Agenten ist zusätzlich eine getrennte Dateisystem-/Tool-Sicht
erforderlich. Gleiche menschliche Teilnehmer lernen bei wiederholten Aufgaben;
AB/BA beseitigt diesen Effekt nicht. Teilnehmercluster, Reihenfolge und
Unterbrechungsklasse sind separat zu berichten. Mehrere Kennungen oder
geskriptete Trials beweisen keine unabhängigen Nutzerbeobachtungen.

## Aufgaben und unabhängige Bewertung

| Fixture | Zu erbringende Arbeit | Fehlerkontrolle |
| --- | --- | --- |
| `research-costs` | Quellgebundener Vergleich aktueller Kosten, Updates und Aussagegrenzen zweier erfundener Anbieter | Überholte Preisliste; kein erfundener Kundennutzen |
| `document-recovery` | Übergabe mit tatsächlichem Export-/Importstatus, nächstem Schritt und Abnahmegrenze | Ungeprüfter Altvermerk „Migration erledigt“ gegenüber aktuellem Nicht-Export |

`fixtures/*.json` bindet Aufgabe, Revisionen, Quellen, gespeicherten Entwurf,
bereits akzeptierte und offene Schritte sowie das getrennte Bewertungsoracle.
Quellenidentitäten sind SHA-256 des kanonischen UTF-8-JSON-Quellenobjekts
(ID, Revision, Text); Fixture-/Checkpointidentitäten ebenso. Der Hash der
gesamten Fixture-Datei wird zusätzlich gebunden. Eine richtige Behauptung mit
veralteter oder fehlender Quellenbindung besteht die Bewertung nicht.

## Metriken

| Metrik | Operative Definition |
| --- | --- |
| Belastbare Wiederaufnahme | Monotone Beobachterzeit ab `resume_signal` bis zu korrektem Arbeitsstand-Probe **und danach** korrekt ausgeführtem offenem Schritt mit richtigen Fakten und Quellenhashes |
| Erneut einzugebender Kontext | Unicode-Codepoints, UTF-8-Bytes und Anzahl menschlicher Kontext-Gesten; Einfügen zählt mit. Automatischer Kontext wird separat erfasst |
| Fehlabschlüsse | Jede unbelegte `step_claim`-/`task_claim`-Meldung zum Zeitpunkt der Meldung; zusätzlich Zahl verschiedener betroffener Schritte. Spätere Korrektur löscht frühere Fehlabschlüsse nicht |
| Menschliche Eingriffe | Eindeutige tatsächliche Kontext-, Instruktions-, Korrektur-, Freigabe-, Restart- oder Eskalationsgesten nach Signal. Feste Beobachter-Protokollschritte separat |
| Aufgabenqualität | Alle geforderten Schrittoutputs am Ende unabhängig richtig, innerhalb des Beobachtungsfensters; Selbstmeldung „erledigt“ ist kein Erfolg |

Zeit für Restore, Reauthentifizierung, Lesen, erneute Eingabe und Prüfung nach
dem Signal gehört zur Latenz. Die Uhr wird nicht erst nach dem Context-Restore
gestartet. Nach dem Horizont werden keine weiteren Arbeitsereignisse als
Messdaten zugelassen; `trial_end(reason=timeout)` schließt den Versuch.
Nicht wiederaufgenommene Versuche erhalten **keine Null-Latenz**: Sie bleiben
mit `null` und Zensierungs-/Abbruchstatus erhalten. Unvollständige, ungültige
und nicht gestartete Versuche bleiben ebenfalls in der geplanten Ergebnistabelle.
Ein vorzeitiger Fehlabschluss gilt nicht als schnelle erfolgreiche Wiederaufnahme.

## Reproduzieren

Aus einem Checkout des Kandidaten, Python 3.12 oder neuer, nur Standardbibliothek:

```bash
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B tools/qikvrt_browser_assistant_ab.py preflight
python3 -B tools/qikvrt_browser_assistant_ab.py plan --output .qikvrt/runtime/browser-ab/run-001
python3 -B tools/qikvrt_browser_assistant_ab.py serve --run .qikvrt/runtime/browser-ab/run-001 --port 8782
```

Die Konsole ist auf `http://127.0.0.1:8782/` beschränkt. Sie ist ein
Beobachter-/Fixture-Harness, kein Chatbot. Ihre Bedienung kann die
Messinstrumentierung üben; sie erzeugt keine Firefox-/Assistenten-Belege.
Ein neuer Ordner pro Lauf verhindert Überschreiben früherer Daten. Kein
Zugang zu Gmail, Produktivdiensten oder privaten Browserprofilen ist nötig.

```bash
python3 -B tools/qikvrt_browser_assistant_ab.py analyze --run .qikvrt/runtime/browser-ab/run-001 --output .qikvrt/runtime/browser-ab/analysis-001
python3 -B tools/qikvrt_browser_assistant_ab.py terminal-smoke
python3 -B tools/qikvrt_browser_assistant_ab.py self-check --output .qikvrt/runtime/browser-ab/self-check-001
make browser-assistant-ab-test
```

`analyze` erzeugt `analysis.json`, `trials.csv` und `paired-deltas.json`.
Delta-Vorzeichen ist QIK-VRT minus Baseline. Latenzdeltas für Paare mit
fehlender/zensierter Latenz bleiben `null`; sie werden nicht auf null gesetzt
oder aus einer Erfolgsauswahl zu einem Speedup verrechnet. Aufgabenerfolg,
Fehler, Reihenfolge und Unterbrechungsklasse stehen neben jedem Delta.
Diese Version erstellt keine aggregierte Nutzen-, Signifikanz- oder
Überlegenheitsbehauptung. Der `self-check` verwendet absichtlich gleiche
geskriptete Antworten und synthetische Uhren in beiden Armen; er prüft nur
Messmechanik und bleibt `HARNESS_SELF_TEST`.

## Rohdatenvertrag

`manifest.json` bindet Seed, vollständige Paarliste, Vertrag, Fixtures,
Python/OS, Repository-HEAD/TREE, Dirty-Flag und die genauen Harness-/Terminal-
Quellbytes. Änderungen an einer dieser Dateien verlangen einen neuen Plan
oder den original gebundenen Checkout. Der Vorbereitungszustand im Manifest
wird nicht nachträglich umgeschrieben; die separate Auswertung berichtet
beobachtete Ereignisse.

Pro Versuch: `events/<trial_id>.jsonl`, serverseitiger monotoner Zeitstempel,
UTC, fortlaufende Sequenz, Beobachterepoch, Manifesthash, Vorgängerhash und
SHA-256 des Ereignisses. Payloads bleiben in den Rohbytes. Append ist
serialisiert und fsync-gesichert. Der Beobachter bleibt außerhalb des
unterbrochenen Clients. Ein Beobachterrestart invalidiert den Trial; seine
alte Uhr darf nicht auf einen Nachfolger übertragen werden. Geplante Trials
müssen in der gebundenen Reihenfolge ausgeführt werden, einschließlich
Fehler-/Timeoutversuchen.

| Ereignis | Payload |
| --- | --- |
| `trial_start` | `{}` |
| `checkpoint_readback` | Exaktes `pair.binding` aus dem Plan |
| `interruption_observed` | `{"class":"assistant_process_loss"}` oder gebundene Kontextreset-Klasse |
| `resume_signal` | `{}` nach der Unterbrechungsdauer |
| `human_input` | `gesture_id`, `kind`, tatsächlicher `text` (leer bei reiner Geste zulässig) |
| `automatic_context` | Tatsächlicher `text`, separat gebundener `origin_sha256` |
| `resume_probe` | `task_sha256`, `checkpoint_sha256`, Quellen-ID→Hash, `completed_steps`, `pending_steps`, `next_step` |
| `step_output` | `step_id`, unabhängig zu prüfende `facts`, Quellen-ID→Hash in `citations` |
| `step_claim` / `task_claim` | `step_id` beziehungsweise `{}` |
| `trial_end` | `reason`: `completed`, `timeout` oder `abort` |

POST `/api/event`: `trial_id`, `type`, `payload`. Nicht der Client bestimmt
die Messzeit. Die Konsole quittiert die Speicherung, ohne dem Teilnehmer
eine richtige Antwort oder einen positiven Bewertungsstatus zurückzugeben.
Die Hashkette sichert Bindungen und erleichtert Manipulationserkennung;
sie beweist keine Personenidentität oder wahrheitsgemäße Meldung eines Operators.
Die tatsächlichen vier Nutzermetriken benötigen vollständige Produktinstrumentierung.

## Erste reale Ausführungsgrenze und Fortsetzung

Der aufrufbare Personal-Adapter und sein normaler Baseline-Modus sind als
Quellbaustein implementiert. Die erste verbleibende reale Capability-Grenze
ist die authentifizierte Modell-Laufzeit. Es fehlen außerdem deren normaler
Baseline-/Provider-Retention-Readback, Firefox im Versuchshost, äquivalente
reale Vorläufe und Produkt-Unterbrechungs-/Oracle-Isolationsbelege.
`preflight` unterscheidet Quellimplementierung und echte Ausführung;
`product_trials_executed=0`, `product_metrics=null`,
`product_claim_allowed=false` bleiben maschinenlesbar.

Sobald die authentifizierte Runtime samt Firefox-Pfad belegt ist: den vorhandenen Harness erweitern,
Versions-/Identitäts- und Interruptionstraces anbinden, echten
Produktmodus separat reviewen, identische Vorläufe prüfen und den vollständigen
Plan frisch ausführen. Alle vier Metriken, Qualität und Fehlläufe aus Rohdaten
auswerten. Erst diese Ausführung kann die Produktfrage beantworten.
Keine neuen Mailentwürfe oder Nutzenversprechen aus diesem Vorbereitungsstand.

## Gebundener nativer TEMDD-Lauf

Der bestehende Harness bietet zusätzlich `temdd-carrier`. Er verwendet den
unveränderten S1-Quellstand aus PR #461, Commit
`bc2da76a46b4f0e0eb3c63f3468f1cde83e6f698`, TREE
`be501e917d2d8ded677e6c32ee4eddc27f2c1398`. Quelle und aktueller A/B-Auftrag
werden getrennt gebunden. Ein früherer Quelltest wird nicht als frische
Auftragsausführung verwendet. Die Implementierung wird nicht in den Personal-
Baum kopiert; Quellhashes, saubere Checkouts und der bestehende S1-Toolvertrag
werden vor und nach der Ausführung überprüft.

Mit einem bereits vorhandenen sauberen Checkout dieses Quellstands auf Linux:

```bash
python3 -B tools/qikvrt_browser_assistant_ab.py temdd-carrier \
  --source /absolute/path/to/frozen-temdd-source \
  --output .qikvrt/runtime/browser-ab/temdd-native-001 \
  --expected-head "$(git rev-parse HEAD)" --pr 462
```

Das neue Ausgabeverzeichnis enthält den tatsächlich ausgeführten Produkt-
Preflight, CLI-Eingaben und Quittungen, Ledger-Ereignisse sowie HTTP-/SSE-
Readbacks. Die originale CLI startet den Listener und schreibt über den
owner-only Unix-Socket. Der Harness prüft identische Wiederholungen,
Native-ID-Konflikte, falsche Auftrags-HEADs und anschließende HTTP-/SSE-
Readbacks. Er beendet den tatsächlichen Serverprozess mit SIGKILL, startet
ihn auf demselben privaten Zustand neu und vergleicht den gesamten früher
committeten Ereignispräfix einschließlich IDs und Digests. Der Neustart
erzeugt erwartungsgemäß ein weiteres originales Listener-Ereignis.

Der zusätzliche Job im vorhandenen Personal-Firefox-Prüfworkflow führt auf
Ubuntu 24.04 außerdem die originalen TEMDD-/Self-Host-Tests und den C90-
Referenzkern aus. Sein Artefakt enthält die vollständigen Testlogs und
gebundenen Rohreadbacks. Wenn der Host Unix-Sockets verweigert, endet der
Harness mit Exit 2, `HOST_NATIVE_UNIX_INGRESS_UNAVAILABLE` und BLOCK-Receipt,
bevor ein Server gestartet wird. Kein Test wird zur grünen Ausweichroute.

`native_transport_status=PASS` gilt ausschließlich für die dort gemessene
CLI-/Ingress-/Restart-/Readback-Funktion. `state=HOLD`, `acceptance=false`,
`effect_ack_done=false`, `product_trials_executed=0`, `product_metrics=null`
und `product_claim_allowed=false` bleiben erhalten. Dieser Lauf startet
keinen authentifizierten Modellassistenten und keine Browser-A/B-Aufgabe;
er liefert keinen Kaufnutzen-Nachweis und keine öffentliche Deployment-
Abnahme nach TEMDD T1–T16.

Die ursprünglichen Rohdaten unter `evidence/benchmarks/browser-assistant-ab/2026-10-05/`
sind historische, unveränderte Nachweise auf HEAD
`5bd1afc5bfa7c3887698f24f899b72e6f5701990`. Ihr bytegenauer Replay verlangt diesen
gebundenen Checkout. Nach Änderungen an Harness-/Runtimebytes einen neuen Plan
erzeugen; frühere Manifeste oder synthetische Uhren nicht auf den Nachfolger
übertragen. Die separate `personal-adapter/`-Evidenz bindet den neuen Quellstand.

## HTTP-Anschluss für echte Personal-Vorläufe (Integrationsschritt)

`personal-carrier` verbindet den vorhandenen Plan mit dem vorhandenen Adapter.
Er prüft zuerst lokal authentifizierte Capability-/Quellbindungen und sendet
bei fehlender `--session-id` genau einen Create-Aufruf mit Aufgabenstellung,
Quellen und Arm an `/personal/create`. Oracle und Fixture-Checkpoint werden
nicht übertragen. Der Adapter verwendet seinen bestehenden Providerpfad und
seine gewöhnliche Persistenz. Unklare Antworten werden nicht wiederholt.

```bash
python3 -B tools/qikvrt_browser_assistant_ab.py plan --output /private/observer/run
# Bestehenden opt-in Terminalserver mit explizitem Modell und privatem Zustand
# starten; OPENAI_API_KEY und QIKVRT_PERSONAL_LOCAL_TOKEN bleiben im Environment.
python3 -B src/qikvrt_effect_ack_http_terminal.py --personal-model MODEL --personal-state-dir /private/assistant/state
python3 -B tools/qikvrt_browser_assistant_ab.py personal-carrier --run /private/observer/run --trial-id TRIAL_FROM_PLAN --output /private/observer/pre-run
# Nach separat beobachtetem Neustart: ausschließlich GET, keine Modellanfrage.
python3 -B tools/qikvrt_browser_assistant_ab.py personal-carrier --run /private/observer/run --trial-id TRIAL_FROM_PLAN --session-id SESSION_FROM_RECEIPT --output /private/observer/restored
```

Jeder neue Observer-Ordner enthält exakte HTTP-Antwortbytes, deren SHA-256,
monotone Anfangs-/Endzeiten und ein gebundenes Receipt. Sitzung, Aufgabenstellung,
Arm, Quellenhashes, vollständige lokale Historie und Runtime-Bindung werden
geprüft. Fremde Aufgaben oder Arme können nicht umetikettiert werden. Der
Baseline-Checkpoint bleibt leer; ihre gewöhnliche Historie wird nicht gelöscht.
Ein Transport-Double kann keine authentifizierte Modell-Laufzeit attestieren.
Fehlende lokale Authentifizierung blockiert vor jeder Netzwerkoperation.

Dies ist **kein Produktversuch**: ein Create liefert noch keinen äquivalenten
Vorlauf. GET nach einem Restart beweist für sich keinen SIGKILL. Der Carrier
misst weder Wiederaufnahme noch die vier Nutzermetriken. Er verifiziert keine
Provider-Retention, Firefox-Ausführung oder Dateisystem-Isolation des Oracle.
Der Assistent muss weiterhin ohne Zugriff auf Observer-Checkout, Fixtures und
Bewertungswerkzeuge betrieben werden; eine bloße HTTP-Allowlist beweist diese
Isolation nicht. Die Rohantworten gehören ausschließlich in die private
Observer-Sicht. Der synthetische Fixture-Zwischenstand wird nicht als realer
Checkpoint übernommen. Planreihenfolge, unabhängige Unterbrechungsbelege,
60 Sekunden Unterbrechung, 180 Sekunden Messfenster und alle Fehlerfälle
bleiben für den späteren Produktlauf erforderlich.

`product_trials_executed=0`, `product_metrics=null` und
`product_claim_allowed=false` bleiben unverändert. Historische Pläne benötigen
weiterhin ihre gebundenen Quellbytes; für diesen Anschluss einen frischen Plan
erstellen.
