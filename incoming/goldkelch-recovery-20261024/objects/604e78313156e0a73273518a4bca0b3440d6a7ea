# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-multicast >/tmp/qikvrt_multicast.out
grep -q "PASS QIKVRT multicast selftest v2.13" /tmp/qikvrt_multicast.out
grep -q "Payload" docs/MULTICAST_PROTOCOL.md
grep -q "Empfängergruppe" docs/MULTICAST_PROTOCOL.md
grep -q "NO_METAPHOR_ONLY_MULTICAST" qikvrt/gates/MULTICAST_ONTOLOGY_GATES.json
printf '%s
' "PASS multicast gates"
