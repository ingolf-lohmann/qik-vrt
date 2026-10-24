# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -R "No unauthorized scanning\|no unauthorized scanning" docs qikvrt tests >/tmp/qikvrt_sec_scan.out
grep -R "No self-propagation\|no self-propagation" docs qikvrt tests >/tmp/qikvrt_sec_prop.out
grep -R "no remote mutation\|No remote mutation" docs qikvrt tests >/tmp/qikvrt_sec_mut.out
./build/qikvrt_verify --selftest-damage-containment >/tmp/qikvrt_sec_damage.out
./build/qikvrt_verify --selftest-windows-shell-zip >/tmp/qikvrt_sec_zip.out
echo 'PASS full security test layer'
