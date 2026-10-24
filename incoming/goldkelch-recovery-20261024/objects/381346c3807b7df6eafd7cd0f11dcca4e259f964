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
grep -q "Unified QIKVRT Node Core" "$ROOT/docs/UC.md"
grep -q "one identical API" "$ROOT/docs/UC.md"
grep -q "role is runtime configuration" "$ROOT/docs/UC.md"
grep -q "normal" "$ROOT/docs/UC.md"
grep -q "seed" "$ROOT/docs/UC.md"
grep -q "no API fork" "$ROOT/docs/UC.md"
grep -q "no seed/node code split" "$ROOT/docs/UC.md"
grep -q "qikvrt_github_api.openapi.yaml" "$ROOT/docs/UC.md"
grep -q "127.0.0.1:8766" "$ROOT/docs/UC.md"
grep -q "workflow_dispatch" "$ROOT/docs/UC.md"
grep -q "repository_dispatch" "$ROOT/docs/UC.md"
grep -q "QIKVRT_UNIFIED_NODE_CORE" "$ROOT/qikvrt/gates/UC.json"
grep -q "QIKVRT_UNIFIED_NODE_CORE_MANIFEST" "$ROOT/qikvrt/manifests/UC.json"
grep -q "UNIFIED_NODE_CORE_REFERENCE" "$ROOT/qikvrt/ledger/UC.jsonl"
"$ROOT/build/qikvrt_verify" --selftest-unified-node-core >/tmp/qikvrt_selftest_unified_node_core.out
grep -q "PASS QIKVRT unified node core selftest" /tmp/qikvrt_selftest_unified_node_core.out
echo 'PASS unified node core gates'
