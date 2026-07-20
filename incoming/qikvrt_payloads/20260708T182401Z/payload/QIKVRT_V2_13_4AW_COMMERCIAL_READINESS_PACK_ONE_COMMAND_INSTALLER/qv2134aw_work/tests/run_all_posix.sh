#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
fail(){ echo "BLOCK $1"; exit 1; }
[ -f START_HIER_COMMERCIAL_READINESS_UPLOAD.cmd ] || fail MISSING_START_CMD
[ -f tools/qikvrt_4aw_uploader.js ] || fail MISSING_UPLOADER_JS
[ -d roles/seed/docs/qikvrt_trust_mesh ] || fail MISSING_SEED_DOCS
[ -d roles/node/docs/qikvrt_trust_mesh ] || fail MISSING_NODE_DOCS
[ -f docs/AI_ACT_NACHWEISPFLICHT_DOSSIER_DE.md ] || fail MISSING_AI_ACT_DOSSIER
[ -f docs/KUENSTLICHE_KOGNITION_UND_ONTOLOGIE_DE.md ] || fail MISSING_KOGNITION_DOC
[ -f docs/RISK_AND_CLAIMS_BOUNDARY_DE.md ] || fail MISSING_CLAIMS_BOUNDARY
find . -name '*.ps1' | grep . && fail PS1_FILE_PRESENT || true
find . -path ./tests -prune -o -type f -print | xargs grep -l "github_pat_" >/dev/null 2>&1 && fail EMBEDDED_PAT_TOKEN || true
find . -path ./tests -prune -o -type f -print | xargs grep -l "ghp_" >/dev/null 2>&1 && fail EMBEDDED_CLASSIC_TOKEN || true
grep -R "git push\|git clone\|git commit" START_HIER_COMMERCIAL_READINESS_UPLOAD.cmd tools/qikvrt_4aw_uploader.js >/dev/null 2>&1 && fail GIT_COMMAND_PATH_PRESENT || true
grep -R "powershell.exe\|pwsh.exe\| -ExecutionPolicy " START_HIER_COMMERCIAL_READINESS_UPLOAD.cmd tools/qikvrt_4aw_uploader.js >/dev/null 2>&1 && fail POWERSHELL_EXECUTION_MARKER || true
node --check tools/qikvrt_4aw_uploader.js >/dev/null 2>&1 || fail JS_SYNTAX
SEED_COUNT=$(find roles/seed -type f | wc -l | tr -d ' ')
NODE_COUNT=$(find roles/node -type f | wc -l | tr -d ' ')
[ "$SEED_COUNT" -ge 10 ] || fail SEED_DOC_COUNT_TOO_LOW
[ "$NODE_COUNT" -ge 10 ] || fail NODE_DOC_COUNT_TOO_LOW
echo "ZIP_PRECHECK PASS"
echo "SEED_DOCS_COUNT $SEED_COUNT"
echo "NODE_DOCS_COUNT $NODE_COUNT"
echo "QIKVRT_4AW_COMMERCIAL_READINESS_CONTRACT_PASS"
