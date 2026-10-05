<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# S1 standalone node package, version 1.1.1

This package reuses the existing Node monitor and reference terminal. It now
also includes the recovered original productive TEMDD ledger/Unix daemon and
Firefox/noVNC deployment sources from snapshot
`c6a53e200c4835a4f871d8496feb81d953610831`. Exact source provenance and the new
portable S1 adapter are described in [RECOVERED_TERMINAL.md](RECOVERED_TERMINAL.md).
The recovered originals remain byte-identical. No second ledger or executor is
introduced. Select `temdd` (the example default), `firefox`, or the compatibility
`reference` profile explicitly. Missing profile retains the existing reference
behavior for prior private configurations.
Linux x86-64/ARM64 operators provision Node 24.x and Python 3.12.x. The builder
freezes their actual patch versions, architectures and executable SHA-256;
startup rejects any substitution. Python's renderer pin remains unchanged.

`tools/bootstrap-runtime.sh --check-only --profile self-host` performs no
GitHub CLI check or installation. Its default adapter is `none`. Selecting
`--adapter github` retains the locked GitHub CLI bootstrap. Every pre-existing
profile still requires that bootstrap and refuses `--adapter none`.
The PowerShell checker carries the same adapter selection; the actual service
launcher is Linux-only. The profile checker is readiness, not deployment proof.

## Freeze, transfer and start

In a clean reviewed checkout run:

```sh
python3 -B tools/qikvrt_self_host.py pack --root . \
  --expected-head <exact-commit> --expected-tree <exact-tree> \
  --output /absolute/new/package-directory
```

The output is a directory and deterministic uncompressed `.tar` of explicitly
allowlisted **committed** blobs with exact sizes, hashes and Git source binding.
It contains neither credentials nor `.git` nor private state. An independent
receiver must obtain the printed manifest pin through a trusted channel, verify
the archive bytes, and safely extract regular files. No online installer, gh,
Railway, npm install or mutable remote checkout is used to start the export.
The declared tools are operator-provisioned, not included binary payloads.

Copy `CONFIG.example.json` outside the package, replace all placeholders and
bind an authorized node identity, absolute volume path, ports and source pair.
Config and secret files must belong to the runtime UID and be mode 0600; the
volume must be mode 0700. Supply a private 32–256-character ASCII terminal token
from the host's existing secret provisioner. Never put a token in argv, source,
the package, caches or receipts. Default listener is loopback. Bind `0.0.0.0`
only behind the host's existing authorized HTTPS routing. No DNS, account,
firewall, billing or routing changes are made by this package.

```sh
python3 -B tools/qikvrt_self_host.py verify --root <package-directory> \
  --manifest-sha256 <independently-obtained-pin>
python3 -B tools/qikvrt_self_host.py run --root <package-directory> \
  --manifest-sha256 <same-pin> --config <absolute-private-config>
```

The launcher and monitor share an OS file lock for the entire service lifetime,
starts the selected original native or reference terminal on loopback and the
existing Node monitor, and shuts both down on termination. A failed bind never becomes a
ready receipt. Configure restart in the host's existing supervisor, using this
exact command and unchanged private config. No second supervision/execution
system or platform service is created. An isolated launcher crash leaves the
surviving monitor holding the lock; restart is refused until it also stops.
Kernel lock release after all holders exit permits crash restart.

The separately mounted volume layout is:

| Path relative to configured volume | Contract |
| --- | --- |
| `binding.json` | fsynced node/package/config/source binding; drift refuses startup |
| `node.lock` | owner-only OS lock; a second live writer is refused |
| `monitor/node.json` | existing exact journal and checkpoint; fsync/rename semantics unchanged |
| `temdd/` | existing owner-only SQLite ledger/Unix ingress location; no substitute ledger is created |
| `receipts/` | reserved private operator receipts; not a cache or public document route |

A different package/config against an existing volume requires separately
reviewed migration. Do not delete or relabel acknowledged data to defeat the
binding. A real persistent mount/device identity, capacity and power-loss
guarantees remain host admission evidence; an ordinary local directory is not
proof of host persistence. The runtime binds only its configured filesystem.

## Network, authentication and readback

Adapter `none` observes its local packaged source, never GitHub. GitHub ingress
and live-run routes are refused. The outbound provider wrapper rejects Railway
and every external provider before transport; only loopback is allowed.
With the explicitly selected GitHub adapter, HTTPS `api.github.com` is permitted
and its webhook requires the existing HMAC boundary. Startup requires an
owner-only `github_webhook_secret_file` containing a 32–256-byte secret.
The host must apply its
own OS egress policy; the application wrapper is not a process sandbox.

