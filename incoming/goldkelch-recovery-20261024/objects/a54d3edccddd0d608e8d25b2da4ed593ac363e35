# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
START=$(date +%s 2>/dev/null || echo 0)
./build/qikvrt_verify --selftest-node-onboarding-testbed >/tmp/qikvrt_perf_nt.out
./build/qikvrt_verify --selftest-rest-api >/tmp/qikvrt_perf_ra.out
END=$(date +%s 2>/dev/null || echo 0)
DUR=$((END-START))
if [ "$DUR" -gt 10 ]; then echo "FAIL performance duration=$DUR"; exit 1; fi
echo "PASS full performance test layer duration_seconds=$DUR"
