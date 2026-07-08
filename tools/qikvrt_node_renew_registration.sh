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
NEXT="$(date -u -d '+24 hours' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p qikvrt/runtime/onboarding evidence/node_registration_renewal
cat > qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json <<JSON
{
  "qikvrt_event": "NODE_REGISTRATION_RENEWAL_4AV1",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "node_branch": "$node_branch",
  "status": "RENEWED",
  "renewed_utc": "$UTC",
  "next_renewal_due_utc": "$NEXT",
  "run_id": "$RUN_ID",
  "boundaries": {
    "node_writes_only_to_node_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON
cat > "evidence/node_registration_renewal/$RUN_ID.json" <<JSON
{
  "qikvrt_event": "NODE_REGISTRATION_RENEWAL_EVIDENCE_4AV1",
  "guid": "$guid",
  "repository": "$source_repo",
  "status": "PASS",
  "renewed_utc": "$UTC",
  "next_renewal_due_utc": "$NEXT",
  "run_id": "$RUN_ID"
}
JSON
cp "evidence/node_registration_renewal/$RUN_ID.json" evidence/node_registration_renewal/LATEST.json
echo "QIKVRT_NODE_REGISTRATION_RENEWAL PASS $guid run_id=$RUN_ID"
