#!/usr/bin/env bash
# Usage: im qik-vrt-Checkout ausfuehren:  bash apply_claude_mirror_bundle.sh <bundle> [--no-push]
set -euo pipefail
BUNDLE="$1"; MODE="${2:-push}"
SHA=d0b1c993e9c6edfeddd227310c2a7d9662eace2b2bfc97ede4e40978fdc466b0
BASE=a38455c739f7f475b2a93447de1db4ea87e4200c
HEAD_EXP=dae356e4df1b3892e58768047b1a5edd1e68c52e
REF=communication/claude/mirror-20261020T1827Z
[ "$(sha256sum "$BUNDLE" | cut -c1-64)" = "$SHA" ] || { echo "HOLD bundle sha256"; exit 1; }
git cat-file -e "$BASE^{commit}" 2>/dev/null || git fetch -q origin main
git cat-file -e "$BASE^{commit}" || { echo "HOLD base commit missing"; exit 1; }
git fetch -q "$BUNDLE" "$REF:$REF"
[ "$(git rev-parse "$REF")" = "$HEAD_EXP" ] || { echo "HOLD head mismatch"; exit 1; }
git merge-base --is-ancestor "$BASE" "$REF" || { echo "HOLD not ff from base"; exit 1; }
WT=$(mktemp -d); git worktree add -q --detach "$WT" "$REF"
( cd "$WT" && python3 -B tools/qikvrt_integrity.py verify ) | tail -1 | grep -q '^PASS' || { git worktree remove --force "$WT"; echo "HOLD integrity"; exit 1; }
git worktree remove --force "$WT"
if [ "$MODE" = "--no-push" ]; then echo "PASS dry-run $HEAD_EXP"; exit 0; fi
git push origin "$REF" && echo "PASS pushed $REF $HEAD_EXP"
