#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

echo "QIKVRT_4AT_TEST_START"
[ -f START_HIER_AUTONOMOUS_MESH_INSTALL.cmd ] || { echo "BLOCK missing start cmd"; exit 1; }
[ -f tools/qikvrt_4at_installer.js ] || { echo "BLOCK missing installer js"; exit 1; }
find . -name '*.ps1' | grep . && { echo "BLOCK ps1 present"; exit 1; } || true
grep -RIn 'powershell\.exe\|pwsh\.exe\|git clone\|git push' START_HIER_AUTONOMOUS_MESH_INSTALL.cmd tools/qikvrt_4at_installer.js && { echo "BLOCK forbidden installer primary path marker"; exit 1; } || true
pat='github_'"pat_"; grep -RIn "$pat" START_HIER_AUTONOMOUS_MESH_INSTALL.cmd tools roles README*.md CONTRACT_STATUS.md COPYRIGHT_AND_LICENSE_ACCEPTANCE.md && { echo "BLOCK embedded token marker"; exit 1; } || true
sh -n roles/seed/tools/qikvrt_seed_registry_acceptance.sh
sh -n roles/seed/tools/qikvrt_seed_mesh_maintenance.sh
sh -n roles/node/tools/qikvrt_node_health_publish.sh
sh -n roles/node/tools/qikvrt_node_seed_status_watch.sh
if command -v node >/dev/null 2>&1; then node --check tools/qikvrt_4at_installer.js >/dev/null; fi
if command -v cc >/dev/null 2>&1; then
  cc roles/seed/tools/qikvrt_handshake_core.c -o /tmp/qikvrt_4at_seed_core
  /tmp/qikvrt_4at_seed_core seed | grep 'PASS' >/dev/null
  cc roles/node/tools/qikvrt_handshake_core.c -o /tmp/qikvrt_4at_node_core
  /tmp/qikvrt_4at_node_core node | grep 'PASS' >/dev/null
fi
TMP=$(mktemp -d)
cp -R roles/seed "$TMP/seed"
cp -R roles/node "$TMP/node"
mkdir -p "$TMP/bin"
cat > "$TMP/bin/curl" <<'MOCK'
#!/bin/sh
out=""
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if [ "$out" = "/dev/null" ]; then exit 0; fi
if [ -n "$out" ]; then
  case "$out" in
    *seed_index*) cat > "$out" <<JSON
{"nodes":[{"guid":"a84f157a-cef2-4c47-bca9-8f407085bdbe","repository":"ingolf-lohmann/qik-vrt","status":"ACCEPTED"}]}
JSON
      ;;
    *seed_entry*) cat > "$out" <<JSON
{"guid":"a84f157a-cef2-4c47-bca9-8f407085bdbe","repository":"ingolf-lohmann/qik-vrt","status":"ACCEPTED"}
JSON
      ;;
    *) cat > "$out" <<JSON
{"repository_guid":"a84f157a-cef2-4c47-bca9-8f407085bdbe","source_repository":"ingolf-lohmann/qik-vrt","seed_repository":"Goldkelch/qik-vrt","boundaries":{"no_global_scanning":true,"no_self_propagation":true,"no_remote_mutation_without_authorization":true}}
JSON
      ;;
  esac
fi
exit 0
MOCK
chmod +x "$TMP/bin/curl"
PATH="$TMP/bin:$PATH"; export PATH
(cd "$TMP/seed" && sh tools/qikvrt_seed_registry_acceptance.sh)
[ -f "$TMP/seed/registry/nodes/a84f157a-cef2-4c47-bca9-8f407085bdbe.json" ] || { echo "BLOCK seed node entry missing"; exit 1; }
[ -f "$TMP/seed/registry/NODEMESH_INDEX.json" ] || { echo "BLOCK seed index missing"; exit 1; }
[ -f "$TMP/seed/registry/NODEMESH_STATUS.json" ] || { echo "BLOCK seed status missing"; exit 1; }
(cd "$TMP/node" && sh tools/qikvrt_node_health_publish.sh && sh tools/qikvrt_node_seed_status_watch.sh)
[ -f "$TMP/node/qikvrt/runtime/onboarding/NODE_HEALTH.json" ] || { echo "BLOCK node health missing"; exit 1; }
[ -f "$TMP/node/qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json" ] || { echo "BLOCK node seed status missing"; exit 1; }
[ -f "$TMP/node/evidence/node_seed_link_status.json" ] || { echo "BLOCK node evidence missing"; exit 1; }
rm -rf "$TMP"
echo "QIKVRT_4AT_AUTONOMOUS_MESH_CONTRACT_PASS"
