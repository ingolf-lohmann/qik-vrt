<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Erkundung mit Gedächtnis: der Irrgarten-Abschluss
## Modellbeweis, Gegenbeispiele und nachprüfbare Grenzen

Publication ID: `qikvrt-labyrinth-closure-20261004-v1`
Publication Index State: `repository_candidate_kernel_verified_owner_review_pending`

Idee, Zweck und Auftrag: Ingolf Lohmann. Ausarbeitung und Code: OpenAI Codex,
künstliche Kognition. Die Bestätigung der früheren Zusammenfassung ist keine
Annahmeentscheidung über die neuen Kandidatenbytes.

[Vollständiger Beweis](PROOF.md) · [Aussagenregister](CLAIM_MATRIX.json) ·
[Finite Prüfquittung](TEST_RECEIPT.json) · [Kernelplan](KERNEL_PROOF_PLAN.json) · [Kernelquittung](KERNEL_RECEIPT.json)

Reproduktion: `python3 -B check_labyrinth.py --output TEST_RECEIPT.json`.
Kernelprüfung: dieselbe Referenzprüfung mit `--lean /absoluter/pfad/lean`
und `--kernel-output /absoluter/pfad/KERNEL_RECEIPT.json`.
Der bestehende Workflow `qikvrt_manuscript_proof.yml` liefert das Artifact
`qikvrt-labyrinth-closure-evidence-<run_id>-<attempt>`.

Der einfache Zufallslauf findet unter endlichem statischem Zusammenhang und
gleichverteilter Nachbarwahl alle Kanten fast sicher. Ein endliches Zeitbudget
ist keine sichere Null- oder Eindeutigkeitsentscheidung. Die Ergänzung mit
vollständigem Nachbarorakel und offener Arbeitsliste terminiert und bestimmt
genau die Durchgänge der erreichbaren Komponente. Globale Aussagen brauchen
eine zusätzliche Abdeckungsbindung.

Wiederverwendung: Das Minimal Recovery Theorem und die vorhandene Formalisierung
`QIKVRTFormalization/Decision/ObservationSufficiency.lean` behandeln die
allgemeine Entscheidungssuffizienz. Sie enthalten weder die konkrete
Durchgangsidentität noch die vollständige lokale Irrgarten-Erkundung. Dieses
Paket ergänzt genau diese Spezialisierung. Cacheprüfung, Bootloader,
Integritätsgenerator, Publikationsindex und Kernelworkflow bleiben die
bestehenden Repository-Verfahren; es wird kein paralleler Runtimeweg angelegt.

Nicht abgenommen: Python-Refinement für beliebige Graphen, Produktkonformität,
Authority/Mirror-Gleichheit, dauerhafte Laufzeitinstallation und Zenodo-
Produktion. Details stehen im Aussagenregister und im Arbeitsnachweis.
