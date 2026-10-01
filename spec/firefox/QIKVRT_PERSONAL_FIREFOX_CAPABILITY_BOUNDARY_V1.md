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

## Windows browser MVP acceptance (Owner scope, 2026-10-01)

The Product Owner clarification at
https://github.com/ingolf-lohmann/qik-vrt/pull/430#issuecomment-5935054969
requires actual execution on a current supported Windows system. FPGA board,
physical clock binding, bitstream, programmer readback and oscillator evidence
belong to separate hardware R&D. Their HOLDs do not block this browser path;
browser evidence does not prove those hardware effects.

The machine contract is `windows_acceptance` in the existing boundary policy.
Its first explicit client target is Windows 11 25H2, build 26200, Home/Pro or
Enterprise, AMD64 or ARM64. Evidence applies only to the executed architecture.
The conservative support window ends before the Home/Pro support end date;
other builds/editions need an updated primary-source-bound target contract.

`windows-2025` and `windows-2022` are Server compatibility targets, not client
acceptance substitutes. GitHub currently documents `windows-11-arm` as Windows
11 Enterprise ARM64. It is a candidate for the ARM64 client scope only: the
witness must independently read ProductType, edition, DisplayVersion, build,
UBR and native architecture at execution time. A label or image README is not
an execution receipt. Mismatch or an expired support window keeps product
target acceptance on HOLD, even when functional tests pass.

The existing Boundary workflow now runs the Windows witness on that client
runner with read-only repository permissions and an exact candidate checkout.
It binds HEAD/TREE, policy/XPI/binary hashes, browser version, runner image,
run/attempt/job, UTC observation and OS identity. It temporarily installs the
unchanged standard XPI in real Firefox, checks terminal content-script loading,
performs UI Prepare and Commit against the existing real loopback backend,
reads a fresh nonce-bound backend event, compares its input/record hashes and
HEAD/TREE, and verifies single-use replay refusal. Prepare must create no event.
The driver is fetched only from the pinned Mozilla release archive and checked
against its recorded SHA-256 before extraction and execution, including warm
cache re-extraction. The declared cache registry covers every new component.

Run on the declared Windows target with Firefox 156.0.1 and Python 3.13.15:

```powershell
python -B tools/qikvrt_tool_cache.py verify
python -B tools/qikvrt_firefox_windows_witness.py --output "$env:TEMP/qikvrt-windows-witness"
```

The default uses an actual headed Firefox session. A separately requested
`--headless` run is labeled as such. Temporary unsigned addon loading proves
test loading, not a signed persistent end-user installation. The standard
package still contains no personal payload. Its bounded local terminal event
has `external_effect=NONE`; it is not an authenticated Personal/OpenAI runtime,
repository effect or general product EFFECT_ACK.

`personal_release_effect_ack_done` remains false until the exact candidate also
has its personal capability manifest, authenticated runtime receipt, credential
non-persistence proof, release installation, public URL fresh readback and
responsible Owner acceptance. The witness never changes repository policy or
claims that release state. If no matching client execution is observed, the
remaining witness is this same exact candidate on supported Windows 11 client
with the declared architecture, loaded extension and fresh functional/effect
readback, followed by the separate authenticated Personal runtime acceptance.
