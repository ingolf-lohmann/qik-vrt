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

Der bestehende Manuskript-Workflow wurde um einen additiven Verbraucher ergänzt. YAML und die neue Shellsequenz wurden geprüft. Dies ist ein Quellenkandidat, keine bereits ausgeführte native CI-Abnahme. Die Archivierung verwendet ausdrücklich `[skip ci]`, solange der im vorhandenen Arbeitsring dokumentierte Publisher-/Quota-Pfad noch eine sichere native Ausführung und Integration benötigt. Es wird kein neuer Workflow, Trigger, Scheduler oder Ersatzexecutor angelegt.

## Offen

Native Exact-HEAD-CI, unabhängige Checker, Review-/Main-Aufnahme, der originale zusätzliche Quellenprüfer, die kandidatengebundene Zenodo-Freigabe und tatsächliche Veröffentlichung sind offen. Der ursprüngliche Quellenprüfer wurde unverändert aus der vorhandenen Versionshistorie zurückgewonnen und ausgeführt. Die vier externen Quellen bestehen die Prüfung in allen fünf Text-/PDF-Formaten. Das vollständige Gate bleibt bis zur eigenen öffentlichen Quellenarchivierung auf FAIL; dies wird nicht durch einen Teil-PASS ersetzt.

Die Originalhost-/SSO-Bindung ist hier nicht verfügbar. Der registrierte Originaldienst unter 127.0.0.1:8766 ist aus diesem Ausführungscontainer nicht erreichbar; daraus wird kein Fehlen geschützter Eingaben beim entfernten Dienst abgeleitet. Eine frische, unabhängig bytegeprüfte Beobachtung von raumzeitterminal.de liefert HTTP 525. Installation, Neustart/Persistenz, HTTPS und produktiver EAP-Effekt werden nicht behauptet. Alle früheren Publisher-/Quota-, Mirror-, R2- und November-2-Archivpflichten bleiben erhalten.

`EFFECT_ACK_DONE` ist unbestätigt. Dieses Paket schließt den konkret beschriebenen lokalen Verbrauchernachweis und die neue Entwurfsfassung, nicht die vollständige Produktivierung oder wissenschaftliche Veröffentlichung.

## Integrität

`BUNDLE_MANIFEST.json` bindet den scoped Payload. Die globalen drei Integritätsausgaben und die beiden scoped Integritätsdateien selbst sind zur Vermeidung von Selbstreferenzen aus diesem Payloadmanifest ausgeschlossen. `REPOSITORY_FILE_MANIFEST.json`, dessen abgesetzter SHA-256 und `SHA256SUMS.txt` werden aus der exakt gelesenen unveränderten Basis und den tatsächlichen Kandidatenbytes inkrementell materialisiert. Das ist keine Behauptung eines vollständigen lokalen Main-Testlaufs.

`python3 package_completion.py` erstellt das reproduzierbare ZIP außerhalb dieses Verzeichnisses. Die ursprünglichen hochgeladenen ZIP-Bytes sind unter den Belegen erhalten. Code- und Textlizenzen, Ursprungszuordnung und die eigenen Lizenzen aller Drittkomponenten bleiben bestehen.
