<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Railway → Own-Host: offline, lossless storage contract v1

This extends `tools/qikvrt_self_host.py`. Its storage-only implementation module
is `tools/qikvrt_self_host_migration.py`; package verification, the recovered
native `Ledger` validator, the original `MonitorStore`, the launcher, supervisor
and independent monitor client remain the existing authorities. No alternative
ledger, provider adapter, transfer daemon or supervisor is introduced. The new
module reuses `state_file_digest`, `synced_private_file`, `sync_directory` and
`stopped_state` from the newer #457 same-binding snapshot/restore implementation
on `198ebe73d63b0411ded905ee34a8407dcfaec919`. Those existing operations intentionally
retain the same package/config binding and exclude browser state, operator
receipts and unknown paths. They cannot import the legacy Railway layout into a
new binding or prove SQLite/WAL and journal consistency. This module adds only
that missing full-inventory/rebinding boundary; same-binding operations remain
available and retain their existing scope. A same-binding snapshot omits the
migration completion/legacy archive; restoring it alone cannot start a config
that requires `migration_export_sha256`. Retain the complete validated migration
archive/receipts separately; no incomplete snapshot may bypass the startup guard.

The source carrier is the existing Railway Universal Terminal, volume
`qikvrt-state` (`0e2d37e2-ac58-4bdc-8238-ed81bf2aa187`), mounted at
`/var/lib/qikvrt`, domain `universal-terminal-production.up.railway.app` and
declared repository `Goldkelch/qik-vrt`. These locators select the intended
source; they do not authenticate a current deployment or attest current bytes.
Its historical inventory is in `runtime/capabilities/S1_OWN_HOST_ADMISSION_20261005.json`.
No live source state, volume, deployment, DNS, service or staged Railway change
is modified by this implementation or its tests.

## Capture boundary

Export accepts only a separate, owner-only **offline snapshot**, never a live
mount. An authorized operator must first independently verify the actual source
Head/Tree, volume identity, all writer cessation (terminal, SQLite, browser and
journal), durable acknowledgements at the cut and a complete stable offline
copy. Keep the exact capture evidence privately and obtain its SHA-256 through
an independent trusted channel. An ordinary directory, an inventory digest,
an unlocked file or the word `QUIESCED` is not a snapshot-consistency proof.
The pinned declaration records that external boundary; software checks cannot
authenticate its author's assertion. Once sealed, the source snapshot must be
protected from concurrent changes for the entire transfer. Current platform
credentials and state are never read or published here.

Copy `MIGRATION_SOURCE.example.json` outside the package, mode 0600. Fill every
null from the actual capture evidence. Layout entries are explicit paths relative
to the volume root. The historical deployment recipe defaults to
`state/temdd/events.sqlite3` and `state/live/QIKVRT_LIVE_EVENTS.jsonl`; the template
does **not** claim these are observed live paths. Correct the layout from the
complete snapshot. `monitor` and `binding` remain null only if absent; identify
existing `monitor/node.json`, `binding.json` and all producer lock files when
present. Existing `owner.lock` and, when bound, `node.lock` are mandatory.

Capture regular file bytes and empty directories, including unknown files,
private browser/profile storage, receipts and any SQLite sidecars. Do not copy
Unix sockets, symlinks, hardlinks, FIFOs, devices or set-ID modes into the offline
payload. Their presence makes export HOLD; the capture evidence must identify
the process-only socket/lock lifetime and any unsupported source entry for
separate handling. No acknowledged data may be omitted to pass the validator.
The native Unix ingress is recreated by the existing owner-only runtime after
host admission; a socket inode does not transfer a connection or lock.
Transport files, manifests and receipts are private, never repository/cache
payloads. Limits are 100,000 entries, 512 MiB per file and 4 GiB total; exceeding
them is a HOLD requiring a reviewed extension, never partial export.

```sh
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-inventory \
  --snapshot <absolute-private-offline-snapshot>
```

The inventory binds every relative path, entry type, mode, byte size and SHA-256.
Set `inventory_sha256` in the private declaration from this result, independently
compare the complete copy with the capture evidence, then pin the **exact**
declaration bytes. `capture_consistency_verified=false` remains explicit.

## Export and independent before/after verification

Use a freshly reviewed `1.2.0` or compatible successor export and independently
obtained package manifest pin. Migration code must itself match the sealed
package. All paths below are absolute, disjoint, non-symlinked paths.

