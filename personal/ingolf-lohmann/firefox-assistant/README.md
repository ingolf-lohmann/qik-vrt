<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Universales Raumzeit-Terminal

Der technische Produktname lautet **Universales Raumzeit-Terminal**. Product
Owner Ingolf Lohmann hat diesen Namen am 2026-10-05 freigegeben. QIK-VRT bleibt
die technische Systembezeichnung; der persönliche Browserassistent für
quellgebundene Recherche, Dokumentation und Fortsetzung beschreibt den konkreten
Anwendungsfall. Eine zusätzliche Fantasie- oder Markenbezeichnung ist nicht
festgelegt. Die Namensfreigabe ist kein Kundennutzen-Nachweis: Die unten
beschriebenen Ausführungs- und Messgrenzen bleiben offen.

## Personal-Rechercheadapter im vorhandenen Firefox-Terminal

Ein opt-in Adapter am bestehenden Port 8771 führt quellgebundene Recherche- und
Dokumentationsdialoge aus. Er ist kein zweiter Webserver, keine Kopie des
Firefox-Pakets und kein Mess-Harness. Der Standarddownload erhält keine
persönlichen Inhalte. Manifest: `CAPABILITIES.json`.

## Start und echte Authentifizierung

Python-Standardbibliothek einschließlich SQLite, vorhandene Toolchain; kein
zusätzliches SDK und kein stiller Modellwechsel. Im Backend-Prozess müssen
`OPENAI_API_KEY` und ein zufälliger lokaler `QIKVRT_PERSONAL_LOCAL_TOKEN`
(32–256 Zeichen, Buchstaben/Ziffern/Unterstrich/Minus) aus einem autorisierten
Secret Store oder der Prozessumgebung bereitstehen. Niemals in Git, Browser-
Storage oder Befehlsargumenten ablegen. Der Server gibt keine Schlüssel aus.
Die Auswahl des konkreten verfügbaren Modells erfolgt explizit:

```bash
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B src/qikvrt_effect_ack_http_terminal.py \
  --personal-state-dir /private/runtime/qikvrt-personal \
  --personal-model <explicit-model-id> \
  --personal-budget-file /private/runtime/confirmed-openai-budget.json
```

Das private Verzeichnis liegt außerhalb des Repositorys und hat auf POSIX
Modus 0700; Dateien erhalten 0600. Unter Windows sind die privaten ACLs durch
den Betreiber bereitzustellen; dieser Kandidat enthält keinen Windows-ACL-
Witness. In Firefox `http://127.0.0.1:8771/personal/` öffnen, den lokalen
Sitzungsschlüssel eingeben und verbinden. Der API-Schlüssel verbleibt im
Backend. Der lokale Schlüssel lebt nur im Speicher der Seite; Seitenreload
verlangt erneute lokale Authentifizierung. Host-/Origin-Prüfung, fehlende CORS-
Freigabe und CSP beschränken die Personal-Routen auf den lokalen Client.

Eine tatsächlich abgeschlossene Modellantwort kann `/personal/capabilities`
einen frischen Runtime-Readback für die aktuell gebundenen Quellbytes geben.
Test-Doubles dürfen diesen Status nicht erzeugen. Das ist keine Personen-
identitätsattestierung, unabhängige fachliche Prüfung oder Produktabnahme.
Standardmäßig verwendet dieser Adapter OpenAI API-Zugang. Der explizite
Claude-Pfad ist unten beschrieben. Kein Pfad behauptet einen authentifizierten
ChatGPT-Pro-/SSO-Zugang oder eine aktivierte Claude-Subscription.

## Gewöhnliche Baseline ohne Persistenzverlust

Innerhalb eines Anbieters werden derselbe Assistant, Provider, explizite Modellstand,
Instruktionen, Parameter (`store=true`) und Quellenzugang. Beide Modi erstellen
bei OpenAI separate normale Provider-Conversations und behalten deren dauerhafte Kennung,
vollständige lokale Gesprächshistorie und gespeicherte Entwürfe. Die Oberfläche
listet frühere Gespräche und öffnet sie nach Restart wieder. Sie löscht weder
Baseline-Tabs noch Dokumente oder Chat-Historie und bietet keinen künstlichen
Baseline-Reset an. Eine beabsichtigte Gesprächskontext-Unterbrechung im späteren
Versuch darf diese normale Persistenz nicht entfernen.

