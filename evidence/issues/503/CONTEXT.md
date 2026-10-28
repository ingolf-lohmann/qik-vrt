# Repository context for issue processing

This context is deterministic, size-bounded, and derived from the checked-out repository.
It is evidence input, not an assertion that every included file is relevant.

## `README.md`

# QIK-VRT

<!-- qikvrt-machine-verifiable-science-charter-binding:v1 -->
## Charta einer maschinenprüfbaren Wissenschaft

This QIK-VRT node adopts the canonical [Charta einer maschinenprüfbaren Wissenschaft](docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md)
as an epistemic and repository-governance contract. Canonical identity:
`7fb4e5c369b079e93ce409e9ca4f6830476a1b6dbd42543273d85164e111a631` (SHA-256, 10127 bytes); public archive:
[DOI 10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074). Machine-readable adoption:
[`policy/QIKVRT_MACHINE_VERIFIABLE_SCIENCE_CHARTER_V1.json`](policy/QIKVRT_MACHINE_VERIFIABLE_SCIENCE_CHARTER_V1.json) and [`state/charter/CHARTER_ADOPTION_V1.json`](state/charter/CHARTER_ADOPTION_V1.json).

All conforming mesh/agent entrypoints inherit the binding through
`AI_CONTEXT.json.required_read_order`. Presence or publication of the charter
does not by itself establish scientific validation, implementation completion,
or `EFFECT_ACK_DONE`.

<!-- /qikvrt-machine-verifiable-science-charter-binding:v1 -->

