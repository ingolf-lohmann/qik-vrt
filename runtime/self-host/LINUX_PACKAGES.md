<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Native Debian/Ubuntu distribution of the original S1 server

Owner: Ingolf Lohmann. Implementation contribution: OpenAI Codex.
Source issue: #672. Target: the existing IONOS VPS and `raumzeitterminal.de`.

This is an additive distribution adapter for `PACKAGE.json` and
`tools/qikvrt_self_host.py`. The repository had an immutable S1 export, OCI
carrier and exact-host systemd supervisor, but no native package-manager split.
The adapter preserves that original runtime and introduces no executor,
watchdog, ledger, provider, network listener or scheduler.

The prior two-package candidate `175d3f52` is retained as a Git predecessor.
Its `tools/qikvrt_debian.py` path and original `deb-pack` / `deb-verify` CLI
entrypoints continue here, with the complete lifecycle and five-module split.
`DEBIAN_PACKAGES.json` explicitly versions that layout as v2. The older raw
native intake request, answer, status and attempt for Issue #672 are preserved
unchanged; their original BLOCK is not rewritten as a later successful run.

| Debian package | Installed component | Dependency |
| --- | --- | --- |
| `qikvrt-eap` | Original EAP Python state/wire/service modules and C90 source/header | Python 3.12 |
| `qikvrt-terminal` | Original Universal Terminal, Transputer and recovered carriers | Exact EAP package version |
| `qikvrt-web` | Sealed React monitor, terminal, browser sources and licensed assets | Exact Terminal package version; Node 24 |
| `qikvrt-runtime` | Original S1 launcher, REST/bootstrap, source manifest and policies | All three exact component versions |
| `qikvrt-server` | Package configuration and `qikvrt-server configure` command | Exact runtime version; systemd >=252; CA certificates |

All application payload is portable source (`Architecture: all`); the original
Python 3.12 / Node 24 runtime contract is unchanged. The actual host interpreter,
Node executable hashes and CPU platform are bound during installation. A host
with different versions fails configuration; the package never adds a foreign
APT repository, downgrades runtimes, downloads a binary or relaxes the contract.
The IONOS host's exact OS/runtime availability must be independently read back.
Debian-family package support does not assert RPM, Alpine or every Linux support.
The first scope is the existing native `temdd` terminal. Firefox/noVNC execution
and extension signing retain their separately authorized acceptance path.

## Build and independent readback

From a clean committed candidate, use the existing original exporter first:

```sh
mkdir -p .qikvrt
python3 -B tools/qikvrt_self_host.py pack --root "$PWD" \
  --expected-head "$(git rev-parse HEAD)" --expected-tree "$(git rev-parse HEAD^{tree})" \
  --output "$PWD/.qikvrt/linux-s1" > .qikvrt/linux-s1-receipt.json
python3 -B tools/qikvrt_debian.py build \
  --root "$PWD/.qikvrt/linux-s1" \
  --manifest-sha256 "$(python3 -c 'import json; print(json.load(open(".qikvrt/linux-s1-receipt.json"))["manifest_sha256"])')" \
  --output "$PWD/.qikvrt/linux-debs"
```

The output directory must be absent and separate from the source. Every
original file has exactly one owner. The original S1 manifest, complete
inventory, file modes, hashes, React assets and Mesh contract must validate
before a package is written. Version is `S1VERSION-REVISION+gSOURCEHEAD`;
all inter-package dependencies pin that full version. A revision is a positive
integer. The full source HEAD/TREE and source-seal pin remain in
`DEBIAN_BUNDLE.json`. No credential, token, configuration or live database is
selected outside the original allowlisted source export.

The existing CI supplies a monotonically increasing packaging revision from
`GITHUB_RUN_NUMBER * 1000 + GITHUB_RUN_ATTEMPT`, so an ordinary newer build
sorts after its predecessor in APT even when its Git hash sorts earlier.
Other trusted release callers must likewise advance `--revision`; a source
hash alone is not a chronological package-version sequence.

Debian 2.0 archives have deterministic ar/tar/gzip metadata. Repeated builds of
the same sealed input and packaging revision are byte-identical. The existing
CI's full test job builds these packages only after its final tested subject
is bound, and retains them as the `qikvrt-linux-debian` artifact. Source HEAD,
TREE and package digests are carried inside the artifact. These are CI assets,
not a published authenticated APT repository. SHA256SUMS detects byte changes;
authentic distribution still requires the existing trusted release/delivery
channel and independent expected digest. No unsigned APT trust configuration
is generated.

