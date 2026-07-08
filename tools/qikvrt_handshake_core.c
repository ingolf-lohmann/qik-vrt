/* SPDX-License-Identifier: Apache-2.0
 * Copyright (c) 2026 Ingolf Lohmann.
 * QIK-VRT ANSI/ISO C handshake core.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int contains_file(const char *path, const char *needle) {
    FILE *f;
    char buf[4096];
    int found = 0;
    f = fopen(path, "rb");
    if (!f) return 0;
    while (fgets(buf, sizeof(buf), f)) {
        if (strstr(buf, needle)) { found = 1; break; }
    }
    fclose(f);
    return found;
}

static void write_time(FILE *f) {
    time_t t = time((time_t*)0);
    fprintf(f, "%ld", (long)t);
}

static int write_seed_outputs(const char *guid, const char *source_repo, const char *seed_repo) {
    FILE *f;
    char path[512];
    sprintf(path, "registry/nodes/%s.json", guid);
#ifdef _WIN32
    system("if not exist registry mkdir registry");
    system("if not exist registry\\nodes mkdir registry\\nodes");
    system("if not exist evidence mkdir evidence");
    system("if not exist evidence\\seed_acceptance mkdir evidence\\seed_acceptance");
    system("if not exist ledger mkdir ledger");
#else
    system("mkdir -p registry/nodes evidence/seed_acceptance ledger");
#endif
    f = fopen(path, "wb");
    if (!f) return 2;
    fprintf(f, "{\n");
    fprintf(f, "  \"spdx_license_identifier\": \"CC-BY-NC-4.0\",\n");
    fprintf(f, "  \"copyright\": \"Copyright (c) 2026 Ingolf Lohmann\",\n");
    fprintf(f, "  \"qikvrt_record_type\": \"seed_node_registry_entry\",\n");
    fprintf(f, "  \"guid\": \"%s\",\n", guid);
    fprintf(f, "  \"repository\": \"%s\",\n", source_repo);
    fprintf(f, "  \"seed_repository\": \"%s\",\n", seed_repo);
    fprintf(f, "  \"status\": \"ACCEPTED\",\n");
    fprintf(f, "  \"acceptance_mode\": \"AUTONOMOUS_SEED_WORKFLOW\",\n");
    fprintf(f, "  \"boundaries\": {\n");
    fprintf(f, "    \"authorized_manifest_graph_only\": true,\n");
    fprintf(f, "    \"no_global_scanning\": true,\n");
    fprintf(f, "    \"no_self_propagation\": true,\n");
    fprintf(f, "    \"no_remote_mutation_without_authorization\": true\n");
    fprintf(f, "  }\n");
    fprintf(f, "}\n");
    fclose(f);

    f = fopen("registry/NODEMESH_INDEX.json", "wb");
    if (!f) return 3;
    fprintf(f, "{\n");
    fprintf(f, "  \"spdx_license_identifier\": \"CC-BY-NC-4.0\",\n");
    fprintf(f, "  \"copyright\": \"Copyright (c) 2026 Ingolf Lohmann\",\n");
    fprintf(f, "  \"qikvrt_nodemesh_index_version\": \"1.0\",\n");
    fprintf(f, "  \"seed_repository\": \"%s\",\n", seed_repo);
    fprintf(f, "  \"nodes\": [\n");
    fprintf(f, "    { \"guid\": \"%s\", \"repository\": \"%s\", \"status\": \"ACCEPTED\" }\n", guid, source_repo);
    fprintf(f, "  ]\n");
    fprintf(f, "}\n");
    fclose(f);

    sprintf(path, "evidence/seed_acceptance/%s.json", guid);
    f = fopen(path, "wb");
    if (!f) return 4;
    fprintf(f, "{\n");
    fprintf(f, "  \"spdx_license_identifier\": \"CC-BY-NC-4.0\",\n");
    fprintf(f, "  \"copyright\": \"Copyright (c) 2026 Ingolf Lohmann\",\n");
    fprintf(f, "  \"qikvrt_event\": \"AUTONOMOUS_SEED_ACCEPTANCE\",\n");
    fprintf(f, "  \"guid\": \"%s\",\n", guid);
    fprintf(f, "  \"repository\": \"%s\",\n", source_repo);
    fprintf(f, "  \"seed_repository\": \"%s\",\n", seed_repo);
    fprintf(f, "  \"status\": \"PASS\",\n");
    fprintf(f, "  \"created_epoch\": "); write_time(f); fprintf(f, "\n");
    fprintf(f, "}\n");
    fclose(f);

    f = fopen("ledger/NODE_REGISTRATION_LEDGER.jsonl", "ab");
    if (!f) return 5;
    fprintf(f, "{\"event\":\"AUTONOMOUS_SEED_ACCEPTANCE\",\"guid\":\"%s\",\"repository\":\"%s\",\"seed_repository\":\"%s\",\"status\":\"PASS\"}\n", guid, source_repo, seed_repo);
    fclose(f);
    return 0;
}

static int write_node_outputs(const char *guid, const char *source_repo, const char *seed_repo) {
    FILE *f;
#ifdef _WIN32
    system("if not exist qikvrt mkdir qikvrt");
    system("if not exist qikvrt\\runtime mkdir qikvrt\\runtime");
    system("if not exist qikvrt\\runtime\\onboarding mkdir qikvrt\\runtime\\onboarding");
    system("if not exist evidence mkdir evidence");
#else
    system("mkdir -p qikvrt/runtime/onboarding evidence");
#endif
    f = fopen("qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json", "wb");
    if (!f) return 6;
    fprintf(f, "{\n");
    fprintf(f, "  \"spdx_license_identifier\": \"CC-BY-NC-4.0\",\n");
    fprintf(f, "  \"copyright\": \"Copyright (c) 2026 Ingolf Lohmann\",\n");
    fprintf(f, "  \"qikvrt_event\": \"NODE_ACK_OF_SEED_ACCEPTANCE\",\n");
    fprintf(f, "  \"guid\": \"%s\",\n", guid);
    fprintf(f, "  \"repository\": \"%s\",\n", source_repo);
    fprintf(f, "  \"seed_repository\": \"%s\",\n", seed_repo);
    fprintf(f, "  \"status\": \"ACCEPTED_BY_SEED\"\n");
    fprintf(f, "}\n");
    fclose(f);
    f = fopen("evidence/node_seed_link_status.json", "wb");
    if (!f) return 7;
    fprintf(f, "{\n");
    fprintf(f, "  \"spdx_license_identifier\": \"CC-BY-NC-4.0\",\n");
    fprintf(f, "  \"copyright\": \"Copyright (c) 2026 Ingolf Lohmann\",\n");
    fprintf(f, "  \"qikvrt_event\": \"NODE_SEED_LINK_CONFIRMED\",\n");
    fprintf(f, "  \"guid\": \"%s\",\n", guid);
    fprintf(f, "  \"status\": \"PASS\"\n");
    fprintf(f, "}\n");
    fclose(f);
    return 0;
}

int main(int argc, char **argv) {
    const char *mode;
    const char *guid;
    const char *source_repo;
    const char *seed_repo;
    const char *json_path;
    if (argc < 6) {
        fprintf(stderr, "usage: qikvrt_handshake_core seed|node GUID SOURCE_REPO SEED_REPO JSON_PATH\n");
        return 64;
    }
    mode = argv[1]; guid = argv[2]; source_repo = argv[3]; seed_repo = argv[4]; json_path = argv[5];
    if (!contains_file(json_path, guid)) { fprintf(stderr, "GUID_CHECK BLOCK\n"); return 10; }
    if (!contains_file(json_path, source_repo)) { fprintf(stderr, "SOURCE_REPO_CHECK BLOCK\n"); return 11; }
    if (!contains_file(json_path, seed_repo)) { fprintf(stderr, "SEED_REPO_CHECK BLOCK\n"); return 12; }
    if (strcmp(mode, "seed") == 0) {
        if (!contains_file(json_path, "no_global_scanning")) { fprintf(stderr, "NO_GLOBAL_SCANNING_CHECK BLOCK\n"); return 13; }
        if (!contains_file(json_path, "no_self_propagation")) { fprintf(stderr, "NO_SELF_PROPAGATION_CHECK BLOCK\n"); return 14; }
        return write_seed_outputs(guid, source_repo, seed_repo);
    }
    if (strcmp(mode, "node") == 0) {
        if (!contains_file(json_path, "ACCEPTED")) { fprintf(stderr, "ACCEPTED_STATUS_CHECK BLOCK\n"); return 15; }
        return write_node_outputs(guid, source_repo, seed_repo);
    }
    fprintf(stderr, "UNKNOWN_MODE BLOCK\n"); return 65;
}
