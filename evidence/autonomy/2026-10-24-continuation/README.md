# Fortsetzungsreparatur und reproduzierbare technische Evidenz

Die dauerhafte technische Projektablage erfolgt im QIK-VRT Authority-Repository.
Ein Dateispeicherlimit dieses Chat-Clients und der beobachtete OneDrive-Fehler
`serviceReadOnly` sind keine Sperre dieser bestätigten Repository-Schreibroute.
Der private historische Korpus wird mit diesem Paket nicht veröffentlicht.

Der ursprüngliche Fortsetzungsworker beendete Lauf 40069884460 für PR #459 nach
bestandenen Tests bei `REST POST git/trees: 502`. Die vorhandene Exportfunktion
prüft nach einer 5xx- oder verlorenen Transportantwort nun genau einmal den
bereits vorher berechneten Git-Baum. Sie rekonstruiert dessen Originalbytes,
setzt nur bei passender Identität fort und wiederholt den POST nicht. Fehlende,
beschädigte, unvollständige oder unlesbare Nachweise halten an; 403 bleibt 403.

Das vollständige ZIP liegt als ausdrücklich bezeichnete Base64-Nutzlast in
`REPRODUCIBLE_PACKAGE.json`. Größe, SHA-256 und ein Dateimanifest erlauben die
bytegenaue Wiederherstellung und Prüfung. Quelltexte und Lizenzhinweise bleiben
erhalten. Die Originale der eigenen lokalen Diagnosejournale sind ausschließlich
lesend/immutable zu öffnen; eine Kopie erhält keine Writerzulassung.

Die archivierten 43 Fortsetzungstests, der lokale Volltest und der native
Test-Fixpunkt beziehen sich auf HEAD 09cd7e5adefd1e64634668f2a5988cce9d9c60f4 /
TREE 4a88006895a6514e8a4cf691bd18c8983cf88bd4. Die spätere Main-Änderung
51f516368ae33d1d788e50b0301929d0252187e5 wurde ohne semantischen Quellkonflikt
aufgenommen; nur erzeugte Integritätsdateien mussten neu erzeugt werden.
Für jeden Integrationsnachfolger sind frische eigene Tests und Readbacks nötig.
Den aktuellen Integrationsstand aus PR #595 und Main lesen, nicht aus einem
historischen Archivstatus ableiten.

Produktive HMI-unabhängige Fortsetzung bleibt eine eigene offene Abnahme:
aktuelles offiziell signiertes XPI, zugelassener dauerhafter Runtime-Endpunkt,
Originalhost und frischer Nutzpfad-Readback auf raumzeitterminal.de. Source-PASS
oder diese Ablage begründen weder produktive Abnahme noch EFFECT_ACK_DONE.

Wiederherstellen mit Python-Standardbibliothek:

```python
import base64, hashlib, json
from pathlib import Path
p = json.loads(Path('REPRODUCIBLE_PACKAGE.json').read_text())
raw = base64.b64decode(p['artifact_base64'], validate=True)
assert len(raw) == p['artifact_size_bytes']
assert hashlib.sha256(raw).hexdigest() == p['artifact_sha256']
Path(p['artifact_name']).write_bytes(raw)
```

Architektur und Autorisierung: Ingolf Lohmann. Implementierung, Prüfung und
Aufbereitung: OpenAI Codex im autorisierten Auftrag. Keine unabhängige
menschliche Prüfung, andere Knotenübernahme oder produktive Wirkung behauptet.
