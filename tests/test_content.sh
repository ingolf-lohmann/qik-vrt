# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
f=docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md
count=$(grep -c '^## Artikel ' "$f")
[ "$count" = "44" ]
grep -q 'QIKVRT' "$f"
grep -q 'Nachvollziehbarkeit ist kein Luxus' "$f"
grep -q 'REQ-M001' docs/REQUIREMENTS.md
grep -q 'REQ-O001' docs/REQUIREMENTS.md
grep -q 'QIKVRT <=> Multicast <=> Gerechtigkeit' docs/FORMAL_MODEL.md
printf '%s
' "PASS content gates"
