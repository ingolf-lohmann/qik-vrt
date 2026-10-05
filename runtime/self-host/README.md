<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# S1 standalone node package, version 1.4.0

The same S1 listener now serves the static React document at `/mesh`, `/node`
and `/client`. Node selection is `/node?repository=<declared-repository>`.
It consumes the existing hash-checked client replica and event stream, refreshes
on opening, visibility/online recovery and explicit readback, and displays the
original observation timestamp even after disconnection. React, React DOM and
Scheduler are frozen with complete MIT notices in `REACT_LOCK.json`; no CDN,
npm installation or framework server is needed. The source document is preserved
byte-for-byte at `/scheibenhard-original.html`. This adds no new monitor, ledger,
executor or public mutation route.

The complete public acceptance order is [MESH_ACTIVATION.json](MESH_ACTIVATION.json).
Candidate CI builds/verifies this document inside the existing S1 lane. Actual
hosting-platform CI is not instantiated: its own-host principal/executor is
unavailable. The contract requires a current complete node/terminal inventory,
one fresh native Transputer ping and authenticated receipt at every terminal,
with shared logical identity, measured receive window and clock uncertainty.
An HTTP health response, SSE connection or local React test cannot close it.
Own-host public deployment, all-node delivery and the first all-terminal round
trip remain OPEN. They are not replaced by the separately hosted observer Site.

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

The [Railway → Own-Host migration contract](MIGRATION.md) now provides
`migration-inventory`, `migration-verify-source`, `migration-export`,
`migration-verify-export`, `migration-import --dry-run`, `migration-import`,
`migration-verify-import` and `migration-rollback` in this same tool. It binds
all source/target paths, sizes and digests, preserves original DB/WAL/journals
and historical event subjects, and checks the explicit new `binding.json` in
separate verifier processes. Failed or rolled-back imports remain quarantined;
the launcher refuses them. These offline operations start no service and mutate
no Railway state or route. Actual snapshot capture, host admission and external
cutover readback remain independently evidence-bound.

The additive [one-shot Railway capture path](CAPTURE.md) now supplies
`migration-capture-supervisor`, `migration-capture-arm` and `migration-capture`.
The supervisor composer is unstarted and preserves all original recovered
source bytes. Its private, pinned hook fences startup before requesting bounded
writer shutdown, refuses unknown processes and drift, records complete private
metadata/acknowledgement evidence and fills `SOURCE.json`. Actual privileged
execution and private transfer remain a separate capability HOLD; no source
snapshot or production export is inferred from this adapter or its tests.

## Private durable-state snapshot and exact restoration

The existing launcher now provides `snapshot-state` and `restore-state`.
The immutable code export excludes state. These separate operations preserve
the **existing** native SQLite database, any WAL/SHM files, original monitor
journal and exact volume binding. They create neither a replacement ledger
nor synthetic production events. Tokens, credentials, Firefox profiles, caches
and private operator receipts are deliberately outside this snapshot.

On the source, stop the admitted service and its path unit through the existing
supervisor. Keep automatic activation and every original writer fenced while
transferring ownership; acquiring locks for a snapshot does not permanently
stop a source service. Do not allow an old and a restored writer to operate
the same node identity on different hosts.

```sh
sudo systemctl stop <authorized-name>.path <authorized-name>.service
sudo systemctl show <authorized-name>.service --property=ActiveState,MainPID
python3 -B tools/qikvrt_self_host.py snapshot-state \
  --root <absolute-verified-package-directory> \
  --manifest-sha256 <independent-package-pin> \
  --config <absolute-unchanged-private-config> \
  --output <absolute-new-private-snapshot-directory>
```

Run the snapshot as the original runtime UID. The command holds both existing
OS writer locks, checks the exact package/config/node/source binding and
streams a bounded 2 GiB inventory. It refuses a live writer before creating
output. The new directory is mode 0700 and its files are mode 0600; file and
directory sync plus independent digest readback precede a successful receipt.
`STATE_MANIFEST.json` binds every file's size and SHA-256. An incomplete output
is a failed operation and is never overwritten or automatically cleaned up.

