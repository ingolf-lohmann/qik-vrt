<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# QIK-VRT with and against IBM technologies

Public protocol and implementation candidate, 18 October 2026. Responsible
human: Ingolf Lohmann. This page is intended to be readable by IBM, the owner
and everyone else without an account. All measured outcomes, including failures,
are to be published. IBM has not participated in or endorsed this preparation.

**Current result: adapters and comparison plans are prepared. No IBM model
performance comparison has been executed. There is no measured winner.**
See `RESULTS.json` for the dated technical verification and remaining work.
Technical doubles, synthetic clocks and a mock HTTP model are engineering
tests, not IBM inference, product trials or independent replication.

## Vergleich und Zusammenarbeit

Der Auftrag von Ingolf Lohmann lautet: „Dann bereite alles Notwendige darauf
vor, um QIK VRT gegen und mithilfe dieser IBM-Technologien antreten zu lassen
und das Ergebnis sowohl für IBM als auch für mich als auch für alle anderen
frei zugänglich zu machen.“

Der vorhandene A/B-Harness, PersonalRuntime, das persistente Sitzungsformat
und die MCP-Schnittstelle werden weiterverwendet. Der bevorzugte Modellpfad
ist Granite auf eigener Infrastruktur. Die optionalen watsonx-/Orchestrate-
Versuche schaffen keine Voraussetzung für den selbst betriebenen QIK-VRT-Knoten.

| Study | Baseline | QIK-VRT arm | Question |
| --- | --- | --- | --- |
| `granite-continuity` | Granite assistant with ordinary full history and restore | Same Granite plus QIK-VRT checkpoints | Does QIK-VRT improve source-bound continuation? |
| `orchestration-head-to-head` | Native IBM Orchestrate agent | QIK-VRT PersonalRuntime using the same Granite | How do the orchestration architectures compare under matched capabilities? |
| `orchestrate-hybrid` | IBM Orchestrate with its normal tools and memory | Same agent plus existing QIK-VRT evidence tools | Does interoperability improve verified task completion? |
| `watsonx-continuity` | Same watsonx model/project, normal full history | Same model/project plus QIK-VRT checkpoints | Is an effect reproducible on the optional IBM API path? |

Each study prepares two existing synthetic tasks, six balanced AB/BA pairs per
task and 24 individual trials: **96 planned trials, zero executed product
trials**. Studies remain separate. The head-to-head and hybrid studies require
an actual Orchestrate executor, import receipt and equivalent tool/memory
configuration before execution; a plan does not implement that service.

## What is implemented

- `src/qikvrt_personal_assistant.py`: `IBMChatTransport` implements text-only
  local OpenAI-compatible Granite chat and optional watsonx `/ml/v1/text/chat`.
  It reuses the existing bounded HTTP transport, redirect rejection, private
  SQLite state, checkpoint validation and unresolved-request protection.
- `--personal-provider granite_local` and `--personal-provider watsonx` use the
  existing terminal and PersonalRuntime. Both arms send ordinary full history.
  The QIK-VRT arm adds only its source-bound checkpoint on explicit resume.
- `ibm-plan` extends the existing A/B CLI and reuses its plan, scoring, journal
  and analysis implementations. Every unstarted trial stays visible.
- No new workflow, executor, automatic model downloader or parallel memory
  store is introduced. `make test` includes `ibm-comparison-test`.
- The existing protected OS credential store and OIDC path remain available.
  Optional legacy environment pairing remains a development path and does not
  establish SSO, biometric verification or production acceptance.

The local adapter accepts only an explicit `http://127.0.0.1:PORT` origin and a
40-character declared model revision. It disables proxies. The optional cloud
adapter restricts requests to explicit IBM regional HTTPS origins and requires
an explicit project, API date and existing IAM bearer. It performs no account
creation, token exchange or automatic request retry. Model substitution,
truncated results and tool-call output are rejected rather than marked complete.

**Model identity:** a configured revision or server-reported model name does
not prove loaded weights. `model_revision_attested=false` remains explicit.
Before comparison, bind model-file SHA-256 values, quantization, server version
and image digest to independent host evidence. The pinned Granite candidate
has not been downloaded or admitted by this preparation. Model-server tools
must enter the existing locked toolchain/cache admission before use.

## Reproduce preparation

Use a complete checkout of this candidate, the repository's declared Python
runtime and the existing toolchain. This work was tested in a byte-verified
REST-materialized sparse checkout; full-repository bootstrap/integrity and
trusted native CI remain separate obligations, recorded in `RESULTS.json`.

```bash
python3 -B tools/qikvrt_tool_cache.py verify
make ibm-comparison-test
make browser-assistant-ab-test
python3 -B tools/qikvrt_browser_assistant_ab.py ibm-plan \
  --output .qikvrt/runtime/ibm-comparison/run-001
```

The last command makes no network request, installs nothing and reads no
credential. It freezes plans plus initial analyses and `IBM_PREPARATION.json`.
Keep this directory private: it contains scoring oracles. Give the model only
the existing HTTP task view and an independently isolated tool/filesystem view.
Use a new directory for every new plan; prior runs are never overwritten.

To connect an **already admitted local Granite server**, set the non-secret
configuration on the owner host:

```bash
export QIKVRT_IBM_ENDPOINT=http://127.0.0.1:8000
export QIKVRT_IBM_MODEL_REVISION=be9e7d995f2a6be22def5dd815f9f2bae98c8b6e
```

