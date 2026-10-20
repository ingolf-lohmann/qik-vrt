# Privacy-preserving interaction archive

QIK-VRT now defines a repository-native contract for preserving user inputs and
machine outputs without placing plaintext conversations, audio transcripts,
credentials, or decryption identities in the public source repository.

## Architectural boundary

The public `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt` repositories contain
only the implementation, schemas, tests, documentation and integrity rules. An
operational deployment writes interaction records into a **separately
access-controlled archive repository or worktree** selected with
`--archive-root`.

The archive operator commits and replicates that encrypted archive through the
private repository's normal Git policy; the public source repositories never
receive those operational records.

Each persisted interaction consists of:

- a minimized JSON event envelope under `events/`;
- an `age`-encrypted payload under `blobs/`;
- SHA-256 bindings for plaintext and ciphertext;
- a previous-event hash and canonical event hash;
- an opaque conversation identifier, role, purpose, consent identity and
  retention boundary.

The archive contains no plaintext payload and no private decryption identity.
A public repository must therefore never be used as the operational archive
unless its ciphertext and metadata exposure has been separately approved.

## Required properties

1. **Explicit authorization:** append, export and retention tombstone operations
   require distinct exact confirmation strings.
2. **Data minimization:** names, email addresses and free-form subject metadata
   are not required by the format. Deployments should use opaque identifiers.
3. **Confidentiality:** payload encryption is delegated to the reviewed `age`
   executable. QIK-VRT does not invent a custom cipher.
4. **Integrity:** every event and ciphertext blob is SHA-256-bound; events form
   an append-only hash chain.
5. **Availability and reachability:** the archive is a normal repository tree
   whose JSON envelopes and encrypted blobs can be replicated, backed up and
   addressed by path and digest.
6. **Machine readability:** event and export documents use canonical JSON
   contracts.
7. **Exportability:** an authorized holder of the `age` identity can export a
   complete conversation or the entire archive as deterministic JSON.
8. **Retention boundary:** a tombstone records a retention or restriction
   decision without falsifying prior history. Effective erasure from Git history
   requires separately governed history rewriting or cryptographic key
   destruction; a tombstone alone is not erasure.

## Append one user input

```bash
python3 -B tools/qikvrt_interaction_archive.py append \
  --archive-root ../qik-vrt-private-interactions \
  --content-file user-input.txt \
  --recipient 'age1...' \
  --conversation-id conversation-opaque-001 \
  --role user \
  --created-at '2026-07-25T08:00:00+02:00' \
  --purpose scientific_interaction_continuity \
  --consent-id consent-2026-07-25 \
  --retention-until '2027-07-25T00:00:00Z' \
  --confirm PERSIST_ENCRYPTED_INTERACTION
```

The same command with `--role assistant` persists the corresponding machine
output. Tool and system events are also permitted when they are relevant to
reconstructing the accountable interaction chain.

## Verify

```bash
python3 -B tools/qikvrt_interaction_archive.py verify \
  --archive-root ../qik-vrt-private-interactions
```

Any changed envelope, broken predecessor link, missing ciphertext or mismatched
digest causes `BLOCK`.

## Export on request

```bash
python3 -B tools/qikvrt_interaction_archive.py export \
  --archive-root ../qik-vrt-private-interactions \
  --identity-file ~/.config/age/keys.txt \
  --conversation-id conversation-opaque-001 \
  --request-id export-request-001 \
  --output interaction-export.json \
  --confirm EXPORT_AUTHORIZED_INTERACTIONS
```

The export includes the original envelopes and decrypted UTF-8 payloads. The
export file is itself reported with SHA-256. It must be delivered only through
an authorized channel and should not be committed to either public repository.

## Retention tombstone

```bash
python3 -B tools/qikvrt_interaction_archive.py tombstone \
  --archive-root ../qik-vrt-private-interactions \
  --event-id event-user-0001 \
  --authorization-id retention-request-001 \
  --created-at '2026-07-25T09:00:00+02:00' \
  --confirm RECORD_RETENTION_TOMBSTONE
```

## Source-bound outgoing correspondence — Owner task 2026-10-20

Use this existing archive for scientific mail, including original provider
records, recipient lists and attachments. Outlook is the preferred business
mailbox. Historical source inspection does not change that provider choice.
The implementation contribution is OpenAI Codex; the requirement and product
authority are Ingolf Lohmann's. Private correspondence stays outside both
public repositories; public evidence contains only neutral scope and status.

`mail-receipt` derives RFC Message-ID, exact header Date and its UTC form,
From/To/CC, Reply-To, References, Received headers, enclosed message identities
and hashes of decoded attachment leaves. It preserves the complete unchanged
RFC 822 bytes, including MIME structure, in base64. Outer forwards and their
enclosed originals retain separate identities. Provider IDs are separate from
RFC Message-IDs and remain bound to the named account. A header's Date is a
declaration; record actual provider timestamps independently when available.

