# QIK-VRT auf beiden iPhones offline verwenden

Dieser statische React-Client bewahrt eine vollständige Git-Arbeitsbaum-Replik,
Dateiversionen und gespeicherte Monitor-Beobachtungen im privaten Browser-Speicher.
Die Produktion benötigt keinen CDN, Server-Speicher, Token oder Scheduler.
GitHub wird nur nach ausdrücklichem Klick lesend beobachtet. Offline-Beobachtungen
behalten ihren Zeitpunkt; sie werden nie als frischer Live-Status ausgegeben.

## Einrichtung

1. Den bereitgestellten HTTPS-Einstieg auf jedem iPhone in Safari öffnen.
2. **Teilen → Zum Home-Bildschirm → Als Web-App öffnen** verwenden.
3. Die installierte App öffnen. Den vollständigen `repository.qikvrt.gz`-Stand
   aus dem zu diesem HEAD gehörenden CI-Transferpaket in **Dateien** sichern und
   dort mit **Repository-Stand … übernehmen** importieren.
4. **Client vollständig im Offline-Cache geprüft** abwarten. Im Flugmodus
   öffnen, eine Datei bearbeiten, speichern, schließen und erneut öffnen.
5. **Sicherung vorbereiten** und danach **Fertigen Stand teilen** verwenden.
   Die getrennten Schritte erhalten die für iOS erforderliche Benutzeraktion
   beim Öffnen der Teilen-Ansicht. In **Dateien** sichern oder per AirDrop auf
   das andere iPhone übertragen; dort in der installierten App importieren.

Safari und die installierte Home-Screen-App teilen ihren lokalen Speicher nicht
automatisch. Der Import gehört deshalb in die App, in der später gearbeitet wird.
Eine heruntergeladene HTML-Datei in der Dateien-Vorschau installiert keine PWA.
Die erste Einrichtung benötigt einen sicheren HTTPS-Origin. Änderungen danach
funktionieren lokal ohne Netz. Exportdateien enthalten persönliche Arbeitsdateien;
sie werden ausschließlich durch die gewählte Datei-/Teilen-Aktion übertragen.

## Persistenz und Übertragung

- Inhaltsblöcke sind auf 1 MiB begrenzt und werden mit SHA-256 geprüft.
- Zusätzlich werden die tatsächlichen Git-Blob- und Git-Tree-SHA-1-Werte
  berechnet. SHA-1 dient der Git-Kompatibilität, nicht als Signatur.
- Sichtbare Versionswechsel erfolgen erst nach Inhaltsprüfung in einer
  atomaren IndexedDB-Transaktion mit gebundenem vorherigem HEAD und anschließendem
  Readback. Gleichzeitige Tabs können keinen unbemerkten Stand überschreiben.
- Ein Export enthält den aktuellen Arbeitsbaum und seine gesamte lokale
  Versionshistorie. Komplette Quellpakete enthalten alle versionierten Dateien,
  Modi, Symlink-Bytes und ihre Git-Objektbindungen, einschließlich Binärdateien.
  Die native `.git`-Datenbank und ihre gesamte frühere Commit-Historie sind
  nicht Teil dieser Arbeitskopie. Dateien werden lokal nicht ausgeführt.
- Beschädigte, unvollständige oder repository-fremde Importe wechseln den HEAD
  nicht. Ein gültiger Parallelstand wird getrennt bewahrt; echte Konflikte
  verlangen eine bewusste Dateientscheidung. Die Zusammenführung hat zwei
  Eltern und lässt sich vollständig zurück auf das andere Gerät übertragen.
- Ein abgebrochener Import kann unreferenzierte Inhaltsblöcke hinterlassen,
  aber keinen teilweise bestätigten Arbeitsbaum. Browser-Quota-Fehler bleiben
  sichtbar. Der tatsächliche Datenträger-FSYNC oder eine dauerhafte iOS-Speicher-
  Zusage wird nicht behauptet: Browser-/Systempolitik kann Daten eviktieren.
  Wichtige Arbeitsstände zusätzlich als Datei sichern.

