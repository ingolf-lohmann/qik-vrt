# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-ontology >/tmp/qikvrt_unit_ontology.out
./build/qikvrt_verify --selftest-rest-api >/tmp/qikvrt_unit_rest.out
./build/qikvrt_verify --selftest-unified-node-core >/tmp/qikvrt_unit_core.out
./build/qikvrt_verify --selftest-license-visibility >/tmp/qikvrt_unit_license.out
./build/qikvrt_verify --selftest-full-test-env >/tmp/qikvrt_unit_ft.out
echo 'PASS full unit test layer'
