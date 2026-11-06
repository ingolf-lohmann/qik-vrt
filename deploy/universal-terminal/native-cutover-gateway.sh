#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Native cutover candidate. Execute only through the separate compose override.
set -eu
[ "$(id -u)" = 65534 ] || { echo "BLOCK: CUTOVER_GATEWAY_UID_NOT_NOBODY" >&2; exit 78; }
config=/opt/qikvrt/deploy/universal-terminal/nginx-native-cutover.conf
[ -r "$config" ] || { echo "BLOCK: CUTOVER_GATEWAY_CONFIG_ABSENT" >&2; exit 78; }
for dir in nginx-client-body nginx-proxy nginx-fastcgi nginx-uwsgi nginx-scgi; do
  mkdir -p "/tmp/$dir"
done
ready=0
attempt=0
while [ "$attempt" -lt 60 ]; do
  if curl --max-time 2 -fsS http://127.0.0.1:8771/.well-known/effect-ack >/dev/null 2>&1 &&
     curl --max-time 2 -fsS http://127.0.0.1:6080/vnc.html >/dev/null 2>&1; then
    ready=1
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done
[ "$ready" = 1 ] || { echo "BLOCK: ORIGINAL_TERMINAL_ENDPOINTS_NOT_READY" >&2; exit 78; }
cat > /tmp/qikvrt-mesh-health.json.tmp <<'EOF'
{"schema":"qikvrt_compose_mesh_gateway_health_v1","state":"READY","roles":{"terminal":"OBSERVED","gateway":"READY","m68k":"SEPARATELY_REOBSERVED","smtp":"SEPARATELY_REOBSERVED","dns":"SEPARATELY_REOBSERVED","snmp":"SEPARATELY_REOBSERVED"},"effect_ack":"NOT_IMPLIED","browser_cutover":"HOLD_ANONYMOUS_403"}
EOF
mv /tmp/qikvrt-mesh-health.json.tmp /tmp/qikvrt-mesh-health.json
nginx -t -c "$config" || { echo "BLOCK: CUTOVER_NGINX_INVALID" >&2; exit 78; }
exec nginx -c "$config" -g 'daemon off;'
