# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
for p in   qikvrt/config/LICENSE_ACCEPTED.json   qikvrt/config/REPOSITORY_TARGET.json   qikvrt/config/ONBOARDING.json   qikvrt/runtime/REPOSITORY_GUID.txt   qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json   qikvrt/ledger/LICENSE_RUNTIME_ACCEPTANCE.jsonl
do
  if grep -F "  $p" SHA256SUMS.txt >/dev/null 2>&1 || grep -F "$p" SHA256SUMS.txt >/dev/null 2>&1; then
    echo "BLOCK mutable runtime/config file in SHA256SUMS: $p" >&2
    exit 1
  fi
done
grep -q 'QIKVRT_MUTABLE_STATE_INTEGRITY_GATE' qikvrt/gates/MS.json
grep -q 'QIKVRT_MUTABLE_STATE_INTEGRITY_MANIFEST' qikvrt/manifests/MS.json
grep -q 'MUTABLE_STATE_INTEGRITY_REFERENCE' qikvrt/ledger/MS.jsonl
printf '%s
' 'PASS mutable state integrity gates'
