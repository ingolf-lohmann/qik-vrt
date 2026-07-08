# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'Ontology of Difference tests' docs/FT.md
grep -q 'Requirements coverage tests' docs/FT.md
grep -q 'Unit tests' docs/FT.md
grep -q 'Integration tests' docs/FT.md
grep -q 'Acceptance tests' docs/FT.md
grep -q 'Performance tests' docs/FT.md
grep -q 'Security tests' docs/FT.md
grep -q 'Runtime REST API tests' docs/FT.md
grep -q 'FULL_REUSABLE_TEST_ENVIRONMENT_GATE' qikvrt/gates/FT.json
echo 'PASS full reusable test environment gates'
