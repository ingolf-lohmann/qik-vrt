# Repository-bound local language model

Owner instruction: Ingolf Lohmann, 23 October 2026, authorized permanent
integration and autonomous AI operation. Authorization persists across clients;
it does not establish a productive host, peer admission or successful effects.
The repository remains the durable authority; the HMI is replaceable.

The existing Personal adapter of the Universal Terminal now accepts the pinned
SmolLM3 3B Q4_K_M model through llama.cpp. Model weights, tokenizer and chat
template are contained in the GGUF. The lock records immutable source revision,
byte counts, SHA-256 and separate upstream licenses. No proprietary ChatGPT
weights, hidden configuration or account memory are exported by this work.
This is generative text inference, not the existing embedding-only retrieval.
Claims about quality, coding correctness, multilingual performance or complete
equivalence with another model require their own evaluations.

## Existing REST and private state

The adapter extends `src/qikvrt_effect_ack_http_terminal.py`; it does not create
a second QIK-VRT executor. Authenticated humans and machines use the same
`/personal/create`, `/personal/turn`, `/personal/resume`, `/personal/session/<id>`
and `/personal/capabilities` contracts. The existing same-origin, Host, body,
confirmation and authentication guards remain in force. Local inference does
not confer authority to run model-generated code, merge, spend or deploy.
Original native Terminal/Transputer admission and event/effect checks still
govern actions. The model drafts; the existing admitted executor applies
authorized actions and independently verifies their effects.

For a registered protected Owner profile on Linux x86_64:

```sh
python3 -B src/qikvrt_effect_ack_http_terminal.py --operation serve \
  --personal-state-dir /private/qikvrt/personal-local \
  --personal-auth-config /private/qikvrt/registered-owner-oidc.json \
  --personal-provider local \
  --personal-model qikvrt-smollm3-3b-q4-k-m \
  --personal-local-model-dir /private/qikvrt/local-llm
```

Development
memory pairing is explicitly separate from productive OIDC acceptance and must
not be reported as that acceptance. The local model requires no provider API
credential or paid inference subscription. Protected identity still requires
its actual registered Owner profile and OS Secret Service binding.

Place the two exact locked artifacts in the model directory. There is no
automatic download or fallback. The adapter hashes both regular files before
launch; symlinks, unsafe writable files and altered bytes are rejected. It
passes the verified model inode to the child, extracts the verified runtime
archive into an owner-private temporary directory, keeps its bundled license
notices, disables inherited proxies and environment overrides, and launches
offline CPU inference on authenticated loopback. No secret is written to argv,
the repository or the transcript. The ephemeral backend key exists in process
memory and the child environment only. Closing the adapter stops that child.

The model is bounded to two CPU threads, one slot, 4096 context tokens and 512
output tokens. Temperature and seed are fixed. Exact output equality across
hardware/runtime changes is not promised. Truncated, tool-bearing or wrong-model
responses are rejected. Request intent is persisted before generation; an
ambiguous result remains pending across restart and is not blindly regenerated.
Full transcripts, source hashes and observed checkpoints live outside the
repository in the existing SQLite WAL/FULL state. Restart preserves that state
and rejects changed model/settings bindings. It never inherits a prior
process's live model attestation.

## Artifact persistence and acceptance

`runtime/models/smollm3-3b-q4-k-m.lock.json` binds the reproducible artifacts.
`runtime/models/smollm3-3b-q4-k-m.parts.json` binds the ordered backup chunks.
The owner-controlled OneDrive partial corpus copy is an additional model
artifact carrier; Apple/iCloud remains the original corpus authority. Model
bytes are large external artifacts, not Git source blobs. Source manifests and
private artifact-carrier readbacks must never be confused with bytes embedded
in Git, a cryptographically authenticated publisher, or a productive runtime.
Reassemble all ordered chunks and verify the whole-model SHA-256 before use.

The offline restoration command checks every chunk and the whole output,
publishes each artifact atomically, and refuses to overwrite an existing file:

```sh
python3 -B tools/qikvrt_restore_local_llm.py \
  --parts-dir /private/qikvrt/model-backup \
  --model-dir /private/qikvrt/local-llm
```

The real-model receipt in `evidence/receipts/local-llm-rest-20261023.json` records
actual CPU generation through the existing authenticated REST adapter,
source-bound extraction, independent session readback, complete adapter/model
restart and checkpoint continuation. An additional actual model code-review draft is
retained as a descriptive draft: it exceeded the requested three-bullet limit
and is not used as independent correctness evidence or release approval.
Technical regression doubles remain
explicitly labelled and cannot attest live inference. Source changes after a
receipt require fresh dependent tests; passing tests do not make future
regressions impossible or prove absolute system integrity.

Productive Owner-host startup, protected identity, original adapter credential
binding, HMI-disconnected backlog continuation, peer ACK/reply, complete ChatGPT
corpus export/equality and exact `raumzeitterminal.de` delivery each remain
separately testable obligations. This module does not replace their admission,
create a timer/proxy executor or infer EFFECT_ACK_DONE from a model response.

## Upstream licensing

- SmolLM3-3B GGUF: Apache-2.0, as declared by its immutable upstream model card:
  <https://huggingface.co/ggml-org/SmolLM3-3B-GGUF/blob/4965cb60b150737b68a0408c36aeefb65078f894/README.md>.
- llama.cpp runtime: MIT plus the third-party notices in the exact locked
  archive. Preserve the archive's LICENSE and companion notices on distribution.
- QIK-VRT integration code retains its existing PolyForm-Noncommercial-1.0.0
  license. Availability of upstream model bytes does not change that boundary.
