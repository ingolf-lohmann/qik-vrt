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
origin must be the current `ingolf-lohmann/qik-vrt` Authority. Both committed
role policies must match the launcher, and the production publisher must name
the same Authority. Historical Goldkelch requests and consumed authorizations
remain immutable; they do not authorize a new Authority upload. The Mirror, an old deployed source and a
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

## Recovered source and acceptance scope

The adapter is recovered from the preserved PR463 source at commit
`ef1d2953a30c1bf27c4a9bc385316c9f50c0c114`, originally proposed while
Goldkelch was Authority. That PR remained unmerged. The generic publisher,
transport, proof validator and existing workflow route already reside in the
current Authority; this change restores their missing S1 host connection.
`PACKAGE.json` now includes the publisher, both dependencies, the original
versioned proof contracts and protected-reference examples. Package admission
rejects an incomplete publication closure. The existing Actions router remains
an alternative original invocation route, with its own exact-Main admission.

Keep the existing protected registry/provider store as the credential authority.
Reuse its opaque references through the existing provisioner; source code and Git
history do not contain or export provider-managed secrets. The GitHub credential
must actually authorize the new Authority; the Zenodo credential must actually
access the intended account. These permissions are established by the original
publisher's authenticated operations, not by declared reference metadata.
This port does not reset consumption locks, mint credentials or claim that
credential delivery has occurred.

Local acceptance tests exercise current Authority binding, private references,
negative controls, one invocation under a lock, suppressed child output and
publisher outcomes. A cold export test checks the shipped closure separately.
They do not prove installation on the original host, credential delivery,
a new Zenodo record, node adoption or EFFECT_ACK_DONE. The existing original
host binding and protected credential references must be observed there before
productive acceptance. Preserve every unresolved publication and host duty.
