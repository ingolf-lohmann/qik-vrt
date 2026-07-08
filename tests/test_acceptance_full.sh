# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --verify docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md >/tmp/qikvrt_acceptance_doc.out
./build/qikvrt_verify --validate-root-layout . >/tmp/qikvrt_acceptance_root.out
./build/qikvrt_verify --selftest-seed-node-delivery >/tmp/qikvrt_acceptance_delivery.out
sh tests/test_hashes.sh
echo 'PASS full acceptance test layer'