Die Limits sind 2 GiB Inhalt, 1 MiB je Block, 10.000 lokale Revisionen und
1,5 MB je Archiv-Metadatenrecord; der Dateiinventar-Record ist ebenfalls begrenzt.
Der aktuelle vollständige Repository-Stand benötigt rund 400 MB unkomprimierten
Inhalt. Die Metadaten-, Browser-Speicher- und Dateiexportgrenzen bleiben wirksam.
Textbearbeitung ist auf 2 MiB je Textdatei begrenzt; Binärdateien können gespeichert,
geprüft und vollständig exportiert werden.

## Bauen und prüfen

```sh
python3 -B tools/qikvrt_offline_repository.py shell
make offline-repository-test
python3 -B tools/qikvrt_offline_repository.py pack --ref HEAD --output /tmp/repository.qikvrt.gz
node docs/monitor/offline/static-server.mjs
```

Für die Browserprüfung das integritätsgebundene Playwright-Testpaket unter
`runtime/offline/browser-tests` mit `npm ci` installieren; der native Workflow
prüft Chromium und WebKit gegen denselben eingefrorenen HEAD/TREE. Er prüft
wirkliches IndexedDB, Neuladen bei abgeschaltetem Origin, einen fehlschlagenden
ungecachten Abruf als Negativkontrolle, Browser-Prozessneustart, getrennte Origins,
binäre Mehrblock-Dateien, zwei Geräte-Branches, Konfliktentscheidung, Rücktransfer,
Manipulation, Abbruch und den konkurrierenden Writer. Außerdem importiert jeder
Browser den vollständigen nativen gzip-Transfer als tatsächliche Browser-Datei
und prüft sämtliche Inhaltsbytes gegen den eingefrorenen Git-Arbeitsbaum. Mobile Desktop-Emulation
und Desktop-WebKit sind **keine** Abnahme auf den zwei tatsächlichen iPhones.

Die native CI erzeugt zusätzlich das vollständige Übertragungspaket und dessen
unabhängig kopierbare SHA-256-/HEAD-/TREE-Quellenbindung. Frühere Ergebnisse
werden nicht übernommen. Eine spätere HEAD-Änderung braucht frische Prüfung.

## Geltung

Dieses Element ist eine offline bearbeitbare Repository-Arbeitskopie. Der native
SQLite-Monolith, seine Ausführung und Governance bleiben eigenständige,
unveränderte Verträge. Lokale Revisionen sind keine GitHub-Commits, Freigaben,
Deployments oder Main-Merges; externe Effekte werden weder simuliert noch
automatisch aus Offline-Notizen abgeleitet. Die aktuelle menschliche Authority
ist Ingolf Lohmann, Product Owner und Code Owner; Repository und ausführende
QIK-VRT-Instanz ersetzen keine unabhängige native Freigabe.

Primärquellen für den iPhone-Einstieg und die Speichergrenzen:

- https://support.apple.com/guide/iphone/open-as-web-app-iphea86e5236/ios
- https://webkit.org/blog/14403/updates-to-storage-policy/
- https://webkit.org/blog/14787/webkit-features-in-safari-17-2/
- https://webkit.org/blog/17333/webkit-features-in-safari-26-0/

React-Laufzeit: bytegleich wiederverwendet aus
`ingolf-lohmann/qik-vrt@53040b450853b0ab5a3d59765b86030b3bd0c978`,
`docs/monitor/react-runtime.js` und `REACT_LICENSE.txt`, React 19.2.6 / Scheduler
0.27.0, MIT. Implementierungsbeitrag: OpenAI Codex; Anforderungen und Freigabe:
Ingolf Lohmann. Projektnutzung gemäß der geltenden Repository-Lizenz.

Die WebKit-Offline-Emulation `setOffline(true)` scheiterte im ersten nativen Lauf
vor der Cache-Navigation mit „WebKit encountered an internal error“. Der frische
Nachweis schaltet daher den tatsächlichen Origin-Server ab; Chromium erhält
zusätzlich das Offline-Flag. Dies belegt ausfallfestes lokales Arbeiten, keine
physische iPhone-Flugmodus-Abnahme. Browser-`navigator.onLine` ist nur ein Hinweis.
Upstream-Diagnose: https://github.com/microsoft/playwright/issues/42775

## Statisches Client-Paket und HTTPS-Hosting

