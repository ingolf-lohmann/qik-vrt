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

The existing Boundary workflow runs the same Windows witness in two matrix
jobs: `windows-11-arm` requires ARM64 and `windows-2025` requires AMD64.
Both use CPython 3.13.15 with the explicitly selected native architecture,
read-only repository permissions and an exact candidate checkout. Separate
architecture-qualified output directories and artifacts prevent collisions;
matrix fail-fast is disabled so one architecture cannot cancel the other's
evidence. Neither job borrows predecessor or sibling evidence.

`windows_native_architecture_witness_test=PASS` requires the actual browser
effect, canonical seed, persistent State, forced termination/restart, every
retained event/record readback, both replay-409 probes and all negative startup
controls, plus matching native OS, interpreter, Firefox and Geckodriver
architectures. `windows_amd64_execution_observed` is true only after these
controls execute natively on AMD64. A green job alone cannot set that result.
Server execution remains `SERVER_COMPATIBILITY_ONLY`; its Windows 11 product
target and `windows_witness_test` remain HOLD. It does not establish a Windows
11 AMD64 client run. Both architectures retain overall release HOLD and
`personal_release_effect_ack_done=false`.

The shared witness binds HEAD/TREE, policy/XPI/binary hashes, browser version, runner image,
run/attempt/job, UTC observation and OS identity. It temporarily installs the
unchanged standard XPI in real Firefox, checks terminal content-script loading,
performs UI Prepare and Commit against the existing real loopback backend,
reads a fresh nonce-bound backend event, compares its input/record hashes and
HEAD/TREE, and verifies single-use replay refusal. Prepare must create no event.
Both Windows and Linux require the unchanged canonical 400-byte seed at
`canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin`, SHA-256
`27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792`.
The seed is a local admission prerequisite and is bound into the hashed
prepare/effect records and events; it does not build the host operating system.

The witness uses `<ephemeral-output>/terminal-state` across actual terminal
process lifetimes, with one snapshot at `.qikvrt/api/terminal.json`.
The existing State snapshot/validation/commit logic is shared. Windows replaces
only POSIX-specific I/O with native exclusive handles, held ancestor-directory
handles, reparse-point refusal, a protected owner/LocalSystem DACL, file fsync
and same-volume `MoveFileExW(REPLACE_EXISTING | WRITE_THROUGH)` replacement.
It never imports the POSIX-only API handler on Windows. Failure or ambiguity
poisons admission until validated restart; initialized state is never reset.

After the browser effect, the witness closes the browser-facing backend,
reopens its exact retained state in the actual CLI, adds a nonce-bound restart
probe, forcibly kills that process without a shutdown hook and starts a new
process. Windows records `WINDOWS_TERMINATE_PROCESS_WITHOUT_SHUTDOWN_HOOK`;
POSIX records `SIGKILL_WITHOUT_SHUTDOWN_HOOK`. Windows does not claim a POSIX
signal was delivered. All retained events and both referenced record classes
must remain byte-equivalent under canonical JSON, with unchanged on-disk
snapshot SHA-256. Both the browser token and restart token must receive HTTP
409 with no second event and no record/snapshot change.

Real CLI negative starts must refuse empty, truncated, missing-newline,
digest-corrupt, duplicate-key and seed-binding-mismatched state, plus altered,
truncated and absent seed bytes and an unseeded restart. Refusal must leave the
invalid bytes unchanged; restoring the valid snapshot must permit a fresh
readback. Only readbacks/digests enter workflow artifacts, never the secret
state file. Native regressions run before the Windows Firefox witness.
These tests cover bounded local process crashes, not power removal, network
loss, live-node replication or unbounded scalability. ARM64 and AMD64 require
their own executions, and emulated browser execution cannot grant a native
architecture PASS. `CODE_OWNER_RULE_NOT_ENFORCED` remains an independent
governance gate; technical results cannot weaken it.
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

## Windows 11 AMD64 carrier boundary and reproducible measurement

