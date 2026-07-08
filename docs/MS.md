# QIKVRT Mutable State Integrity / Veränderlicher Laufzeitstatus

Version: 2.13.4

Deutsch: Dateien, die waehrend Setup, Lizenzakzeptanz, GUID-Erzeugung, Zielkonfiguration, Onboarding oder Deploy erzeugt oder ueberschrieben werden, sind auditierbarer Laufzeitstatus. Sie duerfen nicht als unveraenderliche Release-Dateien in SHA256SUMS.txt gefuehrt werden.

English: Files created or overwritten during setup, license acceptance, GUID generation, target configuration, onboarding or deployment are auditable runtime state. They must not be listed as immutable release files in SHA256SUMS.txt.

Mutable runtime/config examples:

- qikvrt/config/LICENSE_ACCEPTED.json
- qikvrt/config/REPOSITORY_TARGET.json
- qikvrt/config/ONBOARDING.json
- qikvrt/runtime/REPOSITORY_GUID.txt
- qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json
- qikvrt/runtime/**

Author / Urheber: Ingolf Lohmann  
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him  
Software license: Apache-2.0  
Non-software/docs license: CC BY-NC-ND 4.0 unless otherwise stated

Footer / Fusszeile: QIKVRT V2.13.4 | Mutable state is audit evidence, not immutable release content.

DE: Die Laufzeit-Akzeptanzledgerdatei qikvrt/ledger/LICENSE_RUNTIME_ACCEPTANCE.jsonl ist mutable Audit-Evidence und darf nicht in SHA256SUMS.txt stehen.
EN: The runtime acceptance ledger file qikvrt/ledger/LICENSE_RUNTIME_ACCEPTANCE.jsonl is mutable audit evidence and must not be listed in SHA256SUMS.txt.
