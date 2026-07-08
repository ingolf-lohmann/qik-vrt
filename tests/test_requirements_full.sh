# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Requirements' docs/REQUIREMENTS.md
grep -q 'Traceability' docs/TRACEABILITY_MATRIX.md
grep -q 'Article Implementation Matrix' docs/ARTICLE_IMPLEMENTATION_MATRIX.md
grep -q 'FULL_REUSABLE_TEST_ENVIRONMENT_GATE' qikvrt/gates/FT.json
echo 'PASS full requirements coverage gates'
