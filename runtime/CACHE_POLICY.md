<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Runtime cache policy

## Windows x64 startup carrier

The existing `windows-start` profile in `tools/bootstrap-runtime.ps1` binds
`python-embed-windows` in `TOOLCHAIN.lock.tsv` and `CACHE_REGISTRY.json` to the
exact CPython 3.12.10 embeddable ZIP. Its payload manifest binds the archive,
all 35 extracted members, complete upstream license text, SPDX SBOM and recorded
Sigstore bundle. Recording the bundle does not claim signature verification.

The managed location is
`.qikvrt/toolchains/python-embed/3.12.10/windows-amd64/sha256/<archive-sha256>/`;
`QIKVRT_TOOLCHAIN_CACHE` may select the same layout on an external carrier.
`archive/` retains the exact ZIP and `runtime/` is derived locally. Both Windows
frontends reuse this profile. A materialized archive starts without a live
python.org request, ambient Python, pip or package-index access. Every start
rehashes the ZIP, checks its complete member set against repository bindings,
compares every extracted file, rejects reparse points and extra/missing files,
and executes the isolated exact-version x64 self-test before the QIK-VRT launcher.

Offline materialization from an existing archive:

```powershell
tools/bootstrap-runtime.ps1 -Profile windows-start -Install -AcceptThirdParty -ArchiveFile X:\verified\python-3.12.10-embed-amd64.zip
qikvrt.cmd --runtime-self-test
qikvrt.cmd --help
```

The first command requires a previously obtained, hash-bound ZIP. Download is
available only as explicit controlled reconstruction:

```powershell
runtime/download_python_runtime.ps1 -AcceptThirdParty -ReconstructUpstream
```

Normal startup never calls that adapter or enables its network flag. A missing
mandatory cache blocks startup; check-only reports `CONTINUE` without installing
or downloading. Invalid existing material blocks and is never silently replaced.
Installation stages and verifies files, atomically promotes only the new runtime,
rechecks its final path, and removes that new runtime if final verification fails.

The existing runtime logger uses native Windows file handles, protected
owner-rights DACLs, bounded CRT byte-range locks and write-through pointer
replacement on Windows. POSIX permission and locking checks remain active.
Native concurrent-writer, alias-rejection and DACL-readback controls exercise
this platform contract. A filesystem that cannot enforce it blocks logging.

The existing adaptive-runtime workflow restores an exact cache key, performs
explicit preparation outside the offline interval, then executes
`tests/test_runtime_bootstrap.ps1` on native Windows x64. The test denies outbound
traffic for every executable on the start path through read-back OS firewall
rules, removes ambient Python commands, restores from the already materialized
archive, starts the real `qikvrt.cmd`, checks its runtime and launcher log, and
executes tamper/missing/reparse/consent/rollback controls. Firewall state is restored
in `finally`. Its artifact carries the exact-subject receipt and materialized
archive; it is a candidate carrier with finite retention, not a reviewed release.
Only reviewed Main may save the protected shared cache. No broad restore prefix
or cross-OS restore is allowed.

Materialization, coverage, local Linux tests and syntax checks do not close this
dependency. Closure for a materialized carrier requires a freshly read native
`OFFLINE_START_RECEIPT.json` for the exact candidate HEAD/TREE. Main activation,
reviewed durable release delivery and overall `EFFECT_ACK_DONE` remain separate.

The starter's CPython 3.12.10 binding preserves the previously selected embeddable
artifact. The independent IETF renderer remains bound to CPython 3.12.13; this
change does not select an older interpreter for that profile.

## Purpose

The repository is the durable runtime authority. Runtime caches are reusable
accelerators of that repository-defined runtime: exact tools, verified archives,
wheelhouses, derived environments, receipts, and timing evidence are reused so
repeated runs become faster without changing semantics or bypassing checks.

A cold cache and a warm cache MUST execute the same required checks and MUST
produce semantically identical project outputs. Chat state, model memory, proof
conclusions, review decisions, authentication, authorization, and publication
state are never cache authority.

## Authority and location

Committed runtime authorities are the bootstrap source, toolchain locks,
upstream checksums, provenance, third-party notices, cache-key definitions,
validation tests, recovery procedures, `runtime/toolchains/CACHE_REGISTRY.json`,
and `runtime/toolchains/CACHE_COVERAGE.json`.

Downloaded archives, extracted executables, virtual environments, package
caches, timing data, and cache receipts are reusable material under
`.qikvrt/toolchains/`, GitHub Actions caches, GitHub-hosted tool caches, pinned
runner-image layers, or an explicitly selected external cache directory. Large
binary payloads SHOULD remain in content-addressed caches or reviewed release
assets rather than ordinary Git history; their hashes, provenance, recipes, and
receipts MUST remain reconstructable from the repository.