The fresh discovery receipt is the existing work unit's
`windows11_amd64_carrier_continuation`. Its input subject is PR438 HEAD
`2d1176f5790d7c345799f2232ac317a1d306d93a`, TREE
`e5bf9a11a2f58c5f09c8bbd29a689d4137fb174d`; that subject's Server AMD64 and
Windows 11 ARM64 executions remain historical evidence of those exact scopes.
They do not prove a successor or the Windows 11 AMD64 client.

The observed Main `6fb101b2815744b353f67e3fe88ba8458d3c36d5`, TREE
`0aa53d2bb775cbf9534d5a6b9a47e4b6f8637d75`, exposes 77 workflow blobs and
no Windows 11 AMD64 or self-hosted selector. The installed connector lists two
public QIK-VRT repositories and no private carrier. Its repository runner
inventory GET is rejected by the connector endpoint allowlist; no initial
workflow-dispatch tool is exposed. The generic Authority content route returns
404. These are access/exposure observations, not proof that no private host or
runner exists. The first task blocker is
`NATIVE_WINDOWS_11_AMD64_CARRIER_NOT_EXPOSED`.

GitHub's standard runner reference lists Windows 11 ARM64 and Server x64.
Its larger-runner reference documents a Base Windows 11 Desktop image and a
4-vCPU Windows size with 16 GB memory and 150 GB SSD. This is a documented
candidate, not an available, authorized or invoked carrier here. No runner
label is invented, no private host is registered, and no provisioning/billing
effect is authorized by this measurement contract. Sources:
https://docs.github.com/en/actions/reference/runners/github-hosted-runners
and https://docs.github.com/en/actions/reference/runners/larger-runners.

`windows_acceptance.windows11_amd64_client_measurement` preserves a runnable
contract using the existing observer and controls. Before execution, an actual
runner/private carrier must be freshly exposed with its identity, current
availability, repository scope, authorized operation and callable selector.
Reobserve the PR's current HEAD/TREE independently through REST and check out
those exact bytes. Do not fill an expected binding from the checkout itself.
The existing tool-cache contract and both native regression modules must pass
on that carrier with the declared native tools. Then use a new ephemeral output
directory in a headed native Windows session:

```powershell
$env:QIKVRT_EXPECTED_HEAD = '<fresh exact HEAD from independent REST readback>'
$env:QIKVRT_EXPECTED_TREE = '<fresh exact TREE from independent REST readback>'
python -B tools/qikvrt_tool_cache.py verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -B -m unittest -v tests.test_qikvrt_personal_firefox_capability_boundary tests.test_qikvrt_effect_ack_http_terminal
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -B tools/qikvrt_firefox_windows_witness.py --expected-architecture AMD64 --require-product-target --output '<new ephemeral output directory>'
exit $LASTEXITCODE
```

The strict option requires independent expected HEAD/TREE, clean source,
headed Windows and explicit architecture. Native ProductType/edition/build/
DisplayVersion/support-window mismatch returns exit 2 and `HOLD` before driver
provisioning, Firefox or any terminal effect. Architecture, subject and binary
mismatches fail closed. Server compatibility and ARM64 cannot satisfy this
path. Missing or mismatched tools require repair or a separately reviewed
compatible contract update, never downgrade or silent substitution.

The observer reuses the canonical 400-byte seed, persistent State, real
TerminateProcess and distinct restart, every retained event and both referenced
record classes, unchanged snapshot digest, browser-token and restart-token
HTTP 409 with zero second effects, and all ten actual negative CLI startups.
The required native OS, CPython 3.13.15, Firefox 156.0.1 and Geckodriver 0.37.1
must independently read AMD64 and bind their actual executable hashes.

