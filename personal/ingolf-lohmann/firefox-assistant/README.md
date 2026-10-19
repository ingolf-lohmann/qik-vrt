<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Universales Raumzeit-Terminal

## Native SSO-Produktivprüfung, 19.10.2026

Der vorhandene Terminal-Einstieg kann eine bereits erteilte, geschützte
SSO-Sitzung jetzt unabhängig von Modell-Key und HTTP-Listener zurücklesen:

```bash
python3 -B src/qikvrt_effect_ack_http_terminal.py personal-auth-readback \
  --personal-state-dir /private/runtime/qikvrt-personal \
  --personal-auth-config /private/runtime/registered-oidc.json
```

Dies ist eine **aktive Token-Erneuerung** beim genau gebundenen Anbieter,
keine rein lokale Statusabfrage. Sie verwendet dieselbe private Konfiguration,
denselben OS Secret Service, dieselbe profilgebundene Schreibsperre und das
vorhandene Refresh-Pending-Journal. Ein laufender PersonalRuntime blockiert den
konkurrierenden CLI-Schreiber. Ausgegeben werden ausschließlich Status und
Nachweisgrenzen, keine lokalen Bearer, Access- oder Refresh-Tokens. Die
Wiederaufnahme verlängert die bestehende zwölfstündige Sitzungsgrenze nicht.
Bei ungeklärter Erneuerung gibt es keinen automatischen weiteren Versuch.
Die Operation startet keinen Passwortdialog und legt keine Ersatzablage an.

Der Aufruf ist für den zugelassenen nativen Desktop-Benutzer bestimmt. Es gibt
keinen unauthentifizierten HTTP-Endpunkt, der einen gespeicherten Bearer an
eine neu geöffnete Browserseite ausgibt. Der bestehende Firefox-Anmeldepfad und
seine Origin-/PKCE-/State-/Nonce-Prüfungen bleiben erhalten. Eine fremde
Cloud-Browser-Sitzung wird durch diese Funktion nicht angemeldet.

Produktivabnahme verlangt weiterhin die bestehende registrierte Public-Client-
und Owner-Subject-Bindung sowie einen tatsächlich verfügbaren, geschützten
OS-Speicher unter dem angemeldeten Benutzer. Ein Test mit simuliertem IdP oder
Speicher ist kein produktiver SSO-Nachweis. Die lokalen Unit-Tests prüfen
Neustart, Ablauf, Logout-/Pending-Zustände, konkurrierenden Schreiber,
verlorene Refresh-Antwort und geheimnisfreie Ausgabe.

Für die bereits autorisierte OneNote-Arbeit gilt zusätzlich: Der bestehende
Identity-Pfad fordert nur `openid offline_access` an. Das ist keine delegierte
Microsoft-Graph-Berechtigung für OneNote. Der genaue native Adapter benötigt
eine zum registrierten Client gehörende, autorisierte Notes-Berechtigung und
einen eigenen Seiten-Readback. Eine vorhandene Outlook-/OneDrive-Verbindung
liefert diesem Runtime keine exportierbaren Tokens. Der neue Readback fordert
keine zusätzlichen Scopes an und behauptet keinen OneNote-Effekt.

Primärquellen zur getrennten API-Berechtigung:

- https://learn.microsoft.com/en-us/graph/api/resources/onenote-api-overview?view=graph-rest-1.0
- https://learn.microsoft.com/en-us/graph/permissions-reference#notesreadwrite
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow

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
Microsoft wurde vom Owner als vorhandener Anbieter gewählt. Das additive Profil
`microsoft_public_v2` adaptiert den bestehenden Controller an den dokumentierten
Microsoft-v2-Public-Client-Vertrag. Eine konkrete registrierte
Client-/Issuer-/Subject-Bindung ist weiterhin nicht nachgewiesen. Niemand erhält
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
Antwort muss ein neues Refresh-Token vorliegen; es ersetzt den alten Wert im
geschützten Eintrag und wird mit Readback gespeichert.
Ein Timeout/Absturz nach möglicher Rotation bleibt pending und wird nicht
automatisch mit dem alten Token wiederholt. Ein eindeutiger Authentifizierungs-
fehler verlangt Wiederanmeldung. Das bisherige generische Profil verlangt
weiterhin `refresh_protection=rotation`; die zugehörige anbieterseitige
Replay-Erkennung muss separat nachgewiesen werden. Eine geänderte Zeichenfolge
attestiert diese Servereigenschaft nicht unabhängig.

