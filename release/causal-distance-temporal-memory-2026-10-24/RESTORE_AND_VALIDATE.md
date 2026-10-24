# Anschlussarbeit: Kausale Distanz und doppelkanonischer Speicher

Dieses Paket enthält die fertigen Artikel, die reine TTS-Fassung, den ursprünglichen lokalen Wirkungsnachweis und die neue lesende Selbstvermessung des Frameworks. Es enthält keinen erfundenen neuen DOI und keine vorweggenommene Publikationsbestätigung.

Die neue Veröffentlichung ist als eigenständiges Ergänzungspaket zu DOI 10.5281/zenodo.21711193 vorbereitet, Relation isSupplementTo. Die historische Veröffentlichung bleibt unverändert. Die aktuellen Hauptdokumente stehen in release/causal-distance-temporal-memory-2026-10-24/.

PR #596 wurde mit dem getesteten Nachfolger add410ae56cb9c18cb1d0e3bb6553b6d6c7a404e auf Main integriert. Der Merge-Readback bestätigt Commit 51f516368ae33d1d788e50b0301929d0252187e5 mit Tree 93dda6fca437a630045efdabf06f186fa06c107f. Dies ist eine Quell- und Evidenzintegration, keine Produktdomain-Abnahme.

## Lokal prüfen

Nach dem Entpacken im Wurzelverzeichnis ausführen:

```bash
python3 tools/qikvrt_zenodo_machine_proof.py --proof-bundle release/causal-distance-temporal-memory-2026-10-24/MACHINE_PROOF_BUNDLE.json
python3 release/causal-distance-temporal-memory-2026-10-24/validate_article_sources.py
```

Die erste Prüfung verwendet den unveränderten Repository-Validator und seine bytegebundenen v1/v2-Policykontrollen. Das v2-Feld zenodo_upload_authorized bezeichnet die technische Freigabe des Proof-Envelopes. Die tatsächliche Produktionsmutation benötigt daneben zwingend die gesonderte, zeitlich nach der Kandidatenrückgabe liegende Owner-Freigabe, den originalen Publisher, passende geschützte Zugangsdaten und die repositoryweite Verbrauchsquittung. Diese weiteren Bedingungen werden nicht aus einem erfolgreichen Proof-Check abgeleitet.

PUBLICATION_STATE.json dokumentiert den tatsächlichen Stand. EXACT_UPLOAD_DECISION_REQUEST.txt enthält die vom Original-Publisher verlangte kanonische Entscheidung für genau diese Kandidatenbytes. Sie ist eine vorbereitete Anfrage, kein bereits eingetroffenes Freigabeereignis. Es gibt hier absichtlich keine gefälschte OWNER_ZENODO_AUTHORIZATION.json.

PREPARED_UPLOAD_FILESET.json nennt genau die 20 vorgesehenen Zenodo-Dateien. Policykontrollen, frühere Entwürfe und Prüfwerkzeuge im äußeren Wiederherstellungspaket sind nicht automatisch weitere Upload-Dateien. Der Produktivpublisher darf keine fehlenden oder zusätzlichen Upload-Dateien stillschweigend akzeptieren.

## Leserouten und persönliches Profil

QIKVRT_Framework_Selbstvermessung_20261024.zip enthält die ausführbare Auswertung, ihren gebundenen Katalogsnapshot vom 11.10.2026, die statische Zehn-Modul-Auswahl, Personenprofile und sieben Leserouten. Nach dessen Entpacken:

```bash
python3 framework_measurement.py
python3 test_framework_measurement.py -v
```

Dieselbe Softwarestruktur lässt sich mit einem anderen ausdrücklich angegebenen Personenprofil wiederverwenden. Sie erhält dadurch keine Identitätsbestätigung und keine Rechte auf fremde persönliche Daten. Das Lesemodell ist ein begrenzter Twin-Baustein, keine vollständige produktive persönliche Instanz. Für eine solche Instanz bleiben SSO/benutzerseitige Verifikation, Datenrechte, Widerruf, Quellentrennung und native Terminal-/Transputer-Fortsetzung eigene Abnahmekriterien.

Die 61 Tests des ursprünglichen Wirkungs-/Distanzpakets und die sechs weiteren Tests der Navigation beziehen sich auf getrennte Gegenstände. Die gelieferten PDF-Bytes bleiben eingefroren; ein späterer Layout-Neuaufbau kann andere PDF-Metadaten und Hashes erzeugen und ersetzt deshalb nicht diese Publikationsfassung.

## Datenschutzmodi exportierter Testjournale

Ein ZIP-Entpacker kann die ursprünglichen Verzeichnismodi verwerfen. Vor dem Lesen des mitgelieferten historischen Testjournals deshalb im entpackten QIKVRT_Causal_Distance-Verzeichnis für die ausschließlich eigenen Exportkopien wieder lokale Privatsphäre setzen:

```python
from pathlib import Path
for directory in Path("evidence").glob("local-run-*/state"):
    directory.chmod(0o700)
    journal = directory / "temdd"
    journal.chmod(0o700)
    for file in journal.iterdir():
        if file.is_file() and not file.is_symlink():
            file.chmod(0o600)
```

Dies ändert keine Journalbytes und überträgt keine ursprüngliche Writer-Zulassung. Exportierte Journale werden weiterhin ausschließlich mit dem originalen schreibgeschützten Leser geprüft. Ein neuer Witness-Lauf benötigt stattdessen ein frisches eigenes Ausgabeverzeichnis; niemals einen historischen Journalpfad als neuen Writer starten.
