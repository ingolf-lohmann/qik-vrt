<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# QIKVRT Standpunkt- und Serialisierungskodex V1

Status: Standpunktkapitel des konsolidierten, ausführbaren V1-Review-Kandidaten.
Einziger normativer Maschinenvertrag:
`policy/QIKVRT_CODEC_CONTRACT_V1.json#/standpoint`.
`policy/QIKVRT_STANDPOINT_CODEX_V1.json` ist dessen bytewertgleiche,
nichtnormative Kompatibilitätsprojektion; Tests weisen Abweichungen ab.
Implementierung:
`src/qikvrt_standpoint_codex.py`; Prüfeinstieg: `make standpoint-codex-test`.

Die Festlegung von Ingolf Lohmann wird hier erstmals in kanonische Bytes
materialisiert: jedes konforme Mengenelement trägt dieselbe exakt 400 Byte
große QIKVRT-Gesamtsignatur und eine zusätzliche individuelle Identität.
Das exakte Byteimage liegt in `canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin`;
der Maschinenvertrag bindet es zusätzlich per Hex und SHA-256.
Die Signatur beschreibt den verlustfreien, kanonischen, fail-closed Codec.
Ihre konkreten Bytes sind eine neue Implementierungsbindung dieser Festlegung;
sie werden nicht als bereits vorhandenes historisches Byteimage ausgegeben.

## Gemeinsamer Standpunkt: exakt 400 Byte

Alle Zahlen sind vorzeichenlose Ganzzahlen in Big Endian. Längen zählen
Octets (8-Bit-Bytes), niemals Zeichen. Offsets sind nullbasiert. Es gibt keine
plattformabhängige Ausrichtung, implizite Felder oder unbestimmten Reservebytes.

| Offset | Bytezahl | Feld | Verbindliche Bedeutung |
| --- | ---: | --- | --- |
| 0 | 8 | magic | ASCII `QIKVRTSP` |
| 8 | 2 | version | `1` |
| 10 | 2 | total_bytes | `400`, einschließlich Header und Padding |
| 12 | 2 | descriptor_bytes | Exakte UTF-8-Bytelänge des V1-Deskriptors |
| 14 | 2 | flags | `0`; andere Werte werden abgewiesen |
| 16 | 32 | descriptor_digest | SHA-256 der unten definierten Bindung |
| 48 | descriptor_bytes | descriptor | Exakte kanonische JSON-Bytes aus dem Maschinenvertrag |
| 48 + descriptor_bytes | 352 − descriptor_bytes | padding | Ausschließlich Nullbytes |

`descriptor_digest = SHA256(b"QIKVRT-STANDPOINT-V1\0" || signature[0:16] || descriptor)`.
Der JSON-Deskriptor verwendet die vorhandene `canonical_json`-Semantik:
UTF-8/NFC, sortierte Schlüssel, keine überflüssigen Leerzeichen, keine Floats.
Die V1-Werte sind fest gebunden; ein neu berechneter Digest legitimiert keinen
geänderten Deskriptor. Decoder akzeptieren ausschließlich die vollständigen,
im Maschinenvertrag per Hex und SHA-256 gebundenen V1-Signaturbytes.

Die Signatur ist für alle konformen Elemente identisch, unabhängig von
Repository, Rechner, Zeit, Sprache, Modellanbieter und Elementinhalt.
Die Formatversion wird bei einer Änderung der Signatur, Felder, Hash-Domänen,
Sortierung oder Semantik erhöht. Unbekannte Versionen werden abgewiesen;
es gibt keine implizite Herabstufung oder verlustbehaftete Migration.

## Individuelle Identität

Ein Element besteht aus `signature`, `stable_id`, `identity` und `payload`.
`stable_id` enthält exakt 32 Bytes. Der Aufrufer vergibt und persistiert für
jedes logische Element eine eigene stabile ID; sie wird weder aus der aktuellen
Listenposition noch allein aus den Inhaltsbytes abgeleitet. Für neu vergebene
IDs eignet sich eine 256-Bit-Zufallskennung oder eine SHA-256-Bindung eines
eindeutig zugewiesenen, dauerhaft gespeicherten Namensraums und Labels.

`identity = SHA256(b"QIKVRT-ELEMENT-V1\0" || uint16(1) || signature || stable_id || uint64(len(payload)) || payload)`.

Die Domäne und festen Feldbreiten verhindern Mehrdeutigkeit an Feldgrenzen.
Gleicher Inhalt mit verschiedenen stabilen IDs ergibt verschiedene gebundene
Elementidentitäten; eine Inhaltsänderung erhält die stabile ID und erzeugt eine
neue Inhaltsidentität. Doppelte stabile IDs und doppelte Identitätsdigests
innerhalb einer Menge sind Fehler und werden niemals zusammengeführt.
SHA-256 liefert Kollisionsresistenz, keine mathematische Kollisionsfreiheit.
Ein Digest authentifiziert weder einen Urheber noch eine Freigabe.

## Snapshot, Dump und Serialisierung

Diese drei Bezeichnungen verwenden exakt dasselbe Binärformat. Eine Menge
besitzt keine relevante Eingabereihenfolge. Der Serializer sortiert nach
`stable_id` in streng aufsteigender lexikografischer Byteordnung. Der Decoder
weist ungeordnete Eingaben ab, statt sie stillschweigend zu reparieren.

