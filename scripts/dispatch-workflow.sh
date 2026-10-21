#!/usr/bin/env bash
set -Eeuo pipefail

# Deterministic GitHub Actions workflow_dispatch + run verification.
# Requires: curl, jq, date. Token needs Actions: write and Actions: read.
: "${GH_TOKEN:?`GH_TOKEN` must contain a repository-scoped GitHub token}"
: "${GITHUB_REPOSITORY:?`GITHUB_REPOSITORY` must be owner/repo}"
WORKFLOW_ID="${1:?usage: dispatch-workflow.sh <workflow-id-or-file> [ref]}"
REF="${2:-main}"
API="https://api.github.com"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

api() {
  curl --silent --show-error --fail-with-body \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# GitHub returns 204 on successful workflow_dispatch and no response body.
STATUS="$(curl --silent --show-error --output "$TMP" --write-out '%{http_code}' \
  -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/json" \
  --data "$(jq -cn --arg ref "$REF" '{ref:$ref}')" \
  "$API/repos/$GITHUB_REPOSITORY/actions/workflows/$WORKFLOW_ID/dispatches")"

if [[ "$STATUS" != "204" ]]; then
  printf 'DISPATCH_FAILED http_status=%s\n' "$STATUS" >&2
  if [[ -s "$TMP" ]]; then cat "$TMP" >&2; printf '\n' >&2; fi
  exit 1
fi
printf 'DISPATCH_ACCEPTED http_status=204 workflow=%s ref=%s started_at=%s\n' "$WORKFLOW_ID" "$REF" "$STARTED_AT"

# The dispatch endpoint does not return a run ID. Correlate the new run using
# workflow, event, branch, and a start timestamp captured before POST.
DEADLINE=$(( $(date +%s) + ${POLL_TIMEOUT_SECONDS:-180} ))
while (( $(date +%s) < DEADLINE )); do
  if api "$API/repos/$GITHUB_REPOSITORY/actions/workflows/$WORKFLOW_ID/runs?event=workflow_dispatch&branch=$REF&per_page=20" > "$TMP"; then
    RUN="$(jq -c --arg started "$STARTED_AT" --arg ref "$REF" '
      [.workflow_runs[]
       | select(.event == "workflow_dispatch")
       | select(.head_branch == $ref)
       | select(.created_at >= $started)]
      | sort_by(.created_at, .id)
      | last // empty
    ' "$TMP")"
    if [[ -n "$RUN" ]]; then
      jq -r '"RUN id=\(.id) status=\(.status) conclusion=\(.conclusion // "null") created_at=\(.created_at) url=\(.html_url)"' <<<"$RUN"
      exit 0
    fi
  fi
  sleep 3
done

printf 'RUN_NOT_OBSERVED timeout_seconds=%s workflow=%s ref=%s started_at=%s\n' "${POLL_TIMEOUT_SECONDS:-180}" "$WORKFLOW_ID" "$REF" "$STARTED_AT" >&2
exit 2
