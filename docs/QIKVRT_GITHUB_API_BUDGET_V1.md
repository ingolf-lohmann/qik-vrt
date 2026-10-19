# GitHub API rate-limit boundary

The GitHub API quota is an external transport/execution-channel boundary. A quota failure cannot be promoted into a QIK-VRT candidate failure or authority decision.

Canonical law:

```
RATE_LIMIT != CANDIDATE_REJECTION
RATE_LIMIT != AUTHORITY_DECISION
TRANSPORT_ACK != EFFECT_ACK
```

Recovery requires an authorized channel, fresh MAIN and subject readback, exact identity binding, and resumption of the normal authority/effect chain.

The implementation priority is to remove avoidable API dependency: event payload/local Git first; shared immutable snapshots; webhooks over polling; authenticated conditional requests; consolidated REST reads within the existing REST_API_ONLY route; serialized observers; and strict `Retry-After` / `x-ratelimit-reset` backpressure.

A higher-capacity GitHub App installation token is a separate least-privilege execution channel, never a bypass of fail-closed semantics.

The current Owner route is `REST_API_ONLY`, bound by `policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json#/client_continuation/github_route`. Quota recovery preserves that route and the existing authenticated connection. It does not admit GraphQL, a browser-login fallback, token-scope expansion or synthetic triggers.