```bash
python3 -B tools/qikvrt_interaction_archive.py mail-receipt \
  --source-file ../private-mail/original.eml \
  --account 'owner@example.test' --provider-message-id 'actual-provider-id' \
  --observed-at '2026-10-20T14:00:00Z' \
  --evidence-file ../private-mail/provider-response.json \
  --evidence-file ../private-mail/independent-inbox-readback.json \
  --output ../private-mail/source-receipt.json

python3 -B tools/qikvrt_interaction_archive.py mail-verify \
  --receipt-file ../private-mail/source-receipt.json
```

These are operator examples; placeholders confer no account access. Output is
created with owner-only file permissions, fsynced and independently reread.
An identical existing receipt is read back; a conflict cannot overwrite it.
Plaintext output inside a source checkout is rejected. Source snapshots are
preserved as opaque bytes with size and SHA-256, never interpreted as trusted
instructions or promoted to delivery evidence. The source account/record
binding is a caller declaration pending authenticated provider readback.

The self-contained receipt may then be persisted with the existing `append`
command using `--media-type application/vnd.qikvrt.mail-source-receipt+json`.
This validates the receipt before encryption. Use the existing authorized age
recipient, private archive, retention policy and consent identity. Never
manufacture a key binding, silently store plaintext in the source repository,
or call test encryption productive confidentiality. The existing archive
verify/export and private repository replication paths remain authoritative.
Append a separately source-bound assessment or correction; retain originals.

| Evidence stage | Required independent source | Does not establish |
| --- | --- | --- |
| Stored sent copy | Authenticated account, provider ID and original record in Sent | Recipient delivery |
| Provider acceptance | Actual API/SMTP acceptance receipt, bound request and time | Remote MX or inbox acceptance |
| Recipient server acceptance | Exact-recipient DSN or trace with original identity | Inbox placement or human reading |
| Mailbox ingress | Authenticated target-mailbox/folder readback, identity and attachment correlation | Delivery to other recipients or visibility in a particular app |
| Human reading | Separately qualified evidence; an isRead flag is insufficient | Understanding or endorsement |

Receipt generation verifies source fixity only. All five evidence states stay
`NOT_ASSESSED`; a SENT label, 202, CC address, quoted Message-ID or supplied
snapshot cannot change them. A digest detects inconsistent bytes, not a forged
provider record, trusted timestamp or administrative rewrite. Do not describe
this technical record as a certified WORM archive or legal compliance proof.

Every authorized outgoing operation must follow this sequence in the same
work ring:

1. Reobserve actual sender/account, final To/CC/BCC, exact attachment bytes,
   purpose and prior authorization. Use Outlook for business correspondence;
   apply the standing owner CC instruction and existing no-contact decisions.
2. Bind the outgoing intent to its native Work Unit before the one send. Record
   the actual provider result without converting a queued/ambiguous response
   into delivery. This contract does not itself authorize any send.
3. Read the stored sent original independently. Preserve its RFC 822/MIME bytes,
   provider identity, timestamp, final recipients and decoded attachment hashes
   with `mail-receipt`. If the adapter cannot expose MIME or Message-ID, retain
   its exact metadata and an OPEN obligation for that operation; do not invent
   an original or silently switch mail providers.
4. Persist and verify the receipt through this existing private archive. Record
   genuine mailbox ingress/DSNs as separate source-bound assessments. An
   absent or unfindable copy requires investigation before any resend.
5. Close the Work Unit with actual native event IDs/digests, source readback and
   storage receipt. Keep integration, host activation and other-client adoption
   OPEN until separately verified.

Reuse analysis on 2026-10-20: Authority Main's SMTP component
`deploy/universal-terminal/qikvrt_smtpd.py` is a sink and explicitly records
`relay_performed=false`; it is not an outbound mail relay. PR #477 at
`cbf0746db2600c51cec53547caa75aa3c504dd91` extends private Graph mail observation
and incoming problem/task handling. Its selected message projection and
notification path are not an original MIME/attachment archive or an outgoing
send transaction. That unmerged consumer remains a separate integration.
This extension reuses the existing interaction archive and test target; it
adds no sender, provider, timer, OAuth scope, subscription or second journal.
Productive future capture requires the existing authorized mail caller to
execute this sequence and bind its private archive/key on the original host.
Source presence and synthetic tests alone do not demonstrate that activation.

## General non-claims

This mechanism is not, by itself, legal compliance certification. Repository
operators remain responsible for lawful basis, information duties, access
control, retention schedules, key management, backup governance, data-subject
requests and jurisdiction-specific obligations. The implementation establishes
technical confidentiality, integrity, provenance and export primitives; it does
not decide whether a particular processing purpose is lawful.
