#!/usr/bin/env bash
# Run inside the qik-vrt checkout:
#   bash scripts/apply_claude_mirror_bundle.sh <bundle> [--no-push|--push]
# Safe default is --no-push. Remote mutation requires explicit --push.
set -euo pipefail

usage() {
  echo "Usage: $0 <bundle> [--no-push|--push]" >&2
}

if [[ $# -lt 1 || $# -gt 2 ]]; then usage; exit 64; fi
BUNDLE=$1
MODE=${2:---no-push}
case "$MODE" in
  --no-push|--push) ;;
  *) usage; exit 64 ;;
esac
[[ -f "$BUNDLE" && -r "$BUNDLE" ]] || { echo "HOLD bundle missing or unreadable"; exit 1; }

EXPECTED_SHA=d0b1c993e9c6edfeddd227310c2a7d9662eace2b2bfc97ede4e40978fdc466b0
BASE=a38455c739f7f475b2a93447de1db4ea87e4200c
HEAD_EXP=dae356e4df1b3892e58768047b1a5edd1e68c52e
REF=communication/claude/mirror-20261020T1827Z
TMP_REF="refs/qikvrt/verify/claude-mirror-$$"
WT=""
VERIFY_LOG=""
cleanup() {
  if [[ -n "$WT" && -d "$WT" ]]; then git worktree remove --force "$WT" >/dev/null 2>&1 || true; fi
  if [[ -n "$VERIFY_LOG" ]]; then rm -f "$VERIFY_LOG"; fi
  git update-ref -d "$TMP_REF" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL_SHA=$(sha256sum "$BUNDLE" | awk '{print $1}')
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL_SHA=$(shasum -a 256 "$BUNDLE" | awk '{print $1}')
else
  echo "HOLD: neither sha256sum nor shasum is available"; exit 1
fi
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || { echo "HOLD bundle sha256"; exit 1; }

git rev-parse --show-toplevel >/dev/null 2>&1 || { echo "HOLD not inside a Git checkout"; exit 1; }
git remote get-url origin >/dev/null 2>&1 || { echo "HOLD origin remote missing"; exit 1; }

git cat-file -e "$BASE^{commit}" 2>/dev/null || git fetch -q origin main
git cat-file -e "$BASE^{commit}" 2>/dev/null || { echo "HOLD base commit missing"; exit 1; }

git bundle verify "$BUNDLE" || { echo "HOLD bundle verify"; exit 1; }
git fetch -q "$BUNDLE" "$REF:$TMP_REF"
[[ "$(git rev-parse "$TMP_REF")" == "$HEAD_EXP" ]] || { echo "HOLD head mismatch"; exit 1; }
git merge-base --is-ancestor "$BASE" "$TMP_REF" || { echo "HOLD not ff from base"; exit 1; }

WT=$(mktemp -d)
VERIFY_LOG=$(mktemp)
git worktree add -q --detach "$WT" "$TMP_REF"
(
  cd "$WT"
  set -o pipefail
  python3 -B tools/qikvrt_integrity.py verify | tee "$VERIFY_LOG"
) || { echo "HOLD integrity command failed"; exit 1; }
grep -q '^PASS' "$VERIFY_LOG" || { echo "HOLD integrity"; exit 1; }
git worktree remove --force "$WT"
WT=""

if [[ "$MODE" == "--no-push" ]]; then
  echo "PASS local verification only; no remote mutation; candidate=$HEAD_EXP"
  exit 0
fi

# Never overwrite or rewind a remote ref. If it exists, it must be an ancestor
# of the candidate commit for this to be a fast-forward update.
REMOTE_LINE=$(git ls-remote --heads origin "$REF")
if [[ -n "$REMOTE_LINE" ]]; then
  REMOTE_HEAD=$(awk 'NR==1 {print $1}' <<<"$REMOTE_LINE")
  git fetch -q origin "$REF"
  git merge-base --is-ancestor "$REMOTE_HEAD" "$TMP_REF" || {
    echo "HOLD remote ref is not an ancestor of candidate; refusing push"; exit 1;
  }
fi

git push --dry-run origin "$TMP_REF:$REF" || { echo "HOLD push dry-run failed"; exit 1; }
git push origin "$TMP_REF:$REF"
echo "PASS push accepted by origin; independent readback and ACCEPT still required; candidate=$HEAD_EXP"
