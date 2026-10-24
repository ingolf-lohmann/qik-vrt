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
grep -q "QIKVRT Node Onboarding Testbed" "$ROOT/docs/NT.md"
grep -q "Ontology of Difference" "$ROOT/docs/NT.md"
grep -q "Constitution" "$ROOT/docs/NT.md"
grep -q "Unified QIKVRT Node Core" "$ROOT/docs/NT.md"
grep -q "QIKVRT GitHub-Compatible Repository API" "$ROOT/docs/NT.md"
grep -q "authorized seed graph" "$ROOT/docs/NT.md"
grep -q "watchdog" "$ROOT/docs/NT.md"
grep -q "GUID bootstrap" "$ROOT/docs/NT.md"
grep -q "live GitHub evidence" "$ROOT/docs/NT.md"
grep -q "request response traceability" "$ROOT/docs/NT.md"
grep -q "no seed/node code split" "$ROOT/docs/NT.md"
grep -q "NO_UNAUTHORIZED_SCANNING" "$ROOT/qikvrt/gates/NT.json"
grep -q "QIKVRT_NODE_ONBOARDING_TESTBED_MANIFEST" "$ROOT/qikvrt/manifests/NT.json"
grep -q "NODE_ONBOARDING_TESTBED_REFERENCE" "$ROOT/qikvrt/ledger/NT.jsonl"
"$ROOT/build/qikvrt_verify" --selftest-node-onboarding-testbed >/tmp/qikvrt_selftest_node_onboarding_testbed.out
grep -q "PASS QIKVRT unified node onboarding testbed selftest" /tmp/qikvrt_selftest_node_onboarding_testbed.out
echo 'PASS unified node onboarding testbed gates'
