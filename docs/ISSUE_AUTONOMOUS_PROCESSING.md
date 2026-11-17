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
