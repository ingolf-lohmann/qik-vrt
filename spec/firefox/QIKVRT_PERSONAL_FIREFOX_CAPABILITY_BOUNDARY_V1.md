# QIK-VRT Personal Firefox Capability Boundary

Status: normative candidate

## Product split

- `policy/CANONICAL_UPSTREAM_REMOTE_V1.json` selects `ingolf-lohmann/qik-vrt` as Authority for the standard product and `Goldkelch/qik-vrt` as its Mirror.
- Edition selection is separate from repository ownership. The opt-in Ingolf Lohmann Personal Edition is held under `personal/ingolf-lohmann/firefox-assistant` within the Authority repository.
- Standard capabilities may flow into the Personal Edition only through an explicit, provenance-bound update.
- Personal capabilities, personal state, personal prompts/policies, personal psychological/cognitive adaptation, and personal agent configuration MUST NOT flow into the standard download by default, whether it is supplied by Authority or Mirror.

## Firefox editions

### Standard Firefox edition

The Standard Firefox distribution MUST be buildable and testable without any personal-edition payload. The canonical Owner repository name and its public entrypoint addresses are ordinary source bindings, not personal features, profiles or account state. A Mirror page never changes the canonical observer source. The distribution MUST NOT contain personal profiles, personal cognitive/psychological adaptation, personal development-agent configuration, personal credentials, tokens, account state, or personal evidence.

### Ingolf Personal Firefox edition

The Personal Edition MAY expose the complete capability surface authorized by `ingolf-lohmann/qik-vrt`, layered over the standard product.

Its ChatGPT/OpenAI capability is an authenticated runtime integration. The browser MAY connect to authorized OpenAI/ChatGPT services and locally installed/authorized connectors through explicit user authentication and consent. It MUST NOT claim or attempt to redistribute OpenAI's proprietary server-side ChatGPT runtime, model weights, hidden system configuration, credentials, or other non-redistributable service internals.

No credential or access token is committed to this repository. Runtime secrets MUST come from an OS/browser secret store or an explicit authenticated session.

## Mandatory release invariants

```text
STANDARD_TO_PERSONAL                         = ALLOW_WITH_FRESH_BINDING
PERSONAL_TO_STANDARD                         = DENY_BY_DEFAULT
PERSONAL_CAPABILITY_LEAK_TO_STANDARD         = DENY
PERSONAL_STATE_LEAK_TO_STANDARD              = DENY
PERSONAL_CREDENTIAL_LEAK_TO_REPOSITORY       = DENY
PERSONAL_EVIDENCE_TRANSFER_TO_STANDARD       = DENY
CHATGPT_RUNTIME_INTEGRATION                  = AUTHENTICATED_EXTERNAL_SERVICE
CHATGPT_PROPRIETARY_RUNTIME_REDISTRIBUTION   = DENY
PREDECESSOR_EVIDENCE_TRANSFER                = FALSE
```

A standard release is not accepted until a fresh build/readback demonstrates absence of personal payload. A Personal Edition release is not accepted until its exact subject proves the expected personal capability manifest and authenticated runtime boundary.

## TEMDD

```text
SOURCE_REPOSITORY
→ FRESH_IDENTITY_BINDING
→ EDITION_SELECTION
→ CAPABILITY_MANIFEST
→ BUILD
→ TEST
→ OBSERVE
→ READBACK
→ ACCEPT
→ EFFECT_ACK_DONE
```

A successor mutation invalidates predecessor release evidence.

## Opt-in source adapter, 2026-10-05

The existing HTTP terminal accepts `--personal-state-dir` and an explicit
`--personal-model`. It loads `src/qikvrt_personal_assistant.py` only for that
opt-in path. `personal/ingolf-lohmann/firefox-assistant/CAPABILITIES.json`
declares the source capability and the shared `/personal/` Firefox surface.
The Standard extension's seven packaged files remain unchanged and do not
include this Personal payload.

Both ordinary conversation mode and QIK-VRT mode retain provider conversations,
full local transcripts, saved outputs and session restore. Only the observed,
source-bound checkpoint included on resume differs. Model output is never
independent acceptance. No harness oracle is loaded by the adapter.

The original adapter's authentication used a server-side OpenAI API bearer and
an ephemeral local client bearer. That development mode now requires the explicit
`--personal-legacy-memory-pairing` option. The default Personal CLI requires an
explicit private registered OIDC configuration and the opt-in OS-secret-store
path in `src/qikvrt_personal_auth.py`; Standard has no such dependency.

The new path implements public-client Authorization Code with PKCE S256,
form_post callback, one-time state/nonce, pinned discovery and RS256 validation
of issuer, Owner subject, client audience and token lifetime. Linux Secret
Service holds the model credential, renewable token pair and protected pending
journal. No file/database fallback is permitted. After process restart, a current
refresh is required before an existing local bearer is admitted. Local browser
bearers stay in page memory; no application cookies or browser storage are used.
Reopening the page requires the provider's existing SSO authorization flow.

Logout invalidates local admission before optional RFC7009 revocation. Missing
provider support and ambiguous external effects remain explicit and never
authorize unchanged retries. A revocation endpoint ACK does not attest global
provider logout or independent rejection of a reused token. Passkeys/WebAuthn
and biometric verification are delegated to the actually registered IdP/device;
no biometric templates or modality assertions are collected. Identity SSO does
not grant a model API entitlement or transfer a signed-in ChatGPT session.

