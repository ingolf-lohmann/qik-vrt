# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Author / Urheber: Ingolf Lohmann' src/main.c
grep -q 'Author / Urheber: Ingolf Lohmann' src/qikvrt.c
grep -q 'Author / Urheber: Ingolf Lohmann' include/qikvrt.h
grep -q 'QIKVRT License Footer' docs/FT.md
grep -q 'QIKVRT License Footer' docs/SD.md
grep -q 'LICENSE_COPYRIGHT_VISIBILITY_GATE' qikvrt/gates/LC.json
echo 'PASS license copyright header footer gates'