Public GET/HEAD routes reuse monitor activity/events/SSE and the read-only
terminal at `/AI/` or `/terminal/`. Terminal repository reads resolve only
allowlisted public exported files; the immutable package commit is explicitly
distinguished from a current remote `main`. No public terminal effect or owner
Unix operation is exposed. `/api/terminal` returns sanitized runtime metadata,
not private input, record bodies, tokens or secret-file paths. Reference HTTP endpoints require the configured bearer token. Native subject
and SSE reads retain the recovered loopback/Host/same-Origin boundary. Private
native events are never proxied through the public monitor. Owner durable
Prepare/Commit remain the existing Unix peer-UID/socket/SQLite client contract.

Run the **existing independent monitor client** in a separate process:

```sh
node tools/qikvrt_mesh_monitor_readback.mjs --self-host <package-directory> \
  <exact-origin-url> <manifest-pin> <config-sha256> <expected-node-id> none
```

It verifies runtime/config/source pins, terminal binding, exact client assets,
snapshot, original journal bytes/digest chain and a final fresh node readback.
It uses the exported original client bytes, with no Git or provider dependency.
The original Railway plan path remains compatible when its existing contract
is installed; self-host selects an explicit separate plan. No credentials are
needed in the readback process. A local URL proves only local HTTP readback.

## Executable S1 validation

### Own-host admission and existing launcher binding

`admit` extends this same tool. It makes no network call, starts no service,
creates no supervisor, modifies no state and grants no deployment authority.
Without a private host declaration and private configuration it returns
`HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE` (exit 2).

Copy `HOST_ADMISSION.example.json` outside the package, mode 0600. All nulls
mean missing evidence; they are deliberately not a fabricated host or URL.
Bind exact package Head/Tree/manifest, config digest and node ID. The host
operator supplies the SHA-256 of the exact `/etc/machine-id` bytes and the
selected persistent mount fields from `/proc/self/mountinfo`: `mount_point`,
`mount_root`, `device_major_minor`, `filesystem`, `mount_source`. The command
selects the longest mount containing the configured private `state_dir` and
compares these fields locally. Overlay, tmpfs and other ephemeral filesystems
are refused. A matching mount is not a power-loss or capacity guarantee.

The declaration also identifies the actually callable, authorized host
execution operation, existing supervisor/service, authorized public HTTPS
origin and digests of independently validated ownership/authorization,
persistence and HTTPS-routing evidence. Evidence digests alone do not validate
those records. Obtain the declaration pin through an independent trusted
channel; do not infer it from an untrusted self-report. Do not put secrets or
credential values in the declaration, arguments, launcher plan or repository.

```sh
python3 -B tools/qikvrt_self_host.py admit --root <absolute-package-directory> \
  --manifest-sha256 <independent-package-pin> --config <absolute-private-config> \
  --admission <absolute-private-host-declaration> \
  --admission-sha256 <independent-host-declaration-pin>
```

The result is `HOST_LAUNCHER_BOUND_PENDING_EXTERNAL_ACCEPTANCE`, with argv arrays
for the **existing** exported `verify`, `run` and independent monitor-readback
commands. No declaration-supplied command is executed. An independently
reviewed successor tool can prepare this plan for the unchanged exact #457
export `3bf52747bc94de847d390ffacabecae183aee588` / Tree
`96c7bb691675dcd15bb5045871201adb400074f0`; the plan runs that export's original
launcher. A newly packed successor binds its own fresh source pair instead.

After independently validating the named host/control-plane and evidence,
use the existing supervisor with the emitted verify/run argv. From a separate
external client execute the emitted readback against the exact HTTPS origin.
Record acknowledged native SQLite events through the existing owner Unix
ingress and the existing monitor journal, restart the actual deployed service
via the same supervisor, then repeat public readback and compare the exact
acknowledged event bytes and digest chain. Neither an empty ledger nor a
local restart substitutes for this witness. Record supervisor restart identity,
before/after process identities, mount binding and independent observations.

This plan leaves `host_admission_verified`, `public_readback_verified`,
`restart_verified`, `review_governance_satisfied` and `effect_ack_done` false.
Current host capability/HOLD evidence is in
`runtime/capabilities/S1_OWN_HOST_ADMISSION_20261005.json`; tests of synthetic
declarations are explicitly local controls and are not host acceptance.

### Durable supervisor binding and event-based restoration

The same reviewed tool now provides `supervisor` and `run-admitted`. No new
executor, ledger, provider adapter or supervision daemon is created. On a
validated own host with its already provisioned **systemd >=252**, set
`supervisor_id` in the private admission to `systemd:<authorized-name>.service`.
The private config/token/state must be owned by the intended service UID;
generate as that UID. Validate the guard's SHA-256 independently from the
reviewed source, even when it launches the unchanged original #457 export.

