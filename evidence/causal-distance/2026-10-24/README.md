# Kausale Distanz und lokaler Wirkungsnachweis — persistierter Kandidat

**Die dauerhafte Ablage dieses Ergebnisses erfolgt im QIKVRT Authority-Repository.** Der frühere Hinweis auf das Dateispeicherlimit dieses Chat-Clients begründet keine Sperre dieser Repository-Ablage und ist insoweit korrigiert.

## Inhalt und Identität

- [Vollständiges reproduzierbares Paket](REPRODUCIBLE_PACKAGE.json): ZIP als explizit bezeichnete Base64-Nutzlast, 262030 Originalbytes, mit 71 manifestgebundenen Dateien einschließlich Implementierung, Tests, Originalquellen, Rohreadbacks und Prüfbericht.
- [Lesbarer Quelltext der Distanzkomponente](qikvrt_causal_distance.py).
- [Persistenzquittung](PERSISTENCE_RECEIPT.json): tatsächliche Commits und Blob-IDs sowie bytegleicher unabhängiger Repository-Readback.

Original-ZIP SHA-256:

`d070ae7e9c15feeadedddf55b3bf77072a3b74289dad60bb3adce4aee7089f91`

Das unveränderte ZIP bewahrt auch den historischen Bericht mit dessen damaligem Ablagestatus. Für die jetzt erfolgte Repository-Persistenz ist diese korrigierende Nachfolgernotiz maßgeblich. Die im ZIP enthaltenen früheren Testjournale bleiben historische, nur lesend zu öffnende Exporte.

## Ergebnis und Grenze

Im lokalen kontrollierten Programm gibt die passende Zukunftsbedingung eine reale Dateiänderung von 2 auf 3 frei. Unpassende Zukunftsbedingung, falscher Archivtyp und fehlende Verantwortung verhindern sie. Das eingefrorene Vergangenheitsarchiv bleibt unverändert. Der originale Terminal-Leser bestätigt elf Ereignisse nach erneutem Öffnen; ein Feedbackschritt erzeugt aus dem beobachteten Ergebnis die nächste Erwartung 4.

61 dokumentierte Tests bestehen: 16 neue Metrik-/Witness-Tests, 41 originale EAP-Tests und vier ausgewählte originale Writer-Kontinuitätstests. Alle 4096 gerichteten Graphen mit vier Knoten werden gegen eine unabhängige Floyd-Warshall-Berechnung geprüft.

Der gerichtete Abstand ist die kleinste Summe positiver ganzzahliger Gewichte entlang eines gerichteten Abhängigkeitspfads. Er ist eine erweiterte Quasimetrik. Die ungerichtete Projektion liefert eine symmetrische Metrik innerhalb jeder zusammenhängenden Komponente. Bei Einheitsgewicht ist die Einheit ein ausdrücklich deklarierter primitiver Abhängigkeitsschritt. Fehlender Pfad in einem unvollständigen Graphen begründet keine physische Unmöglichkeit. Rückwärtsgerichtete Suche ist von physischer Retrokausalität getrennt.

Diese Ablage integriert den Kandidaten noch nicht in produktive Ausführung oder Main. Die dokumentierten Tests gehören zum eingefrorenen lokalen Kandidaten; ein vollständiges `make test`, neue Lean-Kernelprüfung und Head-CI sind hier nicht als ausgeführt behauptet. Laufzeit- und Domain-Abnahme bleiben eigene Nachweise und verhindern nicht diese Datenablage.

## Paket lokal wiederherstellen

Nach einem normalen Checkout dieses Branches im Verzeichnis dieser README ausführen:

```python
import base64
import hashlib
import json
from pathlib import Path

package = json.loads(Path("REPRODUCIBLE_PACKAGE.json").read_text())
data = base64.b64decode(package["artifact_base64"], validate=True)
assert len(data) == package["artifact_size_bytes"]
assert hashlib.sha256(data).hexdigest() == package["artifact_sha256"]
Path(package["artifact_name"]).write_bytes(data)
```

Nach dem Entpacken enthält die Paket-README die vollständige mathematische Herleitung und Reproduktionsbefehle. Der ZIP-Manifestindex erlaubt die unabhängige Prüfung jeder enthaltenen Datei.

Architekturgedanke und Autorisierung: Ingolf Lohmann. Implementierung, lokale Prüfung und Aufbereitung: ChatGPT im autorisierten Auftrag.
