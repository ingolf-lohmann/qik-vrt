<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Universales Raumzeit-Terminal

## Geschützter Personal-Anmeldepfad, 16.10.2026

Der vorhandene Personal-Adapter hat jetzt einen ausführbaren, ausdrücklich
getrennten OIDC-Pfad. Die normale Personal-CLI verlangt
`--personal-auth-config`; der bisherige Prozessspeicher-/Kopplungspfad benötigt
nun ausdrücklich `--personal-legacy-memory-pairing`. Der Standardserver startet
weiterhin ohne Personal-Payload, OIDC-Konfiguration oder neue Abhängigkeiten.

Der neue Pfad verwendet Authorization Code, PKCE S256 und eine einmalige,
fünf Minuten gültige State-/Nonce-Bindung. `response_mode=form_post` hält den
Code aus URL, Verlauf und Referer heraus. Der Callback akzeptiert keine
doppelten Felder. Signatur (RS256), konfigurierter Issuer, ausschließlich
registrierte Client-Audience, gebundener Owner-Subject, Nonce und Gültigkeit
werden geprüft. Die öffentliche Discovery muss die explizit konfigurierten
Endpunkte und die benötigten Protokollfähigkeiten bestätigen. Es gibt keine
Wildcard-Issuer, automatische Anbieterwahl oder Übertragung einer ChatGPT-Sitzung.

Identitätsanmeldung und OpenAI-/Gemini-API-Berechtigung sind getrennte Träger.
Ein Microsoft-, Apple- oder anderer SSO-Login liefert keinen OpenAI-API-Key.
Microsoft OIDC mit Code/PKCE wurde anhand der Primärdokumentation als möglicher
Weg geprüft; eine registrierte Client-/Issuer-/Subject-Bindung für diesen
Personal-Client ist in diesem Work Unit nicht nachgewiesen. Niemand erhält
Zugriff allein wegen einer passenden E-Mail-Adresse. Ein real gewählter Anbieter
muss die vom Client verlangten Funktionen tatsächlich unterstützen; seine
Passkey-/WebAuthn-Oberfläche übernimmt auf Wunsch die Geräteverifikation.
Der Adapter sammelt keine Biometrie und behauptet weder eine bestimmte
biometrische Modalität noch ein bestimmtes Assurance Level.

### Geschützter Speicher und Sitzungslebensdauer

Unter Linux nutzt der Adapter `/usr/bin/secret-tool` aus dem signierten
libsecret-Systempaket und die geschützte Login-Collection des angemeldeten
Desktop-Benutzers. Nicht als root oder in einem fremden Desktop-/D-Bus-Kontext
betreiben. Der Betreiber muss die tatsächlich verschlüsselte Collection und
deren Sperr-/Entsperrverhalten nativ abnehmen; Secret Service allein ist keine
Verschlüsselungsattestierung. Fehlt der Dienst oder bleibt er gesperrt, bricht
der Pfad ab. Ein ungeschützter File-, SQLite- oder Browser-Storage-Fallback
existiert nicht. Windows-/macOS-Backends sind noch nicht implementiert.

Modell-Key, OIDC-Tokenpaar, lokale Sitzungskennung und Refresh-Journal liegen
ausschließlich in einem profilgebundenen Secret-Service-Eintrag. Jeder Write
wird geschützt zurückgelesen. Der Browser erhält nur einen kurzlebig nutzbaren
lokalen Bearer im Seitenspeicher über eine origin-/popup-/state-geprüfte
`postMessage`-Antwort. Keine Anwendungs-Cookies, LocalStorage oder SessionStorage;
keine Tokens oder Codes in URL, Zugriffsausgabe, Git oder Gesprächs-SQLite.
Das Schließen/Neuladen der Seite verwirft den Browser-Bearer. Erneute lokale
Verbindung erfolgt über den vorhandenen Anbieter-SSO-Pfad; sie ist kein
Versprechen eines promptfreien Browser-Neustarts. Die geschützten Serverdaten
bleiben beim Prozessneustart erhalten; ihre Verwendung erfordert zunächst
eine aktuelle Token-Erneuerung. Eine lokale Anmeldung endet spätestens nach
zwölf Stunden und kann durch erneute OIDC-Anmeldung ersetzt werden.

Vor jedem Refresh wird `REFRESH_PENDING` geschützt geschrieben. Nach erfolgreicher
Antwort muss ein neues Refresh-Token vorliegen; es wird mit Readback gespeichert.
Ein Timeout/Absturz nach möglicher Rotation bleibt pending und wird nicht
automatisch mit dem alten Token wiederholt. Ein eindeutiger Authentifizierungs-
fehler verlangt Wiederanmeldung. Die anbieterseitige Rotation/Replay-Erkennung
muss zur registrierten Public-Client-Konfiguration gehören; eine geänderte
Tokenzeichenfolge attestiert diese Servereigenschaft nicht unabhängig.

Abmelden entwertet zuerst den lokalen Bearer. Ist ein RFC7009-Endpunkt ausdrücklich
konfiguriert und per Discovery gebunden, werden Refresh- und Access-Token einzeln
widerrufen. Ein Endpoint-ACK ist keine unabhängige Token-Reuse-Prüfung und beendet
nicht automatisch die globale Anbieter-Sitzung. Ohne unterstützten Endpunkt
meldet der Client den externen Widerruf als `UNSUPPORTED`. Bei unbekanntem
Ergebnis bleiben die Geheimnisse ausschließlich im geschützten Pending-Journal;
keine Wiederholung. Reconciliation muss über die autorisierte Anbieter-
Sitzungsverwaltung erfolgen, bevor dieses Profil weiterverwendet wird.

### Native Einrichtung