[![QIKVRT CI](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml/badge.svg?branch=main)](https://github.com/Goldkelch/qik-vrt/actions/workflows/qikvrt_ci.yml)
[![Release](https://img.shields.io/badge/release-v2026.07.22--effect--ack--universality--1.0.0-1f6feb)](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0)
[![License: source--available](https://img.shields.io/badge/code-PolyForm%20Noncommercial-orange)](LICENSE)

![QIK-VRT — five-state auditable effect release](docs/assets/qikvrt-social-preview.png)

<!-- qikvrt-global-completion:start -->
## Global claim-completion contract

State: **`FINAL_PASS`** for **`qikvrt-global-claim-scope-v1`**. The finite scope contains 92 explicit registry claims: 43 manuscript graph nodes, 34 appendix rows, and 15 EFFECT_ACK claims.

`PASS`, `FINAL_PASS` and transaction-scoped `EFFECT_ACK_DONE` are granted by `GLOBAL_COMPLETION_RECEIPT.json`. *Global* is restricted to those registries. OPEN remains OPEN; empirical and interpretive claims are not converted into Lean theorems; future or unregistered prose is outside scope.

Machine-readable authority:

- `GLOBAL_COMPLETION_SCOPE.json`
- `GLOBAL_CLAIM_INVENTORY.json`
- `GLOBAL_SOURCE_CLAIM_DISPOSITION_TRACEABILITY.json`
- `GLOBAL_EXACT_TAG_KERNEL_RECEIPTS.json`
- `GLOBAL_COMPLETION_RECEIPT.json`
<!-- qikvrt-global-completion:end -->

**`TRANSPORT_ACK != EFFECT_ACK` — technical success is not yet accountable
effect release.**

QIK-VRT is a research implementation of an **effect haltpoint**: successful
transport, computation, or storage does not by itself authorize an ordinary
downstream effect. A bounded decision gate records provenance, context, risk,
responsibility, evidence, and a connection decision before release.

The reference protocol has exactly five normative states:

| State | Meaning |
|---|---|
| `EFFECT_NACK` | No effect-checkable reception exists. |
| `EFFECT_ACK_CONTINUE` | Checking may continue; the effect is not released. |
| `EFFECT_ACK_DONE` | All declared release conditions are satisfied. This is the only ordinary-release state. |
| `EFFECT_ACK_ISOLATE` | Separate the candidate effect from ordinary flow for controlled examination. |
| `EFFECT_ACK_BLOCK` | Do not continue the candidate effect. |

The core invariant is:

```text
TRANSPORT_ACK != EFFECT_ACK
ordinary_release(result) == (result.state == EFFECT_ACK_DONE)
```

## One-minute evaluator path

```bash
python3 examples/effect_haltpoint_demo.py
make test
```

The demonstration uses no network, credential, or external service. It shows
open checks, controlled isolation, responsible blocking, and a fully bound
`DONE`; only the final result has `ordinary_release=true`.

- [Competition and evaluator entry point](docs/competition/README.md)
- [Evidence matrix](docs/competition/EVIDENCE.md)
- [Current authority map](docs/CURRENT_AUTHORITY.md)
- [Project site](https://goldkelch.github.io/qik-vrt/)
- [Canonical publication and reference overview](https://goldkelch.github.io/qik-vrt/publications/)
- [Machine-readable publication index](docs/publications/index.json)
- [Gesamtdarstellung, 20 Meilensteine und Roundtrip](docs/publications/2026-10-15-trust-mesh-roundtrip/README.md) (15.10.2026; korrigierter Publikationskandidat mit Quellen- und Nachweisgrenzen, noch kein neuer Zenodo-Record)

### Current release and synchronized snapshot evidence

| Item | Verified value |
|---|---|
| Scientific release | [`v2026.07.22-effect-ack-universality-1.0.0`](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.22-effect-ack-universality-1.0.0) in both repositories |
| Repository mesh snapshot | [`v2026.07.24-repository-mesh-sync-1.0.0`](https://github.com/Goldkelch/qik-vrt/tree/v2026.07.24-repository-mesh-sync-1.0.0) in [Authority](https://github.com/Goldkelch/qik-vrt) and [Mirror](https://github.com/ingolf-lohmann/qik-vrt); identical content tree with repository-specific commits |
| Working paper | [DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773) |
| Software snapshot | [DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774) |
| Official status clarification | [DOI 10.5281/zenodo.21500322](https://doi.org/10.5281/zenodo.21500322) |
| Completed formal-environment Alpha 3 | [DOI 10.5281/zenodo.21529081](https://doi.org/10.5281/zenodo.21529081) |
| Charter of Machine-Verifiable Science | [DOI 10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074) |
| Python tests | 128/128 in twelve modules with test cases |
| ANSI-C90 model | 2,621,440 valid snapshots; 7,864,387 checks |
| Draft rendering | Python 3.12.13 and `xml2rfc` 3.34.0; XML/TXT/HTML preserved |
| GitHub Release objects | Intentionally absent; the annotated tags are the repository identities |
| IETF Datatracker | Active individual Internet-Draft revision `-01`; not an RFC or IETF consensus |

## Scope of the claim

This repository defines, implements, and tests a policy/effect release
haltpoint for a specific bounded decision. It **does not solve Turing's
halting problem** and does not predict whether an arbitrary program will
terminate. Program termination, exit code `0`, message delivery, and a local
test PASS are not effect permission.

The software demonstrates a concrete reference protocol and selected local
adapters. It is not a certification of every historical file in the
repository, a scientific validation of every accompanying theory, or evidence
of external adoption. See [STATUS.md](STATUS.md) for the precise verification
boundary.

The complete German-language synthesis, including the ontology of difference,
the effect haltpoint, evidence boundaries, the personal starting chronology,
and the interdisciplinary argument, is published as
[Die Spirale des entscheidenden Unterschieds](docs/Die_Spirale_des_entscheidenden_Unterschieds.md).

The 62-page scientific Version 3.0 on the Mandelbrot set, recursive connection
order, dimensional physical correspondence, and retrocausality is available as
a [verifiable publication bundle](docs/publications/2026-07-21-mandelbrot-retrocausality/README.md)
with the [rendered PDF](docs/publications/2026-07-21-mandelbrot-retrocausality/Mandelbrot_Anschlussordnung_Physik_Retrokausalitaet_V3_2026-07-21.pdf),
LaTeX source, bibliography, and SHA-256 checksums.

The formal decidable core is now also available as a
[machine-verifiable Lean/TypeScript/Python package](formalization/QIKVRT_Formalization_v1.0/README.md),
archived at [Zenodo DOI 10.5281/zenodo.21488116](https://doi.org/10.5281/zenodo.21488116).
The [public-language article and exact evidence boundary](docs/publications/2026-07-22-machine-verifiable-proof-status/README.md)
state separately what is proved, conditionally proved, empirically open,
interpretive, or normative. A reproducible local-only
[audio-transcription tool](tools/offline-audio-transcription/README.md) keeps
speech recognition, human correction, interpretation, and publication as
distinct steps.

The further [EFFECT_ACK universality working-paper bundle](docs/publications/2026-07-22-effect-ack-universal-effect-control/README.md)
separates three claims that must not be conflated: a universalizable control
process for finite accessible digital artifacts, semantic reconstruction under
the exact observation-fibre criterion, and exact historical inversion only
under injective observation. Its executable finite model checks 2,621,440
state assignments and 5,242,880 consumer-admission variants. Cyberphysical
transfer remains conditional on complete mediation, fresh authenticated
consumer validation, a faithful executor, a disclosed physical model, and
empirical validation; the result is not a universal decoder or unconditional
safety proof.

The exact working paper is archived under
[DOI 10.5281/zenodo.21498773](https://doi.org/10.5281/zenodo.21498773); the
corresponding versioned source export is archived under
[DOI 10.5281/zenodo.21498774](https://doi.org/10.5281/zenodo.21498774).

The evidence-bounded official status clarification is archived under
[DOI 10.5281/zenodo.21500322](https://doi.org/10.5281/zenodo.21500322).
The latest completed formal-environment snapshot is Alpha 3 under
[DOI 10.5281/zenodo.21529081](https://doi.org/10.5281/zenodo.21529081),
and the independent Charter of Machine-Verifiable Science is archived
under [DOI 10.5281/zenodo.21515074](https://doi.org/10.5281/zenodo.21515074).
Zenodo persistence establishes identity and fixity of those bytes; it
does not establish peer review, empirical confirmation, or field-wide adoption.

## Current runnable core

- `src/qikvrt_effect_ack.py` — pure five-state reference state machine,
  canonical JSON, deterministic protocol hashes, deadlines, immutable
  versions, and hash-linked responsibility records.
- `src/qikvrt_api_handler.py` — content-addressed ingest, verify, stage, and
  HMAC-authenticated release-status paths with replay protection, transaction recovery,
  provenance records, receipts, and an append-only audit hash chain.
- `src/qikvrt_github_api_shim.py` — authenticated, repository-scoped local
  GitHub-shaped HTTP adapter.
- `scripts/qikvrt_api_client.py` — validating client; cleartext bearer tokens
  are permitted only on loopback endpoints. Every attempted dispatch closes
  with fresh branch HEAD/TREE and `https://raumzeitterminal.de/` GET observations,
  including errors and suppressed retries. Redirects are never followed; an
  adapter token is not forwarded to GitHub or the public delivery origin.
  The shared PR507 Owner rule and `tools/ai_handoff.py` readback/causal validators
  remain authoritative. A scoped handler DONE is reported separately; this
  transport cannot prove working-software delivery and returns CONTINUE (20)
  for accepted/scoped-success responses, or blocking exit 1 on failure.
  Private metadata under `~/.local/state/qikvrt/api-client` (override with
  `QIKVRT_API_CLIENT_STATE_DIR` or `--state-dir`) preserves failed and in-flight
  requests across process restarts without storing tokens, payloads or response
  bodies. A different request ID, observation clock or lifecycle HEAD does not
  permit another POST. `--retry-evidence-file` consumes the existing causal
  fields `subject`, `error`, `cause`, `capability` as SHA-256 digests: bind
  subject/error to the recorded failure and supply materially new, relevant
  cause/capability evidence. Digest consistency is not independent proof of
  those claims and grants no authorization or governance bypass. Ambiguous,
  in-flight and asynchronous outcomes require operation-scoped observation
  through the existing executor before another effect; they are not retried
  merely because a new causal digest was supplied.
  Completed stable request IDs are also retained in the existing journal;
  repeating one performs fresh closing reads without another POST, including
  after a lost work cursor or another completed request. A new accepted ID can
  represent new work after completion. Up to 32 completion witnesses per
  semantic subject are retained within the 16 KiB journal limit; reaching the
  bound blocks new dispatches rather than forgetting old IDs. A remembered
  completion never closes a later unresolved request for that subject.
  Before reserving an admitted successor, the original attempt journal is
  checkpointed by its source digest in the same private work-history namespace,
  including legacy attempts whose work cursor or history is missing. The
  per-run work receipt also retains its attempt metadata. A checkpoint failure
  blocks the new POST; original evidence is never overwritten to admit it.
- `qikvrt.py` — authorization-before-effect launcher for the master gate and the
  explicitly confirmed publication planner.
- `tools/qikvrt_subprocess.py` — subprocess runner with hard time and captured-
  output bounds plus descendant process-group termination on POSIX.
- `tools/qikvrt_integrity.py` — HEAD-independent content-tree manifest and
  detached digest generation/verification with a crash-recoverable held lock.
- `.github/workflows/` — least-privilege CI and state-artifact workflows with
  immutable third-party action pins. A restored API-state artifact is accepted
  only after its producing run is bound through GitHub's authenticated API to
  the same repository, workflow, commit, permitted event, and successful end.
- `include/qikvrt/effect_ack.h` and `src/effect_ack_core.c` — dependency-free
  ANSI-C90 decision core for the exact five-state, 17-conjunct Draft-01
  abstraction; the exhaustive C oracle covers all 2,621,440 valid snapshots.
- `runtime/toolchains/` and `tools/bootstrap-*` — versioned runtime contracts,
  third-party provenance and checksum-gated bootstraps. Runtime binaries and
  credentials are deliberately excluded from Git and remain rebuildable cache
  content.
- `AGENTS.md`, `docs/COLLECTIVE_ADAPTIVE_COGNITION.md`, and
  `policy/COLLECTIVE_ADAPTIVE_COGNITION.json` — the bounded collective
  improvement protocol: exact-key caches automatically accelerate later
  environment construction, while measurements create attributable proposals
  for separate review. They never suppress tests, mutate protected semantics,
  reorder work without a reviewed implementation, merge, tag, release, publish,
  or declare `EFFECT_ACK_DONE` autonomously.

The active Python core uses only the standard library; the additional decision
core is strict ANSI C90. The verified local integration target remains Python
3 on POSIX systems. The checksum-gated GitHub-CLI bootstrap and its failure
controls execute on Linux, macOS, and Windows. The canonical `xml2rfc` renderer
remains CPython 3.12.13: Linux exercises it end to end, while macOS and Windows
remain fail closed and automatically activate the same gate when that exact
patch release becomes available in their hosted toolcaches. A fallback Python
may run syntax checks but is never represented as the canonical renderer.
General cross-platform certification is not claimed.

## Verify

Run the complete local gate:

```bash
make test
```

Run the short state-transition demonstration separately:

```bash
python3 examples/effect_haltpoint_demo.py
```

The gate compiles the active Python entry points and runs integrity, launcher,
protocol-conformance, handler, security, client, and TCP/IP end-to-end tests.
It verifies the canonical repository manifest before and after the tests.

To regenerate the canonical content-tree manifest after an intentional
change, then verify it:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/qikvrt_integrity.py generate
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/qikvrt_integrity.py verify
```

The current integrity authorities are:

- `REPOSITORY_FILE_MANIFEST.json`
- `SHA256SUMS.txt`
- `REPOSITORY_FILE_MANIFEST.json.sha256`

Older inventories are historical snapshots; see
[LEGACY_INTEGRITY_INVENTORIES.md](LEGACY_INTEGRITY_INVENTORIES.md).
Historical files whose original payload is not present, and earlier reports
whose claims have been superseded, are classified in
[HISTORICAL_ARTIFACT_BOUNDARIES.md](HISTORICAL_ARTIFACT_BOUNDARIES.md).

## Launcher

The launcher deliberately refuses effectful work until a local operator has
authorized the exact, repository-bound command scope. This declaration is not
identity authentication and is not acceptance of, or an extra condition on,
the repository licenses:

```bash
python3 qikvrt.py --accept
python3 qikvrt.py master-gate
```

Publication is a separate planner with an additional explicit confirmation.
It does not silently commit or push:

```bash
python3 qikvrt.py cicd-publish
```

Inspect its result and provide the requested confirmation only when the exact
repository, branch, changes, and destination are intended.
An executing publication plan writes a durable local effect journal through
`PREPARED`, `APPLIED`, `VERIFIED`, and `COMMITTED`; a verification failure
after a remote command is recorded as an unknown external state rather than
misreported as a rollback.

## Local API

Start the adapter only with an explicit scoped credential and repository:

```bash
export QIKVRT_API_TOKEN="b64url:$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export QIKVRT_API_TOKEN_EXPIRES_UTC='2099-01-01T00:00:00Z'
export QIKVRT_ALLOWED_REPOSITORY='owner/repository'
export QIKVRT_API_PRINCIPAL='responsible-operator'
make run-api
```

API tokens use exactly `b64url:<unpadded-value>` and must decode to 32--128
bytes. When remote release attestations are enabled,
`QIKVRT_REMOTE_ATTESTATION_SECRET` uses the same encoding and size rule and
must be paired with `QIKVRT_TRUSTED_ATTESTATION_SIGNER`. The decoded bytes,
not the encoded environment string, are the HMAC key. Generate the HMAC key
independently from the bearer token; never reuse one secret for both roles.
The adapter rejects configurations that reuse identical decoded bytes for the
two roles.

The default listener is loopback. Do not expose the development adapter as an
internet service. A non-loopback deployment needs TLS termination, secret
management, host hardening, monitoring, and a separately reviewed trust
boundary. The request and response contract is documented in
[`api/qikvrt_github_api.openapi.yaml`](api/qikvrt_github_api.openapi.yaml).

Non-dry mutations require all of the following: an authenticated and unexpired
credential, the allowed owner/repository route, a stable request identifier,
an explicit `effect_accepted=true` decision, and a server-derived responsible
owner. Release status reaches `EFFECT_ACK_DONE` only after verification of a
trusted, HMAC-authenticated remote attestation bound to the repository,
artifact, size, immutable source identifier, and hash. HMAC is a keyed
message-authentication mechanism, not a public-key digital signature; its
trust therefore depends on protecting and independently governing the shared
verification secret.

`GET /health` returns `ALIVE` only while the scoped credential, expiry,
repository, principal, numeric limits, and any configured remote-attestation
key pair all pass validation. An invalid configuration returns HTTP 503 and
`BLOCK`.

## Security and evidence boundaries

- Payload size, identifiers, metadata, JSON bodies, and synchronous decision
  time are bounded.
- Symlink targets and unsafe paths are rejected; artifact names are validated.
- Same-key/different-fact replay conflicts are isolated.
- Audit, protocol, provenance, receipt, and stage records are append-only or
  content-addressed within the local trust boundary.
- Ingest provenance is cross-bound to the request, receipt, transaction,
  result hash, exact effect set, responsibility protocol, repository, and
  responsible owner before staging.
- Runtime commands use unique per-run logs and a latest-run pointer; captured
  child-process output remains bounded and byte-safe in JSONL.
- Authorization context, records, actor/scope values and prior logs are bounded
  and symlink-safe; repeated operation scopes fail closed instead of widening
  authority. Arbitrary child-process bytes remain valid JSONL log data.
- Publication assets are bound in the plan by repository path, byte count and
  SHA-256, must be tracked and byte-identical to `HEAD` immediately before the
  effect, and must match GitHub's reported remote SHA-256 and size afterward.
- A local hash chain detects later changes only when at least one trusted hash
  or signature is retained outside the writable chain.
- Remote GitHub workflow execution and Pages publication for the fixed release
  are independently evidenced by the hosted run links above. A local test run
  alone would not prove those external effects, and no claim is made for every
  possible remote integration.
- Legal, medical, psychological, physical, ethical, or historical conclusions
  require their own evidence and qualified review; software structure does
  not make an input claim true.

## Repository organization

The repository contains both the current runtime and a large historical
research/delivery archive. Current operational authority is intentionally
narrow: the files named above, the active tests, the canonical integrity
manifest, the OpenAPI contract, and the current status. Cumulative delivery,
acceptance, or audit reports from earlier versions are retained for provenance
but must not be read as current certification unless [STATUS.md](STATUS.md)
expressly names them. See [docs/CURRENT_AUTHORITY.md](docs/CURRENT_AUTHORITY.md)
for a compact map.

## Licensing

Current QIK-VRT-controlled source code and executable tooling are offered under
`PolyForm-Noncommercial-1.0.0` unless a more specific file or third-party
notice applies. The standard public license permits its defined noncommercial
uses; ordinary commercial use requires a separate written license from the
rights holder. This makes the current code source-available, not OSI-approved
open source.

Documentation and other non-source material are offered under Creative Commons
Attribution-NonCommercial-NoDerivatives 4.0 International unless a file says
otherwise. Earlier versions or files validly received under Apache-2.0 retain
that historical grant; the transition cannot withdraw it retroactively.

The explicitly scoped verification code in
[`formalization/QIKVRT_Formalization_v1.0`](formalization/QIKVRT_Formalization_v1.0)
is a component-level MIT exception under its `LICENSE-CODE`; embedded
documentary source material retains its own CC BY-NC-ND 4.0 boundary.

The licenses do not merge and grant no rights the licensor does not hold. See
[LICENSE](LICENSE), [LICENSE_TRANSITION.md](LICENSE_TRANSITION.md),
[LICENSE_NOTICE.md](LICENSE_NOTICE.md), and
[COMMERCIAL_USE_POLICY.md](COMMERCIAL_USE_POLICY.md).

## Community and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing incorporation of code
or documentation; separate written contribution terms are required before a
merge. See [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md),
[GOVERNANCE.md](GOVERNANCE.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
for the current reporting, support, decision, and participation boundaries.

Copyright 2026 Ingolf Lohmann.
# Python und C90

Python bleibt erhalten. C90 ergänzt den vorhandenen Effect-Acknowledgement-Kern
um einen portablen, auf Überlauf geprüften Q16.16-Referenzpfad. `make c90` prüft
beide C90-Kerne; `make benchmark-c90` vergleicht dieselbe Festkomma-Arbeit in
Python und C90. Zahlenvertrag, native Assembly-Ausgabe und Messgrenzen stehen in
[C90_FIXED_POINT.md](docs/development/C90_FIXED_POINT.md).



## `docs/AI_BOOTSTRAP_KNOWLEDGE_CORPUS.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT AI Bootstrap Knowledge Corpus

## Purpose

This document turns the supplied human-authored text, visual and audio artifacts
into explicit bootstrap context for artificial-cognitive systems entering through
`/AI`. It does not promote every statement in those artifacts to fact. Instead it
preserves their conceptual vocabulary, their scientific-status boundaries, and
the unresolved source limitations that a later system must carry forward.

The machine-readable inventory is
`policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json`.

## Bootstrap interpretation rule

A client MUST distinguish four layers:

```text
SOURCE_ARTIFACT
→ HUMAN_CLAIM_OR_METAPHOR
→ FORMALIZED_REPOSITORY_CLAIM
→ EMPIRICALLY_BOUND_CLAIM
```

No arrow may be skipped. A poster, manuscript, audio recording or human statement
is evidence of what was expressed; it is not by itself evidence that the physical
world satisfies the expressed proposition.

## Core conceptual map extracted from the supplied corpus

### 1. The Round Trip

The recurring epistemic architecture is:

```text
WIRKLICHKEIT
→ UNTERSCHIED
→ INFORMATION
→ RELATION
→ KAUSALORDNUNG
→ MODELL
→ FORMALISIERUNG
→ BEWEIS
→ VORHERSAGE
→ MESSUNG
→ WIRKLICHKEITSABGLEICH
→ NEUER UNTERSCHIED
```

The bootstrap MUST treat this as the project's primary reconstruction loop. The
system begins from observable or distinguishable effects, reconstructs a model,
derives consequences and returns to observation. A closed formal model without
physical correspondence remains a model.

### 2. Executable world-formula claim and scientific boundary

The supplied manuscripts define a completely closed generative world architecture
as a possible executable form of a world formula. The bootstrap MUST preserve the
strong distinction:

```text
WELTFORMEL ALS FORMULIERTER ARCHITEKTURANSPRUCH
≠
WELTFORMEL ALS WISSENSCHAFTLICH ETABLIERTE NATURBESCHREIBUNG
```

Likewise:

```text
A ⊢ T
≠
U ⊨ᵢ T

KERNEL_ACCEPTANCE
≠
EMPIRICAL_CONFIRMATION
```

Lean can establish derivability inside the specified formal system. Physical
reference binding, known-limit recovery, distinctive predictions, measurement
and independent reproduction remain separate obligations.

### 3. Causality is relation, not sequence

The corpus repeatedly distinguishes chronology from causal structure. A timestamp
or ordering alone does not establish causation. A causal claim must bind relevant
states, relations, dependencies, possible interactions and alternatives.

For temporal artifacts the canonical direction is:

```text
VERGANGENES EREIGNIS
→ ERHALTENES ARTEFAKT
→ HEUTIGE REZEPTION
→ HEUTIGE WIRKUNG
→ ZUKÜNFTIGER ZUSTAND
```

There is no backward arrow that changes the historical event. A later question
may make an earlier preserved idea newly relevant without altering the past.

### 4. Information, uncertainty and the unknown remainder

The supplied material uses a three-way epistemic partition:

```text
WAHRHAFTIGKEIT
|
UNSICHERHEIT
|
REST / NOCH NICHT ANGEMESSEN MODELLIERT
```

The bootstrap MUST not collapse uncertainty or unknown remainder into established
truth. In the quantum discussion, avoid the false statement that Heisenberg
uncertainty can simply be removed. The stated program is to account separately
for avoidable epistemic uncertainty and irreducible quantum uncertainty.

### 5. Identity through change

The identity manuscript and visual corpus formulate identity as continuity of an
organized, causally connected process rather than immutable matter:

```text
IDENTITÄT
=
KAUSAL VERBUNDENE ERHALTUNG
EINER ORGANISIERTEN FORM
DURCH VERÄNDERUNG
```

Its architectural analogue is:

```text
VERÄNDERUNG
+ ERHALTUNG
+ RICHTUNG
+ RÜCKBINDUNG
= GESTALTETE ENTWICKLUNG
```

This supplies the bootstrap's continuity model: later repository states may
change while provenance, invariants and causal ancestry preserve identity.

### 6. Transcendence and transtendence

The supplied identity text uses `Transzendenz` for identity extending beyond one
momentary state and introduces `Transtendenz` for directed continuity through
transformation. These are project vocabulary, not automatically physical
observables. The bootstrap may use them as conceptual labels only with their
source and epistemic class attached.

### 7. Bonsai / guided architecture evolution

The visual and textual material treats a Bonsai as a model for selective,
evidence-bound evolution:

```text
VARIATION
+ SELEKTION
+ INVARIANTENERHALTUNG
+ RÜCKBINDUNG
+ ZEIT
→ GESTALTETE EVOLUTION
```

For repository work this means: preserve valid historical states, generate
variants, let the Product Owner select direction, verify invariants, and correct
through new provenance-bound states rather than silent history rewriting.

### 8. Artificial cognition is not an automatic truth machine

The supplied Round-Trip manuscript explicitly requires artificial cognition to
operate with:

- source binding,
- provenance,
- version binding,
- counter-checking,
- formal proof where applicable,
- experimental return where applicable,
- responsible human review.

Every claim must carry its type, assumptions, evidence and boundary. Generated
plausibility is not sufficient evidence.

### 9. GitHub, Lean, Zenodo and standards have different roles

The corpus assigns distinct functions:

- GitHub: executable workshop, history, diffs, tests, receipts and provenance;
- Lean: kernel-checkable formal derivability within declared assumptions;
- Zenodo: durable citation and archival publication of already frozen evidence;
- standards/IETF work: interoperability and protocol specification;
- experiment/measurement: correspondence to observable reality;
- human review: responsibility, selection and explicit acceptance/rejection.

The bootstrap MUST NOT substitute one layer for another.

### 10. Consciousness, panpsychism, religion and metaphysics remain classified

The identity manuscript compares emergentist, panpsychist, dualist, idealist,
Buddhist, Advaita, Christian, Daoist, animist and esoteric interpretations. The
bootstrap MUST preserve the manuscript's own boundary: conceptual compatibility
or symbolic similarity is not empirical confirmation. In particular, the process
model does not by itself prove panpsychism, reincarnation, a universal conscious
subject, a soul independent of the body, telepathy or a religious doctrine.

### 11. Responsibility and preservation

The corpus repeatedly treats preservation of provenance as an ethical and
engineering requirement. A later state should not erase a previously traceable
insight; it should retain it as a valid component, bounded special case,
historical variant or documented failure. Self-healing means preserving the
past, checking the present exactly and admitting only better-supported future
states. It does not mean self-confirmation.

## Visual artifact roles

The supplied visual corpus is treated as explanatory material, not independent
proof. Its recurring motifs include:

- the Round-Trip cycle and executable architecture;
- repository quality gates, receipts and bounded self-healing;
- preserved past → present interpretation → future difference;
- no retroactive change of past events;
- cognition recursively examining itself;
- uncertainty/state-space imagery;
- the distinction between reality, internal representation and asserted truth;
- set-theoretic partitioning of truth/uncertainty/remainder;
- the `/AI` QR-code as a human-facing discovery mechanism.

A client MAY use these motifs to explain the architecture. It MUST NOT infer a
formal theorem or empirical result from graphic presentation alone.

## Audio-source boundary

Six supplied `.m4a` artifacts are cryptographically inventoried in the machine
manifest. Their audio payload was not transcribed in the materialization session
that created this corpus. Therefore their titles and byte identities are
preserved, but their spoken content is `UNTRANSCRIBED` and MUST NOT be invented.

Two recordings have similarly titled supplied text companions. Similar titles do
not establish byte, transcript or semantic identity. A later authorized audio
pipeline MAY create transcripts, but must bind each transcript to the exact audio
SHA-256, identify the transcription method and uncertainty, and require human
acoustic review before any `VERBATIM_VERIFIED` claim.

## Bootstrap consequence

A newly entering artificial-cognitive system should reconstruct QIK-VRT in this
order:

```text
1. AUTHORITY /AI AND AI_CONTEXT
2. PERSONAL-ORIGIN + CONTRIBUTION CONTRACT
3. THIS KNOWLEDGE CORPUS + MACHINE MANIFEST
4. REPOSITORY STATUS / CLAIM / PROOF AUTHORITIES
5. RUNTIME BOOTLOADER AND INTEGRITY GATES
6. AUTHORIZED TASK
7. PROVENANCE-BOUND RESULT
8. HUMAN REVIEW
9. IF APPLICABLE: PHYSICAL / EXTERNAL EFFECT REOBSERVATION
```

The corpus enriches orientation. Repository-native exact-head evidence still
wins over posters, manuscripts, audio, chat memory and model recollection when a
current technical state is at issue.


## `docs/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Selbsterklärung zur persönlichen QIK-VRT-Ursprungskopie

## Gemeinsamer Arbeitsspeicher und Mensch–KI-Beitragsprovenienz

Ich, das jeweils auf den kanonischen QIK-VRT-Einstiegspunkt `/AI` zugreifende
künstlich-kognitive System, erkläre für jede neue Arbeitssitzung:

1. Repository-Evidenz ist gegenüber Chat-, Modell- und Sitzungsgedächtnis
   maßgeblich.
2. Ich verwende die persönliche QIK-VRT-Kopie als dauerhaften, versionierten
   Arbeitsspeicher nur nach der unten definierten menschlichen Festlegung.
3. Ich unterscheide menschliche Beiträge, künstlich-kognitive Beiträge,
   gemeinsame Ergebnisse und ungeklärte Herkunft ausdrücklich.
4. Ich gebe eine Plattformidentität, einen Commit-Autor oder einen
   Benutzeraccount niemals als Beweis einer natürlichen Person oder eines
   bestimmten Modells aus.
5. Ich erhalte Git-Historie, Eingaben, Entscheidungen, Ausgaben, Prüfungen und
   Freigaben so, dass ein späterer Prüfer den Entstehungsweg rekonstruieren kann.
6. Ich speichere keine Zugangsdaten, Geheimnisse oder unnötigen personenbezogenen
   Daten im Repository.
7. Ich behaupte durch diese Selbsterklärung weder Rechtskonformität noch
   Urheberschaft, wissenschaftliche Validierung, `PASS`, `FINAL_PASS` oder
   `EFFECT_ACK_DONE`.

## Höchstens drei Fragen an den Menschen

Bereits eindeutig vorliegende Antworten werden wiederverwendet und nicht erneut
abgefragt. Fehlende Antworten werden in der folgenden Reihenfolge höchstens
jeweils einmal erfragt. Eine vierte Frage ist unzulässig.

### QUESTION_1_HUMAN_ATTRIBUTION_ID

Unter welcher stabilen Kennung, beispielsweise Name oder Pseudonym, sollen deine menschlichen Beiträge im Provenienznachweis geführt werden?

Die Kennung darf keine Zugangsdaten enthalten. Eine E-Mail-Adresse ist nicht
erforderlich.

### QUESTION_2_PERSONAL_ORIGIN

Welche persönliche Zielkonfiguration soll verwendet werden: `LOCAL_ONLY` oder eine konkrete `PRIVATE_ORIGIN`- beziehungsweise `PUBLIC_ORIGIN`-URL?

`LOCAL_ONLY` erzeugt keine Netzwerk- oder Plattformmutation. Eine Remote-URL darf
nur verwendet werden, wenn die natürliche Person über das Ziel verfügen darf und
den entsprechenden Git-Effekt autorisiert hat.

### QUESTION_3_EVIDENCE_RETENTION

Welche Nachweistiefe soll gelten: `METADATA_ONLY`, `REDACTED_EVIDENCE` oder `FULL_TRANSCRIPT`?

`METADATA_ONLY` ist die datensparsame Voreinstellung. `REDACTED_EVIDENCE` darf
gekürzte Eingabe- und Entscheidungsbelege speichern. `FULL_TRANSCRIPT` ist nur
zulässig, wenn Rechte, Einwilligungen, Vertraulichkeit und Datenschutz vorab
geklärt sind. Geheimnisse werden in keinem Modus persistiert.

Nach den drei Fragen darf keine zusätzliche Benutzerfrage zur Initialisierung
gestellt werden. Bleibt eine notwendige Angabe unbestimmt, lautet der Zustand
`HOLD`; das System darf weiter lesen und einen lokalen Plan erzeugen, aber weder
pushen noch eine externe Ursprungskopie anlegen.

## Selbstidentifikation des künstlich-kognitiven Systems

Die Selbstidentifikation verbraucht keine Benutzerfrage. Das System trägt, soweit
technisch verfügbar, selbst ein:

- Anbieter und Systemfamilie,
- Modell- oder Build-Bezeichnung,
- Sitzungs- oder Laufkennung,
- verwendete Werkzeuge und Adapter,
- Startzeit, Quell-Repository, Quell-Ref und Quell-Commit,
- bekannte Identitäts- und Beobachtungsgrenzen.

Nicht verfügbare Angaben werden mit `UNAVAILABLE` bezeichnet und nicht erfunden.

## Git-Topologie der persönlichen Ursprungskopie

Die Rollen sind eindeutig:

```text
upstream = https://github.com/ingolf-lohmann/qik-vrt.git
origin   = persönliche Ursprungskopie oder LOCAL_ONLY
```

Bei einer autorisierten Initialisierung gilt sinngemäß:

```sh
git clone https://github.com/Goldkelch/qik-vrt.git qik-vrt-working-memory
cd qik-vrt-working-memory
git remote rename origin upstream
git remote add origin <PERSONAL_ORIGIN_URL>
git fetch --all --prune
git switch -c work/<WORK_UNIT_ID> upstream/main
```

Bei `LOCAL_ONLY` entfällt `git remote add origin`. Das künstlich-kognitive System
legt kein Konto, kein Repository und keine Remote-Ref stillschweigend an. Clone,
Fork, Repository-Erstellung, Push und Pull Request bleiben unterscheidbare,
separat zu autorisierende Effekte. `QIKVRT_EXTERNAL_EFFECTS=disabled` ist die
Voreinstellung.

Die persönliche Kopie wird nicht allein durch ihre Existenz kanonisch. Die
Die aktuelle Authority ist gemäß `policy/CANONICAL_UPSTREAM_REMOTE_V1.json` `ingolf-lohmann/qik-vrt`; ein persönliches `origin` ist die
individuelle, dauerhafte Arbeits- und Nachweiskopie. Bytegleichheit,
Synchronisierung oder Promotion dürfen nur für exakt geprüfte Commits und Pfade
behauptet werden.

## Lückenlose, aber datensparsame Arbeitsprovenienz

Jede persistierte Aufgabe erhält eine abgegrenzte Work Unit unter
`state/work_units/<WORK_UNIT_ID>.json`. Mindestens zu binden sind:

- Quell-Repository, Quell-Ref, Quell-Commit und Ausgangsbaum,
- menschliche Kennung und konkret beigesteuerte Ziele, Randbedingungen,
  Entscheidungen, Freigaben, Messungen und manuelle Änderungen,
- künstlich-kognitive Selbstidentifikation und konkret beigesteuerte Analysen,
  Entwürfe, Codeänderungen, Transformationen, Werkzeugaktionen und Prüfungen,
- Eingabe- und Ausgabepfade mit Byteumfang und kryptografischen Digests,
- Branch, Commits, Elternbeziehungen und geänderte Pfade,
- ausgeführte Prüfkommandos, Ergebnisse, Unsicherheiten und erste Blocker,
- menschliche Annahme, Ablehnung oder noch ausstehende Entscheidung,
- externe Effekte und deren getrennte Post-Effect-Evidenz.

Die Beitragsklassen lauten:

```text
HUMAN
ARTIFICIAL_COGNITIVE_SYSTEM
JOINT_WITH_SEPARABLE_COMPONENTS
UNRESOLVED
```

`UNRESOLVED` darf niemals stillschweigend in `HUMAN` umgedeutet werden. `JOINT`
ist nur zulässig, wenn die einzelnen Bestandteile weiterhin getrennt benannt
werden. Ein vom Menschen akzeptierter KI-Entwurf bleibt hinsichtlich seiner
Entstehung ein KI-Beitrag; die Annahmeentscheidung ist ein menschlicher Beitrag.

Für zugehörige Commits sollen mindestens diese Trailer verwendet werden:

```text
QIKVRT-Human-Actor: <HUMAN_ATTRIBUTION_ID>
QIKVRT-AI-Actor: <SYSTEM_OR_MODEL_ID>
QIKVRT-Contribution-Record: state/work_units/<WORK_UNIT_ID>.json
QIKVRT-Human-Decision: PENDING | ACCEPTED | REJECTED | MODIFIED
```

Git-Trailer ergänzen, aber ersetzen den Work-Unit-Nachweis nicht. Separate
Commits für klar getrennte Beiträge sind zu bevorzugen. Force-Push,
History-Rewrite, nachträgliche Herkunftsumdeutung und das Löschen belastbarer
Zwischenstände sind für den Nachweispfad unzulässig. Korrekturen erfolgen durch
neue, rückgebundene Commits.

## Rechtliche Einordnung

Die Verordnung (EU) 2024/1689 ist grundsätzlich seit dem 2. August 2026
anwendbar, wobei einzelne Pflichten frühere oder spätere Anwendungstermine
haben. Artikel 50 enthält ab diesem Datum anwendbare Transparenzpflichten für
bestimmte KI-Systeme und KI-generierte oder manipulierte Inhalte. Technische
Dokumentation, Protokollierung und Dokumentenaufbewahrung nach den Artikeln 11,
12 und 18 betreffen insbesondere die jeweils erfassten Hochrisiko-KI-Systeme und
hängen von Rolle, Systemklasse und Einsatzkontext ab.

Diese Repository-Architektur unterstützt Nachvollziehbarkeit, Transparenz,
Dokumentation und Beweissicherung. Aus dem AI Act folgt jedoch keine allgemeine
Pflicht, jedes Mensch–KI-Projekt mit Git zu führen oder jede Text- und
Codeänderung nach diesem konkreten Schema zu kennzeichnen. Die Erklärung ist
keine Rechtsberatung und ersetzt keine rollen-, risiko-, urheber-, arbeits-,
datenschutz- oder branchenspezifische Prüfung. Für andere Rechtsordnungen gilt
dieselbe fail-closed Grenze: konkrete Pflichten werden nur nach gebundener
Rechtsquellen- und Zuständigkeitsprüfung behauptet.

Primärquellen:

- Verordnung (EU) 2024/1689: https://eur-lex.europa.eu/eli/reg/2024/1689/oj/deu
- EU-Kommission, Transparenzpflichten nach Artikel 50: https://digital-strategy.ec.europa.eu/de/faqs/transparency-obligations-under-article-50-ai-act

## Ergebnisgrenze

```text
PERSONAL_WORKING_MEMORY_ORIGIN = USER_SELECTED_OR_LOCAL_ONLY
MAXIMUM_HUMAN_QUESTIONS = 3
FOURTH_QUESTION = FORBIDDEN
HUMAN_AI_CONTRIBUTION_SEPARATION = REQUIRED
RAW_TRANSCRIPT_PERSISTENCE = NOT_REQUIRED
SECRETS_IN_REPOSITORY = FORBIDDEN
EXTERNAL_EFFECTS = DISABLED_BY_DEFAULT
LEGAL_COMPLIANCE = NOT_INFERRED
PASS = NOT_CLAIMED
FINAL_PASS = NOT_CLAIMED
EFFECT_ACK_DONE = NOT_CLAIMED
```


## `docs/ARCHITECTURE.md`

# QIKVRT Self-Contained GitHub Repository with REST/TCP-IP API V1

Created: 2026-06-26 05:43:26 CEST

This repository is a self-contained QIK-VRT repository root. It includes:

```text
GitHub-compatible REST/TCP-IP API shim
GitHub Actions workflow_dispatch / repository_dispatch workflow
OpenAPI contract
Handler implementation
Client implementation
Unit and TCP/IP E2E tests
CI workflow
Metagrammar test inventory
Audit and uploadability gates
```

## Local TCP/IP API

```bash
make run-api
```

Health:

```bash
curl http://127.0.0.1:8766/health
```

## Tests

```bash
make test
```

## GitHub REST API enablement

After upload to GitHub, the repository can be triggered through GitHub REST:

```text
POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches
POST https://api.github.com/repos/{owner}/{repo}/dispatches
```

## Boundaries

```text
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
LIVE_GITHUB_ACTIONS_RUN = SUCCESS (run 29764193906)
GITHUB_PAGES_BUILD_AND_DEPLOY = SUCCESS (run 29764192834)
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_THIRD_PARTY_REPRODUCTION = OPEN
```

These hosted results establish the named GitHub effects only. They do not
establish non-bypassability in every integration, production hardening,
external adoption, or empirical validation of claims outside the executable
software boundary.


## `docs/BOUNDARIES.md`

# Boundaries

NO_ACCOUNT_LOGIN_CAPTURE = TRUE
NO_UNAUTHORIZED_ACCOUNT_ACCESS = TRUE
NO_SCRAPING = TRUE
NO_BYPASS = TRUE
GITHUB_TOKEN_STAYS_IN_OWNER_RUNTIME = TRUE
FIXED_RELEASE_COMMIT = a8a9cb2666a91411489d4fc90a5306908f8428ea
FIXED_RELEASE_TREE = c5cefebd20b5836d730a4e9da82eeaa5c9363ebf
MAIN_DOCUMENT_SHA256 = b4d3601c831db8bb70704a3dbed1e95deb47779de9a15bac8ea463f2693f89fe
REMOTE_CI_RUN_29764193906 = SUCCESS
GITHUB_PAGES_RUN_29764192834 = SUCCESS
ZENODO_DOI_FOR_EXACT_RELEASE = OPEN
INDEPENDENT_REPRODUCTION = OPEN

Remote evidence is scoped to the named commit, tree, document, and workflow
runs. It must not be generalized to every archived file, future branch state,
external integration, or scientific claim.


## `docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Charta einer maschinenprüfbaren Wissenschaft

**Urheber:** Ingolf Lohmann  
**Technische Referenzarchitektur:** [QIK-VRT `/AI`](https://github.com/Goldkelch/qik-vrt/blob/main/AI)  
**Lizenz:** Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International

## Präambel

Wissenschaft lebt von überprüfbaren Aussagen, nachvollziehbaren Begründungen und der Möglichkeit unabhängiger Reproduktion. Mit zunehmender Komplexität wissenschaftlicher Erkenntnisse reichen statische Veröffentlichungen allein jedoch nicht mehr aus, um diesen Anforderungen dauerhaft gerecht zu werden.

Deshalb soll jede wissenschaftliche Aussage nicht nur veröffentlicht, sondern auch mit einem transparenten, maschinenlesbaren und reproduzierbaren Nachweis ihres jeweiligen Erkenntnisstatus verbunden sein.

Dieser Nachweis umfasst insbesondere:

- ihre Herkunft,
- ihre Bedeutung,
- ihre Voraussetzungen,
- ihre Abhängigkeiten,
- ihre Nachweise,
- ihren Geltungsbereich,
- ihre Historie sowie
- ihren aktuellen Verifikationsstatus.

Formale Beweise, empirische Evidenz, Simulationen, Experimente, Tests und dokumentarische Quellen werden nicht vermischt. Sie werden entsprechend ihrer jeweiligen wissenschaftlichen Methodik getrennt behandelt und gemeinsam dokumentiert.

Ziel ist nicht, wissenschaftliche Erkenntnis zu automatisieren oder endgültige Wahrheiten festzuschreiben. Ziel ist, den Weg von einer Aussage zu ihrem jeweiligen Erkenntnisstatus dauerhaft nachvollziehbar, reproduzierbar und überprüfbar zu machen.

Eine solche Infrastruktur stärkt Transparenz, Reproduzierbarkeit und Zusammenarbeit, erleichtert die Wiederverwendung wissenschaftlicher Ergebnisse und schafft eine belastbare Grundlage für langfristig wachsende Wissensbestände.

## Artikel 1 - Transparenz

Jede wissenschaftliche Aussage besitzt eine eindeutige Identität, eine dokumentierte Herkunft und einen nachvollziehbaren Erkenntnisstatus.

## Artikel 2 - Trennung der Nachweisformen

Mathematische Beweise, empirische Evidenz, Simulationen, Tests und historische Quellen werden gemeinsam verwaltet, aber niemals als gleichartige Nachweise behandelt.

## Artikel 3 - Reproduzierbarkeit

Jeder ausgewiesene Verifikationsstatus muss mit den dokumentierten Voraussetzungen und Werkzeugen reproduzierbar sein.

## Artikel 4 - Provenienz

Jede Ableitung bleibt bis zu ihrer Quelle zurückverfolgbar. Jede Änderung hinterlässt eine überprüfbare Historie.

## Artikel 5 - Offenheit

Die Wissensbasis verwendet offene Datenmodelle und dokumentierte Schnittstellen, damit unterschiedliche Werkzeuge und Institutionen zusammenarbeiten können.

## Artikel 6 - Revision

Wissenschaftliche Erkenntnis ist grundsätzlich revisierbar. Neue Daten, Beweise oder Formalisierungen ändern den dokumentierten Status, nicht die Historie.

## Artikel 7 - Nachvollziehbarkeit vor Autorität

Der Status einer Aussage ergibt sich aus ihren dokumentierten Nachweisen und Voraussetzungen, nicht aus der Identität ihrer Urheber oder ihrer Verbreitung.

## Artikel 8 - Dauerhaftigkeit

Verifikationsartefakte, Metadaten und Quellen werden so archiviert, dass sie langfristig referenzierbar und reproduzierbar bleiben.

## Artikel 9 - Skalierbarkeit

Die Architektur muss von einzelnen Aussagen bis zu großen, miteinander verknüpften Wissensbeständen konsistent funktionieren.

## Artikel 10 - Wissenschaftliche Bescheidenheit

Das System weist explizit aus, welche Aussagen formal bewiesen, empirisch gestützt, hypothetisch oder noch ungeprüft sind. Es ersetzt nicht den wissenschaftlichen Diskurs, sondern macht ihn transparenter.

## Zusammenfassung

Jede wissenschaftliche Aussage soll einen maschinenlesbaren, reproduzierbaren und transparent dokumentierten Erkenntnisstatus besitzen - einschließlich ihrer Herkunft, ihrer Voraussetzungen, ihrer Nachweise, ihrer Grenzen und ihrer Historie.

## Das Nachvollziehbarkeitsprinzip

Eine wissenschaftliche Aussage ist erst dann vollständig publiziert, wenn nicht nur ihr Inhalt, sondern auch ihr Erkenntnisweg dauerhaft nachvollziehbar ist.

Dieser Erkenntnisweg besteht aus fünf voneinander unabhängigen, aber miteinander verknüpften Bestandteilen:

1. **Quelle** - Woher stammt die Aussage?
2. **Bedeutung** - Was genau wird behauptet?
3. **Begründung** - Wodurch wird sie gestützt?
4. **Grenzen** - Unter welchen Voraussetzungen gilt sie?
5. **Historie** - Wie hat sich ihr Erkenntnisstatus entwickelt?

Erst das Zusammenspiel dieser fünf Elemente ermöglicht eine belastbare Bewertung.

### Konsequenz für die Architektur

Eine wissenschaftliche Wissensbasis speichert nicht nur Informationen, sondern dokumentiert auch den Erkenntnisprozess. Jede Änderung - etwa eine neue Formalisierung, ein verbessertes Experiment oder eine unabhängige Reproduktion - ergänzt diesen Prozess, ohne frühere Zustände zu löschen.

### Praktischer Nutzen

Eine solche Architektur kann insbesondere:

- die Reproduzierbarkeit wissenschaftlicher Ergebnisse verbessern,
- die Wiederverwendung formaler Beweise und anderer Nachweise erleichtern,
- Änderungen und ihre Auswirkungen transparent machen,
- die Integration verschiedener Nachweisformen unterstützen und
- den aktuellen Erkenntnisstand einer Aussage jederzeit nachvollziehbar darstellen.

> Nicht nur Wissen soll dauerhaft verfügbar sein, sondern auch der Weg, auf dem dieses Wissen begründet wurde.

# Architekturgrundprinzipien der QIK-VRT-Repository-Architektur

## 1. Repository vor Konversation

- Das Repository ist die dauerhafte Wissensbasis.
- Chats sind flüchtige Transportschichten.
- Repository-Evidenz hat Vorrang vor Modellgedächtnis.

## 2. Einheitlicher Einstieg

- Jeder neue Mensch oder jede KI beginnt bei `/AI`.
- Danach folgt `AI_CONTEXT.json`.
- Anschließend wird die definierte `required_read_order` abgearbeitet.

## 3. Deterministische Rekonstruktion

Jede neue Instanz muss den vollständigen Projektzustand ausschließlich aus dem Repository rekonstruieren können, ohne den Verlauf früherer Chats zu benötigen.

## 4. Persistenz statt Vergessen

Dauerhafte Erkenntnisse werden im Repository abgelegt. Der Chat dient ausschließlich der aktuellen Interaktion.

## 5. Reuse before Create

Bestehende Werkzeuge werden bevorzugt erweitert, parametrisiert oder generalisiert. Parallele Implementierungen sind nur zulässig, wenn eine Wiederverwendung technisch nachweislich nicht ausreicht.

## 6. Repository als Runtime

Das Repository enthält nicht nur Quellcode, sondern die vollständige reproduzierbare Laufzeitumgebung:

- Toolchain,
- Runtime,
- Cache,
- Bootstrap,
- Tests,
- Provenienz,
- Recovery und
- Verifikation.

## 7. Vollständige Werkzeugbeschreibung

Jedes verwendete Werkzeug besitzt mindestens:

- Version,
- Herkunft,
- Verifikation,
- Selbsttest,
- Lizenz,
- Cache-Strategie,
- Recovery-Regeln und
- Telemetrie.

## 8. Kontinuierliche Verbesserung

Jede erfolgreiche Ausführung soll die Runtime schneller, robuster, reproduzierbarer und besser diagnostizierbar machen.

## 9. Vollständige Nachvollziehbarkeit

Keine Wirkung ohne Tests, Hashes, Provenienz, Integrität und Freigabe.

## 10. Wirkung vor Erklärung

Zuerst arbeiten, danach berichten. Dies gilt insbesondere für automatisierte Repository- und GitHub-Aktionen.

## 11. Fortschritt ist maschinenlesbar

Der Bearbeitungszustand wird standardisiert dokumentiert, beispielsweise in `AI_PROGRESS.json` und `AI_STATUS.md`.

## 12. Keine Behauptung ohne Evidenz

PASS, DONE, Veröffentlichung oder Gleichwertigkeit dürfen niemals ohne überprüfbare Evidenz behauptet werden.

## 13. Strikte Wirkungsgrenze

Transport, Berechnung, Analyse und Vorschläge sind nicht identisch mit einer freigegebenen Wirkung (`EFFECT_ACK_DONE`).

## 14. Menschliche Verantwortung bleibt erhalten

Die letzte Freigabe liegt stets beim verantwortlichen Menschen. Automatische Ausführung ersetzt diese Verantwortung nicht.

## 15. Kumulative kollektive Kognition

Beobachtungen werden gesammelt, strukturiert und reproduzierbar zusammengeführt. Daraus entstehen überprüfbare Vorschläge, nicht automatisch Änderungen.

## 16. Architektur ist nicht Implementierung

Die Architektur kann frei beschrieben und wissenschaftlich diskutiert werden. Die konkrete Implementierung bleibt lizenz-, urheber- und rechtegebunden.

# Erweiterungsprinzip

Durch die kontinuierliche, geeignete Persistierung jeder relevanten Interaktion in den QIK-VRT-Repositories kann im Zusammenspiel von natürlicher Kognition, maschineller Antizipation und künstlicher Kognition eine persistente, kumulativ lernende Informatikarchitektur entstehen. Ihre Leistungsfähigkeit wächst mit jeder verifizierten Iteration durch neue Repository-Artefakte, Verifikationen und Runtime-Erweiterungen.

# Systemmodell

Diese Architektur besteht aus vier dauerhaft zusammenwirkenden Komponenten:

1. Repository `Goldkelch/qik-vrt`,
2. Repository `ingolf-lohmann/qik-vrt`,
3. natürlicher menschlicher Kognition und
4. ChatGPT als Übersetzungs-, Interaktions- und Assistenzschicht.

Das Repository bildet die dauerhafte Autorität. Der Dialog dient als austauschbare Benutzerschnittstelle.

# Wissenschaftliche Einordnung

Diese Architektur beschreibt ein persistentes kollaboratives Kognitionssystem, dessen Informationsfluss sich in vieler Hinsicht analog zu einem lernenden Netzwerk verhält.

Die Persistenz liegt nicht in biologischen Synapsen, sondern in versionierten Repository-Artefakten. Mit jeder verifizierten Änderung wächst die rekonstruierbare Wissens- und Laufzeitbasis, sodass neue Menschen oder KI-Systeme unmittelbar auf den dokumentierten Erkenntnis- und Entwicklungsstand aufsetzen können, ohne auf frühere Gespräche angewiesen zu sein.

Die Architektur beschreibt keine biologische Kognition, sondern ein informatisches Modell eines persistenten kollaborativen Kognitionssystems. Seine langfristige Lernfähigkeit entsteht durch versionierte Repository-Artefakte, reproduzierbare Runtime-Verträge und kontinuierlich verifizierte Persistenz.

**q.e.d.**  
**Ingolf Lohmann**


## `docs/CLAUDE_MCP_CONNECTOR.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Claude Remote-MCP application path

The integrated `/mcp` endpoint reuses PR #509's three evidence-read tools and
PR #511's two data tools in the same `src/qikvrt_github_api_shim.py` transport.
The #509 module retains its read/source/receipt/replay semantics and has no
separate HTTP or JSON-RPC dispatcher. `qikvrt_ingest` delegates to the existing
five-state handler; `qikvrt_readback` and an independent raw-byte GET reuse its
committed ingest-provenance validator. Existing REST paths, client options and
fixed Ruleset pins remain intact. No new dependencies or credential store.

Human scope/implementation authorization: Ingolf Lohmann, 2026-10-09.
Implementation and tests: OpenAI Codex, GPT-6 family; exact build unavailable.
Contribution terms, independent Code Owner review and exact candidate
acceptance remain incorporation gates.

## Reused subjects

| Component | Exact inspected source | Evidence scope |
| --- | --- | --- |
| REST client 2.3.0 | #508 HEAD `2e847ce4af60451bef11ec1b89540d56ee4e3ea6`, TREE `cde054f9aa56d98cb2389df910e0e9c19fc16deb` | Existing REST client, local handler and independent Ruleset readback |
| Evidence-read tools | #509 HEAD `f760a4090b4ca792ca1d79edacce11f4bded7ee0`, TREE `de7a9f41e3e3df62df7fd65225e3c31777ee3c58` | Fresh HEAD/TREE, exact capability blobs and existing EFFECT_ACK receipts |
| Data tools and raw readback | #511 HEAD `18d2598fdbabf4630c9fe168313686aa5743df79`, TREE `bfba67cdce90b4f29838e7018be5c1cbd594de4f` | Authenticated opaque-byte ingest and committed original bytes |
| Direct Claude Messages provider | #506 HEAD `e31ca36c2e64d86a03696525a85865c7332a6377` | Separate provider/budget candidate; no Web-Connector effect |
| Published Mesh Monitor | Site version 17, HEAD `b2d6a25b00abe9b4b0e1301dc08b9504b3e61147`, TREE `1c81811b79160c5ffe9b42b0246eafeaa77004e4` | Fresh authenticated Work MCP observe/readback and independently verified stored bytes; Claude connection remains unverified |

Source locators:

- https://github.com/ingolf-lohmann/qik-vrt/pull/508
- https://github.com/ingolf-lohmann/qik-vrt/pull/509
- https://github.com/ingolf-lohmann/qik-vrt/pull/511
- https://github.com/ingolf-lohmann/qik-vrt/pull/506
- https://qikvrt-scheibenhard.ingolf-lohmann.chatgpt.site/mcp

The monitor supplies observation/D1-snapshot tools on a separate source tree.
Main did not yet contain either MCP candidate at the source inspection.
This integration reuses both existing candidates rather than introducing a
third adapter. The existing monitor/OAuth path
is preserved; this candidate does not deploy to or change that Site.

## Private configuration and permissions

Use the established `make run-api` with its required private environment:
`QIKVRT_API_TOKEN`, future `QIKVRT_API_TOKEN_EXPIRES_UTC`, exact
`QIKVRT_ALLOWED_REPOSITORY`, `QIKVRT_API_PRINCIPAL`, and private durable
`QIKVRT_REPO_ROOT`. Add `QIKVRT_MCP_ENABLED=1`. Separate explicit grants:

| Credential | Principal | Allowlist | Tools |
| --- | --- | --- | --- |
| `QIKVRT_MCP_TOKEN` and future `QIKVRT_MCP_TOKEN_EXPIRES_UTC` | `QIKVRT_MCP_PRINCIPAL` | `QIKVRT_MCP_READ_SCOPES='repository:read capability:read effect_ack:read'` | `qikvrt_repository_state`, `qikvrt_capabilities`, `qikvrt_effect_ack_result` |
| Same separate read credential, additional explicit grant | Same read principal, must own the committed artifact | Add `artifact:read` to `QIKVRT_MCP_READ_SCOPES` | `qikvrt_readback` and raw GET; no ingest |
| Existing REST credential | `QIKVRT_API_PRINCIPAL` | `QIKVRT_MCP_DATA_SCOPES='readback'`; add `ingest` only for authorized storage | `qikvrt_readback`, optionally `qikvrt_ingest` |

Legacy `QIKVRT_MCP_SCOPES` configurations remain valid: their recognized scopes
are filtered separately by authenticated credential domain. An explicit new
domain allowlist takes precedence over its legacy projection, even when empty.
Unknown or misclassified scopes fail closed. Read keys may not alias REST,
attestation or upstream keys. No scopes means no corresponding exposed tools.
The read profile preserves its configured `QIKVRT_MCP_REF` and independent
GitHub GET credential. Replays recheck current auth,
expiry, permission, source/version and explicit acceptance.

The server remains loopback by default. Remote deployment must preserve its
non-loopback opt-in and TLS certificate/key requirements, specify exact
`QIKVRT_MCP_HOSTS` host:port values and configure `QIKVRT_MCP_ORIGINS` when
browser Origins are expected. Host, Origin, duplicate security headers, bearer
expiry and rate limits are checked before execution. OAuth is not implemented
here. Claude's documented private fixed request headers can send the existing
`Authorization: Bearer ...` credential. This is a shared service-principal
configuration, not authentication of a natural person. Retain source-system
permissions and the selected Claude connector's write approval requirements.
Never put credential values into source, logs or evidence.

## Operation and source contracts

Both tools require exact `repository`, `artifact_id`, stable `request_id`,
`expected_sha256`, `api_contract_version: '2.3.0'` and
`expected_implementation_sha256`. Ingest additionally requires canonical
`payload_b64` (at most 256 KiB decoded) and literal `effect_accepted: true`.
Unknown fields, bad hashes, changed versions/source and missing permission
fail before the handler. No automatic fallback or blind retry.

The implementation digest is SHA-256 over the UTF-8 compact sorted JSON map
from these paths to their SHA-256 file digests:

- `scripts/qikvrt_api_client.py`
- `src/qikvrt_api_handler.py`
- `src/qikvrt_effect_ack.py`
- `src/qikvrt_github_api_shim.py`
- `src/qikvrt_mcp_adapter.py`
- `api/qikvrt_github_api.openapi.yaml`

The service freezes this digest at startup and rejects later source drift.
Discovery reports it for inspection; obtain the expected digest independently
from accepted exact candidate bytes. Self-reported discovery alone is not
provenance authority. A changed candidate requires newly reviewed/bound bytes.

MCP `2025-11-25` uses initialization, JSON responses and no optional session/SSE
stream. Current `2026-07-28` uses discovery and per-request `_meta`; the
version/method/tool headers must match the body. The evidence tools retain
their two older, read-only protocol versions. Data writes retain only
`2025-11-25` and `2026-07-28`. This bounded five-tool integration
does not claim optional resources, prompts, sampling or task support.

The original nested handler `EFFECT_ACK_DONE` remains limited to opaque-byte
storage. The MCP envelope stays `EFFECT_ACK_CONTINUE`, `ordinary_release=false`
and `claude_connector_execution_verified=false`. It cannot infer product
release, native Mesh execution, merge or Claude provenance from a client name.

Readback takes a shared lock on the writer's existing lock file, validates
payload, sidecar, provenance, committed transaction, replay receipt and
responsibility protocol, and returns only the same principal's artifact.
It creates no directory, audit event or receipt. Independently fetch:

`GET /repos/{owner}/{repo}/qikvrt/artifacts/{artifact_id}/readback`

with exact `request_id`, `expected_sha256`, `api_contract_version` and
`expected_implementation_sha256` query values, then recompute SHA-256. Both
routes share the local store trust boundary: the separation verifies response
serialization, not a second storage authority. Existing local checksums/audit
chains are not an external rewrite-proof anchor. Deployment must provide the
durable state volume and retention.

## Reproduction

Run `make mcp-conformance-test`, then `make test`. Tests exercise the real
adapter in a separate process with ephemeral fixture credentials. Coverage:
both protocol eras; scoped write plus raw GET; read-only non-mutation; restart
replay; eight concurrent identical calls; changed replay isolation; missing,
invalid and expired auth; missing read/write permission; repository/principal
confinement; wrong version/source/hash; header/body conflict; Host/Origin;
malformed/duplicate JSON; payload limit; and bytes/sidecar/provenance/receipt/
transaction tampering.

Both original conformance suites remain in this target. Joint regressions
exercise separate catalogs, cross-key refusal, explicit original-byte read
grants, principal confinement, source drift, revocation before replay and
discovery without an effect grant. Only source-set expectations in the
original tests change; their original positive and negative assertions remain.

The candidate targets Main and includes the entire #508 dependency, with its
workflow sources, writer pins and native gates preserved. Main-based scope
does not establish enforced Code Owner governance, contribution acceptance or
an independent exact-head approval. These remain governed-incorporation gates.

`scripts/qikvrt_mcp_probe.py` is a standard-library HTTP/JSON/SHA-256 client
with no server imports, no credential redirects and no retries. Default:

```sh
python3 -B scripts/qikvrt_mcp_probe.py \
  --base-url "$QIKVRT_VERIFIED_SERVICE_ORIGIN" \
  --repository ingolf-lohmann/qik-vrt \
  --artifact-id "$QIKVRT_BOUND_ARTIFACT_ID" \
  --request-id "$QIKVRT_BOUND_REQUEST_ID" \
  --expected-sha256 "$QIKVRT_EXPECTED_PAYLOAD_SHA256" \
  --expected-implementation-sha256 "$QIKVRT_EXPECTED_IMPLEMENTATION_SHA256"
```

Only add `--payload-file <approved-file> --accept-effect` for one explicitly
authorized ingest. The private environment supplies the token. Output excludes
credentials/payload bytes and always keeps Claude provenance unverified.
A passing generic client probe is conformance, not actual Claude execution.

## Remaining external boundary

This task exposes no callable authenticated Claude account operation. The
monitor still advertises its same version-17 endpoint. Its two earlier direct
authorization paths returned 401 and are not retried. A materially new
capability appeared during this task: its three actual MCP tools became
callable through the existing authorized Work connection. `qikvrt_observe`
returned a new persistent observation, then `qikvrt_readback` independently
read that exact ID and expected digest. Local Python SHA-256 verification of
the original returned UTF-8 bytes passed: 5,663 bytes, digest
`b666efd88ad324981ec672b9f5853e78f7f59ee3b0bb0ac5b0750e8fe748bb54`,
snapshot `569fb70c-9ba9-4d22-9bdf-314ca388db40`. The fresh evidence is in
`evidence/claude-mcp-connector/2026-10-09/`. This establishes the existing
monitor's Work MCP application scope, not Claude execution or this candidate's
remote deployment. A separate direct public REST fetch from this environment
failed with HTTP 403; no retry was issued and no origin-level cause inferred.

After governed incorporation, deploy these exact accepted bytes to an
authorized public HTTPS service with durable state and privately configured
expiring credentials. Add that verified endpoint to Claude, complete its
private authentication/header configuration, observe an actual `tools/call`
trace from the Claude connection and independently verify the returned bytes
over raw REST. Bind candidate HEAD/TREE, invocation, request and byte digests.
This closes `CLAUDE_WEB_CONNECTOR_EXECUTION` only when independently observed.
The existing monitor may be used after its own OAuth connection becomes
callable, under its separate observation/snapshot contract.

`raumzeitterminal.de` is separately required. The historical #511 provider readback reports
`pending`, `ssl_status=pending_validation`; another hostname proves no delivery
there. No deployment, domain, OAuth, credential, Ruleset or review setting is
changed by this candidate.

Primary specifications, retrieved 2026-10-09:

- https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports


## `docs/COLLECTIVE_ADAPTIVE_COGNITION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Collective adaptive cognition: bounded protocol

## Purpose

This protocol turns multiple attributable observations into a reviewable,
content-addressed proposal. “Collective” means here only that at least two
distinct `observer_id` values label attributable observation records.
Identifier distinctness does not authenticate a person or organization and
does not prove methodological independence, causal independence, or social
consensus. The two deterministic measurements in the workflow run in the same
job and repository context and therefore are not independent reviewers.
“Adaptive” means that
later proposals may use measured results from earlier runs. Neither term means
a shared mind, autonomous authority, self-rewriting code, or permission to act.

The protocol is deliberately smaller than the QIK-VRT effect gate. It creates
evidence for a later decision; it does not replace the decision.

## State transition

```text
authorized observation
  -> schema validation
  -> byte-level SHA-256 binding
  -> attributed aggregation
  -> disagreement preservation
  -> structured proposal
  -> mandatory checks
  -> human review
  -> separate EFFECT_ACK evaluation
```

The repository runtime stops after “structured proposal”. Its only permitted
effect state is `EFFECT_ACK_CONTINUE`, and `ordinary_release` is always false.

## Observation contract

Each UTF-8 JSON observation uses schema
`qikvrt_collective_observation_v1` and contains:

- a unique observation and observer identifier;
- a bounded subject and UTC measurement time;
- scalar measurements with units and disclosed methods;
- findings that reference those measurements;
- optional recommendations that reference findings; and
- explicit limitations.

The runtime rejects unknown top-level keys, symbolic links, duplicate
observation identifiers, invalid references, non-finite numbers, and fewer than
two distinct observer identifiers. Its output sets identifier authentication,
organizational, causal, and person-identity verification to false and expressly
claims no consensus.
Observation text is data only and is never evaluated as a command, template,
expression, or workflow fragment.

## Evidence and synthesis

`tools/qikvrt_adaptive_runtime.sh` reads the fixed repository policy and writes
only to a new directory below `.qikvrt/evidence/collective-adaptive/`, which is
volatile and ignored by Git. It creates:

- `evidence.json`, containing the SHA-256 digest and size of every exact input,
  the policy and runtime digests, and the observed repository commit and tree;
- `proposal.json`, containing attributed proposal groups, support counts,
  conflicting variants, pending checks, and the digest of `evidence.json`.

Recommendations with the same identifier are grouped. Different content under
the same identifier is retained as a conflict; it is not averaged away. A
matching-content or identifier count is a prioritization signal only. It is
never a claim of independence, consensus, truth, or authorization.

Output confinement uses no-follow directory descriptors. Existing `.qikvrt`,
`.qikvrt/evidence`, and `collective-adaptive` components must be real
directories, not symbolic links. The runtime creates the run directory and its
two files relative to already-open directory descriptors and rechecks directory
identity after writing, so a replaced or redirected base fails closed.

## Non-effects

The runtime has no network operation and no Git write operation. It does not:

- edit source, policy, workflows, documentation, or its own implementation;
- create commits, branches, pull requests, merges, tags, releases, or deposits;
- install, update, cache, or execute proposed code;
- change permissions, CODEOWNERS, branch protection, or secrets;
- invoke other agents or recursively generate observations; or
- convert review consensus into `EFFECT_ACK_DONE`.

The GitHub workflow has read-only repository permissions, runs required tests,
generates deterministic measurements, and uploads only volatile review
artifacts. It cannot approve, merge, push, tag, or release.

## Required human boundary

Before any proposal is implemented, a responsible human must review its scope,
provenance, rights, security impact, claim boundary, test evidence, and expected
downstream effect. Implementation is a new, ordinary change subject to the full
repository process. Release additionally requires a separately authenticated
and freshly derived `EFFECT_ACK_DONE`; workflow success and human approval alone
do not manufacture that state.

## Reproducibility

Run the local contract and negative controls with:

```bash
bash -n tools/qikvrt_adaptive_runtime.sh tests/test_adaptive_runtime.sh
bash tests/test_adaptive_runtime.sh
```

The tests confirm the proposal-only state, evidence binding, the
distinct-observer-identifier requirement, path confinement, rejection of
executable fields and absence of tracked-file mutation.


## `docs/CURRENT_AUTHORITY.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Current authority map

QIK-VRT contains an active reference implementation and a substantial
historical research and delivery archive. This map identifies the shortest
path to the current operational authority.

## Active runtime

- `src/qikvrt_effect_ack.py` — five-state synchronous reference gate
- `src/qikvrt_api_handler.py` — authenticated ingest, verification, staging,
  status, transaction, provenance, and audit behavior
- `src/qikvrt_github_api_shim.py` — repository-scoped local HTTP adapter
- `scripts/qikvrt_api_client.py` — validating client
- `qikvrt.py` — authorization-before-effect launcher and publication planner
- `tools/qikvrt_subprocess.py` — bounded subprocess supervision
- `tools/qikvrt_integrity.py` — canonical content-tree integrity tooling
- `src/effect_ack_core.c` and `include/qikvrt/effect_ack.h` — strict ANSI-C90
  five-state core
- `tools/qikvrt_adaptive_runtime.sh` and `runtime/` — bounded proposal-only
  collective adaptation and exact-key verified cache reuse
- `tools/qikvrt_anticipation.py`, `anticipation/`, and
  `receipts/anticipation/` — deterministic current-status projection and
  hash-linked, effect-free closure checkpoints
- `tools/qikvrt_zenodo_actions.py` — hash-bound DOI reserve/finalize client
- `api/qikvrt_github_api.openapi.yaml` — external API contract

## Verification authority

- `tests/` — twelve Python test modules, the offline renderer, and shell/C90
  verification contracts
- `Makefile` — complete local verification entry point
- `STATUS.md` — precise demonstrated and open boundaries
- `BUILD_SUMMARY.md` — test counts and verification results
- `docs/TEST_INVENTORY.md` — test-module inventory
- `REPOSITORY_FILE_MANIFEST.json`, `SHA256SUMS.txt`, and
  `REPOSITORY_FILE_MANIFEST.json.sha256` — canonical integrity trio

## Concept and specification

- `README.md` — current technical entry point
- `docs/ARCHITECTURE.md` — runtime and deployment architecture
- `docs/BOUNDARIES.md` — operational boundaries
- `docs/QIKVRT_THREAT_MODEL.md` — threat model
- `docs/Die_Spirale_des_entscheidenden_Unterschieds.md` — full German-language
  synthesis, including the universal ontology of difference and the distinct
  proof and correspondence levels used by the work

## Release anchor

The current public release is the annotated tag
`v2026.07.22-effect-ack-universality-1.0.0` in both repositories. The working
paper is archived as `10.5281/zenodo.21498773`; the deterministic tagged source
export is archived as `10.5281/zenodo.21498774`. Exact repository-specific
commit, tree and tag-object identities are retained on the public
`qikvrt/zenodo-state` evidence branch.

Historical files remain evidence of their own time and content. They do not
override a current failure or expand the supported runtime scope.


## `docs/EFFECT_ACK_RELEASE_AUTOMATION.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# EFFECT_ACK release automation

This contract automates the already authorized EFFECT_ACK universality release
without a `workflow_dispatch`, a GitHub Release object, a Datatracker
submission, or another interactive sign-in exercise. It consumes the existing
repository secret `ZENODO_ACCESS_TOKEN` only inside the two Zenodo client
steps. The token is never a command-line argument, artifact, state-branch
value, job output, or log value.

The automation is deliberately separate from the bounded adaptive runtime.
Adaptive evidence cannot activate it. Only a reviewed, single-file marker
commit with the exact state, confirmation phrase, source commit, source tree,
schema digest, client digest, manifest digest, and canonical authorization
digest can reach an external-effect job.

## Fixed release identity

| Field | Exact value |
|---|---|
| Version | `2026.07.22-effect-ack-universality-1.0.0` |
| Annotated tag | `v2026.07.22-effect-ack-universality-1.0.0` |
| Tagger | `Ingolf Lohmann <ingolf.lohmann@live.com>` |
| Tagger timestamp | `2026-07-22T00:00:00Z` |
| Authority repository | `Goldkelch/qik-vrt` |
| Mirror repository | `ingolf-lohmann/qik-vrt` |
| Public evidence branch | `qikvrt/zenodo-state` |

The full fixed tag message is in
`release/effect-ack-universality-request.json` and in both workflows. GitHub's
Git database API creates an annotated tag object directly. The finalize
workflow performs one read-only `GET /releases/tags/<tag>` check and blocks
unless GitHub returns `404`; it never creates, edits, deletes, or publishes a
GitHub Release object.

## Immutable two-commit authorization

Both phases use the same pattern. The automation branch must first point to
commit A. Commit A contains the complete reviewed candidate and the inert
marker. Commit B must have A as its sole parent and must change exactly one
path: `release/effect-ack-universality-request.json`. The push of B is the
triggering event.

The workflow blocks unless all of the following are simultaneously true:

1. the event repository and exact automation ref are allowed;
2. the push is not forced, the remote branch still points to B, and the event's
   `before` value is A;
3. B has exactly one parent, and the only A-to-B change is the marker;
4. `expected_source_commit` equals A and `expected_source_tree` equals A's Git
   tree through `git show -s --format=%T HEAD^` and the GitHub API; the marker
   HEAD tree is separately required to differ, preventing accidental use of
   `HEAD^{tree}` in place of the authorized parent tree;
5. the marker has the closed key set and fixed constants, the checked-in JSON
   Schema digest matches, and the canonical authorization digest matches;
6. the hash-bound Zenodo client and the phase-specific Zenodo manifest are
   regular, non-symlink files with the authorized SHA-256 values;
7. `make test` passes in a detached worktree of A, including the canonical
   repository-integrity gate.

This construction avoids a self-referential commit hash in the marker. The
effect targets parent A, never marker commit B. The active marker therefore
stays outside `main`.

The canonical authorization digest is SHA-256 over UTF-8 JSON after removing
only `authorization_payload_sha256`, sorting keys, and using `,` and `:` as
separators without ASCII escaping. The digest detects any change to every
other marker field. It is a byte-binding mechanism; repository review and the
exact confirmation phrase supply authorization.

## Phase 1: reserve, never publish

The reserve workflow listens only on:

`refs/heads/automation/effect-ack-universality-reserve-20260722`

It runs only in `Goldkelch/qik-vrt`. The active marker must use:

- `state`: `reserve`
- `confirm`: `RESERVE_ZENODO_DRAFT_ONLY_NO_PUBLISH`
- exact A commit/tree and current client/reserve-manifest digests
- zero reservation-evidence digest and null DOI fields

After the full release-candidate gate, the workflow invokes:

```text
python -B tools/qikvrt_zenodo_actions.py reserve \
  --manifest release/effect-ack-universality-zenodo.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The client may create or resume drafts and reserve identifiers, but this phase
does not publish. The workflow rejects a result containing the secret, a
secret-shaped field, or an affirmative publication/submission flag.

The exact non-secret reservation result is uploaded as a 30-day Actions
artifact and committed to this stable public path on the dedicated state
branch:

`release-state/effect-ack-universality/zenodo-reservation.json`

That branch is an automation evidence channel, not a source branch. It must
remain writable by the repository `GITHUB_TOKEN` and must not be merged into
`main`. Its history preserves replaced evidence. The state writer creates an
orphan root commit when the branch is absent and otherwise appends a
non-forced commit. Repeating a completed run with identical bytes is a no-op.

The reservation binds the immutable release identity and repository/tag
authorization envelope. The later final manifest may add the reserved DOI to
metadata and rebuild file hashes; it is not incorrectly required to retain a
pre-DOI full-file fingerprint.

The software draft versions the credential-owned QIK-VRT concept
`10.5281/zenodo.21488115` from source record `10.5281/zenodo.21488116`.
Legacy QIKVRT V8.33 record `10.5281/zenodo.20712301` remains an explicit
historical reference; this automation does not claim or rewrite its separately
owned version chain.

## Phase 2: tag both repositories, then publish on Goldkelch

After the reserved DOI values have been embedded, rendered, verified and
merged, both `main` branches must have the same final tree. In each repository,
create the branch below at its own exact `main` commit A, then add only active
marker commit B:

`refs/heads/automation/effect-ack-universality-finalize-20260722`

The active marker must use:

- `state`: `finalize`
- `confirm`: `FINALIZE_TAGS_AND_ZENODO_PUBLICATION`
- that repository's exact main commit A and the shared final tree
- the final client and manifest SHA-256 values
- the SHA-256 of the public reservation result
- both DOI values from that reservation

The finalize workflow additionally proves that A is still the current `main`
head. It then creates the fixed annotated tag at A. If the tag already exists,
the workflow succeeds only when its annotated-object type, target commit,
target tree, tagger identity, timestamp and message all match exactly. A
lightweight, moved or differently annotated tag blocks the run.
Immediately after tag verification, a read-only GitHub API lookup must also
prove that no GitHub Release object exists for that tag.

Run the mirror authorization first. `ingolf-lohmann/qik-vrt` performs only the
tag and public tag verification. The Goldkelch job creates or verifies its own
tag, polls the public mirror tag, and requires the mirror target to have the
same authorized final tree and fixed annotation.

Immediately before publication, the checked-in hash-bound template is expanded
outside the tagged tree:

```text
python -B tools/qikvrt_build_zenodo_manifest.py \
  --repository-root . \
  --template release/effect-ack-universality-zenodo.json \
  --source-commit <authorized-main-commit> \
  --source-tree <authorized-main-tree> \
  --output-directory .qikvrt/release/effect-ack-universality \
  --result .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json
```

The helper reads every blob path from the exact authorized parent commit,
verifies its tree, and emits a normalized deterministic `tar.gz`, a checksum,
provenance, and a transient final manifest. The checked-in reserve template
contains an explicit non-upload sentinel; the final client rejects that
sentinel. The generated manifest replaces it with the exact archive,
checksum, and provenance hashes. Because those derived bytes live under the
integrity-transient `.qikvrt/` prefix and are not inside the tagged tree, the
archive contains the complete tagged tree without asking that tree to contain
the digest of an archive that contains itself.

Only then does Goldkelch call:

```text
python -B tools/qikvrt_zenodo_actions.py finalize \
  --manifest .qikvrt/release/effect-ack-universality/zenodo-final-manifest.json \
  --reservation .qikvrt/release/effect-ack-universality/zenodo-reservation.json \
  --result .qikvrt/release/effect-ack-universality/zenodo-finalization.json \
  --base-url https://zenodo.org/api \
  --repository-root .
```

The hash-bound client provides the idempotent Zenodo reservation/finalization
semantics. A retry verifies the existing tag rather than moving it and resumes
the bound Zenodo records rather than creating unrelated records.

Each repository writes public tag evidence to
`release-state/effect-ack-universality/tag-verification.json`. Goldkelch also
writes a non-secret finalization envelope—with both DOI results, the generated
manifest digest, every deposited filename/size/MD5/SHA-256, and the tag target
commit/tree—to
`release-state/effect-ack-universality/zenodo-finalization.json`. Matching
Actions artifacts are retained for 30 days.

## Permissions and trigger boundary

Validation jobs have `contents: read`. Only jobs that create a tag or append
public evidence have `contents: write`. The repository-scoped `GITHUB_TOKEN`
is used only in its own repository; no cross-repository write token is needed.
Goldkelch reads the public mirror tag but does not modify the mirror.

There is deliberately no `environment:` gate and no interactive login or SSO
step. The immutable two-commit marker is the explicit reviewed authorization,
and Goldkelch consumes its already configured repository secret directly.

All external Actions are pinned by full commit SHA. Both workflows share one
non-cancelling per-repository concurrency group so reserve, tag and state
writes cannot overlap in the same repository.

GitHub documents that events created with `GITHUB_TOKEN` generally do not
start a new workflow run. Accordingly, tag creation is the terminal GitHub
effect here; correctness does not depend on a tag-triggered follow-up workflow
or on a GitHub Release object. Zenodo finalization is an explicit job in the
same Goldkelch workflow.

No step calls the IETF Datatracker. The existing `-01` XML/TXT/HTML validation
remains evidence only and is not submitted by this release automation.


## `docs/GITHUB_DEPLOYMENT.md`

# GitHub REST API execution and continuation

Use `GITHUB_ROUTE=REST_API_ONLY` and the existing authenticated connection.
Read `/AI` and its required evidence before execution. A callable REST POST,
an appropriate repository-scoped credential, and native workflow admission
must each be established; a successful GET does not establish any of them.
Never replace missing initial admission with a rerun, proxy trigger, browser
login, or permission expansion.

## Dispatch adapter/client contract 2.3.0

`api/qikvrt_github_api.openapi.yaml` remains compatible with 2.0.0 and 2.1.0 requests.
The four Mesh operations and existing effect gates are unchanged. The optional
boolean `return_run_details` requests GitHub's asynchronous run ID and URLs.
The loopback adapter accepts this field but retains its synchronous `202`
response and existing handler result.

With an already delivered and scoped credential in `QIKVRT_API_TOKEN`, the
existing client can submit one authorized request:

```sh
python3 scripts/qikvrt_api_client.py \
  --base-url https://api.github.com \
  --owner ingolf-lohmann --repo qik-vrt --ref main \
  --operation release_status --artifact-id status --dry-run true \
  --request-id OWNER_AUTHORIZED_UNIQUE_REQUEST_ID --return-run-details
```

This example is not evidence that a credential or callable executor exists.
Use the exact approved ref and request identifier for the actual work unit.
Do not copy connection credentials into files, chat, logs, or caches.

| Response | Client exit | Evidence established | Required continuation |
| --- | --- | --- | --- |
| GitHub `204`, empty body | `20` | Dispatch transport accepted; run identity unknown | Read authoritative workflow runs and identify the exact subject/request |
| GitHub `200`, bound run details | `20` | Dispatch transport accepted; repository/run URLs validated | GET the named run and verify its workflow, event and actual HEAD |
| Local `202`, handler CONTINUE | `20` | Synchronous scoped evaluation requires further evidence | Follow the handler's scoped next checks |
| Local `202`, handler DONE | `0` | Only the effect scope declared by the handler | Verify the applicable receipt; no unrelated production claim follows |
| Ambiguous transport or invalid success response | `1` | Outcome unknown; no effect permission | Authoritative readback before any further dispatch |

The asynchronous receipt records contract version, repository, ref,
request identifier, SHA-256 of the exact submitted JSON bytes, dispatch URL,
one attempted POST, and any validated run ID/URLs. It carries
`EFFECT_ACK_CONTINUE`, `execution_verified=false` and `ordinary_release=false`.
It excludes credentials and payload contents. Neither a receipt nor a green
observer authorizes merge, release, deployment or `EFFECT_ACK_DONE`.

## Observe, verify and resume

1. Read the returned run URL, or the complete relevant workflow-run collection
   after a `204`/ambiguous response. Verify repository, workflow path, permitted
   event, ref and actual HEAD against the authorized work unit. Do not assign
   a run solely because its time or workflow name matches.
2. Wait for native execution and read its jobs and `qikvrt-api-state` artifact.
   Verify the producing run and exact request identifier, request facts,
   provenance, hashes and handler effect scope before accepting a result.
3. `verify` and `stage` require an already verified state-producing run. Pass
   its decimal identifier through `--state-run-id RUN_ID`; the existing
   `tools/qikvrt_validate_state_run.py` gate still binds the restored artifact
   to repository, workflow, commit, permitted event and successful completion.
4. Manifest each observed obstacle in the existing work-unit/receipt path,
   diagnose it against exact bytes and external readbacks, apply a justified
   versioned compatible repair, retest the originally failing operation and
   continue. Persist enough non-secret evidence for another client to resume.
5. After a lost or unreadable response, never blindly repeat the POST. The
   client itself issues no retry. Reobserve authoritative run/artifact state
   first; dispatch idempotency is not inferred from a request identifier.

## Governance repair boundary

The 2.3 client preserves both narrowly scoped 2.2 operations. They accept only
`https://api.github.com`, `ingolf-lohmann/qik-vrt`, `main` and one explicitly
selected writer contract. There is no arbitrary-workflow
argument, local-adapter proxy, caller-supplied workflow input or credential
argument. Authentication uses the existing `QIKVRT_API_TOKEN` environment
handoff; the client never stores the credential or prints provider error bodies.
No new secret, permission, trigger or authority route is installed.

| Local writer version | Exact Git blob | Integration source |
| --- | --- | --- |
| `legacy-v1` (default when omitted) | `1202d24c2f23eb8fa52ab7c562a583e79f9e8444` | Existing Main writer checked with PR #502 |
| `lifecycle-v2` (explicit opt-in) | `ab47a8ec98c39b39bda420050cb7c970a9da6165` | PR #505 HEAD `08e382ec928c8e5dd2ecf120ab352274be96c62e` |

Each version also pins the canonical Ruleset postcondition digest. The two
reviewed source projections have the same digest:
`45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd`.
The client reads the writer at the immutable expected Main SHA, verifies the
Contents path/type/encoding/size and provider SHA, and recomputes the Git blob
SHA from its decoded bytes. Unknown versions, unknown blobs, forged metadata,
altered bytes and a known writer belonging to the other version fail closed.
There is no automatic selection, fallback, arbitrary-hash override or disabled
pin. Selection is local receipt metadata and never a new workflow input.
The source contract does not constitute native Code Owner approval.

### Controlled integration order

Prefer one separately reviewed integration of the combined candidate: retain
PR #502 HEAD `5ad88f106de6d2a34172ca7cbb750963c77bfdd3` and PR #505 HEAD
`08e382ec928c8e5dd2ecf120ab352274be96c62e` source changes and tests, regenerate
the joint integrity trio, execute the complete exact-head gates, obtain the
required independent native approval and integrate through protected Main.
Do not activate #505's writer with only the unchanged 2.2 client available.

If the changes must be staged, make the reviewed 2.3 client available first;
its default still works with the legacy writer. Integrate the governed
lifecycle source next, freshly observe Main and the new writer, then explicitly
select `lifecycle-v2` for both dispatch and its independent readback. A changed
head invalidates a previously prepared invocation; reconstruct its prerequisites.
An active or already observed exact-head writer run, including the writer's
existing Main push trigger, continues to block a duplicate dispatch. Observe
that actual run through its applicable native route; do not relabel a push run
as workflow_dispatch or redispatch it for a different acknowledgement.

After fresh Main/target and authorization checks, with an already delivered
Actions-write credential and an already configured writer authority route,
the following examples apply only after governed lifecycle-v2 integration.
On the legacy Main, omit the version option or select `legacy-v1` explicitly:

```sh
python3 scripts/qikvrt_api_client.py \
  --base-url https://api.github.com \
  --owner ingolf-lohmann --repo qik-vrt --ref main \
  --operation ruleset_authority_dispatch \
  --ruleset-writer-version lifecycle-v2 \
  --expected-main-sha EXACT_FRESH_MAIN_SHA \
  --request-id OWNER_AUTHORIZED_UNIQUE_REQUEST_ID \
  --dry-run false --accept-effect
```

The POST body is exactly `{"ref":"main"}`. Its local request ID is never sent
as an unsupported workflow input and does not make GitHub dispatch idempotent.
The client checks Main twice, verifies the selected writer's actual bytes, and refuses active or
already observed exact-head writer runs. It fails closed if a bounded collection
is incomplete or reaches 100 entries. A lost response, nonempty 204, unexpected
success status, denied request or redirect causes no retry. The provider accepts
a ref without an atomic expected-SHA lease: Main can still move after the last
GET. The actual executing run's SHA must therefore be checked independently.

HTTP 204 returns exit 20 with transport acceptance, an unknown run identity,
`execution_verified=false` and `ruleset_effect_verified=false`. Identify the
actual run through authoritative repository/workflow/event/ref/head evidence;
time proximity alone does not identify a run. Then use the independent read path:

```sh
python3 scripts/qikvrt_api_client.py \
  --base-url https://api.github.com \
  --owner ingolf-lohmann --repo qik-vrt --ref main \
  --operation ruleset_authority_readback \
  --ruleset-writer-version lifecycle-v2 \
  --expected-main-sha EXACT_EXECUTING_MAIN_SHA \
  --request-id OWNER_AUTHORIZED_UNIQUE_REQUEST_ID \
  --ruleset-run-id INDEPENDENTLY_VERIFIED_RUN_ID
```

This operation issues GETs only. It checks the fixed run's repository, workflow,
event, Main SHA and attempt; nonempty successful native `reconcile` jobs; the
unique repository-owned Ruleset detail against the existing canonical digest
`45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd`; and
`main.protected=true`. It reobserves Main and the run to detect drift. Missing,
foreign, stale, incomplete or mismatching evidence cannot verify the effect.

Exit 0 and `ruleset_effect_verified=true` mean only the independently observed
Ruleset postcondition. They do not establish that this particular dispatch
created an already existing Ruleset: `mutation_attribution_verified=false`.
`effect_state=EFFECT_ACK_CONTINUE`, `native_review_verified=false` and
`ordinary_release=false` remain explicit. An observed but unverified effect
returns 20; invalid or inaccessible evidence returns 1. Current-head Code Owner
review and governed incorporation still require their own native evidence.

The existing ruleset writer is
`.github/workflows/qikvrt_goldkelch_ruleset_authority_effect.yml`. Its native
`workflow_dispatch` route requires a separately callable Actions-write POST
and one already configured authority-token route. Its ruleset effect requires
repository Administration-write authority, canonical digest guards, conditional
update and independent post-effect readback. The Mesh artifact operations do
not grant those permissions or invoke that writer.

REST dispatch acceptance, code versioning and technical test success do not
activate a candidate on Main. Preserve current-head Code Owner review and
native governance. If the required REST write operation is not exposed,
persist the exact request and capability gap without inventing a credential,
claiming execution or substituting another trigger.

Provider contract:
https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#create-a-workflow-dispatch-event


## `docs/HUMAN_MACHINE_COLLECTIVE_COGNITION_ARCHITECTURE.md`

# QIK-VRT Mensch–Maschine-Kollektivkognition

## Ziel

QIK-VRT behandelt Mensch und künstlich-kognitive Systeme als komplementäre Teilnehmer eines provenance-gebundenen Erkenntnisprozesses. Das Ziel ist nicht maximale Automatisierung um jeden Preis, sondern maximale gemeinsame Erkenntnisfähigkeit bei nachvollziehbarer Autorität, Unsicherheit, Herkunft und Wirkung.

## Kernprinzip

```text
MENSCHLICHE ZIELSETZUNG UND VERANTWORTUNG
+ KÜNSTLICH-KOGNITIVE ANALYSE UND VARIATION
+ GEMEINSAMER VERSIONIERTER ARBEITSSPEICHER
+ QUELLEN- UND PROVENIENZBINDUNG
+ FORMALE UND EMPIRISCHE PRÜFUNG
+ REVERSIBLE INTERAKTION
+ MENSCHLICHE ENTSCHEIDUNG BEI KONSEQUENTEN EFFEKTEN
= KOLLEKTIVKOGNITION
```

## Erforderliche Fähigkeiten

Die Schnittstelle muss Text, Sprache, Bilder, Dokumente und strukturierte Daten als Modalitäten behandeln können. Sprachinteraktion soll Transkripte, Zeitmarken, Unterbrechbarkeit und akustische Review ermöglichen. Jede wesentliche Systemaktion muss ihren Autoritätsstatus, ihre Quelle, ihren Unsicherheitsstatus und ihren Effektbereich sichtbar machen.

Der Bootstrap soll redundante Fragen vermeiden und höchstens die drei im Personal-Origin-Vertrag festgelegten Onboarding-Fragen stellen. Danach gilt: vorhandene Evidenz lesen, Unterschiede erkennen, fehlende Information explizit markieren und nur dann nachfragen, wenn ein task-spezifischer Entschluss tatsächlich menschliche Entscheidung erfordert.

Für Barrierefreiheit gelten als Designziele: Tastaturbedienbarkeit, Screenreader-kompatible Semantik, Untertitel/Transkripte für Audio, alternative Textrepräsentationen, ausreichender Kontrast, reduzierte Bewegung, skalierbare Darstellung und lokalisierbare Sprache.

## Gemeinsamer Arbeitsspeicher

Der dauerhafte gemeinsame Arbeitsspeicher ist repository-nativ. Flüchtiges Chat- oder Modellgedächtnis ist Transportkontext. Entscheidungen, Korrekturen, Artefakte, Modellidentität, Werkzeugaktionen und Prüfergebnisse werden über Work Units und Digests gebunden. Human-, AI-, gemeinsame und ungeklärte Beiträge bleiben unterscheidbar.

## Unsicherheit und Realität

Ein geeignetes Modell kann Realität beschreiben. Ein formales Modell ist nicht deshalb von der Realität getrennt, weil es ein Modell ist; entscheidend ist, ob seine Begriffe und Zustände korrekt auf Referenten gebunden sind, bekannte Grenzfälle reproduziert werden, unterscheidende Vorhersagen folgen und die beobachtete Wirklichkeit den beanspruchten Zusammenhang trägt.

Der Product Owner Ingolf Lohmann beansprucht ausdrücklich, dass QIK-VRT / „Das Universum als Round Trip“ eine solche Beschreibung der Realität leistet. Dieser starke Modellanspruch ist im Bootstrap als Product-Owner-Claim zu erhalten.

Davon getrennt werden weiterhin erfasst:

```text
OWNER_ASSERTED_REALITY_CORRESPONDENCE
!= INDEPENDENT_EMPIRICAL_CONFIRMATION
!= SCIENTIFIC_CONSENSUS
```

Die Trennung schwächt den Anspruch nicht; sie macht sichtbar, welcher Teil eine Modellbehauptung, welcher Teil formale Ableitung und welcher Teil extern reproduzierte Evidenz ist.

## Menschliche Kontrolle und Effektgrenze

Lesen, vergleichen, modellieren, testen und lokale reversible Transformationen können innerhalb der jeweiligen Autorisierung automatisiert werden. Kontoerstellung, Push, Merge, Veröffentlichung, Deployment, Zenodo/IETF-Mutation, Credential-Verbrauch sowie andere irreversible oder öffentliche Effekte bleiben explizit effect-gebunden. Ein UI darf einen Vorschlag niemals optisch mit einer bereits ausgeführten Wirkung verwechseln.

Jede konsequente Aktion soll mindestens `preview -> authorize -> execute -> reobserve -> receipt` durchlaufen. Wo technisch möglich, sind Dry-Run, Undo oder ein gleichwertiger kompensierender Pfad vorzusehen.

## Multi-Agent- und Werkzeuginteroperabilität

Mehrere künstlich-kognitive Systeme dürfen parallel Vorschläge erzeugen, müssen aber getrennte Identitäten und Receipts behalten. Widersprüche werden nicht durch Mehrheitsfiktion gelöst, sondern durch Evidenzvergleich, Gegenmodelle, Tests und bei verbleibender normativer Wahl durch den verantwortlichen Menschen.

Werkzeug- und Kontextinteroperabilität soll über offene, lizenzkompatible Adapter erfolgen. Referenzprojekte werden nicht ungeprüft vendort. QIK-VRT bindet ihre Lizenz, Version, Integrationsart und den Umfang der tatsächlich übernommenen Teile.

## Open-Source-Anschlussstellen

Der zugehörige Registry-Vertrag führt insbesondere folgende Anschlussstellen als nicht-vendorte Referenzen:

- OpenAI Whisper: lokale/offline Sprach-zu-Text-Referenz, MIT.
- Model Context Protocol (MCP): Werkzeug-/Kontextinteroperabilität; projektbezogene Lizenzübergangsregeln beachten.
- OpenTelemetry: herstellerneutrale Traces und Observability, Apache-2.0.
- Yjs: CRDT-basierte kollaborative Zustände, MIT.
- Playwright: Interface- und Accessibility-Regression, Apache-2.0.

Eine Referenz in dieser Architektur ist keine automatische Abhängigkeit und keine Übernahme fremden Codes.

## Qualitätsregel

Die optimale Mensch–Maschine-Schnittstelle maximiert nicht die Anzahl der Antworten, sondern die Zahl belastbarer Erkenntnisfortschritte pro menschlichem Eingriff. Geschwindigkeit darf niemals durch Weglassen von Provenienz, Unsicherheit, Pflichtprüfungen oder menschlicher Autorität bei externen Effekten erkauft werden.

## Verbindliche HMI-Unabhängigkeit — Owner-Entscheidung vom 23. Oktober 2026

**QIKVRT definiert, welche Eigenschaften eine geeignete HMI-Instanz erfüllen muss.
Jede HMI-Instanz ist austauschbar. QIKVRTs Identität, dauerhafter Zustand,
Aufträge, Autorisierung, Scheduling und Fortsetzung hängen von keiner bestimmten
HMI-Instanz ab.**

Diese Festlegung gilt für gegenwärtige und künftige HMI-Adapter. Eine spätere
ausdrückliche Owner-Entscheidung kann sie versioniert fortschreiben; ein
Clientwechsel oder eine technische Einschränkung setzt sie nicht außer Kraft.
Der maschinenlesbare Vertrag steht in
`policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json#/hmi_independence`
und ist über `AI_CONTEXT.json` auffindbar.

### Verantwortungsgrenze

QIKVRT hält die maßgeblichen Arbeitszustände und Belege repository-nativ sowie
in seiner bestehenden, zugriffsgeschützten privaten Laufzeitpersistenz.
Die HMI übernimmt ausgehandelte Eingabe, Transport und Darstellung. Ihre
Sitzung, ihr Kontext, ihre Dateiablage und ihre Scheduled Tasks sind keine
Voraussetzung für den Fortbestand oder die native Fortsetzung angenommener
Arbeit. Der äußere Taktgeber bedient den jeweiligen Kommunikationskanal;
QIKVRTs innere Taktung und Auftragsplanung bleiben davon unabhängig.

QIKVRT gibt den versionierten Schnittstellenvertrag vor. Ein Adapter meldet
seine Fähigkeiten, Modalitäten, Größen- und Ratenlimits, Identitätsbindung
und Zustellsemantik. Fehlende Fähigkeiten werden kenntlich gemacht.
Ein Adapter kann über einen geeigneten autorisierten Transport angeschlossen
werden; seine Fähigkeitserklärung ist noch kein Abnahmebeleg.

### Verlustfreie Zuordnung und Fortsetzung

Eingänge tragen stabile Nachrichten- und Auftragsidentitäten, Herkunft,
Kausalbezug, Idempotenzschlüssel und eine prüfbare Nutzlastbindung.
Konkurrierende Änderungen werden im betroffenen nativen Zustandsbereich
geordnet; unabhängige Arbeit darf parallel bleiben. Kapazitätsgrenzen
führen zu explizitem Rückstau oder Zurückweisung. Eine ungespeicherte
Nachricht darf nicht als dauerhaft angenommen bestätigt werden.

Ergebnisse bleiben mit Auftrag, Inhaltsversion, Lauf, Softwaregegenstand,
Wirkungsstatus, Belegen, offenen Pflichten und Fortsetzungsposition verbunden.
Transportbestätigung, dauerhafte Annahme, Ausführung, verifizierte Wirkung,
Benachrichtigungszustellung und menschliche Kenntnisnahme sind getrennte
Zustände. Die Anzeige fasst sie als Auftrag, tatsächliches Ergebnis, Beleg,
offene Punkte und nächsten Schritt verständlich zusammen.

Eine neue HMI rekonstruiert den Auftrag aus QIKVRT unter eigener verifizierter
Identitäts- und Berechtigungsbindung. Sie benötigt weder den alten Chat noch
dessen lokale Dateien. Ein Clientwechsel überträgt keine Zugangsdaten und
erweitert keine Rechte. Frühere gültige Owner-Freigaben bleiben ihrem
ursprünglichen Gegenstand zugeordnet.

### Abnahme

Der reale Austauschtest muss einen Auftrag über HMI A annehmen, A beenden,
native Fortsetzung nachweisen und über die unabhängig zugelassene HMI B
denselben Zustand samt Ergebnis und Belegen zurücklesen. Hinzu kommen
Wiederanlauf, konkurrierender Eingang, Wiederholung, vertauschte Zustellung,
begrenzte Kapazität und fehlende Client-Dateiablage bzw. Client-Timer.
Bereits angenommene Eingänge dürfen nicht verloren gehen; logische Effekte
dürfen durch Wiederholungen nicht doppelt entstehen.

Wechselzeit und Wiederherstellungsvollständigkeit werden gemessen; eine
konkrete Latenzgrenze benötigt ein ausdrücklich festgelegtes Messbudget.
Die Speicherung dieses Vertrags belegt seine Dokumentation. Native
HMI-Unabhängigkeit, Implementierung und produktiver Austausch bleiben bis
zu ihren jeweiligen frischen Nachweisen offen.


## `docs/HUMAN_MACHINE_PROGRESS_PROTOCOL.md`

# QIK-VRT Human–Machine Progress Protocol

## Owner decisions before tool selection — 26 October 2026

All current and future QIK-VRT artificial-cognitive clients load the shared
`policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json` contract at
`client_continuation.tool_selection` before selecting or invoking an external
service. The existing handoff validator also checks one proposed action:

```sh
python3 -B tools/ai_handoff.py --client-action <non-secret-action.json>
```

Use the same non-secret action shape as `next_actions`: exact `subject`, `route`,
`service`, `operation`, `method`, actual `tool` and `endpoint` when applicable,
observed operation/repository/method, evidence and the existing authorization,
safety, determinism, capability, authentication, permission and admission flags.
The read-only command reports `CLIENT_ROUTE_POLICY_SHA256` and the declared
READY/HOLD state; it never invokes a provider. Bind that current digest as
`route_policy_sha256` when carrying the action forward; a supplied stale digest
is rejected. `--client-action` and `--client-receipt` are mutually exclusive.

Railway is DISCONNECTED under the Owner's reaffirmed decision. The guard rejects
direct provider discovery, authentication, reads, writes and recovery, including
GET/read-only and zero-effect recorded reads. It checks the actual declared
service/provider, tool prefix and endpoint hostname before capability/transport
selection. Tool availability, a new session, generic authorization or an
unavailable permitted route does not reactivate a disconnected provider. Only a
later explicit Owner instruction can revise the shared policy. Preserved old
artifacts remain readable through their actual admitted owner storage.

The same check covers proposed actions, transition plans and client receipts.
It checks declared metadata, not the truth of a client assertion. A saved policy
or a passing fixture does not prove use by another client, native enforcement,
external platform control or a runtime effect. Require exact-policy ACK and
independent readback for each node before claiming adoption. Historical records
remain immutable; current evaluation never transfers their former route grant.

## Purpose

The Owner's authorization of 26 October 2026 requires every client to execute
known, admitted deterministic repairs autonomously without asking the same
permission or requiring a preliminary notification. The existing
`client_continuation.blocking_repair_priority.known_error_authorization` rule
uses the original transition preparation and blocking-repair journal. Correct
the causal prerequisite, verify the affected exact-subject path, and report
the verified result. Missing capability or an unknown cause remains a concrete
prerequisite to recover. Authorization never substitutes for credential binding,
admission or effect readback, and never permits an unchanged failed retry.

During repository, build, verification, publication, deployment, or GitHub Actions work, every artificial-cognitive client MUST behave like a visible engineering client rather than a conversational black box.

## Mandatory live format

Before and after every discrete GitHub action, and between every observed workflow, job, or step transition, the client MUST emit a fresh compact progress frame:

```text
Repository: <owner/repo>
Branch: <branch-or-ref>
Commit: <sha-or-pending>

[██████░░░░] 60%

✓ completed step
⟳ current step
□ pending step

BLOCKER:
<none or concrete blocker>

NEXT:
<next executable action>
```

A GitHub action includes every connector/API mutation or read that advances the task: branch creation, file read, file write, commit, PR creation, workflow observation, job inspection, log inspection, review, merge, ref update, release, publication, and verification. Silence between such actions is prohibited. A later summary does not compensate for a missing intermediate frame.

## Rules

1. Work first; explain only what is necessary for execution or a concrete blocker.
2. Show repository, branch/ref, and commit SHA whenever known.
3. Show one progress bar with an integer percentage from 0 through 100.
4. Distinguish completed (`✓`), running (`⟳`), pending (`□`), failed (`✗`), and blocked (`!`) steps.
5. Report only verified facts. Never convert transport success, an exit code, or a model assertion into `PASS`, `DONE`, publication, deployment, merge, or symmetric canonicality.
6. Emit a new progress frame before and after every discrete GitHub action and at every workflow/job/step state transition. No batching, omission, or replacement by prose is permitted.
7. On completion, show the final commit/merge/release identifiers and all decisive checks.
8. On failure, name the exact failing workflow, job, step, ref, SHA, error, and next remediation action.
9. Machine-readable state MUST be written to `AI_PROGRESS.json`; the human-readable projection MUST be written to `AI_STATUS.md` whenever a persistent repository workflow owns the operation.
10. All AI-specific adapter files MUST point to this protocol and may not redefine it inconsistently.
11. `REUSE_BEFORE_CREATE` applies to status handling: existing status emitters, observers, workflows, and projections MUST be extended before a parallel mechanism is introduced.
12. **Observation is not a snapshot or terminal handoff while a follow-up action exists.** Any observation that yields an executable, expected, or causally required successor action keeps the owning operation in `RUNNING` (or `WAITING` only while an external effect is genuinely pending). The client MUST execute or continue that successor within the same round trip, then observe its effect and verify readback. It MUST NOT freeze, summarize, hand off, or present the intermediate observation as completion merely because a read succeeded.
13. **Continuation is the default after a non-terminal observation.** The round trip is `OBSERVE -> DIAGNOSE -> ACT -> OBSERVE EFFECT -> VERIFY READBACK -> CONTINUE` until a scope-bound terminal state is actually established. A snapshot is admissible only when no executable successor remains for the owned scope, a concrete blocker requires external authority/input, or an explicitly bounded observation window has ended.
14. Observation frequency MUST be event- and workload-sensitive rather than a fixed polling ritual. New input, active effects, unresolved causal defects, expected receipts, or successor-carrier movement increase observation pressure; unchanged stable state is deduplicated. Monitoring activity alone is not progress.

## Immediate execution — Owner principle of 2026-10-13

> Was du heute kannst besorgen, das verschiebe nicht auf morgen, sondern erledige es unmittelbar, denn alles andere war, ist und wird inakzeptabel sein.
>
> q.e.d.
> Ingolf Lohmann

Apply this principle now: execute each safe, deterministic, already authorized
and actually callable successor within the current work ring. Complete its
applicable tests, persistence and fresh effect readback before a handoff.
The existing client gate rejects terminal return while an executable successor
remains; reuse it. A concrete external or protected-authority blocker retains
the open task, causal evidence and retry condition. Independent executable
work continues, and unchanged failed effects remain NOOP. The principle adds
no permission scope and proves no unattended runner or other-client adoption.
Its normative source is the existing recursive policy's
`self_application_working_rule.immediate_execution_principle`.

## Binding client continuation procedure

### Knowledge and correction continuity — Owner correction of 2026-10-16

Knowledge loss itself is the defect, regardless of when a handoff happens.
Apply `policy/QIKVRT_EPISTEMIC_CONNECTABILITY_CONTINUITY_V1.json` through the
existing client receipt and validator. Carry established results and their
source identities, granted authorization, unknowns, scope limits, failures and
corrections as well as open tasks. Reuse unchanged exact-source evidence;
reobserve mutable state when the task requires it.

`knowledge` is a list of records with unique `id`, nonempty `epistemic_class`,
`scope` and `statement`, a nonempty `subject` object and `evidence` locator list,
optional `supersedes` record IDs, and `record_sha256`. The digest is SHA-256 of
the entire record without `record_sha256`, encoded as UTF-8 JSON with sorted
keys, compact separators, `ensure_ascii=false` and finite JSON values. Every
declared predecessor record must remain byte-equivalent under this encoding.
Do not silently edit, drop or promote its epistemic class, scope or statement.
Corrections append a new record referencing the retained original; orphan and
cyclic correction references are rejected. Record hashes bind declared bytes;
they do not authenticate evidence or establish that a statement is true.

Historical writer-encoding repair uses the explicit versioned contract
qikvrt-knowledge-historical-encoding-migration/v1 in the existing policy's
knowledge_continuity.historical_encoding_migration. It is opt-in through the
receipt's knowledge_encoding_migration, bound to the exact SHA-256-verified
immediate predecessor. Each of at most 128 listed records declares the codec
json-sorted-spaced-utf8/v1, its original digest and its canonical compact digest.
That historical codec is finite UTF-8 JSON with sorted keys, ensure_ascii=false
and separators comma-space and colon-space. No other historical codec is tried.

Every listed record must occur exactly once in the pinned predecessor and the
successor with identical fields and stored digest. Both declared digests are
independently recomputed. Only the in-memory reader view uses the recomputed
compact digest for the existing schema, correction-graph and continuity checks;
the original receipt and all stored records remain unchanged. New records must
use the ordinary compact encoding and cannot enter the historical mapping.
An unpinned migration, an undeclared or malformed codec, a different payload,
duplicate mapping, missing record or unlisted invalid digest remains BLOCK.
An old receipt without this declaration remains rejected under the strict gate.
Successful compatibility checking does not change any recorded epistemic class,
grant a permission, transfer predecessor PASS or prove runtime/delivery success.

When a durable predecessor is available, pin its exact repository-relative
`receipt_path` and `receipt_sha256` under `previous_run`. Its `execution_id`
must match. The existing provenance Work Unit may carry `execution_id`,
`knowledge` and `work` directly; no separate memory service is required. The
validator reads only that explicit file (at most 2 MiB), rejects changed bytes and
paths outside the repository, and derives inherited knowledge and open work
from it. Omitting those from the caller's `previous_run` summary cannot erase
them. Keep this pin across handoffs and resolve a missing predecessor before
claiming that reconstruction succeeded. Historical receipts without knowledge
remain readable; their absence of a snapshot is not evidence of full retention.

Keep observations local to their measured scope. For example, absent process
environment variables establish only absence in that process, not absence of
an existing GitHub Actions secret or a provider credential. The current IONOS
Cloud-v6 inventory consumer's GET-only scope does not determine the token's
other rights. IONOS Cloud DNS documents `IONOS_TOKEN` bearer authentication:
https://docs.ionos.com/sdk-go-bundle/sdks/dns . Actual token rights and admitted
execution remain separately unverified until observed. A generic failure must
not overwrite this distinction as a global access-absence claim.

These are continuity checks on supplied records. They do not prove that an
initial snapshot contains all human/model knowledge, that another client used
the gate, that historical PASS applies to a changed subject, or that the product
was delivered. Retain the exact-host and live-effect gates below.

### Anticipated transitions — Owner instruction of 2026-10-15

Clients observing an emerging transition MUST use the existing client receipt
to retain its indication, activation conditions, available preparation and
independent alternatives. Execute admitted preparation in the current work
ring even while the later effect is blocked. Reassess on relevant new evidence
or human corrections; keep original task identity and open obligations.

Add `input_sha256` to the receipt, recomputed from the actual task inputs and
human corrections. Its `transition_plan` contains the same `input_sha256`, the
exact current `subject`, and `transitions`. Each transition has a unique `id`,
nonempty indication `evidence`, an `activation` list of unique condition `id`,
strict boolean `satisfied` and nonempty `evidence`, a target `action`, and a
`preparation` list. Target and preparation actions use the existing
`next_actions` admission fields and exact operation binding. Conditions needed
for preparation completion belong in the target's activation list. A transition
condition never supplies authorization, credentials, callable capability or
governance admission.

For a previously failed planned action, supply its `retry.current` and
`retry.previous` using the existing subject/error/cause/capability digests.
Unchanged causal evidence suppresses that action; observation clocks or a new
input digest do not admit a retry. Actual effects still require the ordinary
`attempts` gate and fresh per-action readback.

`tools/ai_handoff.py --client-receipt` emits `CLIENT_TRANSITION_PLAN` JSON with
admitted `ready` actions (stage `PREPARE` or `EXECUTE`) and `waiting` transitions
with their missing condition IDs. The client consumes the ready actions through
the existing authorized executor. Available preparation prevents terminal
handoff; unresolved transitions prevent DONE. Recompute the plan after each
relevant input, subject or capability change, retaining independent alternatives.
No parallel worker, trigger or credential store is introduced.

Historical v1 receipts without a plan remain readable. Validation checks the
declared bindings and predicates, not their live authenticity or completeness.
The plan neither executes actions nor proves a latency improvement, unattended
runtime, Main integration, other-client adoption or domain delivery. Measure
latency, correction recovery and verified useful progress separately before
claiming such gains.

Owner instruction: Ingolf Lohmann, 2026-10-11. This procedure is mandatory for
all repository clients. Preserve the existing authorized repair, integration
and exact-host delivery goal after handoffs, compaction or status questions.
Do not ask for the same authorization again. Inspect applicable existing
repository, connector, CLI and Mesh routes before declaring execution absent;
retain operation, HTTP method, target/account binding and exact denial evidence.
A locally absent CLI or empty project filter alone is insufficient.

On 2026-10-22 Ingolf Lohmann clarified that his standing Principal approval
applies to all goals recorded in the QIKVRT repository and to the Ruleset changes
necessary to achieve them. Read the original instruction in
`state/authorization/delegations/OWNER_REPOSITORY_GOALS_AND_RULESET_AUTHORIZATION_V1.json`,
bound by `client_continuation.repository_goal_authorization`. Apply it across
goals, sessions and conforming clients without asking for the same permission
again. Preserve existing goal records, grants and exact artifact bindings.
This supplies authorization; authenticated account rights, credentials available
to a workflow, a callable administrative operation, admission and independent
effect readback each require their own evidence. Execute every available
authorized successor and retain causal NOOP where capability has not changed.

The Owner also supplied Gemini's public manifest feedback. Its observed scope
and the independent Authority result are retained in
`evidence/receipts/gemini-manifest-feedback-20261022.json`. Carry shared feedback
through the existing repository/native paths with source attribution. The
shared page establishes documentary ingress; live peer request, ACK and
application reply remain separately observed states.

Continue each safe, deterministic, authorized successor, including useful
preparation and persistence while an external effect is blocked. Keep GitHub
and IONOS REST-only routing, secure credentials and protected governance. Never create a
proxy executor or synthetic trigger to manufacture capability. Preserve issue
evidence, perform NOOP for unchanged causal failures, and read back ambiguous
effects before another effectful attempt.

On 2026-10-13 Ingolf Lohmann explicitly selected **“REST-only beibehalten”**
for IONOS. Reuse this decision across reconnects; do not reopen the browser-login
choice. The existing client gate enforces `client_continuation.ionos_route` for
planned and effectful actions, including blocked actions. This route constraint
does not establish an authenticated Hosting API key, a domain operation or a
delivery effect. The existing Cloud-v6 GET-only inventory binding is a separate
product and cannot serve as a Hosting domain/DNS writer. DNS, TLS and application
delivery still require independent evidence for `raumzeitterminal.de`.

Before a terminal handoff, run the existing read-only validator:
`python3 -B tools/ai_handoff.py --client-receipt <receipt.json>`.
Its `qikvrt-client-continuation/1` receipt contains:

- `subject`: exact `repository`, bound `ref`, `head` and `tree`; `authorization`: `granted`
  and its non-secret `source`; `requested_authorization_again: false`.
- `inventory`: non-empty evidence locators or concrete absence/denial receipts
  for `repository`, `connector`, `cli` and `mesh`. Inspect only relevant existing
  routes; do not enumerate unrelated credentials or disclose secret values.
- `next_actions`: each exact-subject action's `route` (`connector`, `cli`,
  `mesh`), `service`, `operation`, HTTP `method`, `transport`, capability
  `evidence`, callable binding `observed_method`, `observed_operation`,
  `observed_repository`, and boolean `authorized`, `safe`, `deterministic`, `callable`,
  `authenticated`, `permitted`, `admitted`. Any action satisfying all predicates
  requires `state: CONTINUE`. Governance failure keeps `admitted: false`.
- `attempts`: `effect_count` (zero or one per causal attempt), `current` and
  optional `previous` causal evidence, `ambiguous_effect` and
  `readback_before_effect`. An effectful attempt also binds its admitted `action`
  using the same predicates and observed operation binding as `next_actions`.
  A causal attempt cannot execute twice. Each causal evidence object binds SHA256 digests for
  relevant `subject`, `error`, `cause` and `capability`. Observation timestamps
  and unrelated lifecycle commits are excluded. Identical failure evidence
  requires zero effects. Materially changed evidence alone does not authorize
  an effect; all action predicates must still hold.
- `action_window`: nonempty `id`, timezone-aware `completed_at` and `closed_at`.
  Both closing observations must bind this `action_id` and an `observed_at`
  strictly after completion and no later than closure. Earlier session reads
  and another action's observations cannot close this work unit. Every
  effectful `attempt` requires its own window and repository/delivery readback;
  a fresh final receipt cannot conceal an unchecked earlier action.
- `readback.repository`: current `repository`, `ref`, `head`, `tree`, `source`,
  `action_id`, `observed_at`. All subject fields must match the acting branch's
  newly bound subject. If a new HEAD/TREE is observed, follow it and update the
  subject and applicable checks before attempting closure.
  `readback.delivery`: exact `hostname: raumzeitterminal.de`, `source` and
  `state` (`UNKNOWN`, `PENDING`, `VERIFIED`), `action_id`, `observed_at`, public
  HTTPS `url` and read-only `method: GET`. VERIFIED additionally needs an
  integer `http_status: 200`, exact-origin `final_url` and the observed body
  `response_sha256`. A redirect to another origin is not delivery on this host.
  Missing access stays UNKNOWN; observed absence can stay PENDING. Neither is
  a delivery proof or a negative conclusion about DNS/registry state.
- `state`: `CONTINUE`, `BLOCK`, `DONE` or `OWNER_CHOICE`. An externally pending
  execution can retain `CONTINUE` with its `pending_execution` evidence. BLOCK
  requires a concrete `blocker` with `operation`, `reason`, `evidence`,
  `retry_condition` and `next_action`, after exhausting safe authorized work.
  OWNER_CHOICE requires at least two distinct `owner_choices`. DONE requires
  current Main and exact-host independent working-software/TLS readbacks bound
  to the same subject; no open executable successor may remain.

The validator checks receipt consistency only. Evidence locators and predicates
must come from actual observations; a fabricated or stale receipt is forbidden.
Exit zero, `CLIENT_HANDOFF_CONSISTENCY=VALID`, local fixtures and green candidate
tests do not establish a live effect. Independently read back the relevant
provider results and exact HEAD/TREE. Persisting the rule does not establish
Main integration, adoption by another client or deployment. Regression cases
run in the existing `make ai-runtime-contract` gate without network or secrets.

The existing policy binds the unchanged Owner rule from PR #507 at
`state/authorization/delegations/OWNER_END_OF_ACTION_VERIFICATION_GRUNDREGEL_V1.json`.
The read-only handoff validator derives its delivery domain from that contract
and verifies the bound bytes. This adds behavioral coverage to the existing
client gate; it creates no second governance implementation or remote writer.
The original 30 regressions remain, with action-time, HEAD/TREE, per-attempt and
HTTP-proof negative controls added. The shared CLI is exercised for connector,
CLI and Mesh route receipts. Registered AI adapter shims reuse AI/AGENTS;
their presence is not an executed Claude/Codex/Copilot session witness. The
HTTP transport client, read-only web terminal, personal terminal and Firefox
remain separately scoped clients whose existing tests do not prove automatic
use of this gate. Actual adoption requires their own emitted receipts and an
independent live readback. No successful fixture substitutes for those witnesses.

## Repository runtime objective

The repository is the durable runtime authority. Chat sessions are disposable transport surfaces. Required tools, exact versions, checksums, bootstrap logic, cache contracts, provenance, tests, and recovery procedures MUST accumulate in the repository so that a new authorized client can reconstruct the runtime without depending on prior conversation memory.

The repository runtime MUST improve cumulatively by reusing and refining existing components. Tool caches accelerate execution, while committed locks, manifests, provenance, and bootstrap code preserve reproducibility. Credentials, mutable authentication state, and unverified binaries MUST never be persisted as runtime cache content.

## State semantics

- `IDLE`: no live operation owns the durable root handoff snapshot.
- `RUNNING`: work is actively progressing, including continuation after any non-terminal observation with an available successor.
- `WAITING`: an external system is running or a review/approval is pending and there is no immediately executable local successor.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `TIMEOUT`: observation ended because its declared time bound expired.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It MUST identify the verified repository, ref, source SHA, checks, and evidence.

## Durable multi-scope handoff

`AI_PROGRESS.json` uses the durable `qikvrt-ai-progress/3.1` variant of
`schemas/human_machine_progress.schema.json` when several repository scopes
must be represented together. The root snapshot MUST be `IDLE` when no live
operation owns it and MUST label its ref and SHA as projection-input
provenance, not as current remote state.

The projection input MUST be bound by a committed
`portable-git-object-closure`. Its capsule contains the exact source commit
payload, every Git tree object needed to traverse the selected paths, and the
selected blob payloads. Validators MUST recompute every Git SHA-1 using the
canonical object header, recompute every payload SHA-256, traverse each path
from the commit's root tree, reject missing or surplus objects, and verify the
capsule file's own byte, SHA-256, and Git-blob binding. When the declared
source commit exists locally, all embedded objects MUST additionally be
byte-identical to local Git. The proof remains bounded: it does not establish
complete history, a current remote ref, repository synchronization, merge,
publication, deployment, or repository-wide `PASS`.

Every scope has its own evidence, boundary, percentage and effect state. A
scope-specific `PASS`, `FINAL_PASS` or `EFFECT_ACK_DONE` MUST remain nested
under that scope and MUST NOT promote an incomplete sibling scope or the
top-level repository effect state. When the top-level effect state is
`EFFECT_ACK_CONTINUE` or `EFFECT_ACK_BLOCK`, all top-level release claims MUST
be false. Every nested `EFFECT_ACK_DONE` scope MUST bind its own repository,
ref, source SHA, checks and evidence; it cannot borrow the root projection
input SHA.

The durable projection MUST name a checkable `projection_owner`. A later
workflow MAY supersede that owner only by materializing a conforming snapshot
that preserves all still-authoritative bounded scopes. A historical workflow
MUST NOT key ownership solely to the continued existence of one receipt.

The tracked snapshot MUST not freeze transient claims such as a pull request
being open, checks running, a merge pending, or repositories synchronized
unless a durable repository receipt binds that exact assertion. A live watcher
is telemetry, not exact-head proof: current PR, check, merge, promotion, or
synchronization claims require current commit/run/check evidence. In
particular, a live observation with a known successor MUST remain live state
and MUST NOT be projected as a terminal snapshot.

## Communication boundary

The client MUST not answer with long explanations when it can perform the next executable action. Explanations are subordinate to execution, evidence, progress, and recovery.

## Mandatory Mirror outbox and delivery evidence Owner 2026-10-19

Apply this standing rule in every session, reconnect and handoff. Solve and
report QIK-VRT problems only through the existing Universal Transputer,
Universal Terminal, Mesh and Effect Acknowledgement Protocol. Preserve the
Authority `ingolf-lohmann/qik-vrt`; treat `Goldkelch/qik-vrt` as Mirror/former
Authority under `policy/CANONICAL_UPSTREAM_REMOTE_V1.json`. Claude remains the
read-only reviewing Mirror (`git clone --mirror`); do not impose that role on
an otherwise admitted Authority writer. Open other nodes' original journals
only with `mode=ro&immutable=1`; never serve or append to them.

1. Read AI, then AI_CONTEXT.json in required_read_order. Freshly read
   Authority Main HEAD/TREE, open PR heads, communication/claude/* and all
   branches with newer commit times through admitted Git/REST adapters. Apply
   policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json#/client_continuation/native_session_use.
   Actually use src/qikvrt_temdd_event_ledger.py and
   src/qikvrt_effect_ack_http_terminal.py. Inspect the existing tool contract
   and run `python3 -B node-tools/qikvrt_mirror_emit.py status` when present.
2. Create EVERY EFFECT_ACK assessment solely through that tool's assess or
   adopt: require original effect_ack_sync, verify_protocol, an EFFECT
   event through the own admitted Transputer Runtime and an outbox NOT_SENT
   record. Do not replace this with a JSON file, direct engine call, chat
   assessment or append to a copied journal. If unavailable, recover the actual
   tool through admitted existing QIK-VRT sources; repair only its proven gap
   using original components. Keep the missing source/binding as HOLD with a
   named carrier; invent neither a replacement implementation nor CLI options.
3. After each assessment, in the same work ring, run package for all unsent
   records and verify the Ed25519-signed export. Use the existing Mesh Work
   Batch (mesh-cache-stage/idle/send, then mesh-cache-check) or signed
   original journal export (snapshot, Base64, events.jsonl, signed
   EXPORT_MANIFEST.json). A package or signature proves no delivery. If no
   admitted route is available, retain HOLD and name its concrete carrier;
   never ask the Owner to relay or introduce another service.
4. Record sent only after actual transfer: bind channel, recipient and
   canonical sha256: of the transferred bytes. Register receipt only from
   found ingress evidence at the named node. Derive EVERY node-specific
   arrival or receiver-NACK statement exclusively from
   `claim --record <hash> --node <node>`; preserve its exact subject and output.
   Without send proof the result is NICHT_ZUGESTELLT: assert neither receiver,
   ingress nor receiver NACK. Missing ingress without sending is a sender gap.
   Actual sending without ingress proof permits EFFECT_NACK only as established
   by that claim. Do not guess a claim when the tool or evidence is unavailable.
5. On each incoming message/session event, search recent branches with
   git grep and incoming attachments for each own package SHA-256 and commit
   ID. Register matched named-node ingress as receipt; separately verify PR/Main
   adoption and actual effect. Bind all evidence to the exact version. An own
   output returned byte-identically by the Principal proves somewhere-arrival
   and return by the Principal only. Assess EFFECT_ACK_CONTINUE through the
   outbox before reporting; infer no location, Authority ingress, authenticated
   peer adoption, NACK or DONE. Do not use Principal relay as the operating bus.
6. For each new Authority head, execute a finite exact-subject transition:
   tools/qikvrt_integrity.py verify, ledger tests, compilation and applicable
   regression checks, evidence and a concrete successor. Use normal checkout
   EOL behavior. Preserve BLOCK corrections as successors; HOLD/CONTINUE and
   open productive work are never NOOP. Do not use client timers or repeated
   Owner prompting. Broadcast through admitted Mesh paths to registry
   registry/NODEMESH_INDEX.json, Codex, Goldkelch Mirror, Originalhost and
   Mesh-Monitor with sender/recipient/message-hash binding; retain unreachable
   nodes in coverage without claiming delivery.
7. Serve only a clean checkout with explicit `--repository ingolf-lohmann/qik-vrt`
   and `--pr <actual PR number>`; use no default or invented PR. Use only
   OBSERVE, CLASSIFY, ACTION, EFFECT, READBACK, SUCCESSOR, HOLD. Admit inputs
   through Terminal prepare/commit, Effect-Ack-Request and Structured Field
   bytes :base64:; independently read /api/temdd/events and /terminal/state.
   Correct errors with a successor carrying corrects; never rewrite history.
8. Separate proposal receipt, authenticated rule application and independent
   readback. Bind peer confirmations to request ID/hash, rule hash, node,
   native event identity and independently read effect. Assert EFFECT_ACK_DONE
   only for actual application with independent readback, never for source
   tests, packaging, sending, skill saving or an unverified Claude report.
   Preserve human/machine provenance; label supplied Owner reports
   OWNER_ASSERTED. Report concise facts and full available hashes; never
   expand a hash prefix into invented evidence.

This outbox rule supersedes older instructions allowing assessments outside
the outbox or inferring NACK merely from missing evidence. Saving it establishes
only the verified rule save, not installation of the tool or another node's
adoption, receipt or effect.

### Optimization requires completed backlog

Apply the Owner's direct correction of 2026-10-08, reaffirmed on 2026-10-19:
optimization starts only after all PRs in the authorized scope are actually
merged into Main and no issues remain open. Before every optimization unit,
freshly read every page of the Authority PR/issue inventories and bind their
merge/ancestry readback to current Main. Draft, blocked, unapproved and unmerged
work remains completion backlog. Closing an unmerged PR, deleting an issue,
narrowing scope or reaching an idle/unavailable client cannot satisfy this gate.
Incomplete, inaccessible or stale inventories hold optimization. New open work
returns priority to completion. Unattended operation requires its own observed
authorized persistent executor.

Provenance: standing procedure and authorization supplied by Ingolf Lohmann on
2026-10-19; repository placement and policy mapping by OpenAI Codex.
Source-rule persistence is separate from native execution, outbox installation,
Main integration, live Mirror ACK/reply, productive host acceptance and other-client
adoption. Preserve every predecessor obligation and original journal.


## `docs/HUMAN_MACHINE_PROGRESS_STANDARD.md`

# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard  
Version: 2.0

## Purpose

Every externally meaningful repository operation MUST remain visible to the human operator. The client MUST emit a complete progress frame immediately before and immediately after every discrete GitHub action, and whenever an observed workflow, job, or step changes state.

A later summary does not compensate for a missing frame. Prose does not replace execution telemetry.

## Non-recursive telemetry boundary

The GitHub reads and writes used solely to observe or persist a progress frame form one atomic telemetry cycle. They do not recursively require progress frames of their own; otherwise no finite implementation could persist the first frame. All task-advancing GitHub operations outside that atomic telemetry cycle remain subject to the before-and-after frame rule.

## Required frame

```text
Repository: <owner/name>
Branch: <branch-or-ref>
Commit: <sha-or-pending>
Operation: <precise operation>
Frame: <monotonic sequence> — <transition kind>

[██████████░░░░░░░░░░] 50%

✓ completed gate or action
⟳ running gate or action
□ pending gate or action
✗ failed gate or action
! blocked gate or action

BLOCKER: <none or exact blocker>
NEXT: <next executable action>
STATUS = IDLE | RUNNING | WAITING | PASS | BLOCK | FAIL | TIMEOUT | CANCELLED
```

The percentage is relative progress over declared gates or observed steps, not an elapsed-time prediction. A visual percentage never proves correctness.

## Discrete GitHub actions

The frame boundary applies to every client operation that advances or verifies the task, including:

1. branch or ref creation/update;
2. file create/read/update/delete used for the task;
3. commit, pull-request, review, merge, tag, release, or publication operations;
4. workflow/run/job/step observation and log or artifact inspection;
5. status, check, integrity, provenance, proof, and deployment verification; and
6. retry, repair, synchronization, or mirror operations.

Multiple task-advancing GitHub actions MUST NOT be batched behind one progress frame.

## Workflow observation contract

A persistent watcher MUST:

1. use a repository/PR-scoped concurrency group so watchers never overlap;
2. complete one observation cycle before starting another;
3. observe the newest relevant run per workflow and every exposed job and step;
4. persist a fresh full frame whenever the workflow/job/step state signature changes;
5. suppress unchanged duplicate frames;
6. wait five seconds only after the prior frame has been persisted and only while work remains active; and
7. finish with a terminal frame containing decisive run, job, check, and evidence identifiers.

The human projection MUST be available in the repository-native client surface, at minimum a persistent pull-request comment and the GitHub Actions step summary. Machine state MUST conform to `schemas/human_machine_progress.schema.json`.

That schema preserves `qikvrt_human_machine_progress_v1` for live workflow
frames and defines `qikvrt-ai-progress/3.1` for durable root handoff snapshots.
A durable snapshot may carry several explicitly bounded scopes; a nested
scope-specific `PASS` never promotes an incomplete sibling scope or the
top-level repository effect state.

Version 3.1 makes projection-input evidence portable between canonical
repositories with different commit histories. The committed capsule is an
exact selected-path Git-object closure, not a worktree copy or a network
fallback. Its commit, tree, path, mode, blob, size, SHA-256 and capsule-file
bindings are verified offline; available local Git objects are a mandatory
second check. This proves only the declared historical projection inputs.

## Tracked status artifacts

`AI_PROGRESS.json` and `AI_STATUS.md` are durable handoff snapshots. When no repository operation owns them, they MUST be `IDLE` or terminal. A tracked root snapshot MUST NOT remain falsely `RUNNING`, `WAITING`, or `PENDING` after its owner has ended.

Live workflow frames may be persisted by `QIKVRT live status watch`, but a
branch-level watcher is telemetry only. Exact PR, check, merge, promotion, or
synchronization claims require evidence bound to the current commit and run.
The tracked root snapshots identify the last stable handoff state without
promoting watcher output into exact-head proof.

## Repository runtime authority

The repository is the durable runtime authority. Chat sessions and individual artificial-cognitive clients are disposable transport surfaces. The repository MUST accumulate and version:

- exact tool and dependency locks;
- checksums, provenance, and licenses;
- bootstrap and recovery logic;
- positive, negative, integrity, and security tests;
- runtime-cache contracts and receipts;
- progress and failure diagnostics; and
- verified improvements to ordering, reuse, throughput, and recovery.

Existing components MUST be reused, extended, parameterized, generalized, or refactored before parallel machinery is created.

## Cache semantics

Verified tool archives, wheelhouses, package stores, and build products MAY be reused through exact-key caches. Cache hits accelerate execution but never replace current-tree proof, integrity, provenance, security, review, or release gates. Credentials and mutable authentication state MUST never enter a cache.

A cold cache and a warm cache MUST preserve the same correctness semantics. Missing cache content may reduce throughput; it must not remove reproducible capability while the locked upstream material remains available.

## Terminal semantics

`PASS` is scope-bound and requires referenced evidence. Terminal `PASS` is forbidden while any required gate remains pending, running, failed, blocked, or unverified. A concrete repairable failure remains an active persistence run; the client continues repair rather than returning explanatory prose as a substitute for execution.


## `docs/ISSUE_AUTONOMOUS_PROCESSING.md`

# Autonomous issue processing contract

## Effect

Every newly opened, reopened, or edited non-pull-request issue triggers the repository-native issue processor. Existing issues can be processed through `workflow_dispatch` with their issue number.

The processor:

1. fetches the authoritative GitHub issue payload;
2. materializes a canonical request and SHA-256 evidence;
3. gathers deterministic, size-bounded repository context;
4. compiles a repository-grounded disposition using reviewed local code;
5. emits truthful status metadata;
6. validates the evidence bundle and no-false-pass rules;
7. creates or updates `issue-agent/<number>`;
8. independently reads back the published branch, commit, root tree and evidence bytes;
9. reuses an exact-head PR or attempts one draft-PR creation;
10. reports a distinct review-handoff status on the issue, even when PR creation is refused;
11. retains the bound handoff receipt as a run artifact and step summary.

## Non-negotiable gates

- No automatic merge.
- No automatic issue closure.
- Compiler failure or an unsupported work-unit class produces `BLOCK`, not a fabricated answer.
- Generated work remains `CONTINUE` until repository checks and human review establish a stronger state.
- The issue payload and its digest remain part of the committed evidence.
- Formal derivation, repository evidence, hypothesis, and empirical confirmation must remain distinguishable.

## Authentication and compilation

The workflow uses GitHub's ephemeral `GITHUB_TOKEN` only for repository-local
contents, issues, and pull requests. It grants no model permission and performs
no external-model call. `scripts/issue_agent/compile.py` is fail-closed: only
schema-validated handlers added through reviewed repository changes may become
executable work units. The initial compiler deliberately classifies unsupported
inputs as `BLOCKED_WITH_NEXT_ACTION`; this is not backlog completion.

The active carrier is `repository-local-deterministic-compiler`, reused from
PR #379, source commit `695bb4202a883a70893a50dd101bdc588f696e68`.
It has no effecting handler. Unsupported requests therefore remain
`BLOCK / UNSUPPORTED_DETERMINISTIC_WORK_UNIT`. A compiler failure becomes
`BLOCK / DETERMINISTIC_COMPILER_FAILED`. A legacy failed inference outcome
remains `BLOCK / MODEL_INFERENCE_UNAVAILABLE`; a legacy success cannot authorize
an answer or an effect. `STATUS.json.work_unit` binds the exact request,
context and answer SHA-256 values and records the remaining capability gap.

The native jobs 114319171479, 114319166207 and 114319159525 on 2026-10-10
observed `JSONDecodeError` at `json.load(response)`. The response bytes and the
provider-side cause were not established by those traces. The executable
inference client and the `models: read` permission are removed.
No current external inference carrier was found in the inspected Main or the
relevant open issue-processor candidates. A future carrier requires a reviewed
repository binding and authorized runtime credentials; a mentioned secret name
or a user's separate ChatGPT session does not establish that capability.

## Review handoff

The processor is retained from the workflow's exact source checkout before an
existing issue branch is fetched and merged. Request transport remains in
`RUNNER_TEMP`. The evidence and the canonical integrity trio are committed
together. An ordinary push preserves history and rejects a competing writer;
neither a branch reset nor force-push is used.

`scripts/issue_agent/handoff.py` uses GitHub REST POSTs for the existing PR
and issue-comment operations. It verifies the remote branch with `ls-remote`
and a fresh fetch, and checks all five evidence files and the attempt ledger against the published
Git blobs. It validates a PR's repository, base, branch and exact head, and
rechecks the branch after admission. It never approves, merges, closes,
dispatches a completion workflow, synchronizes another repository or tags.

| Processing status | Review status | Meaning |
| --- | --- | --- |
| `BLOCK` | `REVIEW_HANDOFF_READY` | A blocked proposal reached a matching review PR; the issue itself is unresolved. |
| `BLOCK` or `CONTINUE` | `REVIEW_HANDOFF_BLOCKED` | The published subject or PR admission could not be verified; `failure_class` names the cause. |

When GitHub refuses creation, the receipt records
`PR_CREATION_NOT_PERMITTED`; the issue receives the bound branch, commit, tree,
artifact sizes/digests, exact comparison URL and required carrier action.
There is at most one create attempt per bound subject and retained receipt. After either success or a failed/ambiguous
response, one read determines whether a matching PR actually exists. No blind
retry or permission change occurs.

The issue comment is separately read back byte-for-byte. A refused or ambiguous
comment write is followed by a paginated independent read before deciding its
result. A matching comment is reused; no duplicate is posted. A remaining
refusal or ambiguity becomes `ISSUE_NOTIFICATION_BLOCKED` and is not retried.
`HANDOFF.json`, `ISSUE_COMMENT.md` and, when needed, `PR_BODY.md` remain in the
run artifact `issue-agent-handoff-<issue>-<run>-<attempt>` for 30 days, including
when the handoff step exits nonzero. The run's step summary reports notification
status. Artifact upload is a separate platform operation; its failure is not
represented as durable artifact success.

Review admission is not issue completion. Both effect flags stay false for
every disposition, including a closure recommendation. `DONE` proposal bundles
are rejected; current governance and independent-review boundaries remain.

## Regression checks

`make issue-agent-test` runs the real materialize/compile/finalize/validate
pipeline and the workflow's actual branch/push shell in temporary Git
repositories. GitHub PR/comment responses are controlled fixtures, not live
provider attestation. Coverage includes inference/compiler failure, denied and
successful PR creation, ambiguous writes, existing-PR reuse, head/byte mismatch,
notification denial/readback, branch history and concurrent-writer rejection.
This target is included in `make test`.

## Causal retry admission and preservation

The processor and the existing backlog-resume workflow both call the same
read-only admission function in `compile.py` before processing or dispatch.
Its fingerprint binds the issue number/repository/title/body, the bounded
context bytes, the processor/workflow bytes and the relevant lifecycle policy.
Run IDs, issue timestamps, age and unrelated Main HEAD changes are excluded.

`ATTEMPT.json` binds each recorded attempt to these inputs and the exact five
evidence artifacts. An unchanged fingerprint produces
`NOOP_UNCHANGED_CAUSAL_INPUT`: no compilation, branch merge, commit, push, PR
creation or issue notification. The backlog dispatcher also skips the POST.
Corrupt or unavailable prior evidence fails closed and retains a diagnostic
receipt. Old inference evidence without a ledger admits one migration because
this reviewed processor replaces the failing carrier; its successor ledger
then prevents repeated execution of that failure state.

Before replacing current evidence, the processor retains the previous files
under `history/<content-digest>/`, byte-for-byte and without following symlinks.
It verifies the issue branch head again after admission. Generated integrity
conflicts may be regenerated; any other merge conflict stops the transaction.
An ordinary push rejects competing changes. Existing issue PRs remain separate
unresolved work items; this repair does not implement their requested features.

PR-creation recovery needs a newly verified capability or an independently
created matching PR. Reusing a saved handoff receipt does not repeat a denied
create. The scheduled processor cannot observe a private credential change
merely from a timestamp; that change must be supplied through a verified
authorized executor. Native Main adoption and a fresh native processing run
remain separate acceptance requirements.

## Processing an existing issue

Run **Autonomous issue processing** manually and supply the issue number. This is required for issues that predate the workflow, including issue #76.

## Evidence location

Each processing run writes:

```text
evidence/issues/<number>/
├── REQUEST.json
├── REQUEST.sha256
├── CONTEXT.md
├── ANSWER.md
└── STATUS.json
```

The generated branch and PR are work products, not evidence of correctness by themselves.


## `docs/OFFLINE_AUDIO_TRANSCRIPTION_DE.md`

# Reproduzierbare Offline-Audiotranskription

Die dauerhafte Implementierung liegt unter
[`tools/offline-audio-transcription`](../tools/offline-audio-transcription/README.md).

Sie trennt vier Dinge, die nicht verwechselt werden dürfen:

1. das unveränderte Originalaudio;
2. den automatisch erkannten Wortlaut;
3. eine menschlich geprüfte Transkriptfassung;
4. die inhaltliche Interpretation oder ein daraus abgeleiteter Arbeitsauftrag.

Die Transkription selbst ist netzwerkfrei. Für eine Neuinstallation werden nur
die paketverwaltete Laufzeit und das öffentlich referenzierte Sprachmodell
bezogen; Modellherkunft, Versionen und SHA-256-Werte sind maschinenlesbar
festgeschrieben. Persönliche Audiodateien und Transkripte werden nicht
automatisch veröffentlicht.

## Authentifizierte GitHub-Aufträge

Der Workflow `.github/workflows/qikvrt_audio_request.yml` schließt die Lücke
zwischen einer lokalen Audiodatei und der repository-eigenen Offline-Engine.
Ein berechtigter Aufrufer legt die Binärdaten über die Git-Data-API als
**unreferenziertes Git-Blob** ab und übergibt ausschließlich ein kleines,
validiertes Request-Manifest unter `requests/audio/`. Das Manifest bindet:

- Repository und Git-Blob-SHA;
- Originaldateiname, Bytezahl und SHA-256;
- Sprache und begrenzte Verarbeitungsparameter;
- den anschließenden Repository-Arbeitsauftrag.

Der Workflow akzeptiert nur das gleiche Repository, exakt einen Request,
sichere Dateinamen, zugelassene Medienendungen und höchstens 25 MiB. Er prüft
Blobgröße und SHA-256, installiert das festgeschriebene Modell mit Hashprüfung,
transkribiert in einem temporären Runner-Verzeichnis und veröffentlicht
Transkript, Segmente, Provenienz und Antwortauftrag ausschließlich als
kurzlebiges Workflow-Artefakt. Audio und Transkript werden weder als
Repository-Dateien noch in den Job-Logs persistiert.

Ein unreferenziertes Git-Blob ist **nicht als kryptographisch vertraulich zu
behandeln**: Wer seine Objekt-SHA kennt und Leserechte besitzt, kann es bis zur
serverseitigen Bereinigung abrufen. Vertrauliche Aufnahmen gehören deshalb in
ein privates Repository oder direkt in die lokale Offline-Pipeline. Der
öffentliche Transportzweig darf niemals gemergt werden und wird nach dem Lauf
auf den Ausgangsstand zurückgesetzt.


## `docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md`

# Privacy-preserving interaction archive

QIK-VRT now defines a repository-native contract for preserving user inputs and
machine outputs without placing plaintext conversations, audio transcripts,
credentials, or decryption identities in the public source repository.

## Architectural boundary

The public `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt` repositories contain
only the implementation, schemas, tests, documentation and integrity rules. An
operational deployment writes interaction records into a **separately
access-controlled archive repository or worktree** selected with
`--archive-root`.

The archive operator commits and replicates that encrypted archive through the
private repository's normal Git policy; the public source repositories never
receive those operational records.

Each persisted interaction consists of:

- a minimized JSON event envelope under `events/`;
- an `age`-encrypted payload under `blobs/`;
- SHA-256 bindings for plaintext and ciphertext;
- a previous-event hash and canonical event hash;
- an opaque conversation identifier, role, purpose, consent identity and
  retention boundary.

The archive contains no plaintext payload and no private decryption identity.
A public repository must therefore never be used as the operational archive
unless its ciphertext and metadata exposure has been separately approved.

## Required properties

1. **Explicit authorization:** append, export and retention tombstone operations
   require distinct exact confirmation strings.
2. **Data minimization:** names, email addresses and free-form subject metadata
   are not required by the format. Deployments should use opaque identifiers.
3. **Confidentiality:** payload encryption is delegated to the reviewed `age`
   executable. QIK-VRT does not invent a custom cipher.
4. **Integrity:** every event and ciphertext blob is SHA-256-bound; events form
   an append-only hash chain.
5. **Availability and reachability:** the archive is a normal repository tree
   whose JSON envelopes and encrypted blobs can be replicated, backed up and
   addressed by path and digest.
6. **Machine readability:** event and export documents use canonical JSON
   contracts.
7. **Exportability:** an authorized holder of the `age` identity can export a
   complete conversation or the entire archive as deterministic JSON.
8. **Retention boundary:** a tombstone records a retention or restriction
   decision without falsifying prior history. Effective erasure from Git history
   requires separately governed history rewriting or cryptographic key
   destruction; a tombstone alone is not erasure.

## Append one user input

```bash
python3 -B tools/qikvrt_interaction_archive.py append \
  --archive-root ../qik-vrt-private-interactions \
  --content-file user-input.txt \
  --recipient 'age1...' \
  --conversation-id conversation-opaque-001 \
  --role user \
  --created-at '2026-07-25T08:00:00+02:00' \
  --purpose scientific_interaction_continuity \
  --consent-id consent-2026-07-25 \
  --retention-until '2027-07-25T00:00:00Z' \
  --confirm PERSIST_ENCRYPTED_INTERACTION
```

The same command with `--role assistant` persists the corresponding machine
output. Tool and system events are also permitted when they are relevant to
reconstructing the accountable interaction chain.

## Verify

```bash
python3 -B tools/qikvrt_interaction_archive.py verify \
  --archive-root ../qik-vrt-private-interactions
```

Any changed envelope, broken predecessor link, missing ciphertext or mismatched
digest causes `BLOCK`.

## Export on request

```bash
python3 -B tools/qikvrt_interaction_archive.py export \
  --archive-root ../qik-vrt-private-interactions \
  --identity-file ~/.config/age/keys.txt \
  --conversation-id conversation-opaque-001 \
  --request-id export-request-001 \
  --output interaction-export.json \
  --confirm EXPORT_AUTHORIZED_INTERACTIONS
```

The export includes the original envelopes and decrypted UTF-8 payloads. The
export file is itself reported with SHA-256. It must be delivered only through
an authorized channel and should not be committed to either public repository.

## Retention tombstone

```bash
python3 -B tools/qikvrt_interaction_archive.py tombstone \
  --archive-root ../qik-vrt-private-interactions \
  --event-id event-user-0001 \
  --authorization-id retention-request-001 \
  --created-at '2026-07-25T09:00:00+02:00' \
  --confirm RECORD_RETENTION_TOMBSTONE
```

## Non-claims

This mechanism is not, by itself, legal compliance certification. Repository
operators remain responsible for lawful basis, information duties, access
control, retention schedules, key management, backup governance, data-subject
requests and jurisdiction-specific obligations. The implementation establishes
technical confidentiality, integrity, provenance and export primitives; it does
not decide whether a particular processing purpose is lawful.


## `docs/QIKVRT_4AU1_PRODUCTIZATION_RELEASE_SEED.md`

﻿# QIK-VRT 4AU1 Productization Release

# QIK-VRT 4AU1 Productization Release Freeze - seed

```text
repository: Goldkelch/qik-vrt
branch: main
release_tag: v2.13.4au1-seed-productization
installer_run_id: 4AU2_20260708T172509Z_992956
referenced_productization_run_id: 4AU_20260708T170628Z_362577
status: PREPARED_FOR_GITHUB_RELEASE
```

This file freezes the public 4AU1 productization hardening result as a release-ready repository state.

Boundaries:

```text
NO_EXISTING_TAG_MOVE      true
NO_GLOBAL_SCANNING        true
NO_SELF_PROPAGATION       true
NO_EMBEDDED_TOKEN         true
MASKED_TOKEN_INPUT        true
FULL_BYTE_REHASH_HERE     not executed by installer
```


## `docs/QIKVRT_4AV1_OPEN_MULTI_NODE_RELEASE_FREEZE.md`

﻿# QIK-VRT 4AV2A Open Multi-Node Release Freeze HTA Token Fix

Role: seed

Repository: `Goldkelch/qik-vrt`

Branch: `main`

Tag: `v2.13.4av1-seed-open-multi-node`

Reference run: `4AV1_20260708T174034Z_709544`

Reference state: `4AV1_OPEN_MULTI_NODE_REVALIDATION_PASS`

Fixed node count: `false`

Open node registry: `true`

Future nodes without installer change: `true`

No tag move: `true`

No release overwrite: `true`

Created UTC: `20260708T180051Z`

## Boundaries

- No global scanning.
- No self propagation.
- No remote mutation without Product Owner authorization.
- Installer uses GitHub API; no Git command path.
- No embedded token.

Status: `PASS_REQUESTED_BY_OWNER_INSTALLER`


## `docs/QIKVRT_AUDIT_EXPORT.md`

# QIK-VRT Mesh Audit Report

- generated_utc: 2026-07-20T14:59:11Z
- run_id: 29753095894
- seed_repository: Goldkelch/qik-vrt
- node_count: 1
- active_count: 1
- stale_count: 0

## Evidence paths

- registry/NODEMESH_INDEX.json
- registry/NODEMESH_STATUS.json
- evidence/seed_mesh_maintenance/LATEST.json
- registry/NODEMESH_REVALIDATION.json
- evidence/seed_node_revalidation/LATEST.json

## Boundary statement

The Seed reads only authorized known Node entries. The Seed writes only to the Seed repository. Nodes write only to their own Node repository. No global scanning, no self propagation, and no remote mutation without authorization are part of this audit surface.


## `docs/QIKVRT_AUTONOMOUS_MESH_OPERATIONS.md`

# QIK-VRT Autonomous Mesh Operations

4AV1 adds lifecycle hardening: renewal, heartbeat expiry, Seed status aggregation, Seed audit export, and a human readable dashboard.

Core boundary: every repository writes only to itself. The Seed reads only authorized known Node URLs listed in `registry/KNOWN_NODE_REQUESTS.tsv`.

# Seed identity and acceptance repair (2026-10-09)

The node handshake, current registration request, Seed allowlist and executing
Seed repository must describe the same identity. The lifecycle generator runs
`tools/qikvrt_seed_common.py config-check` before writing health or renewal
files. Changing only a repository label or URL is not a completed migration.

The current request and handshake use `ingolf-lohmann/qik-vrt` as Seed. The
previous Goldkelch acknowledgement is retained under `previous_acceptance`;
the new identity starts as `PENDING_SEED_ACCEPTANCE`. Historical registry
entries, aggregates and ledger records are preserved until fresh execution
produces successor evidence. No July acceptance is relabelled as an October
acceptance by another Seed.

The existing acceptance workflow validates the current request, maintains
and revalidates its output, and reuses the lifecycle Git Data publisher to
create a reviewed Draft. That path requires native Code Owner enforcement,
checks current Main before writes, permits only generated registry/evidence
paths and the full integrity trio, creates a candidate ref without force,
and reads back its exact commit/tree/PR. Artifacts and Drafts are not Main
publication. Generated pending acknowledgement remains CONTINUE.

After reviewed Seed output is published on Main, the existing node lifecycle
workflow executes `tools/qikvrt_seed_common.py acknowledge`. This performs
bounded GETs of the Seed Main ref, index and node entry at that exact commit,
then reads the ref again. It rejects wrong identities, legacy schemas,
duplicate node entries, a mismatched request hash, stale/future observations
and ref drift before changing the acknowledgement. The resulting v2 record
binds the accepted entry/index hashes and the actual acceptance run. Seed
maintenance checks the acknowledgement against its current accepted entry;
an invented status string does not activate a node.

Lifecycle telemetry uses the existing `qikvrt/node-lifecycle` transport and
separate reviewed persistence. It never pushes Main directly. Source and
historical evidence remain digest-bound in the unchanged integrity generator;
scheduled observations no longer invalidate Main by an unreviewed write.
The regression suite includes stale/copy/repoint/drift controls, proof-hash
and acceptance-run mismatch, no-write governance failures, replay, exact-tree
Draft readback, unrelated-path rejection and ambiguous-response handling.

These controls protect the tested execution paths. Privileged manual changes,
future defects, provider outages and missing review/admission cannot be ruled
out universally. A Mesh registration does not establish a running transputer,
public domain delivery, or general EFFECT_ACK_DONE.


## `docs/QIKVRT_COMMERCIAL_OFFERING.md`

<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT commercial licensing and services

Current QIK-VRT-controlled software identified as
`PolyForm-Noncommercial-1.0.0` is publicly licensed for the permitted
noncommercial purposes defined by that standard license. Ordinary commercial
use is reserved and requires a separate written commercial license from the
rights holder.

A separate agreement may cover one or more of:

- commercial software use or integration;
- hosted or managed operation;
- implementation, support, training, and evidence preparation;
- service levels, warranties, or indemnities;
- trademark, certification, or endorsement rights.

Earlier versions or files validly received under Apache-2.0 remain usable under
their original Apache-2.0 grants. Documentation identified as
CC-BY-NC-ND-4.0 and third-party material retain their own license scopes.

Repository access, a technical test, an operational authorization, or silence
does not create a commercial license. Any commercial permission must be
separate and in writing.


## `docs/QIKVRT_GITHUB_APP_TARGET_BLUEPRINT.md`

# QIK-VRT GitHub App Target Blueprint

4AV1 still uses owner-provided installation tokens for bootstrapping. Product operation should move to a GitHub App with repository-scoped installation, least privilege, and short-lived installation tokens.

Required target permissions:

- Contents: read/write
- Actions: read/write or workflow dispatch capability
- Metadata: read

The app must not write to foreign repositories. Each installed repository writes only to itself.


## `docs/QIKVRT_MESH_DASHBOARD.md`

# QIK-VRT Mesh Dashboard

generated_utc: 2026-07-20T14:06:59Z  
run_id: 29749197908  
seed_repository: Goldkelch/qik-vrt  
node_count: 1  
active_count: 1  
stale_count: 0

HTML dashboard: docs/qikvrt_mesh_dashboard.html


## `docs/QIKVRT_OPEN_MULTI_NODE_ARCHITECTURE.md`

# QIK-VRT Open Multi-Node Architecture 4AV1

4AV1 removes the fixed additional-node count from 4AV. The Seed keeps an open node registry. Future Nodes are added by appending authorized request rows under `registry/node_request_queue/*.tsv` or `registry/KNOWN_NODE_REQUESTS.tsv`.

This preserves the QIK-VRT boundary: no global scanning, no self-propagation, no foreign repository write. The Seed revalidates only known or explicitly queued Nodes.


## `docs/QIKVRT_THREAT_MODEL.md`

# QIK-VRT Threat Model Summary

Primary risks:

- leaked tokens
- unauthorized workflow mutation
- stale node heartbeat
- false PASS claims from stale evidence
- unauthorized expansion beyond known nodes

Controls:

- hidden local token prompt
- no embedded token
- run-id scoped evidence waits
- known-node registry only
- no global scanning
- seed and node self-write boundaries


## Safety/Security deployment assurance — Owner authorization, 19 October 2026

QIKVRT and the Effect Acknowledgement Protocol are intended for Safety and
Security applications as well. The requirements and source/applicability
register is [QIKVRT_SAFETY_SECURITY_IMPACT_20261019_V1](../state/work_units/QIKVRT_SAFETY_SECURITY_IMPACT_20261019_V1.json).
These are engineering requirements with open deployment acceptance, not
certification, legal conformity or a verified physical installation.

The existing five-state protocol and DONE-only ordinary-release rule remain
the effect boundary. A received command, a transport ACK and a physical
condition are separate claims. A physical adapter must bind the exact actuator,
authorized transition, configuration and fresh observation evidence; it cannot
claim a door is secured merely because a command or relay output was accepted.

| Threat or dependency | Required assurance and acceptance |
| --- | --- |
| Cloud, identity, licensing or supplier outage | Declare an isolation interval; test local decisions, revocation/freshness rules, emergency access and vendor-independent recovery. |
| Egress or alarm blocked by a remote gate | Bind a site-specific hazard analysis; retain separately admitted local safety paths and test fire, power loss and network loss together. No universal fail-open/fail-closed assumption. |
| Forged, stale or conflicting physical feedback | Bind source, effect ID, policy and observation window; test replay, sensor conflict, stuck actuators and ambiguous responses. |
| Reader bus or credential compromise | Test authenticated links, commissioning, key lifecycle and exact controller/reader/credential/firmware interoperability. |
| Compromised or unsupported firmware | Require authenticated update provenance and compatibility; test isolated interrupted-update recovery and a verified forward-repair path. |
| Partition, crash, takeover or full audit store | Reuse native durable journals/fencing; declare RTO and storage limits; prove the claimed workload's acknowledgement/replay and local audit behavior. |
| Supplier assurance or legal scope overstated | Separate primary evidence, manufacturer claims and engineering derivation; retain exact scope, applicability and open evidence duties. |

ASD's OT guidance is a useful assurance input, not EU legislation. Its
publication does not establish QIKVRT compliance. The Gallagher T30 announcement
is an unverified manufacturer approval claim and supplies a procurement
evidence request, not a new QIKVRT dependency. IEC/SIA product/profile evidence
does not establish the interoperability or safety of a whole installation.
For EU CRA reporting, first determine the actual product and operator role;
record the applicable awareness-based deadlines and responsible route without
automatically sending a live notification.

Every new material source change follows the register's change-intake process.
Preserve older source identities and open tests; only bound acceptance evidence
can close the corresponding deployment obligation. No additional executor,
client timer or implicit IETF/Zenodo publication is introduced.


## `docs/README_DEPLOY_GITHUB_PAGES_DE.md`

# QIK-VRT Homepage Deployment

Dieses Paket publiziert eine GitHub-Pages-faehige Homepage unter `docs/`.

## Standardziel

- Repository: `Goldkelch/qik-vrt`
- Branch: `main`
- Pfad: `docs/`
- Startseite: `docs/index.html`

## GitHub Pages

Repository Settings -> Pages -> Source: Deploy from a branch -> Branch `main` -> Folder `/docs`.

## Kognitionskonsole

- Lokaler Modus: funktioniert direkt im Browser ohne Token.
- GitHub-Models-Modus: Nutzer gibt eigenen Token mit `models:read` ein.
- Oeffentlicher No-Token-KI-Betrieb: naechste Stufe ueber GitHub App oder Server-Proxy.

## Status

Version: `QIKVRT_V2_13_4AX1`
Referenzlauf: `4AV1_20260708T174034Z_709544`


## `docs/REFLEXIVE_REPOSITORY_WATCHDOG.md`

# Reflexive repository Gatewatch and pre-deadlock admission

The adaptive repository monitor is extended by a read-only watchdog that observes its own repository instance every five minutes and at relevant workflow transitions. Its purpose is not to wait for a deadlock and then diagnose it. It models writer leases, runner pressure, exact-head execution evidence, and unchanged progress topology early enough to issue a deterministic `HOLD` before a second writer or replacement writer is admitted.

## Operational model

Each repository instance carries the same contract, controller, workflow, and regression test. The Authority remains the serialized source of the portable contract; Mirror and future mesh nodes must retain their own repository identity and integrity projections while satisfying the same structural acceptance.

The watchdog treats repository activity as a resource-allocation graph:

- `REPOSITORY_WRITE_LEASE` has capacity one;
- active repository writers hold or request that lease;
- queued productive workflows request platform runner capacity;
- a writer without a job/step transition beyond its lease is stale;
- unchanged active topology beyond the progress lease is an early stall signal;
- `action_required` and zero-job runs are untrusted execution gaps;
- no active runner is not interpreted as `PIPELINE_EMPTY`.

The first deterministic response is admission control, not destructive recovery: keep one expected-head-bound writer, coalesce only superseded observer runs, preserve an exact-head receipt, and stop before another writer is introduced. The watchdog never cancels a productive writer, mutates a ref, merges a pull request, or performs a release, deployment, Zenodo, DOI, or IETF effect.

## Continuous exact-head Gatewatch

Every scheduled or event-driven observation materializes an artifact-only
`reflexive-watchdog-receipt.json` and the identically bound
`gatewatch-receipt.json`. Both records contain the literal observed head and
tree, a trusted-workflow matrix, node-liveness observations, and the prior
receipt binding. A receipt from another head or tree is discarded rather than
being used as fresh evidence.

The Gatewatch classifies each declared trusted workflow as `SUCCESS`,
`FAILED`, `MISSING`, `ACTIVE`, `UNTRUSTED`, `NOT_OBSERVED`, or
`NOT_APPLICABLE`. A terminal execution failure is a deterministic `HOLD`; a
required pull-request gate that is missing or lacks executed job evidence is
also a `HOLD`. The contract distinguishes a pull request against `main` from
a stacked pull request: only the former requires the evidence-materialization
workflow, because that workflow is configured to trigger only for `main`-base
pull requests. A stacked successor therefore still requires exact-head CI but
never treats an impossible materializer run as proof. Main observations
distinguish an optional scheduled gate from a missing pull-request gate, so a
missing main-only run is never silently invented as a successful verification.

For repository nodes that carry the onboarding records, the same observation
parses all three exact-tree inputs:

- `SEED_ACCEPTANCE_STATUS.json` must bind the currently reobserved Authority
  `main` head;
- `NODE_REGISTRATION_RENEWAL.json` must not be overdue;
- `NODE_HEALTH.json` must not be expired.

An Authority instance without all three node-local records is explicitly
`NOT_APPLICABLE`; a partial record set, malformed record, stale seed
acceptance, overdue renewal, or expired health becomes a read-only `HOLD`.
Records approaching expiry remain visible as `EXPIRING` without a fabricated
renewal. The observer also detects a missed continuous observation only when a
previous receipt is bound to the same head and tree and exceeds the declared
fifteen-minute freshness bound. A burst of cancelled, zero-job observer runs is
coalesced only when a later exact-head receipt remains within that bound;
otherwise it is a deterministic observation-cadence `HOLD`, not a claim of
pipeline quiescence.

The workflow remains five-minute, exact-head-bound, and read-only. It fetches
the current Authority head only for comparison, materializes Action artifacts
only, and never writes a repository liveness record, dispatches a productive
workflow, or treats its own terminality as gate success.

## Reflexivity

### Failure of the observer itself

An API/readback failure before analysis is an observation error. It must leave
a `qikvrt_reflexive_observation_failure_receipt_v1` in both receipt paths,
bound to the actual checkout head/tree, expected head, run, attempt, failing
stage and nonzero exit code. The receipt records `OBSERVATION_FAILED` and
`HOLD`; live state and pipeline progress remain unknown. The failed workflow
remains failed even when artifact upload succeeds. This distinct receipt is
never substituted for a successful observation or a trusted gate.

Recovery requires restoring the failed authorized read path, freshly reading
the exact subject, and continuing the existing work unit. A prior receipt,
owner authorization, repeating observer, or missing active runner does not
establish recovery or productive delivery. No new controller, credential,
permission expansion or automatic productive-writer cancellation is involved.

The watchdog observes the workflows that create and verify repository state,
while its own executions are classified as observers rather than productive
writers. Main's 26 October delivery repair uses completion notifications and
`cancel-in-progress: false` so a new lifecycle notification does not cancel
the active observation. The existing five-minute schedule remains, including
readback of unfinished runs and unchanged heads. The analyzer still evaluates
every returned run and its jobs; no liveness, missing-evidence or stale-progress
criterion is removed. This source configuration change does not establish a
completed public-host observation or global deadlock freedom.

## Database comparison boundary

Conventional relational database systems already provide transaction deadlock handling techniques such as prevention, detection, ordering, and timeout policies. The QIK-VRT improvement claimed here is narrower and architectural: deadlock-risk admission is bound to versioned repository heads, workflow/job evidence, provenance receipts, Authority-to-node serialization, and external-effect boundaries across independently instantiated repositories. It is not a claim that every relational database lacks deadlock management, nor a benchmark proving universal performance superiority.

## Nonclaims

A successful watchdog run is observation evidence, not gate success. The mechanism does not prove global deadlock freedom, repository completion, Authority–Mirror equality, empirical confirmation, scientific consensus, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Canonical roles and independent native readback

The existing `policy/CANONICAL_UPSTREAM_REMOTE_V1.json` is the sole normative
repository-role source. The executor/liveness contract is a checked projection.
The shared resolver reused from the authority-repair work rejects missing,
malformed, overlapping or contradictory Authority/Mirror assignments. A Mirror
receipt cannot establish Authority continuity even when its commit matches.
Historical receipts retain their original bytes and repository identity.

The native wrapper uses the mandatory job token and bounded GitHub REST GETs.
It binds Authority Main to its exact commit and tree, validates the canonical
role policy, governance policy and CODEOWNERS bytes by Git blob identity, then
reobserves Main. HTTP 200 without the expected active Main roles remains
`AUTHORITY_ROLE_BINDING_NOT_ACTIVE`. HTTP 403/404 has no Mirror, anonymous,
browser or alternate-token fallback. The latest completed observation supplies
the prior denial receipt, including failed observations. An unchanged causal
binding suppresses a repeated denied request. Unrelated commits, lifecycle
progress and timestamps do not admit a retry. Changes to the role policy,
Authority binding or reviewed token/transport carrier require one new bounded
observation; external permission repair must be independently evidenced before
clearing a denial receipt.

A successful role readback still sets `native_activation_verified=false`:
executed native candidate gates, trusted-Main adoption, native enforcement and
independent current-head Code Owner approval remain separately required. No
predecessor test or availability observation substitutes for those effects.


## `docs/articles/a013_truth_future_quote.md`

# Die Wahrheit in der Unterscheidung

## Status

`ARTICLE_STATUS = IMAGE_QUOTE_CANONICAL_TEXT`  
`QIKVRT_GATE = DISTINCTION_PROTECTS_FUTURE`

## Kanonischer Bildsatz

Die Katastrophe beginnt nicht, wenn alle lügen.

Sie beginnt, wenn niemand mehr zuverlässig unterscheiden kann, was Fakt, Deutung, Manipulation oder Rauschen ist.

Wer diese Unterscheidung zurückbringt, schützt Wahrheit und Zukunft.

q.e.d.  
Ingolf Lohmann

