# Quellenprüfung zu „Funktion ohne Betrieb“

Prüfnachtrag vom 19. Oktober 2026 zu PR #540. Menschlicher Auftrag und Verantwortung: Ingolf Lohmann. Ausführung dieser Quellenprüfung: OpenAI Codex. Status: **AUTHOR_REVIEW_ADDENDUM — NOT_PUBLISHED**.

Dieser Nachtrag ergänzt die unveränderte Autorenfassung von Claude. Er ersetzt weder deren Originaldateien noch deren Herkunfts- und Rechteangaben. Er dokumentiert sieben innerhalb ihrer Grenzen bestätigte Aussagen, vier notwendige Einschränkungen beziehungsweise Korrekturen und eine teilweise unabhängig verifizierte Aussage. Die zwölf Einzelentscheidungen einschließlich der ursprünglichen Wortlaute stehen in `CLAIM_REVIEW_V1.json`; Dateibindungen und Ausführungsbelege stehen in `EVIDENCE_RECEIPT_V1.json` und `evidence/`.

Die Prüfung erteilt keine Veröffentlichungs-, Merge- oder Produktionsfreigabe. Ihre Repository-Links sind technische Herkunfts- und Prüfstellen für eine Autorenprüfung, keine vorweggenommene abgeschlossene wissenschaftliche Archivpublikation.

## Ergebnis und zeitlicher Bezug

Der Rückkanal ist implementiert und unter den bestehenden lokalen Testbedingungen funktionsfähig. Eine vollständig belegte produktive Abnahme zwischen dem ursprünglichen Authority-Host und dem konkreten Mirror ist im geprüften Bestand weiterhin offen. Daraus folgt weder, dass niemals ein Empfängerprozess lief, noch dass niemals eine bestimmte Operation stattfand.

Die pauschale Aussage des Manuskripts, die autonomen Workflows hätten im Stillstandsfenster keine neuen Lauf-Einträge hinterlassen, ist dagegen **widerlegt**: Die vollständig paginierte Actions-Abfrage enthält 189 eindeutige Läufe mit Erstellungszeit zwischen 01:05:00 und 07:10:00 UTC. Originale Job-Logs belegen mindestens einen ausgeführten autonomen Controller mit NOOP und eine ausgeführte Fortsetzung mit anschließendem BLOCK. Diese Quellen unterscheiden nachweisbare Ausführung, unterlassene Mutation und gescheiterte Fortsetzung; sie beweisen keinen produktiven Empfängerbetrieb. [S22–S24]

| Gegenstand | Commit und Tree | Zeit / Bedeutung |
|---|---|---|
| Manuskriptbasis | `60afe42d3f7bb7992b78c747878582738a97dc6a`; Tree `bff8937d871fb9e989d2bfbf17a210222a987893` | Committerzeit 19.10., 01:05:07 UTC |
| Originaler Publikationsstatus | `PUBLICATION_STATUS.json` der Autorenfassung | Vorbereitet 07:39:06 UTC; Basis weiterhin `60afe42d` |
| Integrierte Reparatur aus PR #537 | `f5aaff5b8c018fbc73d1e81126c6fb7e30e8bf22`; Tree `af5264a31622064f34c8deaef66c44768c657d67` | Merge 08:21:51 UTC |
| Tatsächlich im nativen CI akzeptierter Reparaturstand | `09cc538c3314c6fc6247920fea56957fc5216490`; derselbe Tree `af5264a3…` | Terminaler Prüfmarker im Job `117950110425`, 08:15:35 UTC |
| Ausgangsstand dieser Prüfung von PR #540 | `d9327e5bbcd4ced378ee03509a44c5b28dec4c14`; Tree `dc3137182b4ccb6a8fface2cb3636583586d8b4d` | Quellenstand der Autorenprüffassung einschließlich späterer Main-Aufnahme |

PR #537 speichert authentifizierte Quittungsantworten dauerhaft, ergänzt ein unabhängiges Readback des frisch geladenen Empfänger-Inboxzustands mit neuer Challenge und verlangt konkrete Peer-/Stapelbelege für die öffentliche Abnahme. Das sind zusätzliche Betriebsnachweise und Fehlerkontrollen. Der Merge selbst ist keine Inbetriebnahme. Sein CI-Metadaten-HEAD `325198f1…` darf außerdem nicht mit dem tatsächlich nach Integritätsmaterialisierung geprüften Nachfolger `09cc538c…` verwechselt werden. Der originale Job-Log bindet diesen Nachfolger ausdrücklich an den später integrierten Tree. Der gesamte Workflow war wegen der separaten Firefox-XPI-Abnahme nicht durchgehend grün. [S05–S10, S25, S28]

