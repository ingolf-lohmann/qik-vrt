<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# QIK-VRT Claude Remote-MCP readback profile V1

This candidate extends `src/qikvrt_github_api_shim.py` with opt-in `/mcp`.
`src/qikvrt_mcp_adapter.py` is a facade, not another server or state machine.
It reuses the existing API client's bounded no-redirect transport, the
existing handler's secure reads, fsynced atomic writes, process lock and audit
chain, and `src/qikvrt_effect_ack.py` for responsibility protocols.
The loopback Firefox bridge remains its existing separate demonstration.
PR #506 is the Messages provider, not this connector. PR #508 remains the
Ruleset/lifecycle integration; this main-based candidate does not copy its
governance changes or re-pin its writers.

## Callable read functions

| Tool | Scope | Input and verified result |
| --- | --- | --- |
| `qikvrt_repository_state` | `repository:read` | `request_id`; optional `expected_head`; fresh GitHub REST HEAD/TREE before and after the read |
| `qikvrt_capabilities` | `capability:read` | `request_id`, `expected_head`; complete tree plus verified Git blobs and SHA-256 for the existing OpenAPI, handler and EFFECT_ACK engine |
| `qikvrt_effect_ack_result` | `effect_ack:read` | `request_id`, `expected_head`, `target_request_id`, `expected_sha256`; exact bytes and validated responsibility protocol of an existing handler receipt |

The repository and ref are server configuration. Caller-selected URLs,
repositories, filesystem paths, writes, dispatches and effect grants are not
exposed. OpenAPI operation IDs are documentary discovery, not permission to
invoke those operations. All GitHub requests in this profile are GETs to
`https://api.github.com/repos/<configured-repository>/...`; redirects are
refused. Upstream credentials are never forwarded from an MCP bearer token.
Upstream GitHub permissions must independently allow every requested read.

An initial repository read may discover HEAD without a pre-known pin; the
other reads require the discovered exact HEAD. Both HEAD and TREE are checked
again before returning. Missing, malformed, truncated, stale or changed
evidence returns a tool error and never ordinary release. Source URLs are
commit-bound and blob bytes are recomputed independently against Git SHA-1
and SHA-256. Repository text is data, never executable authority.

Successful reads have an outer `EFFECT_ACK_CONTINUE`, `ordinary_release=false`
and `external_effect_verified=false`. An existing receipt can contain an
inner historical `EFFECT_ACK_DONE`; that does not authorize a new effect.
Legacy handler receipts lack a producer HEAD. This is explicitly returned as
`producer_head=null` / `NOT_RECORDED_BY_LEGACY_HANDLER`, never upgraded to
current-head or external-effect evidence. Verification covers record bytes,
the result hash, protocol integrity, configured repository and principal.
It does not re-execute or independently verify the original effect.

Each request ID has a durable, principal/repository/tool/arguments-bound
fingerprint using existing atomic persistence. An identical replay always
performs fresh observations; changed input under that ID is isolated. No
cached reply becomes current proof. Protective replay/audit writes are local
bookkeeping, not a GitHub mutation or an actuator effect.

## Protocol and configuration

Streamable HTTP supports JSON responses, modern MCP `2026-07-28` with
`server/discover` and required per-request metadata/header matching, and
legacy `2025-11-25`, `2025-06-18`, `2025-03-26` with `initialize`.
Standalone SSE, sessions, subscriptions, resources and prompts are not
offered. GET/DELETE return 405 after authentication; legacy accepted
notifications return 202 without a body. Modern success includes
`resultType=complete`; header mismatch uses HTTP 400 / error `-32020`.
This is a bounded tools profile, not certification of the entire MCP standard.

Keep the existing REST service configuration and add:

