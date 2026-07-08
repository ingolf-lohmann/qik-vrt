#!/bin/sh
set -eu

KNOWN="registry/KNOWN_NODE_REQUESTS.tsv"
[ -f "$KNOWN" ] || { echo "BLOCK missing $KNOWN"; exit 2; }
mkdir -p registry evidence/seed_mesh_maintenance
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
INDEX="registry/NODEMESH_INDEX.json"
STATUS="registry/NODEMESH_STATUS.json"
NODE_TMP="registry/.nodemesh_nodes.tmp"
STATUS_TMP="registry/.nodemesh_status.tmp"
: > "$NODE_TMP"
: > "$STATUS_TMP"
count=0

while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  guid=$(printf '%s' "$line" | cut -f1)
  source_repo=$(printf '%s' "$line" | cut -f2)
  seed_repo=$(printf '%s' "$line" | cut -f3)
  request_url=$(printf '%s' "$line" | cut -f4)
  node_branch=$(printf '%s' "$line" | cut -f5)
  [ -n "$node_branch" ] || node_branch="main"
  entry="registry/nodes/$guid.json"
  reg_status="UNKNOWN"
  [ -f "$entry" ] && reg_status="ACCEPTED"
  node_health_url="https://raw.githubusercontent.com/$source_repo/$node_branch/qikvrt/runtime/onboarding/NODE_HEALTH.json"
  node_ack_url="https://raw.githubusercontent.com/$source_repo/$node_branch/qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json"
  health="false"
  ack="false"
  if curl -fsSL "$node_health_url" -o /dev/null; then health="true"; fi
  if curl -fsSL "$node_ack_url" -o /dev/null; then ack="true"; fi
  [ "$count" -gt 0 ] && printf ',\n' >> "$NODE_TMP"
  cat >> "$NODE_TMP" <<JSON
    {
      "guid": "$guid",
      "repository": "$source_repo",
      "seed_repository": "$seed_repo",
      "node_branch": "$node_branch",
      "status": "$reg_status",
      "registry_path": "$entry",
      "node_request_url": "$request_url"
    }
JSON
  [ "$count" -gt 0 ] && printf ',\n' >> "$STATUS_TMP"
  cat >> "$STATUS_TMP" <<JSON
    {
      "guid": "$guid",
      "repository": "$source_repo",
      "registry_status": "$reg_status",
      "node_health_visible": $health,
      "node_ack_visible": $ack,
      "node_health_url": "$node_health_url",
      "node_ack_url": "$node_ack_url"
    }
JSON
  count=$((count + 1))
done < "$KNOWN"

cat > "$INDEX" <<JSON
{
  "qikvrt_event": "NODEMESH_INDEX_AGGREGATE",
  "generated_utc": "$UTC",
  "seed_repository": "Goldkelch/qik-vrt",
  "node_count": $count,
  "nodes": [
$(cat "$NODE_TMP")
  ],
  "boundaries": {
    "seed_index_only_reads_authorized_known_nodes": true,
    "seed_writes_only_to_seed_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON

cat > "$STATUS" <<JSON
{
  "qikvrt_event": "NODEMESH_STATUS_AGGREGATE",
  "generated_utc": "$UTC",
  "seed_repository": "Goldkelch/qik-vrt",
  "node_count": $count,
  "nodes": [
$(cat "$STATUS_TMP")
  ]
}
JSON

EVID="evidence/seed_mesh_maintenance/$STAMP.json"
cat > "$EVID" <<JSON
{
  "qikvrt_event": "SEED_MESH_MAINTENANCE_EVIDENCE",
  "generated_utc": "$UTC",
  "status": "PASS",
  "node_count": $count,
  "index_path": "$INDEX",
  "status_path": "$STATUS"
}
JSON
cp "$EVID" evidence/seed_mesh_maintenance/LATEST.json
rm -f "$NODE_TMP" "$STATUS_TMP"
echo "QIKVRT_SEED_MESH_MAINTENANCE PASS node_count=$count"
