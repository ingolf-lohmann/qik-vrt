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

The original event receipts continue to attest only
`PRIVATE_GRAPH_EVENT_RECONCILIATION_ONLY`; their existing false provider/mail
fields remain correct and immutable. The separately configured native
`GraphMailConsumer` now extends this same reconciliation pass with
`PRIVATE_GRAPH_MAIL_PROVIDER_OBSERVATION_ONLY`. No consumer is silently activated
when its private binding is absent. Explicit invalid consumer configuration
blocks startup before HTTP serving.

## Native provider reconciliation and private inbox handoff

`src/qikvrt_graph_mail_consumer.py` reuses the existing subscription tool's
private `Graph` transport, no-redirect handler, owner-only file reads and the
native handler's ingest, provenance, process lock and fsynced atomic writer.
The ordinary REST entrypoint works with `-S` and from another working directory.
It creates no second server, worker, scheduler or timer. Provider reads occur
only in startup/recovery and a pass triggered by a durable Graph wake, including
replayed basic notifications and all three lifecycle event kinds. Idle service
iterations perform no scan or provider read. After a failure another genuine
wake or process restart is required; there is no timed retry.

Each admitted pass independently reads `/me` and verifies the bound mailbox,
resolves each configured folder's native ID, then completes that folder's delta
round. Opaque next/delta links must keep the exact HTTPS origin and folder path;
empty intermediate pages are followed, cycles, excessive pages and incomplete
responses fail closed. Every touched message is independently read through
`/me/messages/<provider-id>` using the selected properties and
`Prefer: IdType="ImmutableId"`. A current 404 or changed `parentFolderId` is a
removal from the selected folder. Provider data, rather than notification ID,
ETag or event key, determines current membership and version. Canonical hashes
include both the provider version and selected content; changed selected content
is detected even if the version marker is unchanged. A complete selected
projection is required when the version marker is absent. Duplicated event bytes
still wake another provider read without re-emitting an unchanged message.

No notification resource is a network target. Graph reads use only fixed
`https://graph.microsoft.com/v1.0/me` endpoints. The existing transport is
GET-only for this consumer, rejects redirects, duplicate/non-finite JSON and
responses over 1 MiB. Each folder round is bounded to 128 pages, the selected
state to 10,000 messages and the pass to 12,000 successful reads. An HTTP 410
on a previously saved delta cursor permits one provider-justified initial
resynchronization in the same pass. Only a complete replacement may remove
previously observed messages absent from that scope; a failing reset is not
retried. Other HTTP/OAuth/provider failures leave the cursor unchanged.

Only after **all** configured folders and current message reads succeed does
native ingest commit an immutable `mail-observation-<hash>.bin` capsule, its
sidecar, original transaction and responsibility-bound provenance. The capsule
contains selected private messages, version hashes, actual changes/removals,
provider response hashes, cursor state, observed lifecycle signals and a link to
the preceding committed observation. The atomic, independently read-back
`.qikvrt/api/out/graph-mail-current.json` points to that capsule. Compare-and-set
under the existing process lock prevents concurrent rounds or changed private
bindings from overwriting newer state. Network reads do not hold the native
handler lock. Partial rounds, storage failures and process loss before pointer
commit cannot advance a provider cursor.

The downstream private inbox evaluator calls
`GraphMailConsumer.read_observations(webhook_binding, after_key=<its last
accepted observation>)`. It independently verifies native provenance and reads
only the committed hash-linked chain in chronological order. An ingested
candidate left unreachable by process loss is ignored. Unknown continuation
anchors, broken evidence and exceeded readback bounds block rather than return
a partial accepted history. The evaluator keeps its own accepted key; neither
an observation receipt nor cursor progress accepts a document or sends a user
notification. The public health projection reports only state, counts and scope,
never mailbox/message/folder identities, private observation keys, mail content,
OAuth material, cursor URLs or raw provider errors.

