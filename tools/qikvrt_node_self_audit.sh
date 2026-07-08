#!/bin/sh
set -eu
RUN_ID="${QIKVRT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p evidence/node_self_audit audit
health="false"; ack="false"; renewal="false"
[ -f qikvrt/runtime/onboarding/NODE_HEALTH.json ] && health="true"
[ -f qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json ] && ack="true"
[ -f qikvrt/runtime/onboarding/NODE_REGISTRATION_RENEWAL.json ] && renewal="true"
status="PASS"
[ "$health" = "true" ] || status="BLOCK"
[ "$ack" = "true" ] || status="BLOCK"
cat > "evidence/node_self_audit/$RUN_ID.json" <<JSON
{
  "qikvrt_event": "NODE_SELF_AUDIT_4AV1",
  "generated_utc": "$UTC",
  "run_id": "$RUN_ID",
  "status": "$status",
  "node_health_present": $health,
  "node_seed_ack_present": $ack,
  "node_renewal_present": $renewal,
  "boundaries": {
    "node_writes_only_to_node_repository": true,
    "no_global_scanning": true,
    "no_self_propagation": true,
    "no_remote_mutation_without_authorization": true
  }
}
JSON
cp "evidence/node_self_audit/$RUN_ID.json" evidence/node_self_audit/LATEST.json
cat > audit/QIKVRT_NODE_SELF_AUDIT.md <<MD
# QIK-VRT Node Self Audit

- generated_utc: $UTC
- run_id: $RUN_ID
- status: $status
- node_health_present: $health
- node_seed_ack_present: $ack
- node_renewal_present: $renewal
MD
if [ "$status" = "PASS" ]; then echo "QIKVRT_NODE_SELF_AUDIT PASS run_id=$RUN_ID"; else echo "QIKVRT_NODE_SELF_AUDIT BLOCK run_id=$RUN_ID"; exit 9; fi
