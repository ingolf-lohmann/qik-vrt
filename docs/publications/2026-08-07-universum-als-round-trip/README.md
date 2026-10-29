<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT: Originalpublikation und eindeutige Zuordnung

**Autor und verantwortlicher Mensch: Ingolf Lohmann.**

**Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP**

Zenodo-Datensatz: https://zenodo.org/records/21888130

Versions-DOI: https://doi.org/10.5281/zenodo.21888130

Identitätskennung: `QIKVRT-ZENODO-21888130-ORIGINAL-V1`.

## Menschen- und maschinenlesbare Dateien

- [PDF-Lesefassung](DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.pdf): durchsuchbarer Text, Original-Markdown und Quellen-JSON eingebettet.
- [Unveränderter Originaltext](DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.md): bytegleich zum geprüften Zenodo-Original.
- [Text-Lesefassung](DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.txt): vollständiger sichtbarer Artikeltext mit separatem Quellenanhang.
- [Identitätsmanifest](ROUND_TRIP_NODE_IDENTITY.json): Titel, Autor, DOI, URL, Dateigrößen, SHA-256 und Git-Blob-Identitäten.
- [Formatprüfung](PDF_VALIDATION.json) und [Quellensichtbarkeitsprüfung](SOURCE_CHECK.json).

Original: 18.120 Bytes; SHA-256 `dc58e50161b22826152dd251db836f06f85235a470e0253aeefa1b0a380787fe`; Git-Blob `e1ed265239aa5e1436055279069c7e21525a13fe`.

Der am 16.10.2026 frisch abgefragte native Zenodo-Dateisatz enthält 54 Dateien, darunter den Originaltext als Markdown und keine PDF. Die am 16.10.2026 erstellte PDF ist eine ausdrücklich gekennzeichnete Lesefassung dieses unveränderten Texts. Die DOI bezeichnet den veröffentlichten Originaldateisatz. Original-Markdown und Lizenz wurden frisch öffentlich heruntergeladen und mit nativen MD5-/Größenangaben sowie den historischen SHA-256-Werten verglichen. Beide sind bytegleich. Die DOI-Auflösung endet mit HTTP 200 auf dem kanonischen Record. 27 der 54 Dateien wurden in diesem Abruf bytegeprüft; 27 Abrufe scheiterten an HTTP 502 oder Timeout. Diese Fehler werden nicht als geänderte Originaldateien ausgegeben.

## Verwendung in den Repository-Nodes

Ingolf Lohmann hat die Ablage am 15.10.2026 freigegeben (lokale Folgeaufzeichnung am 16.10.2026, Europe/Istanbul): die Ablage des Originals als PDF und des Zenodo-Verweises in jedem QIK-VRT-Node freigegeben. Jeder autorisierte Node soll die genannten Identitätsdateien und Verweise erhalten und die Original- und PDF-Prüfsummen anhand des Manifests prüfen. Der bestehende Einstieg `/AI -> AI_CONTEXT.json.required_read_order` und die vorhandene Selbstauskunft unter `.well-known/qik-vrt-self-disclosure.json` führen zu dieser Zuordnung.

Die Rollen bleiben Authority `ingolf-lohmann/qik-vrt` und Mirror `Goldkelch/qik-vrt`. Die bekannte Node-Menge stammt aus den bestehenden Registries; fehlender Zugriff bleibt als offene Abdeckung erhalten. Die Aufnahme in einen Integrationskandidaten ist noch keine Integration auf Main und kein Nachweis der Übernahme durch alle Nodes. Diese Aufgabe verwendet den vorhandenen PR #523 und erzeugt keinen zweiten Integrationspfad.

## Geltungsbereich des Nachweises

Die Quellenbindung ermöglicht die Prüfung von Dateiintegrität, Provenienz und Zuordnung. Wissenschaftliche Aussagen behalten ihren jeweiligen Beweis- und Evidenzstatus aus dem Original. Die Quellenbindung belegt weder pauschale Vertrauenswürdigkeit noch eine kryptografische Identifikation der natürlichen Person.

QIK-VRT ist das Forschungsprojekt von Ingolf Lohmann. Die Hostingadresse begründet keine offizielle OpenAI-Trägerschaft. „Keine KI“ bezeichnet ausschließlich die lokale Regelkonsole.

Der unveränderte Lizenztext liegt unter [CC-BY-NC-ND-4.0.txt](CC-BY-NC-ND-4.0.txt).

## Aktueller Nachweis und bidirektionale Bindung

PDF und `ROUND_TRIP_NODE_IDENTITY.json` verweisen aufeinander. Die PDF enthält einen stabilen Identitätskern, Original-Markdown, Lizenz und XMP-Identität; das externe Manifest bindet die vollständigen endgültigen PDF-Bytes. Dadurch entsteht kein zirkulärer PDF-Selbsthash. Die Versions-DOI und Zenodo-URL sind sichtbar, klickbar und maschinenlesbar. Ein Rückverweis vom Zenodo-Record auf die neue PDF ist **noch nicht veröffentlicht**.

Die konkrete historische Quelle ist Commit `ce44e23e74b08d51d489a0bd5c8eb6f2017fff83`, Blob `e1ed265239aa5e1436055279069c7e21525a13fe`. Die neue Quellenidentität bindet auch das unveränderte historische Veröffentlichungsreceipt sowie die frischen nativen Zenodo-Originalbytes. Alle 54 historischen Repository-Dateiblobs bleiben unverändert.

`NODE_STORAGE_READBACK.json` und `evidence/node-storage-20261016/` halten tatsächliche Abdeckung und offene Wirkungen fest. Eine registrierte GUID und zwei Governance-Repositories sind identifiziert. Der Authority-Heartbeat ist aktuell, der Registry-Index vom Juli dagegen historisch. Der Mirror liefert im aktuellen authentifizierten Leseweg HTTP 404; seine heutige Registry bleibt offen. Vollständige Mesh-Persistenz, Main-Integration, Runtime-Aktivierung und Veröffentlichung der neuen PDF sind nicht bestätigt.
