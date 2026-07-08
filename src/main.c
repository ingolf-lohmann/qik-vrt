/*
 * QIKVRT Artifact Header
 * Version: 2.13.4
 * Author / Urheber: Ingolf Lohmann
 * Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
 * License: Software source code licensed under Apache-2.0 unless otherwise stated.
 * Non-software texts/docs in this repository: CC BY-NC-ND 4.0 unless otherwise stated.
 * Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "qikvrt.h"

static void usage(const char *argv0) {
    printf("usage: %s <command> [argument]\n", argv0);
    printf("commands: --verify, --verify-repo, --bootstrap, --version\n");
    printf("selftests: multicast ontology governance active watchdog bootstrap\n");
    printf("selftests: tcpip-autonomy damage-containment autonomous-discovery\n");
    printf("selftests: github-seed real-github-seed zip-layout windows-shell-zip short-path live-evidence claim-matrix node-onboarding rest-api unified-node-core node-onboarding-testbed license-visibility full-test-env seed-node-delivery bilingual-docs github-deploy repository-setup\n");
    printf("validators: --validate-root-layout --validate-github-seed-manifest --validate-live-evidence\n");
}

static int print_result(const char *label, int rc, const struct qikvrt_result *result) {
    if (rc == 0) {
        printf("PASS %s v%s\n", label, QIKVRT_VERSION);
        printf("checks=%d failures=%d articles=%d\n", result->checks, result->failures, result->article_count);
        return 0;
    }
    printf("FAIL %s v%s\n", label, QIKVRT_VERSION);
    printf("checks=%d failures=%d articles=%d\n", result->checks, result->failures, result->article_count);
    return 1;
}

int main(int argc, char **argv) {
    struct qikvrt_result result;
    int rc;
    if (argc == 2 && strcmp(argv[1], "--version") == 0) { qikvrt_print_version(); return 0; }
    if (argc == 3 && strcmp(argv[1], "--verify") == 0) { rc = qikvrt_verify_file(argv[2], &result); return print_result("QIKVRT document verification", rc, &result); }
    if (argc == 3 && strcmp(argv[1], "--verify-repo") == 0) { rc = qikvrt_verify_repo(argv[2], &result); return print_result("QIKVRT repository GitHub seed discovery verification", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-multicast") == 0) { rc = qikvrt_selftest_multicast(&result); return print_result("QIKVRT multicast selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-ontology") == 0) { rc = qikvrt_selftest_ontology(&result); return print_result("QIKVRT ontology selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-governance") == 0) { rc = qikvrt_selftest_governance(&result); return print_result("QIKVRT constitutional governance selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-active") == 0) { rc = qikvrt_selftest_active(&result); return print_result("QIKVRT authorized active layer selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-watchdog") == 0) { rc = qikvrt_selftest_watchdog(&result); return print_result("QIKVRT watchdog keepalive selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-bootstrap") == 0) { rc = qikvrt_selftest_bootstrap(&result); return print_result("QIKVRT bootstrapper GUID selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-tcpip-autonomy") == 0) { rc = qikvrt_selftest_tcpip_autonomy(&result); return print_result("QIKVRT TCP/IP autonomy sanity selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-damage-containment") == 0) { rc = qikvrt_selftest_damage_containment(&result); return print_result("QIKVRT damage containment selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-autonomous-discovery") == 0) { rc = qikvrt_selftest_autonomous_discovery(&result); return print_result("QIKVRT autonomous discovery operation selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-github-seed-discovery") == 0) { rc = qikvrt_selftest_github_seed_discovery(&result); return print_result("QIKVRT GitHub seed discovery selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-real-github-seed-integration") == 0) { rc = qikvrt_selftest_real_github_seed_integration(&result); return print_result("QIKVRT real GitHub seed integration selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-zip-layout") == 0) { rc = qikvrt_selftest_zip_layout(&result); return print_result("QIKVRT ZIP layout compatibility selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-windows-shell-zip") == 0) { rc = qikvrt_selftest_windows_shell_zip(&result); return print_result("QIKVRT Windows Shell ZIP compatibility selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-short-path") == 0) { rc = qikvrt_selftest_short_path(&result); return print_result("QIKVRT short path package selftest", rc, &result); }

    if (argc == 2 && strcmp(argv[1], "--selftest-live-evidence") == 0) { rc = qikvrt_selftest_live_evidence(&result); return print_result("QIKVRT live evidence closure selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-claim-matrix") == 0) { rc = qikvrt_selftest_article_claim_matrix(&result); return print_result("QIKVRT article claim matrix selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-node-onboarding") == 0) { rc = qikvrt_selftest_node_onboarding(&result); return print_result("QIKVRT node onboarding selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-rest-api") == 0) { rc = qikvrt_selftest_rest_api(&result); return print_result("QIKVRT GitHub-compatible REST API contract selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-unified-node-core") == 0) { rc = qikvrt_selftest_unified_node_core(&result); return print_result("QIKVRT unified node core selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-node-onboarding-testbed") == 0) { rc = qikvrt_selftest_node_onboarding_testbed(&result); return print_result("QIKVRT unified node onboarding testbed selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-license-visibility") == 0) { rc = qikvrt_selftest_license_visibility(&result); return print_result("QIKVRT license and copyright visibility selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-full-test-env") == 0) { rc = qikvrt_selftest_full_test_environment(&result); return print_result("QIKVRT full reusable test environment selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-seed-node-delivery") == 0) { rc = qikvrt_selftest_seed_node_delivery(&result); return print_result("QIKVRT seed/node split delivery selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-bilingual-docs") == 0) { rc = qikvrt_selftest_bilingual_docs(&result); return print_result("QIKVRT bilingual documentation selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-github-deploy") == 0) { rc = qikvrt_selftest_github_deploy(&result); return print_result("QIKVRT generic GitHub deploy selftest", rc, &result); }
    if (argc == 2 && strcmp(argv[1], "--selftest-repository-setup") == 0) { rc = qikvrt_selftest_repository_setup(&result); return print_result("QIKVRT repository setup and persistent target selftest", rc, &result); }
    if (argc == 3 && strcmp(argv[1], "--validate-live-evidence") == 0) { char *buf; long size; FILE *fp; fp = fopen(argv[2], "rb"); if (fp == 0) { printf("FAIL QIKVRT live evidence file validation v%s\n", QIKVRT_VERSION); return 1; } fseek(fp, 0, SEEK_END); size = ftell(fp); fseek(fp, 0, SEEK_SET); buf = (char*)malloc((size_t)size + 1U); if (buf == 0) { fclose(fp); return 1; } if (fread(buf, 1U, (size_t)size, fp) != (size_t)size) { free(buf); fclose(fp); return 1; } fclose(fp); buf[size] = '\0'; rc = qikvrt_live_evidence_file_validate_text(buf, &result); free(buf); return print_result("QIKVRT live evidence file validation", rc, &result); }
    if (argc == 3 && strcmp(argv[1], "--validate-root-layout") == 0) { rc = qikvrt_repository_root_layout_validate(argv[2], &result); return print_result("QIKVRT repository root layout validation", rc, &result); }
    if (argc == 3 && strcmp(argv[1], "--validate-github-seed-manifest") == 0) { char *buf; long size; FILE *fp; fp = fopen(argv[2], "rb"); if (fp == 0) { printf("FAIL QIKVRT GitHub seed manifest validation v%s\n", QIKVRT_VERSION); return 1; } fseek(fp, 0, SEEK_END); size = ftell(fp); fseek(fp, 0, SEEK_SET); buf = (char*)malloc((size_t)size + 1U); if (buf == 0) { fclose(fp); return 1; } if (fread(buf, 1U, (size_t)size, fp) != (size_t)size) { free(buf); fclose(fp); return 1; } fclose(fp); buf[size] = '\0'; rc = qikvrt_real_github_seed_manifest_validate_text(buf, &result); free(buf); return print_result("QIKVRT GitHub seed manifest validation", rc, &result); }
    if (argc == 3 && strcmp(argv[1], "--bootstrap") == 0) { char guid[64]; rc = qikvrt_bootstrap_ensure_guid(argv[2], guid, (int)sizeof(guid)); if (rc == 0) { printf("PASS QIKVRT bootstrapper v%s\nGUID=%s\n", QIKVRT_VERSION, guid); return 0; } printf("FAIL QIKVRT bootstrapper v%s\n", QIKVRT_VERSION); return 1; }
    usage(argv[0]);
    return 2;
}