Nur `qikvrt` fügt beim Wiederaufnehmen einen Checkpoint aus der tatsächlich
beobachteten letzten Antwort, Aufgabe und Quellenhashes hinzu. `baseline`
setzt die vorhandene Conversation mit dem normalen Fortsetzungswunsch fort.
Ein Checkpoint ist ein unbestätigter Modell-/Arbeitsstand, kein akzeptierter
Schrittoutput. Der Adapter liest weder Fixtures noch Bewertungsoracle und
erzeugt keine Produktmetriken. Diese Baseline bezeichnet die gewöhnliche
Gesprächsfunktion des Adapters; sie repräsentiert keinen gemessenen Vergleich
mit der ChatGPT-Weboberfläche oder einem fremden Produkt.

Gespeichert wird in SQLite mit WAL, `synchronous=FULL` und einem vom
Betriebssystem bei Prozessverlust freigegebenen Writer-Lock. Vor jeder
Provider-Anfrage wird ein dauerhafter Pending-Eintrag angelegt. Bei Timeout,
unvollständiger Antwort oder Prozessverlust während der Anfrage wird kein
blindes Retry ausgeführt. Der unveränderte Pending-Stand bleibt sichtbar und
blockiert weitere Generierung dieser Sitzung bis zur separat zu prüfenden
Provider-Reconciliation. Dieser Kandidat implementiert noch keine automatische
Auflösung unbekannter externer Antwort-IDs.

Normale OpenAI-Provider-Conversations werden gemäß der offiziellen API als dauerhafte
Gesprächsobjekte genutzt. Das reale Lesen der Provider-Historie nach Restart
ist ein noch offener Preflight-Beleg; lokale SQLite-Tests ersetzen ihn nicht.
Quellengebundene Dialoge verwenden hier vom Benutzer bereitgestellte Quellen;
autonomes Web-Browsing und eine Modell-Tool-Sandbox sind noch nicht angebunden.

## Nachweisgrenze

Technische Tests verwenden ausdrücklich Transport-Doubles, nie Nutzertrials:

```bash
make personal-firefox-boundary-test browser-assistant-ab-test
python3 -B tools/qikvrt_browser_assistant_ab.py preflight
```

Vor den 24 Produkttrials fehlen im beobachteten Host: echte autorisierte
Modell-Runtime, gebundener gewöhnlicher Baseline-/Provider-Retention-Readback,
Firefox, beobachtete äquivalente Vorläufe, Unterbrechungsinstrumentierung und
Oracle-Isolation. Der vorhandene Evaluator bleibt auf Harness-Daten begrenzt.
Es erfolgt keine Umbenennung technischer Tests in Produktmessungen.

API-Vertrag, am 2026-10-05 gelesen:

- https://developers.openai.com/api/reference/overview
- https://developers.openai.com/api/docs/guides/conversation-state
- https://developers.openai.com/api/reference/resources/conversations/methods/create
- https://developers.openai.com/api/reference/resources/responses/methods/create

## Claude und getrennte Budgets (Version 1.1.0, Issue #503)

Auf Basis von PR #496 wird derselbe Adapter erweitert. Für Claude explizit
`--personal-provider claude` und einen eigenen privaten `--personal-state-dir`
angeben. `ANTHROPIC_API_KEY` ersetzt nur in diesem Pfad `OPENAI_API_KEY`.
Provider und Modell eines existierenden Verzeichnisses bleiben unveränderlich.
Eine OpenAI-Sitzung wird nicht in Claude umgeschrieben. Claude sendet den
vollständigen lokalen Verlauf über die zustandslose Messages-API; eine
serverseitige Conversation-Speicherung wird dafür nicht behauptet.

```bash
python3 -B src/qikvrt_effect_ack_http_terminal.py \
  --personal-provider claude \
  --personal-state-dir /private/runtime/qikvrt-claude \
  --personal-model <exact-model-id> \
  --personal-budget-file /private/runtime/confirmed-claude-budget.json
```

Auch neue OpenAI-Aufrufe benötigen jetzt einen bestätigten Budgetnachweis.
Das ist eine bewusst strengere Ausführungsbedingung. Bestehende SQLite-
Sitzungsbytes, Conversation-IDs, Quellen und Entwürfe werden nicht migriert
oder gelöscht; ihr lokaler Readback bleibt ohne Budget verfügbar. Nach Import
eines passenden Budgets kann dieselbe OpenAI-Conversation fortgesetzt werden.

