#!/bin/sh
# QIKVRT Artifact Header
# Version: 2.13.4
# Deutsch: Generisches Repository-Setup mit GUID-Persistenz und GitHub-Zielkonfiguration.
# English: Generic repository setup with GUID persistence and GitHub target configuration.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME="$ROOT/qikvrt/runtime/onboarding"
mkdir -p "$RUNTIME"
TSV="$RUNTIME/REGISTER_WITH_SEED_RESULT.tsv"
printf 'timestamp_utc	gate	status	detail
' > "$TSV"
log() { utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ'); printf '%s	%s	%s	%s
' "$utc" "$1" "$2" "$3" | tee -a "$TSV"; }
TARGET="$ROOT/qikvrt/config/REPOSITORY_TARGET.json"
ONBOARD="$ROOT/qikvrt/config/ONBOARDING.json"
[ -f "$TARGET" ] || { log REGISTER_CONFIG BLOCK 'REPOSITORY_TARGET.json missing; run setup first'; exit 3; }
[ -f "$ONBOARD" ] || { log REGISTER_CONFIG BLOCK 'ONBOARDING.json missing; run setup first'; exit 3; }
seed_owner=$(sed -n 's/.*"seed_owner"[[:space:]]*:[[:space:]]*"\([^"]*\)".*//p' "$TARGET" | head -n 1)
seed_repo=$(sed -n 's/.*"seed_repository"[[:space:]]*:[[:space:]]*"\([^"]*\)".*//p' "$TARGET" | head -n 1)
guid=$(sed -n 's/.*"repository_guid"[[:space:]]*:[[:space:]]*"\([^"]*\)".*//p' "$TARGET" | head -n 1)
log REGISTER_CONFIG PASS "guid=$guid seed=$seed_owner/$seed_repo"
if [ -z "${GITHUB_TOKEN:-}" ]; then log REGISTER_WITH_SEED BLOCK 'missing GITHUB_TOKEN; registration request persisted locally, no remote mutation performed'; exit 3; fi
command -v curl >/dev/null 2>&1 || { log REGISTER_WITH_SEED BLOCK 'curl missing'; exit 3; }
body=$(printf '{"event_type":"qikvrt_node_onboarding","client_payload":{"repository_guid":"%s","seed_repository":"%s/%s"}}' "$guid" "$seed_owner" "$seed_repo")
code=$(curl -sS -o "$RUNTIME/register_response.json" -w '%{http_code}' -X POST -H "Authorization: Bearer $GITHUB_TOKEN" -H 'Accept: application/vnd.github+json' -H 'Content-Type: application/json' "https://api.github.com/repos/$seed_owner/$seed_repo/dispatches" --data "$body" || true)
if [ "$code" = "204" ]; then log REGISTER_WITH_SEED PASS "repository_dispatch to $seed_owner/$seed_repo"; exit 0; fi
log REGISTER_WITH_SEED BLOCK "http=$code"; exit 3
