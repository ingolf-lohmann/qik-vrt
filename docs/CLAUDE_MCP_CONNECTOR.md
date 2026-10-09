<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Claude Remote-MCP application path

This candidate extends `src/qikvrt_github_api_shim.py` with optional MCP. It
reuses the REST 2.3.0 architecture: `qikvrt_ingest` delegates to the existing
five-state handler; `qikvrt_readback` and an independent raw-byte GET reuse its
committed ingest-provenance validator. Existing REST paths, client options and
fixed Ruleset pins remain intact. No new dependencies or credential store.

Human scope/implementation authorization: Ingolf Lohmann, 2026-10-09.
Implementation and tests: OpenAI Codex, GPT-6 family; exact build unavailable.
Contribution terms, independent Code Owner review and exact candidate
acceptance remain incorporation gates.

## Reused subjects

| Component | Exact inspected source | Evidence scope |
| --- | --- | --- |
| REST client 2.3.0 | #508 HEAD `2e847ce4af60451bef11ec1b89540d56ee4e3ea6`, TREE `cde054f9aa56d98cb2389df910e0e9c19fc16deb` | Existing REST client, local handler and independent Ruleset readback |
| Direct Claude Messages provider | #506 HEAD `e31ca36c2e64d86a03696525a85865c7332a6377` | Separate provider/budget candidate; no Web-Connector effect |
| Published Mesh Monitor | Site version 17, HEAD `b2d6a25b00abe9b4b0e1301dc08b9504b3e61147`, TREE `1c81811b79160c5ffe9b42b0246eafeaa77004e4` | Fresh authenticated Work MCP observe/readback and independently verified stored bytes; Claude connection remains unverified |

Source locators:

- https://github.com/ingolf-lohmann/qik-vrt/pull/508
- https://github.com/ingolf-lohmann/qik-vrt/pull/506
- https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/mcp

The monitor supplies observation/D1-snapshot tools on a separate source tree.
The inspected repository tree contains no executable MCP adapter. Extending
the existing REST shim is therefore necessary to exercise this repository's
actual ingest/provenance/EFFECT_ACK contracts. Its existing monitor/OAuth path
is preserved; this candidate does not deploy to or change that Site.

## Private configuration and permissions

Use the established `make run-api` with its required private environment:
`QIKVRT_API_TOKEN`, future `QIKVRT_API_TOKEN_EXPIRES_UTC`, exact
`QIKVRT_ALLOWED_REPOSITORY`, `QIKVRT_API_PRINCIPAL`, and private durable
`QIKVRT_REPO_ROOT`. Add `QIKVRT_MCP_ENABLED=1` and the server-side allowlist
`QIKVRT_MCP_SCOPES='readback'`. Only explicitly authorized storage also gets
`ingest`. No scopes means no exposed tools. Replays recheck current auth,
expiry, permission, source/version and explicit acceptance.

The server remains loopback by default. Remote deployment must preserve its
non-loopback opt-in and TLS certificate/key requirements, specify exact
`QIKVRT_MCP_HOSTS` host:port values and configure `QIKVRT_MCP_ORIGINS` when
browser Origins are expected. Host, Origin, duplicate security headers, bearer
expiry and rate limits are checked before execution. OAuth is not implemented
here. Claude's documented private fixed request headers can send the existing
`Authorization: Bearer ...` credential. This is a shared service-principal
configuration, not authentication of a natural person. Retain source-system
permissions and the selected Claude connector's write approval requirements.
Never put credential values into source, logs or evidence.

## Operation and source contracts

Both tools require exact `repository`, `artifact_id`, stable `request_id`,
`expected_sha256`, `api_contract_version: '2.3.0'` and
`expected_implementation_sha256`. Ingest additionally requires canonical
`payload_b64` (at most 256 KiB decoded) and literal `effect_accepted: true`.
Unknown fields, bad hashes, changed versions/source and missing permission
fail before the handler. No automatic fallback or blind retry.

The implementation digest is SHA-256 over the UTF-8 compact sorted JSON map
from these paths to their SHA-256 file digests:

- `scripts/qikvrt_api_client.py`
- `src/qikvrt_api_handler.py`
- `src/qikvrt_effect_ack.py`
- `src/qikvrt_github_api_shim.py`

The service freezes this digest at startup and rejects later source drift.
Discovery reports it for inspection; obtain the expected digest independently
from accepted exact candidate bytes. Self-reported discovery alone is not
provenance authority. A changed candidate requires newly reviewed/bound bytes.

