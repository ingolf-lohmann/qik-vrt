# GitHub API rate-limit boundary

The GitHub API quota is an external transport/execution-channel boundary. A quota failure cannot be promoted into a QIK-VRT candidate failure or authority decision.

Canonical law:

```
RATE_LIMIT != CANDIDATE_REJECTION
RATE_LIMIT != AUTHORITY_DECISION
TRANSPORT_ACK != EFFECT_ACK
```

Recovery requires an authorized channel, fresh MAIN and subject readback, exact identity binding, and resumption of the normal authority/effect chain.

The implementation priority is to remove avoidable API dependency: event payload/local Git first; shared immutable snapshots; webhooks over polling; authenticated conditional requests; consolidated GraphQL where equivalent; serialized observers; and strict `Retry-After` / `x-ratelimit-reset` backpressure.

A higher-capacity GitHub App installation token is a separate least-privilege execution channel, never a bypass of fail-closed semantics.
