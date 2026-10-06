<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# Runtime toolchain provenance

The optional `self-host-systemd` profile uses an already provisioned Linux
systemd >=252. The host distribution owns its binary/package provenance; no
service startup installs or downloads tools. The behavioral contract is unit
syntax verification, exact guard pins and native supervisor/cgroup restart
controls in the existing terminal workflow. The 252 minimum includes path
trigger rate limits. Upstream unit/service/exec contracts are at
<https://github.com/systemd/systemd/tree/v255/man>. `systemctl --version` is
retained with the native test receipt. Actual host admission must separately
bind the authorized host supervisor and its independently validated evidence.
Unavailable tools yield CONTINUE; invalid unit/pin/identity/mount yields HOLD.
Recovery never deletes state, changes a package pin, installs dependencies,
grants review approval or creates a public acceptance receipt.

No executable or authentication token is stored in this directory. The files
here define independently checkable versions, upstream locations, checksums,
and license boundaries for an optional local cache.

The S1 provider admission extension uses the already locked Python 3.12 standard
library (HTTPS/TLS, JSON, Decimal, POSIX locks/fsync) and existing Node 24 monitor
readback plus the existing bounded subprocess helper. It installs no provider
SDK/CLI. Its source/API authorities, error/recovery boundaries and control tests
are in `runtime/self-host/PROVIDER_ADMISSION.md` and
`tests/test_self_host_provider.py`; both extend the existing cache registry.
Bearer credentials, mutable provider state and payment/terms authorizations are
private operator inputs and never cache payloads. A successful fake-provider
test does not establish a live REST/SSH/HTTPS admission.

## GitHub CLI 2.96.0

- Upstream project: <https://github.com/cli/cli>
- Release: <https://github.com/cli/cli/releases/tag/v2.96.0>
- Release assets: `https://github.com/cli/cli/releases/download/v2.96.0/`
- Upstream checksum file retrieved on 2026-07-22.
- SHA-256 of the unmodified upstream checksum file:
  `fc046371efa250e2875208341a786a35a01717d5eebec6903e199a9b8a3f3565`.
- License: MIT; copyright GitHub Inc. See `THIRD_PARTY_NOTICES.md`.

The Linux amd64 archive was independently verified against the upstream hash.
Its cleanly extracted `gh` executable had 40,722,594 bytes and SHA-256
`56b8bbbb27b066ecb33dbef9a256dc9d1314adaeff0908a752feba6c34053b40`.
A separate incomplete extraction was rejected because its size and digest did
not match and it failed its execution self-test. On every supported platform,
the bootstrap therefore verifies the cached archive against the committed
upstream SHA-256, freshly extracts it, compares the candidate executable bytes
with that extraction, and only then runs `gh --version`.

The execution check requires the exact semantic version `2.96.0` and a
well-formed upstream build date. It does not hard-code one build date across
platforms: upstream may rebuild platform assets while retaining the release
version. Byte identity remains controlled by the platform-specific committed
archive SHA-256 and, for every cached executable, fresh re-extraction and byte
comparison.

The locked Windows ZIP assets use the upstream root-relative `bin/gh.exe`
layout. The Windows bootstrap verifies that exact layout instead of assuming
the directory prefix used by other archive formats.

Authentication is deliberately outside this runtime definition. Neither
`GH_TOKEN`, `GITHUB_TOKEN`, nor the state produced by `gh auth login` may be
committed or cached by these scripts.

## xml2rfc 3.34.0

- Upstream project: <https://github.com/ietf-tools/xml2rfc>
- Package index: <https://pypi.org/project/xml2rfc/3.34.0/>
- Bound renderer interpreter: CPython 3.12.13, x64.
- Supported wheel lock targets: Linux x64, macOS x64, and Windows x64.
- Exact direct version: `xml2rfc==3.34.0`.
- License: BSD-3-Clause; copyright IETF Trust. See
  `THIRD_PARTY_NOTICES.md`.

`requirements-xml2rfc-3.34.0.txt` records all 19 exact packages, including
`pypdf==6.15.0`, and the SHA-256 values of the PyPI wheels selected by CPython
3.12.13 on the three x64 runner families. Source distributions are excluded.
The lock file itself has SHA-256
`cd8473b443cc337670f0eec920913f2cabe07d38d497eaff2d140319b393b565`,
also recorded in `TOOLCHAIN.lock.tsv`.

