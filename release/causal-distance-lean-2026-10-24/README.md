# Kausale Distanz: Lean-Anschluss und Zenodo-Kandidat

Publikationsidentität: qikvrt-causal-distance-lean-20261024. Version 2.0.0-lean.
Idee, Architektur und wissenschaftliche Verantwortung: Ingolf Lohmann. Formalisierung, Texte und technische Prüfung: Codex im autorisierten Auftrag.

Die Quelle ist über PR 597 auf Main a1a2204f429bcab7a184afaf51a57b7de03d4ee7 integriert. Der native vollständige Repository-Test gilt für b1863b75e29cb455b88740ade4441312af9caa8f und den byteidentischen Main-Baum 184adc9c40b27cce1be4995d2eae895d3fbbd2ee. MAIN_INTEGRATION.json bindet die Beobachtung.

36 neue Lean-Theoreme sind an die ursprünglichen Effect-ACK- und Speichermodelle angeschlossen. PUBLICATION_KERNEL_RECEIPT.json normalisiert die erhaltene native Kernelquittung; NATIVE_KERNEL_RECEIPT.json bewahrt deren Originalbytes. Die Normalisierung behauptet keinen zusätzlichen Kernel-Lauf. Historische neun Speichertheoreme werden nicht erneut gezählt. Formale Modellbeweise, lokale Laufzeitzeugnisse, Tests, Interpretation und offene empirische Aufgaben bleiben getrennt.

Fachartikel.md und die wissenschaftliche PDF enthalten den Fachartikel. Prosaartikel.txt enthält den ausführlichen Lesetext einschließlich Quellenanhang. QIKVRT_Prosa_Vorlesetext.txt ist die reine Vorlesefassung ohne Quellenanhang und Webadressen. Die Prosa-PDF ist ein gesondertes Lesedokument.

## Exakte Veröffentlichung

PREPARED_UPLOAD_FILESET.json enthält die 28 exakt vorgesehenen Dateien. MACHINE_PROOF_BUNDLE.json ordnet 56 Claims ein und besteht den unveränderten aktiven v2-Validator. Der Validatorwert zenodo_upload_authorized beschreibt allein die v2-Proof-Vollständigkeit; er ersetzt weder die separate natürliche Owner-Entscheidung noch den tatsächlichen Zenodo-Effekt. PUBLICATION_STATE.json enthält den tatsächlichen Publikationsstand.

CHANGE_NOTICE.md und PREPUBLICATION_RETURN_RECEIPT.json binden die sichtbar zurückgelieferte Fassung einschließlich der unveränderten Vorarbeit. Metadaten und der neue Dateisatz wurden nach der allgemeinen Aufgabenfreigabe ausgearbeitet. Die in policy/ZENODO_MACHINE_PROOF_BEFORE_PUBLICATION.md, Abschnitt 5, ausdrücklich verlangte nachfolgende kanonische Einzelfreigabe steht deshalb noch aus. EXACT_UPLOAD_DECISION_REQUEST.txt ist eine Entscheidungsanfrage, keine erhaltene Autorisierung. Es gibt in diesem Kandidaten bewusst keine erfundene OWNER_ZENODO_AUTHORIZATION.json und keinen ausführbaren Queue-Auftrag.

Nach dem tatsächlichen Eingang genau dieser Entscheidung: Original-Publisher-Autorisierung gegen den realen eingefrorenen Kandidatencommit binden; originalen v2-Manifest- und Author-Validator ausführen; den vorhandenen state/publication_requests-Eingang über den bestehenden Review-/Main-Prozess benutzen. Die bestehende qikvrt_publication_router.yml erledigt den einmaligen Dispatch zum ursprünglichen Publisher, den öffentlichen Dateiredownload, DOI-Erfassung und den anschließenden Review-Carrier für Quittung, Katalog und Website-Assets. Keine Ersatzpipeline, Timer oder Änderung der eingefrorenen v2-Policy. Website-Auslieferung auf raumzeitterminal.de bleibt separat nachzuweisen.

## Lokale Prüfung

Im Repository-Wurzelverzeichnis:

```sh
python3 -B tools/qikvrt_zenodo_machine_proof.py --proof-bundle release/causal-distance-lean-2026-10-24/MACHINE_PROOF_BUNDLE.json
python3 -B release/causal-distance-lean-2026-10-24/validate_article_sources.py
```

Der erste Befehl ist rein lesend. Der Quellenprüfer regeneriert seine Prüfquittung und darf in einem bereits eingefrorenen Publikationskandidaten nur in einer separaten Prüfarbeitskopie ausgeführt werden. Die exakte Dateimenge lässt sich durch wiederholte --upload-path-Argumente aus PREPARED_UPLOAD_FILESET.json mitprüfen.

COLD_RESTORE_CHECK.json belegt die Prüfung nach Wiederherstellung aller notwendigen Dateien in einem unabhängigen temporären Verzeichnis einschließlich des exakten Upload-Dateisatzes. PUBLICATION_NEGATIVE_CONTROLS.json dokumentiert die Ablehnung von Kandidaten-Hashänderung, entfernter Kernelquittung, als Tatsache formulierter offener Aussage und fehlendem Upload-Mitglied. Das ZIP enthält auch die acht unveränderten Vorgängerdateien und die sechs eingefrorenen v1/v2-Vertragsdateien.

Die öffentliche Anschlussarbeit ist als isSupplementTo zu https://doi.org/10.5281/zenodo.21711193 vorgesehen. Einstieg in den Korpus: https://doi.org/10.5281/zenodo.21888130. Für diese neue Arbeit wird bis zum tatsächlichen Publikations- und Downloadnachweis kein DOI behauptet.

Lizenzgrenzen der ursprünglichen Artikel, Architektur und Implementierung bleiben erhalten; die enthaltenen Original-Lizenztexte gelten für ihre jeweiligen Teile.
