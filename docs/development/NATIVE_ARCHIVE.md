<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation/evidence: OpenAI Codex. -->
# Nativer Archiv-, Laufzeit- und Terminalnachweis

Ingolf Lohmann beauftragt am 30.10.2026 die ausführbare Prüfung der Übergänge
von doppelt kanonischem Speicher zu verlustfreier Archivierung, ZIP-Anschluss,
nativer Ausführung, Laufzeit, Transputer und Terminal. Die Universalitätsaussage
bleibt seine Architekturthese. Jeder folgende Nachweis besitzt einen eigenen
Geltungsbereich; eine erfolgreiche Stufe bestätigt keine ungeprüfte Folgestufe.

## Reproduzieren

```sh
make native-archive-test
python3 -B tools/qikvrt_native_archive.py --commit <vollständige-commit-sha> --output /tmp/qikvrt-archive-proof
```

Der zweite Befehl benötigt einen vollständigen, lokal lesbaren Objektbestand
für den ausgewählten Commit und seine aktuellen Quelldateien. Er startet weder
archivierten Quellcode noch einen Produktionsdienst. Das Ausgabeverzeichnis muss
neu sein. Der belegte Umfang ist der vollständige **getrackte Quellbaum**, mit
Dateimodi und Symlink-Bytes; Git-Historie, lokale Geheimnisse, ignorierte Dateien
und laufende Hostzustände werden nicht als mitarchiviert ausgegeben.

Commit, jeder durchlaufene Tree und jeder Blob werden zusätzlich zu Gits
Objektauskunft anhand ihrer Originalbytes nachgerechnet. Der ZIP-Manifestbestand
bindet Pfade, Modi, Größen, Git-Blob-Identität und SHA-256. Auch Metadateneinträge
haben feste ZIP-Zeitstempel. Eine Änderung am Prüftreiber während des Laufs
verhindert die Abnahme. Compiler, Flags, native Quellen, Header, Binärdatei und
tatsächliche libz-Datei werden mit ihren Hashes festgehalten.

## Welche Übergänge geprüft werden

| Aussage | Ausführbarer Nachweis | Grenze |
| --- | --- | --- |
| Vollständiger ausgewählter Quellbaum verlustfrei gespeichert | Git-Objektprüfung, ZIP-Inventar, nativer QIKVRTC-Roundtrip, unabhängiges Python-Decoding, Original-/Restore-Hashes | Genau der gebundene Commit; keine stillschweigende Git-Historie |
| Standard-ZIP lesbar | Python-ZIP und eigenständiges Info-ZIP lesen ZIP und SFX | Kein tatsächlicher WinZip-Anwendungslauf auf Windows |
| Selbstextrahierendes Executable | Reales Linux-ELF mit eingebettetem ZIP; native Extraktion liefert bytegleiches `repository.zip` | Linux/ELF/POSIX und verfügbare passende libc/libz; andere ABIs offen |
| Explizite gespeicherte Programmausführung | Dasselbe native Executable liest eine binäre Übergangstabelle; unabhängiges Sparse-Tape-Modell prüft gegen den C90-Kern | Begrenztes Referenzprofil; kein unbegrenzter physischer Rechner |
| Terminal-Anschluss | ORIGINALER authentifizierter Loopback-Handler: Prepare, veränderte Eingabe abgewiesen, einmaliger Commit, unabhängiger GET, Replay abgewiesen | Lokale Eingabebeobachtung, keine produktive Transputer-Aufnahme |
| Produktive universale Mesh-Laufzeit und alle Plattformen | Eigene originale Admission-, Host-, Peer- und Zielplattform-Abnahmen erforderlich | OPEN; keine Ableitung aus lokaler Speicherung oder einem Fixture |

Der externe Produktionsweg wird nicht ersetzt. Ein fehlendes
`ADMITTED_MESH_RUNTIME_ENDPOINT` bleibt eine offene Admission-Voraussetzung.
Die temporäre lokale Terminalprüfung ist ausdrücklich ein Fixture des
Originalhandlers, kein Ersatz für dessen produktive Journal-/Writer-Identität.

## Nativer Zahlen- und Dateivertrag

`src/codec_native.c` implementiert das bestehende QIKVRTC-V1-Format aus
`src/qikvrt_codec.py`, einschließlich der unveränderten 400-Byte-Signatur.
RAW und balanced/zlib verwenden dieselben Header, Blockhashes und Footerregeln.
Es gibt kein neues paralleles Kompressionsformat. Ein Decoder verwirft fremde
Signaturen, ungültige Längen, unvollständige oder zusätzliche zlib-Streams,
Hashfehler, falsche Zähler, überschrittene Budgets und angehängte Daten.