Coverage is explicitly `CONFIGURED_FOLDERS_SELECTED_MESSAGE_FIELDS`. Configure
`inbox` for incoming mail or list other admitted folders privately; the
`/me/messages` subscription can wake a pass for changes outside these folders,
but that does not extend the readback scope. Delta/current reads are not a
globally atomic mailbox snapshot, a full audit of every intermediate mutation,
an attachment download or proof of actual document delivery. Tenant identity
remains a private deployment assertion (`PRIVATE_CONFIGURATION_NOT_TOKEN_ATTESTATION`),
separate from the independently verified mailbox identity. No OAuth consent,
refresh, subscription create/renew/re-authorize or HTTPS activation is performed
by the consumer. Lifecycle signals are retained for separately admitted
control-plane recovery; successful mail reconciliation does not claim that an
expired or removed subscription was repaired.

## Private classification, tasks and day plan

The compatible #477 successor is reused: `GraphMailConsumer` is the producer;
`GraphMailTaskConsumer` in the same source file consumes only its committed,
provenance-verified observation chain. `REUSE_BEFORE_CREATE` searched the
available 2,318-commit history's mail/inbox/reminder/lifecycle path inventory,
current source and open successors. The compatible provider consumer already
exists at `fb986e6aa70233e330377b6c86e75968536e51ec`; the historical reminder
changes provide the day-plan adapter but no mail classifier/task consumer.
There is no new source module, workflow, scheduler, worker or public registry.

Set `QIKVRT_GRAPH_MAIL_TASK_BINDING` only on the existing private REST host,
together with its webhook and provider bindings. Its absolute owner-only file
has this schema (all addresses below are synthetic placeholders):

```json
{
  "schema": "qikvrt_graph_mail_task_binding_v1",
  "repository": "owner/repository",
  "responsibility_owner": "owner",
  "state_root": "/var/lib/qikvrt/private-mail",
  "accepted_effect_scope": "PRIVATE_MAIL_CLASSIFICATION_AND_TASK_PLAN_ONLY",
  "owner_addresses": ["owner@example.test"],
  "human_senders": ["contact@example.test"],
  "timezone": "Europe/Paris"
}
```

Addresses must be sorted, distinct and case-normalized. `human_senders` is an
explicit private contact classification; it is not authentication of a natural
person or protection against spoofed sender headers. An unknown sender's
recognizable directly addressed request is retained for owner review in the
attention lane; it does not acquire verified human status or a derived task.
Changing contact, owner, mailbox or folder bindings blocks reuse of existing
state until an explicitly reviewed private migration. No real address, OAuth
material, contact list or private state is checked into Git.

Current message GETs additionally select `toRecipients`, `ccRecipients`,
`isDraft`, `internetMessageHeaders` and `uniqueBody`, with immutable IDs and
`outlook.body-content-type="text"`. Existing committed observations remain
readable when these extra fields are absent. Such a projection cannot derive
a task. The existing folder-delta selection/cursor contract is retained.
`bodyPreview` is truncated, so it cannot be the basis of a task. The rule scope
is `SELECTED_CURRENT_UNIQUE_BODY_RULES_ONLY`, not complete semantic mail
understanding. HTML, incomplete fields and requests outside the supported
German/English/French rules do not create guessed actions. Explicit request
rules and excerpts remain in private state for human inspection.

Direct requests require the owner in To, an explicitly classified human sender,
a received non-draft message and a supported positive request in the current
unique text. Bulk/automatic headers, no-reply senders, self-sent messages,
CC-only messages, quoted/forwarded text and negated requests cannot derive a
task. Explicit urgency words and Graph `importance=high` create classification
signals. A signal is rule evidence, not proof of urgency or a commitment. An
urgent or important FYI can enter attention without creating a task. Dates and
deadlines are never invented; derived tasks have `due=null` and require owner
confirmation with evidence before completion.

Each provider message has one stable task identity across replay, version/read
flag changes and moves. An updated recognized request updates its source
binding. Removal from selected folders becomes
`SOURCE_UNAVAILABLE_REVIEW_REQUIRED`; removal of the recognizable request
becomes `SOURCE_CHANGED_REVIEW_REQUIRED`. Neither means completed or cancelled.
Lifecycle signals are retained privately and create no subscription/OAuth
recovery task or control-plane write.

