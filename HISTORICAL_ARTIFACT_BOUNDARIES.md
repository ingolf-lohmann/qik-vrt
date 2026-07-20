# Historical artifact boundaries

**Classification date:** 2026-07-20

This repository contains a current reference runtime and a substantially
larger research, publication, and delivery archive. Historical presence is
preserved for provenance; it is not current execution authority and does not
turn an earlier status label into present certification.

Some retained records received explicit 2026-07-20 correction or
classification fields in the current publication. Their original bytes remain
recoverable at baseline commit
`8ae1884116221087bdcc75eed9905bb80bdd9e95`; the current copies must not be
misrepresented as byte-identical contemporaneous records. The later fields
mark present authority and historical scope rather than rewriting what the
baseline commit contained.

## Current operational authority

Current operational claims are governed by `README.md`, `STATUS.md`, the
active source and tests named there, the current OpenAPI contract, and the
canonical integrity trio:

- `REPOSITORY_FILE_MANIFEST.json`
- `SHA256SUMS.txt`
- `REPOSITORY_FILE_MANIFEST.json.sha256`

The canonical manifest records the bytes present in the repaired working
tree. It does not prove the truth of propositions contained in those bytes,
remote publication, field-wide adoption, legal compliance, or scientific
validation.

## Detached digests without local payloads

Fourteen files below `payload/monthly_content/` use a payload name ending in
`.sha256` while the referenced ZIP payload is not included in this checkout.
They are retained as historical digest records. Because the referenced bytes
are absent, they are **not locally verifiable sidecars** and must not be
reported as a present integrity PASS. Verification may resume only after an
independently sourced payload has been bound to the expected name and digest.

## Historical JSON encoding

Some archived JSON files begin with a UTF-8 byte-order mark. They are retained
byte-for-byte where provenance matters. A parser that intentionally consumes
such an archive must use an explicit BOM-aware decoding path and the schema
appropriate to that historical artifact. The current security-sensitive JSON
interfaces reject duplicate object keys and non-finite numbers and do not
silently import arbitrary archived JSON as runtime authority.

## Superseded reports and markers

Earlier build summaries, delivery markers, test inventories, cumulative
acceptance ledgers, `PASS`, `READY`, commercial-readiness, or certification
language describe their own historical context only. A current failing test,
integrity mismatch, missing external artifact, or unverified remote effect
cannot be overridden by one of those records.

## Historical executables and workflows

Archived scripts, Windows material, publication experiments, and Zenodo
material are not invoked by the current launcher or current read-only CI
workflows unless `README.md` and `STATUS.md` expressly name them. The current
reference publisher has no implemented Zenodo effect path and fails closed if
that compatibility flag is requested.

The retained QALL launchers `WINDOWS.bat`, `LINUX.sh`, and `MACOS.command`,
their `QALL.ini` configuration, the older `qikvrt.bat` and `qikvrt.ps1`
wrappers, and the runtime-download/resolver helpers remain historical
Apache-2.0 artifacts. They are not silently relicensed by the 2026-07-20
transition. The current launcher authority is `qikvrt.py` together with its
current `qikvrt.sh` and `qikvrt.cmd` wrappers and the active files named in
`README.md`; those QIK-VRT-controlled current files carry the prospective
`PolyForm-Noncommercial-1.0.0` notice.

## License-transition boundary

The public baseline, earlier releases, historical archives, and any file
validly received under Apache-2.0 keep that grant. Current QIK-VRT-controlled
repair-set software carrying the new notice uses
`PolyForm-Noncommercial-1.0.0`. This repository does not claim that changing a
later header withdraws an earlier perpetual Apache grant or relicenses a
third-party contribution. See `LICENSE_TRANSITION.md`.

## Reproducibility rule

Every new operational claim must identify the exact source snapshot, command,
inputs, environment boundary, result, and unresolved external dependency. A
local PASS is evidence for that bounded local run; it is not a remote or
universal DONE.
