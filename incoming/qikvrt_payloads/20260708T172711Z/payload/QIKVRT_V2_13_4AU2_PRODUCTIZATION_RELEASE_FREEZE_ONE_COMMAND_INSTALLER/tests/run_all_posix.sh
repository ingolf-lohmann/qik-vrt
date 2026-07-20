#!/usr/bin/env sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"

fail(){ echo "BLOCK $1"; exit 1; }
pass(){ echo "PASS $1"; }

[ -f START_HIER_RELEASE_FREEZE_INSTALL.cmd ] || fail missing_start_cmd
[ -f tools/qikvrt_4au2_release_freeze_installer.js ] || fail missing_installer_js
find . -name '*.ps1' | grep -q . && fail ps1_file_present || pass no_ps1_file_present
if grep -R "powershell\.exe\|pwsh\.exe" . >/dev/null 2>&1; then fail powershell_execution_marker_present; else pass no_powershell_execution_marker; fi
if grep -R "cmd /c git\|^git \| git " tools START_HIER_RELEASE_FREEZE_INSTALL.cmd >/dev/null 2>&1; then fail git_command_marker_present; else pass no_git_command_marker; fi
if grep -R "github_pat_\|ghp_\|gho_\|ghu_\|ghs_" README.md README_DE.md README_EN.md CONTRACT_STATUS.md COPYRIGHT_AND_LICENSE_ACCEPTANCE.md VERSION.json START_HIER_RELEASE_FREEZE_INSTALL.cmd tools >/dev/null 2>&1; then fail embedded_token_marker_present; else pass no_embedded_token_marker; fi
if command -v node >/dev/null 2>&1; then node --check tools/qikvrt_4au2_release_freeze_installer.js >/dev/null; pass installer_js_syntax_node_check; else pass node_not_available_syntax_check_skipped; fi
grep -q "MASKED_TOKEN_PROMPT" tools/qikvrt_4au2_release_freeze_installer.js || fail masked_token_prompt_missing
grep -q "RELEASE_ALREADY_EXISTS_NO_TAG_MOVE" tools/qikvrt_4au2_release_freeze_installer.js || fail no_tag_move_guard_missing
grep -q "createRelease" tools/qikvrt_4au2_release_freeze_installer.js || fail create_release_missing
grep -q "release/qikvrt_4au1" tools/qikvrt_4au2_release_freeze_installer.js || fail release_freeze_paths_missing
pass QIKVRT_4AU2_RELEASE_FREEZE_CONTRACT_PASS
