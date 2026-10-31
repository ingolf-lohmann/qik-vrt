<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. Implementation documentation: OpenAI Codex. -->
# EAP HTTP daemon and React DevOps client

The deployment target is the existing owner-controlled IONOS Linux VPS and
`https://raumzeitterminal.de/devops`. This is an extension of the existing S1
listener, OwnerREST adapter, original TEMDD Runtime/ledger, sealed package and
systemd supervisor. It adds no account, provider, alternate writer or scheduler.

## Protocol identity and scope

Author: Ingolf Lohmann. Core wire specification:
https://datatracker.ietf.org/doc/html/draft-lohmann-qikvrt-effect-ack-03

The published revision is an Experimental Internet-Draft. The HTTP
prepare/commit mapping reuses the repository's
`external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml` candidate; its presence
is not a claim of IETF publication or registration of those HTTP fields.

The full closed revision-03 wire adapter reuses `src/qikvrt_effect_ack.py`'s
decision engine. It checks Unicode NFC, duplicate/normalized member names,
I-JSON exact integers, JCS encoding, all five outcomes, each DONE condition,
policy/evidence digests, contiguous immutable input chains, authenticated
authority and the current private chain anchor. It does not infer evidence
truth or deployment conformance from hashes or tests.

This deployment profile protects **one bounded local effect**: accepting a text
input through the original admitted native OwnerREST/ledger. Text is an
observation, never a command to execute. Prepare may persist a CLASSIFY event
and a preparation; it does not persist the protected terminal input. Commit
requires a principal/method/target/input/policy/record/epoch/expiry-bound HMAC
ticket and validates the full wire record again. The original append and cold
SQLite readback supply the receipt. A repeated or ambiguous commit is resolved
through the original receipt, with no second input event.

## Activation in the existing private configuration

Use the existing sealed `temdd` profile, protected OwnerREST credentials,
source/configuration/volume pins and admitted host. Add the following fields
to that private configuration before its normal re-sealing and admission:

```json
{
  "terminal_profile": "temdd",
  "unix_ingress": false,
  "effect_ack_http": {
    "enabled": true,
    "public_origin": "https://raumzeitterminal.de"
  }
}
```

`owner_rest_grants` must name the real Principal and an existing owner-only
`token_file`, with `prepare`, `commit` and `readback` permissions. The internal
read-only terminal key is not an Owner capability. No credential is embedded
in source, HTML, exports or the deployment package. The React client retains
an explicitly entered Owner credential in component memory only.

With this profile enabled, the legacy `/api/owner/*` input mutation routes are
closed and the Unix input listener is disabled. These are mandatory profile
guards against an alternate path to the same protected input. Other admitted
Mesh operations retain their existing independent authority.

Run the existing `tools/qikvrt_self_host.py pack`/`verify` and
`run-admitted`/`supervisor` paths with the exact current source, package,
configuration and host-admission pins. The existing private mTLS Docker host
binding and CI production job are the remote deployment carrier. Neither this
document nor the new source fabricates those protected bindings. An existing
state volume is never reset or silently rebound. Use its existing migration
and verification procedure for a changed package/configuration.

## HTTP routes

| Route | Access | Meaning |
| --- | --- | --- |
| `/devops` | Read-only | React DevOps and EAP terminal |
| `/.well-known/effect-ack` | Anonymous GET | HTTP capability discovery; no release |
| `/api/eap/capabilities` | Anonymous GET | Exact version-1 core capability object |
| `/api/eap/state` | Anonymous GET | Exact admitted runtime subject; no private journal body |
| `/api/eap/effect` | Owner POST | Same exact body in Structured-Field prepare and commit |
| `/api/eap/records/{sha256}` | Owner GET | Full immutable wire record |
| `/api/eap/records/{sha256}/context` | Owner GET | Policy, evidence, chain and latest trusted hash |
| `/api/eap/receipts/{request_id}` | Owner GET | Original independently read SQLite receipt |

Protected requests use the existing `Authorization: Bearer …` and
`QIKVRT-Owner` fields. The public monitor forwards these original caller
credentials to the loopback adapter only after the same-origin check; it
never injects an internal key. Bound request bodies are limited to 32 KiB.

