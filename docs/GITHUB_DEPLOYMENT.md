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
