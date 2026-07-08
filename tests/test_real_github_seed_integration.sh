# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --selftest-real-github-seed-integration >/tmp/qikvrt_selftest_real_github_seed_integration.out
./build/qikvrt_verify --validate-github-seed-manifest qikvrt/reference/GITHUB_SEED_LIVE_MANIFEST_REFERENCE.json >/tmp/qikvrt_validate_github_seed_manifest.out
grep -q 'Goldkelch/qik-vrt' docs/REAL_GITHUB_SEED_INTEGRATION.md
grep -q 'raw.githubusercontent.com' docs/REAL_GITHUB_SEED_INTEGRATION.md
grep -q 'minimal regression' docs/REAL_GITHUB_SEED_INTEGRATION.md
grep -q 'REAL_GITHUB_SEED_INTEGRATION' qikvrt/gates/REAL_GITHUB_SEED_INTEGRATION_GATES.json
grep -q 'GITHUB_REPOSITORY_REACHABLE' qikvrt/gates/REAL_GITHUB_SEED_INTEGRATION_GATES.json
grep -q 'NO_GLOBAL_ADDRESS_SCAN' qikvrt/gates/REAL_GITHUB_SEED_INTEGRATION_GATES.json
grep -q 'PASS_REFERENCE' qikvrt/ledger/REAL_GITHUB_SEED_INTEGRATION_REFERENCE_LEDGER.jsonl
printf '%s
' 'PASS real GitHub seed integration gates'
