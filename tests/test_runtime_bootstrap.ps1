<#
Copyright 2026 Ingolf Lohmann.
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Native Windows adapter for the existing runtime/bootstrap lifecycle tests.
Preparation is separate: SourceCache must already contain the locked ZIP.
#>
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$SourceCache,
      [Parameter(Mandatory = $true)][string]$EvidenceDir)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$spec = Get-Content -LiteralPath (Join-Path $repo 'runtime/toolchains/python-3.12.10-embed-amd64.payload.json') -Raw | ConvertFrom-Json
$relative = 'python-embed/3.12.10/windows-amd64/sha256/' + $spec.archive_sha256
$sourceArchive = Join-Path $SourceCache ($relative + '/archive/' + $spec.archive)
if (-not (Test-Path -LiteralPath $sourceArchive -PathType Leaf)) { throw 'Missing already materialized source archive' }
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourceArchive).Hash.ToLowerInvariant() -ne $spec.archive_sha256) {
    throw 'Source archive is not the locked payload'
}
if (-not [Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([Runtime.InteropServices.OSPlatform]::Windows) -or
    [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -ne 'X64') { throw 'Native Windows x64 is required' }

New-Item -ItemType Directory -Path $EvidenceDir -Force | Out-Null
$git = (Get-Command git -CommandType Application | Select-Object -First 1).Source
$head = (& $git -C $repo rev-parse HEAD).Trim()
$tree = (& $git -C $repo rev-parse 'HEAD^{tree}').Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot bind the native source tree' }
$scratch = Join-Path ([IO.Path]::GetTempPath()) ('qikvrt-win-offline-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $scratch | Out-Null
$carrierCache = Join-Path $scratch 'QIK VRT offline carrier'
$carrierRoot = Join-Path $carrierCache $relative
$carrierArchive = Join-Path $carrierRoot ('archive/' + $spec.archive)
$runtime = Join-Path $carrierRoot 'runtime'
$pythonPath = Join-Path $runtime 'python.exe'
New-Item -ItemType Directory -Path (Split-Path -Parent $carrierArchive) -Force | Out-Null
Copy-Item -LiteralPath $sourceArchive -Destination $carrierArchive
$bootstrap = Join-Path $repo 'tools/bootstrap-runtime.ps1'
$hostExe = (Get-Process -Id $PID).Path
$inboxHost = Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$cmdExe = Join-Path $env:SystemRoot 'System32/cmd.exe'
$launcher = Join-Path $repo 'qikvrt.cmd'
$oldPath = $env:PATH
$oldCache = $env:QIKVRT_TOOLCHAIN_CACHE
$oldFailureHook = $env:QIKVRT_TEST_FAIL_WINDOWS_PYTHON_FINAL_VERIFY
$rules = @()
$profiles = @()
$controls = [ordered]@{}
$firewallEnabled = $false
$releaseControls = [ordered]@{}

function Test-ReleaseAssetRestore {
    # Execute the existing production restore functions with an explicitly local
    # transport fixture. No public release, live network or publication is proved.
    $RepoRoot = $repo
    $tokens = $null; $errors = $null
    $ast = [Management.Automation.Language.Parser]::ParseFile($bootstrap, [ref]$tokens, [ref]$errors)
    if ($errors.Count -ne 0) { throw 'Cannot parse release restore functions' }
    $names = @('Assert-NoReparseChain', 'Write-WindowsPythonStep', 'Assert-WindowsPythonArchive',
        'Get-WindowsPythonReleaseBinding', 'Restore-WindowsPythonReleaseAsset')
    foreach ($function in $ast.FindAll({ param($node)
            $node -is [Management.Automation.Language.FunctionDefinitionAst] }, $true)) {
        if ($names -contains $function.Name) { . ([scriptblock]::Create($function.Extent.Text)) }
    }
    $binding = [pscustomobject]@{ Spec = $spec }
    $bound = Get-WindowsPythonReleaseBinding $binding
    $release = $bound.Candidate
    $script:releaseFixtureMode = 'valid'
    $script:releaseFixtureRequests = @()
    function Invoke-RestMethod {
        param($Uri, $TimeoutSec)
        $script:releaseFixtureRequests += $Uri
        if ($script:releaseFixtureMode -eq 'missing') { throw 'fixture HTTP 404: missing release asset' }
        return [pscustomobject]@{ draft = $false; immutable = $true; tag_name = $release.tag; assets = @(
            [pscustomobject]@{ name = $release.archive.asset_name; state = 'uploaded';
                size = $spec.archive_bytes; digest = 'sha256:' + $spec.archive_sha256 },
            [pscustomobject]@{ name = 'qikvrt-runtime-carrier-sha256-' + $bound.Hash + '.json';
                state = 'uploaded'; size = (Get-Item $bound.Path).Length; digest = 'sha256:' + $bound.Hash }) }
    }
    function Invoke-WebRequest {
        param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec)
        $script:releaseFixtureRequests += $Uri
        if ($Uri -eq $release.download_url) {
            Copy-Item -LiteralPath $sourceArchive -Destination $OutFile
            if ($script:releaseFixtureMode -eq 'tamper') {
                $bytes = [IO.File]::ReadAllBytes($OutFile); $bytes[0] = $bytes[0] -bxor 1
                [IO.File]::WriteAllBytes($OutFile, $bytes)
            }
        } else { Copy-Item -LiteralPath $bound.Path -Destination $OutFile }
    }
    $destination = Join-Path $scratch 'release-restore.zip'
    Restore-WindowsPythonReleaseAsset $binding $destination
    Assert-WindowsPythonArchive $binding $destination
    $releaseControls['restore'] = @{ result = 'PASS'; transport = 'LOCAL_FIXTURE'; public_download_observed = $false }
    $rejected = $false
    try { Restore-WindowsPythonReleaseAsset $binding $destination } catch { $rejected = $true }
    if (-not $rejected) { throw 'Release restore replaced an existing file' }
    Assert-WindowsPythonArchive $binding $destination
    $releaseControls['no-clobber'] = @{ result = 'PASS'; existing_bytes_preserved = $true }
    foreach ($mode in @('missing', 'tamper')) {
        $script:releaseFixtureMode = $mode
        $target = Join-Path $scratch ($mode + '-release.zip')
        $rejected = $false
        try { Restore-WindowsPythonReleaseAsset $binding $target } catch { $rejected = $true }
        if (-not $rejected) { throw "Release restore accepted $mode material" }
        if ($mode -eq 'missing' -and (Test-Path $target)) { throw 'Missing asset created payload' }
        if (Test-Path $target) { Remove-Item -LiteralPath $target -Force }
        if (Test-Path ($target + '.metadata')) { throw 'Failed release restore retained companion staging' }
        $releaseControls[$mode] = @{ result = 'PASS'; upstream_fallback = $false }
    }
    if (@($script:releaseFixtureRequests | Where-Object { $_ -match 'python.org' }).Count -ne 0) {
        throw 'Release failure reached the upstream reconstruction path'
    }
    Assert-WindowsPythonArchive $binding $destination
    $releaseControls['rollback'] = @{ result = 'PASS'; prior_verified_archive_preserved = $true }
}

function Invoke-TestProcess([string]$Name, [string]$Exe, [string]$Arguments, [int]$Expected) {
    $info = [Diagnostics.ProcessStartInfo]::new()
    $info.FileName = $Exe
    $info.Arguments = $Arguments
    $info.WorkingDirectory = $repo
    $info.UseShellExecute = $false
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $info
    try {
        if (-not $process.Start()) { throw "$Name could not start" }
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit(30000)) {
            $process.Kill()
            [void]$process.WaitForExit(2000)
            throw "$Name exceeded its 30-second bound"
        }
        [IO.File]::WriteAllText((Join-Path $EvidenceDir "$Name.stdout.txt"), $stdout.Result)
        [IO.File]::WriteAllText((Join-Path $EvidenceDir "$Name.stderr.txt"), $stderr.Result)
        if ($process.ExitCode -ne $Expected) {
            throw "$Name expected $Expected, observed $($process.ExitCode): $($stderr.Result) $($stdout.Result)"
        }
        Write-Output "PASS: $Name (exit $Expected)"
    } finally { $process.Dispose() }
}

function Invoke-BootstrapTest([string]$Name, [string[]]$Parameters, [int]$Expected) {
    $command = "`$ErrorActionPreference = 'Stop'; & '" + $bootstrap.Replace("'", "''") + "' "
    foreach ($value in $Parameters) {
        if ($value -match '^-(CheckOnly|Install|AcceptThirdParty|Profile|CacheDir|RuntimeReceiptFile|ReconstructUpstream)$') {
            $command += $value + ' '
        } else { $command += "'" + $value.Replace("'", "''") + "' " }
    }
    $command += '; exit $LASTEXITCODE'
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    Invoke-TestProcess $Name $hostExe ('-NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand ' + $encoded) $Expected
}

function Invoke-LauncherTest([string]$Name, [string]$Arguments, [int]$Expected) {
    Invoke-TestProcess $Name $cmdExe ('/d /s /c ""' + $launcher + '" ' + $Arguments + '"') $Expected
}

function Assert-NoLauncherEffect([string]$Name, [scriptblock]$Test) {
    $before = @(Get-ChildItem -LiteralPath (Join-Path $repo 'logs') -Filter '*.jsonl' -ErrorAction SilentlyContinue).Count
    & $Test
    $after = @(Get-ChildItem -LiteralPath (Join-Path $repo 'logs') -Filter '*.jsonl' -ErrorAction SilentlyContinue).Count
    if ($before -ne $after) { throw "$Name reached the Python launcher before rejecting its cache" }
    $controls[$Name] = @{ result = 'PASS'; exit_code = 1; launcher_executed = $false }
}

try {
    Test-ReleaseAssetRestore
    # All executable processes on the start path are denied outbound traffic at
    # the OS level. Source/Action transport runs outside this proof interval.
    $profiles = @(Get-NetFirewallProfile | Select-Object Name, Enabled)
    Set-NetFirewallProfile -Profile Domain, Private, Public -Enabled True
    $firewallEnabled = $true
    foreach ($program in @($hostExe, $inboxHost, $cmdExe, $pythonPath) | Select-Object -Unique) {
        $name = 'qikvrt-offline-' + [guid]::NewGuid().ToString('N')
        New-NetFirewallRule -Name $name -DisplayName $name -Direction Outbound -Action Block `
            -Program $program -Profile Any -Enabled True | Out-Null
        $rules += $name
        $rule = Get-NetFirewallRule -Name $name
        $filter = $rule | Get-NetFirewallApplicationFilter
        if ($rule.Action -ne 'Block' -or $rule.Enabled -ne 'True' -or $filter.Program -ne $program) {
            throw 'Firewall program binding did not read back'
        }
    }
    if (@(Get-NetFirewallProfile | Where-Object { $_.Enabled -ne 'True' }).Count -ne 0) {
        throw 'Firewall egress denial requires every profile enabled'
    }
    $request = [Net.HttpWebRequest]::Create('https://www.python.org/')
    $request.Timeout = 2000
    $request.ReadWriteTimeout = 2000
    $request.Proxy = $null
    $networkDenied = $false
    try { $response = $request.GetResponse(); $response.Close() }
    catch {
        $probeException = $_.Exception
        while ($null -ne $probeException -and $probeException -isnot [Net.WebException]) {
            $probeException = $probeException.InnerException
        }
        if ($probeException -is [Net.WebException] -and $null -eq $probeException.Response) { $networkDenied = $true }
        else { throw }
    }
    if (-not $networkDenied) { throw 'OS egress control allowed a live upstream connection' }

    # py.exe may be installed directly in SystemRoot. Every executable on the
    # witness path is already absolute, so expose only a fresh empty directory.
    $emptyPath = Join-Path $scratch 'empty-path'
    New-Item -ItemType Directory -Path $emptyPath | Out-Null
    $env:PATH = $emptyPath
    $env:QIKVRT_TOOLCHAIN_CACHE = $carrierCache
    Remove-Item Env:QIKVRT_TEST_FAIL_WINDOWS_PYTHON_FINAL_VERIFY -ErrorAction SilentlyContinue
    if (@(Get-Command py, python, python3 -CommandType Application -ErrorAction SilentlyContinue).Count -ne 0) {
        throw 'An ambient Python command remained exposed in the offline witness'
    }
    Invoke-BootstrapTest 'check-only-archive' @('-CheckOnly', '-Profile', 'windows-start', '-CacheDir', $carrierCache) 20
    if (Test-Path -LiteralPath $runtime) { throw 'Check-only derived a runtime' }
    Invoke-LauncherTest 'cold-offline-self-test' '--runtime-self-test' 0
    Invoke-LauncherTest 'cold-offline-launcher-help' '--help' 0
    Invoke-LauncherTest 'warm-offline-launcher-help' '--help' 0
    Invoke-LauncherTest 'effect-acceptance-retained' 'master-gate' 20
    $logTest = @'
import hashlib, json, pathlib, subprocess, sys, tempfile
sys.path.insert(0, sys.argv[1])
from tools import qikvrt_runtime_logger as qlog
with tempfile.TemporaryDirectory(prefix='qikvrt-native-log-') as directory:
    root = pathlib.Path(directory)
    qlog.LOG_DIR = root
    qlog.LOG_FILE = root / 'shared.jsonl'
    qlog.reset_log('native-concurrent-log-contract')
    code = "import pathlib,sys; sys.path.insert(0,sys.argv[1]); from tools import qikvrt_runtime_logger as q; q.LOG_DIR=pathlib.Path(sys.argv[2]); q.LOG_FILE=q.LOG_DIR/'shared.jsonl'; [q.write_event('concurrent_writer',index=i) for i in range(8)]"
    children = [subprocess.Popen([sys.executable, '-I', '-B', '-c', code, sys.argv[1], directory],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    for child in children:
        output, error = child.communicate(timeout=20)
        assert child.returncode == 0, (output, error)
    records = [json.loads(line) for line in qlog.LOG_FILE.read_text().splitlines()]
    assert sum(record['event'] == 'concurrent_writer' for record in records) == 16
    qlog.finish(0)
    pointer = json.loads((root / 'qikvrt_last_run.json').read_text())
    assert pointer['sha256'] == hashlib.sha256(qlog.LOG_FILE.read_bytes()).hexdigest()
    outside = root / 'outside.txt'
    outside.write_bytes(b'unchanged')
    alias = root / 'hardlink.jsonl'
    alias.hardlink_to(outside)
    qlog.LOG_FILE = alias
    try:
        qlog.write_event('untrusted_alias')
    except OSError:
        pass
    else:
        raise AssertionError('logger accepted a hardlink alias')
    assert outside.read_bytes() == b'unchanged'
print('PASS native Windows concurrent log locking, atomic pointer and alias rejection')
'@
    $logCode = "exec(__import__('base64').b64decode('" +
        [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($logTest)) + "'))"
    Invoke-TestProcess 'native-log-contract' $pythonPath ('-I -B -c "' + $logCode + '" "' + $repo + '"') 0
    $controls['native-log-contract'] = @{ result = 'PASS'; concurrent_writers = 2; complete_records = 16; alias_rejected = $true }
    $receiptPath = Join-Path $EvidenceDir 'CACHE_SELF_TEST.json'
    Invoke-BootstrapTest 'offline-cache-readback' @('-CheckOnly', '-Profile', 'windows-start',
        '-CacheDir', $carrierCache, '-RuntimeReceiptFile', $receiptPath) 0
    $cacheReceipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    if ($cacheReceipt.upstream_download_performed -or $cacheReceipt.version -ne '3.12.10' -or
        $cacheReceipt.self_test.executable -ne $pythonPath) { throw 'Offline runtime receipt mismatch' }

    Assert-NoLauncherEffect 'missing-cache' {
        $env:QIKVRT_TOOLCHAIN_CACHE = Join-Path $scratch 'missing'
        try { Invoke-LauncherTest 'missing-cache' '--help' 1 }
        finally { $env:QIKVRT_TOOLCHAIN_CACHE = $carrierCache }
    }
    Assert-NoLauncherEffect 'tampered-archive' {
        $bytes = [IO.File]::ReadAllBytes($carrierArchive)
        $bytes[$bytes.Length - 1] = $bytes[$bytes.Length - 1] -bxor 1
        [IO.File]::WriteAllBytes($carrierArchive, $bytes)
        try { Invoke-LauncherTest 'tampered-archive' '--help' 1 }
        finally { Copy-Item -LiteralPath $sourceArchive -Destination $carrierArchive -Force }
    }
    Assert-NoLauncherEffect 'missing-archive' {
        $saved = Join-Path $scratch 'saved-archive.zip'
        Move-Item -LiteralPath $carrierArchive -Destination $saved
        try { Invoke-LauncherTest 'missing-archive' '--help' 1 }
        finally { Move-Item -LiteralPath $saved -Destination $carrierArchive }
    }
    Assert-NoLauncherEffect 'tampered-executable' {
        $original = [IO.File]::ReadAllBytes($pythonPath)
        $changed = [byte[]]$original.Clone()
        $changed[$changed.Length - 1] = $changed[$changed.Length - 1] -bxor 1
        [IO.File]::WriteAllBytes($pythonPath, $changed)
        try { Invoke-LauncherTest 'tampered-executable' '--help' 1 }
        finally { [IO.File]::WriteAllBytes($pythonPath, $original) }
    }
    Assert-NoLauncherEffect 'missing-stdlib' {
        $stdlib = Join-Path $runtime 'python312.zip'
        $saved = Join-Path $scratch 'saved-stdlib.zip'
        Move-Item -LiteralPath $stdlib -Destination $saved
        try { Invoke-LauncherTest 'missing-stdlib' '--help' 1 }
        finally { Move-Item -LiteralPath $saved -Destination $stdlib }
    }
    Assert-NoLauncherEffect 'unexpected-module' {
        $extra = Join-Path $runtime 'sitecustomize.py'
        [IO.File]::WriteAllText($extra, 'raise RuntimeError("untrusted cache module")')
        try { Invoke-LauncherTest 'unexpected-module' '--help' 1 }
        finally { Remove-Item -LiteralPath $extra }
    }
    Assert-NoLauncherEffect 'reparse-cache' {
        $junction = Join-Path $scratch 'reparse-cache'
        New-Item -ItemType Junction -Path $junction -Target $carrierCache | Out-Null
        $env:QIKVRT_TOOLCHAIN_CACHE = $junction
        try { Invoke-LauncherTest 'reparse-cache' '--help' 1 }
        finally {
            $env:QIKVRT_TOOLCHAIN_CACHE = $carrierCache
            [IO.Directory]::Delete($junction)
        }
    }
    Invoke-BootstrapTest 'reconstruction-consent-required' @('-Install', '-ReconstructUpstream',
        '-Profile', 'windows-start', '-CacheDir', (Join-Path $scratch 'nonconsented')) 1
    $controls['reconstruction-consent-required'] = @{ result = 'PASS'; exit_code = 1 }

    $rollbackCache = Join-Path $scratch 'rollback'
    $rollbackArchive = Join-Path $rollbackCache ($relative + '/archive/' + $spec.archive)
    New-Item -ItemType Directory -Path (Split-Path -Parent $rollbackArchive) -Force | Out-Null
    Copy-Item -LiteralPath $sourceArchive -Destination $rollbackArchive
    $env:QIKVRT_TEST_FAIL_WINDOWS_PYTHON_FINAL_VERIFY = '1'
    Invoke-BootstrapTest 'final-verification-rollback' @('-Install', '-AcceptThirdParty', '-Profile',
        'windows-start', '-CacheDir', $rollbackCache) 1
    Remove-Item Env:QIKVRT_TEST_FAIL_WINDOWS_PYTHON_FINAL_VERIFY
    $rollbackRoot = Join-Path $rollbackCache $relative
    if (Test-Path -LiteralPath (Join-Path $rollbackRoot 'runtime')) { throw 'Failed verification retained a promoted runtime' }
    if (@(Get-ChildItem -LiteralPath $rollbackRoot -Filter '.install-*').Count -ne 0) { throw 'Failed verification retained staging' }
    $controls['final-verification-rollback'] = @{ result = 'PASS'; exit_code = 1; rollback_verified = $true }
    Invoke-LauncherTest 'reobserved-offline-self-test' '--runtime-self-test' 0

    $pointer = Get-Content -LiteralPath (Join-Path $repo 'logs/qikvrt_last_run.json') -Raw | ConvertFrom-Json
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $pointer.logfile).Hash.ToLowerInvariant() -ne $pointer.sha256) {
        throw 'Fresh Python launcher log readback digest mismatch'
    }
    $logAcl = Get-Acl -LiteralPath $pointer.logfile
    $access = @($logAcl.Access)
    if (-not $logAcl.AreAccessRulesProtected -or $access.Count -ne 1 -or
        $access[0].IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -ne 'S-1-3-4' -or
        $access[0].AccessControlType -ne 'Allow' -or $access[0].IsInherited -or
        ($access[0].FileSystemRights -band [Security.AccessControl.FileSystemRights]::FullControl) -ne
            [Security.AccessControl.FileSystemRights]::FullControl) { throw 'Runtime log owner-only DACL did not read back' }
    $controls['native-log-owner-dacl'] = @{ result = 'PASS'; protected = $true; owner_rights_sid = 'S-1-3-4' }
    $os = Get-CimInstance Win32_OperatingSystem
    $receipt = [ordered]@{
        schema = 'qikvrt-windows-python-offline-start-receipt/1.0'
        observed_utc = [DateTime]::UtcNow.ToString('o')
        source_head = $head; source_tree = $tree
        run_id = $env:GITHUB_RUN_ID; run_attempt = $env:GITHUB_RUN_ATTEMPT; job = $env:GITHUB_JOB
        runner_os = $env:RUNNER_OS; runner_arch = $env:RUNNER_ARCH
        windows_caption = $os.Caption; windows_version = $os.Version; windows_build = $os.BuildNumber
        windows_11_client_claimed = $false
        powershell_version = $PSVersionTable.PSVersion.ToString()
        archive_sha256 = $spec.archive_sha256; archive_bytes = $spec.archive_bytes
        license_sha256 = $spec.license_sha256
        payload_manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo 'runtime/toolchains/python-3.12.10-embed-amd64.payload.json')).Hash.ToLowerInvariant()
        bootstrap_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $bootstrap).Hash.ToLowerInvariant()
        cmd_launcher_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $launcher).Hash.ToLowerInvariant()
        ps_launcher_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $repo 'qikvrt.ps1')).Hash.ToLowerInvariant()
        native_windows_x64 = $true; system_python_candidates_exposed = $false
        os_egress_denied = $true; upstream_connection_negative_control = 'PASS'
        upstream_download_during_offline_start = $false
        cold_offline_restore = 'PASS'; fresh_qikvrt_cmd_start = 'PASS'; warm_offline_start = 'PASS'
        runtime_self_test = $cacheReceipt.self_test; negative_controls = $controls
        launcher_log_readback_sha256 = $pointer.sha256
        effect_acceptance_retained = $true; dependency_closed_for_materialized_carrier = $true
        release_carrier_controls = $releaseControls
        release_asset_download_observed = $false; durable_public_readback_verified = $false
        ordinary_release = $false; main_activation_verified = $false
        predecessor_evidence_transfer = $false; effect_ack_done = $false
    }
    [IO.File]::WriteAllText((Join-Path $EvidenceDir 'OFFLINE_START_RECEIPT.json'),
        (($receipt | ConvertTo-Json -Depth 10) + "`n"), [Text.UTF8Encoding]::new($false))
    # The existing Action artifact path carries the materialized archive as well
    # as receipts. It is a candidate carrier, not a reviewed release asset.
    $payloadDir = Join-Path $EvidenceDir 'toolchains'
    $portableArchive = Join-Path $payloadDir ($relative + '/archive/' + $spec.archive)
    New-Item -ItemType Directory -Path (Split-Path -Parent $portableArchive) -Force | Out-Null
    Copy-Item -LiteralPath $sourceArchive -Destination $portableArchive
    Write-Output 'PASS: fresh native Windows x64 offline startup, strict cache controls and receipt readback'
} finally {
    foreach ($name in $rules) { Remove-NetFirewallRule -Name $name -ErrorAction SilentlyContinue }
    if ($firewallEnabled) {
        foreach ($profile in $profiles) { Set-NetFirewallProfile -Profile $profile.Name -Enabled $profile.Enabled }
    }
    $env:PATH = $oldPath
    $env:QIKVRT_TOOLCHAIN_CACHE = $oldCache
    $env:QIKVRT_TEST_FAIL_WINDOWS_PYTHON_FINAL_VERIFY = $oldFailureHook
    if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch -Recurse -Force }
}