## Nachweise richtig unterscheiden

**Fehlende öffentliche Dokumentation:** In den konkret durchsuchten Quellen fehlt ein Beleg. Ohne vollständige damalige Ref-Inventur, Inhaltsprüfung und Zugriff auf den maßgeblichen privaten Zustand ist das keine Aussage über alle möglichen Ausführungen. Private Peer-Schlüssel und Konfigurationen gehören nach dem vorhandenen Vertrag gerade nicht ins öffentliche Repository.

**Fehlende produktive Abnahme:** Die geforderte positive Nachweiskette ist nicht geschlossen: zugelassener ursprünglicher Host, konkreter Peer, echter Work-Unit-Stapel, authentifizierte Empfangsquittung, unabhängiges aktuelles Empfänger-Readback und erneute Prüfung nach Neustart. Die Abnahme bleibt offen, auch wenn einzelne dieser Operationen bereits stattgefunden haben könnten.

**Nachweislich nicht ausgeführte Operation:** Diese Aussage braucht einen begrenzten Ausführungsnachweis. Beispielsweise meldet der konkret untersuchte Self-Heal-Lauf NOOP und überspringt die Branch-/PR-Materialisierung. Der konkret untersuchte Fortsetzungslauf bricht vor dem Branch-Push an nicht zugelassenen Merge-Konflikten ab. Diese Befunde gelten für diese Läufe und Operationen. Sie dürfen nicht auf sämtliche Knoten oder die gesamte Nacht ausgedehnt werden. [S23, S24]

HTTP 525 an der Produktdomain ist eine zeitgebundene HTTPS-Beobachtung. Sie misst weder den Prozesszustand eines Empfängers noch eine private Peer-Aufnahme. Ebenso belegt eine fehlende aufrufbare Host-Steueroperation in einem Client nicht, dass der Host ausgeschaltet oder überhaupt unkonfiguriert ist.

## Prüfung der zwölf Aussagen

