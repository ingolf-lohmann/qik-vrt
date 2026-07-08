# QV2134P Node Git Idempotent Tag Push Repair

# QIKVRT V2.13.4P Node Git Idempotent Tag Push Repair

Status: SANDBOX_STATIC_VERIFIED_PENDING_EXTERNAL_WINDOWS_NODE_GIT_PUSH_RETEST
Role scope: node only
Base: V2.13.4H Windows inline script scope ledger repair

## Fixed defect

Previous node deploy built `qv2134_node.zip` and produced SHA256 evidence, but then failed at GitHub release lookup/create semantics for the node target repository. The local direct GitHub Release REST path could mask the real create error behind a blind `GET /releases/tags/<tag>` 404.

## Repair

2.13.4P removes local GitHub Release REST create/upload from the node deploy path.

Local deploy now performs only:

1. license/authorship acceptance,
2. repository target persistence,
3. Windows/POSIX acceptance gates,
4. local Git repository preparation,
5. commit of the node repository state,
6. annotated tag creation,
7. `git push` of branch and tag.

The target repository workflow `.github/workflows/qikvrt_node_release.yml` creates or updates the GitHub Release and uploads `qv2134_node.zip` plus `qv2134_node.zip.sha256` using the target repository's GitHub Actions context.

## Security and AV boundary

The local token is used only as a Git credential for `git push`; it is not persisted and it is not used for local GitHub Release REST API calls. The local direct release asset upload path is deprecated for this node variant.

## Non-regression gates

- NODE_ONLY_VARIANT
- LOCAL_RELEASE_REST_API_DISABLED
- GIT_PUSH_BRANCH
- GIT_PUSH_TAG
- GITHUB_ACTIONS_RELEASE_TRIGGER
- TARGET_WORKFLOW_CONTENTS_WRITE
- TARGET_WORKFLOW_RELEASE_ASSET_UPLOAD


## V2.13.4P follow-up repair

Bug class: `POWERSHELL_NATIVE_GIT_STDERR_MISCLASSIFIED_AS_TERMINATING_EXCEPTION`.

External Windows symptom: after `GIT_INIT PASS`, `git checkout -B main` printed the normal Git success line `Switched to a new branch 'main'`, but Windows PowerShell 5.1 surfaced the native stderr stream as a terminating error under the inline/StrictMode host. The deploy catch block then produced `NODE_GIT_DEPLOY_FINAL BLOCK` although the Git operation itself had succeeded.

Repair: Windows `tools/gh_deploy.ps1` now executes Git through `System.Diagnostics.Process` with explicit stdout/stderr capture and exit-code evaluation. Normal Git stderr output is audit text only. Only a non-zero Git exit code blocks deployment.

Preserved boundaries: node-only package, 4H technology basis, no local GitHub Release REST create/upload, release/asset creation remains delegated to target-repository GitHub Actions.


## V2.13.4P follow-up repair

Bug class: `POWERSHELL_OPTIONAL_GIT_PROBE_NO_REMOTE_ORIGIN_THROW`.

External Windows symptom after V2.13.4L: fresh `git init` succeeded, branch preparation succeeded, but the optional probe `git remote get-url origin` surfaced `error: No such remote 'origin'` as a terminating PowerShell error before the intended `git remote add origin ...` branch could run. The deploy catch block therefore reported `NODE_GIT_DEPLOY_FINAL BLOCK` although the absence of `origin` is the normal state of a fresh local repository.

Repair: all optional Git probes in `tools/gh_deploy.ps1` now use the same `System.Diagnostics.Process` wrapper as checked Git operations. `remote get-url origin`, `branch --show-current`, `config user.*`, `rev-parse`, and `diff --cached --quiet` are evaluated by native exit code. Missing `origin` now deterministically follows the `git remote add origin <target>` path; an existing origin follows `git remote set-url origin <target>`.

Preserved boundaries: node-only package, 4H/4K/4L technology basis, no local GitHub Release REST create/upload, release/asset creation remains delegated to target-repository GitHub Actions.


