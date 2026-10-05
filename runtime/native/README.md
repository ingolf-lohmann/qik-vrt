<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# QIKVRT Bootstrap und Laufzeitvarianten

Der erhaltene C90-Kern wird aus dem Snapshot
[`c6a53e200c4835a4f871d8496feb81d953610831`](https://github.com/ingolf-lohmann/qik-vrt/tree/c6a53e200c4835a4f871d8496feb81d953610831)
wiederverwendet. Die ursprünglichen Git-Blobs, SHA-256-Werte und Änderungen stehen
in [SOURCE_RECOVERY_20261005.json](../../evidence/native_release/SOURCE_RECOVERY_20261005.json).
Historische Testergebnisse werden nicht auf diese Ausgabe übertragen.

Der Kernel benötigt weder Netzwerk noch Anbieter-API, Betriebssystemaufrufe oder
Heap. Der ausführbare CLI-Adapter verwendet die C-Standardbibliothek. Neubau und
SQL-Adapter benötigen einen C90-Compiler beziehungsweise Python mit SQLite und
ctypes. Der S1-HTTP-/Docker-Träger hat seine eigenen, ausdrücklich gebundenen
Laufzeitabhängigkeiten. Damit ist Anbieterunabhängigkeit prüfbar; eine vollständige
Unabhängigkeit von Betriebssystem, Compiler und Interpreter wird nicht behauptet.

| Variante | Artefakt und Einstieg | Eigener Nachweis |
|---|---|---|
| Linux | `qikvrt-c90`, `libqikvrt.so` | C90-, TEMDD-, CLI-, Transport- und SQL-Ausführung |
| macOS | `qikvrt-c90`, `libqikvrt.dylib` | nativer macOS-Runner, gemessene Architektur |
| Windows | `qikvrt-c90.exe`, `qikvrt.dll` | nativer Windows-Runner; binärer stdin/stdout-Modus |
| SQL | SQLite-BLOB-UDF `qikvrt_evaluate` | Aufruf derselben nativen Bibliothek; ungültige Eingaben abweisen |
| TEMDD | C90-Kernel, Smalltalk-Klasse, MC68000-Routine | frische Tests je Backend; keine implizite DONE-Freigabe |
| Smalltalk | wiederhergestelltes Pharo-13-Image | SHA-gebundener VM-/Image-Bootstrap und exhaustive C90-Vergleiche |
| MC68000 ABI | Objekt, rohe `.text`-Bytes, statischer Linux-ABI-Test | `-m68000`, Disassembly und QEMU-Ausführung; kein Hardwarebeweis |
| HTTP / Docker | bestehendes S1-Paket 1.2.0 | `make self-host-test`, native systemd- und isolierte Docker-Tests |

Eine Builddefinition ist noch kein verfügbares Binary. Ein Ziel wird erst mit
seinem erfolgreich ausgeführten `EXECUTION.json`, den Artefaktbytes und ihren
Prüfsummen aufgenommen. Windows-Server-CI ist kein Nachweis einer Ausführung
auf Windows 11; eine solche Zielumgebung benötigt ihren eigenen Readback.

## Quellgebundener Erstbau

In einem sauberen Checkout des veröffentlichten Quell-Commits:

```sh
python3 tools/qikvrt_native_release.py build --root . \
  --expected-head "$(git rev-parse HEAD)" \
  --expected-tree "$(git rev-parse 'HEAD^{tree}')" \
  --output /tmp/qikvrt-native
```

Der Builder kopiert ausschließlich die im Commit festgelegten Paketdateien,
kompiliert CLI und gemeinsame Bibliothek und führt die Tests aus. Er erzeugt
`MANIFEST.json`, `EXECUTION.json` und `/tmp/qikvrt-native.zip`. Der ausgegebene
Manifest-SHA-256 muss unabhängig vom heruntergeladenen Paket bezogen werden,
zum Beispiel aus dem bestätigten Zenodo-Record und dem Repository-Releaseindex.

```sh
python3 tools/qikvrt_native_release.py verify --package /tmp/qikvrt-native \
  --manifest-sha256 MANIFEST_SHA256
/tmp/qikvrt-native/bin/qikvrt-c90 evaluate 0000000700000003060201010100
python3 tools/qikvrt_native_release.py sql --package /tmp/qikvrt-native \
  --manifest-sha256 MANIFEST_SHA256
```

Das Beispiel liefert `000000040201`: Wert 4, CONTINUE, gültig. Die feste ABI
verwendet 14 Eingabe- und 6 Ausgabeoktette in Big-Endian-Reihenfolge. Sie ist
kein vollständiger EFFECT_ACK-DONE-Nachweis und führt keine externen Effekte aus.

## Neubau ohne Git, Netzwerk oder Anbieterzugang

```sh
python3 /tmp/qikvrt-native/source/tools/qikvrt_native_release.py rebuild \
  --package /tmp/qikvrt-native --manifest-sha256 MANIFEST_SHA256 \
  --output /tmp/qikvrt-native-rebuilt
```

Das vorhandene Paket wird vor Nutzung aller Quellen geprüft. Jede Zieldatei,
jeder zusätzliche Eintrag und jede Symlink-Abweichung muss zum Manifest passen.
Der Neubau erhält einen eigenen Ausführungsbeleg und einen eigenen Manifestpin.
Gleiche Quellbytes garantieren keine identischen Binärbytes über verschiedene
Compiler; deshalb wird der Compiler selbst mit Version und SHA-256 gebunden.

## Smalltalk, MC68000 und S1

```sh
python3 tools/qikvrt_smalltalk.py install
python3 tools/qikvrt_smalltalk.py test
python3 tools/qikvrt_smalltalk.py build --output /tmp/qikvrt-smalltalk
make self-host-test
```

Pharo-Downloadbytes werden vor der Nutzung gegen den vorhandenen Lock geprüft.
Die CI bewahrt Image, Changes, Sources, ursprüngliche VM-/Image-Archive und deren
Lizenztexte. Der MC68000-Job erhält die bestehende Assembly und prüft zusätzlich
ungültige Ereigniswerte, deren niederes Byte 1 oder 2 ist. `cmpi.l` verhindert,
dass solche Werte als gültiges Ereignis durchgehen. Die reine MC68000-Routine
nutzt D0; der Testadapter verwendet die dokumentierte m68k-Linux-C-ABI.

Das vollständige S1-Bootstrap-Paket wird weiterhin mit
`tools/qikvrt_self_host.py pack` gebaut. Es wird nicht durch den kleineren
nativen Kernel ersetzt. Codeexport enthält keine Zugangsdaten oder Live-Zustände;
ein privater Zustandsumzug bleibt an seinen bestehenden Recovery-Vertrag gebunden.

## Zenodo und Repository-Nodes

Jede neue Variante ergänzt [VARIANTS.json](VARIANTS.json) und dieses sichtbare
Verzeichnis. Die vorhandene CI baut sie am exakten Commit. Der Releaseindex
bindet Ziel, Quell-Head/Tree, Lizenzdateien, Binary-SHA-256 und Testbeleg.
Bootstrapping, Quellpaket, Zielbinary, Anleitung, Lizenztexte und Maschinenbelege
werden als zusammengehöriger Versionssatz archiviert. Ein neues Ziel erhält
einen neuen Zenodo-Versionskandidaten im selben Versionsverbund, niemals eine
stille Änderung archivierter Bytes.

Der bestehende `tools/qikvrt_zenodo_publish.py` bleibt der Veröffentlichungspfad.
Vor Veröffentlichung sind der v2-Maschinenbeleg, die Rückgabe des konkreten
Kandidaten, die bestehende exakte Autorisierung und ein authentifizierter
Zenodo-Zugang erforderlich. Erst der öffentliche Download-Readback erlaubt
`PUBLISHED`. DOI, Record-ID oder Node-Synchronisation dürfen nicht vorweggenommen
werden. Jeder Node erhält dieselben geprüften Quell-/Archivbytes sowie seine
eigene Zielvariante; Head, Tree und Paketpins werden anschließend neu gelesen.
Nicht erreichbare Nodes bleiben ausdrücklich offen. Neue Nodes verwenden den
gleichen Importvertrag und ergänzen ihr Ziel, statt eigene Kernlogik einzuführen.

## Lizenzen

Es gelten die erhaltenen dateispezifischen Hinweise und die mitgelieferte
[Lizenzzuordnung](../../LICENSE). Aktueller QIKVRT-Code:
PolyForm-Noncommercial-1.0.0; Dokumentation: CC-BY-NC-ND-4.0. Kommerzielle
Nutzung erfordert eine gesonderte schriftliche Erlaubnis. Historische Ausnahmen
und Drittanbieterhinweise bleiben erhalten. Pharo-/VM-/Systembibliotheken werden
nicht als QIKVRT-eigenes Werk oder unter einer anderen Lizenz ausgegeben.