The additive `microsoft_public_v2` profile requires a concrete tenant-GUID v2
issuer and its exact global-cloud endpoints, registered application GUID,
Owner pairwise subject, signed tenant/version checks and an explicit
`microsoft_replacement` refresh contract. Only this named profile handles the
documented omission of S256 and public-client `none` from Microsoft's discovery;
it still sends S256 and no client secret. Generic configurations keep their
exact protected binding and rotation/discovery requirements. Microsoft token
replacement MUST NOT be described as old-token invalidation or replay detection.
Only the latest token pair is retained in the protected entry. No Graph scopes
are added. Local token removal, optional browser provider sign-out and external
account/tenant token revocation remain distinct operations and evidence states.
Neither the selected provider nor its public consumer tenant identifies the
Owner's actual registered client or establishes an authenticated session.

## Independent entitlement and bounded consumption — Owner #580

The protected Personal factory requires a separate operator-supplied
`consumption` record in the existing OS Secret Service profile before any
provider call. SSO remains identity evidence only. The existing explicit legacy
memory-pairing development path is not productive consumption acceptance.

`src/qikvrt_personal_budget.py` reuses the original #506 SQLite budget ledger.
Its `ConsumptionGuard` separately checks provider access, seat assignment when
the selected offer requires it, concrete service rights, and a consumption
decision bound to the exact budget digest. A base-subscription entitlement is
required only when the selected offer actually declares that prerequisite.
Catalog lookup binds provider/product/SKU IDs, service, region, channel and
effective interval. Display names cannot grant access. Unknown or stale
evidence blocks the call. Each right retains its own kind, exact-subject digest,
documentary-source digest and observation/expiry interval.

The private record describes operator-confirmed documentary evidence; its
validation is not a live vendor entitlement or balance query. A market report,
an SSO token, the presence of an API key, or a provider's default limit cannot
create a consumption grant. No real new Microsoft product/SKU IDs are supplied
by this source change. Microsoft prerequisites must be read from the actual
applicable offer, not inferred from a marketing name or a future launch date.

The October 2026 Microsoft Partner Center announcement distinguishes the
01 December purchase change from licensed app/service capabilities. Its
initial default-billing rollout excludes France. Accordingly an operator
catalog can permit an explicitly configured service in France while excluding
France from `default_billing_regions`; it cannot infer that default activation
from the announcement. Source:
https://learn.microsoft.com/en-us/partner-center/announcements/2026-october

Budgets use integer micro-USD and explicit period/local/organization/workspace
limits. V1 token quotes remain readable. V2 requires `currency: USD` and also
supports a bounded unit quote with an explicit unit price and maximum units;
unknown currencies are denied. Quotes must bound all charges for the declared
request. Unit conversion is supplied by the pinned private quote, never a
hard-coded Copilot Credit price. The existing model adapter accepts token quotes
only: unit-metered Copilot accounting is not a new Microsoft execution adapter.
No Copilot API entitlement or endpoint is inferred from a subscription SKU.
V2 `billing_mode: bounded_usage` supports invoiced usage through a separately
authorized, expiring spend allowance. It does not pretend that an invoice
subscription has a prepaid balance. The allowance, its period and every limit
remain bound to the explicit consumption decision; no default allowance or
calendar rollover can create spend authority. V1 prepaid semantics are retained.

The original `BEGIN IMMEDIATE` reservation precedes external activity.
Independent connections share the same remaining pool and limits. A request ID
and its input/configuration digest bind the reservation. Completed repeats read
the cached result; unresolved outcomes hold the maximum reservation and freeze
new consumption pending reconciliation. Expired/changed grants are checked
again before dispatch. A changed protected operator record requires restart.
Current provider usage and exact resolved model must match the price contract
before settlement; unknown/malformed usage cannot release a hold.
The protected OpenAI path also calls the documented
`POST /responses/input_tokens` with the exact model, conversation, instructions
and input before generation. A count above the reserved input ceiling blocks
generation; output is bounded with `max_output_tokens`. Post-response input
usage must agree with that preflight count. The budget is rechecked after the
count, so a slow preflight cannot cross an expiry boundary into generation.
Other model transports remain unaccepted for protected consumption until their
own enforceable input-bound path is established. The existing legacy development
path is unchanged. API source:
https://developers.openai.com/api/docs/guides/token-counting

The existing terminal can provision a private, mode-0600 record outside any
repository with `--personal-store-consumption-config PATH`, together with the
existing Personal state/model/provider/auth-config arguments. Provisioning uses
the existing writer lock, validates reconciliation against the actual quiescent
budget revision, and independently reads back the protected store. No grant is
installed through browser input. `GET /personal/consumption` requires the
existing Personal authentication and exposes the bounded admission readback.
Tests use explicitly synthetic product IDs and provider doubles, real SQLite
connections/restarts and the actual authenticated HTTP handler.

Source tests, provisioning and a local HTTP readback do not establish productive
SSO, vendor rights, signed Firefox activation, host deployment or delivery at
`raumzeitterminal.de`. Those require their own exact-subject runtime receipts.

No real IdP registration/binding, native protected-login-collection witness,
productive personal authentication or actual Firefox SSO run is attested by
these source components and simulations. Windows/macOS secret backends remain
unimplemented. Runtime credentials and browser authentication state are never
committed or placed in the transcript SQLite store. Source availability, test
doubles, RSA controls and restored transcripts do not establish external
authentication, provider retention readback or a Firefox product run.
