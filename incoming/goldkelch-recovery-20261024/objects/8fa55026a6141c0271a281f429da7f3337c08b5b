# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --verify-repo . >/tmp/qikvrt_integration_repo.out
./build/qikvrt_verify --selftest-node-onboarding-testbed >/tmp/qikvrt_integration_node_testbed.out
./build/qikvrt_verify --selftest-github-seed-discovery >/tmp/qikvrt_integration_seed.out
./build/qikvrt_verify --selftest-real-github-seed-integration >/tmp/qikvrt_integration_real_seed.out
grep -q '127.0.0.1:8766' api/qikvrt_github_api.openapi.yaml
echo 'PASS full integration test layer'
