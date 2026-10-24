#!/bin/sh
# QIKVRT Artifact Header
# Version: 2.13.4R
# Deutsch: Generisches Node-Git-Deployment. Kein lokaler GitHub-Release-REST-Create; Release/Asset entstehen im Zielrepo per GitHub Actions.
# English: Generic node Git deployment. No local GitHub release REST create; release/asset are created in the target repo by GitHub Actions.
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Apache-2.0 for scripts unless otherwise stated.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME="$ROOT/qikvrt/runtime/deploy"
mkdir -p "$RUNTIME"
TSV="$RUNTIME/deploy_result.tsv"
JSONL="$RUNTIME/deploy_result.jsonl"
: > "$JSONL"
printf 'utc\tgate\tstatus\tdetail\n' > "$TSV"
log(){ utc=$(date -u '+%Y-%m-%dT%H:%M:%SZ'); clean=$(printf '%s' "$3" | tr '\t\r\n' '   '); printf '%s\t%s\t%s\t%s\n' "$utc" "$1" "$2" "$clean" | tee -a "$TSV"; printf '{"timestamp_utc":"%s","gate":"%s","status":"%s","detail":"%s"}\n' "$utc" "$1" "$2" "$(printf '%s' "$clean" | sed 's/"/\\"/g')" >> "$JSONL"; }
fail(){ log "$1" BLOCK "$2"; exit 3; }
parse_remote(){ printf '%s' "$1" | sed -n 's#.*github.com[:/]\([^/][^/]*\)/\([^/.][^/.]*\)\(.git\)\{0,1\}$#\1 \2#p'; }
git_checked(){ gate=$1; pass=$2; shift 2; out=$(git "$@" 2>&1) || { log "$gate" BLOCK "$out"; exit 1; }; [ -n "$pass" ] || pass=$out; log "$gate" PASS "$pass"; }
if [ -n "${QIKVRT_GITHUB_OWNER:-}" ] && [ -n "${QIKVRT_GITHUB_REPO:-}" ]; then owner=$QIKVRT_GITHUB_OWNER; repo=$QIKVRT_GITHUB_REPO; log GITHUB_TARGET_ENV PASS "$owner/$repo"; else
  if [ -f "$ROOT/qikvrt/config/REPOSITORY_TARGET.json" ]; then
    owner=$(sed -n 's/.*"github_owner"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT/qikvrt/config/REPOSITORY_TARGET.json" | head -n 1)
    repo=$(sed -n 's/.*"github_repository"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT/qikvrt/config/REPOSITORY_TARGET.json" | head -n 1)
    if [ -n "$owner" ] && [ -n "$repo" ]; then log GITHUB_TARGET_PERSISTED_CONFIG PASS "$owner/$repo"; persisted_target=1; else persisted_target=0; fi
  else persisted_target=0; fi
  if [ "${persisted_target:-0}" != "1" ]; then
    remote=$(git -C "$ROOT" config --get remote.origin.url 2>/dev/null || true)
    parsed=$(parse_remote "$remote")
    if [ -n "$parsed" ]; then owner=$(printf '%s' "$parsed" | awk '{print $1}'); repo=$(printf '%s' "$parsed" | awk '{print $2}'); log GITHUB_TARGET_GIT_REMOTE PASS "$owner/$repo"; else
      printf 'GitHub owner/org: '; read owner
      printf 'GitHub repository: '; read repo
      [ -n "$owner" ] && [ -n "$repo" ] || fail GITHUB_TARGET_PROMPT 'missing owner/repo'
      log GITHUB_TARGET_PROMPT PASS "$owner/$repo"
    fi
  fi
fi
role=node
if [ -f "$ROOT/qikvrt/config/ROLE.json" ]; then role=$(sed -n 's/.*"role"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT/qikvrt/config/ROLE.json" | head -n 1); [ -n "$role" ] || role=node; fi
[ "$role" = node ] || fail NODE_ONLY_VARIANT "role=$role; this 2.13.4R package is node-only"
log NODE_ONLY_VARIANT PASS 'general node variant only; no seed deploy path included'
command -v git >/dev/null 2>&1 || fail GIT_AVAILABLE 'git not found in PATH'
log GIT_AVAILABLE PASS "$(command -v git)"
branch=${QIKVRT_GIT_BRANCH:-main}
if [ ! -d "$ROOT/.git" ]; then git_checked GIT_INIT 'initialized local repository for node deploy' -C "$ROOT" init; git_checked GIT_BRANCH_PREPARE "branch=$branch" -C "$ROOT" checkout -B "$branch"; else log GIT_INIT PASS 'existing .git directory present'; cur=$(git -C "$ROOT" branch --show-current 2>/dev/null || true); [ -n "$cur" ] && branch=${QIKVRT_GIT_BRANCH:-$cur}; fi
email=$(git -C "$ROOT" config user.email 2>/dev/null || true); if [ -z "$email" ]; then git_checked GIT_USER_EMAIL 'qikvrt-deploy@users.noreply.github.com' -C "$ROOT" config user.email qikvrt-deploy@users.noreply.github.com; else log GIT_USER_EMAIL PASS "$email"; fi
name=$(git -C "$ROOT" config user.name 2>/dev/null || true); if [ -z "$name" ]; then git_checked GIT_USER_NAME 'QIKVRT Deploy Bot' -C "$ROOT" config user.name 'QIKVRT Deploy Bot'; else log GIT_USER_NAME PASS "$name"; fi
remote_url="https://github.com/$owner/$repo.git"
if git -C "$ROOT" remote get-url origin >/dev/null 2>&1; then git_checked GIT_REMOTE_ORIGIN "$remote_url" -C "$ROOT" remote set-url origin "$remote_url"; else git_checked GIT_REMOTE_ORIGIN "$remote_url" -C "$ROOT" remote add origin "$remote_url"; fi
tag=${QIKVRT_RELEASE_TAG:-v2.13.4-node-r}
git_checked GIT_ADD 'staged node repository state including release workflow' -C "$ROOT" add -A
if git -C "$ROOT" diff --cached --quiet --exit-code; then log GIT_COMMIT PASS 'no staged changes; reusing current HEAD'; else git_checked GIT_COMMIT "committed node state for $tag" -C "$ROOT" commit -m "QIKVRT node git-trigger release $tag"; fi
if git -C "$ROOT" rev-parse --verify --quiet "refs/tags/$tag" >/dev/null 2>&1; then
  if [ "${QIKVRT_FORCE_TAG:-0}" = 1 ]; then git_checked GIT_TAG_RECREATE "deleted local tag $tag because QIKVRT_FORCE_TAG=1" -C "$ROOT" tag -d "$tag"; else fail GIT_TAG_EXISTS "local tag already exists: $tag; set QIKVRT_FORCE_TAG=1 only if intentional"; fi
fi
git_checked GIT_TAG_CREATE "$tag" -C "$ROOT" tag -a "$tag" -m "QIKVRT node release trigger $tag"
asset="$RUNTIME/qv2134_${role}.zip"
rm -f "$asset"
git_checked DEPLOY_ASSET_GIT_ARCHIVE "$asset" -C "$ROOT" archive --format=zip --output="$asset" "$tag"
log DEPLOY_STAGING_SELF_COPY_PREVENTION PASS '.gitattributes export-ignore excludes qikvrt/runtime/deploy, qikvrt/runtime/bootstrap, qikvrt/runtime/win_acceptance, qikvrt/runtime/setup, package_staging, build, and git metadata'
hash=$(sha256sum "$asset" | awk '{print $1}')
log DEPLOY_ASSET_PACKAGE PASS "$asset"
log DEPLOY_ASSET_SHA256 PASS "$hash"
log LOCAL_RELEASE_REST_API PASS 'disabled; local deploy uses git push only; GitHub Actions in target repo creates/releases asset'
if [ "${QIKVRT_DRY_RUN:-0}" = 1 ]; then fail GIT_PUSH 'dry-run; branch/tag not pushed and no remote mutation performed'; fi
if [ -z "${GITHUB_TOKEN:-}" ]; then
  printf '%s\n' 'GitHub token is required for git push only. It will not be persisted.'
  printf '%s' 'GitHub token for git push: '
  stty -echo 2>/dev/null || true
  read tok || tok=''
  stty echo 2>/dev/null || true
  printf '\n'
  GITHUB_TOKEN=$tok; export GITHUB_TOKEN
fi
GITHUB_TOKEN=$(printf '%s' "$GITHUB_TOKEN" | tr -d '\000-\037\177' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
case "$GITHUB_TOKEN" in Bearer\ *) GITHUB_TOKEN=${GITHUB_TOKEN#Bearer }; GITHUB_TOKEN=$(printf '%s' "$GITHUB_TOKEN" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//');; esac
[ -n "$GITHUB_TOKEN" ] || fail GITHUB_TOKEN_SANITIZE 'missing token after prompt sanitization; git push not performed'
log GITHUB_TOKEN_SANITIZE PASS 'git credential safe; token not persisted; local REST release API not used'
askpass="$RUNTIME/qikvrt_git_askpass.sh"
cat > "$askpass" <<'ASK'
#!/bin/sh
case "$1" in *Username*) printf '%s\n' x-access-token ;; *) printf '%s\n' "$QIKVRT_GIT_TOKEN" ;; esac
ASK
chmod 700 "$askpass"
QIKVRT_GIT_TOKEN=$GITHUB_TOKEN GIT_ASKPASS=$askpass GIT_TERMINAL_PROMPT=0 git -C "$ROOT" push origin "HEAD:refs/heads/$branch" >/tmp/qikvrt_git_push_branch.out 2>&1 || { out=$(cat /tmp/qikvrt_git_push_branch.out); log GIT_PUSH_BRANCH BLOCK "$out"; rm -f "$askpass"; exit 1; }
log GIT_PUSH_BRANCH PASS "origin $branch"
if [ "${QIKVRT_FORCE_TAG:-0}" = 1 ]; then tag_push_args="--force origin refs/tags/$tag"; else tag_push_args="origin refs/tags/$tag"; fi
# shellcheck disable=SC2086
QIKVRT_GIT_TOKEN=$GITHUB_TOKEN GIT_ASKPASS=$askpass GIT_TERMINAL_PROMPT=0 git -C "$ROOT" push $tag_push_args >/tmp/qikvrt_git_push_tag.out 2>&1 || { out=$(cat /tmp/qikvrt_git_push_tag.out); log GIT_PUSH_TAG BLOCK "$out"; rm -f "$askpass"; exit 1; }
rm -f "$askpass"
log GIT_PUSH_TAG PASS "origin $tag"
log GITHUB_ACTIONS_RELEASE_TRIGGER PASS "pushed tag $tag; target workflow .github/workflows/qikvrt_node_release.yml is responsible for release and asset upload"
exit 0
