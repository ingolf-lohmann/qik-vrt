#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Origin: QIK-VRT self-contained GitHub REST/TCP/IP deployment package
# Rights-Holder: Ingolf Lohmann
# Project: QIK-VRT
# Source-Code-License: Apache-2.0
# Non-Source-Code-License: CC BY-NC 4.0 for non-code repository materials
# Notice: See QIKVRT_LICENSE_AND_RIGHTS.md, LICENSE, NOTICE, and .qikvrt/license/.
set -eu
OWNER="${1:?owner}"
REPO="${2:?repo}"
PAYLOAD_FILE="${3:?payload file}"
TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN required in owner-controlled runtime}"
python3 scripts/qikvrt_api_client.py --base-url https://api.github.com --owner "$OWNER" --repo "$REPO" --token "$TOKEN" --payload-file "$PAYLOAD_FILE" --dry-run true