The client performs capability discovery, compact/full response binding checks and separate record/context reads,
independently rederives the state and verifies the policy/evidence/input/hash
bindings before enabling commit. After commit it separately reads the original
receipt and checks the principal, request, subject, original input, epoch and
native payload/body digests before displaying acceptance. A lost commit response leaves the operation
uncertain and exposes only the explicit receipt-readback continuation.

## Transport, restart and limits

Terminate public HTTPS on the existing host reverse proxy; leave native and
monitor listeners at their already admitted bindings. Keep the existing
systemd crash/restart controller and private native store. Request socket and
network I/O are bounded; the monotonic evaluator deadline is cooperative.
No per-request hard CPU-preemption guarantee is asserted. A hard wall-clock
guarantee requires an independently verified process supervisor.

The original engine can select timeout BLOCK for an entirely absent input,
while revision-03's closed grammar permits `input_hash=UNAVAILABLE` only for
NACK. This adapter fails closed when no valid wire record can be represented;
it never invents an input hash. The HTTP native-input profile accepts actual
bounded input bytes before evaluation and therefore avoids that combination.

The supplied `devops.html` capture is preserved as an explicitly historical
fallback (2026-10-27T12:25:19.056Z). Current data comes from the original
`/api/activity` and `/api/stream`; no client polling timer is added. JSONL
export hashes projection bytes and does not establish a ClickHouse import.

## Verification

`make conformance` includes the original core suite, revision-03 wire controls,
real local HTTP/SQLite prepare/commit/readback/restart tests and the actual
browser-side verifier. The React production runtime is reused byte-for-byte
under `runtime/self-host/REACT_LOCK.json`; no CDN or build tool is required on
the VPS. Local tests, repository integration, admitted VPS execution, public
TLS and useful exact-domain delivery each require their own readback.

## Mirror client and the three live prerequisites

`tools/qikvrt_eap_mirror_client.py` is the original Claude contribution recovered
from commit `75522c4911304efbe14fd9780c1a49bb7700e1f3`, tree
`3954495264e5e1fedbdcbac7d919189872c6810d`. The Authority source carrier
`mirror/eap-mirror-client-20261031` preserves that complete tree at the separate
REST import commit `9581951ff7c852fcb9dc425de49d3b029f79ceb8`. The original Git
bundle and independent ref/commit readbacks are retained with the client-delivery
evidence. The isolated `fix/eap-mirror-client-integration-20261031` candidate retains the
PR546 predecessor R1-R5 source and the client attribution. It has not replaced
the parallel PR546 formal-proof successor. Its negative-control repair rejects redirects before a
bearer credential can leave the request target and verifies both receipts against
the submitted input, principal, request, subject, observed ledger epoch and native
event digests. The unchanged source carrier remains available for comparison.

Source availability does not install the client in another node. A live run also
requires the actual Mirror's permitted HTTPS route to `raumzeitterminal.de` and
its protected host grant. The existing private `owner_rest_grants` mechanism must
bind the real principal (the original client fixture uses `claude:mirror`) to its
own mode-0600 token file and `prepare`, `commit`, `readback` permissions. The
existing normal seal, source/configuration pins and native host admission still
apply. An example entry, a token generated elsewhere or local token absence is
not proof of this remote grant. No grant or secret is created by a source import.

With that original protected binding available in the actual Mirror process,
the existing client invocation is:

```sh
python3 -B tools/qikvrt_eap_mirror_client.py \
  --base-url https://raumzeitterminal.de \
  --principal claude:mirror \
  --request-id "$QIKVRT_EAP_REQUEST_ID" \
  --text-file "$QIKVRT_EAP_TEXT_FILE"
```

The credential comes from `QIKVRT_EAP_TOKEN`, never from an argument, repository
file or report. Preserve the original request identifier and input bytes. A
connection refusal, HTTP525, missing token, unavailable readback or rejected
binding remains HOLD. An uncertain commit requires the existing receipt readback
for that request before another effect; the client performs no automatic retry.

`DELIVERED_TO_AUTHORITY_LEDGER` at this exact HTTPS origin requires all eight
HTTP200 steps and the live host's separate receipt readback. A loopback fixture
can test that sequence but cannot establish Mirror-to-Authority delivery. Even
the live receipt accepts one text observation only: it authorizes neither its
execution nor a merge, deployment or productive `EFFECT_ACK_DONE`.