The existing `tools/qikvrt_owner_reminders.py` now accepts the bounded private
mail/task state through `project_private_mail_plan`. It produces a private
owner-timezone day plan with tasks ranked by urgency/importance and a separate
attention/notification-intent lane. This event-native lane does not execute the
public reminder delivery path, invent Library references, send a notification
or change `OWNER_REMINDERS_V1.json`. The existing scheduled reminders retain
their independent scope. Actual private notification delivery remains an
independently admitted and read-back effect.

A single native immutable `mail-tasks-<hash>.bin` capsule includes mail status,
source-bound tasks and that exact day plan. Native provenance, every source
message in the committed provider chain and the entire private plan are
independently read back before a compare-and-set, fsynced atomic
`graph-mail-tasks-current.json` pointer advances. Losing the process before
that pointer leaves an ignored orphan and a replayable observation. Competing
writers, forged excerpts, uncommitted provider sources, corrupt provenance,
symlinks and changed bindings fail closed. The existing REST pass first
recovers accepted provider observations, then reads the provider and consumes
newly committed observations. A later provider failure cannot erase recovered
tasks. Idle loops do nothing; failure requires a genuine delivery or restart.

`read_private_state(webhook_binding)` returns the verified capsule and day plan
only to the host-private caller. It is not a public endpoint or public receipt.
Public health includes scope/status/counts only; task IDs, observation keys,
mail text, subjects, sender/recipient identities, cursor URLs, raw exceptions
and contact classifications never enter it. All verification fixtures are
synthetic. Classification and task-plan binding do not establish public HTTPS,
OAuth, subscription registration, a live provider mail event, document receipt,
human task completion or `EFFECT_ACK_DONE`.

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

Set `QIKVRT_GRAPH_MAIL_CONSUMER_BINDING` in the existing REST runtime to an
additional absolute, owner-only private JSON file. Its owner/repository/store,
tenant and mailbox must exactly match the webhook binding. Example schema only:

```json
{
  "schema": "qikvrt_graph_mail_consumer_binding_v1",
  "repository": "owner/repository",
  "responsibility_owner": "owner",
  "state_root": "/var/lib/qikvrt/private-mail",
  "accepted_effect_scope": "PRIVATE_GRAPH_MAIL_PROVIDER_OBSERVATION_ONLY",
  "tenant_id": "22222222-2222-2222-2222-222222222222",
  "mailbox_id": "verified-mailbox-id",
  "folder_ids": ["inbox"],
  "token_file": "/private/graph-oauth-bearer"
}
```

The bearer remains host-private and must already authorize `/me` and the
selected mail reads (the existing delegated account/`Mail.Read` grant). A file
or configuration alone is not a verified OAuth or live-mail gate. Changing the
mailbox, tenant or folder scope does not silently inherit old cursor evidence.
The binding and all provider-derived data stay outside public Git and Actions
artifacts. Neither a connector token nor the example values are a live binding.

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
negative controls, synthetic control-plane tests and the native provider
consumer controls. These include a real HTTP wake, versionless/idless replay,
independent current message reads, delta reset, page/read bounds, deletion/move,
private inbox continuation, stale-writer rejection and process-loss recovery.
The private task controls add real local HTTP-to-plan execution, explicit
DE/EN/FR request derivation, urgency-only attention, unknown/bulk/CC/quote/draft
and negation boundaries, stable IDs on replay/update/move, no false completion
on removal, committed source/excerpt proof, abrupt fresh-process loss and
recovery, storage/tamper/symlink/binding/concurrency controls, owner-timezone
priority projection and no idle/timed retry or public content leakage. `make test` includes
this target and all existing gates.
No new dependency or undeclared runtime is required.

- [Graph webhook delivery and validation](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)
- [Outlook notification permissions and resource scopes](https://learn.microsoft.com/en-us/graph/outlook-change-notifications-overview)
- [Subscription creation](https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions?view=graph-rest-1.0)
- [Lifecycle recovery](https://learn.microsoft.com/en-us/graph/change-notifications-lifecycle-events)
- [Subscription expiration](https://learn.microsoft.com/en-us/graph/api/resources/subscription?view=graph-rest-1.0)

- [Message delta rounds and folder scope](https://learn.microsoft.com/en-us/graph/api/message-delta)
- [Immutable Outlook IDs](https://learn.microsoft.com/en-us/graph/outlook-immutable-id)
