# QIKVRT V45.12 Error Classes

## WINDOWS_PYTHON_APP_EXECUTION_ALIAS_9009_UNHANDLED

Severity: BLOCK

A Windows CMD wrapper calls `python` directly. On systems without a real Python
runtime, Windows may route this to the Microsoft Store App Execution Alias and
return exit code `9009`.

Rule:

```text
No required local verification wrapper may call `python` directly.
Use PowerShell-first verification or a runtime resolver.
```

## PYTHON_REQUIRED_FOR_LOCAL_VERIFY_WITHOUT_RUNTIME_RESOLVER

Severity: BLOCK

The repository requires Python for local verification but does not resolve or
bundle a runtime safely.

Rule:

```text
Local Windows verification must either be PowerShell-only or use a resolver that
checks .\python\python.exe, py -3, py, and real python.exe while rejecting alias
failures.
```

## GITHUB_AUTOMATION_GATE_FALSE_PASS_WITHOUT_REAL_REMOTE_EFFECT

Severity: BLOCK

An internal test, script, log line, or master gate reports that GitHub
merge/commit/push/release has passed while no real remote effect is evidenced.

Rule:

```text
No GitHub release PASS without live remote evidence JSON verified by
GITHUB_REMOTE_EFFECT_EVIDENCE_GATE.
```

## USABILITY_ACCEPTANCE_TEST_FAILED_DESPITE_INTERNAL_PASS

Severity: BLOCK

The Product Owner's usability acceptance test fails even though an internal gate
prints PASS.

Rule:

```text
Product Owner usability failure overrides internal green output.
```

## ACCEPTANCE_NOT_PERSISTED_BEFORE_EFFECT

Severity: BLOCK

A state-changing effect was attempted before Product Owner acceptance had been
persisted.

Rule:

```text
No local commit, merge, push, release, or repository-state mutation may occur
before an accepted persisted acceptance record exists.
```

## REMOTE_EFFECT_EVIDENCE_NOT_PERSISTED

Severity: BLOCK

A remote operation may have been attempted, but the evidence record is missing,
incomplete, synthetic, or not independently verifiable.

Rule:

```text
Remote release claims require repository URL, branch, commit SHA, remote SHA,
push verification, release ID, release URL, tag, asset list, and downloaded asset
hash verification.
```


## WINDOWS_CMD_DP0_TRAILING_BACKSLASH_QUOTE_ARGUMENT_MERGE

Severity: BLOCK

A Windows CMD wrapper passes `%~dp0` directly as a quoted PowerShell argument.
Because `%~dp0` ends in a backslash, some command-line parsing paths can merge
the following PowerShell parameter into the same path argument. The result is a
malformed path such as a repository path polluted with `-OutDir ...`.

Rule:

```text
Do not pass quoted `%~dp0` directly. First assign it to QIKVRT_ROOT, remove the
trailing backslash, and pass the normalized root variable to PowerShell.
```

## POWERSHELL_RESOLVE_PATH_USED_ON_MISSING_OUTPUT_DIRECTORY

Severity: BLOCK

A PowerShell build script applies `Resolve-Path` to an output directory before
creating it. This makes a valid build fail merely because `dist` does not exist
yet.

Rule:

```text
Resolve existing Root literally. Normalize missing OutDir with
[System.IO.Path]::GetFullPath, create it, then verify it exists.
```


## V45.12 additional repair class

### REAL_GITHUB_WRAPPER_REQUIRES_EXTERNAL_ENV_WITHOUT_INTERACTIVE_ACCEPTANCE_PATH

Severity: BLOCK

A user-facing real GitHub release wrapper must not require the user to know and set an external environment variable before the wrapper can perform its own guarded acceptance flow. The wrapper must present the real-effect boundary, require exact Product Owner confirmation, persist acceptance, set the real-effects variable only after that persistence, and then run the GitHub automation.

Correction: the external environment variable remains a lower-level hard guard inside the automation script, but the official wrapper is responsible for setting it after successful acceptance persistence.