The hosted CI toolcache currently supplies the exact CPython 3.12.13 runtime
on Linux x64 but not on the selected macOS Intel and Windows x64 runners. Those
runners therefore execute the independently locked GitHub-CLI and bootstrap
failure contracts and report the renderer capability as unavailable. The
workflow probes the exact version on every run and automatically activates the
same XML install/render gate if it becomes available. A fallback Python 3.12
is used only for non-renderer contract checks and never satisfies the renderer
identity predicate.

Installation requires explicit third-party consent. Pip runs in isolated mode
with its configuration file set to the platform null device, an explicit PyPI
index for initial wheel retrieval, `--only-binary=:all:`, `--no-deps`, and
`--require-hashes`. A restored wheelhouse is copied through pip's offline hash
verification. The final venv is always newly derived, offline, from that
verified wheel set at its final absolute path with copied interpreter
launchers. Check-only mode never executes a pre-existing venv.

## Trust boundary

Checksums establish byte identity with named upstream assets; they do not prove
the absence of upstream defects. A cache hit is an optimization and never an
`EFFECT_ACK_DONE`, scientific result, review, authentication, or publication
authorization.

## Additional version contracts

The remaining profiles deliberately name contracts rather than inventing
archive hashes for tools supplied by an operating system, a language package
manager, or an independently managed formal toolchain:

| Profile | Required contract | Automatic installation |
|---|---|---|
| `core` | a compiler that accepts the strict ANSI-C90 probe | no |
| `ietf` | CPython 3.12.13 x64, `xml2rfc==3.34.0`, and pypdf 6.15.0 from hash-locked wheels | fresh locked environment, with consent |
| `formal` | Python 3.12.x, pytest 9.1.1, Node 24.x, Zod 4.4.3, Lean 4.19.0 and Lake | no |
| `audio` | Node 24.x, sherpa-onnx-node 1.13.4, FFmpeg and matching FFprobe | no |
| `publication` | XeLaTeX and Poppler (`pdfinfo`, `pdftotext`, and `pdftoppm`) with reported versions | Poppler only in the guarded Ubuntu 24.04 manuscript workflow; XeLaTeX remains operator-managed |
| `all` | every preceding contract | xml2rfc generally; Poppler only in the guarded Ubuntu 24.04 manuscript workflow |

Zod and sherpa-onnx-node versions are already fixed by their respective npm
lockfiles. Pytest is fixed by the formalization requirements file. `Lean
4.19.0` is the formal kernel version used by the evidence package; Node 24 and
Python 3.12 are the corresponding execution contracts.

FFmpeg, XeLaTeX, Poppler and C compilers are commonly distribution builds with
feature- and license-dependent packaging. The repository therefore records no
false universal binary hash or license simplification for them. Check-only
mode reports `CONTINUE` until the named commands and behavioral contracts are
present. The Ubuntu 24.04 manuscript workflow has one bounded exception: when
any declared Poppler command is absent, it installs the distribution
`poppler-utils` package without recommended packages, records the reported
package and command versions, and then executes the unchanged PDF verification
gate. Other installation remains an operator/platform responsibility.

## S1 standalone runtime (2026-10-04)

