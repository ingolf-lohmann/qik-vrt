<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Owner-local durable Universal Terminal input

This PR-454 successor extends `src/qikvrt_effect_ack_http_terminal.py` with
`durable-prepare`, `durable-commit`, and `durable-readback` CLI operations.
They are clients of the **existing** `state/temdd/ingress.sock`. The ordinary
HTTP server retains its process-local input scope and has no durable writer.
No new listener, socket, network route, permission change, deployment, merge,
publication, or governance repair is introduced.

## Exact effect and boundary

The bounded effect is one `OBSERVE` event carrying a canonical JSON text input,
its SHA-256, and its transputer-native provenance in the existing SQLite ledger.
This is an input observation, not acceptance of every claim in its text.
Only bounded text is admitted; audio/video persistence is not enabled.

Prepare reads the existing ledger identity and validates the route. It inserts
no event. Its hash binds the canonical input, complete native event, exact
repository/PR/HEAD/TREE subject, ledger epoch, state directory, random native ID,
and 120-second expiry. The CLI requires a clean checkout, the matching `origin`,
and explicitly supplied expected HEAD and TREE. The ledger additionally rejects
a subject that differs from its running carrier. The source manuscript/PR cited
in an input must not be substituted for the carrier's subject.

Commit requires the independently supplied prepare hash and unchanged input,
subject and route. It validates the owner-only directory, UID, non-symlink
paths, mode-0600 existing socket, and Linux `SO_PEERCRED` owner UID. It performs
one bounded JSON-line send, with a five-second socket timeout, to the existing
Unix ingress. It never writes SQLite directly or changes file permissions.

After the ingress response, the client opens a **fresh read-only SQLite
connection** and verifies the ledger epoch, native ID and digest, exact subject,
binding, stored body, payload digest, `evidence_transfer=DENY`, `dod=false`, and
body digest. The reply must equal that independently read durable event. A
`PERSISTED` string or successful transport alone cannot produce a receipt.

Repeating a committed preparation is refused before sending. The ingress's
existing unique `(source,native_id)` constraint limits concurrent copies to one
effect. After a lost or inconsistent response, use `durable-readback` with the
same preparation, input and hash; do not generate another native ID or blindly
repeat Commit. Readback remains usable after expiry and process restart. A
changed subject or ledger epoch never inherits predecessor evidence.

All adapter receipts retain `EFFECT_ACK_DONE=false`, `ordinary_release=false`,
`authority_effect=false`, and `public_readback_verified=false`. A local durable
receipt proves its bounded local input effect only. Public SSE replay and
product acceptance remain separate observations and gates.

## Owner-side invocation after verified deployment

Run inside the clean verified carrier checkout under the existing ledger owner's
UID. Use the carrier subject from its fresh `/api/temdd/subject` readback and
verified Git checkout, not PR-454's predecessor values. Protect the preparation
file with the existing owner-only state-directory boundary (`umask 077`).

```sh
python3 -B src/qikvrt_effect_ack_http_terminal.py durable-prepare \
  --root /opt/qikvrt --state-dir /var/lib/qikvrt/state \
  --repository <verified-carrier-repository> --pr <verified-carrier-pr> \
  --expected-head <verified-head> --expected-tree <verified-tree> \
  --input <exact-input-file> > <owner-only-preparation-file>

python3 -B src/qikvrt_effect_ack_http_terminal.py durable-commit \
  --root /opt/qikvrt --state-dir /var/lib/qikvrt/state \
  --repository <verified-carrier-repository> --pr <verified-carrier-pr> \
  --expected-head <verified-head> --expected-tree <verified-tree> \
  --input <same-input-file> --prepared <same-preparation-file> \
  --prepare-hash <independently-verified-prepare-hash>
```

For recovery or a fresh post-restart observation, use the same Commit arguments
with operation `durable-readback`. Neither this document nor the plan itself
grants permission for another effect.

After a supported exact-byte deployment and owner-local Commit, verify that the
same event ID, ledger digest, input hash and carrier subject are replayed by
the existing durable `/api/temdd/events` SSE stream through its public proxy.
Record fresh response bytes, UTC observation time, subject envelope and replay
cursor. A live old event or old PR-1236 envelope does not close PR-454's gap.

## Verification scope and remaining blocker

The new cases are included in the existing
`tests.test_qikvrt_effect_ack_http_terminal` module and therefore in the existing
`QIKVRT EFFECT_ACK HTTP Firefox terminal` workflow. They use actual Unix sockets
and SQLite WAL/FULL commits in an **independent contract fixture**, exercising
prepare-without-event, commit, restart, concurrent/duplicate input, tampering,
expiry, subject/epoch drift, unsafe permissions/symlinks/peer UID, false ACK,
corrupt durable readback, lost-response recovery and the real CLI.

The fixture implements the native-event and SQL contract reported by Railway's
read-only source inspection. It is not the deployed daemon: that module and the
Universal Terminal deployment files are absent from this Mirror candidate.
Source excerpts are agent-reported observations, not byte-exact source delivery
or an independently verified full-source hash. A malformed earlier reported
hash was rejected and is not used as evidence.

The Work environment refuses AF_UNIX creation with `EPERM`; this is recorded
as a local execution blocker, not a passing Unix test or a reason to omit the
hosted Linux tests. The existing HTTP tests and the negative control denying
HTTP durable routes can run locally. Exact-head hosted results must be read back
before claiming the complete test module passes.

Railway exposes configuration and redeployment of existing builds, but the
current service bootstraps its exact checkout from `Goldkelch/qik-vrt`.
That repository is unavailable to this session's GitHub connection/Git route,
and no container exec, source write, or local Unix submit capability is exposed.
An old-build redeployment cannot install this Mirror successor. Source switching,
startup-code injection, a new public writer, or governance bypass is outside
this repair. The productive persistence gap therefore remains open until an
authorized exact-byte carrier path and fresh public durable replay are verified.

Human purpose and constraints: Ingolf Lohmann. Implementation, contract tests,
diagnostics and successor evidence: OpenAI Codex, artificial cognition.