## V2.13.4P follow-up repair

Bug class: `NODE_GIT_PUSH_INTERACTIVE_CREDENTIAL_HANG`.

External Windows symptom after V2.13.4M: deployment reached `GIT_REMOTE_ORIGIN PASS add https://github.com/ingolf-lohmann/qik-vrt.git` and then appeared to hang. The missing subsequent rows (`GIT_ADD`, `GIT_COMMIT`, `GIT_TAG_CREATE`, `GIT_PUSH_BRANCH`, `GIT_PUSH_TAG`) indicate that a later Git process did not return a QIKVRT row. The likely hang class is an interactive Git Credential Manager / network credential prompt or an unbounded native Git process.

Repair: every Git process now runs with a hard timeout (`QIKVRT_GIT_TIMEOUT_SECONDS`, default 120 seconds), `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=Never`, `GCM_MODAL_PROMPT=0`, and `GIT_CREDENTIAL_INTERACTIVE=Never`. Push authentication no longer writes an AskPass token file and no longer depends on Credential Manager. The token is passed only for the push process via a non-persistent `http.https://github.com/.extraheader` value. If Git cannot authenticate or stalls, the deploy emits a deterministic BLOCK row instead of hanging.

Preserved boundaries: node-only package, 4H/4K/4L/4M technology basis, no local GitHub Release REST create/upload, release/asset creation remains delegated to target-repository GitHub Actions.


## V2.13.4P follow-up repair

Bug class: `POWERSHELL_FUNCTION_OUTPUT_ARRAY_CONTAMINATION` / `NODE_GIT_ARCHIVE_PATH_ARRAY_DRIVE_PARSE_FAILURE`.

External Windows symptom after V2.13.4N: deployment reached `DEPLOY_ASSET_GIT_ARCHIVE PASS` and `DEPLOY_STAGING_SELF_COPY_PREVENTION PASS`, then failed with `Das Laufwerk wurde nicht gefunden. Ein Laufwerk mit dem Namen " C" ist nicht vorhanden.` The sequence proves that the git archive existed and the failure occurred while treating the returned asset path as a PowerShell path. Root cause: PowerShell functions emit all uncaptured pipeline output, so helper functions such as `New-GitArchiveAsset` returned both internal `Invoke-GitChecked` text and the intended `$asset`. The resulting array was coerced into a space-joined string like `<path> <path>`, which PowerShell path parsing could misread as an invalid drive prefix.

Repair: helper functions now suppress internal `Invoke-GitChecked` outputs with `$null = ...` and return only scalar strings for branch and asset path. The local git line-ending policy is also set to `core.autocrlf=false` and `core.eol=lf` before staging to reduce CRLF warning noise. Node-only scope, noninteractive Git push, and GitHub Actions release architecture are preserved.


## V2.13.4P follow-up repair

Bug class: `NODE_LOCAL_TAG_EXISTS_IDEMPOTENCE_BLOCKS_PUSH_AFTER_PARTIAL_RUN`.

External Windows symptom after V2.13.4O: a previous run had created the local commit and local tag `v2.13.4-node`, then blocked at GitHub authorization. A subsequent run reused the same `.git` directory and correctly found no staged changes, but stopped at `GIT_TAG_EXISTS BLOCK` before attempting the now-authorized push. The package therefore needed idempotent local tag handling.

Repair: if the local release tag already exists and its peeled commit equals `HEAD`, the tag is reused and the deploy proceeds to archive and push. If the local tag points to a different commit, deployment still blocks unless `QIKVRT_FORCE_TAG=1` is explicitly set. Remote tag push is likewise idempotent: if the remote tag already exists and matches the local tag object, the push is treated as `PASS`; if the remote tag differs, it blocks unless force mode is explicit. Primary branch non-fast-forward rejection falls back to a node deploy branch `qikvrt-node/<tag>` while preserving auth/permission failures as hard blocks.