```sh
sh tools/bootstrap-runtime.sh --check-only --profile self-host-systemd --adapter none
python3 -B tools/qikvrt_self_host.py supervisor \
  --root <absolute-package-directory> --manifest-sha256 <independent-package-pin> \
  --config <absolute-private-config> --admission <absolute-private-host-declaration> \
  --admission-sha256 <independent-host-declaration-pin> \
  --admission-tool-sha256 <independently-reviewed-guard-pin> \
  --output <absolute-new-supervisor-output-directory>
```

The create-only directory contains `<authorized-name>.service`,
`<authorized-name>.path` and `BINDING.json` with exact unit/guard/package/config
pins. It is `SYSTEMD_BINDING_PREPARED_NOT_INSTALLED`. Validate both units with
`systemd-analyze verify`. On the independently authorized host, install those
exact unit bytes as root-owned mode 0644 files under `/etc/systemd/system/`,
compare their digests with `BINDING.json`, then use the **existing** supervisor:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now <authorized-name>.service <authorized-name>.path
sudo systemctl show <authorized-name>.service \
  --property=MainPID,InvocationID,NRestarts,ExecMainStatus,ActiveState,UnitFileState
```

The root-owned installed units and independently verified guard/runtime paths
are part of host admission. Do not install unreviewed generated bytes or infer
deployment permission from a declaration digest. Unit generation installs
nothing and performs no host or routing effect.

Every service start, including automatic recovery, rechecks the guard, exact
package/runtime/config/host/mount/admission pins. The original exported
`verify` runs in a separate process; its original `run` replaces the guard
with `exec`, preserving systemd's MainPID and cgroup. The existing kernel lock
and persistent volume binding remain authoritative. The guard requires an
active systemd PID1/version and compares MainPID/InvocationID with the actual
manager; an environment variable alone cannot establish this binding.
Identity drift returns
HOLD **78**, which suppresses unattended restart. State is never deleted,
recreated, relabeled or silently migrated by recovery.

`Restart=always` recovers an unexpected exit; an intentional `systemctl stop`
does not restart. `KillMode=control-group` removes surviving children before
another writer can start. Boot and the admitted mount's activation pull in the
enabled service; `RequiresMountsFor`/`BindsTo` prevent a missing mount from being
replaced by an ordinary directory. Five starts per 300 seconds bound a crash
storm. Restoring the **same pinned** config, admission, manifest, guard or
machine-ID bytes triggers the `.path` unit to retry admission. The retry is a
filesystem event, not an HTTP probe or a periodic loop. Restoring a package
directory atomically must include its manifest event. A changed head, revoked
authorization, changed identity/device, corruption or exhausted rate limit
requires a separately validated repair (`systemctl reset-failed` and a fresh
start after diagnosis); recovery cannot grant itself a new pin or credential.

The existing terminal workflow now requires a real native systemd test on its
disposable runner: kill only the launcher MainPID, observe a new invocation
and cgroup cleanup, preserve acknowledged native SQLite rows and monitor
journal bytes, force admission drift into HOLD 78, then restore the exact
admission bytes and observe automatic event-based recovery. Its receipt and
systemd version are retained as an exact-head artifact. This is a CI fixture,
not an owned public deployment. External HTTPS/readback, the actual deployed
restart witness and review governance stay mandatory and separate.

On the declared Linux runtime run `make test repository-monitor-test self-host-test`.
The existing full repository suite stays intact; the two explicit S1 targets add
the original monitor controls and standalone package controls. CI, repository
evidence, global completion, collective review and Batch-003 remaining subject
disposition require all three targets
after provisioning the S1 runtime. The existing terminal workflow additionally
requires all 31 HTTP/owner-Unix controls and freezes the actual source package.
A profile-specific Linux test is not imposed on unrelated portable callers.

## Precise remaining acceptance

The former productive source gap is resolved for the exact recovered historical
snapshot. The original Goldkelch commit declared by that snapshot could not be
retrieved directly, and equality with a later Railway production build remains
unverified. The selected native daemon runs its original SQLite/WAL and Unix
implementation through the new sealed-source adapter. Reference HTTP remains
process-local and does not supply durable native evidence.

The native suite exercises actual owner Prepare/Commit, fresh SQLite/SSE,
wrong subject, drift, duplicate commit and crash restart. The terminal workflow
also builds the declared Linux Firefox carrier and runs the actual candidate
export with only loopback networking, no Git/gh in its runtime PATH, real X11
window and VNC WebSocket readbacks, plus native/browser crash restart. These
checks establish only the execution recorded by the immutable workflow head.

No callable own-host deployment operation, verified host identity, durable mount
or public route is available in this task. The deployment work unit records
`HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE` and references the historical source recovery separately. Container and local
restart tests do not close the host admission condition.
S1 remains OPEN until host admission, exact deployment,
fresh public use/readback and deployed restart acceptance are established.
No public URL, S1 DONE or EFFECT_ACK_DONE is asserted.