Das explizite Microsoft-Profil verwendet `refresh_protection=microsoft_replacement`:
Microsoft ersetzt Refresh-Tokens, entwertet das alte Token dabei aber nicht
automatisch. Deshalb speichert der Client ausschließlich das aktuelle Token,
fordert beim Refresh wieder nur `openid offline_access` an und behauptet keine
serverseitige Replay-Erkennung. Das ist ein eigener, offen ausgewiesener
Providervertrag; die Anforderungen des generischen Profils werden nicht
umgedeutet. Schutz des nativen Secret Service ist hierfür eine notwendige
Betriebsbedingung. Ein Diebstahl eines noch gültigen Tokens lässt sich nicht
durch bloße Tokenersetzung heilen; dann ist Anbieter-Widerruf erforderlich.

Abmelden entwertet zuerst den lokalen Bearer. Ist ein RFC7009-Endpunkt ausdrücklich
konfiguriert und per Discovery gebunden, werden Refresh- und Access-Token einzeln
widerrufen. Ein Endpoint-ACK ist keine unabhängige Token-Reuse-Prüfung und beendet
nicht automatisch die globale Anbieter-Sitzung. Ohne unterstützten Endpunkt
meldet der Client den externen Widerruf als `UNSUPPORTED`. Bei unbekanntem
Ergebnis bleiben die Geheimnisse ausschließlich im geschützten Pending-Journal;
keine Wiederholung. Reconciliation muss über die autorisierte Anbieter-
Sitzungsverwaltung erfolgen, bevor dieses Profil weiterverwendet wird.

Microsofts Discovery weist keinen RFC7009-Endpunkt aus. Die lokale Abmeldung
entfernt die lokal verfügbaren Identitätstokens und meldet
`PROVIDER_SESSION_MANAGEMENT_REQUIRED`. Ein gesonderter Link öffnet nur nach
weiterem Klick den genau gebundenen Microsoft-End-Session-Endpunkt; dieser
Schritt ist kein Token-Widerruf. Die Oberfläche verwirft ihren lokalen Bearer
auch bei fehlendem Logout-ACK und löst keine automatische Wiederholung aus.
Microsoft Graph `revokeSignInSessions` betrifft mehrere Anwendungen, verlangt
gesonderte Berechtigungen und unterstützt delegierte private Microsoft-Konten
nicht. Der Client fordert diese Berechtigung nicht an und ruft Graph nicht auf.
Der tatsächliche externe Widerruf bleibt über die autorisierte Konto- oder
Tenant-Verwaltung nachzuweisen. Der Modell-API-Key bleibt für Wiederanmeldung
im OS-Speicher; IdP-Abmeldung widerruft keine gesonderte Modellberechtigung.

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

Für den bereits registrierten Microsoft-Public-Client wird stattdessen diese
ebenfalls absichtlich unvollständige Vorlage privat ausgefüllt. Die konkrete
Tenant-GUID und der für genau diese Application-ID verifizierte paarweise
Owner-Subject sind verbindlich; `common`, `organizations`, `consumers`,
Tenant-Wildcards und passende E-Mail-Adressen sind kein Ersatz:

```json
{
  "provider_profile": "microsoft_public_v2",
  "issuer": "https://login.microsoftonline.com/<tenant-guid>/v2.0",
  "client_id": "<existing-authorized-application-guid>",
  "subject": "<verified-owner-subject-for-this-application>",
  "authorization_endpoint": "https://login.microsoftonline.com/<tenant-guid>/oauth2/v2.0/authorize",
  "token_endpoint": "https://login.microsoftonline.com/<tenant-guid>/oauth2/v2.0/token",
  "jwks_uri": "https://login.microsoftonline.com/<tenant-guid>/discovery/v2.0/keys",
  "end_session_endpoint": "https://login.microsoftonline.com/<tenant-guid>/oauth2/v2.0/logout",
  "redirect_uri": "http://127.0.0.1:8771/personal/auth/callback",
  "refresh_protection": "microsoft_replacement"
}
```

Die feste Consumer-Tenant-GUID lautet nach Microsofts Dokumentation
`9188040d-6c67-4c5b-b112-36a304b66dad`; das ist keine Zuordnung dieses Owners
oder seiner Registrierung. Workforce-Konten benötigen ihren konkreten Tenant.
Die Registrierung muss den tatsächlich verwendeten Loopback-Callback für einen
nativen **öffentlichen Desktop-Client** erlauben. Ein vertraulicher Web-Client
oder ein SPA-Redirect wird nicht durch Weglassen eines Client-Secrets kompatibel.
HTTP-127.0.0.1-Redirects werden bei Microsoft über das App-Manifest registriert.
Der Client ändert keine Registrierung und übernimmt keine fremde Connector-App.

Microsofts öffentliche v2-Discovery listet S256 und die Public-Client-Methode
`none` derzeit nicht. Nur das ausdrücklich gewählte Microsoft-Profil darf diese
beiden fehlenden Angaben anhand des dokumentierten Providervertrags behandeln.
Es sendet immer S256 und kein Client-Secret; bei ausdrücklich widersprechender
PKCE-Metadatenangabe blockiert es. Issuer, Auth-/Token-/JWKS-/Logout-Endpunkte,
form_post, Code-Response und RS256 bleiben genau geprüft. Die signierten Claims
`tid` und `ver=2.0` werden zusätzlich geprüft. Der bisherige generische Pfad
und seine unveränderten Konfigurations-/Speicherbindungen bleiben kompatibel.
Ein Profilwechsel benötigt zuvor die Abmeldung/Reconciliation des alten
Profils; bestehende geschützte Daten werden nicht stillschweigend migriert.

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

