#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test -f "$ROOT/QIKVRT.cmd"
test -f "$ROOT/QIKVRT.sh"
test -f "$ROOT/tools/setup_repository.ps1"
test -f "$ROOT/tools/setup_repository.sh"
test -f "$ROOT/tools/register_with_seed.ps1"
test -f "$ROOT/tools/register_with_seed.sh"
TMPROOT=/tmp/qikvrt_rs_test_$$
rm -rf "$TMPROOT"
mkdir -p "$TMPROOT"
cp -R "$ROOT/qikvrt" "$TMPROOT/qikvrt"
cp -R "$ROOT/tools" "$TMPROOT/tools"
cp "$ROOT/QIKVRT.sh" "$TMPROOT/QIKVRT.sh"
chmod +x "$TMPROOT/QIKVRT.sh"
cd "$TMPROOT"
QIKVRT_ACCEPT_LICENSE=1 QIKVRT_SETUP_NONINTERACTIVE=1 sh ./QIKVRT.sh setup > /tmp/qikvrt_setup_repo.out
test -s "$TMPROOT/qikvrt/runtime/REPOSITORY_GUID.txt"
test -s "$TMPROOT/qikvrt/config/REPOSITORY_TARGET.json"
test -s "$TMPROOT/qikvrt/config/ONBOARDING.json"
test -s "$TMPROOT/qikvrt/runtime/onboarding/SEED_REGISTRATION_REQUEST.json"
grep -q 'github_owner' "$TMPROOT/qikvrt/config/REPOSITORY_TARGET.json"
grep -q 'github_repository' "$TMPROOT/qikvrt/config/REPOSITORY_TARGET.json"
guid1=$(cat "$TMPROOT/qikvrt/runtime/REPOSITORY_GUID.txt")
QIKVRT_ACCEPT_LICENSE=1 QIKVRT_SETUP_NONINTERACTIVE=1 sh ./QIKVRT.sh setup > /tmp/qikvrt_setup_repo_2.out
guid2=$(cat "$TMPROOT/qikvrt/runtime/REPOSITORY_GUID.txt")
test "$guid1" = "$guid2"
rm -rf "$TMPROOT"
echo PASS repository setup persistence gates
