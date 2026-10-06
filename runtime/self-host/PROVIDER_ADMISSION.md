<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. -->

# Provider-neutral S1 admission

The existing `tools/qikvrt_self_host.py` entrypoint owns every operation below.
`qikvrt_self_host_provider.py` is its implementation extension, in the same
pattern as the existing migration extension. Reuse investigation found only the
offline host/mount/routing `admit` gate; it cannot inventory a provider account,
bind a provider tariff or reconcile a resource-create outcome. Its existing
launcher, host admission, supervisor, native ledger and independent monitor
verifier remain the execution/acceptance paths. No new workflow, launcher,
supervisor, credential store, domain purchase or terms-acceptance flow is added.

## Order and exact boundaries

1. Read the existing complete provider inventory before account/catalog/key
   planning. Retain unknown resources. No inventory result is interpreted as
   permission to delete or adopt them. A partial, duplicate, changing or
   unbound paginated result holds admission. DigitalOcean's ordinary and GPU
   inventories are separate reads and are both required by the REST adapter.
2. Fail closed on account/inventory disagreement, account warning, missing
   authentication, unsupported product/contract and quota disagreement. A
   readable account does not prove a payment method or accepted terms.
3. Bind the requested account/project/contract, region, size, image, source
   repository/Head/Tree, exact S1 manifest/config and node identity. Bind the
   fresh price quote in its original currency and price basis. DigitalOcean
   includes the selected base compute/boot disk/public IPv4 tariff; Hetzner
   additionally includes the location's separately priced Primary IPv4 and
   uses project gross prices. Neither is an invoice ceiling: variable traffic,
   taxes where not included and other usage need separate explicit acceptance.
   Missing price, currency, budget or usage authorization holds admission.
4. Reuse the selected existing **public** SSH wire key by SHA-256. Comments and
   display fingerprints do not identify a key. No private SSH key is read and
   no key is generated or registered. A missing registered key holds
   DigitalOcean/Hetzner creation. IONOS Cloud accepts a separately pinned
   existing operator public key for boot-volume injection; its volume GET hides
   `sshKeys`, so no fictitious key-list endpoint is used.
5. Explicit existing resource IDs select reuse. Name similarity alone does not
   adopt an unknown resource. The single operation ID is bound to exact request
   bytes across reuse and creation. Price/account/inventory changes require
   renewed exact admission; observation timestamps themselves do not invalidate
   an otherwise identical authorization.
6. `provider-apply` first reobserves through the authenticated fixed-origin API.
   Paid creation additionally requires an independently pinned, unexpired exact
   authorization, payment evidence and **previously accepted** terms evidence.
   A JSON declaration/pin is a trusted-operator assertion, not cryptographic
   proof of the natural person or independent validation of the payment/terms
   documents. The embedding caller must obtain/validate those through its
   authorized trust channel. This tool neither accepts terms nor repairs payment.
7. Write and fsync the immutable intent before the first POST under the existing
   private filesystem/lock primitives. A crash before/after sending, rejected
   request, lost ACK or ambiguous response fences every later cooperating
   executor into readback. Absence from a list never licenses another POST.
   A rejected operation remains recorded; a separately reviewed, changed
   successor requires a new operation ID and authorization. Do not copy a
   receipt directory to create independent executors for the same operation.
8. Read the resource again by provider ID and exact metadata. A transport ACK,
   name match or metadata receipt proves neither SSH access nor native startup.
   Then check running state, global public IPv4, DNS-to-provider IPv4 binding,
   CA/SNI-validated HTTPS `/health`, fresh node/source and `HEALTHY` status.
9. Run the **existing** monitor verifier in a separate bounded process against
   the same IPv4 pin. It validates exact client, runtime and journal bytes. No
   provider credential or Node preload configuration is inherited. Reobserve
   provider identity/address afterward; drift holds the result.
10. Native host/mount admission, authenticated native effect/restart witness,
    governance and public Mesh acceptance remain separate existing gates.
    All receipts here retain `effect_ack_done=false` and
    `host_admission_verified=false` until those actual gates close elsewhere.

The receipt directory must be owner-only (0700), separate from the immutable
package, and reside on separately admitted durable storage. Each receipt is
create-only (0600), fsynced and read back. The lock fences cooperating local
executors; privileged deletion, storage loss, external provider writers and
multiple unsynchronized receipt stores are outside that guarantee. No claim
of global provider exactly-once support is made.

## Available products and read-only endpoints

