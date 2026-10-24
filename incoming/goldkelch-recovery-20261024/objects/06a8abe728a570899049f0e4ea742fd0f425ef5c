# QIKVRT 2.13.4H Windows Inline Script Scope Ledger Repair

DE: Externer Windows-Retest von 2.13.4G bestaetigte den neuen Inline-Host (`QIKVRT_POWERSHELL_SCRIPT_HOST PASS`), brach danach jedoch in `tools\setup_repository.ps1` unter `Set-StrictMode` ab: `$script:Rows` war nicht gesetzt.

EN: External Windows retest of 2.13.4G confirmed the new inline host (`QIKVRT_POWERSHELL_SCRIPT_HOST PASS`), but then aborted in `tools\setup_repository.ps1` under `Set-StrictMode`: `$script:Rows` was not set.

Root cause:
- Under the previous `powershell -File` execution model, an unscoped `$Rows = @()` initializer was effectively available as the script ledger used by `Add-*Result` functions.
- Under the AllSigned-safe inline `ScriptBlock` host, functions referencing `$script:Rows` require explicit `$script:Rows = @()` initialization.

Repair:
- `tools/setup_repository.ps1`: `$script:Rows = @()` and serialization from `$script:Rows`.
- `tools/choco_bootstrap.ps1`: `$script:Rows = @()`.
- `tools/gh_deploy.ps1`: `$script:Rows = @()` and serialization from `$script:Rows`.
- `tools/register_with_seed.ps1`: `$script:Rows = @()` and serialization/pass-count from `$script:Rows`.
- `tests/test_cb.sh`: non-regression gate forbids unscoped `$Rows = @()` in these inline-hosted scripts.

Boundary: This repair is sandbox/static/POSIX-verified. External Windows Defender, PowerShell 5.1 policy, and live GitHub upload retest remain owner-side.
