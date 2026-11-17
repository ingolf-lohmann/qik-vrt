<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Existing Railway carrier: one private capture, no cutover

This is the missing privileged boundary before [MIGRATION.md](MIGRATION.md).
It extends the same `qikvrt_self_host_migration.py` storage operations. The
additive `deploy/universal-terminal/railway-capture-hook.sh` uses the **existing
cloud supervisor's** child registrations, cleanup and original role binaries.
All 44 recovered historical source files remain byte-frozen. There is no second
runtime, transfer daemon, provider executor or public download endpoint.

## Current capability HOLD

Fresh inspection on 2026-10-05 identifies the existing service
`feb518e8-bfb2-450d-a36a-c992b052427c`, deployment
`d74053cf-7753-4d41-8d61-eab36b65c678` and volume `qikvrt-state` / `/var/lib/qikvrt`.
The Railway Agent's callable tools can list/read container files, but cannot
execute commands, write a deployed-container file, list account SSH keys, or
privately transfer a binary archive. The local executor has no Railway CLI,
Railway credential configuration, SSH identity or agent credential. Documented
`railway ssh` / SCP / SFTP functionality does not establish session capability.

The Agent read `/opt/qikvrt/.git/HEAD` as
`f2fa5a5e11dafe6d9579301c2a479e0eaa02d16c`. This is a mediated text observation,
not checked-out tree/cleanliness, stopped-writer or capture proof. The service's
configured source commit `2fdcf8d...` is not silently substituted for it.
Do not use either value to fill missing live capture facts from memory.

First blocker: `HOLD_PRIVILEGED_RAILWAY_CAPTURE_AND_PRIVATE_TRANSFER_CAPABILITY`.
The retry condition is an admitted privileged SSH/exec **and** private SFTP/SCP
carrier for this exact running deployment, with independently verified restart
fencing. No production capture, writer stop, export or cutover has occurred.

The [bounded public capability receipt](../../evidence/self_host/RAILWAY_CAPTURE_CAPABILITY_20261005.json)
binds the observations and exact command digests. Only the early start guard is
staged on this service; its live startCommand and running deployment remain
unchanged. The hook has not been admitted into the running supervisor.

## Admit the one-shot hook, preserving the legacy source

Do not redeploy new application code merely to gain volume access. A privileged
operator must preserve and verify the actual legacy checkout and role binaries,
and admit the hook to its existing supervisor under the deployment change
contract. The composer below creates an **unstarted**, owner-only script by
inserting the separately sealed hook into the exact actual Git-bound original
supervisor. It does not install itself, signal the old process, start a second
supervisor, alter Railway configuration or select a source replacement.

Before admitting that composition, ensure the existing Railway startCommand has
this fence **before** any source fetch, profile, tool, follow-script or application
write, and retain the authenticated applied-config/deployment receipt privately:

```sh
[ ! -e /var/lib/qikvrt/.RAILWAY_CAPTURE_HOLD.json ] || exit 78
```

A volume marker alone cannot fence a provider entrypoint that ignores it. Its
independent control-plane receipt pin is mandatory in the private request. This
code cannot authenticate that operator assertion; a digest is not permission or
platform proof. Never apply all environment staged changes to install this one
fence. The observed environment already has unrelated staged work.

Copy `CAPTURE_REQUEST.example.json` to a disjoint private directory, 0600. Bind
the actual provider IDs and mount, current deployment ID, independently observed
clean Git HEAD/TREE, complete actual layout, snapshot ID and a deadline at most
15 minutes ahead. After ingress is drained, obtain the final durable native
acknowledgement cut independently: original epoch, nonempty committed event
count and full SQLite logical digest using the existing validator on a sealed
read copy. Retain the acknowledged receipt(s) and native row/monitor evidence
privately. Unknown, ambiguous or missing stores remain HOLD; no profile bytes,
file names, request, provider credential or cut witness are committed here.

With independently obtained package and request pins on the admitted carrier:

```sh
python3 -B <sealed-package>/tools/qikvrt_self_host.py migration-capture-supervisor \
  --root <sealed-package> --manifest-sha256 <independent-package-pin> \
  --source-root /opt/qikvrt --live-volume /var/lib/qikvrt \
  --capture-request <private-REQUEST.json> --capture-request-sha256 <independent-request-pin> \
  --output <new-private-supervisor-script> --capture-output <new-private-capture-directory>
```

Inspect/pin/admit the unstarted script using the existing deployment's privileged
execution contract; do not launch it beside the current supervisor. Once it is
actually the sole supervisor and the fresh private cut still matches, one
operator `SIGUSR1` invokes its hook. A signal without all exact private inputs
leaves the current runtime running. After valid admission, `migration-capture-arm`
creates/fsyncs the durable fence exactly once; repeated arms cannot dispatch
again. The supervisor asks its original children to stop gracefully within
20 seconds. Unresponsive or unknown writers refuse capture. There is no SIGKILL,
automatic resume, secret output or provider route switch.

## Private offline result and independent verification

`migration-capture` requires root on Linux, the actual mounted volume, matching
provider/deployment metadata, clean current legacy Git HEAD/TREE, the exact
persisted fence, a fresh request and held original producer locks. Its real
`/proc` census allows only the capture and its supervisor/transport ancestors
plus exited zombies. All other processes refuse the operation, including
background follow writers, browsers, SQL, SMTP or an unknown actor. Locks and
census are rechecked around the copy. Privileged operator interference and
authenticated provider identity/fencing remain independent trust obligations.

Every file, sidecar and empty directory is copied, including unknown state,
browser profiles, mail and receipts. Unsupported sockets, links, devices,
set-ID bits, ACL/xattrs, size limits or inadequate private storage refuse the
complete capture; none are silently omitted. Source UIDs/GIDs/modes are recorded
in private `CAPTURE.json`; the offline copy becomes owned by the capturing UID
with 0700 directories / 0600 files. This explicit access transformation prevents
private legacy world/group permissions from leaking into the transport.
SQLite/WAL, native history/digests, monitor and JSONL validation reuse the original
migration authorities. Original files, namespace census and acknowledged cut
must still match after the copy. A failure quarantines a partial copy and leaves
the source fenced. It does not repair, remove or restart source data.

The new private directory contains `snapshot/`, exact `REQUEST.json`, original
metadata/consistency/process evidence `CAPTURE.json`, and the filled `SOURCE.json`.
Obtain their digests via a separate trusted channel and independently validate
the capture evidence, including the restart fence and acknowledged receipts.
The command explicitly returns
`OFFLINE_CAPTURE_SEALED_PENDING_INDEPENDENT_VALIDATION`, with
`capture_consistency_independently_validated=false`.

Then run the existing commands in **separate processes** with independent pins:

```sh
python3 -B <sealed-package>/tools/qikvrt_self_host.py migration-verify-source \
  --root <sealed-package> --manifest-sha256 <package-pin> \
  --snapshot <capture-directory>/snapshot --source-declaration <capture-directory>/SOURCE.json \
  --source-declaration-sha256 <independent-SOURCE.json-pin>
python3 -B <sealed-package>/tools/qikvrt_self_host.py migration-export \
  --root <sealed-package> --manifest-sha256 <package-pin> \
  --snapshot <capture-directory>/snapshot --source-declaration <capture-directory>/SOURCE.json \
  --source-declaration-sha256 <independent-SOURCE.json-pin> --output <new-private-export-directory>
python3 -B <sealed-package>/tools/qikvrt_self_host.py migration-verify-export \
  --root <sealed-package> --manifest-sha256 <package-pin> \
  --bundle <export-directory> --export-sha256 <independent-EXPORT.json-pin>
```

Keep capture/export/evidence private and separately durable, using the admitted
operator's encrypted private storage/transfer. SCP/SFTP addresses the running
container's filesystem, not an automatic volume snapshot. Never stream archive
bytes or private inventories through the Agent, chat, public logs, repository or
shared cache. Only aggregate pins and bounded public receipts may be persisted.
No Own-Host import, deployment, route/DNS change or cutover is authorized here.
Release of the capture fence requires a separate explicit, freshly verified
resume/reconciliation decision; this adapter has no remove/resume operation.