## V45.12 additional reflexive error classes

### ZIP_EXTRACTION_NOT_TREATED_AS_GIT_BOOTSTRAP_STATE

A locally delivered repository ZIP is executed as if it already contained a `.git` runtime state. ZIP delivery does not preserve a usable Git working tree. The real GitHub effect path must either bootstrap `.git` locally or BLOCK cleanly.

Severity: BLOCK

Repair: run `qikvrt_git_bootstrap_windows.ps1` before remote effects when `.git` is absent.

### GIT_ORIGIN_MISSING_CAUSES_NULL_METHOD_CRASH

A missing Git remote origin is treated as an object with methods, producing a PowerShell null-method exception instead of a controlled QIKVRT BLOCK state.

Severity: BLOCK

Repair: capture `git remote get-url origin` with an exit-code-safe subprocess and handle missing origin explicitly.

### REAL_GITHUB_WRAPPER_MUST_COLLECT_ORIGIN_OR_BLOCK_CLEANLY

A real GitHub release wrapper cannot assume origin is configured after ZIP extraction. It must collect a GitHub origin URL/OWNER/REPO or block with a human-readable remediation.

Severity: BLOCK


## POWERSHELL_COMMON_FUNCTION_NOT_LOADED_BEFORE_USE_V45_12

Severity: BLOCK

A PowerShell entrypoint uses a shared helper function such as `Normalize-QikvrtPathArg` before the shared helper library defines or exports it. This is a usability-acceptance failure because the local verifier can crash before it reaches the actual repository checks.

Correction: every PowerShell entrypoint must dot-source `tools/qikvrt_common_windows.ps1`, and `qikvrt_common_windows.ps1` must define every shared function used by build, verify, Git bootstrap, GitHub release and evidence-gate scripts. Missing helper functions are BLOCK, not CONTINUE and not PASS.


## WINDOWS_COMPRESS_ARCHIVE_OUTPUT_PARENT_OR_LONG_PATH_FAILURE_V45_12

Severity: BLOCK

A Windows ZIP build must not fail because the build wrapper passes an overlong nested output path or because `Compress-Archive` opens a destination ZIP stream before the parent directory exists. Repository package names and generated ZIP filenames must remain short enough for default Windows PowerShell environments, and `dist` must be created before ZIP creation.

Correction: V45.12 uses `QIKVRT_V45_12` as short root and `dist\QIKVRT_V45_12.zip` as short output artifact; the build script creates `OutDir` and ZIP parent before compression and excludes `dist` from staged package content.


## QIKVRT-RQL-V45-009 POWERSHELL_5_1_PROCESSSTARTINFO_ARGUMENTLIST_NOT_AVAILABLE

PowerShell scripts must not use `ProcessStartInfo.ArgumentList` in official Windows entrypoints
because Windows PowerShell 5.1 / .NET Framework installations may expose it as unavailable or NULL.
Captured process execution must go through a PowerShell 5.1 compatible `.Arguments` string builder.

Required consequence:

```text
ArgumentList usage in tools/*.ps1 => BLOCK
```


## QIKVRT-RQL-04511 LOCAL_ROOT_COMMIT_DIVERGES_FROM_EXISTING_ORIGIN_MAIN

A ZIP-extracted repository initialized a new local root commit and then attempted `git pull --ff-only` against an existing `origin/main`. This is a false Git strategy for publication kits. If a remote target branch exists, it must be used as canonical base before the QIKVRT overlay commit is created.

Rule: `origin/<target>` exists => fetch remote base => restore QIKVRT overlay => commit overlay => verify `origin/<target>` is ancestor of `HEAD` => push/release.


## QIKVRT-RQL-V45-012 TAG_FORCE_UPDATE_AND_RELEASE_ASSET_CLOBBER_NOT_ALLOWED

A GitHub release automation must not report a frozen evidence state when it force-updates an existing tag or overwrites an existing release asset. V45.12 requires a new immutable tag for a new effect state or exact hash verification of already-existing release assets.