```sh
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-verify-source \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --snapshot <offline-snapshot> --source-declaration <private-capture.json> \
  --source-declaration-sha256 <independent-capture-pin>
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-export \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --snapshot <offline-snapshot> --source-declaration <private-capture.json> \
  --source-declaration-sha256 <independent-capture-pin> \
  --output <new-private-export-directory>
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-verify-export \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --bundle <export-directory> --export-sha256 <independent-EXPORT.json-pin>
```

Export automatically runs a separate source-verifier process before copying
and a separate export-verifier process afterwards. It locks the declared existing
producer files without creating/truncating them and compares the source inventory
again after each phase. The output is create-only: `SOURCE.json` (exact declaration
bytes), `EXPORT.json` (sizes, digests, source pin, verifier pin and consistency
witnesses), and `payload/<exact-source-relative-path>`. Preserve the stdout result
and obtain the export pin independently before import. Matching process checks
are technical independence of fresh execution, not independent organizations,
human review or independent validation of the operator's capture assertion.

SQLite is inspected only in disposable copies. Every SQLite image and matching
WAL is checked; orphan sidecars, broken images, foreign-key failures, hot rollback
journals, incomplete WAL frames, checksum/salt mismatch, stale suffixes and
uncommitted WAL suffixes refuse export. The conservative WAL rule requires a
separately sealed clean source if SQLite could legitimately ignore an old or
uncommitted suffix; the migration never repairs the live source.
The WAL format/checksum source is the [SQLite file-format specification](https://www.sqlite.org/fileformat2.html#walformat);
the normalization uses SQLite's [Online Backup API](https://www.sqlite.org/backup.html)
on the disposable copy only. Original DB/WAL/SHM bytes remain in the payload. SQLite rebuilds its shared-memory
index in the disposable copy. Integrity and semantic checks bind the logical
SQLite dump, native epoch, row count, historical subjects, original body/native
digests, provenance and payload hashes through the recovered kernel validator.
Native triggers, views and unknown schema objects are refused.

The declared monitor journal is checked by the original `MonitorStore` in a
separate Node process: event order, payload digests, digest chain and confirmed
checkpoint. Replica monitor state needs separate admission and is refused by
this primary-carrier migration. A declared legacy JSONL journal is preserved
byte-exactly and checked for complete object records, UTF-8/JSON framing and
final newline. No unknown legacy hash-chain schema is invented; its capture
evidence remains the source authority. Snapshot and source binding changes
refuse transfer instead of copying a partial state.

## Dry-run, import and explicit rebinding

Prepare the normal private target config for the exact sealed package. Its
`state_dir` must name a **new, nonexistent** target directory on the later admitted
persistent mount. If a source monitor/binding exists, retain its node ID. The
private config must additionally contain `migration_export_sha256` equal to the
independently obtained export pin. This pins the planned migration before import
and prevents startup with empty or incompletely imported state, even if a failed
preparation has no surviving hold marker. Ordinary new-node configs omit it.
The existing launcher validates tokens/runtime requirements at host admission/start;
the migration does not provision or transfer provider credentials. Adapter must
be `none`; the native `temdd` or `firefox` profile remains explicit.

```sh
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-import \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --bundle <export-directory> --export-sha256 <independent-export-pin> \
  --config <private-target-config> --output <new-target-state-dir> --dry-run
```

Dry-run executes the independent export checks and validates the proposed binding
without creating the target, changing a source file, starting a runtime or
performing routing. Remove `--dry-run` to materialize the same create-only import.

| Target path relative to `state_dir` | Preserved/imported state |
| --- | --- |
| `legacy/railway/<source-relative-path>` | Every original file byte and empty directory; original modes retained in export metadata |
| `temdd/events.sqlite3` | SQLite Backup API image of all committed source rows/meta; logical digest independently compared |
| `temdd/owner.lock`, `node.lock` | Fresh empty kernel-lock files; source lock-file bytes retained in the legacy tree |
| `monitor/node.json` | Exact original journal/checkpoint bytes, when present; no fabricated prior journal |
| `binding.json` | New node/package/config/Head/Tree binding; original binding remains byte-exact in legacy |
| `receipts/railway-migration/EXPORT.json`, `SOURCE.json` | Exact export/capture manifests |
| `receipts/railway-migration/IMPORT.json` | Target paths, sizes, SHA-256, source export pin and explicit transformation boundaries |
| `receipts/railway-migration/VERIFIED.json` | Exact import-manifest digest, export pin and new binding; written only after independent verification |
| `.MIGRATION_HOLD.json` | Fail-closed preparation/failure/rollback guard |

Directories/files become owner-only 0700/0600 under the importing UID. This
ownership/access transformation is explicit; original permission metadata stays
in `EXPORT.json`. No timestamps, hardlink identity, process, socket connection,
ACL/xattr or OS-lock transfer is claimed. Unsupported source metadata requires
separate capture review. Historic SQLite event subjects/bodies/digests are never
rewritten to the new source pair. The original ledger continues filtering by the
new exact runtime subject; preserved historical rows do not become current
evidence or public event bodies. Browser/profile and all legacy paths are retained
privately as original data; this v1 contract does not silently select a historical
Firefox profile for the new authenticated session.

The target is held while copying, backing up and fsyncing. A separate verifier
process reads the complete export again, revalidates the private target config,
checks target inventory and legacy original bytes, compares all native rows/meta
and the monitor checkpoint, and pins the exact import manifest. The importer
reobserves under target producer locks before releasing the offline guard.
It first fsyncs the deterministic completion receipt. The launcher checks both
private receipt files and their digest/binding relation under `node.lock`;
missing, changed or unfinished receipts refuse any implicit fresh-state startup.
Only then is the result
`OFFLINE_IMPORT_VERIFIED_PENDING_HOST_ADMISSION_AND_EXTERNAL_READBACK`.

```sh
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-verify-import \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --bundle <export-directory> --export-sha256 <export-pin> \
  --config <private-target-config> --output <target-state-dir> \
  --import-sha256 <independent-IMPORT.json-pin>
```

This verifies the **offline pre-traffic baseline**. Keep stdout and pins in the
operator's private evidence channel; do not commit volume contents or secrets.
After normal runtime writes, inventory differs by design. The finite cutover
acceptance uses the original native readbacks and monitor client plus preserved
receipt/row/checkpoint comparison, rather than relabelling a changed baseline.

## Fail-closed rollback and later cutover

Any import failure leaves the new target quarantined with its diagnostic bytes.
The original launcher checks the guard before and after acquiring `node.lock`
and refuses startup; systemd recovery cannot delete it or rebind the volume.
No pre-existing target or source data is overwritten or removed. Source and
export paths cannot be parents/children of the target or sealed package.

```sh
python3 -B <exact-package>/tools/qikvrt_self_host.py migration-rollback \
  --root <exact-package> --manifest-sha256 <package-pin> \
  --bundle <export-directory> --export-sha256 <export-pin> \
  --config <private-target-config> --output <target-state-dir> \
  --import-sha256 <import-pin>
```

Rollback takes both target producer locks before quarantining. A live writer
refuses the operation; use the separately authorized existing supervisor to stop
it first. An unchanged candidate becomes
`CANDIDATE_QUARANTINED_SOURCE_UNTOUCHED`; drift, changed receipts or any write after
import becomes `HOLD_TARGET_DRIFT_RECONCILIATION_REQUIRED`. Rollback never deletes
target state, restarts the source, changes routing, resets acknowledgements or
promotes a stale snapshot. Once either side accepted new writes, a separately
verified reconciliation/new snapshot is mandatory before any return to that
side. Do not manually remove the guard to defeat this boundary.

The current task prepares and tests these commands; it performs no live capture,
export, import, writer freeze, Railway mutation or own-host deployment. When an
actual authorized own-host carrier exists, independently validate the capture
and transfer pins, execute this contract on the real source snapshot and target
mount, then use the existing **host admission** and supervisor plan. Validate the
real host/control plane/mount/HTTPS authority and do independent **external
readback**, including preserved acknowledged history, fresh owner Prepare/Commit,
the existing monitor journal and an actual supervisor restart. Keep a single
writer and the verified capture cut until that acceptance; enable the separately
authorized routing switch only after the target witness, never from a dry-run.
No URL or host is supplied here. Review governance stays a separate repository
condition; migration tests do not close `CODE_OWNER_RULE_NOT_ENFORCED`.

`make self-host-test` includes executable inventory/source/export/import/dry-run,
corruption, writer-lock, rebinding and rollback controls. The same existing native
TEMDD suite requires actual imported-volume Unix Prepare/Commit and crash restart
with nonempty historical and newly acknowledged rows. In the existing native
state-recovery CI artifact, `MIGRATION_NATIVE_OWNER_READBACK.json` binds the fresh
source Head/Tree, fixture/package/export/import/completion pins and the historical
and newly acknowledged row/journal hashes. It contains only synthetic test
observations, never a captured private volume. Existing technical lanes
run these gates on the fresh containing head. Local fixtures, separate verifier
processes and green CI establish their declared execution scope only:
`host_admission_verified=false`, `public_readback_verified=false`,
`deployment_performed=false`, `EFFECT_ACK_DONE=false`.
