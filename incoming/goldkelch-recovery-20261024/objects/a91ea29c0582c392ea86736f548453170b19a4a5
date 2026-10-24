<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

# QIKVRT GitHub Deployment / GitHub-Deployment

## Deutsch
Dieses Repository enthält generische Deployment-Skripte für Windows und POSIX. Sie dürfen GitHub Owner und GitHub Repository nicht hart verdrahten. Die Werte werden zur Laufzeit aus Umgebungsvariablen, aus `git remote origin` oder durch interaktive Abfrage ermittelt.

## English
This repository contains generic deployment scripts for Windows and POSIX. They must not hard-code the GitHub owner or repository. Values are resolved at runtime from environment variables, from `git remote origin`, or by interactive prompt.

## Runtime Inputs / Laufzeiteingaben
- `QIKVRT_GITHUB_OWNER`
- `QIKVRT_GITHUB_REPO`
- `QIKVRT_RELEASE_TAG`
- `QIKVRT_RELEASE_TITLE`
- `GITHUB_TOKEN`

## Scripts / Skripte
- `QIKVRT.cmd deploy`
- `QIKVRT.sh deploy`
- `tools/gh_deploy.ps1`
- `tools/gh_deploy.sh`

## Boundary / Grenze
no remote mutation without authorization. / Keine Remote-Mutation ohne Autorisierung.

The scripts may create or update a GitHub Release only when explicitly run with an authorized token. They do not scan the internet, do not self-propagate, and do not mutate remote repositories without authorization.

Die Skripte dürfen nur mit ausdrücklich autorisiertem Token ein GitHub Release erstellen oder aktualisieren. Sie scannen nicht das Internet, verbreiten sich nicht selbst und verändern keine entfernten Repositories ohne Autorisierung.


<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->


## Deploy staging recursion prevention / Schutz vor Staging-Rekursion

Deutsch: Deployment-Pakete dürfen `qikvrt/runtime/deploy`, `package_staging`, `build` und `.git` niemals in das neu erzeugte Release-Asset kopieren. Dadurch wird rekursives Self-Copying verhindert.

English: Deployment packages must never copy `qikvrt/runtime/deploy`, `package_staging`, `build`, or `.git` into the generated release asset. This prevents recursive self-copying.

Gate: `DEPLOY_PACKAGE_STAGING_RECURSION_PREVENTION = PASS`


## DE/EN: Unified entrypoint and token prompt / Einheitlicher Einstiegspunkt und Token-Abfrage

Deutsch: Das GitHub-Deployment wird ueber `QIKVRT.cmd deploy` oder `QIKVRT.sh deploy` gestartet. Falls `GITHUB_TOKEN` nicht gesetzt ist und kein Dry-Run angefordert wurde, fragt `tools/gh_deploy.ps1` bzw. `tools/gh_deploy.sh` den Token zur Laufzeit ab. Der Token wird nicht persistiert.

English: GitHub deployment is started through `QIKVRT.cmd deploy` or `QIKVRT.sh deploy`. If `GITHUB_TOKEN` is not set and dry-run mode is not requested, `tools/gh_deploy.ps1` or `tools/gh_deploy.sh` prompts for the token at runtime. The token is not persisted.

---

QIKVRT bilingual footer / Zweisprachiger Footer. Author / Urheber: Ingolf Lohmann. Software license: Apache-2.0. Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
