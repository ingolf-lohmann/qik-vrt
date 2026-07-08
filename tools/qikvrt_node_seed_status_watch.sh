#!/bin/sh
set -eu
CONFIG="qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv"
[ -f "$CONFIG" ] || { echo "BLOCK missing $CONFIG"; exit 2; }
line=$(grep -v '^#' "$CONFIG" | grep -v '^$' | head -n 1)
guid=$(printf '%s' "$line" | cut -f1)
source_repo=$(printf '%s' "$line" | cut -f2)
seed_repo=$(printf '%s' "$line" | cut -f3)
seed_index_url=$(printf '%s' "$line" | cut -f4)
seed_node_entry_url=$(printf '%s' "$line" | cut -f5)
node_branch=$(printf '%s' "$line" | cut -f6)
[ -n "$node_branch" ] || node_branch="main"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
echo "QIKVRT_NODE_STATUS CHECK $guid $source_repo seed=$seed_repo run_id=$RUN_ID"
TMPDIR="${TMPDIR:-/tmp}"
idx="$TMPDIR/qikvrt_seed_index_$guid.json"
entry="$TMPDIR/qikvrt_seed_entry_$guid.json"
curl -fsSL "$seed_index_url" -o "$idx"
curl -fsSL "$seed_node_entry_url" -o "$entry"
grep -F "\"$guid\"" "$idx" >/dev/null || { echo "BLOCK guid missing in NODEMESH_INDEX"; exit 3; }
grep -F "\"$source_repo\"" "$idx" >/dev/null || { echo "BLOCK source repo missing in NODEMESH_INDEX"; exit 4; }
grep -F '"ACCEPTED"' "$entry" >/dev/null || { echo "BLOCK seed node entry not accepted"; exit 5; }
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p qikvrt/runtime/onboarding evidence/node_seed_link/runs
cat > qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json <<JSON
{
  "qikvrt_event": "NODE_ACK_OF_SEED_ACCEPTANCE_4AU",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "status": "ACCEPTED_BY_SEED",
  "checked_utc": "$UTC",
  "run_id": "$RUN_ID",
  "seed_index_url": "$seed_index_url",
  "seed_node_entry_url": "$seed_node_entry_url",
  "boundaries": {
    "node_writes_only_to_node_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON
cat > "evidence/node_seed_link/runs/$RUN_ID.json" <<JSON
{
  "qikvrt_event": "NODE_SEED_LINK_CONFIRMED_4AU",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "status": "PASS",
  "checked_utc": "$UTC",
  "run_id": "$RUN_ID"
}
JSON
cp "evidence/node_seed_link/runs/$RUN_ID.json" evidence/node_seed_link_status.json
cp "evidence/node_seed_link/runs/$RUN_ID.json" evidence/node_seed_link/LATEST.json
echo "QIKVRT_NODE_SEED_STATUS_WATCH PASS $guid run_id=$RUN_ID"
