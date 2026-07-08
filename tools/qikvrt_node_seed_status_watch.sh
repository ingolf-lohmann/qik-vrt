#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
set -eu
CONFIG="qikvrt/runtime/onboarding/NODE_HANDSHAKE_CONFIG.tsv"
CORE="/tmp/qikvrt_handshake_core"
if [ ! -x "$CORE" ]; then
  echo "QIKVRT_NODE_STATUS BLOCK missing compiled core" >&2
  exit 90
fi
if [ ! -f "$CONFIG" ]; then
  echo "QIKVRT_NODE_STATUS BLOCK missing NODE_HANDSHAKE_CONFIG.tsv" >&2
  exit 91
fi
mkdir -p qikvrt/runtime/onboarding evidence tmp
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ""|\#*) continue ;; esac
  guid=$(printf '%s
' "$line" | cut -f1)
  source_repo=$(printf '%s
' "$line" | cut -f2)
  seed_repo=$(printf '%s
' "$line" | cut -f3)
  seed_index_url=$(printf '%s
' "$line" | cut -f4-)
  if [ -z "$guid" ] || [ -z "$source_repo" ] || [ -z "$seed_repo" ] || [ -z "$seed_index_url" ]; then
    echo "QIKVRT_NODE_STATUS BLOCK malformed node config line" >&2
    exit 92
  fi
  echo "QIKVRT_NODE_STATUS CHECK $guid $seed_repo"
  curl -fsSL "$seed_index_url" -o tmp/nodemesh_index.json
  "$CORE" node "$guid" "$source_repo" "$seed_repo" tmp/nodemesh_index.json
  echo "QIKVRT_NODE_STATUS PASS $guid"
done < "$CONFIG"
echo "QIKVRT_NODE_SEED_STATUS_FINAL PASS"
