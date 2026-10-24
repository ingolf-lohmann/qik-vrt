# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-autonomous-discovery >/tmp/qikvrt_selftest_autonomous_discovery.out
grep 'PASS QIKVRT autonomous discovery operation selftest' /tmp/qikvrt_selftest_autonomous_discovery.out >/dev/null
grep 'impossibility boundary' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'no third-party service' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'authorized seed peer' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'local multicast' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'no global address scanning' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'sanity selftest requestable' docs/AUTONOMOUS_INTERNET_DISCOVERY.md >/dev/null
grep 'NO_FINAL_PASS_WITHOUT_AUTONOMOUS_DISCOVERY_OPERATION_GATES' qikvrt/gates/AUTONOMOUS_DISCOVERY_GATES.json >/dev/null
grep 'MAGICAL_GLOBAL_DISCOVERY_CLAIM' qikvrt/gates/AUTONOMOUS_DISCOVERY_GATES.json >/dev/null
echo 'PASS autonomous discovery operation gates'
