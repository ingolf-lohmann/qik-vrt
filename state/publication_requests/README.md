# Manuskripteingang des Raumzeitterminal-Verlags

Implementation and workflow: `tools/qikvrt_publication_router.py` and
`.github/workflows/qikvrt_publication_router.yml`. Human requirements and
authorization: Ingolf Lohmann. Implementation and tests: OpenAI Codex.

This directory is a repository intake queue, not an anonymous web upload API.
It contains **no production request or author grant by default**. A manuscript
enters through the existing reviewed repository process. Do not move private
manuscripts here without their separate repository-publication permission.

Each JSON request uses the closed `qikvrt_editorial_publication_request_v1`
shape. Example placeholders below are documentation, not an executable grant:

```json
{
  "schema": "qikvrt_editorial_publication_request_v1",
  "publication_id": "the-exact-v2-proof-publication-id",
  "manifest_path": "release/the-candidate/publish-request.json",
  "manifest_sha256": "REPLACE_WITH_THE_EXACT_64_HEX_MANIFEST_SHA256",
  "manuscript_paths": ["docs/publications/the-candidate/ARTICLE_DE.md"],
  "website": {
    "origin": "https://raumzeitterminal.de",
    "path": "/publications/the-exact-v2-proof-publication-id/"
  }
}
```

The manifest must retain the generic publisher's Authority v2 schema. Manuscripts
must be both exact uploads and exact files returned to their author. Text input
is nonempty UTF-8 Markdown, plain text or TeX; PDF inspection uses the existing
hash-locked pypdf 6.15.0 runtime and requires readable, unencrypted text. This is
a structural/readability check, not a replacement for candidate/content/visual
review. Other formats are held without silently converting the candidate.

Read-only intake:

```sh
python3 -B tools/qikvrt_publication_router.py --json \
  --editorial-request state/publication_requests/the-request.json
```

Missing proof or individual author approval remains a HOLD. The active policy
supports its named natural-person principal, Ingolf Lohmann. Multiple creators
remain held until each creator has an independently validated approval protocol;
one principal's approval never supplies another author's consent. No historical
Goldkelch authorization is migrated, rebound or reused for a new candidate.

After an independently reviewed, protected Main merge, the existing workflow
checks committed inputs, the actual merged carrier's exact-head native Code
Owner approval, current rules and fresh Authority HEAD/TREE. It creates one
repository-wide create-only dispatch reservation and supplies the exact inputs
to **the same** `workflow_dispatch` publisher lane with `execute=true`. The
manual lane retains `execute=false` as its default. No new publisher, proxy
executor, approval impersonation, force update or Main push is introduced.

An existing reservation means NOOP and remote reconciliation, even after a
lost dispatch response. Its existence is not publication. Do not delete or
force-update reservation/authorization refs to make a retry appear new.
Credential delivery, Actions admission and Main adoption are separately required.

The existing generic publisher retains its v2 claim/proof/return/author gates,
single-use authorization lock and interrupted-effect recovery. Subsequent
anonymous verification independently downloads every exact public Zenodo file,
checks metadata and hashes, and captures the published version DOI. A reservation,
private draft, publisher return or green workflow is not public publication.

Verified original uploads, escaped metadata and DOI produce deterministic static
website assets. Public assets use content-addressed names; authorization controls
and credentials are excluded. Receipts, a safe docs projection, the existing
publication indexes and regenerated integrity files are persisted through a
create-only **draft review carrier** using the existing Git-Data REST transport.
The self-heal repair allowlist is not widened. Review, exact-head tests and
protected Main merge remain required. A lost ref/PR acknowledgement is read back
before continuing; no unchanged ambiguous POST is repeated.

Website deployment remains the existing
`qikvrt_effect_ack_http_terminal.yml` route. After its actual Main deployment
and product-HTTP jobs succeed, this router independently checks every published
website asset on **https://raumzeitterminal.de/**. A successful workflow with
skipped deployment jobs produces NOOP. Redirects, missing files, altered bytes
and incomplete asset inventories cannot pass. HTTP 525 is not delivery.

Native artifacts preserve admission, publication, DOI, persistence and public
delivery as separate states. Local workflow outputs live under the already
transient `.qikvrt/evidence/publication-request/`; they do not contaminate the
repository inventory. No timer, repeated failed publication or notification
loop is installed. Whole-system `EFFECT_ACK_DONE` is never inferred, including
while Mirror persistence or runtime/domain acceptance remains open.
