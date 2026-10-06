<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright (c) 2026 Ingolf Lohmann. -->

# Repository owned mail event handling

Owner instruction of 6 October 2026: condition checks for incoming documents
and comparable mail tasks belong to the repository runtime and webhooks. Do
not create, resume or extend a client-side scheduled watch. The existing EAP
mail client automation was disabled in its native control plane. Other
independently authorized briefing tasks retain their existing scope.

This adapter extends `src/qikvrt_github_api_shim.py`; it does not introduce a
second HTTP server, mailbox scheduler, ledger or public mail-processing
workflow. `src/qikvrt_graph_webhook.py` uses the existing authenticated
`HandlerConfig` ingestion, fsynced storage, audit chain, replay receipts and
independent byte readback. Credentials and business conditions stay in the
host's private binding. Public source and tests contain only synthetic data.

## Event contract

- POST `/webhooks/microsoft-graph/mail`: basic message change notifications.
- POST `/webhooks/microsoft-graph/lifecycle`: missed, removed-subscription and
  reauthorization events.
- A validation POST with `validationToken` returns its decoded opaque value as
  `text/plain`, without requiring the REST client's bearer. It cannot enqueue
  an observation. GET cannot perform a webhook effect.
- Other POSTs require the privately bound subscription ID, tenant ID,
  mailbox resource prefix and constant-time `clientState` comparison. The
  whole batch is validated before any item is ingested. Unknown, rich,
  malformed and unbound notifications are rejected.
- A `202 TRANSPORT_ACK` is sent only after the existing ingest handler and an
  independent byte readback confirm durable private storage. Storage failure
  returns `503`, allowing provider recovery. The response reports
  `document_received=false` and `effect_ack_done=false`.
- Canonical normalized metadata determines the existing immutable artifact
  and request IDs. Repeated requests reuse those stored bytes and receipts;
  secrets are not stored in notification records. Changed message versions
  produce different keys. Mail text, diagnoses and attachments never enter
  Git, public Actions artifacts or logs.

The existing REST entrypoint now constructs `QikvrtGitHubApiServer` and binds
its `threading.Event` as `server.graph_mail_wakeup` when the private Graph
binding is configured. Every independently durable record, including replays,
sets that event. If a later storage operation in a validated batch fails, the
earlier durable records still wake the loop; the HTTP response remains `503`.
Rejected notifications and validation challenges never wake it.

`GraphMailReconciler` is an adapter of the existing native REST service loop
and serialized API handler. It creates no additional thread, worker process or
scheduler. Before serving HTTP, it reconciles existing `graph-<hash>.bin`
records in the same private ingest store. On a wake, the existing
`service_actions` hook clears the event **before** scanning; a concurrent wake
therefore survives for another pass. Idle service-loop iterations do not scan
the store or query the mailbox. There is no timed mailbox poll or timed retry.

Each pass verifies exact normalized metadata and the current subscription,
tenant and mailbox binding, then reuses the native ingest-provenance verifier
and `run_handler` byte verification. A correctly named/hash-matched file alone
is insufficient: the original committed transaction, replay receipt, sidecar,
responsibility and protocol must match. The existing private `api/out` stores
fsynced `graph-<hash>.reconciled.json` receipts with independent byte readback.
Replay and restart revalidate the original evidence and reuse identical
receipts without overwriting them. Corrupt records, symlinks, missing provenance
and conflicting receipts fail closed. A runtime reconciliation failure is
visible as `BLOCK` in `/health`; pending bytes remain for another real delivery
or restart, rather than an automatic timed retry.

These receipts attest only `PRIVATE_GRAPH_EVENT_RECONCILIATION_ONLY`. They
retain `native_mail_consumer_bound=false`, `provider_readback_performed=false`,
`document_received=false` and `effect_ack_done=false`. The inbox records remain
intact for the separately admitted mail/lifecycle consumer. No executable Graph
mail consumer was found in the bound #477 source tree. The existing server loop
and handler are reused here; no external consumer is invented or imported from
an unmerged Self-Host lane.

The signal and local reconciliation are not task completion. Basic notifications
may omit an event ID or etag: the worker must independently fetch the current
message, reconcile its version, and deduplicate actual document/notification
effects by exact hashes. Ingress deduplication alone cannot prove that every
distinct mailbox mutation was observed.

The admitted mail consumer must still independently reconcile provider state
on startup/recovery and on replay. A local event-byte receipt is not a provider
cursor or a completed mail observation, especially when a basic notification
omits its event ID or etag.

