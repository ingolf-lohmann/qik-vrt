# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Live Evidence Closure' docs/LE.md
grep -q 'NO_FALSE_LIVE_PASS' docs/LE.md
grep -q 'NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE' docs/LE.md
test -f tools/gh_live_fetch.sh
grep -q 'external live GitHub seed fetch' tools/gh_live_fetch.sh
./build/qikvrt_verify --selftest-live-evidence >/tmp/qikvrt_le_selftest.out
./build/qikvrt_verify --validate-live-evidence qikvrt/evidence/GH_WEB_REF.json >/tmp/qikvrt_le_file.out
echo 'PASS live evidence closure gates'
