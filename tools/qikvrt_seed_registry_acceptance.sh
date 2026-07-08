#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Ingolf Lohmann.
set -eu
KNOWN="registry/KNOWN_NODE_REQUESTS.tsv"
CORE="/tmp/qikvrt_handshake_core"
if [ ! -x "$CORE" ]; then
  echo "QIKVRT_SEED_ACCEPTANCE BLOCK missing compiled core" >&2
  exit 80
fi
if [ ! -f "$KNOWN" ]; then
  echo "QIKVRT_SEED_ACCEPTANCE BLOCK missing KNOWN_NODE_REQUESTS.tsv" >&2
  exit 81
fi
mkdir -p registry/nodes evidence/seed_acceptance ledger tmp
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ""|\#*) continue ;; esac
  guid=$(printf '%s
' "$line" | cut -f1)
  source_repo=$(printf '%s
' "$line" | cut -f2)
  seed_repo=$(printf '%s
' "$line" | cut -f3)
  request_url=$(printf '%s
' "$line" | cut -f4-)
  if [ -z "$guid" ] || [ -z "$source_repo" ] || [ -z "$seed_repo" ] || [ -z "$request_url" ]; then
    echo "QIKVRT_SEED_ACCEPTANCE BLOCK malformed known-node line" >&2
    exit 82
  fi
  echo "QIKVRT_SEED_ACCEPTANCE CHECK $guid $source_repo"
  curl -fsSL "$request_url" -o tmp/seed_registration_request.json
  "$CORE" seed "$guid" "$source_repo" "$seed_repo" tmp/seed_registration_request.json
  echo "QIKVRT_SEED_ACCEPTANCE PASS $guid"
done < "$KNOWN"
echo "QIKVRT_SEED_ACCEPTANCE_FINAL PASS"