Die optionalen Abhängigkeiten stehen in
`runtime/toolchains/requirements-personal-auth-50.0.2.txt`; der neue Cache-Vertrag
beinhaltet Version, Herkunft, Ausfallgrenze und Tests. Die Datei ist kein
heruntergeladener Wheel-Nachweis. Eine isolierte Personal-Umgebung wird separat
bereitgestellt; installierte Versionen werden niemals zurückgestuft.

Eine private Datei außerhalb jedes Git-Projekts, Modus 0600, bindet den bereits
autorisierten registrierten Public Client. Diese Vorlage enthält Platzhalter
und wird unverändert absichtlich abgelehnt:

```json
{
  "issuer": "https://<registered-issuer>",
  "client_id": "<registered-public-client-id>",
  "subject": "<verified-owner-subject>",
  "authorization_endpoint": "https://<registered-issuer>/authorize",
  "token_endpoint": "https://<registered-issuer>/token",
  "jwks_uri": "https://<registered-issuer>/keys",
  "revocation_endpoint": "https://<registered-issuer>/revoke",
  "redirect_uri": "http://127.0.0.1:8771/personal/auth/callback",
  "refresh_protection": "rotation"
}
```

Ein Anbieter ohne RFC7009 darf `revocation_endpoint` auslassen; der Client darf
dann keinen erfolgreichen Anbieter-Widerruf behaupten. Ein optionaler
`end_session_endpoint` wird ebenfalls genau gebunden. Keine Client-Secrets in
dieser Konfigurationsdatei; dieser Pfad ist ausschließlich ein Public Client.
Keine OAuth-Client-ID eines anderen Produkts wiederverwenden.

Den separat autorisierten Modell-Key einmal im eigenen Terminal verdeckt in
den OS-Speicher eingeben; er steht weder in Argumenten noch in Ausgabe/Umgebung:

```bash
python3 -B src/qikvrt_effect_ack_http_terminal.py \
  --personal-state-dir /private/runtime/qikvrt-personal \
  --personal-auth-config /private/runtime/registered-oidc.json \
  --personal-store-model-credential

python3 -B src/qikvrt_effect_ack_http_terminal.py \
  --personal-state-dir /private/runtime/qikvrt-personal \
  --personal-auth-config /private/runtime/registered-oidc.json \
  --personal-model <explicit-model-id>
```

Danach in Firefox `http://127.0.0.1:8771/personal/` öffnen und beim gebundenen
Identitätsanbieter anmelden. Der Token-POST erfolgt serverseitig; es gibt keine
Eingabe persönlicher Anbieterpasswörter in die lokale Oberfläche.

### Getrennte Nachweise

`make personal-firefox-boundary-test` führt die bestehenden Tests und den neuen
Lifecycle-Vertrag aus. Der neue Vertrag simuliert IdP und OS-Speicher, einschließlich
echtem Prozessabbruch/-neustart mit ausschließlich erfundenen temporären
Fixturewerten. Separate Tests führen echte RSA-Signatur-/Negativkontrollen mit
dem optionalen cryptography-Runtime durch. Ist dieser Runtime nicht vorhanden,
werden diese gesondert markiert übersprungen; das ist keine Signaturabnahme.
Es sind keine Nutzeranmeldungen, keine native Secret-Service-Persistenzabnahme
und keine realen Firefox-Produkttests. `authenticated_runtime_readback` bleibt
separat an eine tatsächliche Modellantwort gebunden. Das Capability-Manifest
bewahrt die offenen Produktgrenzen.

Primärquellen:

- https://openid.net/specs/openid-connect-core-1_0.html
- https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html
- https://www.rfc-editor.org/rfc/rfc7636
- https://www.rfc-editor.org/rfc/rfc8252
- https://www.rfc-editor.org/rfc/rfc9700
- https://www.rfc-editor.org/rfc/rfc7009
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc
- https://gnome.pages.gitlab.gnome.org/libsecret/
- https://cryptography.io/en/50.0.2/installation/

## Optionaler Argon-Prüfkandidat vom 14.10.2026

Der vorhandene Server unterstützt nun zusätzlich die explizite Auswahl
`--personal-provider gemini --personal-model gemini-4-argon`. Standard bleibt
OpenAI. Gemini verwendet `GEMINI_API_KEY` aus der autorisierten Prozessumgebung,
dieselbe lokale Client-Authentifizierung und ein getrenntes privates
State-Verzeichnis. Ein bestehendes OpenAI-State-Verzeichnis wird wegen der
abweichenden Providerbindung abgelehnt.

Die Interactions-Anfragen sind auf Text, `store=false`, `background=false`,
`thinking_level=low` und 4096 Output-/Thinking-Tokens begrenzt. Der vollständige
lokale Verlauf wird als gekennzeichnete Gesprächsdaten erneut mitgesendet;
es werden keine gespeicherten Google-Interaktionen oder Tools verwendet.
Provider-Sicherheitslogs können trotz `store=false` bestehen. Die bisherige
OpenAI-Baseline und ihre Provider-Conversations bleiben unverändert.
Vergleiche zwischen den beiden Providern sind durch diese Tests nicht belegt.

Technische Prüfung: `python3 -B -m unittest discover -s tests -p 'test_qikvrt_gemini_adapter.py' -v`.
Transport-Doubles sind keine authentifizierten Argon-Antworten. Live-Nutzung
setzt einen für den Zweck zulässigen Paid-Service-Zugang, sicher bereitgestellte
Credentials und den in `ARGON_REVIEW.md` beschriebenen Rechtecheck voraus.
Dieser ältere Argon-Kandidat implementiert kein Browser-Autonomietool;
der neue getrennte OIDC-Pfad ist oben beschrieben.

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

## Bisheriger Memory-Pfad für ausdrückliche Entwicklungstests

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
  --personal-legacy-memory-pairing \
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
