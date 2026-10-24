#!/bin/sh
# QIKVRT Artifact Header
# Version: 2.13.4R
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
set -eu
# The 2.13.4R node deploy path must not create/upload GitHub releases locally.
! grep -q 'Invoke-RestMethod' tools/gh_deploy.ps1
! grep -q 'api.github.com/repos.*releases' tools/gh_deploy.ps1
! grep -q 'upload_url' tools/gh_deploy.ps1
! grep -q 'curl .*api.github.com/repos.*/releases' tools/gh_deploy.sh
! grep -q 'upload_url' tools/gh_deploy.sh
# It must push branch/tag by git and rely on target-repository workflow.
grep -q 'git.*push' tools/gh_deploy.sh
grep -q 'GIT_PUSH_TAG' tools/gh_deploy.ps1
grep -q 'System.Diagnostics.ProcessStartInfo' tools/gh_deploy.ps1
grep -q 'GIT_NATIVE_STDERR_CAPTURE' tools/gh_deploy.ps1
grep -q 'GIT_OPTIONAL_PROBE_CAPTURE' tools/gh_deploy.ps1
grep -q 'GIT_NONINTERACTIVE_ENV' tools/gh_deploy.ps1
grep -q 'GIT_TIMEOUT_GATE' tools/gh_deploy.ps1
grep -q 'GIT_FUNCTION_OUTPUT_SCALAR_GATE' tools/gh_deploy.ps1
grep -q 'GIT_CORE_AUTOCRLF' tools/gh_deploy.ps1
grep -q 'GIT_CORE_EOL' tools/gh_deploy.ps1
grep -q 'QIKVRT_GIT_TIMEOUT_SECONDS' tools/gh_deploy.ps1
grep -q 'GIT_TERMINAL_PROMPT' tools/gh_deploy.ps1
grep -q 'GCM_INTERACTIVE' tools/gh_deploy.ps1
grep -q 'http.https://github.com/.extraheader' tools/gh_deploy.ps1
! grep -q 'New-AskPass' tools/gh_deploy.ps1
grep -q 'NODE_GIT_PUSH_INTERACTIVE_CREDENTIAL_HANG' release/QV2134R_NODE_GIT_IDEMPOTENT_TAG_PUSH_REPAIR_REF.md
grep -q 'NODE_GIT_ARCHIVE_PATH_ARRAY_DRIVE_PARSE_FAILURE' release/QV2134R_NODE_GIT_IDEMPOTENT_TAG_PUSH_REPAIR_REF.md
grep -q "'remote', 'add', 'origin'" tools/gh_deploy.ps1
grep -q "'remote', 'set-url', 'origin'" tools/gh_deploy.ps1
grep -q 'remote get-url origin' release/QV2134R_NODE_GIT_IDEMPOTENT_TAG_PUSH_REPAIR_REF.md
test -f .github/workflows/qikvrt_node_release.yml
grep -q 'contents: write' .github/workflows/qikvrt_node_release.yml
grep -q 'gh release create' .github/workflows/qikvrt_node_release.yml
# Workflow must not regenerate the artifact; it must upload the committed artifact.
! grep -q 'git archive --format=zip' .github/workflows/qikvrt_node_release.yml
grep -q 'release/artifacts/qv2134_node.zip' .github/workflows/qikvrt_node_release.yml
grep -q 'qv2134_node.zip' .github/workflows/qikvrt_node_release.yml
grep -q 'v2.13.4-node-r' tools/gh_deploy.ps1
grep -q 'GIT_PUSH_BRANCH_CONFLICT_FALLBACK' tools/gh_deploy.ps1
grep -q 'Get-GitShortObjectId' tools/gh_deploy.ps1
grep -q 'v2.13.4-node-r' .github/workflows/qikvrt_node_release.yml
grep -q 'NODE_FORWARD_ONLY_TAG_BRANCH_CONFLICT' release/QV2134R_NODE_FORWARD_ONLY_TAG_BRANCH_CONFLICT_REPAIR_REF.md || grep -q 'forward-only tag/branch conflict' release/QV2134R_NODE_FORWARD_ONLY_TAG_BRANCH_CONFLICT_REPAIR_REF.md
printf '%s\n' 'PASS node git function output scalar repair gates'
grep -q 'GIT_IDEMPOTENT_TAG_GATE' tools/gh_deploy.ps1
grep -q 'GIT_TAG_EXISTS_REUSE' tools/gh_deploy.ps1
grep -q 'Push-TagIdempotent' tools/gh_deploy.ps1
grep -q 'Push-BranchBestEffort' tools/gh_deploy.ps1
grep -q 'GIT_PUSH_TAG_IDEMPOTENT' tools/gh_deploy.ps1
grep -q 'qikvrt-node/' tools/gh_deploy.ps1
grep -q 'NODE_LOCAL_TAG_EXISTS_IDEMPOTENCE_BLOCKS_PUSH_AFTER_PARTIAL_RUN' release/QV2134R_NODE_GIT_IDEMPOTENT_TAG_PUSH_REPAIR_REF.md
echo 'PASS node git idempotent tag push repair gates'

# QIKVRT 2.13.4R hash parity checks
grep -q "NODE_HASH_PARITY_GATE" tools/gh_deploy.ps1
grep -q "release/artifacts/qv2134_node.zip" .github/workflows/qikvrt_node_release.yml
grep -q "uploads the committed artifact verbatim" .github/workflows/qikvrt_node_release.yml
grep -F -q "release/artifacts/** export-ignore" .gitattributes