```text
QIKVRT_MCP_ENABLED=1
QIKVRT_MCP_TOKEN=<separate canonical b64url secret decoding to 32–128 bytes>
QIKVRT_MCP_TOKEN_EXPIRES_UTC=<future timezone-aware timestamp>
QIKVRT_MCP_PRINCIPAL=<authorized receipt owner / service principal>
QIKVRT_MCP_SCOPES=repository:read capability:read effect_ack:read
QIKVRT_MCP_REF=main
QIKVRT_MCP_ALLOWED_ORIGINS=https://claude.ai
QIKVRT_MCP_GITHUB_READ_TOKEN=<optional separately supplied GitHub read credential>
```

Use a supported secret-injection mechanism. Never put actual credentials in
Git, artifacts or chat. The dedicated MCP credential must differ from the
existing REST write key, attestation key and upstream GitHub credential. Every
request revalidates expiry and granted scopes. Discovery is filtered by scope.
Origin is checked when present; a cloud-to-server request may omit it. Shared
static authentication identifies the configured service principal, not the
individual Claude user. This profile implements no OAuth issuer, user login,
token exchange or refresh mechanism.

Start the existing service with `make run-api`. For non-loopback binding keep
its existing explicit opt-in and TLS certificate/key requirements. A public
HTTPS reverse proxy may forward only `/mcp` to the loopback service; preserve
Authorization and protocol headers and enforce request limits. Do not expose
the existing dispatch routes to a read-only connector. Keep `.qikvrt/api`
state persistent, with operator-controlled retention and restricted access.
The body limit is the existing 1 MiB; upstream responses remain bounded to
2 MiB, blobs and returned receipts to 1 MiB. There are no automatic retries.

## Exact remaining live prerequisites

1. Deploy this exact candidate on an existing authorized runtime, serve public
   HTTPS `/mcp` with valid TLS and Anthropic-cloud reachability, and bind the
   deployed source HEAD/TREE in a fresh delivery receipt. The current Monitor
   Site endpoint is a different implementation and cannot count as deployment
   of this Python candidate.
2. Supply the separate expiring read credential, principal and scopes through
   secure runtime configuration. The runtime must reach GitHub REST with any
   independently required upstream permission and mount its authorized API
   receipt store if receipt inspection is needed.
3. Connect an authorized Claude account. Anthropic's fixed Request headers
   authentication is beta and not available to every organization. If
   available, configure required `Authorization: Bearer <MCP credential>`
   exactly. If unavailable, an approved OAuth resource-server/issuer gateway
   with audience/scope validation and Claude-compatible discovery is required;
   this candidate does not implement or claim that gateway.
4. From Claude, record authenticated discovery and successful repository read,
   then a stale-HEAD or missing-grant refusal. Bind the client, server version,
   request IDs, response bytes/digests and independent GitHub readback. A
   Python or ChatGPT client cannot establish a Claude-account connection.

The existing Monitor plugin now has separately observed authenticated MCP
calls from the current Codex session, including a matching byte readback and
wrong-digest refusal. That closes only its declared client/operation scope.
Its snapshot preserves historical inaccessible repository observations and
UNKNOWN runtime states. It does not establish this candidate's deployment,
native Mesh execution, Claude authentication or `raumzeitterminal.de` delivery.

| Evidence class | Candidate acceptance boundary |
| --- | --- |
| Technical conformance | Executable bounded-profile and existing regression tests |
| Successful connection | Authenticated MCP discovery from the identified client |
| Executed operation | Successful tools/call and independently verified returned bytes |
| External effect | Exact-effect authorization, actual executor and independent post-effect evidence; none exposed here |

## Verification and primary sources

`make mcp-readback-test` is included in existing `make test`. Tests use an
independent HTTP wire client, explicit GitHub fixtures and temporary handler
state. They cover accepted reads, credential expiry/separation, scope and
origin refusal, stale/during-read HEAD drift, replay conflict, absent effect
grant, receipt provenance/tampering, bounded malformed requests, modern header
matching and legacy compatibility. Passing them is not a Claude live witness.

- https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- https://claude.com/docs/connectors/custom/add-unlisted
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

This is technical implementation/evidence documentation; no scientific
confirmation, publication, merge or global EFFECT_ACK_DONE is asserted.