The additional `python-selfhost` component uses operator-provisioned CPython
3.12.x, separately from the unchanged exact 3.12.13 IETF renderer. Upstream:
https://www.python.org/ ; build/provider licenses and notices remain applicable.
Node 24.x uses the existing component (https://nodejs.org/). Package assembly
records actual version, architecture and executable SHA-256; every start must
match them. No unverified fallback or interpreter download is performed.
Read-only Git object export uses https://git-scm.com/ (GPL-2.0-only); it is a
build/native-owner-client dependency, absent from the standalone HTTP readback.
Provision failure holds; recovery restores the exact admitted executables or
requires a reviewed new package/volume migration. Self-host fixtures test source
binding, denied providers, authentication, crash restart and exact readback.
The cache registry covers both added tools and the explicit GitHub-only adapter.


## S1 recovered Firefox/noVNC carrier

The optional `self-host-firefox` profile preserves the existing Node 24 and
Python 3.12 requirement and needs no GitHub CLI. Linux provisioning is declared
in `runtime/self-host/Dockerfile`; startup performs no download or installation.
The official base indexes observed on 2026-10-05 are pinned by digest:

- `node:24-bookworm-slim`: `sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6`.
- `python:3.12-slim-bookworm`: `sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3`.

Debian apt resolution happens only while provisioning. An arbitrary later build
is not claimed to reproduce those package versions. CI retains the actual OCI
image ID and distribution versions; the frozen export pins actual Node/Python
and browser executable hashes, Firefox version and every noVNC asset byte.
Debian distribution-managed noVNC links are frozen as regular files within the
explicit source tree or `/usr/share/javascript` and `/usr/share/nodejs`.
The noVNC distribution copyright file travels with those assets. Firefox/noVNC
use MPL-2.0, x11vnc GPL-2.0-or-later and websockify LGPL-3.0; X11 tool notices and
other dependency licenses are carried by the actual Debian distribution image.
No binary, private profile, password or credential is committed into the source
package or tool cache. Existing tools retain their earlier versions and license
boundaries. Missing Firefox dependencies produce CONTINUE readiness, not PASS.

Original QIK-VRT deployment/source provenance is separately recorded in
`evidence/self_host/SOURCE_RECOVERY_20261005.json`. The historical originals are
not relabeled as new implementations. The S1 source/config binding and portable
browser startup are explicitly new adapters, with no public deployment claim.


The isolated Firefox acceptance runs Docker with `--init`; the platform-provided
Docker init (tini, MIT) is the namespace PID 1 and reaps killed child processes.
It is part of the Docker distribution, not an additional QIK-VRT executor or
bundled binary. CI records the actual Docker engine version and init executable
hash. A real crash/restart control observes removal of the old Xvfb PID before
acknowledged ledger/profile readback. x11vnc uses `-no6 -rfbportv6 0` so neither
its own IPv6 adapter nor LibVNCServer opens a default undeclared VNC port. Actual
kernel listener readback requires exactly the four declared IPv4 loopback ports.
Source authorities: https://docs.docker.com/reference/cli/docker/container/run/
and the LibVNCServer-0.9.14 `libvncserver/cargs.c` / `sockets.c` source.

## S1 offline Railway-state migration

The storage-only migration module extends the existing self-host tool. It uses
the already declared Python 3.12 stdlib (`sqlite3`, `hashlib`, `fcntl`, file I/O)
and Node 24 original MonitorStore. No provider SDK, database server, new transfer
daemon, installer or executable dependency is introduced; cache coverage stays
25/25. The exact source export pins the new module with the existing launcher
and verifier. The committed transport code is PolyForm-Noncommercial-1.0.0;
private state, credentials and transfer manifests never enter tool caches.
SQLite format authority: https://www.sqlite.org/fileformat2.html#walformat
and Backup API: https://www.sqlite.org/backup.html . Native event checks reuse
the recovered original Ledger validator; its restoration provenance is unchanged.
Missing/changed pins, files, snapshots, SQLite/journal consistency or writer locks
hold. Failed imports are quarantined; explicit rollback preserves target bytes
and never resets a route or source writer. The mandatory completion receipt
prevents implicit fresh-state startup after an interrupted planned migration.
Dry-run and corruption controls run through `make self-host-test`; the existing
native Unix lane verifies imported historical and new-subject event restart.

The one-shot Railway capture adapter reuses those same Python/Git/Node
authorities and the original cloud supervisor; it adds no executable dependency
or cache profile. Privileged Linux mount metadata, `fcntl` locks, `/proc` PID
namespace visibility and mixed UID/GID access are required behavioral inputs,
not inferred from provider environment variables. The existing isolated root
Docker lane tests the complete storage adapter, real process-census admission
and foreign-owner preservation. Private request/capture/export bytes remain
outside Git and caches. The currently unavailable authenticated privileged
exec/SSH plus private transfer carrier remains an explicit capability HOLD.

## Static React S1 interface

React and React DOM 19.2.6 and Scheduler 0.27.0 are reused from the already
installed, lock-bound Site source dependencies. Their unmodified production
CommonJS sources and identical full MIT licenses were independently read.
`runtime/self-host/REACT_LOCK.json` binds each source slice, package/version,
reproduction locator and the assembled browser bundle. All upstream notices and
the complete MIT permission text accompany the bundle. This MIT dependency does
not relicense QIK-VRT implementation code. No CDN, compiler, npm installation,
server renderer or new service is needed at S1 startup. The existing package
freezer verifies the bundle and every original source slice; the ordinary
manifest then binds the emitted assets. Corruption returns HOLD before export.
Node VM/API and real exported-process HTTP controls verify this bounded scope.
Browser rendering, public hosting, provider CI, native Mesh ping and all terminal
receipts remain separately required; source assets never establish those effects.
