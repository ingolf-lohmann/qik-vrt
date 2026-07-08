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
while IFS='\t' read -r guid source_repo seed_repo seed_index_url; do
  case "$guid" in ""|\#*) continue ;; esac
  echo "QIKVRT_NODE_STATUS CHECK $guid $seed_repo"
  curl -fsSL "$seed_index_url" -o tmp/nodemesh_index.json
  "$CORE" node "$guid" "$source_repo" "$seed_repo" tmp/nodemesh_index.json
  echo "QIKVRT_NODE_STATUS PASS $guid"
done < "$CONFIG"
echo "QIKVRT_NODE_SEED_STATUS_FINAL PASS"
