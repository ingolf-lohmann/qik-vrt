# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
grep -q "Authorized Active Layer" "$ROOT/docs/ACTIVE_LAYER.md"
grep -q "Opt-in only" "$ROOT/docs/ACTIVE_LAYER.md"
grep -q "No unauthorized scanning" "$ROOT/docs/ACTIVE_LAYER.md"
grep -q "No self-propagation" "$ROOT/docs/ACTIVE_LAYER.md"
grep -q "ACTIVE_LAYER_OK" "$ROOT/docs/ACTIVE_LAYER.md"
grep -q "AUTHORIZED_DISCOVERY_OK" "$ROOT/qikvrt/gates/ACTIVE_LAYER_GATES.json"
grep -q "UNAUTHORIZED_INTERNET_SCANNING" "$ROOT/qikvrt/gates/ACTIVE_LAYER_GATES.json"
grep -q "Continuous cognitive improvement" "$ROOT/docs/EVOLUTION_POLICY.md"
grep -q "Cognitive improvement" "$ROOT/docs/COGNITIVE_IMPROVEMENT.md"
grep -q "Active operation lifecycle" "$ROOT/docs/ACTIVE_OPERATION_SPEC.md"
"$ROOT/build/qikvrt_verify" --selftest-active >/dev/null
printf '%s
' "PASS active layer gates"
