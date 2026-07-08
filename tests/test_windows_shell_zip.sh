# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-windows-shell-zip >/tmp/qikvrt_selftest_windows_shell_zip.out
grep -q 'Windows Shell ZIP' docs/WINDOWS_SHELL_ZIP_COMPATIBILITY.md
grep -q 'WINDOWS_SHELL_ZIP_EXTRACTION_EMPTY_AFTER_FLAT_REPAIR' docs/WINDOWS_SHELL_ZIP_COMPATIBILITY.md
grep -q 'NO_WINDOWS_SHELL_EMPTY_EXTRACTION_FINAL_PASS' docs/WINDOWS_SHELL_ZIP_COMPATIBILITY.md
test -s qikvrt/gates/WINDOWS_SHELL_ZIP_COMPATIBILITY_GATES.json
echo 'PASS Windows Shell ZIP compatibility gates'
