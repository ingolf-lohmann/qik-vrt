<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Technical text contribution: OpenAI Codex. -->
# Portable monolithic Mesh repository

Owner requirement, 2026-10-06: one ordinary local repository file and a React
HTML Universal Terminal, including mobile file selection; cloud persistence
is interchangeable and connected explicitly through the Universal Transceiver.
GitHub and Git are optional source/hosting adapters, not the client data model.

The existing S1 monitor, React runtime and package exporter are extended. The
previous monitor JSON journal and native SQLite effect ledger have no portable
browser decoder or single-file virtual source tree. They cannot satisfy this
requirement unchanged. The shared codec, file persistence adapter and React
panel are components on the existing listener, not an executor or a parallel
deployment pipeline. The unchanged native effect ledger remains a distinct
live operational store; automatic migration or replication of its effects
into this format is **not** claimed by the portable source export.

## Byte format v1

The filename is `repository.qmesh` in the cloud volume. Local copies may use
another normal filename. No extended attributes, resource forks, links,
directories, Git database, WAL or sidecar index are needed to read the object.
The portable v1 profile admits at most 4,294,967,295 bytes. This is a profile
limit, not a claim about every device's available storage. Node's cooperative
writer uses a transient exclusive `.lock`; it is not repository content.

The first eight bytes are the ASCII magic `QIKMESH1`. Each following frame is:

| Field | Bytes | Encoding |
| --- | ---: | --- |
| Metadata length | 4 | Unsigned big-endian integer |
| Payload length | 4 | Unsigned big-endian integer |
| Metadata | 1–16,384 | Canonical UTF-8 JSON |
| Payload | 0–1,048,576 | Original binary bytes |
| Frame digest | 32 | Raw SHA-256 bytes |

Canonical JSON sorts object keys, retains array order, uses JSON string
escaping and contains no whitespace. Metadata has exactly `sequence`, `id`,
`kind`, `key`, `previous_digest`, `content_sha256`. Sequence starts at zero;
IDs are unique within a repository. Payload SHA-256 must match. The frame hash
is SHA-256 of UTF-8 `qikmesh-frame/v1` followed by NUL, previous digest bytes,
the two length fields, metadata and payload. The initial previous digest is
32 zero bytes. A reader rejects unknown versions, duplicate identities,
noncanonical JSON, missing references, reordered or incomplete frames and
digest mismatches. The operational reader admits at most 100,000 records.

The first record is `genesis`: its ID equals the repository identity and its
payload declares `qikvrt-mesh-file/v1` and provenance. Subsequent kinds are:

- `chunk`: original binary payload, addressed by payload SHA-256.
- `entry`: virtual key and a canonical descriptor containing `bytes`,
  `media_type`, and ordered `chunks` with digest and byte count. All referenced
  chunks must already exist. The descriptor SHA-256 is a **content root**,
  not a substituted claim about the SHA-256 of the concatenated whole file.
- `event`: opaque retained event bytes. Presence is not a native Effect-Ack.

Repeated virtual keys create revisions; earlier frames remain. Virtual keys
are exact valid Unicode strings up to 4,096 characters without controls. They
are never normalized, extracted as OS paths or executed. Thus reserved names,
case distinctions, long components and different Unicode normalization forms
can remain internal data without becoming host filesystem paths.

SHA-256 supplies consistency checking, not authorship authentication. It does
not prevent an adversary from rebuilding an entire file. A known independent
checkpoint can reject history rollback; an unpinned first open cannot detect
a complete, internally consistent substitution. Repository identity and
checkpoint checks preserve this boundary.

## Local React client

`universal-terminal.html` includes the already locked React 19.2.6 runtime,
complete MIT notices, codec, terminal component and styles. Opening it needs
no Git, Node, Python, service worker, CDN or cloud connection. A device must
actually support running local HTML/JavaScript; some mobile file viewers are
not browsers. The same client can be served as ordinary HTML where local HTML
execution is unavailable. Actual iOS/Android device validation remains open.

File chooser + Blob reads + save-copy is the default. Imports are read in
bounded 1 MiB blocks. New revisions stay a visibly pending working copy until
the downloaded file is reopened or a direct file handle is read back. A
download click never establishes persistence. File System Access is optional
and feature-detected. A direct write checks the saved head before writing and
verifies the complete resulting chain after close; uncertain writes require
reopening. Its OS/device durability and exclusion against noncooperating
external programs are not established by the browser API.

The terminal opens, verifies and lists entries, reads text, exports exact
binary content, imports local files, appends text revisions, saves copies and
synchronizes a selected cloud URL. Imported content is data, never evaluated
as code. The chosen Owner key remains only in React session memory. There is
no mandatory account and no automatic cloud discovery.

## Cloud REST carrier

The existing `createMonitor` listener accepts an optional `MeshFileStore`.
S1 private configuration may set `mesh_file: "repository.qmesh"`; the existing
Owner terminal token authorizes only these storage routes. The file must
already exist. A missing file or failed read never creates an empty successor.

