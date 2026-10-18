# QIK-VRT Homepage: versionierte Quellen und Hosting

Die deutsche Gedicht-Startseite liegt in `docs/index.html`. Die Quellen stammen
aus der bereits veröffentlichten Site-Version 37 (Quellcommit
`706fa071dee5d300c5aeca8565d40f3936ef232d`). Diese Integration veröffentlicht
oder verändert die bestehende ChatGPT-Site nicht.

| Bestandteil | Repository-Pfad |
| --- | --- |
| Deutsche Startseite | `docs/index.html` |
| Französisches Original und 57 Übersetzungen | `docs/sprachen.html` |
| Unveränderte Originalsammlung zum Download | `docs/texte/La_mere_bien_sur_57_Uebersetzungen.html` |
| Unveränderte Originalgrafik | `docs/assets/images/la-mere-bien-sur.png` |
| Deutsche Textfassung | `docs/texte/la-mere-deutsch.txt` |
| Bisherige Projektseite mit Konsole und Timeline | `docs/projekt.html` |
| Quellenvergleich, Originalnamen, Größen und SHA-256 | `state/work_units/QIKVRT_POETIC_HOMEPAGE_SOURCE_20261018_V1.json` |
| Unveränderter früherer Veröffentlichungsbeleg | `state/work_units/sources/Raumzeitterminal_Startseite_20261018.json` |

Die Gedichttexte bleiben unverändert. Relative lokale Startseitenlinks erlauben
statisches Hosting von `docs/` am Origin-Root oder unter einem Pfadpräfix. Die
vorhandenen Terminal-, Redaktions- und Publikationsseiten bleiben erhalten.
Die frühere Konsole arbeitet weiterhin lokal und verarbeitet keine API-Tokens.
Die Übersetzungsseite ergänzt nur den Rückweg zur Startseite.

Der Offline-Link verwendet den vorhandenen Client `monitor/offline/` mitsamt
seinem unveränderten Service Worker. Software-Downloads bleiben explizit unter
https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/release/index.html
verlinkt: Die dortigen großen Archivteile und deren serverseitige Prüf-API
werden nicht als Teil dieser Startseite dupliziert oder als unabhängig gehostet
behauptet. Der KI-Einstieg verweist auf das Authority-Repository.

## Unabhängiges Self-Hosting

Der vorhandene S1-Weg in `runtime/self-host/README.md` bleibt maßgeblich.
`runtime/self-host/PACKAGE.json` nimmt die Homepage und ihre öffentlichen
Abhängigkeiten in das vorhandene versiegelte Paket auf. `tools/qikvrt_self_host.py
pack` exportiert ausschließlich den exakten sauberen Commit; `verify` prüft die
Paketbytes. Der bestehende Node-Server liefert `/`, `/sprachen.html`,
`/projekt.html`, `/news/`, `/publications/`, `/monitor/`, `/terminal/` und den
Offline-Client aus demselben Paket aus. `/mesh`, `/node`, `/client` und die
bestehenden Runtime-, Ledger- und Monitor-APIs behalten ihre Funktion.
Veröffentlichungsdateien bleiben unter der bestehenden begrenzten
Publikationsfreigabe; interne Autorisierungen werden nicht öffentlich ausgeliefert.

Die Sammlung benötigt kein JavaScript. Für ihre vorhandenen eingebetteten
Stile verwendet der S1-Server inhaltsgebundene CSP-Hashes. Die bisherigen
Sicherheitsgrenzen werden nicht durch `unsafe-inline` ersetzt.

Prüfung: `make editorial-navigation-test repository-terminal-test` sowie
`python3 -B -m unittest tests.test_self_host.StandaloneTests` im deklarierten
Node-24/Python-3.12-S1-Runtimeprofil. Die Tests prüfen Originalhashes, alle 58
Sprachabschnitte, deutsche Textgleichheit, Rückwege und echte exportierte
HTTP-Antworten einschließlich GET/HEAD, Bildbytes, Offline-Dateien und CSP.
Lokale Prüfungen sind keine öffentliche Domain-Abnahme.

## GitHub Pages und Auslieferungsgrenze

Authority: `ingolf-lohmann/qik-vrt`; Branch `main`; statischer Ordner `docs/`.
Die Pages-/Reverse-Proxy-/DNS-Konfiguration ist eine getrennte Hostingaktion.
Statisches Hosting stellt Dokumente bereit; die vorhandenen Monitor- und
Terminal-APIs benötigen die dokumentierte Runtime. Die Quellensicherung allein
belegt weder native Produktausführung noch DNS/TLS oder erfolgreiche
Auslieferung über https://raumzeitterminal.de/.
