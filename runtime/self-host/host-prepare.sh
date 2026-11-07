#!/bin/sh
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
#
# Prepare an owner-controlled Ubuntu/Debian host as the S1 Linux host expected
# by the existing `container-deploy` consumer (tools/qikvrt_self_host_container.py).
#
# It supplies exactly the host-side predicates that consumer requires and that
# no repository step can create remotely:
#   - Docker Engine reachable only through mutual-TLS REST (tcp 2376)
#   - owner-only CA/server/client certificates (0600), generated ON the host
#   - the labelled persistent state volume and private config directory
#   - a partial LINUX_HOST_BINDING with the real daemon ID and API origin
#
# It does not start the node, deploy an image, change DNS, create accounts or
# export private keys anywhere except the printed local file paths. Re-running
# is idempotent: existing certificates, volume and config are kept.
#
# Usage (as root on the VPS):
#   sh host-prepare.sh --public-ip <IPv4> [--node-id <guid>] --admin-cidr <trusted-IPv4/CIDR> [--dry-run]
# Test only the certificate step (no root): QIKVRT_HOST_TLS_DIR=<dir> sh host-prepare.sh --public-ip <IPv4> --certs-only
set -eu

REPOSITORY="ingolf-lohmann/qik-vrt"
ORIGIN="https://raumzeitterminal.de"
CONTAINER_NAME="qikvrt-s1"
STATE_VOLUME="qikvrt-s1-state"
CONFIG_DIR="/etc/qikvrt/s1"
TLS_DIR="${QIKVRT_HOST_TLS_DIR:-/etc/qikvrt/docker-tls}"
API_PORT=2376
PUBLIC_IP=""
NODE_ID=""
ADMIN_CIDR=""
DRY_RUN=0
CERTS_ONLY=0

die() { echo "HOLD_$1" >&2; exit 2; }
run() { if [ "$DRY_RUN" = 1 ]; then echo "DRY-RUN: $*"; else "$@"; fi; }

while [ $# -gt 0 ]; do
    case "$1" in
        --public-ip) PUBLIC_IP="${2:-}"; shift 2 ;;
        --node-id) NODE_ID="${2:-}"; shift 2 ;;
        --admin-cidr) ADMIN_CIDR="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --certs-only) CERTS_ONLY=1; shift ;;
        *) die "UNKNOWN_ARGUMENT" ;;
    esac
done

# Validate numeric IPv4 octets before generating TLS SANs and JSON.
valid_ipv4() {
    printf '%s\n' "$1" | awk -F. '
        NR != 1 { exit 1 }
        NF != 4 { exit 1 }
        { for (i = 1; i <= 4; i++) {
            if ($i !~ /^[0-9]+$/ || length($i) > 3 || $i + 0 > 255) exit 1
          }
        }
    '
}
valid_ipv4 "$PUBLIC_IP" || die "PUBLIC_IPV4_REQUIRED"
# Never open the Docker mTLS control port without an explicit narrow source.
# Restrict this setup path to a single IPv4 host or a small trusted /24-/32 network.
# --certs-only creates no listener and does not require a network policy.
if [ "$CERTS_ONLY" = 0 ]; then
    [ -n "$ADMIN_CIDR" ] || die "ADMIN_CIDR_REQUIRED"
    ADMIN_IP="${ADMIN_CIDR%/*}"
    ADMIN_PREFIX="${ADMIN_CIDR#*/}"
    [ "$ADMIN_IP" != "$ADMIN_CIDR" ] || die "ADMIN_CIDR_INVALID"
    valid_ipv4 "$ADMIN_IP" || die "ADMIN_CIDR_INVALID"
    case "$ADMIN_PREFIX" in
        ''|*[!0-9]*) die "ADMIN_CIDR_INVALID" ;;
    esac
    [ "${#ADMIN_PREFIX}" -le 2 ] && [ "$ADMIN_PREFIX" -ge 24 ] && [ "$ADMIN_PREFIX" -le 32 ] || die "ADMIN_CIDR_INVALID"
    command -v ufw >/dev/null 2>&1 || die "FIREWALL_REQUIRED_FOR_REMOTE_DOCKER_API"
fi
if [ -n "$NODE_ID" ]; then
    printf '%s' "$NODE_ID" | grep -Eq '^[A-Za-z0-9_.:-]{1,100}$' || die "NODE_ID_INVALID"
fi
if [ "$DRY_RUN" = 0 ] && [ "$CERTS_ONLY" = 0 ]; then
    [ "$(id -u)" = 0 ] || die "ROOT_REQUIRED"
    command -v apt-get >/dev/null 2>&1 || die "DEBIAN_FAMILY_HOST_REQUIRED"
fi

if [ "$CERTS_ONLY" = 0 ]; then
# 1. Docker Engine and tools (distribution packages; no curl|sh installers).
if ! command -v docker >/dev/null 2>&1 || ! command -v openssl >/dev/null 2>&1; then
    run apt-get update
    run env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends docker.io openssl ca-certificates
fi
fi

