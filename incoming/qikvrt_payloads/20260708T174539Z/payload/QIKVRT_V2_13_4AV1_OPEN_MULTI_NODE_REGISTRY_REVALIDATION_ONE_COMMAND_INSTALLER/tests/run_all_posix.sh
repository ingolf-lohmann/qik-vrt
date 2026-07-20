#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
fail(){ echo "BLOCK $1"; exit 1; }
[ -f START_HIER_OPEN_MULTI_NODE_REVALIDATION_INSTALL.cmd ] || fail missing_cmd
[ -f tools/qikvrt_4av1_installer.js ] || fail missing_installer_js
find . -name '*.ps1' | grep -q . && fail ps1_present || true
grep -R "github_pat_" CONTRACT_STATUS.md COPYRIGHT_AND_LICENSE_ACCEPTANCE.md README.md README_DE.md README_EN.md START_HIER_OPEN_MULTI_NODE_REVALIDATION_INSTALL.cmd roles tools 2>/dev/null && fail embedded_token || true
# No fixed additional node count prompt may remain.
grep -R "How many additional Node" tools START_HIER_OPEN_MULTI_NODE_REVALIDATION_INSTALL.cmd roles 2>/dev/null && fail fixed_node_count_prompt_present || true
grep -R "Add additional known Node request entries" tools START_HIER_OPEN_MULTI_NODE_REVALIDATION_INSTALL.cmd roles 2>/dev/null && fail additional_node_prompt_present || true
grep -q "OPEN_MULTI_NODE_REGISTRY_CONFIG" tools/qikvrt_4av1_installer.js || fail missing_open_registry_config
[ -f roles/seed/registry/NODE_DISCOVERY_POLICY.json ] || fail missing_node_discovery_policy
[ -f roles/seed/registry/node_request_queue/OPEN_NODE_REQUESTS.tsv ] || fail missing_open_queue
for f in roles/seed/tools/*.sh roles/node/tools/*.sh; do sh -n "$f" || fail "shell_syntax_$f"; done
for f in roles/seed/.github/workflows/*.yml roles/node/.github/workflows/*.yml; do grep -q "QIKVRT_PUSH_ATTEMPT" "$f" || fail "missing_push_retry_$f"; done
grep -q 'registry/node_request_queue' roles/seed/tools/qikvrt_seed_mesh_maintenance.sh || fail maintenance_not_queue_aware
grep -q 'fixed_node_count": false' roles/seed/tools/qikvrt_seed_node_revalidation.sh || fail revalidation_not_open
cc -std=c99 -Wall -Wextra -pedantic roles/seed/tools/qikvrt_handshake_core.c -o /tmp/qikvrt_4av1_core
/tmp/qikvrt_4av1_core | grep -q QIKVRT_4AV1_HANDSHAKE_CORE_OK || fail core_run
rm -rf /tmp/qikvrt_4av1_mock && mkdir -p /tmp/qikvrt_4av1_mock/registry/node_request_queue /tmp/qikvrt_4av1_mock/tools
cp roles/seed/tools/qikvrt_seed_node_revalidation.sh roles/seed/tools/qikvrt_seed_mesh_audit_export.sh /tmp/qikvrt_4av1_mock/tools/
cat > /tmp/qikvrt_4av1_mock/registry/NODEMESH_INDEX.json <<'JSON'
{"fixed_node_count":false,"node_count":3,"nodes":[{"guid":"a","repository":"repo/a"},{"guid":"b","repository":"repo/b"},{"guid":"c","repository":"repo/c"}]}
JSON
cat > /tmp/qikvrt_4av1_mock/registry/NODEMESH_STATUS.json <<'JSON'
{"fixed_node_count":false,"node_count":3,"nodes":[{"effective_status":"ACTIVE","registry_status":"ACCEPTED"},{"effective_status":"STALE","registry_status":"ACCEPTED"},{"effective_status":"SUSPENDED","registry_status":"SUSPENDED"}]}
JSON
(cd /tmp/qikvrt_4av1_mock && QIKVRT_RUN_ID=TEST4AV1 sh tools/qikvrt_seed_node_revalidation.sh)
[ -f /tmp/qikvrt_4av1_mock/registry/NODEMESH_REVALIDATION.json ] || fail mock_revalidation_missing
grep -q '"fixed_node_count": false' /tmp/qikvrt_4av1_mock/registry/NODEMESH_REVALIDATION.json || fail mock_revalidation_fixed_count
(cd /tmp/qikvrt_4av1_mock && QIKVRT_RUN_ID=TEST4AV1 sh tools/qikvrt_seed_mesh_audit_export.sh)
[ -f /tmp/qikvrt_4av1_mock/evidence/seed_mesh_audit/runs/TEST4AV1.json ] || fail mock_audit_evidence_missing
[ -f /tmp/qikvrt_4av1_mock/docs/QIKVRT_AUDIT_EXPORT.md ] || fail mock_audit_doc_missing
echo QIKVRT_4AV1_OPEN_MULTI_NODE_REVALIDATION_CONTRACT_PASS
