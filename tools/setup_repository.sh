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
ROLE="node"
VERSION="2.13.4"
DEFAULT_OWNER="Goldkelch"
DEFAULT_REPO="qik-vrt-node"
DEFAULT_SEED_OWNER="Goldkelch"
DEFAULT_SEED_REPO="qik-vrt"
RUNTIME="$ROOT/qikvrt/runtime/setup"
ONBOARD="$ROOT/qikvrt/runtime/onboarding"
mkdir -p "$RUNTIME" "$ONBOARD" "$ROOT/qikvrt/config" "$ROOT/qikvrt/runtime/node"
TSV="$RUNTIME/SETUP_RESULT.tsv"
JSONL="$RUNTIME/SETUP_RESULT.jsonl"
printf 'timestamp_utc	gate	status	detail
' > "$TSV"
: > "$JSONL"
log() { utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ'); printf '%s	%s	%s	%s
' "$utc" "$1" "$2" "$3" | tee -a "$TSV"; printf '{"timestamp_utc":"%s","gate":"%s","status":"%s","detail":"%s"}
' "$utc" "$1" "$2" "$(printf '%s' "$3" | sed 's/"/\"/g')" >> "$JSONL"; }
ask_default() { prompt=$1; def=$2; envname=$3; eval envval=\${$envname:-}; if [ -n "$envval" ]; then printf '%s' "$envval"; return; fi; if [ "${QIKVRT_SETUP_NONINTERACTIVE:-0}" = "1" ]; then printf '%s' "$def"; return; fi; printf '%s [%s]: ' "$prompt" "$def" >&2; IFS= read ans || ans=''; [ -n "$ans" ] || ans=$def; printf '%s' "$ans"; }
log QIKVRT_REPOSITORY_SETUP PASS started
GUID_PATH="$ROOT/qikvrt/runtime/REPOSITORY_GUID.txt"
if [ -s "$GUID_PATH" ]; then GUID=$(cat "$GUID_PATH" | tr -d '
'); log REPOSITORY_GUID PASS "existing $GUID"; else
  if command -v uuidgen >/dev/null 2>&1; then GUID=$(uuidgen | tr 'A-Z' 'a-z'); else GUID=$(python3 - <<'PYG'
import uuid
print(uuid.uuid4())
PYG
); fi
  printf '%s
' "$GUID" > "$GUID_PATH"; log REPOSITORY_GUID PASS "generated $GUID"
fi
printf '%s
' "$GUID" > "$ROOT/qikvrt/runtime/node/REPOSITORY_GUID.txt"
OWNER=$(ask_default 'GitHub target owner/org' "$DEFAULT_OWNER" QIKVRT_GITHUB_OWNER)
REPO=$(ask_default 'GitHub target repository' "$DEFAULT_REPO" QIKVRT_GITHUB_REPO)
SEED_OWNER=$(ask_default 'GitHub seed owner/org' "$DEFAULT_SEED_OWNER" QIKVRT_SEED_OWNER)
SEED_REPO=$(ask_default 'GitHub seed repository' "$DEFAULT_SEED_REPO" QIKVRT_SEED_REPO)
cat > "$ROOT/qikvrt/config/REPOSITORY_TARGET.json" <<EOF
{
  "version": "$VERSION",
  "role": "$ROLE",
  "repository_guid": "$GUID",
  "github_owner": "$OWNER",
  "github_repository": "$REPO",
  "github_repository_full_name": "$OWNER/$REPO",
  "seed_owner": "$SEED_OWNER",
  "seed_repository": "$SEED_REPO",
  "seed_repository_full_name": "$SEED_OWNER/$SEED_REPO",
  "seed_url": "https://github.com/$SEED_OWNER/$SEED_REPO",
  "raw_seed_manifest_url": "https://raw.githubusercontent.com/$SEED_OWNER/$SEED_REPO/main/MANIFEST.json",
  "no_prompt_after_setup": true,
  "node_identifies_to_seed_with_guid": true,
  "remote_mutation_requires_token": true,
  "author": "Ingolf Lohmann",
  "rights_holder": "Ingolf Lohmann or a legal entity designated by him"
}
EOF
log REPOSITORY_TARGET_CONFIG PASS "$OWNER/$REPO seed=$SEED_OWNER/$SEED_REPO"
cat > "$ROOT/qikvrt/config/ONBOARDING.json" <<EOF
{
  "version": "$VERSION",
  "event": "QIKVRT_NODE_ONBOARDING_REQUEST",
  "role": "$ROLE",
  "repository_guid": "$GUID",
  "source_repository": "$OWNER/$REPO",
  "seed_repository": "$SEED_OWNER/$SEED_REPO",
  "seed_url": "https://github.com/$SEED_OWNER/$SEED_REPO",
  "automatic_after_setup": true,
  "no_further_human_machine_interaction_after_setup": true,
  "authorized_manifest_graph_only": true,
  "no_global_scanning": true,
  "no_self_propagation": true,
  "no_remote_mutation_without_authorization": true
}
EOF
cp "$ROOT/qikvrt/config/ONBOARDING.json" "$ONBOARD/SEED_REGISTRATION_REQUEST.json"
log SEED_REGISTRATION_REQUEST PASS "$ONBOARD/SEED_REGISTRATION_REQUEST.json"
log SETUP_RESULT_TSV PASS "$TSV"
log SETUP_RESULT_JSONL PASS "$JSONL"
exit 0
