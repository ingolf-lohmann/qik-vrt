# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
grep -q 'qv2134_seed.zip' docs/SD.md
grep -q 'qv2134_node.zip' docs/SD.md
grep -q 'same QIKVRT Node Core' docs/SD.md
grep -q 'SEED_NODE_SPLIT_DELIVERY_GATE' qikvrt/gates/SD.json
echo 'PASS seed node split delivery gates'