No credential may enter a runtime cache. This includes `GH_TOKEN`,
`GITHUB_TOKEN`, Git credential-helper state, `gh auth login` state, cookies,
SSH keys, signing keys, and package-registry credentials.

## Complete declared-tool coverage

Every unique component in `runtime/toolchains/TOOLCHAIN.lock.tsv` MUST have
exactly one entry in `runtime/toolchains/CACHE_REGISTRY.json`. The deterministic
coverage authority `runtime/toolchains/CACHE_COVERAGE.json` MUST report `PASS`
and 100 percent coverage. `python3 tools/qikvrt_tool_cache.py verify` is a
mandatory repository and runtime gate.

“All tools” means every tool required by a declared QIK-VRT runtime profile.
A runtime operation MUST NOT invoke an undeclared tool. When a new task needs a
new tool, the same change MUST add its version/platform contract, source or
provider, cryptographic or behavioral verification, cache location, cache key,
self-test, provenance/license metadata, failure/rollback rule, and progress
telemetry before the tool is used.

Cache strategies may use repository-managed archives or wheelhouses,
GitHub-hosted tool caches, ecosystem dependency caches, verified build caches,
or pinned runner-image layers. Payload bytes may remain outside Git history, but
the authority needed to reproduce and verify them MUST remain in the repository.

## Cumulative runtime rule

Each successful runtime operation SHOULD leave the repository-defined runtime
more capable, faster, more diagnosable, or more reproducible by improving an
existing lock, bootstrap, cache recipe, receipt, test, recovery rule, or status
emitter. `REUSE_BEFORE_CREATE` applies: extend the existing runtime and cache
path before adding parallel machinery.

A tool needed repeatedly MUST acquire, in order:

1. an exact version and platform declaration;
2. an upstream source or pinned provider and verification contract;
3. a deterministic bootstrap or restore path;
4. a cache key bound to all relevant inputs;
5. an execution self-test;
6. provenance and license metadata;
7. a failure/rollback procedure; and
8. integration with step-level progress telemetry.

## Keys and restoration

A shared CI cache key MUST contain all of:

1. operating system and architecture;
2. a format-version prefix;
3. exact interpreter and tool versions;
4. capability outcomes relevant to the selected runner;
5. a digest of `runtime/toolchains/**`; and
6. digests of every bootstrap used to consume the cache.

Restoration MUST use an exact key. Broad restore prefixes and cross-OS cache
archives are prohibited. Every managed executable is compared against
repo-hash-anchored source material or an equivalent verified receipt before
execution. Cache metadata is not trusted merely because a hosting service
returned it.

The shared CI cache may contain hash-locked archives and wheelhouses. Derived
environments may be cached only when their path binding, platform binding, and
validation contract are explicit. Every authorized install verifies locked
inputs, stages changes atomically, self-tests the final path, and restores the
previous valid state on failure.

Untrusted pull requests may read a default-branch cache where GitHub permits
that behavior, but they MUST NOT publish a cache that a protected branch can
later treat as authoritative. Cache-save steps run only for reviewed code on
`main` or an explicitly dispatched trusted workflow after all contract checks
pass.

## Step-level visibility

Every cache restore, miss, verification, install, derivation, self-test, save,
rollback, and eviction decision is a discrete GitHub/runtime step and MUST
produce a progress frame through the existing human-machine progress protocol.
Cache work may not become a hidden interval.

## Effect boundary

- A cache hit is never `EFFECT_ACK_DONE`.
- No test, renderer validation, security check, license check, reviewer gate, or
  release check may be skipped because a previous result is cached.
- Compiled dependencies and verified tool environments may be reused; mandatory
  project checks execute again against the current tree.
- A mismatch, incomplete extraction, unexpected version, symlink/reparse point,
  or failed execution self-test is `BLOCK`, not a cache miss.
- Absence of an optional runtime in check-only mode is `CONTINUE` and causes no
  network or source-tree mutation.

## Installation and retention

Installation is opt-in where third-party terms require acceptance. Downloads
use named HTTPS upstreams and locked hashes. Installation is staged, verified,
atomically promoted, verified again in its final location, and rolled back if
final verification fails.

GitHub-hosted caches are accelerators with service-defined retention and quota;
durable reproducibility comes from committed locks, provenance, recipes, and
tests. Durable large payloads use reviewed, content-addressed release assets or
equivalent storage. Bootstrap scripts do not perform broad recursive deletion.

## Bounded adaptation

Automatic adaptation may reuse exact-key caches and collect non-authoritative
timing/diagnostic evidence. Optimization of ordering, parallelism, or cache
composition occurs through reviewed repository changes. It may never alter
`EFFECT_ACK` predicates, lower review or test requirements, inject credentials,
accept unverified tools, or treat cache state as proof authority.
