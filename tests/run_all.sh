# QIKVRT Artifact Header
# Version: 2.13.4
# Author / Urheber: Ingolf Lohmann
# Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
# License: Software source code licensed under Apache-2.0 unless otherwise stated.
# Non-software texts/docs: CC BY-NC-ND 4.0 unless otherwise stated.
# Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.

#!/bin/sh
set -eu
./build/qikvrt_verify --verify docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md >/tmp/qikvrt_verify_doc.out
./build/qikvrt_verify --verify-repo . >/tmp/qikvrt_verify_repo.out
./build/qikvrt_verify --selftest-multicast >/tmp/qikvrt_selftest_multicast.out
./build/qikvrt_verify --selftest-ontology >/tmp/qikvrt_selftest_ontology.out
./build/qikvrt_verify --selftest-governance >/tmp/qikvrt_selftest_governance.out
./build/qikvrt_verify --selftest-active >/tmp/qikvrt_selftest_active.out
./build/qikvrt_verify --selftest-watchdog >/tmp/qikvrt_selftest_watchdog.out
./build/qikvrt_verify --selftest-bootstrap >/tmp/qikvrt_selftest_bootstrap.out
./build/qikvrt_verify --selftest-tcpip-autonomy >/tmp/qikvrt_selftest_tcpip_autonomy.out
./build/qikvrt_verify --selftest-damage-containment >/tmp/qikvrt_selftest_damage_containment.out
./build/qikvrt_verify --selftest-autonomous-discovery >/tmp/qikvrt_selftest_autonomous_discovery.out
./build/qikvrt_verify --selftest-github-seed-discovery >/tmp/qikvrt_selftest_github_seed_discovery.out
./build/qikvrt_verify --selftest-real-github-seed-integration >/tmp/qikvrt_selftest_real_github_seed_integration.out
./build/qikvrt_verify --selftest-zip-layout >/tmp/qikvrt_selftest_zip_layout.out
./build/qikvrt_verify --selftest-windows-shell-zip >/tmp/qikvrt_selftest_windows_shell_zip.out
./build/qikvrt_verify --selftest-short-path >/tmp/qikvrt_selftest_short_path.out
./build/qikvrt_verify --selftest-live-evidence >/tmp/qikvrt_selftest_live_evidence.out
./build/qikvrt_verify --selftest-claim-matrix >/tmp/qikvrt_selftest_claim_matrix.out
./build/qikvrt_verify --selftest-node-onboarding >/tmp/qikvrt_selftest_node_onboarding.out
./build/qikvrt_verify --selftest-rest-api >/tmp/qikvrt_selftest_rest_api.out
./build/qikvrt_verify --selftest-unified-node-core >/tmp/qikvrt_selftest_unified_node_core.out
./build/qikvrt_verify --selftest-node-onboarding-testbed >/tmp/qikvrt_selftest_node_onboarding_testbed.out
./build/qikvrt_verify --selftest-license-visibility >/tmp/qikvrt_selftest_license_visibility.out
./build/qikvrt_verify --selftest-full-test-env >/tmp/qikvrt_selftest_full_test_env.out
./build/qikvrt_verify --selftest-seed-node-delivery >/tmp/qikvrt_selftest_seed_node_delivery.out
./build/qikvrt_verify --selftest-bilingual-docs >/tmp/qikvrt_selftest_bilingual_docs.out
./build/qikvrt_verify --selftest-github-deploy >/tmp/qikvrt_selftest_github_deploy.out
./build/qikvrt_verify --selftest-repository-setup >/tmp/qikvrt_selftest_repository_setup.out
./build/qikvrt_verify --validate-live-evidence qikvrt/evidence/GH_WEB_REF.json >/tmp/qikvrt_validate_live_evidence.out
./build/qikvrt_verify --validate-root-layout . >/tmp/qikvrt_validate_root_layout.out
sh tests/test_content.sh
sh tests/test_boundaries.sh
sh tests/test_multicast.sh
sh tests/test_ontology.sh
sh tests/test_governance.sh
sh tests/test_active_layer.sh
sh tests/test_watchdog.sh
sh tests/test_bootstrapper.sh
sh tests/test_tcpip_autonomy.sh
sh tests/test_autonomous_discovery.sh
sh tests/test_github_seed_discovery.sh
sh tests/test_real_github_seed_integration.sh
sh tests/test_zip_layout.sh
sh tests/test_windows_shell_zip.sh
sh tests/test_sp.sh
sh tests/test_le.sh
sh tests/test_cm.sh
sh tests/test_no.sh
sh tests/test_ra.sh
sh tests/test_uc.sh
sh tests/test_nt.sh
sh tests/test_wk.sh
sh tests/test_lc.sh
sh tests/test_ft.sh
sh tests/test_sd.sh
sh tests/test_bi.sh
sh tests/test_gd.sh
sh tests/test_rs.sh
sh tests/test_cb.sh
sh tests/test_ms.sh
sh tests/test_gt.sh
sh tests/test_requirements_full.sh
sh tests/test_unit_full.sh
sh tests/test_integration_full.sh
sh tests/test_acceptance_full.sh
sh tests/test_performance_full.sh
sh tests/test_security_full.sh
sh tests/test_node_git_tag_release.sh
sh tests/test_hashes.sh
echo 'PASS POSIX acceptance suite v2.13.4'
