# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-tcpip-autonomy >/tmp/qikvrt_selftest_tcpip_autonomy.out
grep 'PASS QIKVRT TCP/IP autonomy sanity selftest' /tmp/qikvrt_selftest_tcpip_autonomy.out >/dev/null
./build/qikvrt_verify --selftest-damage-containment >/tmp/qikvrt_selftest_damage_containment.out
grep 'PASS QIKVRT damage containment selftest' /tmp/qikvrt_selftest_damage_containment.out >/dev/null
grep 'No unauthorized scanning' docs/TCPIP_AUTONOMY_SANITY.md >/dev/null
grep 'No remote mutation' docs/TCPIP_AUTONOMY_SANITY.md >/dev/null
grep 'quarantine-required' docs/DAMAGE_CONTAINMENT.md >/dev/null
grep 'UNAUTHORIZED_SCANNING' qikvrt/gates/TCPIP_AUTONOMY_SANITY_GATES.json >/dev/null
grep 'REMOTE_MUTATION_WITHOUT_AUTHORIZATION' qikvrt/gates/TCPIP_AUTONOMY_SANITY_GATES.json >/dev/null
echo 'PASS tcpip autonomy and damage containment gates'