Der bestehende Personal-Boundary-Workflow berücksichtigt jetzt auch Änderungen
am Auth-Modul, seinen Tests und dem optionalen Requirements-Vertrag. Er baut
eine frische isolierte Personal-Testumgebung mit den bereits gebundenen
Crypto-Versionen und führt `make personal-firefox-boundary-test` darin aus.
Damit sollen die echten RSA-Kontrollen dieses Jobs nicht wegen einer fehlenden
optionalen Abhängigkeit übersprungen werden. Zwei zusätzliche Node-Tests prüfen
lokales Tokenverwerfen bei erfolgreichem und verlorenem Logout-ACK sowie die
gesonderte Anbieter-Aktion; DOM und HTTP-Antworten sind dabei simuliert.
Ein erfolgreicher nativer CI-Lauf ist weiterhin keine Anmeldung eines Menschen.

Primärquellen:

- https://openid.net/specs/openid-connect-core-1_0.html
- https://openid.net/specs/oauth-v2-form-post-response-mode-1_0.html
- https://www.rfc-editor.org/rfc/rfc7636
- https://www.rfc-editor.org/rfc/rfc8252
- https://www.rfc-editor.org/rfc/rfc9700
- https://www.rfc-editor.org/rfc/rfc7009
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow
- https://learn.microsoft.com/en-us/entra/identity-platform/v2-protocols-oidc
- https://learn.microsoft.com/en-us/entra/identity-platform/refresh-tokens
- https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference
- https://learn.microsoft.com/en-us/entra/identity-platform/reply-url
- https://learn.microsoft.com/en-us/graph/api/user-revokesigninsessions?view=graph-rest-1.0
- https://login.microsoftonline.com/9188040d-6c67-4c5b-b112-36a304b66dad/v2.0/.well-known/openid-configuration
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
# Frische Bindung beim Übergang aus dem unabhängigen Firefox-Tab

„Personal öffnen“ navigiert ohne Daten oder Credentials nach `/personal/#terminal`.
Nach der bestehenden OIDC-Anmeldung aktiviert der Benutzer „Personal-Modus
aktivieren“. Der gleiche vorhandene Terminal-Prozess erneuert den gebundenen
SSO-Grant einmal, bereitet die genaue Quell-/Identitätsbindung vor und nimmt
einen einmaligen, 120 Sekunden gültigen EFFECT_ACK-Commit entgegen.
Der Original-Transputer schreibt ein begrenztes Ereignis; das Original-Terminal
prüft es über eine frische lesende SQLite-Verbindung. Die Oberfläche prüft
anschließend einen gesonderten authentifizierten GET und den Ereignishash.
„Übergang prüfen“ liest nach verlorener Antwort, ohne den Commit zu wiederholen.

Dieser Pfad nutzt das bereits vorhandene In-Process-API und denselben HTTP-
Listener. Er eröffnet keinen ungeschützten nativen HTTP-Writer. Native
Schreiberbindung, Originaljournal, Eigentümerrechte und exakte Quelle bleiben
verbindlich. Bei explizit aktiviertem nativen Pfad bleiben Gespräche und
Modellanfragen bis zur Bindung gesperrt. Der bisherige Entwicklungspfad kann
diesen Übergang nicht bestätigen.

Zum vorhandenen geschützten Start werden die bereits unterstützten Argumente
`--root`, `--repository`, `--pr`, `--expected-head`, `--expected-tree` und
`--state-dir` mit den tatsächlich zugelassenen Werten gesetzt. `--state-dir`
bezeichnet den originalen, zugelassenen lokalen TEMDD-Speicher; Kopien übertragen
keine Schreiberzulassung. Modellargumente und private SSO-Konfiguration bleiben
diejenigen des vorhandenen Personal-Starts. Fehlende oder veränderte Bindungen
halten geschlossen, ohne Token-Fallback oder neuen Dienst.

`EFFECT_ACK_DONE` dieses Pfads gilt ausschließlich für
`AUTHENTICATED_NATIVE_PERSONAL_BINDING_ONLY`. Produktives Microsoft-SSO,
dauerhafte signierte Firefox-Aktivierung, Modellbetrieb und öffentliche
Auslieferung benötigen jeweils eigene Nachweise. Die Regressionen nutzen
ausdrücklich simulierte Identitätsanbieter und Vaults, jedoch Original-
Transputer, Journal, Terminal und einen zusätzlichen Prozess für den Readback.
