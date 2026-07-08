<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

# GD Reference / GD-Referenz

Deutsch: Generische GitHub-Deployment-Skripte für Rolle `node` vorhanden und testbar.

English: Generic GitHub deployment scripts for role `node` are present and testable.


<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->


## Deploy staging recursion prevention / Schutz vor Staging-Rekursion

Deutsch: Deployment-Pakete dürfen `qikvrt/runtime/deploy`, `package_staging`, `build` und `.git` niemals in das neu erzeugte Release-Asset kopieren. Dadurch wird rekursives Self-Copying verhindert.

English: Deployment packages must never copy `qikvrt/runtime/deploy`, `package_staging`, `build`, or `.git` into the generated release asset. This prevents recursive self-copying.

Gate: `DEPLOY_PACKAGE_STAGING_RECURSION_PREVENTION = PASS`


Runtime state rule / Laufzeitstatus-Regel: runtime generated files are excluded from immutable SHA256SUMS and must be created by setup/deploy/runtime scripts at execution time.