Treat the complete snapshot as private durable application data. Transfer it
over the operator's existing authorized secure channel; keep the manifest pin
in an independent trusted channel. Never put this directory in Git, an Actions
artifact/cache, a public route or an email to another project participant.
Provision credentials separately through the intended host's secret facility.

On the independently authorized target, the configured state path must be
**absent** beneath a pre-existing owner-only parent. Keep the exact configured
absolute path, package pin, config bytes and node identity unchanged. The
restoration is create-only; an existing state path, wrong manifest, changed
binding, symlink, unlisted file, unsafe mode or changed file bytes returns HOLD.

```sh
python3 -B tools/qikvrt_self_host.py restore-state \
  --root <absolute-verified-package-directory> \
  --manifest-sha256 <same-independent-package-pin> \
  --config <absolute-unchanged-private-config> \
  --state-snapshot <absolute-private-snapshot-directory> \
  --state-manifest-sha256 <independently-obtained-state-pin>
```

This copies and rechecks the acknowledged bytes before runtime use. It neither
starts a process nor changes host admission. Bind a new host declaration to the
actual target, validate its persistent mount, install the pinned supervisor
units, then start through the existing `run-admitted` guard. Independently
compare the original ledger epoch, exact native event rows/digest chain and
monitor journal before and after a deployed restart, and repeat the external
HTTPS readback. Snapshot/restore success alone leaves all host, runtime,
Railway-cutover and EFFECT_ACK_DONE assertions false.

