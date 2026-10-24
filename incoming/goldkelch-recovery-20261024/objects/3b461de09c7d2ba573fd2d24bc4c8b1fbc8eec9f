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
grep -q "Watchdog Keepalive Layer" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "authorized heartbeat" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "node lost" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "last_seen_epoch" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "location hint" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "No unauthorized probing" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "WATCHDOG_KEEPALIVE_OK" "$ROOT/docs/WATCHDOG_KEEPALIVE.md"
grep -q "emit_heartbeat" "$ROOT/docs/WATCHDOG_OPERATION_SPEC.md"
grep -q "evaluate_node_status" "$ROOT/docs/WATCHDOG_OPERATION_SPEC.md"
grep -q "lost_since_epoch" "$ROOT/docs/WATCHDOG_OPERATION_SPEC.md"
grep -q "UNAUTHORIZED_SCANNING" "$ROOT/qikvrt/gates/WATCHDOG_KEEPALIVE_GATES.json"
grep -q "NODE_LOSS_STATUS_RECORDED" "$ROOT/qikvrt/gates/WATCHDOG_KEEPALIVE_GATES.json"
grep -q "WATCHDOG_KEEPALIVE_OK" "$ROOT/qikvrt/gates/WATCHDOG_KEEPALIVE_GATES.json"
grep -q "NODE_LOST_PENDING_REVIEW" "$ROOT/qikvrt/ledger/WATCHDOG_KEEPALIVE_LEDGER.jsonl"
"$ROOT/build/qikvrt_verify" --selftest-watchdog >/dev/null
printf '%s
' "PASS watchdog keepalive gates"