| Route | Operation | Guard |
| --- | --- | --- |
| `GET /api/mesh-file/status` | Full sanity read, metrics and capacity decision | Bearer Owner key |
| `GET /api/mesh-file/bytes` | Stream file, ETag = verified head | Bearer Owner key |
| `GET /api/mesh-file/bytes?after=HEAD` | Stream exact frame suffix | Known prefix + Bearer |
| `POST /api/mesh-file/append` | Append bounded binary suffix | Bearer + `If-Match: "HEAD"` |

Append requests admit at most 8 MiB. The cooperating writer acquires exclusive
create-only lock, rechecks file identity and expected head, verifies the entire
proposed suffix, checks available space when statfs is supported, appends,
requests OS fsync and reads back the resulting chain before acknowledging
storage. A lost response is resolved by a fresh status read. A repeated exact
suffix under its old head has no new effect. Divergent histories, same-ID
changed bytes and competing heads are held, never merged or overwritten.

Partial writes are left intact and further writes are quarantined. Readers
do not truncate incomplete tails. A process killed while holding the lock may
leave it behind; clear it only after independently confirming the old writer
is stopped and inspecting retained bytes. File consistency does not attest
physical media, privileged external writers, provider persistence or native
effect replication. There is no automatic writer takeover.

No permissive CORS wildcard is installed. By default, the API accepts its own
origin. Operators may declare exact HTTPS origins using
`mesh_file_allowed_origins`. A local `file:` client generally uses Origin
`null`; permitting literal `null` is an explicit operator choice and still
requires the Owner key. Redirects are refused; remote connections require
HTTPS except loopback development. CORS, routing and HTTPS admission must be
verified on the actual host before internet use.

The byte storage contract is `read range`, `append if head matches`,
`durable readback`, `capacity` and `exclusive writer`. Another persistence
adapter can implement it without changing the format or React client. No
unimplemented provider adapter is reported as working.

## Sanity, metrics and orchestration

Every explicit sanity check verifies framing, content hashes, chain,
repository identity, sequence, unique IDs, chunk closure and entry sizes.
Node additionally compares inode/device/size/timestamps before and after the
read. A session retains a confirmed checkpoint; it cannot accept an older
file in place of the confirmed history. Externally pinned checkpoints are
required for rollback detection across an otherwise unbound fresh process.

JSON telemetry includes file bytes, record/entry counts, read/write operations
per second, byte throughput, mean operation latency, fsync activity, errors,
measurement time and rolling-window duration. These are **this adapter's file
I/O**, not device IOPS. statfs reports mounted-filesystem free/total bytes when
supported. Browser Blob reads do not reveal the selected filesystem's free
space or physical write rate; unavailable values stay unknown. Numeric labels
remain readable independently of the analogue dial and color. Keyboard focus,
44-pixel controls, live status, error announcements and reduced motion are
provided by the existing React panel.

The same status is consumed by the adapter: corruption, uncertainty or writer
lock gives HOLD; known capacity below the 2 MiB reserve blocks admission.
`orchestration.accept_writes`, batch limit and reserve are machine-readable.
These bounded storage decisions do not claim autonomous optimization of the
whole Mesh or safe native-effect failover.

## Existing export and recovery path

Use the existing exporter on a clean exact source commit:

```sh
python3 -B tools/qikvrt_self_host.py portable --root . \
  --expected-head "$SOURCE_COMMIT" --expected-tree "$SOURCE_TREE" \
  --output /absolute/new-output
```

It exports every committed source blob into the one file, independently checks
each Git blob identity while writing, retains a source-tree mode manifest,
fsyncs and verifies the finished object. Git is needed for this **build-time
source export**, not for using the output. The export contains the exact source
tree; it does not pretend to contain unavailable Goldkelch live checkout or
Railway ledger state. Output is create-only. Existing S1 `snapshot-state` /
`restore-state` retain the optional cloud file byte-for-byte under the original
quiescence and create-only restoration gates. Their aggregate 2 GiB snapshot
profile remains unchanged.

Source entries retain original committed blob bytes. Checkout-only line-ending
conversion (for example CRLF for Windows `.cmd` files) is not applied inside
the monolith. The embedded source-tree descriptor labels that representation.
Legacy integrity inventories describe their materialized checkout scope;
their bytes are preserved and are not silently reinterpreted as checksums of
a different line-ending representation.

References: [Node file I/O](https://nodejs.org/docs/latest-v24.x/api/fs.html),
[browser File API](https://developer.mozilla.org/en-US/docs/Web/API/File),
[optional file picker](https://developer.mozilla.org/en-US/docs/Web/API/Window/showSaveFilePicker).

No mathematical proof of universal non-repetition is inferred. The executable
negative controls establish the reported invariants only in their recorded
file/REST/OS test scope.
