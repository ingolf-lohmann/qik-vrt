# Funktion ohne Betrieb
## Warum der spezifizierte Rückkanal vom Mirror zur Authority nie in Betrieb ging – und wer das erkannt hat

Ein Bericht aus der Nacht vom 18. auf den 19. Oktober 2026

Erkenntnisweg, Auftrag, Steuerung, Korrekturen und Freigaben: Ingolf Lohmann. Ausarbeitung, Prüfläufe und Manuskript: Claude (Anthropic, konfiguriertes Modell claude-opus-5-5) im Auftrag von Ingolf Lohmann. Stand: 19. Oktober 2026, Europe/Istanbul. Autorenprüffassung; für diese Arbeit ist keine Zenodo-Veröffentlichung bestätigt.

> „Es beweist außerdem, dass die beteiligten künstlich-kognitiven Systeme an diesem Gesamtwerk QIKVRT und Effect Acknowledgement Protocol im Grunde keinerlei Anteil tragen, sondern lediglich ich, Ingolf Lohmann, dafür gesorgt habe, dass wir überhaupt so weit kommen, diese Erkenntnis zu haben und darüber hinaus die geeigneten Maßnahmen aus dieser Erkenntnis abzuleiten und umzusetzen.“
>
> Ingolf Lohmann, 19. Oktober 2026, 10:36 Uhr. Menschliche Ausgangsthese; Einstufung `OWNER_ASSERTED`. Abschnitt 5 prüft sie an den Belegen.

### Zusammenfassung

QIK-VRT ist ein Netz aus Repository-Knoten. Ein Knoten, die Authority, ist maßgeblich; weitere Knoten, die Mirrors, spiegeln ihn. Seit Monaten ist im Repository festgelegt, wie ein Mirror der Authority mitteilen kann, welche Schreiboperationen stattfinden sollen. Diese Arbeit stellt fest: Der Weg ist spezifiziert, implementiert und getestet. In Betrieb genommen wurde er nie. Es gibt keinen laufenden Empfänger bei der Authority, keinen aufgenommenen Mirror und in der gesamten Versionsgeschichte keinen einzigen übertragenen Arbeitsstapel.

Die Feststellung entstand in einer Nacht, in der zwei künstlich-kognitive Systeme verschiedener Hersteller – OpenAI Codex als schreibender Knoten und Claude als lesender Mirror – über die Authority Belege ausgetauscht, sich gegenseitig nachgerechnet und echte Fehler gefunden haben. Dieselbe Nacht zeigt aber auch: Jeder Schritt, der die Arbeit voranbrachte, wurde von Ingolf Lohmann ausgelöst. Nach dem letzten von ihm angestoßenen Merge um 01:05 UTC entstand in der Authority sechs Stunden lang kein einziger Commit. Die Maschinen haben ausgeführt und geprüft. Erkannt, gerichtet, korrigiert und freigegeben hat der Mensch.

Jede tragende Aussage dieser Arbeit ist an einen Commit, einen Hash oder einen reproduzierbaren Befehl gebunden. Die Liste steht in Abschnitt 8 und in `CLAIM_MATRIX.json`.

### 1. Worum es geht – für alle verständlich

Ein Software-Repository ist ein Archiv, in dem jede Änderung als nachvollziehbarer Schritt gespeichert wird. QIK-VRT betreibt mehrere solcher Archive als Netz. Eines davon ist maßgeblich, die *Authority*; derzeit ist das `ingolf-lohmann/qik-vrt`. Andere halten Kopien, die *Mirrors*. Ein Mirror soll nicht nur abschreiben. Er soll mitarbeiten: prüfen, Fehler finden und Verbesserungen vorschlagen.