| Provider | Exact product | Inventory and catalog reads | Missing live binding |
|---|---|---|---|
| DigitalOcean | `digitalocean-v2` | `/droplets?type=droplets`, `/droplets?type=gpus`, `/account`, `/account/keys`, `/regions`, `/sizes`, `/images` | Warning/conflicting inventory blocks creation before payment/terms |
| IONOS/1and1 | `ionos-cloud-v6` | Existing `/datacenters`, nested servers/public LANs, `/contracts`, `/locations`, `/templates`, `/images` | A 1and1 customer account does not identify this Cloud contract; legacy Cloud Panel is not silently substituted |
| Hetzner | `hetzner-cloud-v1` | `/servers`, `/ssh_keys`, `/locations`, `/server_types`, `/images`, `/pricing` | Existing project/token and independent principal binding required |

IONOS creation is restricted to an existing admitted Cloud datacenter/public
LAN and an exact VCPU/boot-disk specification. It requires a separately pinned,
unexpired contract quote covering compute, boot disk and public IPv4; template
catalogs are not fabricated prices. Existing datacenters/LANs are never created
or changed. Hetzner uses location fields; removed datacenter endpoints are not
queried. No proxy, redirect, credential search, login or automatic retry exists.
Provider failures expose a bounded error class/status, never a raw provider
body containing private data. Inventory persistence whitelists public resource
metadata and excludes passwords, user-data and credentials.

## Commands

Copy the examples outside the package and fill all required nulls with actual
independently verified bindings. Files must be absolute, owner-only 0600 and
not symlinked. The examples contain no grant, credentials or fabricated host.
`--provider-credential` names an existing private bearer-token file. Alternatively
the caller may explicitly provide `DIGITALOCEAN_TOKEN`, `IONOS_TOKEN` or
`HCLOUD_TOKEN` in its process environment; values never appear in arguments,
output, repository or cache. The principal binding is also independently pinned.

```sh
python3 -B tools/qikvrt_self_host.py provider-inventory --provider digitalocean \
  --provider-binding /private/binding.json --provider-binding-sha256 <pin> \
  --provider-credential /private/existing-token --output /private/inventory.json
python3 -B tools/qikvrt_self_host.py provider-classify --provider digitalocean \
  --provider-inventory /private/inventory.json --provider-inventory-sha256 <pin>
python3 -B tools/qikvrt_self_host.py provider-plan --provider digitalocean \
  --provider-inventory /private/inventory.json --provider-inventory-sha256 <pin> \
  --provider-request /private/request.json --provider-request-sha256 <pin>
```

`provider-plan` performs no network call or effect. An independently pinned
connector projection can be classified/planned but cannot authorize an API
create. Declare `complete=false` if a connector omits pagination/total/GPU scope
evidence. `provider-inventory` is GET-only and stops at absent product/credential.

`provider-apply` uses the same binding/request and a durable
`--provider-receipts /private/receipts` directory. Explicit reuse requires no
paid grant. Creation requires `--provider-authorization` and its independent
pin, and binds the verified package/config through `--root`,
`--manifest-sha256` and `--config`. No create is permitted from a cached inventory.
IONOS additionally uses `--provider-quote`/`--provider-quote-sha256` and
`--provider-public-key`/`--provider-public-key-sha256`.

`provider-reconcile` is GET-only: it accepts no instruction to resubmit an intent.
`provider-readback` uses the same package/config and existing verifier. A missing
public native resource stops before any HTTPS/independent-client claim. After
actual host acceptance, continue through existing `admit`, `supervisor` and
native restarted readback; do not turn an admission plan into deployment evidence.

## Sources and validation scope

Provider contracts were checked against these primary sources on 2026-10-06:

- <https://docs.digitalocean.com/products/droplets/reference/api/droplets/>
- <https://docs.digitalocean.com/reference/api/reference/ssh-keys/>
- <https://docs.digitalocean.com/reference/api/reference/sizes/>
- <https://docs.ionos.com/reference/get-started>
- <https://docs.ionos.com/nodejs-sdk/api/contractresourcesapi>
- <https://docs.ionos.com/cloud/compute-services/compute-engine/how-tos/boot-cloud-init>
- <https://docs.hetzner.cloud/reference/cloud>
- <https://docs.hetzner.cloud/changelog>
- <https://docs.hetzner.com/cloud/servers/overview/>

`make self-host-test` includes the admission controls. The provider tests use an
explicit fake control plane for crash/lost-ACK/payment/authorization cases; they
do not provision or prove a live provider integration. Current authenticated
connector observations and missing live bindings are retained in the associated
Work Unit. Live REST/SSH/deployment witnesses must bind their own fresh subjects.
