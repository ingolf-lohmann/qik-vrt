# QIKVRT Repository Setup and Persistent Runtime Configuration / QIKVRT Repository-Setup und persistente Laufzeitkonfiguration

**Author / Urheber:** Ingolf Lohmann  
**Rights holder / Rechteinhaber:** Ingolf Lohmann or a legal entity designated by him  
**Software license / Softwarelizenz:** Apache-2.0  
**Documentation license / Dokumentationslizenz:** CC BY-NC-ND 4.0 unless otherwise stated

## Deutsch

Dieses Dokument definiert das generische Setup für ein QIKVRT-Repository. Beim ersten Setup-Lauf muss eine Repository-GUID erzeugt und lokal in `qikvrt/runtime/REPOSITORY_GUID.txt` persistiert werden. Zusätzlich werden GitHub Owner und GitHub Repository für das Zielrepository abgefragt, mit Defaultwerten versehen und in `qikvrt/config/REPOSITORY_TARGET.json` gespeichert.

Nach erfolgreichem Setup dürfen Onboarding, Deployment und Runtime nicht erneut interaktiv nach Owner/Repository fragen. Sie müssen die persistierte Konfiguration verwenden. Ein Node identifiziert sich gegenüber dem Seed mithilfe seiner Repository-GUID und der persistierten Seed-Zielparameter selbstständig. Remote-Mutation bleibt an Autorisierung und Token gebunden.

Defaultwerte für diese Rolle:

- role: `node`
- seed owner default: `Goldkelch`
- seed repository default: `qik-vrt`
- target owner default: `Goldkelch`
- target repository default: `qik-vrt-node`

## English

This document defines the generic setup for a QIKVRT repository. During the first setup run, a repository GUID must be generated and persisted locally in `qikvrt/runtime/REPOSITORY_GUID.txt`. In addition, GitHub owner and GitHub repository for the target repository are requested with defaults and persisted in `qikvrt/config/REPOSITORY_TARGET.json`.

After successful setup, onboarding, deployment, and runtime must not ask interactively for owner/repository again. They must use the persisted configuration. A node identifies itself to the seed by using its repository GUID and persisted seed target parameters. Remote mutation remains bound to authorization and token presence.

## Required persisted files / Erforderliche persistierte Dateien

- `qikvrt/runtime/REPOSITORY_GUID.txt`
- `qikvrt/config/REPOSITORY_TARGET.json`
- `qikvrt/config/ONBOARDING.json`
- `qikvrt/runtime/setup/SETUP_RESULT.tsv`
- `qikvrt/runtime/setup/SETUP_RESULT.json`
- `qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json`

## Footer / Fußzeile

QIKVRT | Ingolf Lohmann | Apache-2.0 for software | CC BY-NC-ND 4.0 for documentation | NO_TRACEABILITY_NO_FINAL_PASS
