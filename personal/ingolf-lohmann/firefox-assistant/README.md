<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Personal-Rechercheadapter im vorhandenen Firefox-Terminal

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
  --personal-model <explicit-model-id>
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
Dieser Adapter verwendet OpenAI API-Zugang; er behauptet keinen authentifi-
zierten ChatGPT-Pro-/SSO-Pfad. Fehlt dieser API-Träger, bleibt die Grenze offen.

## Gewöhnliche Baseline ohne Persistenzverlust

Verglichen werden derselbe Assistant, Provider, explizite Modellstand,
Instruktionen, Parameter (`store=true`) und Quellenzugang. Beide Modi erstellen
separate normale Provider-Conversations und behalten deren dauerhafte Kennung,
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

Normale Provider-Conversations werden gemäß der offiziellen API als dauerhafte
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

Die externen API-Spezifikationen sind nicht mitvendort. Ihre Verfügbarkeit
belegt keine Authentifizierung dieses Benutzers oder dieses Versuchshosts.
