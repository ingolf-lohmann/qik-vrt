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

The standard extension explicitly permits backend connections only to its declared loopback origins and the GitHub API in its extension-page CSP. The MV3 default `upgrade-insecure-requests` is omitted so the existing local HTTP Effect-ACK backend remains reachable; script and object sources remain self-only. The Windows witness observes Firefox's active host-permission origins in its temporary profile. Any test-only grant is limited to the already-declared loopback origin and does not prove production installation consent. Native browser architecture is read from the actual PE binary, independently of user-agent text.

Firefox host match patterns omit ports: Mozilla bug 2052000 (duplicate of 1362809) documents that port-qualified grants are reported active but do not match requests. The backend allowlist and `connect-src` still enforce port 8771. This corrects matching semantics; it does not permit connecting to arbitrary loopback services. Source: https://bugzilla.mozilla.org/show_bug.cgi?id=2052000

## Canonical public URL readback and Authority capability boundary

The canonical product URL remains `https://goldkelch.github.io/qik-vrt/`.
`docs/README_DEPLOY_GITHUB_PAGES_DE.md` declares Authority repository
`Goldkelch/qik-vrt`, branch `main`, folder `/docs`, entry `docs/index.html`.
The Personal repository contains that entry and its assets. Its Seed Dashboard
workflow builds and preserves local artifacts; it is not a Pages deployment.
The Personal candidate contains no `actions/deploy-pages` publishing workflow.
These facts do not establish the inaccessible Authority's actual configuration.

The existing Windows witness now observes the canonical URL before installing
the extension. It emits `PUBLIC_URL_READBACK.json`, the bounded exact HTTP body
and an uninjected Firefox screenshot. The receipt binds the current candidate
HEAD/TREE, run/attempt/job, observer/policy hashes and UTC observation times.
The anonymous GET requests cache revalidation, retains status/headers/body
SHA-256 even for HTTP 404, refuses redirects, and compares a successful response
with this candidate's exact `docs/index.html` bytes. The browser independently
records final URL, title, product DOM, visible text and navigation response
status when available. An injected terminal on a 404 page cannot satisfy this
gate. HTTP 200 with an error page, different bytes, a redirect or another host
also remains HOLD. A complete failed observation is evidence, not URL acceptance.

This readback proves only the declared root bytes and browser DOM. It does not
prove deployment of the whole candidate tree or authenticated Personal runtime,
and it never accepts a Personal release. The functional Windows witness can
still pass while its distinct `public_url_fresh_readback` remains false.

The exact external capability HOLD and diagnostic observations are persisted in
`state/work_units/QIKVRT_FIREFOX_WINDOWS_SCOPE_20261001.json` under
`public_pages_continuation`. Authenticated Authority repository read returned
404; the available GitHub connector rejects the Pages endpoint and exposes no
Pages mutation operation. Anonymous Pages API read also returned 404. None of
these responses alone proves that Pages is disabled, that its source is wrong,
or that the repository does not exist. No Authority settings were changed.

Continuation requires an authenticated Authority Pages reader/writer to inspect
the actual source and latest build/deployment against the existing `main:/docs`
site, repair the first established configuration/publishing defect, then rerun
the same candidate's public readback. No Mirror URL or other host substitutes
for the canonical product URL. Signed persistent installation, Personal
capability manifest and authenticated runtime readback remain separate gates.



## Seed-bound Linux ring witness

The existing Windows witness also accepts `--linux-ring --headless` on the
explicitly declared Ubuntu runner. Its real Firefox process loads the same
Standard extension, validates the full prepare record, commits one local
terminal event and independently reads the nonce, hashes, HEAD and TREE back.
The Linux bridge requires the unchanged canonical 400-byte signature copied
byte-for-byte from PR437 HEAD 6a1098699d096806958b9c3b50a97d205b8110e9,
blob 9b06a2b407fb99d99d2bda5a3decc80ab68a092b. Altered, absent or
wrong-length bytes refuse admission; the original signature is never rewritten.

The cause of the previous missing seed-to-effect evidence is the absence of
any seed check in the HTTP bridge. The successor makes the seed a local
admission prerequisite and binds it into hashed records, events and readback.
This proves that admission rule when its positive and negative controls run;
it does not prove that 400 bytes contain Linux or construct a whole operating
system. The host kernel, Firefox, driver and interpreter remain explicit
runner-image/toolcache dependencies, with native versions and binary digests.

The real HTTP controls execute fanout 1, 2, 4 and 8, an eight-client race on one
token, and client-discarded-response recovery through fresh readback. Only one
race effect may occur. A complete, hash-bound process-lifetime event snapshot
must retain every unique nonce exactly once. No network failure is injected.
The single actual Firefox roundtrip and the HTTP-client fanout are distinct
measurements. These finite measurements do not establish Firefox fanout,
unbounded scalability, restart persistence, live Authority/Mirror replication,
lossless node consolidation, or productive Linux reconstruction from a retained
full-node closure. Those acceptance scopes remain open. Native Main admission,
public product release and personal runtime acceptance remain separate gates.

Ingolf Lohmann supplied and authorized the ring scope; OpenAI Codex generalized
the existing witness, implemented the seed gate and executed the controls.
