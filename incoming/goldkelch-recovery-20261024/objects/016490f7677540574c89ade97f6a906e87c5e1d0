# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
grep -q "QIKVRT GitHub-Compatible Repository API" "$ROOT/docs/RA.md"
grep -q "qikvrt_github_api.openapi.yaml" "$ROOT/docs/RA.md"
grep -q "http://127.0.0.1:8766" "$ROOT/docs/RA.md"
grep -q "https://api.github.com" "$ROOT/docs/RA.md"
grep -q "/health" "$ROOT/docs/RA.md"
grep -q "workflow_dispatch" "$ROOT/docs/RA.md"
grep -q "repository_dispatch" "$ROOT/docs/RA.md"
grep -q "ingest" "$ROOT/docs/RA.md"
grep -q "verify" "$ROOT/docs/RA.md"
grep -q "stage" "$ROOT/docs/RA.md"
grep -q "release_status" "$ROOT/docs/RA.md"
grep -q "Seed nodes and normal nodes expose the same API" "$ROOT/docs/RA.md"
grep -q "openapi: 3.0.3" "$ROOT/api/qikvrt_github_api.openapi.yaml"
grep -q "QIKVRT GitHub-Compatible Repository API" "$ROOT/api/qikvrt_github_api.openapi.yaml"
"$ROOT/build/qikvrt_verify" --selftest-rest-api >/tmp/qikvrt_selftest_rest_api.out
grep -q "PASS QIKVRT GitHub-compatible REST API contract selftest" /tmp/qikvrt_selftest_rest_api.out
echo 'PASS GitHub-compatible REST API contract gates'
