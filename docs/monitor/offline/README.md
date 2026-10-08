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

## Automatische Clientaktualisierung

Der vorhandene Service Worker prüft neue Produktionsdateien vollständig mit
SHA-256 und liest den fertigen separaten Versionscache zurück. Erst danach ist
die Version installierbar. Auch Änderungen ausschließlich am Worker bekommen
einen eigenen Versionscache. Ein unvollständiger Download, Netzabbruch oder
Prüfsummenfehler verwirft den Kandidaten; der aktive Worker und die bisherigen
Caches bleiben erhalten. Die HTTPS-Publikation des Workers ist die
Vertrauensautorität: Diese Inhaltsprüfung ist keine unabhängige Signatur gegen
einen kompromittierten Origin.

Der Client prüft bei Start, Online-Ereignis, Wiederanzeigen/Fokus und Rückkehr
in den Vordergrund automatisch auf Updates (`updateViaCache: 'none'`).
Wiederholte Vordergrundereignisse werden 30 Sekunden lang zusammengefasst;
eine Netzrückkehr löst eine neue Prüfung aus. Es gibt keinen Hintergrundtimer
und keine automatische GitHub-Repository-Beobachtung.

Ein installierter Update-Worker verlangt von **allen** geöffneten Clients einen
zurückgelesenen IndexedDB-Checkpoint. Laufende Speichern-/Import-/Export-/Teilen-
Vorgänge, eine IME-Komposition und die erste Sekunde nach einer Texteingabe
schieben die Übergabe auf. Während der kurzen Übergabe sind neue Änderungen
gesperrt. `skipWaiting()` und `clients.claim()` wechseln anschließend den
vollständigen Client; sichtbare Fenster laden automatisch neu, Hintergrundfenster
bei ihrer nächsten Anzeige. Der Entwurf mit Pfad, Text, Suche, Konfliktentscheidungen,
vorbereitetem Export sowie Fokus und Textauswahl wird wiederhergestellt. Ein
Entwurf wird dadurch **nicht** als neue Repository-Revision gespeichert. Die
vorhandene IndexedDB-Datenbank, Arbeitsstände und lokale Historie bleiben erhalten.
Entwürfe werden nach einer Eingabepause auch ohne Update lokal gesichert;
mehrere Tabs haben eigene Checkpoints. Hintergrund-Sicherungen ändern den
Vordergrund-Verweis nicht. Nach einem kalten Start ohne Tab-Kennung wird der
zuletzt im Vordergrund gesicherte Entwurf wiederhergestellt.

Ein offener Altclient aus #484 besitzt diese Übergabe noch nicht. Der neue Worker
überspringt dessen fehlendes Checkpoint-Acknowledgement nicht: Die erste Übernahme
erfolgt automatisch nach dem Schließen seiner Fenster und dem nächsten Öffnen.
Ungespeicherter RAM-Inhalt eines bereits ausgelieferten Altclients kann nicht
nachträglich durch einen Service Worker gesichert werden. Sein geprüftes
`ad47e6386536abdca5d5ba025832b27718ee66dd` bleibt als eigenständiger PR erhalten.

**Mobile Grenze:** Eine vollständig geschlossene oder vom Betriebssystem
suspendierte App führt diese Vordergrundlogik nicht aus. Eine Aktualisierung
während dieser Zeit oder zu einer garantierten Uhrzeit wird nicht zugesagt.
Beim nächsten geeigneten Online-Öffnen bzw. Fortsetzen erfolgen Prüfung und
Übernahme automatisch. Browser-Quota, Eviktion und ein Abbruch vor abgeschlossenem
IndexedDB-Checkpoint bleiben Systemgrenzen; der letzte bestätigte Stand bleibt
die Recovery-Basis. Desktop-Chromium und Desktop-WebKit attestieren kein echtes
iPhone und keinen öffentlichen Produktionsorigin.

`browser.test.mjs` veröffentlicht vier vom bestehenden Produktionsbuilder
gebaute Versionen nacheinander unter **demselben** Origin. Ohne einen Update-
Knopf, `registration.update()` oder `skipWaiting()` aus dem Test werden die
Online-Ereignishandler ausgeübt. Echte HTTP-Verbindungsabbrüche und manipulierte
Assetbytes müssen die Installation verweigern. Die Tests prüfen die automatische
Übernahme, zwei unabhängige ungespeicherte Entwürfe, einen laufenden Schreibvorgang,
sämtliche aktiv ausgelieferten Asset-Digests, Textauswahl, unveränderte Historie,
Wiederherstellung nach Fehler, kalten Prozessneustart und anschließende Offline-
Navigation. Die Online-Ereignisse sind DOM-Lifecycle-Kontrollen; es wird kein
physischer Mobilfunk-/Flugmoduswechsel behauptet.

Primärquellen für Lifecycle und Ausführungsgrenzen:

- https://www.w3.org/TR/service-workers/
- https://webkit.org/blog/8090/workers-at-your-service/
- https://webkit.org/blog/14403/updates-to-storage-policy/
