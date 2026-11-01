<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# Workspace React client

The Owner's `QIKVRT_START_HIER.html` is preserved byte-for-byte as
`workspace-original.html`. `/workspace` and `/workspace/` render its connected
React successor on the existing owner-controlled S1 listener. `/client` links
to it. Package, configure and serve through the existing
`tools/qikvrt_self_host.py` procedure in `runtime/self-host/README.md`;
use its admitted `temdd` profile and EAP HTTP configuration from `EAP_HTTP.md`.
There is no new host, framework, dependency, scheduler, executor or credential store.

The client reuses the locked React 19.2.6 bundle, `client-replica.js` and the
existing `NativeTerminal` component from `devops-react.js`. It reads only
same-origin `/api/runtime`, `/api/node`, `/api/activity`, `/api/eap/state` and
the original `/api/stream`. Source repository, roles, exact head/tree, node,
version, manifest/config digests, epoch, snapshot digest and consecutive original
events must agree. A failed, expired or wrong-subject readback disables native
preparation/commit. The last observation remains visible with its own time.
SSE heartbeats never refresh the native readback time; there is no source polling
or client timer. Going online, returning to the page or explicit refresh reads
the original endpoints again.

Native input follows the existing EAP prepare, independent record/context
verification, explicit commit and independent receipt readback. The same guarded
component serves `/devops` and `/workspace`; its scope is durable text input,
never command execution, membership or license acceptance. Uncertain commit
outcomes retain the exact request and preparation for readback rather than resend.
Owner credentials remain in component memory. No login or other identity provider
is added. These are OwnerREST permissions, not proof of an SSO membership.

`/workspace/access.json` declares the unresolved workspace/member/acceptance/access
bindings. There is no admitted workspace membership or license-acceptance API in
the inspected S1 contract. Consequently this client neither grants access nor
creates a local acceptance checkbox/ledger. Adding that service requires an
actual admitted contract binding member, workspace, timestamp, license versions,
artifact manifest and independent readback. Public original sources remain public.
Workspace admission is independent of the already existing native Owner admission.

All displayed license links resolve to original files inside the sealed package;
the attachment's historical license/source links remain preserved in its original.
Documents, current code, historical Apache grants and third-party licenses retain
their individual boundaries. The package manifest returned by `/api/runtime`
binds the actual carried source bytes; it is immutable packaged source, not a
fresh observation of remote Main.

Validation: `node --test docs/monitor/workspace.test.mjs`, the existing
`tests.test_self_host_eap` cold-export acceptance (including workspace routes),
`tests/test_workspace_live_client.mjs` against that original exported process,
`tests/test_devops_client.mjs`, package verification and repository checks.
The JavaScript adapter test runs the actual served client bytes against real
HTTP endpoints; it does not assert desktop-browser rendering. The exact locked
browser installer returned truncated CDN archives in this session; no visual
browser acceptance is claimed. These are isolated software tests, not productive host evidence.
Exact `https://raumzeitterminal.de/` delivery and global `EFFECT_ACK_DONE`
require their own current readbacks.

Requirements and supplied text: Ingolf Lohmann. Implementation: OpenAI Codex.