Then start the existing terminal `serve` operation with `--personal-provider
granite_local`, an explicit `--personal-model` matching the server's served-model
name, private `--personal-state-dir` and the existing private
`--personal-auth-config`. Keep the registered OIDC/secret-store binding.
For a protected local model endpoint, use the existing provider-key slot
`granite_local`; credentials stay outside this repository. Anonymous local
model HTTP does not establish an authenticated model-runtime receipt.

For optional watsonx use the same terminal with `--personal-provider watsonx`.
Set non-secret `QIKVRT_IBM_ENDPOINT`, `QIKVRT_IBM_PROJECT_ID` and
`QIKVRT_IBM_API_VERSION` to the exact supported service contract, and select an
available explicit model ID from that project's inventory. The existing
protected provider-key slot is `watsonx`, containing an IAM bearer, not an IBM
API key. The environment-only development equivalent is
`IBM_WATSONX_BEARER_TOKEN`. A locally missing variable says nothing about
credentials on another host. Expired or ambiguous requests remain pending;
read back their outcome before any successor request.

## IBM Orchestrate integration

Reuse `src/qikvrt_github_api_shim.py` and `src/qikvrt_mcp_adapter.py`, not a new
facade. The existing HTTP MCP route is `/mcp`. Import that **actually deployed,
authenticated** server using Orchestrate's documented Streamable HTTP import.
`ORCHESTRATE_IMPORT.json` binds the intended tools and prerequisites, and is
explicitly a template with `server_url=null`; no live endpoint is invented.

Import only `qikvrt_repository_state`, `qikvrt_capabilities` and
`qikvrt_effect_ack_result`, with a separate existing read credential restricted
to `repository:read capability:read effect_ack:read` and an exact repository/ref.
The latter tools require exact-head/result binding. Retain ordinary Orchestrate
memory and tools in the baseline. No publication, merge or deployment authority
is granted by these tools. Bind the actual Orchestrate agent revision, model,
toolset, retention, run trace, import readback and budget before measurement.

## Measurement and independent reproduction

Use the existing independent scorer and event chain. Record completion quality,
false completion claims, all failures/timeouts, source correctness, resumption
latency including restore and verification, human re-entry and interventions.
Record observed token usage, memory, wall time and evidenced monetary cost;
publish energy only when measured. A self-reported successful tool call is not
an independently observed external effect. Use sandbox effects for replay,
duplicate, lost-ACK and restart checks; publish each workload's exact scope.

Keep normal baseline restore and memory. Freeze matching weights, quantization,
thinking settings, prompts, sources, allowed tools and local hardware/cache
policy. Report cloud transport/hardware differences separately. The default
sample is a balanced pilot, not a powered confirmatory study. Preregister the
confirmatory sample size and analysis before its execution; do not select only
successful pairs or turn missing latency into zero.

The existing product gate still requires equivalent observed pre-runs, real
interruptions, isolated oracles, baseline retention readback and independent
scoring. The current harness intentionally does not promote those missing
obligations into product acceptance. SOFAI-LM and NeuroVSA are declared research
extensions requiring their own executable revision, licence and matched task
bindings. Neither is presented as implemented or measured here.

## Public result and contribution record

Publish this protocol, candidate source, versioned result JSON, technical test
logs, all admitted public/synthetic trial rows, scoring rules and exact source
bindings together. Append corrections and successor results; retain earlier
failures and frozen runs. Keep private credentials and personal source data out
of public artifacts. Anyone, including IBM, can inspect the public repository
candidate and submit an independently bound reproduction through its ordinary
review process. Public readability does not change existing implementation or
third-party licences. No endorsement or independent replication is inferred.

Human contribution: Ingolf Lohmann's task, architecture, standing method and
publication direction. Artificial-cognitive contribution: this candidate's
adapter code, tests, experiment mapping and prose prepared by the coding
assistant. Joint component: the implementation applies the human-specified
requirements; acceptance does not change its recorded origin.

QIK-VRT's published entry point is the source listed below. Its archived
formal/model results retain their original premises and scope; they do not
constitute a new empirical IBM comparison. Git commit/tree and file digests in
the work receipt are implementation provenance, not a substitute for a
scientific publication or a confirmed Zenodo archival of new results.

## Sources / Quellen

Checked 18 October 2026. IBM statements describe documented interfaces and
research scope; implementation tests here are separately identified above.

1. Ingolf Lohmann: Von Softwarearchitektur zur Weltformel – DAS UNIVERSUM ALS ROUND TRIP.
   Version DOI 10.5281/zenodo.21888130.
   https://doi.org/10.5281/zenodo.21888130
2. IBM Granite Team: Granite-4.2-3B model card, 25 August 2026.
   https://huggingface.co/ibm-granite/granite-4.2-3b
   Candidate revision: https://huggingface.co/ibm-granite/granite-4.2-3b/tree/be9e7d995f2a6be22def5dd815f9f2bae98c8b6e
3. IBM: Adding generative chat function to your applications with the chat API.
   https://www.ibm.com/docs/en/watsonx/saas?topic=code-chat
4. IBM: Adding MCP server tools to a single agent.
   https://www.ibm.com/docs/en/watsonx/watson-orchestrate/base?topic=server-adding-mcp-tools-single-agent
5. IBM Research: SOFAI-LM: A Cognitive Architecture for Building Efficient and Reliable Reasoning Systems with LLMs, AAAI 2026, 20 January 2026.
   https://research.ibm.com/publications/sofai-lm-a-cognitive-architecture-for-building-efficient-and-reliable-reasoning-systems-with-llms
6. IBM Research: Neuro-Vector-Symbolic Architecture.
   https://research.ibm.com/projects/neuro-vector-symbolic-architecture