`windows_11_amd64_client_execution_observed=true` can only follow all those
controls on the supported native AMD64 client with `windows_witness_test=PASS`.
Independent readback must bind numeric run/attempt/job/artifact, actual runner
and OS, observation within the job interval, archive digest, policy/observer/
backend/XPI/binary bytes, complete records and receipt/job-log agreement.
Local simulated admission tests, an exit code or a self-reported receipt alone
cannot establish execution. Upload only the existing allowlisted readbacks;
private State/token bytes stay off artifacts. `PREDECESSOR_EVIDENCE_TRANSFER=false`
and architecture transfer remains false. Personal release, authenticated
runtime, public URL, signed installation, governance and power-loss acceptance
keep their separate evidence boundaries.

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
race effect may occur. A complete, hash-bound fsynced event snapshot
must retain every unique nonce exactly once. No network failure is injected.
The single actual Firefox roundtrip and the HTTP-client fanout are distinct
measurements. The shared restart and invalid-state controls also run on Linux;
restart persistence requires their fresh actual readback on the current head.
These finite measurements do not establish Firefox fanout,
unbounded scalability, live Authority/Mirror replication,
lossless node consolidation, or productive Linux reconstruction from a retained
full-node closure. Those acceptance scopes remain open. Native Main admission,
public product release and personal runtime acceptance remain separate gates.

Ingolf Lohmann supplied and authorized the ring scope; OpenAI Codex generalized
the existing witness, implemented the seed gate and executed the controls.

The source-bound successor also separates repository-observation output from the
prepared/committed effect output. A late read-only Authority response must never
replace the displayed prepared record or change its effect state. The actual
content-script regression controls that ordering; both success and read errors
remain in the observation channel. Fresh native Firefox execution is required.


### Explicit Windows 11 AMD64 workflow attachment (2026-10-03)

Reuse `.github/workflows/qikvrt_personal_firefox_capability_boundary.yml`.
Ordinary pull-request runs retain the independent ARM64 and Server AMD64
lanes. Only an explicit `workflow_dispatch` with `windows11_amd64_runner`,
`expected_head` and `expected_tree` attaches an existing authorized dedicated
Windows 11 AMD64 label to the AMD64 lane. All three values are mandatory together;
the Linux boundary job refuses malformed labels, generic/known incompatible
labels, absent or substituted subjects before the optional Windows job is allocated.
The dispatch commit and checkout must match the independently read HEAD/TREE.
The AMD64 observer then uses `--expected-architecture AMD64 --require-product-target`
in headed mode; it refuses Server or unsupported client identity before browser
provisioning/effects. A custom label is routing data, never OS or authorization proof.

Before dispatch, independently verify the runner exists, is available, has a unique
label and access to this repository, and its use/billing is already authorized.
This change does not provision a runner, grant billing authority, or dispatch one.
The connector exposes neither runner inventory nor workflow dispatch; therefore
no complete inventory or global absence is claimed.

GitHub documents Base Windows 11 Desktop under Partner images for Windows x64,
with a minimum 4 vCPU / 16 GB RAM / 150 GB SSD configuration. Larger runners require
an organization or enterprise on GitHub Team or Enterprise Cloud. Fresh repository
metadata identifies `ingolf-lohmann` as User: eligibility and repository access for
that candidate are not established. Do not silently transfer the repository or
execute the witness elsewhere. An already authorized repository-level self-hosted
Windows 11 AMD64 desktop is an alternative. Use an isolated clean working directory,
a headed interactive desktop and dedicated unique label; do not expose a privileged
persistent host to automatic untrusted PR execution.

Actual client identity must satisfy the existing product policy: ProductType 1,
25H2 build 26200, supported Enterprise/Professional/Core edition and AMD64;
Python 3.13.15, Firefox 156.0.1 and Geckodriver 0.37.1 must be native AMD64 and
byte-bound. Image branding alone cannot establish this. The existing seed, State,
TerminateProcess/restart, event/record, two replay-409 and ten negative-startup
controls are reused unchanged. Fresh numeric job/artifact and independent byte
readback remain required. Architecture and predecessor evidence transfer remain
false; Personal release acceptance remains separate.

Provisioning sources:
- https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners/manage-larger-runners
- https://docs.github.com/en/actions/reference/runners/larger-runners
- https://docs.github.com/en/actions/how-tos/manage-runners/larger-runners/use-larger-runners

## Windows-11-AMD64 admission, 5 October 2026

