<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Documentation contribution: OpenAI Codex. -->

# Canonical SQLite storage and derived QIKMESH1 transport

The sole persistent product representation for a Node and a Client is
SQLITE3_WITH_CARRIER_META_AND_EVENTS. The machine contract is
MESH_ACTIVATION.json#/storage_contract, enforced by S1 mesh-contract, pack
and verify. The native path is <private-state>/temdd/events.sqlite3;
the distribution name is repository.sqlite3. Both roles use the same
format, bytes and starter.

This successor reconciles PR #469 at
e19ddef7c10e9fe817b0cbb2c3518cbeea478718 and PR #470 at
f47f61c7fdeb35ee21c13d0462b763bf3377883c. The first preserves the native
carrier, ledger, preparations, replay and Owner REST. The second explicitly
lacks complete native-state migration acceptance. Choosing SQLite preserves
that state. Historical source-only QIKMESH1 exports cannot be promoted or
imported as native product stores.

## SQLite object and full-tree extension

Application ID is 0x51495654; user version is 1. The existing carrier, meta,
events, sqlite_sequence and native indexes retain their original semantics.
Original native Python/HTTP ledger sources are unchanged. Owner preparations,
event/native/body/payload digests, sequence numbers and epoch stay original.
Credentials and runtime bindings remain private and external to the object.

The optional repository_files(path, mode, git_blob_sha1, body) table contains
the complete original source tree. Paths are virtual UTF-8 keys, never
silently normalized, case-folded or extracted as host filenames. Original
regular, executable and symlink blob modes are preserved. Submodules are
refused. Export reads Git objects, including original bytes before checkout
EOL conversion. Verification hashes every blob and reconstructs the complete
Git tree without Git at runtime. Missing, extra, renamed, case-changed,
mode-changed and byte-changed entries fail closed.

Monoliths without this extension remain compatible. Adding it never projects
or replaces the ledger. A full-tree source distribution starts with the
original kernel's empty ledger; it is not migration of production effects.

## Stable snapshot and derived transport

Active SQLite may require WAL/SHM/journal transaction companions. Copying
only its live main file is forbidden. Existing checkpoint requires both
stopped-writer locks, exact private volume binding, wal_checkpoint(TRUNCATE),
DELETE journal mode, absence of companions, fsync and fresh byte readback.
Transport export reacquires both locks and holds them for the complete copy.

repository.qmesh contains exactly one entry, canonical/store.sqlite3, with
the entire unchanged SQLite image. Genesis qikvrt-sqlite-transport/v1 binds
canonical format, SHA-256, byte count, carrier manifest pin, ledger epoch and
source HEAD/TREE. The role is DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY.

QIKMESH1 framing retains eight-byte magic; big-endian metadata/payload
lengths; canonical UTF-8 JSON; content SHA-256; ordered sequence/identity,
previous-frame digest and domain-separated chained SHA-256. Chunks are
bounded to 1 MiB, metadata to 16 KiB and frames to 100,000. Portable file
limits remain explicit. Framing establishes consistency, not authorship
or native effect acceptance.

Append primitives construct exports and test format recovery. A bound
SQLite export refuses extra entries, revised SQLite entries and event
frames even with a coherent chain. It is not another runtime writer.

## Create-only import

monolith-transport-import requires independently obtained transport SHA-256,
canonical image SHA-256 and carrier manifest SHA-256. Its own metadata
cannot supply those independent pins. Import:

1. Checks a private regular source file and the independent transport pin.
2. Validates the entire chain and the single SQLite entry.
3. Extracts exact image bytes into a private temporary candidate.
4. Verifies stopped-checkpoint header, application/version, SQLite integrity,
   admitted schema and every independently pinned carrier byte.
5. Validates epoch, original event/native/payload/body digests and subject
   bindings, order and sqlite_sequence; verifies the optional full tree.
6. Checks source stability, atomically creates an absent destination,
   fsyncs its directory and independently reads back the exact bytes.

Wrong pins, corruption/truncation, symlinks, existing destinations, unsafe
schema, invalid ledger or replay sequence refuse installation. No existing
database is overwritten. No input/effect is executed or acknowledged.
All SQLite bytes remain identical, including pending preparations and
replay metadata. Resume requires separately admitted private configuration
and credentials. A #469 image without the extension can roundtrip. A
source-only #470 export cannot supply missing native state and is refused.
QIKMESH1 canonical promotion is forbidden.

## Terminal, ordinary file access and secure Origin

The native passive React Terminal, authenticated Owner REST and offline
restart remain available without Git/GitHub. Reading/opening the Terminal
does not commit input. The standalone export viewer selects ordinary files
or direct read handles, copies downloads and extracts SQLite. It cannot
create or edit a QIKMESH product repository. Adapter I/O, latency and size
remain measured; unknown device/capacity values remain unknown.

The existing listener offers authenticated read-only /api/mesh-file/status
and /api/mesh-file/bytes with explicit CORS. POST append is always refused;
preflight advertises GET/OPTIONS. Comparing exports issues no POST. Different
snapshots require new independent pins and import, not automatic promotion.
Existing separately authenticated Mesh proposal/cache/idle transfer remains.

Secure-Origin storage preserves the original SQLite image in one atomic
IndexedDB record with the pinned Worker/Service Worker and React assets.
It retains native epoch/events and byte-identical export and validates the
optional full-tree table. Native input keeps its original permission path.
HTTPS or permitted loopback bootstrap is required. Arbitrary HTTP, opaque
Origin and pure file start of persistent Origin runtime are refused.
A read-only local viewer does not grant Origin persistence or native execution.

## Evidence boundary

Fresh successor tests cover actual native REST, pending Prepare, committed
effect, SIGKILL, SQLite/QIKMESH/SQLite byte identity, all original meta/events
and sequence, restart and replay without duplicates. Negatives cover active
writer locks, WAL/companions, legacy exports, pins, truncation, corruption,
symlinks, existing targets, unsafe schema, ledger/replay tampering and
forbidden export writes. Full-tree controls verify bytes, modes and tree ID.

All checks and witnesses bind the successor HEAD/TREE. Predecessor checks,
reviews, approvals and receipts are never transferred. Actual public HTTPS,
Android/iOS, native multi-node replication/fencing, host power-loss and
general Mesh/EFFECT_ACK_DONE acceptance remain separate unverified obligations.