## Private deployment binding

Set `QIKVRT_GRAPH_WEBHOOK_BINDING` to an absolute, owner-only regular JSON
file. Reuse the REST shim's exact `QIKVRT_ALLOWED_REPOSITORY` and
`QIKVRT_API_PRINCIPAL`. Provision a separate owner-only private state directory
on a verified persistent host. Symlinks and public-readable bindings are
rejected. Example structure; replace all placeholders privately:

```json
{
  "schema": "qikvrt_graph_mail_webhook_binding_v1",
  "repository": "owner/repository",
  "responsibility_owner": "owner",
  "state_root": "/var/lib/qikvrt/private-mail",
  "accepted_effect_scope": "OPAQUE_GRAPH_MAIL_EVENT_STORAGE_ONLY",
  "notification_url": "https://own-host.example/webhooks/microsoft-graph/mail",
  "lifecycle_url": "https://own-host.example/webhooks/microsoft-graph/lifecycle",
  "subscriptions": [{
    "id": "00000000-0000-0000-0000-000000000000",
    "tenant_id": "22222222-2222-2222-2222-222222222222",
    "resource_prefix": "users/verified-mailbox-id/messages/",
    "client_state": "REPLACE_WITH_A_DISTINCT_PRIVATE_RANDOM_SECRET"
  }]
}
```

The all-zero ID explicitly denotes pending registration. It permits the
validation challenge but cannot authenticate a notification. Only the native
provider's independently read-back subscription ID replaces it. The operator
must bind the actual authenticated mailbox and tenant identities; sample
identities are not credentials or evidence.

`tools/qikvrt_graph_subscription.py` uses a pre-existing, privately provisioned
delegated Graph OAuth bearer. It creates no application, consent grant, login
flow or client scheduler. It verifies `/me` against the exact mailbox prefix,
reads the complete bounded subscription inventory, admits one create or
renewal effect and independently reads it back before atomically updating the
private binding. Matching existing subscriptions are reused. An ambiguous
effect is resolved by readback, never an automatic second write. A missing
already-bound subscription or conflicting private state stops with `BLOCK`.

```sh
python3 -B tools/qikvrt_graph_subscription.py \
  --binding /private/graph-mail.json --repository owner/repository --principal owner
```

This is a credential-free plan. After the same existing REST shim is admitted
on the independently verified HTTPS host, add `--apply --token-file
/private/graph-oauth-bearer` to register; use `--renew` for an exact existing
subscription. Do not copy OAuth material out of a client connector.

Subscriptions expire. The admitted native worker must handle lifecycle events
to renew/re-authorize the subscription and perform an authenticated delta
reconciliation after a missed event or removed subscription. Microsoft advises
against a separate reauthorize and PATCH within the same ten-minute window;
this tool implements only PATCH renewal. Registration, expiry renewal, token
refresh, recovery, worker binding and actual document receipt remain distinct
acceptance requirements. A lost-response recovery or local test is not a
continuous-operation claim.

## Deployment acceptance and current boundary

Activation requires the exact reviewed source, a verified persistent own host,
public HTTPS challenge readback, a scoped delegated Graph permission and native
subscription receipt, an admitted repository worker, a real provider event,
independent message/attachment readback, restart recovery and a verified
owner-private notification. Only document delivery and its required acceptance
close a document task. There is no automatic reply, complaint or medical/legal
decision.

The currently exposed Outlook connector can search/read mail but exposes no
Graph subscription registration action or transferable OAuth binding. No
matching own-host/worker HTTPS endpoint is established by this candidate's
local tests. The candidate therefore remains activation-blocked. The local
native REST binding does not establish a persistent production worker, public
callback, Graph OAuth, registered subscription or real mail readback. Disabling
the client watch is verified; repository reception of live mailbox events is
not yet established.
The resulting monitoring gap must remain visible, rather than restarting the
client watch as a fallback.

## Verification and primary contracts

`make graph-mail-webhook-test` runs real native-loop HTTP calls, wake ordering,
startup reconciliation, concurrent wake preservation, replay without receipt
overwrite, abrupt process exit/restart, provenance/tamper/symlink/storage
negative controls and synthetic control-plane tests. `make test` includes
this target and all existing gates.
No new dependency or undeclared runtime is required.

- [Graph webhook delivery and validation](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
- [Outlook notification permissions and resource scopes](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview)
- [Subscription creation](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [Lifecycle recovery](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events)
- [Subscription expiration](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)
