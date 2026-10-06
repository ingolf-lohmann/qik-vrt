<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# PR #452: publication post-effect receipt for submission 169906

This is an additive, immutable observation of the already posted individual
Internet-Draft `draft-lohmann-qikvrt-epistemic-status-00`. It is not a new
submission. The accepted candidate remains bound to HEAD
`08e3dee1cb7c45948197240aa02da43886041fcf`, TREE
`8f80b27e223b8929c4c99b9c75a7857220890abf`.

`POST_EFFECT_RECEIPT.json` binds submission `169906`, the raw public `posted`
response, completed UTC GET timestamps, exact public files and candidate
hashes. The public XML and TXT are byte-identical to the accepted files.
The server HTML is a separate xml2rfc 3.34.1 derivation, 82 bytes larger than
the accepted local xml2rfc 3.34.0 HTML. Its complete 28263-byte body is identical,
SHA-256 `5a2cb214e9d282d1b227065f059e7159658bc02d69612d522572680379e13191`.
`SERVER_HTML_DIFF.patch` records the exact generator/dependency and head-CSS
differences. Complete HTML byte identity is false.

All 26 files in the frozen v3 package, every earlier staging package, and their
historical Pending manifests remain unchanged. Historical fields describe
their observation time; the new receipt supplies the later publication state.
Publication is not RFC status, IETF consensus, WG adoption, PR merge, or a
repository-wide completion claim.

Public source locators:

- https://datatracker.ietf.org/api/submission/169906/status
- https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-epistemic-status/
- https://datatracker.ietf.org/doc/draft-lohmann-qikvrt-epistemic-status/00/
- https://www.ietf.org/archive/id/draft-lohmann-qikvrt-epistemic-status-00.xml
- https://www.ietf.org/archive/id/draft-lohmann-qikvrt-epistemic-status-00.txt
- https://www.ietf.org/archive/id/draft-lohmann-qikvrt-epistemic-status-00.html

Recheck the archived bytes from this directory with `sha256sum -c SHA256SUMS`.
From the repository root run:

```sh
python3 -B publication-staging/ietf-epistemic-status-00-reconciled-20261005-v3/verify_staging.py --negative-controls
python3 -B tools/qikvrt_integrity.py verify
```

The candidate validator's no-submission result applies to its historical
frozen preparation state. It does not override the successor `posted` receipt.
For a fresh observation, GET the public status endpoint and archive files;
compare exact bytes, not normalized or rendered text. Later observations or
corrections require a new successor path; do not regenerate this receipt in place.

Only public GET payloads and whitelisted public metadata are retained. No
private access/confirmation links, tokens, cookies, credentials or mail payloads
are stored. Archived IETF document bytes retain their original IETF Trust
notices; this receipt does not relicense them. No browser or new publisher
workflow is involved.