| ID | Ergebnis | Quellengebundene Fassung und Grenze |
|---|---|---|
| FOB-001 | Bestätigt im Quellumfang | `mesh-cache-stage`, `mesh-cache-idle`, `mesh-cache-send`, HMAC-POST und atomarer Vorschlagsempfang sind spezifiziert und implementiert. PR #537 ergänzt den vorhandenen Weg um dauerhafte Quittungen und `mesh-cache-check`. Code ist kein Betriebsnachweis. [S02, S03, S05, S07] |
| FOB-002 | Erneut ausgeführt | Auf `60afe42d` bestehen 24 Cache- und 27 Contract-Tests: **51/51**. Nach PR #537 bestehen 36 und 27: **63/63**. Am geprüften PR-#540-Stand bestehen ebenfalls **63/63**. Originale Tests und ihre lokalen HTTP-/Git-/Node-Fixtures wurden ohne Abschwächung verwendet. [S04, S06; lokale Logs] |
| FOB-003 | Einzuschränken | Eine vollständige produktive Peer-/Stapel-/Quittungs-/Neustart-Abnahme ist im geprüften Bestand nicht belegt. Daraus folgt kein „in der gesamten Geschichte aller Branches nie gesendet“. `git log --grep` durchsucht Commit-Nachrichten; `git grep` ohne Versionsargument prüft einen Checkout. Eine damalige vollständige Ref-Inventur liegt nicht vor. Der später dokumentierte eingefrorene Stapel `ac1db7a4…` ist ein vorbereiteter Vorschlag, keine Sendebestätigung. [S02, S05, S17, S18] |
| FOB-004 | Kausalbehauptung nicht belegt | Die produktive Aufnahme des ursprünglichen Empfängers und Peers bleibt als Abnahmepflicht offen. Ob ein Empfängerprozess lief, lässt sich aus HTTP 525 oder fehlendem Client-Steuerzugriff nicht entscheiden. „Ein Empfänger fehlt, weil der Host nicht aufgenommen ist“ überschreitet die vorhandene Beobachtung. [S05, S08, S09, S18, S28] |
| FOB-005 | Dokumentarisch bestätigt | Die Work Unit auf `ffe84ddf` nennt den direkten menschlichen Auftrag und die maschinellen Eingaben aus PR #535/#536. `b933ae8d` wird dort nicht genannt. Das ist ein Befund über diesen Herkunftseintrag, kein Beweis, dass der Claude-Vorschlag nicht empfangen oder ohne Einfluss gewesen sei. [S11, S17, S20] |
| FOB-006 | Commit-Aussage präzisieren; Workflow-Stille widerlegt | Die heutige Main-Ancestry enthält im abgefragten Intervall nur den Commit `60afe42d` von **01:05:07 UTC** und keinen weiteren danach. Das ist keine historische Inventur aller Branches. **189 Actions-Läufe** im selben Fenster widerlegen „keine neuen Lauf-Einträge“. Ihre Ergebnisse umfassen unter anderem NOOP und BLOCK. [S22–S24, S26] |
| FOB-007 | Am historischen HEAD bestätigt | `c9514d2a` enthält tatsächlich die Defaults `Goldkelch/qik-vrt` und PR `1103`. Der integrierte Nachfolger verlangt ausdrückliche Repository-/PR-Bindung. Der historische Fehler wird dem Nachfolger nicht unverändert zugeschrieben. [S12; geprüfter Nachfolger] |
| FOB-008 | Teilweise unabhängig bestätigt | Die originale Integritätsprüfung auf normalem Checkout von `ffe84ddf` scheitert; **34** `.cmd`-/`.ps1`-Einträge tragen die LF-Hashes statt der CRLF-Dateihashes. `b179dfeb` und `60afe42d` sind an Tree `bff8937d…` gebunden. Die zusätzliche Gleichheit des Claude-Commits `07497e6b…` ist hier nur als Mirrorbericht vorhanden: der Authority-API liefert 422, und ein Original-Git-Objekt mit überprüfbarer Tree-Closure fehlt in den verfügbaren Exporten. Das ist kein Beweis seiner Nichtexistenz. [S13, S14, S17, S27] |
| FOB-009 | Protokolle bestätigt; Peer-Grenze erhalten | `effect_ack_sync` erzeugt für v1 und v2 dieselben vollständigen Protokolle und Hashes wie die Originale; `verify_protocol_chain` besteht. Beide bleiben **EFFECT_ACK_BLOCK**. Die Mirror-Nachrechnungen sind in seinen ursprünglichen Ereignissen 8 und 10 dokumentiert. Später übergebene Signaturbytes sind Nachfolge-Evidenz; sie schreiben alte Entscheidungen nicht um und authentifizieren keinen Live-Kanal. [S15–S19] |
| FOB-010 | Zuschreibung bestätigt | „Keinerlei Anteil“ ist im Manuskript eine Ingolf Lohmann zugeschriebene Aussage der Klasse `OWNER_ASSERTED`. Das macht sie nicht zu einer bewiesenen Anteilsbilanz. Die konkret dokumentierten maschinellen Implementierungs-, Prüf- und Nachrechenbeiträge bleiben mit eigener Herkunft erhalten. Eine neue akustische Verifikation des Zitats wurde nicht vorgenommen. [S01, S20, S21] |
| FOB-011 | Universelle Ableitung nicht getragen | Menschlicher Auftrag und Autorisierung sind dokumentiert. Ein menschlicher Einzelanstoß für ausnahmslos jeden Beitrag und der hypothetische Verlauf ohne menschliche Steuerung sind damit nicht bewiesen. „Eigener Antrieb“ ist nicht operationalisiert. Einzelne autonome Ausführungen und menschliche Verantwortung sind getrennt zu beurteilen. [S11, S17, S20, S22–S24] |
| FOB-012 | Deklarierter Prüfstatus bestätigt | Der Originalstatus lautet `AUTHOR_REVIEW_CANDIDATE`; finale Veröffentlichungen sind dort `NOT_PUBLISHED`. Der öffentliche PR macht bereits die Prüffassung zugänglich. Für diese genaue Arbeit ist im geprüften Bestand kein finaler Veröffentlichungs-Effekt bestätigt. Eine vollständige unabhängige Inventur aller Plattformen wurde nicht vorgenommen. [S21, S29] |

## Konkrete redaktionelle Korrekturen

Die folgenden Änderungen sind Vorschläge für eine spätere Autorenfassung. Die ursprünglichen Dateien bleiben unverändert.