# 2. Mutual-TLS material, generated on the host and never overwritten.
run install -d -m 0700 "$TLS_DIR"
if [ ! -f "$TLS_DIR/ca.pem" ]; then
    run openssl genrsa -out "$TLS_DIR/ca-key.pem" 4096
    run openssl req -new -x509 -days 825 -sha256 -key "$TLS_DIR/ca-key.pem" \
        -subj "/CN=qikvrt-s1-docker-ca" -out "$TLS_DIR/ca.pem"
    run openssl genrsa -out "$TLS_DIR/server-key.pem" 4096
    run openssl req -new -sha256 -key "$TLS_DIR/server-key.pem" -subj "/CN=$PUBLIC_IP" -out "$TLS_DIR/server.csr"
    if [ "$DRY_RUN" = 0 ]; then
        printf 'subjectAltName = IP:%s,IP:127.0.0.1\nextendedKeyUsage = serverAuth\n' "$PUBLIC_IP" > "$TLS_DIR/server.ext"
        printf 'extendedKeyUsage = clientAuth\n' > "$TLS_DIR/client.ext"
    fi
    run openssl x509 -req -days 825 -sha256 -in "$TLS_DIR/server.csr" -CA "$TLS_DIR/ca.pem" \
        -CAkey "$TLS_DIR/ca-key.pem" -CAcreateserial -extfile "$TLS_DIR/server.ext" -out "$TLS_DIR/server-cert.pem"
    run openssl genrsa -out "$TLS_DIR/client-key.pem" 4096
    run openssl req -new -sha256 -key "$TLS_DIR/client-key.pem" -subj "/CN=qikvrt-s1-deployer" -out "$TLS_DIR/client.csr"
    run openssl x509 -req -days 825 -sha256 -in "$TLS_DIR/client.csr" -CA "$TLS_DIR/ca.pem" \
        -CAkey "$TLS_DIR/ca-key.pem" -CAcreateserial -extfile "$TLS_DIR/client.ext" -out "$TLS_DIR/client-cert.pem"
    run sh -c "rm -f '$TLS_DIR'/*.csr '$TLS_DIR'/*.ext && chmod 0600 '$TLS_DIR'/*"
fi

[ "$CERTS_ONLY" = 0 ] || { echo "QIKVRT_HOST_CERTS=READY $TLS_DIR"; exit 0; }

# 3. Docker API: unix socket stays; TCP only with --tlsverify.
run install -d -m 0755 /etc/systemd/system/docker.service.d
if [ "$DRY_RUN" = 0 ]; then
    cat > /etc/systemd/system/docker.service.d/qikvrt-mtls.conf <<EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd:// -H tcp://0.0.0.0:$API_PORT --tlsverify --tlscacert=$TLS_DIR/ca.pem --tlscert=$TLS_DIR/server-cert.pem --tlskey=$TLS_DIR/server-key.pem --containerd=/run/containerd/containerd.sock
EOF
fi
run systemctl daemon-reload
run systemctl enable --now docker
run systemctl restart docker

# 4. Firewall: SSH, HTTP/HTTPS for the public edge, mTLS API (optionally narrowed).
run ufw allow 22/tcp
run ufw allow 80/tcp
run ufw allow 443/tcp
run ufw allow from "$ADMIN_CIDR" to any port "$API_PORT" proto tcp
run ufw --force enable

# 5. Persistent owner state volume and private configuration directory.
if [ "$DRY_RUN" = 1 ] || ! docker volume inspect "$STATE_VOLUME" >/dev/null 2>&1; then
    run docker volume create --label "de.qikvrt.repository=$REPOSITORY" "$STATE_VOLUME"
fi
run install -d -m 0700 "$CONFIG_DIR"

# 6. Self-check through the same mTLS route the deploy consumer will use.
DAEMON_ID="DRY-RUN"
if [ "$DRY_RUN" = 0 ]; then
    DAEMON_ID=$(docker --tlsverify --tlscacert="$TLS_DIR/ca.pem" --tlscert="$TLS_DIR/client-cert.pem" \
        --tlskey="$TLS_DIR/client-key.pem" -H "tcp://127.0.0.1:$API_PORT" info --format '{{.ID}}') \
        || die "MTLS_DOCKER_API_SELF_CHECK_FAILED"
fi
[ -n "$NODE_ID" ] || NODE_ID="$DAEMON_ID"

# 7. Partial binding: host facts only. Pins come from the packaged release.
cat <<EOF
QIKVRT_HOST_PREPARE=READY
# Partial LINUX_HOST_BINDING (complete the null pins from the S1 package step):
{
  "schema": "qikvrt-s1-linux-host-binding/v1",
  "repository": "$REPOSITORY",
  "origin": "$ORIGIN",
  "docker_api": "https://$PUBLIC_IP:$API_PORT",
  "daemon_id": "$DAEMON_ID",
  "container_name": "$CONTAINER_NAME",
  "state_volume": "$STATE_VOLUME",
  "config_directory": "$CONFIG_DIR",
  "config_sha256": null,
  "node_id": "$NODE_ID",
  "manifest_sha256": null,
  "loopback_port": 8080,
  "source_head": null,
  "source_tree": null,
  "image_digest": null
}
# Repository secrets for the deploy consumer (copy file contents, never commit):
#   QIKVRT_LINUX_HOST_CA   <- $TLS_DIR/ca.pem
#   QIKVRT_LINUX_HOST_CERT <- $TLS_DIR/client-cert.pem
#   QIKVRT_LINUX_HOST_KEY  <- $TLS_DIR/client-key.pem
EOF
