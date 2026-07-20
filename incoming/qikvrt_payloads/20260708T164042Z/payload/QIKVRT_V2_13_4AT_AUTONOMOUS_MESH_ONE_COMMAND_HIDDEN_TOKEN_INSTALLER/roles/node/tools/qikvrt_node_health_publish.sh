#!/bin/sh
set -eu
CONFIG="qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv"
[ -f "$CONFIG" ] || { echo "BLOCK missing $CONFIG"; exit 2; }
line=$(grep -v '^#' "$CONFIG" | grep -v '^$' | head -n 1)
guid=$(printf '%s' "$line" | cut -f1)
source_repo=$(printf '%s' "$line" | cut -f2)
seed_repo=$(printf '%s' "$line" | cut -f3)
node_branch=$(printf '%s' "$line" | cut -f6)
[ -n "$node_branch" ] || node_branch="main"
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p qikvrt/runtime/onboarding evidence/node_health
cat > qikvrt/runtime/onboarding/NODE_HEALTH.json <<JSON
{
  "qikvrt_event": "NODE_HEALTH_HEARTBEAT",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "node_branch": "$node_branch",
  "status": "ACTIVE",
  "heartbeat_utc": "$UTC",
  "boundaries": {
    "node_writes_only_to_node_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON
cat > "evidence/node_health/$STAMP.json" <<JSON
{
  "qikvrt_event": "NODE_HEALTH_EVIDENCE",
  "guid": "$guid",
  "repository": "$source_repo",
  "status": "PASS",
  "heartbeat_utc": "$UTC"
}
JSON
cp "evidence/node_health/$STAMP.json" evidence/node_health/LATEST.json
echo "QIKVRT_NODE_HEALTH_PUBLISH PASS $guid"
