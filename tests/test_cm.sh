# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Article Claim Matrix' docs/CM.md
grep -q 'IMPLEMENTED_AND_LOCAL_TESTED' docs/CM.md
grep -q 'FUTURE_APPLICATION' docs/CM.md
grep -q 'NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE' docs/CM.md
./build/qikvrt_verify --selftest-claim-matrix >/tmp/qikvrt_cm_selftest.out
echo 'PASS article claim matrix gates'
