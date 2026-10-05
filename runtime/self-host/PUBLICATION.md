<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Exact publication continuation through the existing terminal host

Product Owner Ingolf Lohmann authorized closing this integration gap on
5 October 2026. Using QIK-VRT's own existing Terminal, Transputer and Mesh
functions for legitimate recovery is a permanent product acceptance criterion.
Actual publication, independent public byte readback and required node receipts
remain acceptance obligations. This document does not declare them fulfilled.

The launcher now offers `publication-check`, `publication-resume` and
`publication-supervisor`. It reuses `tools/qikvrt_zenodo_publish.py` unchanged,
its exact v2 controls, source validator, remote single-use authorization lock,
reconciliation phases and independent public metadata/file gate. No second
publisher, job/transfer daemon, HTTP shell endpoint or credential vault is added.

## Protected inputs

Keep the exact request, credential reference registry and provider-managed
credential files outside both the launcher package and the Authority checkout.
Directories for the request and registry must be runtime-UID-owned, mode 0700;
files must be regular, runtime-UID-owned, mode 0600, without symlinked ancestors.
Reuse the host's existing secret provisioner to supply credential files.
The example registry contains only opaque references, declared principal,
origin, scopes, source path and actual expiry. Never put secret values in this
registry, Git, cache, request, command line or public receipt.

`PUBLICATION_REQUEST.example.json` binds the actual complete Authority checkout,
execution HEAD/TREE, existing publisher/launcher/interpreter bytes and manifest
digest. Its independently reviewed SHA-256 is supplied separately. The real
origin must be Goldkelch/qik-vrt. The Mirror, an old deployed source and a
`READY` response cannot substitute for this binding. Every invocation rechecks
the original v2 manifest, machine proof, return receipt and authorization.
The request grants no authorization absent those publisher controls.

```sh
python3 -B tools/qikvrt_self_host.py publication-check \
  --publication-request /private/exact-publication.json \
  --publication-request-sha256 <independently-reviewed-request-pin>
python3 -B tools/qikvrt_self_host.py publication-resume \
  --publication-request /private/exact-publication.json \
  --publication-request-sha256 <same-pin>
```

Check performs no network mutation and reads no credential value. Publisher
and both transport/proof modules must match their committed execution blobs
and the reviewed launcher package. Private reads are bounded and verify the
opened file's owner, permissions and type; actual credential values in reference
metadata are rejected before journaling or invoking the publisher. Resume locks
both request and registry, reobserves admission, delivers credentials only to
the dedicated publisher process through its environment, and invokes that
publisher once. Child output is suppressed to prevent credential/error leakage.
The publisher's durable phase receipt remains the detailed recovery authority.
A failure or timeout remains HOLD; there is no automatic blind retry. A later
prerequisite event re-enters the existing publisher's reconciliation path.

The protected registry's adjacent `.interactions.json` journal is updated with
fsync, atomic replacement and readback after credential delivery and publisher
outcomes. It contains references and metadata, never credential values. Delivery
is explicitly not a successful browser login. Declared principal/scopes are
not independently established account identity/permissions. A successful
authenticated publication plus public readback is recorded as that bounded
effect, without inventing a biometric or SSO event.

## Automatic continuation without polling

```sh
python3 -B tools/qikvrt_self_host.py publication-supervisor \
  --publication-request /private/exact-publication.json \
  --publication-request-sha256 <same-pin> \
  --publication-unit qikvrt-publication.service \
  --output /private/new-supervisor-binding
```

This prepares, but does not install, a `Type=oneshot` service and `.path` unit
for the host's existing systemd manager. The service can run at boot or explicit
start; the path activates it when the request, reference registry or provisioned
credential files change. It has `Restart=no`, bounded trigger rate and no timer.
The interaction journal is deliberately not watched: recording an outcome
must not create an execution loop. Source/request drift refuses execution rather
than silently repinning the authorization. Install/enable these exact units
through the existing independently admitted host workflow. No Railway staged
patch, deployment, restart or key registration is applied by this command.

The local tests exercise adapter admission, negative controls and publisher
outcome handling with isolated Git repositories and mocked external effects.
They do not prove a deployed supervisor, real credentials, a Zenodo publication,
SSO, Authority accessibility or all-node equality. The current Railway session
still lacks production exec and scoped publisher credential delivery; activation
must be verified on that exact carrier before product acceptance is reported.

The original PR461 candidate bc2da76a, artifact 11343403081, is unchanged. This
launcher successor does not rebuild, replace or promote those frozen bytes.
