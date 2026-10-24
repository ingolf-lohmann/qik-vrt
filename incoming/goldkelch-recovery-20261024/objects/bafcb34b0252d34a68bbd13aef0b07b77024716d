# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
grep -q "QIKVRT Node Onboarding" "$ROOT/docs/NO.md"
grep -q "generic node profile" "$ROOT/docs/NO.md"
grep -q "no person-bound default" "$ROOT/docs/NO.md"
grep -q "privacy-preserved evidence" "$ROOT/docs/NO.md"
grep -q "GENERIC_NODE_PROFILE" "$ROOT/qikvrt/gates/NO.json"
grep -q "INGOLF_NODE_DEFAULT" "$ROOT/qikvrt/gates/NO.json"
grep -q "generic-qikvrt-node" "$ROOT/qikvrt/manifests/NO.json"
grep -q "NODE_ONBOARDING_REFERENCE" "$ROOT/qikvrt/ledger/NO.jsonl"
echo 'PASS node onboarding gates'