The existing original entrypoints remain available: `qikvrt_self_host.py
deb-pack --root <sealed-source> --manifest-sha256 <source-pin> --output <new-dir>`
and `qikvrt_self_host.py deb-verify --root <bundle> --debian-bundle-sha256
<DEBIAN_BUNDLE.json-pin>`. Verification uses the retained independent archive
reader and checks package controls, exact source partition, all source bytes,
file modes, source-manifest pin and the checksum index without executing
maintainer scripts.

After that channel has verified the downloaded bytes, an admitted Debian/Ubuntu
host can install the complete set in one package-manager transaction:

```sh
sha256sum --check SHA256SUMS.txt
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y ./*.deb
```

APT resolves external dependencies from its existing trusted sources. The
ordinary dependency solver is mandatory. The isolated `dpkg --root` fixture
models only external distribution-package metadata; it executes the real
runtime checks and rejects mixed QIK-VRT component versions without ignoring
dependencies. VPS installation uses its actual package database.

## Installation, activation and updates

The server package's `postinst` verifies the assembled original seal and
inventory again, checks compatible real runtimes and copies the source into a
new content-addressed candidate under `/var/lib/qikvrt/distribution/<seal>`.
It changes only the runtime binding in a newly derived S1 manifest, carrying
the immutable original source-seal digest. The original seal and source files
are preserved. The unchanged original S1 verifier validates the candidate
before and after atomic publication. Failed validation produces HOLD 78 and
no accepted candidate. Repeated identical configuration verifies and reuses
the same candidate; corruption is rejected rather than silently resealed.

`qikvrt-server configure` repeats that bounded operation and prints the full
candidate path, derived manifest SHA-256, guard SHA-256 and source HEAD/TREE.
It does not change an active-version pointer, private config, credentials,
writer identity, state directory, mount, firewall, DNS, TLS or systemd units.
Package installation reports `INSTALLED_CANDIDATE_NOT_HOST_ADMITTED`.

Activation is the original `supervisor` -> exact generated `.service`/`.path`
units -> `run-admitted` path documented in the adjacent README. Its existing
protected CI/host consumer must bind the candidate's **derived** seal and guard
to the independently validated private configuration and host admission.
It must generate and install the original exact units as the admitted service
UID, then independently read back the running service and original data.
An old admission cannot authorize a new package merely because APT installed
it. The exact-hash, machine-ID, mount, writer fence and state-ownership guards
remain unchanged; their absence holds activation. Private inputs stay in their
existing protected store, outside packages and public artifacts.

On upgrade, the new package configures a new candidate, retaining the existing
admitted runtime and durable data. Switching the original supervisor requires
the same new candidate-bound admission. Failed upgrade configuration cannot
remove the previously sealed runtime. Removal/purge deletes package-owned
distribution source and CLI files only; it retains sealed candidates and all
private state, and does not terminate an independently installed original S1
service. Service retirement and candidate cleanup therefore remain explicit
operations through the original host lifecycle, with state readback first.
No destructive package-maintenance script is supplied.

## Acceptance and boundaries

`make linux-packages-test` is part of the existing S1 `self-host-test` target,
which the current CI runs together with `make test`. Its native dependency is
scoped to that Linux installation lane; generic portable tests do not acquire
a dpkg dependency. The native package target requires
real `dpkg-deb` and `dpkg`; an unavailable checker fails, never skips. Cases
cover byte-identical builds; complete disjoint module ownership; exact native
metadata/dependencies; wrong seal, changed/extra/symlink source; unsafe output;
mixed package versions rejected by the native dependency solver;
incompatible runtime and unavailable checker; unchanged seal reuse and corrupt
candidate refusal; actual isolated-root installation, revision upgrade, removal
and purge with original configuration/ledger bytes retained. The installed
candidate starts the original native TEMDD process and survives a real process
restart through the existing HTTP/SQLite fixture with optional private Unix
ingress disabled. The separate native S1 suite retains Unix-socket acceptance;
the package test does not claim that socket path. The installed original Owner
REST path prepares/commits an input, independently reads its original SQLite
record, reads the same receipt after restart and checks every stopped native
state byte across upgrade/removal/purge. This is local input acceptance, not
productive EFFECT_ACK_DONE. No test daemon replaces the original runtime.

Those local checks are not native protected CI, exact IONOS host admission,
public TLS/domain acceptance, deployed restart evidence or productive
`EFFECT_ACK_DONE`. Each remains independently bound to its actual target.

Rights are unchanged. Original implementation and C90 sources retain
PolyForm-Noncommercial-1.0.0 where declared; documentation retains its stated
license; React and other third-party assets retain their own license notices.
No architecture-publication argument relicenses the implementation.
