<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Bidirectional universal-interface serialization and timing

Owner requirement and implementation authorization: Ingolf Lohmann, 23 October
2026. Architecture and requirements are the Owner's contribution; source changes,
test design and this technical specification were prepared by OpenAI Codex.
This candidate extends the existing TEMDD journal, private native ingress and
Owner reminder adapter. It creates no second executor, journal or scheduler.

## Two directions, one durable ordering boundary

External adapters authenticate and authorize callers before submitting INBOUND
envelopes through the existing owner-only Unix ingress or admitted Runtime API.
OUTBOUND envelopes identify their target HMI adapter and principal. A principal
name in an envelope is attribution, never identity or authorization proof.

`qikvrt_hmi_envelope_v1` requires message_id, direction, adapter, principal,
received_at (UTC), content_type (bare media type), payload_base64 and
payload_sha256, plus schema. Unknown fields fail closed. Original binary bytes
and line endings are retained. Base64 is encoding, not encryption. Canonical
metadata uses the existing journal JSON encoding, without claiming RFC 8785.
Human-readable formatting is an adapter projection of these preserved bytes.

Concurrent producers receive sequence numbers after commit and durable readback.
This is local acceptance order, not source time, physical causality or consensus.
Equal adapter/principal/direction/message IDs require identical envelope bytes;
conflicting retries cannot overwrite an original. Producers retain pending items
until persistence readback. Pre-commit crashes, unavailable storage and rejected
frames produce no acceptance ACK. Unlimited traffic is not guaranteed: retain
unaccepted work and apply backpressure. Original writer/copy fences remain.

## Poll, claim, read back

The original Runtime exposes `hmi(operation, arguments)` for enqueue, pending,
claim and acknowledge. Its private Unix ingress accepts these operations in
`qikvrt_hmi_request_v1`. No new public HTTP writer or authentication is added.
The Runtime exact-subject check runs before each operation.

Pending reads are bounded, non-destructive FIFO projections scoped by direction,
adapter, principal and stable consumer. Fetching never acknowledges delivery.
A byte limit never truncates a message or drops remaining entries. Oversized
items require an actually prepared artifact or supported larger transport;
no pointer is invented and the original stays queued.

A durable claim admits one delivery attempt for one stable consumer. The next
stream item waits for its predecessor acknowledgement. Independent streams may
run in parallel. A crashed/ambiguous claim remains visible and cannot expire
into a blind retry. Recover by reconciling the actual recipient readback with
the original payload and claim. Confirmed non-delivery needs a separately
reviewed successor/re-admission path: this candidate adds no automatic reset.
That may hold a stream but does not silently lose or duplicate its contents.

Acknowledgement requires the original claim digest and an adapter-verified
TRANSPORT_READBACK receipt binding payload SHA-256 and receipt identity. Receipt
fields alone do not authenticate a peer: the admitted adapter obtains the real
recipient readback first. One consumer cannot drain another consumer's output.
Delivery, human reading, task completion, native acceptance and EFFECT_ACK_DONE
remain separate. This version adds no destructive journal pruning.

## HMI capabilities and independent internal timing

The ChatGPT adapter uses the one existing Schedule-Tor, no more often than
hourly. This is an HMI capability constraint, not the native clock. One hour is
not a guaranteed maximum latency: delayed/failed polls create explicit gaps.
The native worker continues admitted work independently. Other HMIs may use
their actually available request/reply, stream or event capability; they do not
inherit ChatGPT's limit. Never assume an unsupported client capability.
Tor registration alone proves neither native ingress nor an unattended consumer.

## Work backward from the real deadline

The existing Owner reminder adapter accepts an optional `timing` object with
preparation_seconds, reaction_seconds, safety_seconds and
hmi_delay_budget_seconds. These are explicit nonnegative integer assumptions,
not measured performance guarantees. Do not invent estimates. Existing records
without timing retain their due-only behavior and content identity.

For deadline D, preparation budget P, reaction budget R, margin S and channel
budget H:

- preparation must start by D - P - S;
- the human must be able to react by D - P - S - R;
- publish the reminder by D - P - S - R - H.

Changing H changes publication timing, never the preparation deadline. Compute
in UTC after checking IANA zone/offset, preserving DST. The original executor
becomes eligible at publish_by, not only D. Receipts expose missed budgets.
Its schedule may still be delayed. Calculation neither performs preparation nor
proves readiness or delivery. Preparation uses existing admitted work units and
independent completion readback. Cancellation, expiry and exact-version claims
remain. Unknown budgets/dependencies are visible planning obligations.

## Acceptance boundaries

Fixture tests cover concurrent inputs, duplicate/conflicting IDs, binary bytes,
batches, consumers, FIFO, restart recovery, original Runtime subject fencing,
prior journal behavior and timing across Paris DST. These prove tested source
behavior. The real Unix-ingress test also needs a host allowing Unix sockets.
Full integrity, bootstrap and make test, review, host admission, actual HMI
input/output, recipient readback and exact raumzeitterminal.de delivery are
separate gates. This document claims no scientific or overall product acceptance.
