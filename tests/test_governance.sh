# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
BIN="./build/qikvrt_verify"
$BIN --selftest-governance | grep 'PASS QIKVRT constitutional governance selftest v2.13' >/dev/null
grep 'No final-pass is valid if assertion class is missing' docs/EVIDENCE_AND_ASSERTION_CLASSES.md >/dev/null
grep 'Multicast delivery' docs/GOVERNANCE_PROCESS.md >/dev/null
grep 'Anti-surveillance rule' docs/PRIVACY_PROPORTIONALITY_EMERGENCY.md >/dev/null
grep 'GOV-LIFECYCLE' docs/ARTICLE_IMPLEMENTATION_MATRIX.md >/dev/null
grep 'CONSTITUTIONAL_GOVERNANCE_GATES' qikvrt/gates/CONSTITUTIONAL_GOVERNANCE_GATES.json >/dev/null || grep 'constitutional_governance_gates' qikvrt/gates/CONSTITUTIONAL_GOVERNANCE_GATES.json >/dev/null
echo 'PASS governance gates'