Der Berechnungskern ist strikt C90 und verwendet Integer-/Bitoperationen ohne
Fließkomma. Das Archiv braucht keine Q16.16-Quantisierung: Bytewerte bleiben
exakt, entsprechend Skalierung 1. Der vorhandene Q16.16-Vertrag bleibt für
numerische Nutzlasten maßgeblich; seine Rundungsregeln werden nicht auf
beliebige Archivbytes übertragen. SHA-256 arbeitet mit explizit auf 32 Bit
begrenzten Wörtern auch auf Hosts mit breiterem `unsigned long`.

Dieses native Profil benötigt 8-Bit-Bytes und ausreichend breite `size_t` und
`unsigned int`. Es begrenzt einen Nutzdatenstrom ausdrücklich auf 2^31-1 Bytes
und Blöcke auf 4096 bis 16777216 Bytes. Das allgemeinere bestehende Wireformat
wird dadurch nicht geändert. Größen außerhalb des Profils werden abgewiesen.
Der POSIX-Dateiadapter schreibt zunächst eine private temporäre Datei, prüft
und synchronisiert sie und ersetzt das Ziel erst nach erfolgreicher Abnahme.
Spezialdateien und Symlink-Ziele werden nicht ersetzt. Eine Aussage über
Crash-Durabilität des Zielverzeichnisses ist damit nicht verbunden.

zlib ist eine separat identifizierte native Abhängigkeit, kein eigener
QIK-VRT-Algorithmus. Fehlende Header, Library oder Info-ZIP führen zum Abbruch;
der Nachweis installiert keine Pakete und lädt keine ungebundenen Binärdateien.
Die vorhandene Toolchain-/Cache-Registry enthält die zugehörigen Verträge.

## ZIP und nativer Start

Der Standard-ZIP-Quellcontainer enthält alle ursprünglichen Dateien direkt und
zusätzlich `.QIKVRT_ARCHIVE/manifest.json` sowie `standpoint.bin`. Der Linux-SFX
enthält einen echten ELF-Präfix und ein Standard-ZIP mit `repository.zip` und
einem kleinen gespeicherten Beispielprogramm. Info-ZIP kann beide Einträge
ohne Ausführung des ELF lesen. Das native Programm extrahiert das innere ZIP
über einen längen- und hashgebundenen Locator im normalen ZIP-Kommentar.
Es extrahiert keine vom Archiv vorgegebenen Pfade auf dem Host.

```sh
./qikvrt-repository.run extract restored.zip
./qikvrt-repository.run --version
./qikvrt-repository.run machine binary_increment.tm 1110 100 100
```

Die native Startdatei beginnt mit ELF, nicht mit einem Nullbyte. Die früher
beschriebene Nullbyte-Hülle ist ein eigener Formatentwurf und wird durch diesen
ZIP/SFX-Anschluss weder rückwirkend umgeschrieben noch als direkt vom
Betriebssystem startbar ausgegeben. Ein Ausführbarkeitsnachweis benötigt die
tatsächlich gestartete Zielplattformdatei.

## Programm- und Simulationsvertrag

Das reine Referenzprogramm besteht aus Magic `QIKTM01\0`, einer Big-Endian-
16-Bit-Zustandszahl und zwei vier Byte langen Regeln je Zustand. Eine Regel
enthält Folgezustand (16 Bit), Schreibbit und Richtung (0 links, 1 bleiben,
2 rechts). Zustand 0 ist der Start, 65535 ist HALT; sonstige Folgezustände müssen
im deklarierten Programm liegen. Das native Profil erlaubt 1 bis 4096 Zustände,
höchstens 10000000 Schritte und höchstens 1000000 Bandzellen. Die Eingabe ist
eine Bitfolge. Außerhalb ihres anfänglichen Bereichs ist das Band null.
Nur nach HALT wird das Ergebnis ausgegeben; Ressourcenfehler sind keine
erfolgreiche Berechnung. Die Maschine kennt weder Shellbefehle noch Netzwerk,
Geheimnisse oder einen privilegierten Host-Dispatcher.

