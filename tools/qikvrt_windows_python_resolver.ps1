param(
  [string]$OutFile = "",
  [string]$Script = ""
)
$ErrorActionPreference = "SilentlyContinue"
. (Join-Path $PSScriptRoot "qikvrt_common_windows.ps1")

$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$candidates = @()
$candidates += @{Kind="bundled"; Command=(Join-Path $root "python\python.exe"); Args=@("--version")}
$candidates += @{Kind="py -3"; Command="py.exe"; Args=@("-3", "--version")}
$candidates += @{Kind="py"; Command="py.exe"; Args=@("--version")}
$candidates += @{Kind="python"; Command="python.exe"; Args=@("--version")}
$candidates += @{Kind="python3"; Command="python3.exe"; Args=@("--version")}

foreach ($c in $candidates) {
  $cmd = Get-Command $c.Command -ErrorAction SilentlyContinue
  if ($null -eq $cmd -and $c.Kind -ne "bundled") { continue }
  if ($c.Kind -eq "bundled" -and !(Test-Path -LiteralPath $c.Command)) { continue }
  try {
    $probe = Invoke-QikvrtCapture $c.Command $c.Args
    $out = $probe.Stdout + $probe.Stderr
    if ($probe.ExitCode -eq 0 -and $out -match 'Python\s+3\.') {
      $resolved = if ($c.Kind -like "py*") { "py" } else { $cmd.Source }
      if ($c.Kind -eq "bundled") { $resolved = $c.Command }
      if ($OutFile) { $resolved | Set-Content -LiteralPath $OutFile -Encoding ASCII }
      Write-Host "PASS Python runtime resolved via $($c.Kind): $resolved"
      if (![string]::IsNullOrWhiteSpace($Script)) {
        if (!(Test-Path -LiteralPath $Script)) { Write-Host "BLOCK optional Python script missing: $Script"; exit 1 }
        if ($resolved -eq "py") { & py -3 $Script } else { & $resolved $Script }
        exit $LASTEXITCODE
      }
      exit 0
    }
  } catch { }
}
Write-Host "CONTINUE_RUNTIME_MISSING no usable Python 3 runtime found; local PowerShell verifier remains authoritative"
exit 20
