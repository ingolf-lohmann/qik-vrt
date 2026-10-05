<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Recovered historical TEMDD and Firefox/noVNC carrier

`architecture/universal-transputer-c90-v1` retains exact snapshot commit
`c6a53e200c4835a4f871d8496feb81d953610831`, tree
`f1640191ec25495c90e997b38e77490995808b1c`. Its commit declares Authority source
`b1971ca5003f5ac63fb8baf0bc663195f7ebcb78`. The snapshot commit/tree and restored
blob bytes were retrieved; the declared Authority commit is not independently
reachable through this connection. Neither equality with today's Railway build
nor completeness of later Authority changes is inferred.

`evidence/self_host/SOURCE_RECOVERY_20261005.json` binds every restored path by
size, SHA-256 and original Git blob. The native daemon, IDE, deployment recipes,
original tests and original Firefox extension source are historical original
bytes. The extension is preserved separately under `original-firefox/`; it is
not silently installed or substituted for the currently selected client.

The historical Dockerfile/entrypoints assume the full original `/opt/qikvrt`
checkout and its broader Cloud Transputer dependencies. They are preserved as
source evidence, not invoked against the narrower S1 export. The new portable
adapter in `tools/qikvrt_self_host.py` replaces only the Git/layout binding and
child startup. It reuses the unmodified original `Ledger`, HTTP handler and
owner-only Unix ingress. These adapter changes are **new implementation**, not
restored original source. No replacement ledger, scheduler or effect executor
is introduced.

## Native portable profile

The example config now selects `terminal_profile: temdd`, an explicit
`source_repository` and `subject_pr`. Startup and every native operation verify
the independently supplied manifest pin, exact exported source, executable
hashes, private config and volume binding. This path needs Node 24 and Python
3.12, but neither Git nor gh nor a provider network. Legacy config without an
explicit profile retains the process-local `reference` profile.

The existing durable CLI accepts `--manifest-sha256 <independent-pin>` with its
unchanged input, preparation/hash, repository/PR/head/tree and state-directory
arguments. This explicit path verifies the sealed export instead of a Git
checkout. Prepare still inserts no event; Commit uses the existing mode-0600
Unix ingress and owner UID; receipt verification uses a fresh read-only SQLite
connection. The recovered daemon keeps original native-ID conflict detection,
WAL/FULL commit, epoch, event bytes and SSE replay. HTTP writes are refused.

The public monitor `/api/terminal` reads and validates the native subject and
epoch, returning sanitized metadata only. Private event bodies and native SSE
remain on the loopback owner interface. Public routing and access to personal
browser state require the host's separately admitted authenticated HTTPS route.

## Firefox/noVNC profile

`runtime/self-host/Dockerfile` provisions a compatible dependency image from
digest-pinned official Python 3.12 and Node 24 bases and Debian packages. A
builder with these tools can freeze a browser variant using
`pack --browser-assets-root /usr/share/novnc`. Its manifest binds every admitted
noVNC source file and all six executable hashes. Third-party distribution
copyright metadata is retained. No binaries, credentials or live profiles enter
the source package. Package assembly is not a distribution-wide reproducible
APT-build claim: the actual build package versions and image are retained in CI.

Set `terminal_profile: firefox`, explicit separate `novnc_port`, `vnc_port`,
`display` (for example `:99`) and an owner-only `browser_password_file` containing
exactly eight printable ASCII bytes. The adapter starts Xvfb, x11vnc,
websockify and Firefox on the native IDE. VNC authentication is mandatory; every
VNC/noVNC listener remains loopback. Both x11vnc and LibVNCServer IPv6
listeners are disabled; the configured IPv4 port is the only VNC listener. No unsigned extension/signing exception is
enabled. Bounded startup checks require a real Firefox Navigator window and
byte-exact noVNC HTTP response. Linux pidfds supervise actual child exits without
runtime polling. Profile/state/logs are private and outside the export.

The existing terminal workflow builds the dependency image and runs the actual
candidate export in `docker run --init --network none`, with a private temporary
volume. It checks Firefox/X11, noVNC WebSocket/RFB authentication negotiation,
native Prepare/Commit/SQLite/SSE and crash/restart preservation. The container
must provide a real init reaper; operators use their existing host supervisor
with process-group termination and orphan reaping. Kernel PID and TCP-listener
readbacks verify crashed Xvfb removal and only four declared loopback ports.
Artifacts bind
the actual candidate head/tree, package, binary/source hashes and fresh runtime
readbacks. A missing dependency or failed runtime is an error, not a skipped
acceptance case.

## Remaining acceptance

Historical source recovery closes the claim that **no native source carrier is
reachable** for this bounded snapshot. Fresh CI runtime readback must still be
observed on the successor. The independent-host identity, persistent-device
attestation, authenticated public HTTPS routing and deployed restart remain
separate acceptance obligations. No deployment, public-runtime acceptance,
S1 DONE, Authority/Mirror equality or `EFFECT_ACK_DONE` follows from recovery or
CI. The configured local filesystem is not an attestation of power-loss safety.