Der konstruktive Simulationsschritt ist explizit: Für Zustand q und gelesenes
Bit b wird Regel `2*q+b` gewählt, deren Bit geschrieben, der Kopf bewegt und
der Folgezustand übernommen. Eine neue Bandzelle enthält null. Identische
Anfangskonfiguration und identische Übergangstabelle ergeben durch Induktion
über die Schrittzahl identische Konfigurationen, solange beide Ausführungen
innerhalb des deklarierten Budgets liegen. Die Differenztests verwenden für
die unabhängige Referenz ein Integer-adressiertes Sparse Tape statt der
nativen verketteten Zellen.

Dies ist ein nachvollziehbares Simulationsargument plus ausführbare Evidenz
für das endliche Profil. Es ist kein Kernelbeweis über den C-Compiler, keine
uneingeschränkte Turing-Vollständigkeitsabnahme des produktiven Mesh und kein
Nachweis nativer Ausführung auf jeder existierenden Zielplattform. Insbesondere
wird Rechneruniversalität nicht allein aus der Speicherfunktion gefolgert.

## Belege und Messung

Der eingefrorene Prüfbeleg liegt unter `evidence/native-archive/2026-10-30/`.
Der Prüftreiber erzeugt zusätzlich die tatsächlichen ZIP-, QIKVRTC-, ELF- und
Restore-Artefakte. Source-, Restore- und Referenz-Hashes müssen übereinstimmen.
Wiederholung mit gleichem Quellbaum und gleicher Codec-/Toolchain-Version muss
dieselben Archivbytes ergeben; Terminalereignisse behalten ihren eigenen
Beobachtungszeitpunkt und sind keine deterministischen Paketbytes.

Die aufgezeichneten Einzelzeiten sind keine statistische Performance-Abnahme.
Die fünf vergleichbaren Vorher-/Nachher-Paare der bestehenden Performance-Phase
bleiben erforderlich. Der native Backend wird nicht allein aufgrund seiner
Sprache als schneller ausgegeben und ersetzt den Python-Standardpfad nicht
automatisch.

Die fünf abwechselnden warmen Messpaare am vollständigen 295.614.106-Byte-ZIP
ergaben auf demselben Host folgende Medianwerte. Jeder zeitlich gemessene
Output wurde anschließend gegen den ursprünglichen SHA-256 geprüft.

| Vorgang | Python-Referenz | Portabler C90-Kern | Python / C90 |
| --- | ---: | ---: | ---: |
| Kodieren, CLI-Wandzeit | 7,527 s | 10,461 s | 0,720 |
| Dekodieren, CLI-Wandzeit | 0,860 s | 3,648 s | 0,236 |

Der native Kern ist hier langsamer. Python nutzt bereits native Hash- und
Kompressionsbibliotheken; die Referenz berechnet zusätzlich einen Nutzdatenhash.
Der Standardpfad bleibt deshalb bestehen. Der nächste Optimierungsschritt muss
am tatsächlich gemessenen Engpass ansetzen. Diese Werte belegen weder eine
Beschleunigung der gesamten CI noch den angestrebten Faktor 10.

`MEASUREMENT.json` enthält alle Einzelzeiten und CPU-Zeiten, Compiler-/Binär-
und Quellenbindungen sowie getrennte Build-, Start- und I/O-Messungen. Die
Build-Zeit betrug 0,464 s. CLI-Werte enthalten Start, I/O und Synchronisation;
die getrennten Baselines werden nicht davon abgezogen. Die Serie ist warm;
der Host ist geteilt und keine exklusive CPU-Zuteilung wird behauptet.
Reproduktion nach einem vollständigen Prüflauf, aus dem Repository-Root:

```sh
python3 -B evidence/native-archive/2026-10-30/MEASUREMENT.py /tmp/qikvrt-archive-proof /tmp/measurement.json
```

`FULL_TEST_VALIDATION.json` bindet den vollständigen lokalen `make --trace test`:
2.247 Python-Testausführungen, die native Testgruppe und die abschließende
Integritätsprüfung sind enthalten. Zwei frühere zusammengeführte Protokolle
waren unvollständig und werden nicht als Gesamtabnahme verwendet. Getrennte
Originalausgaben und ihre Hashes sind archiviert; eine Ursache im Testcode ist
aus den unvollständigen Protokollen nicht nachgewiesen. Die spätere native
PR-CI muss den finalen Commit separat bestätigen.

Primärquellen der verwendeten Formate/API:

- PKWARE ZIP APPNOTE 6.3.10: https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT
- Originales zlib-Handbuch: https://www.zlib.net/manual.html
- Bestehender QIK-VRT-Vertrag: `policy/QIKVRT_CODEC_CONTRACT_V1.json`