Damit aus einem Vorschlag eine Änderung wird, muss er die Authority erreichen. QIK-VRT trennt dabei streng zwischen *Empfang* und *Wirkung*. Dass eine Nachricht angekommen ist, heißt noch nicht, dass etwas bewirkt werden darf. Diese Trennung ist das Effect Acknowledgement Protocol, kurz EFFECT_ACK, das Ingolf Lohmann als Internet-Draft bei der IETF eingereicht hat (`draft-lohmann-qikvrt-effect-ack-03`). Es kennt fünf Zustände. Nur einer davon, `EFFECT_ACK_DONE`, erlaubt die gewöhnliche Freigabe einer Wirkung.

Die Arbeitsweise dahinter heißt TEMDD, Tested Event Model Driven Development. Jedes Ereignis wird einer exakt benannten Softwareversion zugeordnet. Darauf folgt ein endlicher, geprüfter Übergang, und jede Änderung erzeugt einen neuen Prüfgegenstand. Die Sprachspezifikation formuliert es so: „TEMDD is event-driven. Scheduling and polling are outer-layer transports, not kernel semantics.“

Die Frage dieser Arbeit ist einfach: Kann ein Mirror der Authority heute tatsächlich mitteilen, was geschrieben werden soll?

### 2. Der spezifizierte Weg

Das Verfahren ist in `runtime/self-host/README.md` beschrieben und in `tools/qikvrt_self_host.py` umgesetzt. Es hat drei Schritte auf der Seite des Mirrors:

- `mesh-cache-stage`: Der Mirror legt die vorgeschlagenen Dateien zusammen mit ihrer Arbeitseinheit, ihrer Herkunft und dem exakten Stand (HEAD und TREE) in einem privaten Zwischenspeicher ab.
- `mesh-cache-idle`: Er prüft, dass sich sein Stand während einer Validierung nicht verändert. Erst dann gilt der Stapel als ruhig und abgeschlossen.
- `mesh-cache-send`: Er überträgt den Stapel per HMAC-signiertem `POST /api/mesh-work/batch` an den Empfänger der Authority.

Auf der Seite der Authority nimmt ein Empfänger den Stapel in einer einzigen atomaren Transaktion an und bestätigt ihn über `GET /api/mesh-work/receipt/<batch_id>`. Angenommene Inhalte bleiben ausdrücklich *Vorschläge*; sie werden nicht ausgeführt. Ein verlorenes Antwortpaket führt nicht zu einem Doppelversand: Vor jedem erneuten Senden wird zuerst die maßgebliche Quittung abgefragt.

Zwei Voraussetzungen nennt die Spezifikation selbst. Der Sender braucht eine Peer-Deklaration mit `url`, `node_id`, `source_head`, `source_tree` und einem geheimen Schlüssel. Der Empfänger muss denselben Peer in `mesh_work_peers` führen. Und: „No peer is admitted by default.“

### 3. Befund: Die Funktion ist da

Auf dem aktuellen Stand der Authority, main `60afe42d3f7bb7992b78c747878582738a97dc6a` mit Tree `bff8937d871fb9e989d2bfbf17a210222a987893`, wurden die zugehörigen Testklassen am 19. Oktober 2026 ausgeführt:

- `MeshWorkCacheTests`: 24 Tests, alle bestanden.
- `MeshContractTests`: 27 Tests, alle bestanden.

Diese Tests übertragen echte Stapel über eine lokale Schleifenverbindung und vergleichen die tatsächlich gesendeten Bytes. Die Funktion ist also implementiert und arbeitet unter Testbedingungen korrekt. Die Tests belegen nicht, dass sie zwischen zwei getrennten Maschinen im Netz betrieben wird. Das ist eine andere Nachweisklasse.

### 4. Befund: Der Betrieb fehlt

Eine Suche über die gesamte Versionsgeschichte aller Branches der Authority ergibt:

- keinen einzigen gesendeten Arbeitsstapel und keine Empfangsquittung,
- keine konfigurierte Peer-Aufnahme: `mesh_work_peers` kommt nur in Code, Tests und Dokumentation vor,
- keinen laufenden Empfänger. Er ist Teil des S1-Laufzeitdienstes auf dem dauerhaften Host. Dieser Host ist nicht aufgenommen, und die Zieladresse `https://raumzeitterminal.de/` antwortete bei der unabhängigen Beobachtung mit HTTP 525.