### Privater Budgetnachweis

Die Datei liegt außerhalb von Git, auf POSIX mit Modus 0600. Sie enthält keine
Credentials. Der Import ist eine ausdrückliche Bestätigung des Betreibers
anhand eines aktuellen Console-/Billing-Nachweises, kein automatischer
Kontostandsabruf. Dessen private Quelldatei wird nur durch SHA-256 gebunden.
Die Anwendung behauptet weder Aktivierung noch unabhängige Verifikation des
Kontos. **Ein Tarifname erzeugt niemals Guthaben.** Das Budget-Schema ist
`qikvrt_personal_budget_v1`; die folgende Struktur ist absichtlich unbestätigt
und nicht ausführbar, bis alle erforderlichen Werte aus echten Nachweisen
eingetragen wurden. Geldbeträge sind ganzzahlige Mikro-USD (1 USD = 1000000).
Zeitpunkte sind UTC-Unixsekunden. `null` bedeutet unbekannt, nicht kostenlos.

```json
{
  "schema": "qikvrt_personal_budget_v1",
  "provider": "claude",
  "organization_id": "REQUIRED",
  "workspace_id": "REQUIRED",
  "subscription": {"plan": null, "status": null, "linked_organization_id": null},
  "observation": {
    "id": "REQUIRED-UNIQUE-OBSERVATION",
    "source_sha256": "REQUIRED-64-HEX-DIGEST",
    "confirmed_at": 0, "valid_until": 0, "ledger_revision": 0
  },
  "credits": [
    {"id": "confirmed-promo", "kind": "subscription", "remaining_micro_usd": null, "expires_at": null, "cycle_id": "REQUIRED"},
    {"id": "confirmed-purchased", "kind": "purchased", "remaining_micro_usd": null, "expires_at": null, "cycle_id": null}
  ],
  "limits": [
    {"id": "local", "period_start": 0, "period_end": 0, "remaining_micro_usd": null},
    {"id": "organization", "period_start": 0, "period_end": 0, "remaining_micro_usd": null},
    {"id": "workspace", "period_start": 0, "period_end": 0, "remaining_micro_usd": null}
  ],
  "pricing": {
    "model": "REQUIRED-EXACT-MODEL-ID",
    "source_sha256": "REQUIRED-64-HEX-PRICE-DIGEST",
    "valid_until": 0, "input_token_ceiling": 0, "max_output_tokens": 0,
    "input_micro_usd_per_million": 0, "output_micro_usd_per_million": 0,
    "max_request_micro_usd": 0
  },
  "allow_purchased": false, "billing_mode": "prepaid", "auto_reload": false,
  "warning_remaining_percent": [20, 10], "expiry_warning_seconds": 86400
}
```

`input_token_ceiling` muss die dokumentierte maximale Eingabekapazität des
gewählten Modells abdecken. Die Raten müssen obere Kostengrenzen für alle
anwendbaren Tarif-/Kontextstufen sein. Reserviert werden konservativ die
vollständige Eingabekapazität plus das konfigurierte Ausgabelimit, nicht eine
Tokenschätzung. Ohne überprüfbare Preis-/Kontextbindung bleibt der Aufruf
gesperrt. Das Ausgabelimit wird im API-Payload erzwungen. Die Rückantwort muss
genau das preisgebundene Modell nennen; Modell-Aliase mit anderer Auflösung
werden gesperrt. Tools, Bilder, Thinking-Konfiguration und bezahlte Zusatz-
dienste sind nicht Teil dieses Pfads.

Die jeweils kleinste verfügbare Grenze aus Guthaben, lokalem Budget,
Organisations- und Workspace-Limit entscheidet. Unbekannte Kreditpools werden
nicht verwendet; bekannte gekaufte Guthaben nur bei `allow_purchased=true`.
Bestätigte Subscription-Guthaben werden zuerst verbraucht. Ein Abrechnungs-
wechsel erzeugt keine Einzahlung, ein Kalenderwechsel setzt lokal keine
Limits zurück. Ein neuer bestätigter Snapshot muss die aktuelle
`ledger_revision` aus `/personal/budget` und einen jüngeren Beobachtungszeitpunkt
tragen; er darf keine offenen Reservierungen überschreiben. Derselbe Snapshot
ist bei erneutem Import wirkungslos. Abgelaufene Daten bleiben lesbar.

