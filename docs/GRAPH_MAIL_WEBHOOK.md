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

If the admitted host binds its existing worker's `threading.Event` as
`server.graph_mail_wakeup`, every durably accepted delivery, including replays,
wakes that worker. This signal is not task completion. Basic notifications
may omit an event ID or etag: the worker must independently fetch the current
message, reconcile its version, and deduplicate actual document/notification
effects by exact hashes. Ingress deduplication alone cannot prove that every
distinct mailbox mutation was observed.

On startup or recovery, the existing worker must reconcile pending
`graph-<hash>.bin` records in the same private ingest store before waiting for
the next event. This adapter does not claim that such a worker has been bound
or that any document has arrived. There is no timed mailbox poll.

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
Graph subscription registration action or transferable OAuth binding. A
matching own-host/worker HTTPS endpoint is not currently admitted. The
candidate therefore remains activation-blocked. Disabling the client watch is
verified; repository reception of live mailbox events is not yet established.
The resulting monitoring gap must remain visible, rather than restarting the
client watch as a fallback.

## Verification and primary contracts

`make graph-mail-webhook-test` runs real loopback HTTP calls, replay across
fresh server processes and synthetic control-plane tests. `make test` includes
this target and all existing gates.
No new dependency or undeclared runtime is required.

- [Graph webhook delivery and validation](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
- [Outlook notification permissions and resource scopes](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview)
- [Subscription creation](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [Lifecycle recovery](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events)
- [Subscription expiration](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)
