#!/bin/sh
set -eu
mkdir -p audit evidence/seed_mesh_audit/runs
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
INDEX="registry/NODEMESH_INDEX.json"
STATUS="registry/NODEMESH_STATUS.json"
[ -f "$INDEX" ] || { echo "BLOCK missing $INDEX"; exit 2; }
[ -f "$STATUS" ] || { echo "BLOCK missing $STATUS"; exit 3; }
node_count=$(sed -n 's/.*"node_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
active_count=$(sed -n 's/.*"active_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
stale_count=$(sed -n 's/.*"stale_count"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$STATUS" | head -n 1)
[ -n "$node_count" ] || node_count=0
[ -n "$active_count" ] || active_count=0
[ -n "$stale_count" ] || stale_count=0
REPORT="audit/QIKVRT_MESH_AUDIT_REPORT.md"
cat > "$REPORT" <<MD
# QIK-VRT Mesh Audit Report

- generated_utc: $UTC
- run_id: $RUN_ID
- seed_repository: Goldkelch/qik-vrt
- node_count: $node_count
- active_count: $active_count
- stale_count: $stale_count

## Evidence paths

- registry/NODEMESH_INDEX.json
- registry/NODEMESH_STATUS.json
- evidence/seed_mesh_maintenance/LATEST.json

## Boundary statement

The Seed reads only authorized known Node entries. The Seed writes only to the Seed repository. Nodes write only to their own Node repository. No global scanning, no self propagation, and no remote mutation without authorization are part of this audit surface.
MD
cat > audit/QIKVRT_MESH_AUDIT_SUMMARY.json <<JSON
{
  "qikvrt_event": "SEED_MESH_AUDIT_EXPORT_4AU",
  "generated_utc": "$UTC",
  "run_id": "$RUN_ID",
  "status": "PASS",
  "seed_repository": "Goldkelch/qik-vrt",
  "node_count": $node_count,
  "active_count": $active_count,
  "stale_count": $stale_count,
  "report_path": "$REPORT"
}
JSON
EVID="evidence/seed_mesh_audit/runs/$RUN_ID.json"
cp audit/QIKVRT_MESH_AUDIT_SUMMARY.json "$EVID"
cp "$EVID" evidence/seed_mesh_audit/LATEST.json
echo "QIKVRT_SEED_MESH_AUDIT_EXPORT PASS run_id=$RUN_ID node_count=$node_count"
