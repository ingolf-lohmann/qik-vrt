<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Universales Raumzeit-Terminal: Bootstrap und geprüfte Laufzeitvarianten

Vorbereiteter Software- und Nachweissatz für Zenodo und QIK-VRT-Nodes.
Quell-HEAD: bc2da76a46b4f0e0eb3c63f3468f1cde83e6f698
Quell-TREE: be501e917d2d8ded677e6c32ee4eddc27f2c1398
Originalarchiv: 118774398 Bytes.
SHA-256: c6d6cb258d8e2f35874f7783a3c802f8cd6159d6f8e8bcd2388dd375c1b011e3

Das Archiv ist für die Repository-Ablage in 29 unveränderte Teile zerlegt.
BUNDLE_PARTS.json bindet Reihenfolge, Bytezahlen, SHA-256 und Git-Blobs.
Die native CI hat Linux x86_64, macOS arm64, Windows Server 2025 AMD64,
SQLite/TEMDD, Pharo 13.1 unter Linux und MC68000 unter einem Linux-ABI-Emulator
ausgeführt. HTTP/Docker ist durch den S1-Quellträger und Firefox/noVNC-CI belegt;
ein vollständiges OCI-/noVNC-Laufzeitimage ist nicht im Archiv enthalten.
Windows 11 und physische MC68000-Hardware bleiben offen.

## Wiederherstellung auf Linux, macOS und Windows

Im Verzeichnis dieses README mit Python 3 ausführen:

```python
import pathlib, json, hashlib
p = pathlib.Path('.')
m = json.loads((p / 'BUNDLE_PARTS.json').read_bytes())
out = p / m['archive']['name']
with out.open('xb') as f:
    for e in m['parts']:
        b = (p / e['name']).read_bytes()
        assert len(b) == e['bytes']
        assert hashlib.sha256(b).hexdigest() == e['sha256']
        f.write(b)
assert out.stat().st_size == m['archive']['bytes']
assert hashlib.sha256(out.read_bytes()).hexdigest() == m['archive']['sha256']
```

Nach dem Entpacken stehen die drei qikvrt-native-*.zip, die Smalltalk-Image-/VM-
Dateien, MC68000-Objekt/Raw-Kernel/ABI-Witness, der S1-Quellträger, die Firefox-
Erweiterung und alle gebundenen Belege bereit. Die Datei runtime/native/README.md
im Archiv enthält Aufruf, SQL-Nutzung und Neubau ohne Git/Anbieterzugriff.

## Lizenz- und Provenienzbindung

Die vollständigen Lizenztexte und dateispezifischen Hinweise liegen im Archiv.
QIK-VRT-Code: PolyForm-Noncommercial-1.0.0; Dokumentation: CC-BY-NC-ND-4.0;
historische und Drittanbieter-Lizenzen bleiben erhalten. Eine Veröffentlichung
ändert keine dieser Rechte. Kommerzielle Nutzung benötigt den bestehenden
gesonderten schriftlichen Grant. Der C90-Kernel ist anbieterunabhängig; Compiler,
Betriebssystem, C-Bibliothek, Python/SQLite, Pharo und S1 behalten ihre deklarierten
Abhängigkeiten. Vollständige Unabhängigkeit von jeder anderen Software wird nicht
aus dem begrenzten Nachweis abgeleitet.

## Publikations- und Variantenstatus

CLAIM_MATRIX.json trennt gemessene Ergebnisse, Quellbindung, Owner-Regeln und
offene Ziele. Neue Varianten werden durch die vorhandene CI exakt gebaut und
gesammelt. Ihre Veröffentlichung bleibt an den vorhandenen Zenodo-v2-Publisher,
eine tatsächliche Authority, sichere Credentials und die konkrete gebundene
Freigabe angeschlossen. Eine neue Variante benötigt neue Zielausführung und
neue öffentliche Datei-Readbacks; Vorgängerevidenz wird nicht übernommen.

Dieser Kandidat hat noch keinen neu veröffentlichten DOI. Die vollständige
Veröffentlichung und All-Node-Synchronisierung bleiben bis zum echten Readback
offen. Repository-/CI-URLs in den Belegen sind Provenienz, keine finalen
wissenschaftlichen Zenodo-Zitate.
