# QIKVRT Self-Contained GitHub Repository with REST/TCP-IP API V1

Created: 2026-06-26 05:43:26 CEST

This repository is a self-contained QIK-VRT repository root. It includes:

```text
GitHub-compatible REST/TCP-IP API shim
GitHub Actions workflow_dispatch / repository_dispatch workflow
OpenAPI contract
Handler implementation
Client implementation
Unit and TCP/IP E2E tests
CI workflow
Metagrammar test inventory
Audit and uploadability gates
```

## Local TCP/IP API

```bash
make run-api
```

Health:

```bash
curl http://127.0.0.1:8766/health
```

## Tests

```bash
make test
```

### Canonical record profile

`policy/QIKVRT_CANONICAL_RECORD_V1.json` binds the existing Python Effect-ACK
serializer to recursive NFC for string values and object keys, strict UTF-8,
Unicode-code-point key ordering, compact JSON and significant array order.
Object keys must be strings; normalization collisions, lone surrogates and all
floating-point values fail closed. The existing tuple/Enum adapters use those
same rules. This integer-only profile is not RFC 8785/JCS.

`canonical_json` retains its string return type. `canonical_json_bytes` exposes
the exact UTF-8 bytes; `compute_record_hash` returns `sha256:<lowercase hex>`
over the complete supplied object. No signature, timestamp or hash field is
implicitly removed. The existing ResponsibilityProtocol hash uses its explicit
projection, which still excludes `created_utc` and `protocol_hash`.

The required `VERIFY_CANONICALIZATION` gate runs with `make canonicalization-test`
and is included in `make test`. Fixed byte/hash vectors, recursive Unicode,
key-order permutations, array order and invalid inputs are tested. These are
reference-implementation tests, not a general proof of semantic equivalence or
cross-language conformance. NFC does not make arbitrary logically equivalent
records identical. Existing native journals, wire hashes, knowledge receipts
and signed artifacts retain their own encoding contracts. This gate alone
establishes neither signature authenticity nor external Effect-Ack acceptance.

The existing scientific-bundle gate also reproduces the current runtime report
against `evidence/receipts/effect-ack-runtime-proof-20261022.json`. The published
bundle, historical report and release manifests remain unchanged. The successor
updates only the runtime byte count and source digest; its existing
`CONTINUE_PARTIAL_CORE_ONLY` boundary remains in force.

## GitHub REST API enablement

After upload to GitHub, the repository can be triggered through GitHub REST:

```text
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/dispatches
```

## Boundaries

```text
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
LIVE_GITHUB_ACTIONS_RUN = SUCCESS (run 29764193906)
GITHUB_PAGES_BUILD_AND_DEPLOY = SUCCESS (run 29764192834)
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_THIRD_PARTY_REPRODUCTION = OPEN
```

These hosted results establish the named GitHub effects only. They do not
establish non-bypassability in every integration, production hardening,
external adoption, or empirical validation of claims outside the executable
software boundary.