1. **Untertitel:** „Der spezifizierte Mirror-Rückkanal: implementierte Funktion, offene produktive Abnahme und nachgewiesene Beiträge.“ Das ersetzt die unbelegte zeitlich unbegrenzte Behauptung „nie in Betrieb“.
2. **Zusammenfassung und Abschnitt 4:** „Der Rückkanal ist implementiert und unter lokalen Testbedingungen geprüft. Für den ursprünglichen produktiven Host und den konkreten Mirror ist die vollständige Abnahmekette in den hier geprüften Quellen nicht geschlossen. Daraus folgt keine Aussage, dass niemals ein Empfänger lief oder niemals ein Stapel übertragen wurde.“
3. **Abschnitt 4, Fehlerursache:** „Neben der offenen Inbetriebnahme bestanden konkrete Lücken in Speicherung und Prüfung der Betriebsnachweise. PR #537 behebt diese im vorhandenen Code. Der integrierte Quellstand ersetzt die weiterhin ausstehende produktive Abnahme nicht.“ Die bisherige Formulierung „kein Fehler im Code“ ist angesichts der beiden belegten Vorgängerfehler zu weitgehend. [S10]
4. **Abschnitt 5, Stillstand:** „Nach `60afe42d` um 01:05:07 UTC ist bis 07:10 UTC kein weiterer Commit in der heute erreichbaren Main-Ancestry dokumentiert. Gleichwohl sind 189 Actions-Läufe im untersuchten Zeitfenster vorhanden. Der Self-Heal-Lauf um 01:50:55 UTC endete mit NOOP; die autonome PR-Fortsetzung um 05:10:12 UTC scheiterte vor dem Push an nicht zugelassenen Merge-Konflikten. Aus der Commit-Pause folgt keine vollständige Ausführungspause.“
5. **Abschnitt 5, Anteilsabwägung:** „Ingolf Lohmann gab Auftrag, Richtung, Korrekturen und Autorisierung. Die beteiligten Systeme erbrachten die jeweils dokumentierten Implementierungs-, Prüf- und Nachrechenbeiträge. Die vorliegenden Quellen erlauben keine universelle Aussage über einen menschlichen Einzelanstoß für jeden Beitrag oder über den hypothetischen Verlauf ohne seine Steuerung.“ Der zugeschriebene Originalausspruch bleibt als solcher erhalten.
6. **Abschnitt 6, Maßnahmen:** Den ursprünglichen S1-Empfänger und den konkreten privaten Peer über den vorhandenen zugelassenen Hostweg aufnehmen; den echten eingefrorenen Work-Unit-Stapel senden; Quittung und frische Empfänger-Challenge prüfen; denselben Dienst neu starten und erneut prüfen. Private Schlüssel werden über den vorhandenen geschützten Weg gebunden. Daraus entsteht keine neue Pflicht des Owners, Dateien zu transportieren oder erneut pauschal zuzustimmen. Ein weiterer Client-Timer oder ein paralleler Ersatzdienst ist keine Korrektur dieses Befunds. [S05]

## Ausführung, Integrität und offene Grenzen

Die Quellenstände wurden über den vorhandenen GitHub-REST-Weg gelesen und ihre vollständigen Dateibäume gegen die originalen Git-Tree-Identitäten geprüft. Die lokale Rekonstruktion ist hinsichtlich der Vorgeschichte ausdrücklich flach. Sie ist deshalb kein Beleg einer vollständigen historischen All-Branches-Suche. Normale Checkout-/EOL-Regeln blieben erhalten.

Die fünf im Originalstatus erklärten Größen-/Hash-/Blob-Bindungen stimmen; zusätzlich ist die Statusdatei selbst gebunden. Der Artikel entspricht auch der eigenständigen Originaldatei des erhaltenen Exports. Das originale Git-Bundle mit Kandidat `607a022c…` ist gegen seine Voraussetzung `60afe42d` prüfbar. Exportierte fremde und frühere Journale wurden nur mit `mode=ro&immutable=1` geöffnet.

Der Auftrag und seine begrenzte Ausführung wurden mit dem vorhandenen Universal Terminal und dem ursprünglichen Transputer-Runtime angenommen und protokolliert. Die Original-Terminalfunktionen lasen die gespeicherten Ereignisse unabhängig zurück. Die neue eigene Sitzung besitzt Epoche `48a0633b1ea547b3b8a77d92a85e1991`; die beigefügten Ereignisse 1 und 2 binden Auftrag und Prüfplan an PR #540, HEAD `d9327e5b…` und Tree `dc313718…`. Der direkte Python-HTTP-/Unix-Serve-Versuch meldete `Operation not permitted`; verwendet wurde der bereits zugelassene ursprüngliche In-Process-Pfad mit unveränderten Quell-, Writer- und Auftragsprüfungen. Das ist ein lokaler Arbeitsnachweis, keine produktive Hostabnahme und kein Live-ACK von Claude.