Das native Transfer-Artefakt enthält zusätzlich `offline-client.zip` mit allen
Produktionsdateien, MIT-Lizenz, Startskript und `SOURCE.json`. Die Datei benennt
den unveränderlichen Quell-HEAD/TREE und die SHA-256-Werte der einzelnen Bytes.
Entpackt kann es mit Node 24 über `node static-server.mjs` lokal verwendet oder
als rein statischer Inhalt über einen eigenen HTTPS-Origin bereitgestellt werden.
Das ZIP allein installiert in der iPhone-Dateien-Vorschau keine Offline-App.

Die Bereitstellung über die verbundenen Hostingwege ist aktuell blockiert:
Railway meldet einen abgelaufenen Trial; Vercel verweigert den Zugriff auf den
vorhandenen Ingolf-Workspace mit HTTP 403. GitHub Pages ist nicht aktiviert.
Diese technischen Hostingzustände ändern weder Ingolf Lohmanns Freigabe noch
die aktuelle Mesh Authority. Ein bereits funktionierender HTTPS-Einstieg wird
erst nach erfolgreichem Deployment und Byte-Readback benannt.

## Automatische sichere Client-Aktualisierung

Der bestehende Worker bleibt unter derselben URL und demselben HTTPS-Scope
registriert (`updateViaCache: none`). Der Client prüft beim Start, bei `online`,
`focus`, `pageshow` und Rückkehr in die sichtbare App sowie alle fünf Minuten
während sichtbarer, als online gemeldeter Sitzungen. Gleichzeitige Prüfungen
werden zusammengefasst; Ereignisse haben 30 Sekunden Mindestabstand. Fehler
verlängern die Wiederaufnahmefrist auf höchstens fünf Minuten. Erreichbarkeit
wird durch den Abruf geprüft, nicht aus `navigator.onLine` abgeleitet. Diese
Prüfung aktualisiert nur Clientcode; sie beobachtet GitHub nicht und überträgt
keine persönlichen Dateien.

Ein Release ist der SHA-256-gebundene Asset-Satz aus dem vorhandenen Builder.
Alle Dateien werden ohne HTTP-Cache und ohne Redirect geladen, vollständig
geprüft, gespeichert und erneut gelesen. Erst danach wird die Installation
abgeschlossen. Ein Completion-Record ist an den SHA-256 des kanonischen
Asset-Manifests gebunden. Hashes prüfen Integrität und Versionszugehörigkeit;
sie sind keine Herausgebersignatur. Die Vertrauenswurzel bleibt der HTTPS-Origin.

`skipWaiting()` wird erst nach einer Vorbereitung aller erreichbaren offenen
Clients aufgerufen. Jeder Client sperrt neue Eingaben kurz, wartet auf einen
ruhenden Arbeitsraum, sichert Pfad, Text, Filter, Konfliktentscheidungen und
Editorposition getrennt von bestätigten Revisionen in einer strikten
IndexedDB-Transaktion und bestätigt den SHA-256-Readback. Beschäftigte,
fehlerhafte oder nicht antwortende Clients halten den Wechsel an. Ein zweiter
Client-Abgleich erfasst neu hinzugekommene Tabs. Abgebrochene Abstimmungen lösen
die Eingabesperre; ein Timeout schützt auch gegen einen beendeten Worker.

Nach `clients.claim()` prüft jeder Client den neuen Cache und seinen Entwurf
nochmals, navigiert automatisch zum stabilen Einstieg und stellt den Entwurf
wieder her. Auch ein unerwarteter Controllerwechsel lädt niemals einen
beschäftigten Arbeitsraum neu. Neue Dokumente übernehmen einen vorhandenen
Tab-Checkpoint und schreiben anschließend unter einer eigenen Identität;
auch kopierte `sessionStorage`-Werte führen nicht zu gemeinsam überschriebenen
Entwürfen. Geht eine Tab-Sitzungskennung bei einem Neustart verloren, sind ihre
verifizierten Sicherungen unter „Gesicherte Entwürfe“ weiterhin einzeln verfügbar.
Die Auswahl eines Parallelentwurfs überschreibt keine bestätigte Revision und
sichert den aktuell geöffneten Entwurf vor dem Wechsel. Checkpoints liegen unter eigenen `refs`-Schlüsseln im vorhandenen
Datenbankschema. Sie erzeugen keine Revision und ändern weder HEAD noch Historie.
Eine beschädigte Sicherung wird sichtbar angehalten, nicht stillschweigend als
leerer Entwurf ersetzt. Die gewöhnliche Entwurfsicherung hat 500 ms Verzögerung;
vor jedem automatischen Wechsel wird sie ausdrücklich vollständig bestätigt.

