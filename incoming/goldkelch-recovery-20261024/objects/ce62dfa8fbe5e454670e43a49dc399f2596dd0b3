# QIKVRT Artifact Header
# Deutsch: Test für zweisprachige Dokumentation.
# English: Test for bilingual documentation.
# Author / Urheber: Ingolf Lohmann
# License: Apache-2.0 for scripts unless otherwise stated.
#!/bin/sh
set -eu
[ -s docs/BI.md ]
grep -q 'Deutsch' docs/BI.md
grep -q 'English' docs/BI.md
grep -q 'QIKVRT-DE-EN-DOC-HEADER' README.md
grep -q 'QIKVRT-DE-EN-DOC-FOOTER' README.md
grep -q 'Author / Urheber: Ingolf Lohmann' docs/BI.md
grep -q 'Apache-2.0' docs/BI.md
grep -q 'CC BY-NC-ND 4.0' docs/BI.md
echo 'PASS bilingual documentation gates'
