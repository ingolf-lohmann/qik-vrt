<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Wiederanschluss der 400-Byte-Signaturen-Studie, 19. Oktober 2026

Die eingefrorene 20-seitige PDF im übergeordneten Verzeichnis bleibt unverändert:
SHA-256 `c10f65ca2e70db052bf66b250114130bfedd4a5f423e255a5e29a1fc9c7e12ad`,
238186 Byte, Gitblob `302046b1347dfac36462f12066fdb0177999b388`.

Das bereits erzeugte Original-Evidenzpaket vom 2. Oktober ist als
`original-evidence-20261002.zip` wieder angeschlossen. Seine 1736349 Byte und
SHA-256 `7d3f856c7aaa558895d45ed4b95cfb64a504300d3ac4836aed626616f2d6e7f3`
stimmen mit Referenz R01 der Synthese und dem erhaltenen Fortsetzungsarchiv überein.
Alle 58 Mitglieder sind erhalten; alle 57 Zeilen der ursprünglichen SHA256SUMS
und alle 55 ursprünglichen Fileset-Bindungen wurden geprüft. Darin liegen die
Originale PAPER.md, CLAIM_MATRIX.json mit 24 Claims, beide 400-Byte-Frames,
Saat, Rohmessungen, historische Firefox-Belege, Reproduktionsquellen, Errata,
Änderungsvermerk, Metadaten und IETF-04-XML. Keine Arbeit wurde neu geschrieben.

## Versionen und wissenschaftliche Grenzen

Die separat erhaltene Dateifassung unter `versions/` hat 263159 Byte und SHA-256
`1de4565bd12f9a284cc99061e04e0d260cb37d788218f5e1f3a3bb4272395f61`.
Ihr extrahierter Text und alle 20 bei 72 dpi gerenderten Seiten stimmen mit der
Repository-PDF überein. Sie ist trotzdem kein bytegleicher Ersatz.

Die 43 gedruckten Aussagen sind im neuen CLAIM_RECONCILIATION-Index transkribiert.
Das ist eine ausdrücklich gekennzeichnete Ableitung aus der unveränderten PDF,
keine Wiederauffindung der ursprünglichen 43-Claim-JSON oder von PAPER_DE.md.
Diese vollständigen technischen Quellen vom 5. Oktober bleiben nicht lokalisiert.
Die 24 Original-Claimdatensätze vom 2. Oktober bleiben unverändert im Original-ZIP.
Neue Metadaten ersetzen keine verlorenen Originale und keinen produktionsfähigen Proof.

Die 56 Messläufe und acht Aufwärmläufe stammen vom lokalen Versuch am 2. Oktober,
HEAD `6a1098699d096806958b9c3b50a97d205b8110e9`. Ihre Gruppenmediane wurden aus
den unveränderten Rohdaten erneut berechnet: starke Skalierung 347,480389 auf
97,760355 ms, Faktor 3,554410; aggregierte CPU-Zeit steigt um 24,124851 Prozent.
Das ist keine Energieeinsparungsmessung und kein allgemeiner KI-Benchmark.
Unbegrenzte Beschleunigung, globale Optimalität und historische Überlegenheit
bleiben unbewiesen; die Paradigmenbewertung bleibt dem Owner zugeschrieben.
Transportframes sind keine kryptographischen Signaturen. Historische Rollen
werden nicht auf die aktuelle Authority/Mirror-Zuordnung übertragen.

Der Linux/Firefox-Beleg R02 gehört zu einem anderen HEAD/TREE und Run 36959391916,
Versuch 1. Sein HOLD für vollständige Mesh-Schließung bleibt bestehen.
R03/R04 sind historische Writer-/Pipelinebefunde vom 5. Oktober; sie sind keine
aktuellen Messungen und keine Veröffentlichungsgates dieses neuen Branchstands.

## IETF und Zenodo