Die aus verifizierten HTML-Bytes abgeleiteten Script-/CSS-URLs enthalten die
Release-ID. Relative Modulimporte bleiben dadurch im selben Namespace.
Vorherige Caches bleiben für noch laufende oder spät fortgesetzte Dokumente
verfügbar; unbekannte oder beschädigte gebundene Assets ergeben HTTP 503 statt
Code aus einem anderen Release. Die erste ungeprüfte Netzwerkseite gibt die
Bearbeitung erst nach einer Navigation durch den geprüften Worker frei.
Beschädigte Staging-Caches werden nur durch erneuten vollständigen Abruf der
bekannten, digestgebundenen Bytes repariert. Ein Fehler ersetzt den gesunden
aktiven Worker nicht. Es gibt weder eine Datenbankmigration noch automatische
Löschung alter Revisionen oder Entwürfe.

### Plattformgrenzen, insbesondere iOS

| Fall | Automatisch möglich / Grenze |
| --- | --- |
| Bereits eingerichteter Client, aktive Online-Sitzung | Updateprüfung, Asset-Verifikation, sicherer Reload und Entwurfswiederherstellung brauchen keine weitere Benutzerfreigabe. |
| Alle kontrollierten Fenster geschlossen | Der Browser darf einen vollständig installierten wartenden Worker selbst aktivieren; der nächste Start verwendet die neue Version. |
| Lang laufende sichtbare Sitzung | Der Fünf-Minuten-Takt ist ein Vordergrund-Timer. Auslastung oder Browserdrosselung können ihn verzögern. |
| Suspendierte oder geschlossene iOS-App | Kein garantierter Timer, Download, Aktivierungszeitpunkt oder Weiterlauf. Worker sind ereignisgebunden und dürfen beendet werden. Bei Rückkehr wird erneut geprüft. |
| Periodic Background Sync / Push | Kein Bestandteil dieser Lösung. Selbst eine verfügbare API legt keinen verlässlichen, vom Entwickler garantierten Ausführungstakt fest. |
| Bereits laufender unveränderter Client aus PR #484 | Er kennt die neue Entwurfsabstimmung nicht. Der neue Worker bleibt wartend und erzwingt keinen Reload. Die sichere Erstübernahme erfolgt nach natürlichem Schließen der alten Clients und erneutem Öffnen. |
| Originwechsel, iOS-Safari versus Home-Screen-App | Speichergrenzen bleiben getrennt. Ein Codeupdate überträgt Arbeitsdaten nicht zwischen Origins oder Installationen. |
| Prozessabbruch, Speicher-Eviction, Geräte-/Browserdatenlöschung | Browserpolitik bleibt maßgeblich. Der kontrollierte Releasewechsel bestätigt Entwürfe vorab; beliebiger Absturz vor der normalen 500-ms-Sicherung und dauerhafte Aufbewahrung sind keine Garantie. Datei-Backups bleiben verfügbar. |

Die vorhandene Chromium-/WebKit-Prüfung wird um echte Wechsel zwischen vier
lokalen Release-Fixtures erweitert: sichtbarer Sitzungstakt, Online-/Focus-/
Pageshow-Ereignisse, Netzabbruch, beschädigte Assets und Staging-Caches,
unkooperative und parallele Clients, laufende UI-Schreiboperation,
IndexedDB-Sicherungsfehler, Wiederaufnahme, unveränderte bestätigte Historie,
getrennte Entwürfe und Browserprozess-Neustart bei abgeschaltetem Origin.
`update-readback.json` ist aktuelle Ausführungsevidenz; Test-Fixtures sind keine
veröffentlichten Releases und Desktop-WebKit attestiert kein physisches iPhone.

Primärquellen für die Update-/Hintergrundgrenzen (geprüft 2026-10-08):

- https://w3c.github.io/ServiceWorker/#service-worker-lifetime
- https://w3c.github.io/ServiceWorker/#service-worker-registration-update
- https://developer.chrome.com/docs/workbox/service-worker-lifecycle/
- https://developer.chrome.com/docs/capabilities/periodic-background-sync
- https://webkit.org/blog/14403/updates-to-storage-policy/