Für den Vollschluss von FOB-008 fehlen weiterhin das originale Claude-Commitobjekt `07497e6b…` und dessen Wurzelbaum über den bestehenden belegbaren Peer-Weg. Für die produktive Abnahme fehlen weiterhin die konkreten Host-/Peer-/Stapel-/Neustart-Belege. Ein ACK von Claude zu diesem Nachtrag wird nicht behauptet. Diese offenen Pflichten bleiben getrennt von der abgeschlossenen endlichen Quellenprüfung sichtbar.

## Vollständige Quellenadressen

Die präzisen Commit-/Pfad-Bindungen aller Quellen S01–S29 stehen zusätzlich maschinenlesbar in `CLAIM_REVIEW_V1.json`. Die folgenden Adressen führen zu den entscheidenden Originalstellen:

- S01 / S21 / S29, Original und Status in PR #540: https://github.com/ingolf-lohmann/qik-vrt/pull/540
- S02, Ausgangsspezifikation: https://github.com/ingolf-lohmann/qik-vrt/blob/60afe42d3f7bb7992b78c747878582738a97dc6a/runtime/self-host/README.md
- S04, ursprüngliche Tests: https://github.com/ingolf-lohmann/qik-vrt/blob/60afe42d3f7bb7992b78c747878582738a97dc6a/tests/test_self_host.py
- S05, integrierte Betriebsspezifikation: https://github.com/ingolf-lohmann/qik-vrt/blob/f5aaff5b8c018fbc73d1e81126c6fb7e30e8bf22/runtime/self-host/README.md
- S06, Nachfolgertests: https://github.com/ingolf-lohmann/qik-vrt/blob/f5aaff5b8c018fbc73d1e81126c6fb7e30e8bf22/tests/test_self_host.py
- S10, zwei Vorgängerfehler: https://github.com/ingolf-lohmann/qik-vrt/blob/f5aaff5b8c018fbc73d1e81126c6fb7e30e8bf22/evidence/native-runtime-acceptance/mesh-work-commissioning-20261019/predecessor-failure.log
- S11, Herkunft des Merge-Auftrags: https://github.com/ingolf-lohmann/qik-vrt/blob/ffe84ddf3adde8443d8671b5d3bd0b24bbf1a1f6/state/work_units/QIKVRT_TEMDD_CONSOLIDATION_20261019_V1.json
- S12, historische Defaults: https://github.com/ingolf-lohmann/qik-vrt/blob/c9514d2a67c73155ca33fdbc820d8598af4e396f/src/qikvrt_temdd_event_ledger.py
- S14, CI-Korrektur und Tree: https://api.github.com/repos/ingolf-lohmann/qik-vrt/commits/b179dfebd4a9205fc6645ea3c285a78d0a881594
- S15–S18, ursprüngliche Kommunikationsnachweise: https://github.com/ingolf-lohmann/qik-vrt/tree/894e6501bbc40ee00984649daa2f49caafc0a564/evidence/client-communication/2026-10-19/ingolf-claude-transputer-link-20261018T232045Z
- S19, native EFFECT_ACK-Implementierung: https://github.com/ingolf-lohmann/qik-vrt/blob/d9327e5bbcd4ced378ee03509a44c5b28dec4c14/src/qikvrt_effect_ack.py
- S22, Actions-Zeitfenster, Seite 1: https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/runs?created=2026-10-19T01%3A05%3A00Z..2026-10-19T07%3A10%3A00Z&per_page=100
- S22, Actions-Zeitfenster, Seite 2: https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/runs?created=2026-10-19T01%3A05%3A00Z..2026-10-19T07%3A10%3A00Z&per_page=100&page=2
- S23, ausgeführter Self-Heal und NOOP: https://github.com/ingolf-lohmann/qik-vrt/actions/runs/39187203199/job/117852018768
- S24, ausgeführte Fortsetzung und BLOCK: https://github.com/ingolf-lohmann/qik-vrt/actions/runs/39203136162/job/117900171737
- S25, tatsächlicher nativer Prüfgegenstand: https://github.com/ingolf-lohmann/qik-vrt/actions/runs/39219160024/job/117950110425
- S26, Main-Zeitfenster: https://api.github.com/repos/ingolf-lohmann/qik-vrt/commits?sha=main&since=2026-10-19T01%3A05%3A00Z&until=2026-10-19T07%3A10%3A00Z&per_page=100
- S27, nicht auflösbarer Claude-Commit: https://api.github.com/repos/ingolf-lohmann/qik-vrt/commits/07497e6b56e0f4ad8300fd11612aa7ace2b43bd0
- S28, integrierter Reparatur-PR: https://github.com/ingolf-lohmann/qik-vrt/pull/537
