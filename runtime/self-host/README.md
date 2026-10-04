<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# S1 standalone node package, version 1.0.0

This package configures the existing `docs/monitor/server.mjs`, existing public
repository terminal and existing `src/qikvrt_effect_ack_http_terminal.py`.
It introduces no monitor, job executor, scheduler, daemon or effect ledger.
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

The foreground launcher holds an OS file lock for the entire service lifetime,
starts the existing HTTP reference terminal on loopback and the existing Node
monitor, and shuts both down on termination. A failed bind never becomes a
ready receipt. Configure restart in the host's existing supervisor, using this
exact command and unchanged private config. No second supervision/execution
system or platform service is created. Kernel lock release permits crash restart.

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
not private input, record bodies, tokens or secret-file paths. The loopback
reference HTTP endpoints require the configured bearer token. Owner durable
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

## Precise remaining acceptance

The productive Universal Terminal TEMDD daemon and Firefox/noVNC deployment
sources are absent from the accessible Mirror tree and retained checkpoint.
The known Goldkelch source read is unavailable; no replacement daemon is built.
The package therefore includes the existing HTTP **reference** carrier and
owner Unix **client**, not a complete productive terminal appliance. Reference
HTTP events remain process-local; its positive bounded local input state is
never promoted into S1/global EFFECT_ACK_DONE. Monitor confirmed data remains
durable under its existing filesystem contract. The Unix fixture tests verify
the existing client/ledger protocol, not a productive daemon.

No callable own-host deployment operation, verified host identity, durable mount
or public route is available in this task. The deployment work unit records
`HOLD_OWN_HOST_IDENTITY_STORAGE_ROUTING_UNAVAILABLE` and the independent native
terminal-source gap. Package/restart tests do not close either condition.
S1 remains OPEN until complete source and host admission, exact deployment,
fresh public use/readback and deployed restart acceptance are established.
No public URL, S1 DONE or EFFECT_ACK_DONE is asserted.
