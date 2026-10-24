# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Kein amtlicher Rechtsakt' docs/SECURITY_AND_BOUNDARY.md
grep -q 'Kein Überwachungsinstrument' docs/SECURITY_AND_BOUNDARY.md
grep -q 'Kein Instrument zur Beschuldigung konkreter Dritter' docs/SECURITY_AND_BOUNDARY.md
grep -q 'No final pass unless multicast and ontology selftests pass' qikvrt/gates/MULTICAST_ONTOLOGY_GATES.json
grep -q 'No final pass without traceability' qikvrt/gates/BOUNDARY_GATES.json
printf '%s
' "PASS boundary gates"