Die Reservierung erfolgt mit SQLite `BEGIN IMMEDIATE` vor dem ersten
Provider-Aufruf, bleibt über Neustart bestehen und wird bei eindeutig
zuordenbarer Token-Nutzung abgerechnet. Die lokale Kostenrechnung bleibt eine
Obergrenze aus dem bestätigten Preisvertrag, keine Provider-Rechnung.
Unbekannte Nutzung oder Überschreiten des Preisvertrags friert weitere Aufrufe
ein. Vor Claude-Generierung wird der kostenfreie Token-Count-Pfad auch für den
Abgleich der tatsächlich gemeldeten Organisation und des Workspace verwendet.
Abweichende oder fehlende Scope-Header stoppen vor der kostenpflichtigen Anfrage.

`/personal/budget` erfordert die vorhandene lokale Authentifizierung. Es zeigt
Kreditpools, unabhängige Limitperioden, Ablaufdaten, Nachweisstatus und
Warnschwellen. Die Oberfläche zeigt Sperren und Warnungen. Die lokale
Reservierung koordiniert nur diesen gemeinsamen Ledger; fremde API-Keys können
ein geteiltes Konto zusätzlich belasten. Ein dedizierter Workspace mit
providerseitigem Limit und zeitnahem Abgleich ist deshalb Teil des Betriebs-
vertrags. Diese Implementierung setzt keine entfernten Limits und deaktiviert
kein bereits anderswo aktiviertes Auto-Reload. Der Betreiber muss dessen
Deaktivierung tatsächlich bestätigt haben (`auto_reload=false`, Prepaid).
Es existiert kein Kauf-, Claim-, Reload- oder Subscription-Schreibpfad.

### Wiederholung und offene Außenwirkung

Die additive HTTP-Eigenschaft `request_id` bindet genau einen Auftrag.
Wiederholungen desselben Auftrags liefern das gespeicherte Ergebnis; geänderte
Inputs oder Anbieter unter derselben Kennung werden abgelehnt. Alte Clients
ohne Kennung erhalten einen deterministischen Inhaltsschlüssel. Für bewusst
identische neue Arbeit ist eine neue explizite Kennung erforderlich. Die
Oberfläche hält nur Kennung und Eingabehash im Tab-Speicher über Reload fest,
keine Schlüssel oder Texte. Der A/B-Carrier bindet ausdrücklich neue Aufträge
an seine bereits existierende Observer-Epoche.

Bei Timeout, HTTP-Fehler, Crash oder unverständlicher Antwort bleibt die volle
Reservierung gebunden. Es gibt keine automatische Wiederholung und keinen
automatischen Anbieterwechsel. Ein anderer Auftrag derselben ungeklärten
Sitzung wird ebenfalls gesperrt. Alte Reservierungen werden bei Guthaben-
verfall nicht in neues Guthaben umgewandelt. Der Kandidat enthält keine
automatische Remote-Reconciliation. Die kleinste Fortsetzung ist der
authoritative Abgleich von Request-ID, Provider-Nutzung und lokalem Pending-
Datensatz; keine DB-Löschung, kein Refill und kein Fallback ersetzt diesen.

Primärquellen, am 2026-10-09 geprüft:

- Credits, Verfall, getrennte Abrechnungs- und Limitperioden:
  https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers
- HTTPS-Authority, Authentifizierung und Scope-Header:
  https://platform.claude.com/docs/en/api/overview
- Zustandslose Gesprächsfortsetzung:
  https://platform.claude.com/docs/en/build-with-claude/working-with-messages
- Kostenfreie Tokenschätzung (keine garantierte Kostenschranke):
  https://platform.claude.com/docs/en/build-with-claude/token-counting

Die Tests verwenden kontrollierte Provider-Doubles. Kontoguthaben, Aktivierung,
echte Modellantworten und produktiver Firefox-Betrieb sind weiterhin unbewiesen.

Die externen API-Spezifikationen sind nicht mitvendort. Ihre Verfügbarkeit
belegt keine Authentifizierung dieses Benutzers oder dieses Versuchshosts.
