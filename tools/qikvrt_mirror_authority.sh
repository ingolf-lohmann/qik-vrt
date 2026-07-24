#!/usr/bin/env bash
set -euo pipefail

readonly AUTHORITY_URL="https://github.com/Goldkelch/qik-vrt.git"
readonly AUTHORITY_COMMIT="3d640b05e815ff8644fe7640ddd7dcf89d4094c4"
readonly EXPECTED_MIRROR_BASE_COMMIT="ac05aeff4835aeab049a22f3b6271c3224856dc2"
readonly TARGET_BRANCH="mirror/manuscript-formalization-v2-completion"

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

if git remote get-url authority >/dev/null 2>&1; then
  git remote set-url authority "$AUTHORITY_URL"
else
  git remote add authority "$AUTHORITY_URL"
fi

git fetch --no-tags --prune authority +refs/heads/main:refs/remotes/authority/main
git fetch --no-tags --prune origin +refs/heads/main:refs/remotes/origin/main

git cat-file -e "$AUTHORITY_COMMIT^{commit}"
git merge-base --is-ancestor "$AUTHORITY_COMMIT" refs/remotes/authority/main

mirror_parent="$(git rev-parse refs/remotes/origin/main)"
authority_tree="$(git rev-parse "$AUTHORITY_COMMIT^{tree}")"
git merge-base --is-ancestor "$EXPECTED_MIRROR_BASE_COMMIT" "$mirror_parent"

unexpected="$(
  git diff --name-only "$EXPECTED_MIRROR_BASE_COMMIT" "$mirror_parent" |
    grep -Ev '^(.github/workflows/qikvrt_batch04_integrity.yml|.github/workflows/qikvrt_ci.yml|.github/workflows/qikvrt_mirror_authority_main.yml|.qikvrt/evidence/mirror-bootstrap-final-retrigger.json|REPOSITORY_FILE_MANIFEST.json|REPOSITORY_FILE_MANIFEST.json.sha256|SHA256SUMS.txt|tools/qikvrt_mirror_authority.sh)$' || true
)"
if [[ -n "$unexpected" ]]; then
  printf 'BLOCK unexpected bootstrap paths:\n%s\n' "$unexpected" >&2
  exit 1
fi

export GIT_AUTHOR_DATE="$(git show -s --format=%aI "$AUTHORITY_COMMIT")"
export GIT_COMMITTER_DATE="$(git show -s --format=%cI "$AUTHORITY_COMMIT")"

message="Mirror completed 62-page manuscript formalization

Authority commit: $AUTHORITY_COMMIT
Authority tree: $authority_tree
Mirror parent: $mirror_parent

Exact verified authority tree persisted with mirror main as first parent and authority commit as second parent."

mirror_commit="$(
  printf '%s\n' "$message" |
    git commit-tree "$authority_tree" -p "$mirror_parent" -p "$AUTHORITY_COMMIT"
)"

git push --force-with-lease origin "$mirror_commit:refs/heads/$TARGET_BRANCH"
remote_commit="$(git ls-remote origin "refs/heads/$TARGET_BRANCH" | awk '{print $1}')"
[[ "$remote_commit" == "$mirror_commit" ]]
remote_tree="$(git rev-parse "$remote_commit^{tree}")"
[[ "$remote_tree" == "$authority_tree" ]]

printf 'PASS mirror commit=%s tree=%s\n' "$mirror_commit" "$remote_tree"