| Offset | Bytezahl | Snapshot-Feld | Bedeutung |
| --- | ---: | --- | --- |
| 0 | 8 | magic | ASCII `QIKVRTSS` |
| 8 | 2 | version | `1` |
| 10 | 2 | signature_bytes | `400` |
| 12 | 8 | element_count | Zahl der vollständigen Elemente |
| 20 | 8 | body_bytes | Exakte Bytezahl aller Elementrecords zusammen |
| 28 | 400 | signature | Kanonische Gesamtsignatur, auch für die leere Menge |
| 428 | body_bytes | elements | Records in kanonischer Byteordnung |

Jeder Record enthält ohne Zwischenräume oder implizites Padding:

| Relativer Offset | Bytezahl | Element-Feld |
| --- | ---: | --- |
| 0 | 400 | Dieselbe kanonische `signature` |
| 400 | 32 | `stable_id` |
| 432 | 32 | `identity` |
| 464 | 8 | `payload_bytes` als uint64 |
| 472 | payload_bytes | Unveränderte `payload`-Bytes |

Der leere Snapshot hat exakt 428 Bytes. Ein Snapshot mit n Elementen und p
Inhaltsbytes hat exakt `428 + 472*n + p` Bytes. Es gibt keine Trailer,
ignorierten Zusatzfelder, alternative Textkodierung oder implizite Kompression.
Payloads dürfen beliebige Bytes enthalten, einschließlich Nullbytes und
ungültigem UTF-8. Unicode-Normalisierung betrifft nur den festen Deskriptor.

Die Kompressionsschicht in `src/qikvrt_codec.py` transportiert genau diese
Snapshotbytes. Sie führt keine zweite Elementstruktur, Zufallsnonce oder
Snapshotserialisierung ein. Neue Container verwenden dieselbe feste Signatur.
Ausdrückliches Legacy-Decoding früherer generischer Transportcontainer bleibt
auf deren externe Seed-Bindung beschränkt und begründet keine Konformität
eines fremden Standpunkts; `decode_snapshot` akzeptiert diesen Modus nicht.

Für jede zulässige Menge E gilt:
`deserialize(serialize(E)) = sort_by_stable_id(E)` mit identischen Feldbytes.
Für jeden akzeptierten Dump D gilt: `serialize(deserialize(D)) = D` bytegenau.
Jedes semantische Feld wird erhalten; Reihenfolge und doppelte Mitglieder sind
ausdrücklich keine zusätzliche Mengensemantik.

## Fail-Closed und Ressourcen

Serializer und Deserializer geben erst nach vollständiger Validierung ein
Ergebnis zurück. Falsche Typen, veränderte Signaturen oder Digests, unbekannte
Versionen, widersprüchliche Längen, Trunkierung, Zusatzbytes, doppelte IDs,
geänderte Feldreihenfolge oder nichtkanonische Records werfen `CodexError`.
Der Decoder liest alle Elemente aus dem Snapshot, ohne Netzwerk, Modellaufruf,
Toolausführung, Uhrzeit, Zufall oder undeklarierten Empfänger-Vorzustand.

Das Wireformat besitzt uint64-Längen. Die lokale Standardgrenze beträgt
64 MiB pro Snapshot, 100.000 Elemente und 16 MiB pro Payload. `Limits` erlaubt
explizite andere nichtnegative uint64-Budgets, ohne das Byteformat zu ändern.
Ressourcengrenzen werden vor allokationsbestimmenden Längen verwendet.

Die 400 Bytes beschreiben den Codec; die Inhaltsbytes bleiben vollständig im
Dump. Dieser Kodex behauptet keine universelle Kompression beliebiger Daten
auf 400 Bytes, keine Rekonstruktion verlorener Daten und keine Ausführung
eines MC68000-Kernels. Solche Nachweise behalten ihre eigenen Verträge.

## Normativer Prozess und Provenienz

`BIND → SERIALIZE → DESERIALIZE → BYTE_COMPARE → TEST → READBACK` ist lokal
und deterministisch ausführbar. Er benötigt keinen ChatGPT-/OpenAI-Service
und keinen externen Modellanbieter. Optional aktivierte Assistenzadapter
behalten ihre Authentifizierungs-, Rechte-, Provenienz- und Wirkungsgrenzen;
ihre Verfügbarkeit ist keine Vorbedingung des Kodex.

Die veröffentlichte Charta, archivierte Publikationen, frühere Receipts und
ChatGPT-Herkunftsangaben bleiben byteunverändert. Ihr dokumentarischer
Interaktions- oder Beitragsnachweis wird nicht in eine Laufzeitpflicht
umgedeutet. Der Kodex ersetzt auch keine natürliche Verantwortung oder
TEMDD-Abnahme: Codec-Roundtrip und bestandene Tests sind allein kein Merge,
Release, wissenschaftlicher Universalitätsbeweis oder `EFFECT_ACK_DONE`.

## Verwendung

```python
from pathlib import Path
from src.qikvrt_standpoint_codex import Element, serialize, deserialize

element = Element(stable_id=bytes(range(32)), payload=b"arbitrary\x00bytes")
dump = serialize([element])
Path("snapshot.qikvrt").write_bytes(dump)
restored = deserialize(Path("snapshot.qikvrt").read_bytes())
assert restored == (element,)
assert serialize(restored) == dump
```

Regressionen prüfen beide Roundtrip-Richtungen, feste Vektoren, sämtliche
einzelnen Bitänderungen des Standpunkts, manipulierte Elementinhalte,
neuberechnete fremde Signaturen, doppelte Identitäten, Reihenfolge, Längen,
Versionen, Padding, Ressourcenbudgets und Dateireadback. Die Prüfungen laufen
auch unter `python -O`; die Validierung verwendet keine `assert`-Guards.
