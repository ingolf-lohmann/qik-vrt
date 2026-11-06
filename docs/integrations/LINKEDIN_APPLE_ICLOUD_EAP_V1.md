<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# QIK-VRT: LinkedIn, Apple Account and iCloud Drive EAP integration candidate

**Status: DESIGN / FAIL-CLOSED PREFLIGHT ONLY. Not connected, not deployed, not admitted.**
**Authority baseline:** `37f8e4eb805292a31024a9e6213afc85d3a6a4a2`.
**Requested by:** Product Owner. No account password, OAuth token, signing key, browser cookie, private document path or Apple identity claim may be committed here.

## Three distinct principals / capabilities

| Boundary | Credential-bearing protocol | Smallest intended capability | Explicit exclusion |
| --- | --- | --- | --- |
| LinkedIn personal account | LinkedIn OAuth 2.0 / OpenID Connect; developer application with registered redirect and enabled products | `identity.read` (OIDC); `posts.write` only after separate consent and LinkedIn product entitlement | No private inbox, contacts extraction, broad member read, auto-publishing |
| Apple Account identity | Sign in with Apple, registered App/Services ID, domain and redirect, nonce/state and server-side signature/issuer/audience/expiry verification | `identity.signin` | **No iCloud Drive authorization**, no Apple Account password capture |
| iCloud Drive documents | OS-native document picker / File Provider and a *user-selected* security-scoped file or directory grant on an admitted iOS/macOS bridge | `files.read_selected` or separately consented `files.write_selected` | No full-Drive scraping, no inferred grant from Sign in with Apple, no credential reuse |

**Terminology:** "Apple Drive" is interpreted as **iCloud Drive**. This file does not claim an Apple-supported server-side API that grants broad Drive access from an Apple identity token.

Provider references:
- LinkedIn API access: https://learn.microsoft.com/en-us/linkedin/shared/authentication/getting-access
- Sign in with Apple: https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple
- Security-scoped directory access: https://developer.apple.com/documentation/uikit/providing-access-to-directories

## Prescribed native binding and EAP separation

1. Discover the original admitted QIK-VRT runtime and exact Authority HEAD/TREE. Preserve existing S1 credentials and source/host pins; no substitute executor, account, token, operator, CI bypass or new secret store.
2. Register provider-specific applications outside the repository. A user authenticates and consents at the provider/OS; verified credentials and refresh material remain in the original OS secret service, never in public CI, browser logs, task descriptions, Git or terminal EAP text.
3. Verify provider responses **server-side**: exact account subject; OAuth redirect/state/nonce and callback binding; cryptographic signature/audience/issuer/expiration when applicable; precise scopes; product entitlement; user-selected iCloud file bookmark/scope; revocation. Client-supplied booleans and this preflight are not sufficient.
4. Create an immutable intent and private evidence record bound to provider, capability, scope, original account subject digest, expiry, Authority HEAD/TREE and evidence hash. Use QIK-VRT's existing canonical EAP record / policy / predecessor binding.
5. Call the existing native prepare/commit only through an admitted endpoint. Verify independently the original provider or OS state (identity readback, authorized post receipt, selected-file digest and local-on-device reread), and the original EAP record/receipt. An HTTP 200, OAuth callback or platform transfer acknowledgement does not imply `EFFECT_ACK_DONE`.
6. Each binding is separately revocable; on revocation/expiry produce BLOCK/ISOLATE for subsequent effects, preserve nonsecret audit evidence and remove stored provider authorization material by the original secrets-management path.
7. Protected actions (public posting, data transfer, deletion, write-back) require exact-content, destination, actor and action approval; read-only discovery must precede any write.

The existing QIK-VRT reference machine (`src/qikvrt_effect_ack.py`, `runtime/self-host/EAP_HTTP.md`) decides *effect* release; the helper `tools/qikvrt_external_account_binding_preflight.py` only rejects structurally unsafe *proposals*. Its output cannot establish authentication, materialization, runtime readiness, EAP DONE or global DoD.

## Required acceptance evidence (all absent until separately verified)

- LinkedIn: OAuth consent receipt for QIK-VRT app; provider-subject readback with narrowly granted scopes, verified at provider; if posting, a separately authorized post and provider-side content/id readback.
- Apple Account: registered and valid Services ID with production redirect; token signature/issuer/audience/nonce/state validation; verified stable subject without publishing raw identity token.
- iCloud Drive: a native File Provider document-picker grant for an explicitly chosen file/folder on an admitted device; a metadata/digest readback on that exact object; a distinct readback if copy/sync/write is requested.
- Native EAP: admitted runtime, scoped exact request, independent receipt and observed external effect, unchanged Authority/governance requirements.

### Current infrastructure limitations

The public target `raumzeitterminal.de` last returned HTTP 525 and native `ready=false` with `ADMITTED_MESH_RUNTIME_ENDPOINT` open. This candidate does not remedy TLS/SSO/Originalhost admission or claim that LinkedIn/Apple users have logged in. CI and integration tests, provider sandbox/live readbacks, public deployment and an authorized EAP effect remain separate HOLD gates.
