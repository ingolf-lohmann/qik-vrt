# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
BIN="./build/qikvrt_verify"
ROOT="${TMPDIR:-/tmp}/qikvrt_bootstrap_test_$$"
rm -rf "$ROOT"
mkdir -p "$ROOT/qikvrt"
"$BIN" --selftest-bootstrap > "$ROOT/selftest.out"
grep -q "PASS QIKVRT bootstrapper GUID selftest" "$ROOT/selftest.out"
"$BIN" --bootstrap "$ROOT" > "$ROOT/bootstrap1.out"
grep -q "PASS QIKVRT bootstrapper" "$ROOT/bootstrap1.out"
test -s "$ROOT/qikvrt/runtime/REPOSITORY_GUID.txt"
GUID1=`cat "$ROOT/qikvrt/runtime/REPOSITORY_GUID.txt"`
"$BIN" --bootstrap "$ROOT" > "$ROOT/bootstrap2.out"
GUID2=`cat "$ROOT/qikvrt/runtime/REPOSITORY_GUID.txt"`
test "$GUID1" = "$GUID2"
grep -q "BOOTSTRAP_GUID_READY" "$ROOT/qikvrt/runtime/BOOTSTRAP_LEDGER.jsonl"
case "$GUID1" in ????????-????-????-????-????????????) : ;; *) echo "invalid guid"; exit 1 ;; esac
rm -rf "$ROOT"
echo "PASS bootstrapper gates"
