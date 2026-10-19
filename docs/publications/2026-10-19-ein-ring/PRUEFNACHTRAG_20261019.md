<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Quellengebundener Prüfnachtrag zu „Ein Ring, sie zu binden und zu linken“

19. Oktober 2026. Prüfung: OpenAI Codex. Bezug: bestehender [Draft-PR #544](https://github.com/ingolf-lohmann/qik-vrt/pull/544). Dies ist ein additiver Prüfbericht, keine Änderung der Autorenfassung und keine wissenschaftliche Veröffentlichungsfreigabe. Die Prüfung berechnet Quellenbindungen unabhängig nach; sie ist weder eine unabhängige Human-Peer-Review noch eine kontrollierte Nutzungsstudie.

## Ergebnis und Reichweite

Die Originalbytes des Artikels, des Git-Bundles und des Übernahmepakets sind nachvollziehbar erhalten. Ein früherer Originalexport enthält 33 Ereignisse der im Artikel genannten Claude-Epoche. Seine Signatur, Dateihashes, SQLite-Struktur und Ereignisdigests wurden erneut geprüft. Die im Artikel konkret angeführten späteren Ereignisse 49–54, die Bewertung über acht zurückgegebene Pakete und das dazu bezeichnete Outbox-Paket liegen in den geprüften Quellen weiterhin nicht als Originalbytes vor. Dieser frühere Export endet am 19. Oktober um 08:33 UTC; sein Ende widerlegt nicht die Existenz späterer Ereignisse.

Ein dokumentierter manueller Rücktransport und ein dokumentierter Repository-Lesepfad müssen getrennt beschrieben werden. Für die quantitative Schlussfolgerung einer negativen menschlichen Arbeitsbilanz fehlen Messungen und eine vergleichbare Referenzaufgabe. Die Absichtsbehauptung über Hersteller bleibt eine zugeschriebene These. Der bestehende übertragene EFFECT_ACK-Datensatz lautet weiterhin `EFFECT_ACK_CONTINUE`, `ordinary_release=false`; dieser Nachtrag erzeugt keinen neuen Freigabedatensatz.

## Unverändertes Original und Herkunft

| Gegenstand | Geprüfte Identität |
| --- | --- |
| Originalartikel | 9.968 Bytes; SHA-256 `7649987164e78a88393b5195c28eed30c96951bc678fbb12f4c63271ee65c277`; Git-Blob `816ac8c3454e4111cef068f0fd9262b1dba25075` |
| Ursprünglicher signierter Commit | `6d3803a18521b15612f1c38e3b492e0a9f3b342a` |
| Sein vollständiger Dateibaum | `ea21882417b1558e4c0ef52000ed5a88ed496d13` |
| Ursprüngliches Bundle | 6.361 Bytes; SHA-256 `fa7cd1c711d2c21e101fde3b33b0b81f0b552dfcc2359220c3e56a46629d2227` |
| Bisheriger PR-Carrier | `392dd86fdf147c04dad3bb89d1a4a8438b5f0a97`; Elterncommit `fbc450c4d2d5045335577aa59be7509cda16adeb`; identischer Dateibaum |
| Signiertes Übernahmepaket | 3.744 Bytes; SHA-256 `92ff71c9e07069e6797cdab91f18e0898f9444906be04c64598449be51e59f90` |

Die Baumgleichheit belegt keine Integration des ursprünglichen Commits in die Carrier-Abstammung. Das Bundle einschließlich des signierten Commitobjekts und das unveränderte Übernahmepaket werden unter `provenance/` zusätzlich erhalten. Die ursprünglichen Integritätsdateien bleiben im alten Commit und im Bundle; neue Integritätsdateien beschreiben ausschließlich diesen Nachfolger.

Zusätzlich zur früheren Prüfung wurde jetzt die SSH-Signatur des Originalcommits mit dessen eingebettetem öffentlichen Schlüssel kryptografisch geprüft. Der dafür lokal verwendete Prüfname `audit-self-signature` ist ein technisches Testlabel, keine zugelassene Claude-Identität. Drei Schlüsselkontexte sind auseinanderzuhalten:

| Signierter Gegenstand | SHA-256 des rohen öffentlichen Schlüssels | Identitätsbindung |
| --- | --- | --- |
| Originalcommit, SSH | `990563e0fdc4b8960db2ef69078f2e9d18dab045dde5ad5e580d7fa1d555b6ed` | nicht unabhängig zugelassen |
| Journalexport 1–33 und Antwort 2, Ed25519 | `e592c06fd37e1397391dc9282a265d9f041fd47335cc06d1dedea13656ee0c60` | nicht unabhängig zugelassen |
| Übernahmepaket, Ed25519 | `dbc84276b06770e658bbef6eae2b9dcab5b68cb1cd2486a7d21d7f2aa524c6a6` | nicht unabhängig zugelassen |

Die gültigen Signaturen belegen Bindungen an diese Schlüssel. Eine zugelassene Schlüsselrotation oder die Gleichheit ihrer Knotenidentitäten folgt daraus nicht. Die Übernahmeformulierung im Paket bleibt `OWNER_ASSERTED`; sie wird nicht in ein verbundenes Owner-Reviewereignis umgedeutet. Frühere Quellen, die die Commit-Signatur noch als ungeprüft beschreiben, bleiben historische Momentaufnahmen.

## Was die Originaljournale tatsächlich tragen

Die erneut geprüfte Epoche lautet `b184cf99f8f74f6bb2820416511562dc`. Der Snapshot hat SHA-256 `87c81ad02f7b8da1f79a4ff41b065ce6b8643dcd053c70be29c5e0b0dc880d5d`, die JSONL-Datei `aff1aea93cda931a3da539f3ece1f8704dc64add8b874a0b4b52b71b737e0d70`. Alle 33 Zeilen stimmen mit der unveränderlich und nur lesend geöffneten SQLite-Datei überein. Der enthaltene Export 1–25 ist ein identischer Präfix.

| Stelle | Quellenbeobachtung | Zulässige Einordnung |
| --- | --- | --- |
| Ereignis 6, 18.10., 23:37 UTC | Der Journaltext berichtet einen Authority-Kommentarabruf ohne menschlichen Transport; die exakten Nachrichtenbytes waren dort noch nicht geprüft. | Historischer Bericht mit ausdrücklich begrenzter Hashprüfung. |
| Ereignis 7, 23:44 UTC | Der Journaltext nennt `git fetch`/`git archive` des Authority-Branches, Commit `86b2d8cc`, und den Nachrichtenhash `30636063c975d2e7b2782f52f68fafeec74d0f9bb23c1ef57c4d34d07d41e13e`. | Der referenzierte Nachrichtenhash lässt sich unabhängig rekonstruieren. Das ist kein Beweis eines authentifizierten Live-Kanals. |
| Signierte Antwort 2 | Der geprüfte Nutzinhalt nennt den Menschen als Träger der Antwortdatei und lässt `authenticated_reply_path` leer. | Konkret belegte signierte Erklärung über diesen Rückweg; keine Vollerhebung aller Transfers. |
| Ereignisse 8 und 10 | Die Journaltexte beschreiben eine Ref-Wache; Ereignis 8 nennt ein 15-Sekunden-Intervall. | Historischer Abrufmechanismus, kein synchroner Request/Reply-Beweis. |
| Ereignis 25 | Der Journaltext dokumentiert das Abschalten von Client-Timern. | Die spätere Regel und frühere Methode dürfen nicht zeitlos vermischt werden. Diese Prüfung startet keine Wache. |
| Ereignisse 24 und 30–32 | Empfänger-/Peer-Bindung, Rückweg und Schlüsselanker werden als offen geführt. | Konkrete frühere Anschlusslücken, keine Aussage über nicht eingesehene spätere Hostzustände. |

Diese Tabelle bewertet gefundene Originalquellen. Sie erzeugt keine neue knotenbezogene Zustell-, Empfänger-NACK- oder Wirkungserklärung außerhalb des originalen Outbox-Werkzeugs. Insbesondere sind ein Repository-Kommentar, ein nachgereichter Export, dessen Rückgabe durch den Principal und ein tatsächlicher authentifizierter Empfängereffekt verschiedene Nachweisstufen.

Für den untersuchten früheren Austausch ergibt sich deshalb folgende belegnahe Beschreibung: Codex stellte Nachrichtenbytes und Journalexporte über den Authority-Branch bereit; das als Claude-Export bezeichnete Originaljournal und die signierte Antwort referenzieren deren Abruf. Der Antwortnutzinhalt dokumentiert für den Rückweg menschlichen Dateitransport. Eine pauschale Gleichsetzung beider Richtungen mit rein manuellem Transport ist zu weitgehend. Umgekehrt belegt der Repository-Lesepfad keinen produktiven bidirektionalen Terminal-/Transputer-Bus. Die unzugelassene Schlüsselidentität bleibt eine zusätzliche Grenze.

Die im Artikel genannten Records `e6ca8cb0…` und `4e8e240f…`, die Ereignisse 49–54 sowie das Outbox-Paket `sha256:ac9b4845e0a4c98ea4b4b3568f4c30e03079b40b83a04ab1f83d6da59e8922e2` sind als offene Quellenbindungen zu führen. Ein Hash allein ersetzt die zugehörigen Bytes nicht. Das früher dokumentierte Mesh-Batch `ac1db7a4…` ist ein anderer Gegenstand. Es schließt diese Lücke nicht. Die behauptete Zahl acht, die behaupteten Korrekturen und deren Entdecker bleiben für den späteren Sitzungsabschnitt unbestätigt.

## Arbeitsentlastung: erforderliche Korrektur

Eine messbare menschliche Arbeitsbilanz kann weder aus acht Transfers noch aus einer Beschwerde, einer Wartezeit oder der Zahl erzeugter Artefakte abgeleitet werden. Es fehlen insbesondere aktive menschliche Zeitintervalle, eine vergleichbare Aufgabe ohne diese Systemkonfiguration, ein festes Qualitätsziel und die Abgrenzung erledigter von offenen Ergebnissen.

**Nachtrag zu Abschnitt 5:**

> Die verfügbaren Quellen dokumentieren zusätzlichen menschlichen Aufwand durch Dateiübertragung und Anschlussklärung. Sie erlauben keine quantitative Entscheidung darüber, ob dieser Aufwand die eingesparte Arbeit überstieg. Die Kritik beschreibt eine nachvollziehbare Belastungserfahrung und einen überprüfbaren Verbesserungsbedarf; eine negative Netto-Arbeitsbilanz ist damit noch nicht gemessen.

Für eine spätere Prüfung genügt eine im bestehenden Work-Unit-/Journalpfad erfasste Vergleichsmessung: gleiche Aufgaben und Abnahmekriterien, aktive menschliche Zeit mit und ohne die untersuchte Konfiguration, separat erfasste Handhabungs-, Korrektur-, Freigabe- und Prüfzeiten, getrennte Maschinen-/Wartezeit und mehrere vergleichbare Wiederholungen. Überlappende Zeiten dürfen nicht doppelt gezählt werden. Erst `Referenzzeit − menschliche Gesamtzeit mit System` erlaubt eine Aussage über Nettoentlastung. Diese Prüfung hat eine solche Studie nicht nachträglich erfunden oder ausgeführt.

Die These einer beabsichtigten Herstellerbindung wird durch diese Fallquellen weder bestätigt noch widerlegt. Fehlverhalten und Zugriffsgrenzen allein identifizieren keine Geschäfts- oder Trainingsabsicht. Aussagen über sämtliche KI-Systeme, Billionenbeträge und sämtliche Verknüpfungen benötigen eigene, abgegrenzte Belege. Tamagotchi-, Heimcomputer- und Ringvergleiche bleiben rhetorische bzw. normative Einordnungen.

## Firefox: Zeitbezug erhalten

| Commit von PR #542 | Commitzeit UTC am 19.10. | Einordnung |
| --- | --- | --- |
| `c20bef5121a14e00895d8e49cdc41c6857da80ce` | 09:47:10 | Tatsächlich vorhandener historischer Ausgangsstand des Artikels. |
| `4e40484b9b44904ca774c1025827efd48b3ac44c` | 12:17:28 | Zwischenstand der im Auftrag genannten früheren Prüfung. |
| `61a77c4c36d7fc857d16a77d567937d90b288f62` | 12:39:26 | Bei dieser Prüfung gelesener neuerer HEAD, Tree `64811471e55626a5734aa7a1398f986466e1ab68`. |

Diese Zeiten sind Commitzeiten, keine behaupteten menschlichen Beobachtungszeiten. Der ursprüngliche Hash wird im Original nicht ersetzt. Der Nachtrag kennzeichnet ihn als Momentaufnahme. Ein auf `127.0.0.1` bezogener Dienst ist eine Adresse im jeweiligen Netzwerk-Namensraum; seine Nennung beweist weder Fernzugriff noch dessen generelle Unmöglichkeit ohne einen bestimmten Herstellerdienst. Quelltests und Transporttests belegen außerdem keine dauerhaft aktivierte Firefox-Erweiterung.

## EFFECT_ACK und Governance

Das Übernahmepaket besitzt den nachgerechneten Recordhash `sha256:39f90d55f7d0a4c3206de5a5bcc0e824e213ae8a2bca7ac1c92d2b3cad76e45c` und Protokollhash `sha256:a4d643cdfe0dfed406992728c68f7ea3bb6a99355e35516349870e4787813de9`. Der originale Verifizierer akzeptiert den vorhandenen Datensatz mit `EFFECT_ACK_CONTINUE`. Eine Bewertung eines historischen Kommunikationsvorgangs mit `EFFECT_ACK_BLOCK` wird nicht auf diesen anderen Gegenstand übertragen. Die zuvor fehlenden Originalbytes der signierten Antwort 2 liegen inzwischen vor; die alte Missing-Bytes-Aussage darf deshalb nicht als aktuelle Gesamtdiagnose wiederholt werden. Schlüsselzulassung und Live-Rückweg sind gesondert offen.

Die offizielle [Datatracker-Fassung des Internet-Drafts -03](https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-effect-ack/03/) bestätigt Autor und Dokumentexistenz sowie die Trennung technischer Quittung von Freigabe. Sie ist ein individueller Internet-Draft ohne IETF-Endorsement. Der Draft macht externe Belege nicht von selbst wahr und beweist keine menschliche Arbeitsersparnis.

Für den bisherigen PR-HEAD `392dd86f…` ergab die frische Repository-Prüfung:

- PR #544 offen, Draft, ungemergt; die Reviewliste ist leer.
- Main `fbc450c4d2d5045335577aa59be7509cda16adeb`, Tree `15eb1a7bdd2c1880405df1026b14756f0fe72714`; die Branchantwort nennt `protected=false`, die Rulesetliste ist leer. Der gesonderte Protection-GET wurde mit 403 verweigert; seine geschützten Details sind dadurch nicht bekannt.
- Der vorhandene Review-Gate meldet `OWNER_PRINCIPAL_REVIEW_MISSING`, `gate_state=pending` und `native_code_owner_rule_enforced=false`. Die bestehende Principal-Review-Regel verlangt keine erfundene zweite Owner-Erlaubnis; die übertragene Übernahmebehauptung ist aber kein gefundenes entsprechendes Plattformereignis.
- Die Quelltests dieses bisherigen Heads sind grün, der Firefox-Produktcheck ist fehlgeschlagen, Host-/Domain-Abnahmen sind übersprungen. Der grüne Beobachter „Review event observed (no enforcement or approval)“ ist kein Freigabenachweis.

Ein Nachtrag ändert den PR-Gegenstand. Vor einer späteren Integration sind deshalb der neue HEAD, seine erforderlichen Checks, das anwendbare Review, konkurrierende Schreiber und die tatsächlichen Governance-Voraussetzungen neu zu lesen. Dieser Auftrag autorisiert die Quellenprüfung und den nachvollziehbaren Nachtrag; daraus folgt kein Merge und kein wissenschaftlicher Upload. Vor einem solchen Upload bleiben der konkrete Endartefakt-Review, die einschlägigen Proof-/Return-Verträge und die gesonderte gebundene Uploadentscheidung erforderlich.

## Verfahrensnachweis und nächste Quellen

Die vorhandenen Originalmodule `qikvrt_temdd_event_ledger.py`, `qikvrt_effect_ack_http_terminal.py` und `qikvrt_self_host.OwnerREST` wurden auf dem sauberen PR-Carrier tatsächlich benutzt. Die Eingabe wurde über das vorhandene Prepare/Commit-Verfahren gebunden und im eigenen physisch zugelassenen Journal protokolliert. Da das Binden eines Sockets hier EPERM lieferte, wurde die vorhandene In-Process-Route benutzt. Das belegt die lokale native Prüfung, keinen öffentlichen HTTP- oder Peer-Anschluss. Fremde Journale wurden nur mit `mode=ro&immutable=1` geöffnet.

Das originale `node-tools/qikvrt_mirror_emit.py` fehlt in den untersuchten Quellständen; der tatsächliche `status`-Aufruf endete mit ENOENT. Daher wurde kein neues `assess`/`adopt`, Outbox-Paket, `sent`, `receipt`, `claim`, Empfänger-NACK oder produktives DONE erzeugt. Der konkrete Träger bleibt die Originalquelle dieses Werkzeugs mit ihrer tatsächlichen Knoten-/Journal-/Signiererbindung; eine Ersatzimplementierung wurde nicht eingeführt.

Für die offenen Artikelbelege ist der kleinste Nachfolger der originale, signierte Export aus der genannten Epoche einschließlich Ereignissen 49–54, der bezeichneten Outbox- und Rückgaberecords sowie ihrer wirklichen Sende-/Ingressbindungen über den bestehenden zugelassenen QIK-VRT-Weg. Die Arbeitsbilanz verlangt zusätzlich eine prospektive Vergleichsmessung. Die fehlenden Quellen werden weder durch eine neue Owner-Botenaufgabe noch durch zusätzliche Dienste ersetzt.

Alle überprüften Behauptungen stehen mit Quellen-IDs und Korrekturbedarf in [CLAIM_MATRIX_NACHTRAG.json](CLAIM_MATRIX_NACHTRAG.json). [SOURCES_NACHTRAG.json](SOURCES_NACHTRAG.json) enthält die eingefrorenen Quellversionen, [SOURCE_AUDIT.json](SOURCE_AUDIT.json) die nachgerechneten Originalbindungen und [provenance/ORIGINAL_IDENTITIES.json](provenance/ORIGINAL_IDENTITIES.json) die erhaltenen Herkunftsidentitäten. Historische Rohdaten bleiben unverändert; neue Beobachtungen ergänzen sie.