Das ursprüngliche -04-XML ist unverändert wiedergefunden: 57308 Byte,
SHA-256 `a6d63859dfca44b19c59d5f6bfb9ed217bcb636cf763ffd3b46c74322c16ec3d`,
Gitblob `4b43c9fe04dd021f0c5166a0bcb6f1a951927f02`.
Neue Text-/HTML-Ableitungen wurden mit der vorhandenen hashgebundenen
xml2rfc-3.34.0-Toolchain offline erzeugt. Das Originaldatum 2. Oktober bleibt
sichtbar; die Datumswarnung ist dokumentiert. Alle Artwork-Blöcke stimmen mit
öffentlich bytegleich gelesener Revision -03 überein. Das Datatracker-API nennt
am 19. Oktober weiterhin Revision 03; der direkte -04-Archivabruf liefert 404.
Erfolgreiches Rendering ist keine Einreichung oder IETF-Annahme.

Die öffentliche Zenodo-Titelsuche liefert null Treffer. Das ist eine begrenzte
Suchbeobachtung und kein Beweis, dass weltweit kein Record existiert. Ein
öffentlich bytegleich verifizierter Record für die eingefrorene PDF ist nicht
zugeordnet. Die bestehenden separaten Quellenrecords bleiben getrennt.

PUBLICATION_GATE_STATUS.json bewahrt die Aufgabe und die vorhandene Freigabe
zur Vorbereitung. Es wurde keine passende spätere AUTHORIZE_EXACT_UPLOAD- oder
exakte IETF-04-Einreichungsentscheidung gefunden. Das historische Proof-Bundle
ist ausdrücklich DRAFT. Fehlende vollständige Originalquellen, v2-Proof,
kandidatenspezifische Rücklieferung und exakte Freigabe bleiben offene Gates.
Kein Produktionsupload, Submit, Release, Merge oder Mirror-Gleichstand wird
behauptet. Die vorhandenen Publisher, Prüfungen und Verbrauchsref-Regeln bleiben
maßgeblich; es wurde kein Ersatzpublisher oder Scheduler eingerichtet.

## Reproduzieren

1. Im Verzeichnis dieser README `sha256sum -c SHA256SUMS` ausführen.
2. `original-evidence-20261002.zip` in ein neues Verzeichnis entpacken und dort
   `sha256sum -c SHA256SUMS` ausführen. Historische Dateien unverändert lassen.
3. In dessen `reproduce/` die originale Testanweisung aus README.md ausführen:
   `python3 -B -m unittest tests.test_qikvrt_standpoint_codex tests.test_qikvrt_codec`.
4. Für neue Messungen ausschließlich eine neue Kopie des Reproduktionsordners
   verwenden. `measure_scaling.py` erzeugt neue Beobachtungen unter der dort
   dokumentierten Umgebung; sie ersetzen niemals die historischen Rohmessungen.
5. Für IETF die vorhandenen hashgepinnten Anforderungen in einer isolierten
   Umgebung installieren und xml2rfc mit `--v3 --text` bzw. `--html`,
   `--no-network --skip-config-files --warn-bare-unicode` auf das ORIGINAL-XML
   anwenden. Ausgabe und Original getrennt halten.

Konzept, Auftrag und Owner-Bewertungen: Ingolf Lohmann. Historische und neue
technische Ausführung, Quellenvergleich, Transkription und Prüfung: OpenAI Codex;
diese Herkunftsangabe ist eine Plattformzuordnung, kein kryptographischer
Modell- oder Personenbeweis. Dokumentation/Evidenz CC-BY-NC-ND-4.0, konkrete
Implementierung PolyForm-Noncommercial-1.0.0; IETF ipr=trust200902 bleibt erhalten.

Präzisionshinweis C43: Die unveränderte PDF nennt rund 24,13 Prozent mehr CPU-Zeit. Die Originalmediane ergeben 24,1248514191583 Prozent; auf zwei Dezimalstellen gerundet sind es 24,12 Prozent. Der neue Index dokumentiert diese kleine Rundungsabweichung sichtbar.
