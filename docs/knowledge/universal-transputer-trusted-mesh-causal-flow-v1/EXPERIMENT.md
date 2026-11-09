# Zwei-Speicher-Experiment: evidenzgebundener Hin- und Rückweg

**Status: LOCAL_BOUNDED_REFERENCE / NOT_NETWORKED / NOT_PRODUCTIVE / NOT_SCIENTIFICALLY_REVIEWED**

Dieses Experiment operationalisiert die im Erkenntnisknoten V1 formulierte H1. Es sind **zwei getrennte Verzeichnisse in einem lokalen Python-Prozess**, nicht zwei unabhängig kontrollierte Maschinen, kein authentifizierter Mesh-Transport, keine IONOS-Instanz und kein EAP-Ausführungsbeleg.

## Ausführung

Vom Repository-Root:


```sh
python3 -B -m unittest discover -s docs/knowledge/universal-transputer-trusted-mesh-causal-flow-v1 -p 'test_two_way_reference.py' -v
```

Nur Python-Standardbibliothek; keine externen Services, Pakete, Zugangsdaten oder Netzwerkaufrufe. Der Versuchsstand ist an den angegebenen Code- und Test-Blob gebunden.

## Prüflogik

1. Node-A erzeugt ein typisiertes Ereignis (CLAIM oder COUNTER_EVIDENCE) mit originalem Bytepayload, Quell-HEAD und SHA-256, speichert es in seinem separaten Outbox-Verzeichnis.
2. Node-B prüft den zu erwartenden Sender-Identifikator, den exakten HEAD, Event-ID, SHA-256, die nächste lückenlose Sequenz und den vorherigen Receipt-Digest. Ohne ausdrückliche **lokale Simulationszulassung** verweigert Node-B die Annahme.
3. Node-B schreibt die neuen Bytes und ein strikt als RECEIVED_VERIFIED klassifiziertes Receipt in die eigene Dateispeicherung (atomare Ersetzung mit fsync).
4. Node-A liest das Receipt über eine separate Lesefunktion erneut aus dem Node-B-Verzeichnis, prüft seine Bindung und markiert das lokale Empfangs-Readback. Das ist **kein** physischer Wirknachweis.
5. Wiederanlauf und Replay werden mit einem neuen Receiver-Objekt gegen denselben gespeicherten Node-B-Bestand geprüft; Gegenbelege bleiben getrennte Ereignisse.

**Lokale Negativkontrollen:** ausgelassene Sequenz, Event-ID mit anderen Payloadbytes, falscher Quell-HEAD, veralteter Vorgänger-Receipt, fehlende Zulassung, fehlendes Receipt, manipuliertes Ledger, falscher Receiver, Payloadänderung ohne Hash, gefälschtes effect_ack_done=true und idempotenter Replay ohne zusätzliche Buchung.

## Ergebnis und Grenzen

Die lokale Python-3.13.5-Ausführung der exakt in `LOCAL_VALIDATION_REPORT.json` gebundenen Dateien hat **14/14 Tests PASS** geliefert. Dies ist ein gemessener *Software-Regressionsbefund* innerhalb eines Prozesses auf einem Dateisystem. Ein Speicher-SHA-256 beweist keine Absenderauthentisierung, Byzantine-Sicherheit, Netzwerkeigenschaft, tatsächliche Effekt-Ausführung oder physikalische Kausalität.

Für eine unabhängige Zulassung wären getrennte Hosts/Sicherheitsdomänen, geprüfte kryptografische Node-Identitäten, echte Transportfehler, crash-konsistente Writer-Isolation, gegengeprüfte ACK-Journale, Originalhost-Readback und separate EAP-Wirkungsprüfung erforderlich. Genau diese Punkte bleiben **OPEN**, insbesondere `EFFECT_ACK_DONE` bleibt hier immer `false`.

**Nicht nachgewiesen:** eine allumfassende „Verlustfreiheit“ unter beliebigen Ausfällen; persistente Outbox-Verifikation bei beliebiger Manipulation; unbeschränkte parallele Sender; physikalischer Rückwärts-Zeitkanal; universelle Rechenfähigkeit oder kosmologische Wahrheit.
