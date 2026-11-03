# QIK-VRT RealEnergy: geprüfter Forschungs- und Verbraucherkandidat

Stand: 03.11.2026. Auftrag: Ingolf Lohmann, bestehender Arbeitsring de5f082b. Ausarbeitung und Prüfung: OpenAI Codex.

## Ergebnis

Das separate Lake-Paket ist tatsächlich gelockt und gebaut. Acht ursprüngliche Sätze über reelle Energiegrößen wurden erneut kernelgeprüft; acht zusätzliche Aussage-/Beweis-Bindungen und beide vollständigen Axiomaudits wurden geprüft. Vier falsche mathematische Aussagen wurden verworfen. Drei Prüferselbsttests unterscheiden gültige Quellen von veränderten Quellen und einem fehlenden Compiler. Das ursprüngliche Std-only-Paket bleibt unverändert.

Die Fachfassung hat sieben, die Prosafassung fünf Seiten. Beide enthalten den neuen formalen Nachweis und den zeitlichen Geltungsbereich. Alle zwölf Seiten wurden visuell geprüft; je neun Quellen bzw. Nachweise sind bytegleich eingebettet. Die bestehende FLRW-Rechnung mit 48 Kontrollen, Quellcode und ursprünglichen Rohlogs ist erhalten.

## Lesen und ausführen

1. `docs/publications/2026-11-03-energy-cosmology-model-test/README.md`
2. Fachartikel/PDF, Prosa/PDF und `CLAIM_MATRIX.json` im selben Verzeichnis
3. `formalization/QIKVRT_RealEnergy_v1/README.md`
4. `formalization/QIKVRT_RealEnergy_v1/verification/acceptance-001/RECEIPT.json`
5. `evidence/real-energy-20261103/` und `CHANGE_NOTICE.md`

Das eigene Paket rekonstruiert mathlib aus dem unveränderten, hashgebundenen Originalarchiv. Der vollständige Original-Dateibaum und die acht transitiven Git-Revisionen sind gebunden. `vendor/` und `.lake/` werden rekonstruiert und nicht als Quellenpayload verteilt. Die Bootstrap-Prüfung lief sowohl mit vorhandenem Quellbaum als auch in einem frischen Verzeichnis erfolgreich.

Der bestehende Manuskript-Workflow enthält den additiven Verbraucher. Native Läufe 41616011235 (Head 7a67d924) und 41616823386 (Head c71f0699) waren erfolgreich; der zweite emittierte zusätzlich den vollständigen Originalprüferbeleg in sein Joblog. Acht ursprüngliche Sätze und acht gesonderte Aussagebindungen wurden dort geprüft, vier falsche Aussagen verworfen. Das unveränderte Prüferfeld `native_CI=NOT_EXECUTED` beschreibt den lokalen Prüfer selbst; die zusätzliche Publikationsbindung dokumentiert den unabhängig zurückgelesenen erfolgreichen nativen Lauf. Keine ZIP-Artefakt-Bytegleichheit wird aus der Rekonstruktion des JSON-Standardausgabestroms abgeleitet.

PR679 integriert den Forschungszweig. Der Konflikt mit Main b1952c6c wurde durch einen Commit mit beiden geordneten Eltern gelöst. Vollständige CI und Review bleiben gesonderte Voraussetzungen. Ein separater Review-Automat erhielt HTTP403; dieses Ergebnis wird nicht als fachliche Ablehnung oder fehlende Owner-Freigabe umgedeutet.

Das neue Quellenarchiv und der v2-Publikationsumschlag liegen unter `source_archive/`. Der originale v2-Prüfer bestätigt elf Aussagen, dreizehn Belegartefakte und den geschlossenen Satz von sechzehn Upload-Dateien. Der Quellenkandidat wurde mit exakten Downloadlinks an den Owner zurückgegeben. Die allgemeine Publikationsfreigabe ist erhalten; für diesen neu zurückgegebenen Archivkandidaten ist noch kein späteres kanonisches Upload-Ereignis verzeichnet. Der Publisher wurde lokal bis zu genau diesem fehlenden Ereignis geprüft und führte keine Produktionsmutation aus.

## Offen

Vollständige CI, unabhängige Checker, Review-/Main-Aufnahme, die spätere bytegebundene Archivfreigabe und die tatsächliche Veröffentlichung sind offen. Der ursprüngliche Quellenprüfer wurde unverändert aus der vorhandenen Versionshistorie zurückgewonnen und ausgeführt. Die vier externen Quellen bestehen die Prüfung in allen fünf Text-/PDF-Formaten. Das vollständige Gate bleibt bis zur eigenen öffentlichen Quellenarchivierung auf FAIL; dies wird nicht durch einen Teil-PASS ersetzt.

Die Originalhost-/SSO-Bindung ist hier nicht verfügbar. Der registrierte Originaldienst unter 127.0.0.1:8766 ist aus diesem Ausführungscontainer nicht erreichbar; daraus wird kein Fehlen geschützter Eingaben beim entfernten Dienst abgeleitet. Eine frische, unabhängig bytegeprüfte Beobachtung von raumzeitterminal.de liefert HTTP 525. Installation, Neustart/Persistenz, HTTPS und produktiver EAP-Effekt werden nicht behauptet. Alle früheren Publisher-/Quota-, Mirror-, R2- und November-2-Archivpflichten bleiben erhalten.

`EFFECT_ACK_DONE` ist unbestätigt. Dieses Paket schließt den konkret beschriebenen lokalen Verbrauchernachweis und die neue Entwurfsfassung, nicht die vollständige Produktivierung oder wissenschaftliche Veröffentlichung.

## Integrität

`BUNDLE_MANIFEST.json` bindet den scoped Payload. Die globalen drei Integritätsausgaben und die beiden scoped Integritätsdateien selbst sind zur Vermeidung von Selbstreferenzen aus diesem Payloadmanifest ausgeschlossen. `REPOSITORY_FILE_MANIFEST.json`, dessen abgesetzter SHA-256 und `SHA256SUMS.txt` werden aus der exakt gelesenen unveränderten Basis und den tatsächlichen Kandidatenbytes inkrementell materialisiert. Das ist keine Behauptung eines vollständigen lokalen Main-Testlaufs.

`python3 package_completion.py` erstellt das reproduzierbare ZIP außerhalb dieses Verzeichnisses. Die ursprünglichen hochgeladenen ZIP-Bytes sind unter den Belegen erhalten. Code- und Textlizenzen, Ursprungszuordnung und die eigenen Lizenzen aller Drittkomponenten bleiben bestehen.