MCP `2025-11-25` uses initialization, JSON responses and no optional session/SSE
stream. Current `2026-07-28` uses discovery and per-request `_meta`; the
version/method/tool headers must match the body. This bounded two-tool adapter
does not claim optional resources, prompts, sampling or task support.

The original nested handler `EFFECT_ACK_DONE` remains limited to opaque-byte
storage. The MCP envelope stays `EFFECT_ACK_CONTINUE`, `ordinary_release=false`
and `claude_connector_execution_verified=false`. It cannot infer product
release, native Mesh execution, merge or Claude provenance from a client name.

Readback takes a shared lock on the writer's existing lock file, validates
payload, sidecar, provenance, committed transaction, replay receipt and
responsibility protocol, and returns only the same principal's artifact.
It creates no directory, audit event or receipt. Independently fetch:

`GET /repos/{owner}/{repo}/qikvrt/artifacts/{artifact_id}/readback`

with exact `request_id`, `expected_sha256`, `api_contract_version` and
`expected_implementation_sha256` query values, then recompute SHA-256. Both
routes share the local store trust boundary: the separation verifies response
serialization, not a second storage authority. Existing local checksums/audit
chains are not an external rewrite-proof anchor. Deployment must provide the
durable state volume and retention.

## Reproduction

Run `make mcp-conformance-test`, then `make test`. Tests exercise the real
adapter in a separate process with ephemeral fixture credentials. Coverage:
both protocol eras; scoped write plus raw GET; read-only non-mutation; restart
replay; eight concurrent identical calls; changed replay isolation; missing,
invalid and expired auth; missing read/write permission; repository/principal
confinement; wrong version/source/hash; header/body conflict; Host/Origin;
malformed/duplicate JSON; payload limit; and bytes/sidecar/provenance/receipt/
transaction tampering.

`scripts/qikvrt_mcp_probe.py` is a standard-library HTTP/JSON/SHA-256 client
with no server imports, no credential redirects and no retries. Default:

```sh
python3 -B scripts/qikvrt_mcp_probe.py \
  --base-url "$QIKVRT_VERIFIED_SERVICE_ORIGIN" \
  --repository ingolf-lohmann/qik-vrt \
  --artifact-id "$QIKVRT_BOUND_ARTIFACT_ID" \
  --request-id "$QIKVRT_BOUND_REQUEST_ID" \
  --expected-sha256 "$QIKVRT_EXPECTED_PAYLOAD_SHA256" \
  --expected-implementation-sha256 "$QIKVRT_EXPECTED_IMPLEMENTATION_SHA256"
```

Only add `--payload-file <approved-file> --accept-effect` for one explicitly
authorized ingest. The private environment supplies the token. Output excludes
credentials/payload bytes and always keeps Claude provenance unverified.
A passing generic client probe is conformance, not actual Claude execution.

## Remaining external boundary

This task exposes no callable authenticated Claude account operation. The
monitor still advertises its same version-17 endpoint. Its two earlier direct
authorization paths returned 401 and are not retried. A materially new
capability appeared during this task: its three actual MCP tools became
callable through the existing authorized Work connection. `qikvrt_observe`
returned a new persistent observation, then `qikvrt_readback` independently
read that exact ID and expected digest. Local Python SHA-256 verification of
the original returned UTF-8 bytes passed: 5,663 bytes, digest
`b666efd88ad324981ec672b9f5853e78f7f59ee3b0bb0ac5b0750e8fe748bb54`,
snapshot `569fb70c-9ba9-4d22-9bdf-314ca388db40`. The fresh evidence is in
`evidence/claude-mcp-connector/2026-10-09/`. This establishes the existing
monitor's Work MCP application scope, not Claude execution or this candidate's
remote deployment. A separate direct public REST fetch from this environment
failed with HTTP 403; no retry was issued and no origin-level cause inferred.

After governed incorporation, deploy these exact accepted bytes to an
authorized public HTTPS service with durable state and privately configured
expiring credentials. Add that verified endpoint to Claude, complete its
private authentication/header configuration, observe an actual `tools/call`
trace from the Claude connection and independently verify the returned bytes
over raw REST. Bind candidate HEAD/TREE, invocation, request and byte digests.
This closes `CLAUDE_WEB_CONNECTOR_EXECUTION` only when independently observed.
The existing monitor may be used after its own OAuth connection becomes
callable, under its separate observation/snapshot contract.

`raumzeitterminal.de` is separately required. Current provider readback reports
`pending`, `ssl_status=pending_validation`; another hostname proves no delivery
there. No deployment, domain, OAuth, credential, Ruleset or review setting is
changed by this candidate.

Primary specifications, retrieved 2026-10-09:

- https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