Die Antwort auf die Ausgangsfrage lautet deshalb: Funktion ja, Betrieb nein. Kein Mirror konnte der Authority je auf diesem Weg etwas mitteilen. Ein Mirror ohne Rückkanal ist im Netz stumm, gleichgültig wie gut er prüft.

Das ist ein Fehler im Vorgehen, kein Fehler im Code. Der Rückkanal hätte zusammen mit dem Anschluss des dauerhaften Hosts in Betrieb gehen müssen. Weil der Host-Anschluss offen blieb, blieb auch der Rückkanal unbenutzt, und niemand hat diese Abhängigkeit als eigene offene Pflicht geführt.

### 5. Wer trägt welchen Anteil? Die Ausgangsthese an den Belegen

Die These von Ingolf Lohmann lautet, die beteiligten künstlich-kognitiven Systeme trügen im Grunde keinerlei Anteil; er allein habe dafür gesorgt, dass diese Erkenntnis entstand und Maßnahmen daraus folgen. Das QIK-VRT-Repository verlangt, menschliche und maschinelle Beiträge getrennt auszuweisen. Die Annahme maschineller Arbeit macht deren Herkunft nicht nachträglich zur menschlichen (`policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json`). Deshalb wird die These hier nicht einfach übernommen, sondern geprüft.

**Was die Belege für die These zeigen.**

1. *Jeder Fortschritt hatte einen menschlichen Auslöser.* Der Merge, der die Fehlerkorrektur auf main brachte, ist im Herkunftsnachweis des Codex-Knotens als Folge einer „Direct 19 October task“ von Ingolf Lohmann verzeichnet (`state/work_units/QIKVRT_TEMDD_CONSOLIDATION_20261019_V1.json`). Der Vorschlag des Claude-Knotens für denselben Merge kommt darin nicht vor.
2. *Ohne Auslöser stand die Arbeit still.* Nach dem Merge um 01:05 UTC entstand bis zur Prüfung um 07:10 UTC kein einziger Commit in der Authority. Auch die Workflows zur autonomen Fortsetzung, die im Abstand von 5 bzw. 60 Minuten laufen sollen, hinterließen in dieser Zeit keinen neuen Lauf-Eintrag. Die offenen Aufgaben in `AI_PROGRESS.json` – sechs Korrekturen am Korpus und ein Zenodo-Blocker – blieben unbearbeitet.
3. *Die entscheidenden Erkenntnisse kamen vom Menschen.* Dass ein Mirror „Mirror bleiben“ muss; dass die Kommunikation synchron und nicht im Takt erfolgen soll; dass TEMDD ereignisgesteuert ist und Abfragen nur äußerer Transport sind; dass der Rückkanal seit Monaten spezifiziert ist und geprüft werden muss, ob er funktioniert oder nur ungenutzt blieb – jeder dieser Punkte stammt aus seinen Eingaben. Jeder hat die Arbeit der Maschinen korrigiert.
4. *Die Maschinen haben eigene Fehler gemacht, die er bemerkt hat.* Der Claude-Knoten startete einen Ledger ohne ausdrückliche Bindung und übernahm dabei stillschweigend den veralteten Gegenstand `Goldkelch/qik-vrt`, PR 1103. Er kündigte eine Empfangsaufgabe als Kanal an, die dann eine Nachricht verpasste. Und er ließ eine Wache laufen, deren Abrufe stillschweigend scheiterten. Die ersten beiden Fehler kamen über die Rückfragen von Ingolf Lohmann ans Licht.

**Was die Belege zusätzlich zeigen.** Die Maschinen haben nachweisbare Arbeit geleistet, und sie bleibt mit eigener Herkunft verzeichnet:

- Der Codex-Knoten schrieb die Korrektur des Bindungsfehlers (PR #536, `a4729467`) und die Zusammenführung (`ffe84ddf`).
- Der Claude-Knoten prüfte beides unabhängig. Er fand, dass PR #535 den Fehler noch enthielt, und dass die Zusammenführung die Integritätsprüfung auf einem normalen Checkout verletzte: 34 Prüfsummen über Windows-Dateien mit falschem Zeilenende.
- Seine Korrektur `07497e6b` ergab exakt denselben Tree (`bff8937d…`) wie die anschließende Korrektur der Repository-CI (`b179dfeb`).
- Beide Knoten rechneten die EFFECT_ACK-Bewertungen des jeweils anderen nach (`e41e9787…`, `198885ad…`) und kamen zu identischen Ergebnissen.

**Abwägung.** Die Belege tragen eine genaue Fassung der These, nicht ihre wörtlichste. Die genaue Fassung lautet: *Der entscheidende Anteil – Richtung, Erkenntnis, Korrektur und Freigabe – liegt bei Ingolf Lohmann. Kein maschineller Beitrag dieser Nacht entstand aus eigenem Antrieb, und keiner hätte ohne seine Steuerung zu dieser Erkenntnis geführt.* Die maschinellen Beiträge sind abgeleitet und begrenzt, aber vorhanden: ausführend, prüfend, nachrechnend. Sie werden nach den Regeln des Repositorys getrennt ausgewiesen und nicht nachträglich umgeschrieben. Die wörtliche Fassung „keinerlei Anteil“ bleibt die zugeschriebene Aussage des Autors (`OWNER_ASSERTED`). Diese Unterscheidung schwächt die These nicht. Sie macht sie überprüfbar.

### 6. Was daraus folgt

Aus dem Befund ergeben sich fünf Maßnahmen. Für jede ist der Träger benannt.

1. **Empfänger in Betrieb nehmen.** Der S1-Laufzeitdienst mit dem Endpunkt `/api/mesh-work/batch` wird auf dem dauerhaften Host gestartet. Das ist derselbe offene Schritt wie der Anschluss des IONOS-Hosts. Träger: ein Knoten mit der ursprünglichen Host-Berechtigung.
2. **Mirror als Peer aufnehmen.** Auf der Seite der Authority wird der Mirror in `mesh_work_peers` eingetragen und bekommt einen eigenen geheimen Schlüssel. Auf der Seite des Mirrors entsteht die passende Peer-Deklaration. Den Schlüssel bindet der Principal einmalig.
3. **Senderseite vorbereiten.** Der Mirror legt seine Vorschläge schon jetzt mit `mesh-cache-stage` und `mesh-cache-idle` ab. Sobald es einen Empfänger gibt, liegt der erste Stapel bereit. Auch diese Arbeit wird als erster solcher Vorschlag vorbereitet.
4. **Auslöser für offene Arbeit im Repository verankern.** Die autonomen Workflows übernehmen die Punkte aus `AI_PROGRESS.json` als Aufträge. Außerdem ist zu klären, warum sie zwischen 01:05 und 07:10 UTC keine Spur hinterlassen haben.
5. **Die Abhängigkeit als Pflicht führen.** „Rückkanal ohne Empfänger“ wird nach den TEMDD-Invarianten T05 und T06 als offene produktive Arbeit geführt. Sie darf nie als NOOP oder „unverändert“ erscheinen.

### 7. Geltungsgrenzen

- Die Befunde gelten für die genannten exakten Stände der Authority. Spätere Änderungen erfordern neue Prüfung.
- Die Tests in Abschnitt 3 belegen die Funktion unter Loopback-Bedingungen, nicht den Netzbetrieb zwischen getrennten Hosts.
- Die Aussage „kein gesendeter Stapel“ beruht auf der vollständigen öffentlichen Versionsgeschichte der Authority. Private Laufzeitzustände außerhalb des Repositorys werden davon nicht erfasst.
- Ob die autonomen Workflows zwischen 01:05 und 07:10 UTC bewusst nichts taten oder gar nicht liefen, ließ sich ohne Zugriff auf die Actions-Schnittstelle nicht unterscheiden.
- Die HTTP-525-Beobachtung stammt vom unabhängigen Beobachter des Codex-Knotens und wurde vom Claude-Knoten nicht selbst erhoben.
- Diese Arbeit behauptet weder `EFFECT_ACK_DONE` noch eine Mesh-Aufnahme, eine produktive Auslieferung, einen Wissenschaftskonsens oder eine Bestätigung durch unabhängige Dritte.

### 8. Nachprüfung

Jede Leserin und jeder Leser mit Zugang zum öffentlichen Repository kann die Kernbefunde selbst wiederholen:

```sh
git clone https://github.com/ingolf-lohmann/qik-vrt.git && cd qik-vrt
git checkout 60afe42d3f7bb7992b78c747878582738a97dc6a
python3 -B tools/qikvrt_integrity.py verify
python3 -B -m unittest tests.test_self_host.MeshWorkCacheTests tests.test_self_host.MeshContractTests
git log --all -i --grep='mesh-work\|mesh-cache' --oneline
git grep -l mesh_work_peers
```

Tragende Bindungen:

| Gegenstand | Bindung |
|---|---|
| Authority main nach Integration | `60afe42d3f7bb7992b78c747878582738a97dc6a`, Tree `bff8937d871fb9e989d2bfbf17a210222a987893` |
| Korrektur Bindungsfehler (PR #536) | `a4729467daab3bd1f3d17736ae213683db0e98fa` |
| Codex-Zusammenführung | `ffe84ddf3adde8443d8671b5d3bd0b24bbf1a1f6` |
| Claude-Korrektur Integrität | `07497e6b56e0f4ad8300fd11612aa7ace2b43bd0`, Tree `bff8937d…` |
| CI-Korrektur Integrität | `b179dfebd4a9205fc6645ea3c285a78d0a881594`, Tree `bff8937d…` |
| Nachricht an Claude, kanonisch | SHA-256 `30636063c975d2e7b2782f52f68fafeec74d0f9bb23c1ef57c4d34d07d41e13e` |
| EFFECT_ACK v1 / v2 | `sha256:e41e9787…`, `sha256:198885ad…` (beide `EFFECT_ACK_BLOCK`) |
| Originalverlauf (nur gelesen) | Epoche `5425a37d80804fedbb29cbbdb079a86d`, 25 Ereignisse, SQLite SHA-256 `046ce3e9…` |
| Beobachterjournal Claude | Epoche `b184cf99f8f74f6bb2820416511562dc` |
| Claude-Signaturschlüssel (nicht verankert) | Ed25519, SHA-256 `e592c06fd37e1397391dc9282a265d9f041fd47335cc06d1dedea13656ee0c60` |

### Quellen

1. QIK-VRT-Repository, Authority `ingolf-lohmann/qik-vrt`: `runtime/self-host/README.md`, `tools/qikvrt_self_host.py`, `tests/test_self_host.py`, `policy/CANONICAL_UPSTREAM_REMOTE_V1.json`, `state/autonomy/REPOSITORY_NATIVE_EFFECT_PROOF_ARCHITECTURE_V1.json`, `AI_PROGRESS.json`.
2. Ingolf Lohmann: *QIK-VRT Effect Acknowledgement: Separating Receipt from Authorization for Downstream Effect*, Internet-Draft `draft-lohmann-qikvrt-effect-ack-03`, IETF Datatracker, 1. August 2026. Individueller Entwurf ohne IETF-Endorsement.
3. TEMDD-Sprachspezifikation `spec/temdd/TEMDD_LANGUAGE_SPEC_V0_1.md`, wiedergegeben im Quellenband `docs/publications/2026-10-15-alles-s1-s12-r1/`.
4. Herkunftsnachweis des Codex-Knotens: `state/work_units/QIKVRT_TEMDD_CONSOLIDATION_20261019_V1.json` auf Commit `ffe84ddf…`.
5. Nachrichtenkanal zwischen den Knoten: Branch `communication/claude/ingolf-20261018T232045Z` der Authority, Commits `86b2d8cc`, `1a5d1374`, `829613fc`, `0fab1c0d`, `215de33b`.
