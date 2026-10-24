# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-zip-layout >/tmp/qikvrt_selftest_zip_layout.out
./build/qikvrt_verify --validate-root-layout . >/tmp/qikvrt_validate_root_layout.out
test -s README.md
test -s Makefile
test -s SHA256SUMS.txt
test -d docs
test -d src
test -d tests
test -d qikvrt
grep -q 'NO_WRAPPER_ONLY_EXTRACTION' docs/ZIP_LAYOUT_COMPATIBILITY.md
echo 'PASS zip layout compatibility gates'
