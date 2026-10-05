# QIK-VRT Personal Firefox Capability Boundary

Status: normative candidate

## Product split

- `Goldkelch/qik-vrt` is the public standard product baseline.
- `ingolf-lohmann/qik-vrt` is the Ingolf Lohmann Personal Edition.
- Standard capabilities may flow into the Personal Edition only through an explicit, provenance-bound update.
- Personal capabilities, personal state, personal prompts/policies, personal psychological/cognitive adaptation, and personal agent configuration MUST NOT flow into the Goldkelch standard download by default.

## Firefox editions

### Standard Firefox edition

The Goldkelch Firefox distribution MUST be buildable and testable without any Ingolf-specific payload. It MUST NOT contain personal profiles, personal cognitive/psychological adaptation, personal development-agent configuration, personal credentials, tokens, account state, or personal evidence.

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

The implemented authentication is server-side OpenAI API bearer authentication
plus an ephemeral local client bearer. A signed-in ChatGPT/SSO bridge is not
implemented or established. Runtime credentials and browser authentication
state are never committed or placed in the SQLite store. Source availability,
test doubles, a local paired client and a restored transcript do not establish
external authentication, provider retention readback or a Firefox product run.
