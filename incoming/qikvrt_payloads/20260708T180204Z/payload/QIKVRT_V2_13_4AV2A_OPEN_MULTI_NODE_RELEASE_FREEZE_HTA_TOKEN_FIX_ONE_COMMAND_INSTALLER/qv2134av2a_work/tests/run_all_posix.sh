#!/usr/bin/env sh
set -eu
root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$root"
node --check tools/qikvrt_release_freeze_wsh.js >/dev/null
if grep -R "Sub Window_OnLoad:" -n tools/qikvrt_release_freeze_wsh.js; then
  echo "BLOCK legacy inline VBScript HTA syntax still present"
  exit 1
fi
if ! grep -q 'language=\\"javascript\\"' tools/qikvrt_release_freeze_wsh.js; then
  echo "BLOCK HTA JavaScript token prompt marker missing"
  exit 1
fi
if find . -name '*.ps1' | grep -q .; then
  echo "BLOCK ps1 present"
  exit 1
fi
if grep -R "shell.Run(.*powershell\|shell.Run(.*pwsh\|cscript.*powershell\|cmd /c powershell" -ni START_HIER_RELEASE_FREEZE_INSTALL.cmd tools; then
  echo "BLOCK PowerShell execution marker present"
  exit 1
fi
if grep -R "shell.Run(.*git \|cmd /c git \|exec.*git " -ni START_HIER_RELEASE_FREEZE_INSTALL.cmd tools; then
  echo "BLOCK Git command execution marker present"
  exit 1
fi
if grep -R "github[_]pat_\|gh[p]_" -n --exclude=run_all_posix.sh .; then
  echo "BLOCK embedded token marker present"
  exit 1
fi
echo "QIKVRT_4AV2A_RELEASE_FREEZE_HTA_TOKEN_FIX_CONTRACT_PASS"
