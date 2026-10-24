# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
BIN="${1:-./build/qikvrt_verify}"
ROOT="${2:-.}"
"$BIN" --selftest-github-seed-discovery >/tmp/qikvrt_github_seed_discovery.out
cat /tmp/qikvrt_github_seed_discovery.out
grep -q "PASS QIKVRT GitHub seed discovery selftest" /tmp/qikvrt_github_seed_discovery.out
grep -q "Goldkelch/qik-vrt" docs/GITHUB_SEED_DISCOVERY.md
grep -q "no service except seed" docs/GITHUB_SEED_DISCOVERY.md
grep -q "graph reachability" docs/GITHUB_SEED_DISCOVERY.md
grep -q "No final pass without GitHub seed discovery gates" qikvrt/gates/GITHUB_SEED_DISCOVERY_GATES.json
grep -q "no_global_address_scanning" qikvrt/manifests/GITHUB_SEED_DISCOVERY_MANIFEST.json
