# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
ROOT=${1:-.}
BIN="$ROOT/build/qikvrt_verify"
OUTDIR="$ROOT/qikvrt/evidence"
mkdir -p "$OUTDIR"
MANIFEST_URL='https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/MANIFEST.json'
API_URL='https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json'
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$MANIFEST_URL" -o "$OUTDIR/gh_manifest_live.json"
  curl -fsSL "$API_URL" -o "$OUTDIR/gh_api_live.json"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$OUTDIR/gh_manifest_live.json" "$MANIFEST_URL"
  wget -qO "$OUTDIR/gh_api_live.json" "$API_URL"
else
  echo 'BLOCK no curl or wget available for external live GitHub fetch' >&2
  exit 3
fi
"$BIN" --validate-github-seed-manifest "$OUTDIR/gh_manifest_live.json"
"$BIN" --validate-github-seed-manifest "$OUTDIR/gh_api_live.json"
{
  echo '{'
  echo '  "evidence": "EXTERNAL_LIVE_GITHUB_FETCH",'
  echo '  "seed": "https://github.com/Goldkelch/qik-vrt",'
  echo '  "manifest": "MANIFEST.json",'
  echo '  "rest_tcpip_manifest": "QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json",'
  echo '  "status_markers": ["GITHUB_WEB_VISIBILITY_PASS", "RAW_MANIFEST_REFERENCE_PASS", "REST_TCPIP_MANIFEST_REFERENCE_PASS", "EXTERNAL_LIVE_FETCH_REQUIRED", "NO_FALSE_LIVE_PASS"],'
  echo '  "result": "EXTERNAL_LIVE_FETCH_PASS"'
  echo '}'
} > "$OUTDIR/gh_live_fetch_result.json"
echo 'PASS external live GitHub seed fetch'
