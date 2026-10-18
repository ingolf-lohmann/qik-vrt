#!/bin/sh
set -eu
if [ "$#" -ne 4 ]; then
    printf '%s\n' 'usage: qikvrt_github_api_client.sh OWNER REPO PAYLOAD_FILE REQUEST_ID' >&2
    exit 2
fi
OWNER="$1"
REPO="$2"
PAYLOAD_FILE="$3"
REQUEST_ID="$4"
: "${GITHUB_TOKEN:?GITHUB_TOKEN required in owner-controlled runtime}"
# Reuse the supplied host binding; never pass credentials in process arguments.
# REQUEST_ID is caller-bound and stable. This wrapper remains dry-run only.
QIKVRT_API_TOKEN="$GITHUB_TOKEN" exec python3 scripts/qikvrt_api_client.py \
    --base-url https://api.github.com --owner "$OWNER" --repo "$REPO" \
    --payload-file "$PAYLOAD_FILE" --request-id "$REQUEST_ID" --dry-run true