A new package head or changed config requires separately reviewed migration;
these operations cannot relabel old data for a new version. They also do not
export a legacy Railway volume. The observed live Railway terminal has a
different source/runtime layout whose exact data binding and export capability
remain to be verified; do not apply this S1 binding to it by editing metadata.
The [Railway SSH documentation](https://docs.railway.com/cli/ssh), freshly
read on 5 October 2026, describes registered-key SSH and SCP/SFTP access to
mounted-volume files. That is an operator transfer path, not a callable
authenticated export capability in this task. Do not register a new key, expose
a public data endpoint or copy a live SQLite file alone to bypass this gap.

### Railway retirement boundary

The fresh configuration inventory covers all five existing production services.
It distinguishes applied configuration from staged changes; no staged patch was
applied and no service, volume, route, variable value or account was changed.
The precise observation is in
`evidence/self_host/RAILWAY_EXIT_PREPARATION_20261005.json`.

| Existing service | Observed dependency | Required retirement evidence |
| --- | --- | --- |
| `universal-terminal` | Goldkelch source `2fdcf8d`; GitHub/tool installation at boot; Railway domain, deployment identity and live `/var/lib/qikvrt` volume | Exact legacy source/data export; source-writer fence; admitted target; independent original-event/epoch and public-use/restart readback |
| `mesh-monitor` | Applied Goldkelch `/docs/monitor` configuration; separate staged mirror source/volume changes | Actual current journal/source/route readback and safe export; independently accepted own-host monitor; no assumption that staged storage is live |
| `mesh-monitor-exact` | Applied Goldkelch `/deploy/mesh-monitor`, managed Python startup | Bound replacement of its actual role/data and independently checked consumers/routes |
| `mesh-monitor-live` | Applied Goldkelch `/deploy/mesh-monitor`, managed Python startup | Bound replacement of its actual role/data and independently checked consumers/routes |
| `mesh-monitor-bootstrap` | Applied Python 3.13 Alpine image and Railway domain | Verify remaining bootstrap consumers and replace their actual endpoint before retirement |

Before retiring each service, retain its recoverable original data and establish
the replacement's exact role, ownership and route with independent acceptance.
Keep the original writer fenced if rollback becomes necessary; reverse a
cutover only after diagnosing which side owns the acknowledged state.
Traffic/DNS switching, volume deletion, account cancellation and decommission
are separate operations after this evidence. No spend, DNS change, account
cancellation, staged deployment, legacy-state rebinding or Railway shutdown is
performed by this preparation.

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

The same mandatory native lane also exercises snapshot/restore with a real
owner-Unix Prepare/Commit, SIGKILL, exact SQLite/WAL and monitor-journal bytes,
and fresh original-daemon readback after restoration. Additional original
SQLite-backend controls cover abrupt WAL retention and each actual OS writer
lock. They supplement the owner-Unix controls. Sanitized exact-head test
receipts contain only synthetic-fixture digests/counts and explicit unfulfilled
deployment assertions; the private state directories themselves are never
uploaded.

On the declared Linux runtime run `make test repository-monitor-test self-host-test`.
The existing full repository suite stays intact; the two explicit S1 targets add
the original monitor controls and standalone package controls. CI, repository
evidence, global completion, collective review and Batch-003 remaining subject
disposition require all three targets
after provisioning the S1 runtime. The existing terminal workflow additionally
requires all 31 HTTP/owner-Unix controls and freezes the actual source package.
A profile-specific Linux test is not imposed on unrelated portable callers.


## Verbindliche Nachweisoberfläche je Repository-Knoten

Product Owner Ingolf Lohmann verlangt seit dem 5. Oktober 2026, 23:47 Uhr
Europe/Paris, die Oberfläche
<https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/>
für **jeden gegenwärtigen und künftigen QIK-VRT-Repository-Knoten** und für das
Mesh insgesamt. Produktname: **Universales Raumzeit-Terminal**.

Jeder Knoten stellt eine eigene, öffentlich über HTTPS erreichbare,
repositorygebundene Instanz bereit. Er zeigt seine Identität, Rolle, exakt
ausgelieferten HEAD/TREE und Paketbytes sowie getrennt davon den frisch
beobachteten Remote-Stand. Bekannte unerreichbare Knoten bleiben sichtbar.
Ein gemeinsamer Host ist zulässig, sofern Identität, Quelle, Speicher und
Readback jeder Instanz einzeln prüfbar sind.

Zum Mindestumfang gehören automatische Aktualisierung beim Öffnen und
Fortsetzen, der vorhandene Replica-/SSE-Pfad, explizite Aktualisierung,
zeitgebundene HTTP-Befunde, persistierte unveränderte Beobachtungsbytes mit
SHA-256, ein separater bytegenauer Readback, sichtbare Historie und
JSON-Downloads. Quellen, Bootstrap-/Runtime-Paket, Manifest, Downloadprüfung
und Lizenzhinweise bleiben nachvollziehbar. Ein Hintergrundlauf muss über das
Repository oder die zugelassene Hosting-CI ohne geöffneten Client arbeiten.

Die Referenz aktualisiert offene Clients und wiederverwendbare Serverbefunde
im 60-Sekunden-Fenster, markiert Befunde nach 120 Sekunden als veraltet und
hält 200 Beobachtungen vor. Jede Instanz erklärt und prüft ihre Frische und
Aufbewahrung; geschützte native Wirkungsbelege behalten ihre eigenen Regeln.
Bei Fehlern bleibt der ursprüngliche Beobachtungszeitpunkt erhalten.
Standard-Knoten übernehmen ausschließlich freigegebene öffentliche Metadaten
und lizenzierte Paketbytes, keine persönlichen Inhalte oder Geheimnisse.

Der maschinenlesbare Vertrag und die exakt gebundene Referenzquelle stehen in
[`MESH_ACTIVATION.json#/required_repository_surface`](MESH_ACTIVATION.json).
Bestehender Monitor, S1-Listener, Replica und Paketpfad werden weiterverwendet.
Die vollständige Funktionsdeckung und öffentliche Bereitstellung je Knoten
sind weiterhin **ungeprüft**. Der aktuelle Referenzstand ist kein neuer
öffentlicher HTTP-, Hosting-CI- oder nativer Transputer-Wirkungsnachweis.
Alle bisherigen Erst-Ping-, vollständigen Terminal-Empfangs- und
Restart-Abnahmestufen bleiben erforderlich.

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
