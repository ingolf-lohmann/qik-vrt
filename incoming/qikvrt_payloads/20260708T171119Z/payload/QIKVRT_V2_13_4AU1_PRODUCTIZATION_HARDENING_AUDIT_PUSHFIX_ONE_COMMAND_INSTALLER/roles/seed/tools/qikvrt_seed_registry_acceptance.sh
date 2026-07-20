#!/bin/sh
set -eu
KNOWN="registry/KNOWN_NODE_REQUESTS.tsv"
POLICY="registry/NODE_POLICY.tsv"
[ -f "$KNOWN" ] || { echo "BLOCK missing $KNOWN"; exit 2; }
mkdir -p registry/nodes evidence/seed_acceptance/runs ledger
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
TMPDIR="${TMPDIR:-/tmp}"
run_count=0
fail_count=0
policy_status_for() {
  g="$1"
  if [ -f "$POLICY" ]; then
    awk -F '\t' -v G="$g" 'BEGIN{v="ACTIVE"} $1==G {v=$2} END{print v}' "$POLICY"
  else
    printf '%s\n' "ACTIVE"
  fi
}
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|'#'*) continue ;; esac
  guid=$(printf '%s' "$line" | cut -f1)
  source_repo=$(printf '%s' "$line" | cut -f2)
  seed_repo=$(printf '%s' "$line" | cut -f3)
  request_url=$(printf '%s' "$line" | cut -f4)
  node_branch=$(printf '%s' "$line" | cut -f5)
  [ -n "$node_branch" ] || node_branch="main"
  policy_status=$(policy_status_for "$guid")
  echo "QIKVRT_SEED_ACCEPTANCE CHECK $guid $source_repo $seed_repo policy=$policy_status run_id=$RUN_ID"
  if [ "$policy_status" = "REVOKED" ]; then
    echo "BLOCK node policy revoked $guid"
    fail_count=$((fail_count + 1))
    continue
  fi
  req="$TMPDIR/qikvrt_seed_request_$guid.json"
  curl -fsSL "$request_url" -o "$req"
  grep -F "\"$guid\"" "$req" >/dev/null || { echo "BLOCK guid not present in node request"; exit 3; }
  grep -F "\"$source_repo\"" "$req" >/dev/null || { echo "BLOCK source_repo not present in node request"; exit 4; }
  grep -F "\"$seed_repo\"" "$req" >/dev/null || { echo "BLOCK seed_repo not present in node request"; exit 5; }
  grep -F '"no_global_scanning"' "$req" >/dev/null || { echo "BLOCK no_global_scanning missing"; exit 6; }
  grep -F '"no_self_propagation"' "$req" >/dev/null || { echo "BLOCK no_self_propagation missing"; exit 7; }
  grep -F '"no_remote_mutation_without_authorization"' "$req" >/dev/null || { echo "BLOCK no_remote_mutation_without_authorization missing"; exit 8; }
  status="ACCEPTED"
  [ "$policy_status" = "SUSPENDED" ] && status="SUSPENDED"
  cat > "registry/nodes/$guid.json" <<JSON
{
  "qikvrt_event": "AUTONOMOUS_SEED_ACCEPTANCE",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "node_branch": "$node_branch",
  "node_request_url": "$request_url",
  "status": "$status",
  "policy_status": "$policy_status",
  "acceptance_mode": "AUTONOMOUS_SEED_WORKFLOW_4AU",
  "accepted_utc": "$UTC",
  "last_acceptance_run_id": "$RUN_ID",
  "lifecycle": {
    "renewal_supported": true,
    "heartbeat_required": true,
    "suspend_supported": true,
    "revoke_supported": true,
    "reaccept_supported": true
  },
  "boundaries": {
    "authorized_manifest_graph_only": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true,
    "seed_writes_only_to_seed_repository": true
  }
}
JSON
  cat > "evidence/seed_acceptance/$guid.json" <<JSON
{
  "qikvrt_event": "AUTONOMOUS_SEED_ACCEPTANCE_EVIDENCE",
  "guid": "$guid",
  "repository": "$source_repo",
  "seed_repository": "$seed_repo",
  "node_request_url": "$request_url",
  "status": "PASS",
  "policy_status": "$policy_status",
  "run_id": "$RUN_ID",
  "created_utc": "$UTC"
}
JSON
  cp "evidence/seed_acceptance/$guid.json" "evidence/seed_acceptance/runs/$RUN_ID.json"
  printf '{"utc":"%s","run_id":"%s","event":"AUTONOMOUS_SEED_ACCEPTANCE","guid":"%s","repository":"%s","seed_repository":"%s","status":"PASS","policy_status":"%s"}\n' "$UTC" "$RUN_ID" "$guid" "$source_repo" "$seed_repo" "$policy_status" >> ledger/NODE_REGISTRATION_LEDGER.jsonl
  run_count=$((run_count + 1))
  echo "PASS seed accepted $guid"
done < "$KNOWN"
if [ -f tools/qikvrt_seed_mesh_maintenance.sh ]; then
  sh tools/qikvrt_seed_mesh_maintenance.sh
fi
echo "QIKVRT_SEED_REGISTRY_ACCEPTANCE PASS accepted_count=$run_count fail_count=$fail_count run_id=$RUN_ID"