The current machine contract under
`windows_acceptance.windows11_amd64_client_measurement` now separates
`runner_binding`, `current_runtime_candidate_input` and
`same_carrier_runtime_admission`. Discovery reads the exact Main, #438 and #461
trees and actual numeric Actions jobs. The runner-inventory endpoint is rejected
by the current connector allowlist. Inventory is incomplete; neither global
carrier absence nor an available dedicated client runner is proved.

`runner_binding.state=UNBOUND`: the dedicated existing selector, host/runner ID,
native client OS identity, availability, repository access and callable initial
execution operation have no observed value. These fields must be filled from
fresh authorized readbacks before execution. No label, host, paid resource or
dispatch is manufactured by this preparation. The existing three-input dispatch
contract remains the Firefox execution path. Independently bind the then-current
successor HEAD/TREE, rather than the discovery parent recorded in the work unit.

The separately pinned runtime input is [PR #461 at
1d28e59f99f0814a3410465a0712cb3ca0e899a9](https://github.com/ingolf-lohmann/qik-vrt/tree/1d28e59f99f0814a3410465a0712cb3ca0e899a9),
TREE `533c31c8e1765e3928767b4b290b8573ae8c7f9b`. Run `37304233153`,
job `111743929182`, artifact `11342338623` supplies a Windows Server build,
independently downloaded and byte-checked. The outer artifact SHA-256 is
`ea73fc2ea93e1a1ccdaf57051a24e57e17bdcae5ac6ffa3c24d3e18f49a81395`;
the inner `qikvrt-native.zip` SHA-256 is
`2fdc3e255481163a2e03b80ffa3071a2359a57a7289db18b196b6486c5866092`;
its manifest pin is
`d3bb1294fdf72bbca36f08a7b610e65c8d294f8681d7b66af6a4ba6bf88cf764`.
The machine contract additionally binds the actual AMD64 CLI/DLL bytes. These
are verified candidate inputs, not Windows-11 client-execution evidence.

The existing #438 workflow runs the Firefox witness; it does not execute the
separate native package. Its native-package execution operation therefore also
remains unbound. Once an authorized client carrier is available, execute the
existing #461 package operations on that same clean host, keeping both distinct
source identities. After independent archive and manifest verification, using
an already verified extraction of the pinned package, the existing operations
are:

```powershell
$pin = 'd3bb1294fdf72bbca36f08a7b610e65c8d294f8681d7b66af6a4ba6bf88cf764'
python -B "$package/source/tools/qikvrt_native_release.py" verify --package "$package" --manifest-sha256 $pin
& "$package/bin/qikvrt-c90.exe" evaluate 0000000700000003060201010100
python -B "$package/source/tools/qikvrt_native_release.py" sql --package "$package" --manifest-sha256 $pin
python -B "$package/source/tools/qikvrt_native_release.py" rebuild --package "$package" --manifest-sha256 $pin --output "$newOutput"
python -B "$package/source/tools/qikvrt_native_release.py" verify --package "$package" --manifest-sha256 $pin
```

Every operation must exit successfully; CLI and SQL must return
`000000040201`. Bind the actual host/OS and executing binary hashes, command
results, fresh rebuild manifest/binaries, and unchanged input bytes. Artifact
expiry requires exact-source reconstruction with fresh pins, not acceptance of
a different build. Preserve the native receipt alongside the same-carrier
Firefox source, run/attempt/job/artifact, real restart, full records, replay and
startup-refusal readbacks. Downloaded Server receipts cannot supply those client
observations.

`product_target_matches` means only that the preflight OS/build/edition matches.
`product_target_verified` stays false until the actual native Firefox effect and
all restart/record/replay/negative-start controls complete on that supported
client architecture; it stays false on execution failure. The AMD64 field
`windows_11_amd64_client_execution_observed` additionally requires native AMD64.
ARM64 verification remains confined to ARM64. The combined Firefox/runtime
admission and Personal release remain separate unverified scopes until their
own same-carrier and independent readbacks exist.
