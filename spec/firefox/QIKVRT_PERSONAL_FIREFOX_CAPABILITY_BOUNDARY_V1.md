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

No real IdP registration/binding, native protected-login-collection witness,
productive personal authentication or actual Firefox SSO run is attested by
these source components and simulations. Windows/macOS secret backends remain
unimplemented. Runtime credentials and browser authentication state are never
committed or placed in the transcript SQLite store. Source availability, test
doubles, RSA controls and restored transcripts do not establish external
authentication, provider retention readback or a Firefox product run.

## Local codec boundary restored from PR #437

The QIKVRT standpoint codec serializes, decodes and verifies bytes locally without an external model or account. `policy/QIKVRT_STANDPOINT_CODEX_V1.json` defines that scope. An optional external adapter retains the existing authenticated service and personal capability boundaries when enabled. Local codec success supplies no authentication, native personal admission or delivery evidence. Historical contribution disclosures remain unchanged.
