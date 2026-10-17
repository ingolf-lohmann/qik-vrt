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

The normative QIKVRT process uses the locally executable standpoint codex in `policy/QIKVRT_STANDPOINT_CODEX_V1.json`. Its serialization, deserialization, identity validation and byte readback require no ChatGPT/OpenAI service or external model.

An explicitly enabled ChatGPT/OpenAI adapter is an optional authenticated runtime integration. The browser MAY connect to authorized OpenAI/ChatGPT services and locally installed/authorized connectors through explicit user authentication and consent. Adapter availability is not a QIKVRT core-process or release prerequisite. It MUST NOT claim or attempt to redistribute OpenAI's proprietary server-side ChatGPT runtime, model weights, hidden system configuration, credentials, or other non-redistributable service internals.

Published sources and historical ChatGPT contribution or interaction disclosures remain historical provenance; they are not rewritten or interpreted as runtime dependencies.

No credential or access token is committed to this repository. Runtime secrets MUST come from an OS/browser secret store or an explicit authenticated session.

## Mandatory release invariants

```text
STANDARD_TO_PERSONAL                         = ALLOW_WITH_FRESH_BINDING
PERSONAL_TO_STANDARD                         = DENY_BY_DEFAULT
PERSONAL_CAPABILITY_LEAK_TO_STANDARD         = DENY
PERSONAL_STATE_LEAK_TO_STANDARD              = DENY
PERSONAL_CREDENTIAL_LEAK_TO_REPOSITORY       = DENY
PERSONAL_EVIDENCE_TRANSFER_TO_STANDARD       = DENY
QIKVRT_CODEX_RUNTIME                         = LOCAL_DETERMINISTIC
CHATGPT_RUNTIME_INTEGRATION                  = OPTIONAL_AUTHENTICATED_ADAPTER
EXTERNAL_SERVICE_REQUIRED_FOR_CODEX          = FALSE
CHATGPT_PROPRIETARY_RUNTIME_REDISTRIBUTION   = DENY
PREDECESSOR_EVIDENCE_TRANSFER                = FALSE
```

A standard release is not accepted until a fresh build/readback demonstrates absence of personal payload. A Personal Edition release is not accepted until its exact subject proves the expected personal capability manifest and local codex roundtrip/readback. If an optional adapter is enabled, its authenticated runtime boundary must additionally be verified; the disabled adapter requires no external account or service readback.

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
