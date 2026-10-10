# GitHub REST API execution and continuation

Use `GITHUB_ROUTE=REST_API_ONLY` and the existing authenticated connection.
Read `/AI` and its required evidence before execution. A callable REST POST,
an appropriate repository-scoped credential, and native workflow admission
must each be established; a successful GET does not establish any of them.
Never replace missing initial admission with a rerun, proxy trigger, browser
login, or permission expansion.

## Dispatch adapter contract 2.1.0

`api/qikvrt_github_api.openapi.yaml` remains compatible with 2.0.0 requests.
The four operations and existing effect gates are unchanged. The optional
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
