# Identical external GET failures and controlled continuation

This is technical repository and HTTP-access evidence. It is not a scientific
article, a new Zenodo deposit, archive-damage evidence, or publication acceptance.

Original candidate: `8f9740018e1a864605a9fd0babff01454df4e1cc`,
TREE `097927c2fe98ee075d1034778f25ecc8638a7dae`.

The two complete decoded UTF-8 job logs are retained unchanged. Their lengths,
SHA-256 digests, source runs and precise HTTP-504 lines are bound in
`release/zenodo-corpus-proof-2026-07-28/ZENODO_EXTERNAL_GET_FAILURE_JOURNAL.json`.
Original source locators:

- https://github.com/ingolf-lohmann/qik-vrt/actions/runs/38226630154
- https://github.com/ingolf-lohmann/qik-vrt/actions/runs/38226629752
- https://zenodo.org/api/records/21244412

The existing archive probe uses the existing `client_causal_key`, private
atomic writer/lock, and pinned no-redirect Git-Data REST transport. The three
existing archive callers share `refs/tags/qikvrt-archive-get/<resource-digest>/`.
These refs contain technical intent/result journals, not publication releases.
Every sequence slot is create-only, reserved and independently read back before
one external GET. Results preserve the original intent and earlier results.
No DELETE, force update, scheduler, new workflow, or second archive reader is used.
The archive-only caller's existing repository token is granted `contents: write`
solely for these journal records; the other two callers already had that grant.

The request URL, Accept type and byte bound identify the resource. DOI, record
identity, file name and expected size/MD5/SHA-256 identify the material input.
Observation clocks, HEAD changes, workflow names and run IDs are provenance only.
Known unchanged failures perform zero Zenodo GETs and preserve NOOP/BLOCK. A
changed material input admits one attempt. Returning to an older failed input
does not erase its failure. An unresolved native reservation is read-only.
The 64-attempt and 128-KiB bounds fail closed without evicting original evidence.

A failure-bound independently observed HTTP response can also admit one attempt.
Supply a versioned evidence file through the existing workflow-dispatch input
`archive_retry_evidence_path`, the probe's `--retry-evidence-file`, or
`QIKVRT_ARCHIVE_RETRY_EVIDENCE_FILE`. Its schema is
`qikvrt_archive_get_retry_evidence_v1`; required fields are `kind` equal to
`EXTERNAL_HTTP_RESPONSE`, exact `url`, `input_key`, `previous_error_key`, an
actually different `http_status`, `body_sha256`, a copyable HTTPS `source`, and
`response_body_path`. The source response bytes must exist and match the digest.
Changing only a clock, source locator, failure-page body or repository HEAD is
insufficient. Reusing a consumed causal observation after another failure is
also insufficient. This byte binding does not independently authenticate who
made an externally supplied observation; it is an explicit evidence input.

Portable local invocations retain the same semantic state in the existing
`.qikvrt/runtime/` namespace. Hosted invocations must bind the shared native
journal and fail before GET if that binding is absent. Immutable native refs
provide cross-workflow retention independent of the diagnostic artifact's
30-day retention. Privileged native ref rewriting remains a separate repository
governance boundary; cooperating journal clients never perform it.

HTTP success records fetched bytes and their digest only. The existing record,
DOI, file-set, size, MD5, SHA-256, ZIP CRC and path/decompression checks still run.
Their successful transport cannot become scientific confirmation. Archive
recovery, proof-corpus publication, protected Main integration and public
product delivery retain their separate evidence obligations.

Regression path: `make evidence-contract-test`, included in existing `make test`.
The native Git-Data concurrency cases use a deterministic transport fixture;
they do not assert a live provider recovery or production journal mutation.
