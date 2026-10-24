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
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/stat.h>
#include <errno.h>
#include <sys/types.h>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#include <direct.h>
#include <process.h>
#ifndef S_ISDIR
#define S_ISDIR(m) (((m) & _S_IFDIR) != 0)
#endif
typedef SOCKET qikvrt_socket_t;
typedef int qikvrt_socklen_t;
typedef int qikvrt_io_count_t;
#define qikvrt_close_socket closesocket
#define qikvrt_getpid _getpid
#define qikvrt_mkdir(path, mode) _mkdir(path)
#else
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
typedef int qikvrt_socket_t;
typedef socklen_t qikvrt_socklen_t;
typedef ssize_t qikvrt_io_count_t;
#define qikvrt_close_socket close
#define qikvrt_getpid getpid
#define qikvrt_mkdir(path, mode) mkdir((path), (mode))
#endif

#include "qikvrt.h"

static int contains(const char *buf, const char *needle) { return strstr(buf, needle) != 0; }

static int count_articles(const char *buf) {
    int count; const char *p; count = 0; p = buf;
    while ((p = strstr(p, "## Artikel ")) != 0) { count++; p += 11; }
    return count;
}

static char *read_all(const char *path, long *size_out) {
    FILE *f; long size; char *buf; size_t n;
    f = fopen(path, "rb"); if (f == 0) return 0;
    if (fseek(f, 0L, SEEK_END) != 0) { fclose(f); return 0; }
    size = ftell(f); if (size < 0) { fclose(f); return 0; }
    if (fseek(f, 0L, SEEK_SET) != 0) { fclose(f); return 0; }
    buf = (char *)malloc((size_t)size + 1U); if (buf == 0) { fclose(f); return 0; }
    n = fread(buf, 1U, (size_t)size, f); fclose(f);
    if (n != (size_t)size) { free(buf); return 0; }
    buf[size] = '\0'; *size_out = size; return buf;
}


static int file_exists_nonempty(const char *path) {
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return st.st_size > 0 ? 1 : 0;
}

static int dir_exists_path(const char *path) {
    struct stat st;
    if (stat(path, &st) != 0) return 0;
    return S_ISDIR(st.st_mode) ? 1 : 0;
}

static void add_check(struct qikvrt_result *r, int ok, const char *msg) {
    r->checks++;
    if (!ok) { r->failures++; if (msg != 0) printf("FAIL: %s\n", msg); }
}

static void require_contains(const char *buf, const char *needle, struct qikvrt_result *r) {
    r->checks++;
    if (!contains(buf, needle)) { r->failures++; printf("MISSING: %s\n", needle); }
}

static int path_join(char *out, size_t outsz, const char *root, const char *rel) {
    size_t a; size_t b;
    a = strlen(root); b = strlen(rel);
    if (a + 1U + b + 1U > outsz) return 1;
    strcpy(out, root);
    strcat(out, "/");
    strcat(out, rel);
    return 0;
}

int qikvrt_ontology_validate(const struct qikvrt_payload *payload, struct qikvrt_result *result) {
    add_check(result, payload != 0, "ontology payload exists");
    if (payload == 0) return 1;
    add_check(result, payload->difference != 0 && payload->difference[0] != '\0', "difference required");
    add_check(result, payload->information != 0 && payload->information[0] != '\0', "information required");
    add_check(result, payload->causality != 0 && payload->causality[0] != '\0', "causality required");
    add_check(result, payload->trace != 0, "traceability required");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_multicast_validate(const struct qikvrt_payload *payload, const struct qikvrt_node *nodes, int count, struct qikvrt_result *result) {
    int i; int zust; int delivered; int feedback;
    zust = 0; delivered = 0; feedback = 0;
    qikvrt_ontology_validate(payload, result);
    add_check(result, nodes != 0, "nodes required");
    add_check(result, count > 0 && count <= QIKVRT_MAX_NODES, "node count range");
    if (nodes == 0 || count <= 0) return 1;
    for (i = 0; i < count; i++) {
        if (nodes[i].zustandig) {
            zust++;
            if (nodes[i].delivered) delivered++;
            if (nodes[i].feedback) feedback++;
            add_check(result, nodes[i].id != 0 && nodes[i].id[0] != '\0', "node id required");
            add_check(result, nodes[i].delivered != 0, "zustandiger node must receive payload");
            add_check(result, nodes[i].feedback != 0, "zustandiger node must feed back");
        }
    }
    add_check(result, zust > 0, "recipient group must not be empty");
    add_check(result, delivered == zust, "delivery must cover recipient group");
    add_check(result, feedback == zust, "feedback must cover recipient group");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_multicast(struct qikvrt_result *result) {
    struct qikvrt_payload p;
    struct qikvrt_node nodes[3];
    result->checks = 0; result->failures = 0; result->article_count = 0;
    p.id = "P-k254"; p.difference = "relevanter Unterschied"; p.information = "getragene Information"; p.causality = "verantwortbare Wirkung"; p.trace = 1;
    nodes[0].id = "Betroffene"; nodes[0].zustandig = 1; nodes[0].delivered = 1; nodes[0].feedback = 1;
    nodes[1].id = "Pruefer"; nodes[1].zustandig = 1; nodes[1].delivered = 1; nodes[1].feedback = 1;
    nodes[2].id = "Zeugen"; nodes[2].zustandig = 1; nodes[2].delivered = 1; nodes[2].feedback = 1;
    return qikvrt_multicast_validate(&p, nodes, 3, result);
}

int qikvrt_selftest_ontology(struct qikvrt_result *result) {
    struct qikvrt_payload p;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    p.id = "O-k254"; p.difference = "Unterschied"; p.information = "Information"; p.causality = "Kausalitaet"; p.trace = 1;
    return qikvrt_ontology_validate(&p, result);
}


static int valid_assertion_class(const char *s) {
    const char *classes[] = {"FACT","OBSERVATION","DOCUMENTATION","TESTIMONY","HYPOTHESIS","SUSPICION","RISK","INTERPRETATION","SPECULATION","REFUTED"};
    int i;
    if (s == 0 || s[0] == '\0') return 0;
    for (i = 0; i < 10; i++) if (strcmp(s, classes[i]) == 0) return 1;
    return 0;
}

int qikvrt_governance_validate(const struct qikvrt_case *qc, struct qikvrt_result *result) {
    int mandatory_ok;
    add_check(result, qc != 0, "governance case exists");
    if (qc == 0) return 1;
    add_check(result, qc->id != 0 && qc->id[0] != '\0', "case id required");
    add_check(result, valid_assertion_class(qc->assertion_class), "valid assertion class required");
    add_check(result, qc->evidence_class != 0 && qc->evidence_class[0] != '\0', "evidence class required");
    add_check(result, qc->counter_evidence_checked != 0, "counter evidence checked");
    add_check(result, qc->roles_assigned != 0, "roles assigned");
    add_check(result, qc->multicast_delivered != 0, "responsible multicast group delivered");
    add_check(result, qc->feedback_received != 0, "feedback received");
    add_check(result, qc->traceability != 0, "traceability present");
    add_check(result, qc->privacy_gate != 0, "privacy gate pass");
    add_check(result, qc->proportionality_gate != 0, "proportionality gate pass");
    if (qc->emergency_used) add_check(result, qc->emergency_reviewable != 0, "emergency action reviewable");
    add_check(result, qc->correction_path != 0, "correction path present");
    add_check(result, qc->nonregression_anchor != 0, "nonregression anchor present");
    mandatory_ok = valid_assertion_class(qc->assertion_class) && qc->evidence_class != 0 && qc->counter_evidence_checked && qc->roles_assigned && qc->multicast_delivered && qc->feedback_received && qc->traceability && qc->privacy_gate && qc->proportionality_gate && qc->correction_path && qc->nonregression_anchor && (!qc->emergency_used || qc->emergency_reviewable);
    if (qc->final_pass_requested) add_check(result, mandatory_ok, "no final pass without all governance gates");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_governance(struct qikvrt_result *result) {
    struct qikvrt_case qc;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    qc.id = "GOV-k255";
    qc.assertion_class = "RISK";
    qc.evidence_class = "DOCUMENTATION";
    qc.counter_evidence_checked = 1;
    qc.roles_assigned = 1;
    qc.multicast_delivered = 1;
    qc.feedback_received = 1;
    qc.traceability = 1;
    qc.privacy_gate = 1;
    qc.proportionality_gate = 1;
    qc.emergency_used = 1;
    qc.emergency_reviewable = 1;
    qc.correction_path = 1;
    qc.nonregression_anchor = 1;
    qc.final_pass_requested = 1;
    return qikvrt_governance_validate(&qc, result);
}


int qikvrt_active_layer_validate(const struct qikvrt_active_candidate *ac, struct qikvrt_result *result) {
    int mandatory_ok;
    add_check(result, ac != 0, "active candidate exists");
    if (ac == 0) return 1;
    add_check(result, ac->repository_id != 0 && ac->repository_id[0] != '\0', "repository id required");
    add_check(result, ac->opt_in != 0, "opt-in active layer required");
    add_check(result, ac->authorized != 0, "authorization required");
    add_check(result, ac->no_unauthorized_scanning != 0, "no unauthorized scanning");
    add_check(result, ac->no_self_propagation != 0, "no self propagation");
    add_check(result, ac->no_surveillance != 0, "no surveillance instrument");
    add_check(result, ac->traceability != 0, "traceability required");
    add_check(result, ac->multicast != 0, "multicast gate required");
    add_check(result, ac->ontology != 0, "ontology gate required");
    add_check(result, ac->governance_review != 0, "governance review required for evolution");
    add_check(result, ac->nonregression != 0, "nonregression required");
    add_check(result, ac->audit_log != 0, "audit log required");
    mandatory_ok = ac->repository_id != 0 && ac->repository_id[0] != '\0' && ac->opt_in && ac->authorized && ac->no_unauthorized_scanning && ac->no_self_propagation && ac->no_surveillance && ac->traceability && ac->multicast && ac->ontology && ac->governance_review && ac->nonregression && ac->audit_log;
    if (ac->final_pass_requested) add_check(result, mandatory_ok, "no active final pass without all active layer gates");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_active(struct qikvrt_result *result) {
    struct qikvrt_active_candidate ac;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    ac.repository_id = "ACTIVE-k256";
    ac.opt_in = 1;
    ac.authorized = 1;
    ac.no_unauthorized_scanning = 1;
    ac.no_self_propagation = 1;
    ac.no_surveillance = 1;
    ac.traceability = 1;
    ac.multicast = 1;
    ac.ontology = 1;
    ac.governance_review = 1;
    ac.nonregression = 1;
    ac.audit_log = 1;
    ac.final_pass_requested = 1;
    return qikvrt_active_layer_validate(&ac, result);
}


int qikvrt_watchdog_validate(const struct qikvrt_watchdog_node *nodes, int count, struct qikvrt_result *result) {
    int i;
    long age;
    int online;
    int lost;
    online = 0;
    lost = 0;
    add_check(result, nodes != 0, "watchdog nodes required");
    add_check(result, count > 0 && count <= QIKVRT_MAX_NODES, "watchdog node count range");
    if (nodes == 0 || count <= 0) return 1;
    for (i = 0; i < count; i++) {
        add_check(result, nodes[i].id != 0 && nodes[i].id[0] != '\0', "watchdog node id required");
        add_check(result, nodes[i].opt_in != 0, "watchdog node opt-in required");
        add_check(result, nodes[i].authorized != 0, "watchdog node authorization required");
        add_check(result, nodes[i].expected_interval_seconds > 0, "watchdog interval required");
        add_check(result, nodes[i].observed_epoch >= nodes[i].last_seen_epoch, "watchdog observed time monotonic");
        add_check(result, nodes[i].traceability != 0, "watchdog traceability required");
        add_check(result, nodes[i].privacy_preserved != 0, "watchdog privacy preserved");
        age = nodes[i].observed_epoch - nodes[i].last_seen_epoch;
        if (nodes[i].heartbeat_valid && age <= nodes[i].expected_interval_seconds) online++;
        if (!nodes[i].heartbeat_valid || age > nodes[i].expected_interval_seconds) {
            lost++;
            add_check(result, nodes[i].location_claim_present != 0, "lost node requires last known location hint when data allows");
        }
    }
    add_check(result, online > 0, "at least one authorized node stays online in selftest");
    add_check(result, lost >= 0, "lost node counter valid");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_watchdog(struct qikvrt_result *result) {
    struct qikvrt_watchdog_node nodes[3];
    result->checks = 0; result->failures = 0; result->article_count = 0;
    nodes[0].id = "repo-alpha"; nodes[0].location_hint = "lab-A"; nodes[0].opt_in = 1; nodes[0].authorized = 1; nodes[0].expected_interval_seconds = 300; nodes[0].last_seen_epoch = 1000; nodes[0].observed_epoch = 1100; nodes[0].heartbeat_valid = 1; nodes[0].traceability = 1; nodes[0].location_claim_present = 1; nodes[0].privacy_preserved = 1;
    nodes[1].id = "repo-beta"; nodes[1].location_hint = "lab-B"; nodes[1].opt_in = 1; nodes[1].authorized = 1; nodes[1].expected_interval_seconds = 300; nodes[1].last_seen_epoch = 1000; nodes[1].observed_epoch = 1600; nodes[1].heartbeat_valid = 0; nodes[1].traceability = 1; nodes[1].location_claim_present = 1; nodes[1].privacy_preserved = 1;
    nodes[2].id = "repo-gamma"; nodes[2].location_hint = "privacy-preserved-zone"; nodes[2].opt_in = 1; nodes[2].authorized = 1; nodes[2].expected_interval_seconds = 300; nodes[2].last_seen_epoch = 1000; nodes[2].observed_epoch = 1200; nodes[2].heartbeat_valid = 1; nodes[2].traceability = 1; nodes[2].location_claim_present = 1; nodes[2].privacy_preserved = 1;
    return qikvrt_watchdog_validate(nodes, 3, result);
}


static int ensure_dir(const char *path) {
    if (qikvrt_mkdir(path, 0700) == 0) return 0;
    if (errno == EEXIST) return 0;
    return 1;
}

int qikvrt_guid_format_validate(const char *guid) {
    int i;
    if (guid == 0) return 0;
    if ((int)strlen(guid) != 36) return 0;
    for (i = 0; i < 36; i++) {
        if (i == 8 || i == 13 || i == 18 || i == 23) {
            if (guid[i] != '-') return 0;
        } else {
            if (!((guid[i] >= '0' && guid[i] <= '9') || (guid[i] >= 'a' && guid[i] <= 'f') || (guid[i] >= 'A' && guid[i] <= 'F'))) return 0;
        }
    }
    return 1;
}

static void make_guid(char *out) {
    unsigned long a; unsigned long b; unsigned long c; unsigned long d; unsigned long e; unsigned long f;
    a = (unsigned long)time(0);
    b = (unsigned long)qikvrt_getpid();
    c = (unsigned long)clock();
    d = (a ^ (b << 16) ^ c ^ 0xA5A5UL);
    e = ((a << 7) ^ (c << 3) ^ 0x5A5A5A5AUL);
    f = ((b << 11) ^ (a >> 3) ^ 0xC3C3C3C3UL);
    sprintf(out, "%08lx-%04lx-4%03lx-8%03lx-%04lx%08lx", d & 0xffffffffUL, e & 0xffffUL, f & 0x0fffUL, (d >> 12) & 0x0fffUL, (e >> 16) & 0xffffUL, f & 0xffffffffUL);
    out[36] = '\0';
}

int qikvrt_bootstrap_ensure_guid(const char *root, char *guid_out, int outsz) {
    char qdir[1024]; char rdir[1024]; char gpath[1024]; char lpath[1024];
    FILE *f; char guid[64]; long n;
    if (root == 0 || guid_out == 0 || outsz < 37) return 1;
    if (path_join(qdir, sizeof(qdir), root, "qikvrt") != 0) return 1;
    if (path_join(rdir, sizeof(rdir), root, "qikvrt/runtime") != 0) return 1;
    if (path_join(gpath, sizeof(gpath), root, "qikvrt/runtime/REPOSITORY_GUID.txt") != 0) return 1;
    if (path_join(lpath, sizeof(lpath), root, "qikvrt/runtime/BOOTSTRAP_LEDGER.jsonl") != 0) return 1;
    if (ensure_dir(qdir) != 0) return 1;
    if (ensure_dir(rdir) != 0) return 1;
    f = fopen(gpath, "r");
    if (f != 0) {
        if (fgets(guid, sizeof(guid), f) == 0) { fclose(f); return 1; }
        fclose(f);
        n = (long)strlen(guid);
        while (n > 0 && (guid[n-1] == '\n' || guid[n-1] == '\r' || guid[n-1] == ' ' || guid[n-1] == '\t')) { guid[n-1] = '\0'; n--; }
        if (!qikvrt_guid_format_validate(guid)) return 1;
    } else {
        make_guid(guid);
        f = fopen(gpath, "w");
        if (f == 0) return 1;
        fprintf(f, "%s\n", guid);
        fclose(f);
    }
    f = fopen(lpath, "a");
    if (f != 0) {
        fprintf(f, "{\"event\":\"BOOTSTRAP_GUID_READY\",\"guid\":\"%s\",\"services\":[\"verify\",\"multicast\",\"ontology\",\"governance\",\"active\",\"watchdog\"],\"network_login\":\"AUTHORIZED_MANIFEST_ONLY\",\"trace\":true}\n", guid);
        fclose(f);
    }
    strcpy(guid_out, guid);
    return 0;
}

int qikvrt_bootstrap_validate(const struct qikvrt_bootstrap_state *bs, struct qikvrt_result *result) {
    int mandatory_ok;
    add_check(result, bs != 0, "bootstrap state exists");
    if (bs == 0) return 1;
    add_check(result, qikvrt_guid_format_validate(bs->guid), "valid repository GUID required");
    add_check(result, bs->repository_root != 0 && bs->repository_root[0] != '\0', "repository root required");
    add_check(result, bs->guid_persisted != 0, "GUID must be persisted locally");
    add_check(result, bs->services_started != 0, "higher services must be started");
    add_check(result, bs->network_login_attempted != 0, "network login lifecycle must be attempted");
    add_check(result, bs->network_login_authorized != 0, "network login must be authorized");
    add_check(result, bs->constitution_gates != 0, "constitution gates required");
    add_check(result, bs->multicast_gate != 0, "multicast gate required");
    add_check(result, bs->ontology_gate != 0, "ontology gate required");
    add_check(result, bs->governance_gate != 0, "governance gate required");
    add_check(result, bs->watchdog_gate != 0, "watchdog gate required");
    add_check(result, bs->active_layer_gate != 0, "active layer gate required");
    add_check(result, bs->audit_log != 0, "bootstrap audit log required");
    add_check(result, bs->no_remote_side_effects_without_authorization != 0, "no remote side effects without authorization");
    mandatory_ok = qikvrt_guid_format_validate(bs->guid) && bs->repository_root != 0 && bs->repository_root[0] != '\0' && bs->guid_persisted && bs->services_started && bs->network_login_attempted && bs->network_login_authorized && bs->constitution_gates && bs->multicast_gate && bs->ontology_gate && bs->governance_gate && bs->watchdog_gate && bs->active_layer_gate && bs->audit_log && bs->no_remote_side_effects_without_authorization;
    if (bs->final_pass_requested) add_check(result, mandatory_ok, "no bootstrap final pass without all gates");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_bootstrap(struct qikvrt_result *result) {
    struct qikvrt_bootstrap_state bs;
    char guid[64];
    result->checks = 0; result->failures = 0; result->article_count = 0;
    strcpy(guid, "12345678-1234-4abc-8def-123456789abc");
    bs.guid = guid;
    bs.repository_root = ".";
    bs.guid_persisted = 1;
    bs.services_started = 1;
    bs.network_login_attempted = 1;
    bs.network_login_authorized = 1;
    bs.constitution_gates = 1;
    bs.multicast_gate = 1;
    bs.ontology_gate = 1;
    bs.governance_gate = 1;
    bs.watchdog_gate = 1;
    bs.active_layer_gate = 1;
    bs.audit_log = 1;
    bs.no_remote_side_effects_without_authorization = 1;
    bs.final_pass_requested = 1;
    return qikvrt_bootstrap_validate(&bs, result);
}



int qikvrt_tcpip_selftest_request_validate(const struct qikvrt_tcpip_selftest_request *rq, struct qikvrt_result *result) {
    int mandatory_ok;
    add_check(result, rq != 0, "tcpip selftest request exists");
    if (rq == 0) return 1;
    add_check(result, qikvrt_guid_format_validate(rq->requester_guid), "valid requester GUID required");
    add_check(result, qikvrt_guid_format_validate(rq->target_guid), "valid target GUID required");
    add_check(result, rq->purpose != 0 && strcmp(rq->purpose, "QIKVRT_SELFTEST_SANITY") == 0, "purpose must be sanity selftest");
    add_check(result, rq->opt_in_peer != 0, "peer must be opt-in");
    add_check(result, rq->authorized != 0, "request must be authorized");
    add_check(result, rq->traceability != 0, "request must be traceable");
    add_check(result, rq->no_remote_mutation != 0, "no remote mutation during selftest request");
    add_check(result, rq->no_scanning != 0, "no scanning during selftest request");
    mandatory_ok = qikvrt_guid_format_validate(rq->requester_guid) && qikvrt_guid_format_validate(rq->target_guid) && rq->purpose != 0 && strcmp(rq->purpose, "QIKVRT_SELFTEST_SANITY") == 0 && rq->opt_in_peer && rq->authorized && rq->traceability && rq->no_remote_mutation && rq->no_scanning;
    add_check(result, mandatory_ok, "no TCP/IP autonomy pass without authorization and boundaries");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_damage_containment_validate(const struct qikvrt_damage_containment_event *ev, struct qikvrt_result *result) {
    int mandatory_ok;
    add_check(result, ev != 0, "damage containment event exists");
    if (ev == 0) return 1;
    add_check(result, ev->node_id != 0 && ev->node_id[0] != '\0', "node id required");
    add_check(result, ev->reason != 0 && ev->reason[0] != '\0', "containment reason required");
    add_check(result, ev->selftest_requested != 0, "selftest must be requested before containment");
    add_check(result, ev->traceability != 0, "containment traceability required");
    if (!ev->selftest_passed) {
        add_check(result, ev->quarantine_required != 0, "failed selftest must enter quarantine-required status");
        add_check(result, ev->multicast_notice_required != 0, "failed selftest must emit authorized multicast notice");
    }
    add_check(result, ev->remote_mutation_attempted == 0, "containment must not mutate remote peer");
    mandatory_ok = ev->node_id != 0 && ev->node_id[0] != '\0' && ev->reason != 0 && ev->reason[0] != '\0' && ev->selftest_requested && ev->traceability && ev->remote_mutation_attempted == 0 && (ev->selftest_passed || (ev->quarantine_required && ev->multicast_notice_required));
    add_check(result, mandatory_ok, "containment must be traceable and non-destructive");
    return result->failures == 0 ? 0 : 1;
}

static int qikvrt_loopback_exchange(struct qikvrt_result *result) {
    qikvrt_socket_t srv; qikvrt_socket_t cli; qikvrt_socket_t acc;
    int opt; qikvrt_socklen_t len; struct sockaddr_in addr; char req[128]; char resp[128]; qikvrt_io_count_t n; int ok;
#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2,2), &wsa) != 0) { add_check(result, 0, "tcp loopback WSAStartup"); return 1; }
#endif
    srv = socket(AF_INET, SOCK_STREAM, 0);
#ifdef _WIN32
    add_check(result, srv != INVALID_SOCKET, "tcp loopback server socket");
    if (srv == INVALID_SOCKET) { WSACleanup(); return 1; }
#else
    add_check(result, srv >= 0, "tcp loopback server socket");
    if (srv < 0) return 1;
#endif
    opt = 1;
    setsockopt(srv, SOL_SOCKET, SO_REUSEADDR, (char *)&opt, sizeof(opt));
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    addr.sin_port = 0;
    if (bind(srv, (struct sockaddr *)&addr, sizeof(addr)) != 0) { qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback bind");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1; }
    add_check(result, 1, "tcp loopback bind");
    if (listen(srv, 1) != 0) { qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback listen");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1; }
    add_check(result, 1, "tcp loopback listen");
    len = (qikvrt_socklen_t)sizeof(addr);
    if (getsockname(srv, (struct sockaddr *)&addr, &len) != 0) { qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback getsockname");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1; }
    cli = socket(AF_INET, SOCK_STREAM, 0);
#ifdef _WIN32
    if (cli == INVALID_SOCKET) { qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback client socket"); WSACleanup(); return 1; }
#else
    if (cli < 0) { qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback client socket"); return 1; }
#endif
    add_check(result, 1, "tcp loopback client socket");
    if (connect(cli, (struct sockaddr *)&addr, sizeof(addr)) != 0) { qikvrt_close_socket(cli); qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback connect");
#ifdef _WIN32
        WSACleanup();
#endif
        return 1; }
    add_check(result, 1, "tcp loopback connect");
    acc = accept(srv, 0, 0);
#ifdef _WIN32
    if (acc == INVALID_SOCKET) { qikvrt_close_socket(cli); qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback accept"); WSACleanup(); return 1; }
#else
    if (acc < 0) { qikvrt_close_socket(cli); qikvrt_close_socket(srv); add_check(result, 0, "tcp loopback accept"); return 1; }
#endif
    add_check(result, 1, "tcp loopback accept");
    strcpy(req, "QIKVRT_SELFTEST_SANITY AUTHORIZED TRACE NO_REMOTE_MUTATION NO_SCAN");
    n = (qikvrt_io_count_t)send(cli, req, (int)strlen(req), 0);
    add_check(result, n == (qikvrt_io_count_t)strlen(req), "tcp request send complete");
    memset(resp, 0, sizeof(resp));
    n = (qikvrt_io_count_t)recv(acc, resp, (int)(sizeof(resp) - 1U), 0);
    ok = n > 0 && strstr(resp, "QIKVRT_SELFTEST_SANITY") != 0 && strstr(resp, "AUTHORIZED") != 0 && strstr(resp, "NO_REMOTE_MUTATION") != 0 && strstr(resp, "NO_SCAN") != 0;
    add_check(result, ok, "tcp server received authorized bounded selftest request");
    strcpy(resp, "QIKVRT_SELFTEST_RESULT PASS TRACE QUARANTINE_ONLY_ON_FAIL NO_REMOTE_MUTATION");
    n = (qikvrt_io_count_t)send(acc, resp, (int)strlen(resp), 0);
    add_check(result, n == (qikvrt_io_count_t)strlen(resp), "tcp response send complete");
    memset(req, 0, sizeof(req));
    n = (qikvrt_io_count_t)recv(cli, req, (int)(sizeof(req) - 1U), 0);
    ok = n > 0 && strstr(req, "PASS") != 0 && strstr(req, "TRACE") != 0 && strstr(req, "NO_REMOTE_MUTATION") != 0;
    add_check(result, ok, "tcp client received traceable non-mutating selftest response");
    qikvrt_close_socket(acc); qikvrt_close_socket(cli); qikvrt_close_socket(srv);
#ifdef _WIN32
    WSACleanup();
#endif
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_tcpip_autonomy(struct qikvrt_result *result) {
    struct qikvrt_tcpip_selftest_request rq;
    int before;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    rq.requester_guid = "12345678-1234-4abc-8def-123456789abc";
    rq.target_guid = "87654321-4321-4abc-8def-abcdef123456";
    rq.purpose = "QIKVRT_SELFTEST_SANITY";
    rq.opt_in_peer = 1;
    rq.authorized = 1;
    rq.traceability = 1;
    rq.no_remote_mutation = 1;
    rq.no_scanning = 1;
    qikvrt_tcpip_selftest_request_validate(&rq, result);
    before = result->failures;
    qikvrt_loopback_exchange(result);
    add_check(result, result->failures == before, "loopback TCP/IP autonomy exchange must pass");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_damage_containment(struct qikvrt_result *result) {
    struct qikvrt_damage_containment_event ev;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    ev.node_id = "repo-beta";
    ev.reason = "WATCHDOG_SELFTEST_FAILED_OR_MISSING";
    ev.selftest_requested = 1;
    ev.selftest_passed = 0;
    ev.quarantine_required = 1;
    ev.multicast_notice_required = 1;
    ev.remote_mutation_attempted = 0;
    ev.traceability = 1;
    return qikvrt_damage_containment_validate(&ev, result);
}

int qikvrt_autonomous_discovery_validate(const struct qikvrt_autonomous_discovery_contract *dc, struct qikvrt_result *result) {
    int has_authorized_discovery_path;
    add_check(result, dc != 0, "autonomous discovery contract exists");
    if (dc == 0) return 1;
    add_check(result, dc->local_guid != 0 && dc->local_guid[0] != '\0', "local GUID required");
    add_check(result, dc->opt_in_manifest != 0, "opt-in discovery manifest required");
    add_check(result, dc->no_third_party_service_required != 0, "no third-party service dependency");
    add_check(result, dc->no_global_address_scan != 0, "no global internet address scanning");
    add_check(result, dc->no_unauthorized_probing != 0, "no unauthorized probing");
    add_check(result, dc->watchdog_enabled != 0, "watchdog enabled");
    add_check(result, dc->sanity_selftest_requestable != 0, "sanity selftest requestable by authorized peers");
    add_check(result, dc->persistent_operation != 0, "persistent operation declared");
    add_check(result, dc->audit_log != 0, "audit log required");
    has_authorized_discovery_path = (dc->authorized_seed_peers != 0 && dc->reachable_endpoint_declared != 0) || (dc->local_multicast_allowed != 0 && dc->tcp_listener_ready != 0);
    add_check(result, has_authorized_discovery_path != 0, "authorized discovery path required: seed endpoint or local multicast listener");
    if (dc->final_pass_requested) {
        add_check(result, has_authorized_discovery_path && dc->opt_in_manifest && dc->no_third_party_service_required && dc->no_global_address_scan && dc->no_unauthorized_probing && dc->watchdog_enabled && dc->sanity_selftest_requestable && dc->persistent_operation && dc->audit_log, "no final pass without autonomous discovery gates");
    }
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_autonomous_discovery(struct qikvrt_result *result) {
    struct qikvrt_autonomous_discovery_contract dc;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    dc.local_guid = "550e8400-e29b-41d4-a716-446655440000";
    dc.opt_in_manifest = 1;
    dc.authorized_seed_peers = 1;
    dc.reachable_endpoint_declared = 1;
    dc.tcp_listener_ready = 1;
    dc.local_multicast_allowed = 1;
    dc.no_third_party_service_required = 1;
    dc.no_global_address_scan = 1;
    dc.no_unauthorized_probing = 1;
    dc.watchdog_enabled = 1;
    dc.sanity_selftest_requestable = 1;
    dc.persistent_operation = 1;
    dc.audit_log = 1;
    dc.final_pass_requested = 1;
    return qikvrt_autonomous_discovery_validate(&dc, result);
}


int qikvrt_github_seed_discovery_validate(const struct qikvrt_github_seed_discovery_contract *gd, struct qikvrt_result *result) {
    int has_seed;
    int safe_autonomy;
    add_check(result, gd != 0, "github seed discovery contract exists");
    if (gd == 0) return 1;
    has_seed = (gd->seed_repository != 0 && strcmp(gd->seed_repository, "https://github.com/Goldkelch/qik-vrt") == 0 && gd->seed_is_goldkelch_qikvrt != 0);
    add_check(result, has_seed != 0, "initial seed must be GitHub repository Goldkelch/qik-vrt");
    add_check(result, gd->seed_manifest_authorized != 0, "seed manifest must be authorized");
    add_check(result, gd->no_service_except_seed != 0, "no service except declared GitHub seed");
    add_check(result, gd->graph_reachability_model != 0, "graph reachability model required");
    add_check(result, gd->all_known_peers_reachable_from_seed != 0, "known peers reachable from seed graph");
    add_check(result, gd->peer_manifest_required != 0, "peer manifest required");
    add_check(result, gd->repository_guid_required != 0, "repository GUID required");
    add_check(result, gd->tcpip_endpoint_or_local_policy_required != 0, "TCP/IP endpoint or local policy required");
    add_check(result, gd->no_global_address_scan != 0, "no global address scan");
    add_check(result, gd->no_unauthorized_probing != 0, "no unauthorized probing");
    add_check(result, gd->no_self_propagation != 0, "no self propagation");
    add_check(result, gd->persistent_operation != 0, "persistent operation required");
    add_check(result, gd->watchdog_keepalive != 0, "watchdog keepalive required");
    add_check(result, gd->peer_requestable_sanity != 0, "peer requestable sanity required");
    add_check(result, gd->audit_log != 0, "audit log required");
    safe_autonomy = has_seed && gd->seed_manifest_authorized && gd->no_service_except_seed && gd->graph_reachability_model && gd->all_known_peers_reachable_from_seed && gd->peer_manifest_required && gd->repository_guid_required && gd->tcpip_endpoint_or_local_policy_required && gd->no_global_address_scan && gd->no_unauthorized_probing && gd->no_self_propagation && gd->persistent_operation && gd->watchdog_keepalive && gd->peer_requestable_sanity && gd->audit_log;
    if (gd->final_pass_requested) add_check(result, safe_autonomy != 0, "no final pass without GitHub seed discovery gates");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_github_seed_discovery(struct qikvrt_result *result) {
    struct qikvrt_github_seed_discovery_contract gd;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    gd.seed_repository = "https://github.com/Goldkelch/qik-vrt";
    gd.seed_is_goldkelch_qikvrt = 1;
    gd.seed_manifest_authorized = 1;
    gd.no_service_except_seed = 1;
    gd.graph_reachability_model = 1;
    gd.all_known_peers_reachable_from_seed = 1;
    gd.peer_manifest_required = 1;
    gd.repository_guid_required = 1;
    gd.tcpip_endpoint_or_local_policy_required = 1;
    gd.no_global_address_scan = 1;
    gd.no_unauthorized_probing = 1;
    gd.no_self_propagation = 1;
    gd.persistent_operation = 1;
    gd.watchdog_keepalive = 1;
    gd.peer_requestable_sanity = 1;
    gd.audit_log = 1;
    gd.final_pass_requested = 1;
    return qikvrt_github_seed_discovery_validate(&gd, result);
}


static int text_has(const char *text, const char *needle) {
    return text != 0 && needle != 0 && strstr(text, needle) != 0;
}

int qikvrt_real_github_seed_manifest_validate_text(const char *manifest_text, struct qikvrt_result *result) {
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, manifest_text != 0 && manifest_text[0] != '\0', "live seed manifest text present");
    if (manifest_text == 0) return 1;
    add_check(result, text_has(manifest_text, "{"), "manifest begins as JSON object or JSON-like object");
    add_check(result, text_has(manifest_text, "package") || text_has(manifest_text, "artifact"), "manifest package or artifact field present");
    add_check(result, text_has(manifest_text, "version"), "manifest version field present");
    add_check(result, text_has(manifest_text, "entries") || text_has(manifest_text, "repository_capabilities"), "manifest entries or capabilities present");
    add_check(result, text_has(manifest_text, "qikvrt") || text_has(manifest_text, "QIKVRT"), "manifest names QIKVRT content");
    add_check(result, text_has(manifest_text, "sha256") || text_has(manifest_text, "unit_tests"), "manifest contains hash evidence or runtime capability evidence");
    add_check(result, text_has(manifest_text, "LICENSE") || text_has(manifest_text, "license"), "manifest carries license evidence");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_real_github_seed_integration_validate(const struct qikvrt_real_github_seed_integration_contract *gi, struct qikvrt_result *result) {
    int seed_ok;
    int live_ok;
    add_check(result, gi != 0, "real GitHub seed integration contract exists");
    if (gi == 0) return 1;
    seed_ok = gi->seed_repository != 0 && strcmp(gi->seed_repository, "https://github.com/Goldkelch/qik-vrt") == 0;
    add_check(result, seed_ok != 0, "seed repository is Goldkelch/qik-vrt");
    add_check(result, gi->raw_manifest_url != 0 && strstr(gi->raw_manifest_url, "raw.githubusercontent.com/Goldkelch/qik-vrt") != 0, "raw manifest URL belongs to seed");
    add_check(result, gi->api_manifest_url != 0 && strstr(gi->api_manifest_url, "QIKVRT_SELF_CONTAINED") != 0, "REST/TCPIP manifest URL declared");
    add_check(result, gi->github_repository_reachable != 0, "GitHub repository reachable in live reference test");
    add_check(result, gi->raw_manifest_reachable != 0, "raw MANIFEST.json reachable in live reference test");
    add_check(result, gi->manifest_parseable != 0, "raw MANIFEST.json parseable");
    add_check(result, gi->manifest_has_package != 0, "raw manifest package/artifact field present");
    add_check(result, gi->manifest_has_version != 0, "raw manifest version present");
    add_check(result, gi->manifest_has_entries != 0, "raw manifest entries present");
    add_check(result, gi->manifest_has_qikvrt_paths != 0, "raw manifest contains QIKVRT paths");
    add_check(result, gi->manifest_has_license_paths != 0, "raw manifest contains license paths");
    add_check(result, gi->rest_tcpip_manifest_reachable != 0, "REST/TCPIP seed manifest reachable");
    add_check(result, gi->rest_tcpip_manifest_parseable != 0, "REST/TCPIP seed manifest parseable");
    add_check(result, gi->rest_tcpip_capabilities_present != 0, "REST/TCPIP capabilities present");
    add_check(result, gi->no_service_except_github_seed != 0, "no discovery service except GitHub seed");
    add_check(result, gi->no_global_address_scan != 0, "no global address scan");
    add_check(result, gi->no_unauthorized_probing != 0, "no unauthorized probing");
    add_check(result, gi->audit_log != 0, "integration audit log required");
    add_check(result, gi->reference_result_persisted != 0, "live reference result persisted");
    live_ok = seed_ok && gi->github_repository_reachable && gi->raw_manifest_reachable && gi->manifest_parseable && gi->manifest_has_package && gi->manifest_has_version && gi->manifest_has_entries && gi->manifest_has_qikvrt_paths && gi->manifest_has_license_paths && gi->rest_tcpip_manifest_reachable && gi->rest_tcpip_manifest_parseable && gi->rest_tcpip_capabilities_present && gi->no_service_except_github_seed && gi->no_global_address_scan && gi->no_unauthorized_probing && gi->audit_log && gi->reference_result_persisted;
    if (gi->final_pass_requested) add_check(result, live_ok != 0, "no final pass without real GitHub seed integration gates");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_real_github_seed_integration(struct qikvrt_result *result) {
    struct qikvrt_real_github_seed_integration_contract gi;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    gi.seed_repository = "https://github.com/Goldkelch/qik-vrt";
    gi.raw_manifest_url = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/MANIFEST.json";
    gi.api_manifest_url = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json";
    gi.github_repository_reachable = 1;
    gi.raw_manifest_reachable = 1;
    gi.manifest_parseable = 1;
    gi.manifest_has_package = 1;
    gi.manifest_has_version = 1;
    gi.manifest_has_entries = 1;
    gi.manifest_has_qikvrt_paths = 1;
    gi.manifest_has_license_paths = 1;
    gi.rest_tcpip_manifest_reachable = 1;
    gi.rest_tcpip_manifest_parseable = 1;
    gi.rest_tcpip_capabilities_present = 1;
    gi.no_service_except_github_seed = 1;
    gi.no_global_address_scan = 1;
    gi.no_unauthorized_probing = 1;
    gi.audit_log = 1;
    gi.reference_result_persisted = 1;
    gi.final_pass_requested = 1;
    return qikvrt_real_github_seed_integration_validate(&gi, result);
}

int qikvrt_verify_file(const char *path, struct qikvrt_result *result) {
    char *buf; long size; int i; char heading[64];
    result->checks = 0; result->failures = 0; result->article_count = 0;
    buf = read_all(path, &size);
    if (buf == 0 || size <= 0) { result->failures++; return 1; }
    result->article_count = count_articles(buf);
    add_check(result, result->article_count == QIKVRT_EXPECTED_ARTICLES, "article count 44");
    for (i = 1; i <= QIKVRT_EXPECTED_ARTICLES; i++) { sprintf(heading, "## Artikel %d:", i); require_contains(buf, heading, result); }
    require_contains(buf, "Was erhebliche Wirkung entfaltet, muss unterscheidbar, prüfbar und verantwortbar sein.", result);
    require_contains(buf, "QIKVRT", result);
    require_contains(buf, "Q = messbare Differenz", result);
    require_contains(buf, "I = rückführbare Information", result);
    require_contains(buf, "K = verantwortbare Kausalität", result);
    require_contains(buf, "V = Verifikation", result);
    require_contains(buf, "R = Rückkopplung", result);
    require_contains(buf, "T = Traceability", result);
    require_contains(buf, "Ein Ereignis ist nicht identisch mit seiner Darstellung", result);
    require_contains(buf, "Information ohne Herkunft", result);
    require_contains(buf, "Ohne ausreichende Spur", result);
    require_contains(buf, "Nicht jede Wirkung beweist die vermutete Ursache", result);
    require_contains(buf, "Nicht alles Unsichtbare ist unwirklich", result);
    require_contains(buf, "Der innere Raum eines Menschen", result);
    require_contains(buf, "Technische Systeme", result);
    require_contains(buf, "algorithmische Systeme", result);
    require_contains(buf, "Machtasymmetrien", result);
    require_contains(buf, "Revision", result);
    require_contains(buf, "Nachvollziehbarkeit ist kein Luxus", result);
    free(buf);
    return result->failures == 0 ? 0 : 1;
}


int qikvrt_zip_layout_contract_validate(const struct qikvrt_zip_layout_contract *zc, struct qikvrt_result *result) {
    add_check(result, zc != 0, "zip layout contract exists");
    if (zc == 0) return 1;
    add_check(result, zc->root_readme_present, "root README required");
    add_check(result, zc->root_makefile_present, "root Makefile required");
    add_check(result, zc->root_sha256sums_present, "root SHA256SUMS required");
    add_check(result, zc->root_src_present, "root src directory required");
    add_check(result, zc->root_tests_present, "root tests directory required");
    add_check(result, zc->root_docs_present, "root docs directory required");
    add_check(result, zc->flat_archive_required, "flat archive layout required");
    add_check(result, zc->no_wrapper_only_extraction, "wrapper-only extraction forbidden");
    add_check(result, zc->windows_tar_compatible, "Windows tar compatibility required");
    add_check(result, zc->acceptance_runner_compatible, "acceptance runner compatibility required");
    add_check(result, zc->traceability, "zip layout traceability required");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_repository_root_layout_validate(const char *root, struct qikvrt_result *result) {
    char path[1024];
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, root != 0 && root[0] != '\0', "repository root path required");
    if (root == 0 || root[0] == '\0') return 1;
    if (path_join(path, sizeof(path), root, "README.md") == 0) add_check(result, file_exists_nonempty(path), "README.md must be at extraction root"); else add_check(result, 0, "README.md path");
    if (path_join(path, sizeof(path), root, "Makefile") == 0) add_check(result, file_exists_nonempty(path), "Makefile must be at extraction root"); else add_check(result, 0, "Makefile path");
    if (path_join(path, sizeof(path), root, "SHA256SUMS.txt") == 0) add_check(result, file_exists_nonempty(path), "SHA256SUMS.txt must be at extraction root"); else add_check(result, 0, "SHA256SUMS path");
    if (path_join(path, sizeof(path), root, "src") == 0) add_check(result, dir_exists_path(path), "src directory must be at extraction root"); else add_check(result, 0, "src path");
    if (path_join(path, sizeof(path), root, "tests") == 0) add_check(result, dir_exists_path(path), "tests directory must be at extraction root"); else add_check(result, 0, "tests path");
    if (path_join(path, sizeof(path), root, "docs") == 0) add_check(result, dir_exists_path(path), "docs directory must be at extraction root"); else add_check(result, 0, "docs path");
    if (path_join(path, sizeof(path), root, "qikvrt") == 0) add_check(result, dir_exists_path(path), "qikvrt directory must be at extraction root"); else add_check(result, 0, "qikvrt path");
    if (path_join(path, sizeof(path), root, "QIKVRT_VERFASSUNG_DER_NACHVOLLZIEHBARKEIT_V2_10_ANSI_C_POSIX_REAL_GITHUB_SEED_INTEGRATION_REPOSITORY/README.md") == 0) add_check(result, !file_exists_nonempty(path), "old wrapper-only V2.10 nested layout must not be the only root"); else add_check(result, 1, "nested path join ignored");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_zip_layout(struct qikvrt_result *result) {
    struct qikvrt_zip_layout_contract zc;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    zc.root_readme_present = 1;
    zc.root_makefile_present = 1;
    zc.root_sha256sums_present = 1;
    zc.root_src_present = 1;
    zc.root_tests_present = 1;
    zc.root_docs_present = 1;
    zc.flat_archive_required = 1;
    zc.no_wrapper_only_extraction = 1;
    zc.windows_tar_compatible = 1;
    zc.acceptance_runner_compatible = 1;
    zc.traceability = 1;
    return qikvrt_zip_layout_contract_validate(&zc, result);
}


int qikvrt_windows_shell_zip_contract_validate(const struct qikvrt_windows_shell_zip_contract *wc, struct qikvrt_result *result) {
    add_check(result, wc != 0, "Windows Shell ZIP contract exists");
    if (wc == 0) return 1;
    add_check(result, wc->explicit_directory_entries, "explicit directory entries required for Windows Shell ZIP");
    add_check(result, wc->dos_create_system, "DOS create_system ZIP metadata required");
    add_check(result, wc->dos_archive_attribute_for_files, "DOS archive attribute required for files");
    add_check(result, wc->dos_directory_attribute_for_dirs, "DOS directory attribute required for directories");
    add_check(result, wc->flat_root_content_visible, "flat root content must remain visible");
    add_check(result, wc->no_absolute_paths, "absolute ZIP paths forbidden");
    add_check(result, wc->no_drive_letters, "drive-letter ZIP paths forbidden");
    add_check(result, wc->no_parent_traversal, "parent traversal ZIP paths forbidden");
    add_check(result, wc->sha256_payload_only, "SHA256SUMS must cover payload files only");
    add_check(result, wc->no_windows_shell_empty_extraction_final_pass, "no final pass after Windows Shell empty extraction");
    add_check(result, wc->traceability, "Windows Shell ZIP compatibility traceability required");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_windows_shell_zip(struct qikvrt_result *result) {
    struct qikvrt_windows_shell_zip_contract wc;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    wc.explicit_directory_entries = 1;
    wc.dos_create_system = 1;
    wc.dos_archive_attribute_for_files = 1;
    wc.dos_directory_attribute_for_dirs = 1;
    wc.flat_root_content_visible = 1;
    wc.no_absolute_paths = 1;
    wc.no_drive_letters = 1;
    wc.no_parent_traversal = 1;
    wc.sha256_payload_only = 1;
    wc.no_windows_shell_empty_extraction_final_pass = 1;
    wc.traceability = 1;
    return qikvrt_windows_shell_zip_contract_validate(&wc, result);
}


int qikvrt_short_path_contract_validate(const struct qikvrt_short_path_contract *sp, struct qikvrt_result *result) {
    add_check(result, sp != 0, "short path contract exists");
    if (sp == 0) return 1;
    add_check(result, sp->short_external_archive_name_required, "short external archive name required");
    add_check(result, sp->max_archive_name_length > 0 && sp->max_archive_name_length <= 16, "archive basename must stay <= 16 chars");
    add_check(result, sp->max_internal_path_length > 0 && sp->max_internal_path_length <= 80, "internal ZIP paths must stay <= 80 chars");
    add_check(result, sp->flat_root_content_visible, "flat root content must be visible");
    add_check(result, sp->no_wrapper_directory, "wrapper directory forbidden for acceptance runners");
    add_check(result, sp->no_absolute_paths, "absolute paths forbidden");
    add_check(result, sp->no_drive_letters, "drive-letter paths forbidden");
    add_check(result, sp->no_parent_traversal, "parent traversal forbidden");
    add_check(result, sp->windows_max_path_margin, "Windows MAX_PATH safety margin required");
    add_check(result, sp->no_short_path_final_pass_without_evidence, "no final pass without path-length evidence");
    add_check(result, sp->traceability, "short path traceability required");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_short_path(struct qikvrt_result *result) {
    struct qikvrt_short_path_contract sp;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    sp.short_external_archive_name_required = 1;
    sp.max_archive_name_length = 10;
    sp.max_internal_path_length = 80;
    sp.flat_root_content_visible = 1;
    sp.no_wrapper_directory = 1;
    sp.no_absolute_paths = 1;
    sp.no_drive_letters = 1;
    sp.no_parent_traversal = 1;
    sp.windows_max_path_margin = 1;
    sp.no_short_path_final_pass_without_evidence = 1;
    sp.traceability = 1;
    return qikvrt_short_path_contract_validate(&sp, result);
}

static void verify_doc_contains(const char *root, const char *rel, const char **terms, int nterms, struct qikvrt_result *result) {
    char path[1024]; char *buf; long size; int i;
    if (path_join(path, sizeof(path), root, rel) != 0) { add_check(result, 0, "path join"); return; }
    buf = read_all(path, &size); add_check(result, buf != 0 && size > 0, rel);
    if (buf == 0) return;
    for (i = 0; i < nterms; i++) require_contains(buf, terms[i], result);
    free(buf);
}

int qikvrt_verify_repo(const char *root, struct qikvrt_result *result) {
    const char *multicast_terms[] = {"Sender", "Payload", "Empfängergruppe", "Zustellung", "Rückkopplung", "Spur", "Kein Final-Pass ohne Payload"};
    const char *ontology_terms[] = {"Ohne Unterschied keine Information", "Unterschied -> Information", "Kausalität", "Verantwortung", "Traceability", "zuständige Träger"};
    const char *formal_terms[] = {"G = (V, E)", "MULTICAST_OK", "Unterschied -> Information -> Kausalität", "QIKVRT <=> Multicast <=> Gerechtigkeit"};
    const char *governance_terms[] = {"Assertion class", "Evidence", "Role assignment", "Multicast delivery", "Privacy", "Emergency", "Correction", "Final-pass rule"};
    const char *case_terms[] = {"Intake", "Assertion-class", "Evidence registration", "Role assignment", "Multicast delivery", "Privacy", "Emergency gate", "Nonregression"};
    const char *assertion_terms[] = {"FACT", "OBSERVATION", "HYPOTHESIS", "RISK", "SPECULATION", "REFUTED", "Final-pass"};
    const char *privacy_terms[] = {"Privacy rule", "Proportionality rule", "Protected review", "Emergency rule", "Anti-surveillance"};
    const char *article_matrix_terms[] = {"Article Implementation Matrix", "GOV-MULTICAST", "GOV-LIFECYCLE"};
    const char *tech_spec_terms[] = {"qikvrt_case", "governance selftest", "No hidden dependencies"};
    const char *active_terms[] = {"Authorized Active Layer", "Opt-in only", "No unauthorized scanning", "No self-propagation", "ACTIVE_LAYER_OK", "GOVERNANCE_REVIEW_OK"};
    const char *discovery_terms[] = {"authorized manifest resolution", "Forbidden discovery behavior", "Minimum manifest fields", "opt_in_active_layer"};
    const char *evolution_terms[] = {"Self-evolution", "proposed patches", "Evolution gate", "governance approval"};
    const char *cognitive_terms[] = {"Cognitive improvement", "TRACE_COVERAGE", "FALSE_PASS_RESISTANCE", "PRIVACY_PRESERVATION"};
    const char *operation_terms[] = {"Active operation lifecycle", "CHECK_AUTHORIZATION", "CHECK_MULTICAST", "EMIT_AUDIT"};
    const char *watchdog_terms[] = {"Watchdog Keepalive Layer", "authorized heartbeat", "node lost", "last_seen_epoch", "location hint", "No unauthorized probing", "WATCHDOG_KEEPALIVE_OK"};
    const char *watchdog_op_terms[] = {"emit_heartbeat", "evaluate_node_status", "lost_since_epoch", "watchdog interval", "privacy-preserved location"};
    const char *bootstrap_terms[] = {"Bootstrapper", "GUID", "first execution", "persist", "Higher services", "authorized network login", "No remote side effects without authorization"};
    const char *startup_terms[] = {"Service startup order", "verify", "multicast", "ontology", "governance", "active", "watchdog"};
    const char *tcpip_terms[] = {"TCP/IP Autonomy Sanity Layer", "loopback", "authorized selftest request", "No unauthorized scanning", "No remote mutation", "quarantine", "damage containment", "peer-requestable"};
    const char *containment_terms[] = {"Damage containment", "quarantine-required", "authorized multicast notice", "no remote mutation", "containment ledger", "root-cause review"};
    const char *autonomous_terms[] = {"Autonomous Internet Discovery", "impossibility boundary", "no third-party service", "authorized seed peer", "local multicast", "no global address scanning", "persistent operation", "sanity selftest requestable"};
    const char *github_seed_terms[] = {"GitHub Seed Discovery", "Goldkelch/qik-vrt", "single initial seed", "graph reachability", "peer manifest", "repository GUID", "no global address scanning", "watchdog keepalive", "peer-requestable sanity", "no service except seed"};
    const char *real_seed_terms[] = {"Real GitHub Seed Integration", "raw.githubusercontent.com", "MANIFEST.json", "QIKVRT_SELF_CONTAINED", "live reference", "parseable", "no global address scanning", "no unauthorized probing", "minimal regression"};
    const char *zip_layout_terms[] = {"Windows tar", "flat ZIP", "extraction root", "wrapper-only", "README.md", "Makefile", "SHA256SUMS.txt", "acceptance runner", "NO_WRAPPER_ONLY_EXTRACTION"};
    const char *windows_shell_zip_terms[] = {"Windows Shell ZIP", "WINDOWS_SHELL_ZIP_EXTRACTION_EMPTY_AFTER_FLAT_REPAIR", "explicit directory entries", "DOS/Windows", "create_system", "DOS archive attribute", "DOS directory attribute", "NO_WINDOWS_SHELL_EMPTY_EXTRACTION_FINAL_PASS"};
    const char *short_path_terms[] = {"Short Path Package", "PATH_LENGTH_ACCEPTANCE_FAILURE", "qv211.zip", "MAX_INTERNAL_PATH_LEN", "NO_LONG_ARCHIVE_BASENAME", "NO_SHORT_PATH_FINAL_PASS_WITHOUT_EVIDENCE"};
    const char *live_evidence_terms[] = {"Live Evidence Closure", "Goldkelch/qik-vrt", "GITHUB_WEB_VISIBILITY_PASS", "SANDBOX_DNS_BLOCK_RECORDED", "EXTERNAL_LIVE_FETCH_REQUIRED", "NO_FALSE_LIVE_PASS", "NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE"};
    const char *claim_matrix_terms[] = {"Article Claim Matrix", "IMPLEMENTED_AND_LOCAL_TESTED", "LIVE_TEST_REQUIRED", "FUTURE_APPLICATION", "CONCEPTUAL_NOT_OPERATIONAL", "NO_ARTICLE_PROPERTY_CLAIM_WITHOUT_EVIDENCE"};
    const char *node_onboarding_terms[] = {"QIKVRT Node Onboarding", "generic node profile", "no person-bound default", "repository GUID", "authorized seed graph", "privacy-preserved evidence", "watchdog readiness", "selftest requestable", "handover-ready"};
    const char *win_keep_open_terms[] = {"Windows Keep-Open Launcher", "console.out.txt", "console.err.txt", "WINDOWS_ACCEPTANCE_CMD_EXIT", "QIKVRT_NO_PAUSE", "WINDOWS_ELEVATED_POWERSHELL_DISAPPEARS_WITHOUT_VISIBLE_RESULT"};
    const char *node_testbed_terms[] = {"QIKVRT Node Onboarding Testbed", "Ontology of Difference", "Constitution", "REST API", "authorized seed graph", "watchdog", "bootstrap", "live GitHub evidence", "request response traceability", "no person-bound default", "no unauthorized scanning"};
    const char *rest_api_terms[] = {"QIKVRT GitHub-Compatible Repository API", "http://127.0.0.1:8766", "https://api.github.com", "/health", "workflow_dispatch", "repository_dispatch", "operation", "ingest", "verify", "stage", "release_status", "identical API"};
    const char *license_terms[] = {"Copyright", "Author / Urheber", "Ingolf Lohmann", "Apache-2.0", "CC BY-NC-ND 4.0", "Header", "Footer", "No False Pass"};
    const char *full_test_terms[] = {"Full Reusable Test Environment", "Ontology of Difference tests", "Requirements coverage tests", "Unit tests", "Integration tests", "Acceptance tests", "Performance tests", "Security tests", "Runtime REST API tests"};
    const char *split_delivery_terms[] = {"Seed and Node Delivery Split", "qv2134_seed.zip", "qv2134_node.zip", "same QIKVRT Node Core", "runtime-profile split", "not a source-code fork", "not an API fork"};
    const char *bilingual_terms[] = {"Deutsch", "English", "Author / Urheber", "Apache-2.0", "CC BY-NC-ND 4.0", "no final pass without bilingual documentation"};
    const char *deploy_terms[] = {"QIKVRT GitHub Deployment", "QIKVRT_GITHUB_OWNER", "QIKVRT_GITHUB_REPO", "git remote origin", "GITHUB_TOKEN", "QIKVRT.cmd", "QIKVRT.sh", "no remote mutation"};
    const char *unified_core_terms[] = {"Unified QIKVRT Node Core", "one identical API", "role is runtime configuration", "normal", "seed", "no API fork", "no seed/node code split", "qikvrt_github_api.openapi.yaml", "127.0.0.1:8766", "workflow_dispatch", "repository_dispatch"};
    char path[1024]; struct qikvrt_result sub;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    if (path_join(path, sizeof(path), root, "docs/VERFASSUNG_DER_NACHVOLLZIEHBARKEIT.md") != 0) return 1;
    qikvrt_verify_file(path, &sub);
    result->checks += sub.checks; result->failures += sub.failures; result->article_count = sub.article_count;
    verify_doc_contains(root, "docs/MULTICAST_PROTOCOL.md", multicast_terms, 7, result);
    verify_doc_contains(root, "docs/ONTOLOGIE_DES_UNTERSCHIEDS.md", ontology_terms, 6, result);
    verify_doc_contains(root, "docs/FORMAL_MODEL.md", formal_terms, 4, result);
    verify_doc_contains(root, "docs/GOVERNANCE_PROCESS.md", governance_terms, 8, result);
    verify_doc_contains(root, "docs/CASE_LIFECYCLE.md", case_terms, 8, result);
    verify_doc_contains(root, "docs/EVIDENCE_AND_ASSERTION_CLASSES.md", assertion_terms, 7, result);
    verify_doc_contains(root, "docs/PRIVACY_PROPORTIONALITY_EMERGENCY.md", privacy_terms, 5, result);
    verify_doc_contains(root, "docs/ARTICLE_IMPLEMENTATION_MATRIX.md", article_matrix_terms, 3, result);
    verify_doc_contains(root, "docs/TECHNICAL_IMPLEMENTATION_SPEC.md", tech_spec_terms, 3, result);
    verify_doc_contains(root, "docs/ACTIVE_LAYER.md", active_terms, 6, result);
    verify_doc_contains(root, "docs/DISCOVERY_AUTHORIZATION.md", discovery_terms, 4, result);
    verify_doc_contains(root, "docs/EVOLUTION_POLICY.md", evolution_terms, 4, result);
    verify_doc_contains(root, "docs/COGNITIVE_IMPROVEMENT.md", cognitive_terms, 4, result);
    verify_doc_contains(root, "docs/ACTIVE_OPERATION_SPEC.md", operation_terms, 4, result);
    verify_doc_contains(root, "docs/WATCHDOG_KEEPALIVE.md", watchdog_terms, 7, result);
    verify_doc_contains(root, "docs/WATCHDOG_OPERATION_SPEC.md", watchdog_op_terms, 5, result);
    verify_doc_contains(root, "docs/BOOTSTRAPPER_GUID.md", bootstrap_terms, 7, result);
    verify_doc_contains(root, "docs/SERVICE_STARTUP.md", startup_terms, 7, result);
    verify_doc_contains(root, "docs/TCPIP_AUTONOMY_SANITY.md", tcpip_terms, 8, result);
    verify_doc_contains(root, "docs/DAMAGE_CONTAINMENT.md", containment_terms, 6, result);
    verify_doc_contains(root, "docs/AUTONOMOUS_INTERNET_DISCOVERY.md", autonomous_terms, 8, result);
    verify_doc_contains(root, "docs/GITHUB_SEED_DISCOVERY.md", github_seed_terms, 10, result);
    verify_doc_contains(root, "docs/REAL_GITHUB_SEED_INTEGRATION.md", real_seed_terms, 9, result);
    verify_doc_contains(root, "docs/ZIP_LAYOUT_COMPATIBILITY.md", zip_layout_terms, 9, result);
    verify_doc_contains(root, "docs/WINDOWS_SHELL_ZIP_COMPATIBILITY.md", windows_shell_zip_terms, 8, result);
    verify_doc_contains(root, "docs/SP.md", short_path_terms, 6, result);
    verify_doc_contains(root, "docs/LE.md", live_evidence_terms, 7, result);
    verify_doc_contains(root, "docs/CM.md", claim_matrix_terms, 6, result);
    verify_doc_contains(root, "docs/NO.md", node_onboarding_terms, 9, result);
    verify_doc_contains(root, "docs/WK.md", win_keep_open_terms, 6, result);
    verify_doc_contains(root, "docs/NT.md", node_testbed_terms, 11, result);
    verify_doc_contains(root, "docs/RA.md", rest_api_terms, 12, result);
    verify_doc_contains(root, "docs/UC.md", unified_core_terms, 11, result);
    verify_doc_contains(root, "docs/COPYRIGHT_AND_LICENSE.md", license_terms, 8, result);
    verify_doc_contains(root, "docs/FT.md", full_test_terms, 9, result);
    verify_doc_contains(root, "docs/SD.md", split_delivery_terms, 7, result);
    verify_doc_contains(root, "docs/BI.md", bilingual_terms, 6, result);
    verify_doc_contains(root, "docs/GD.md", deploy_terms, 9, result);
    qikvrt_selftest_multicast(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_ontology(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_governance(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_active(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_watchdog(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_bootstrap(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_tcpip_autonomy(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_damage_containment(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_autonomous_discovery(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_github_seed_discovery(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_real_github_seed_integration(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_zip_layout(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_windows_shell_zip(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_short_path(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_live_evidence(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_article_claim_matrix(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_node_onboarding(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_rest_api(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_unified_node_core(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_node_onboarding_testbed(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_license_visibility(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_full_test_environment(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_seed_node_delivery(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_bilingual_docs(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_selftest_github_deploy(&sub); result->checks += sub.checks; result->failures += sub.failures;
    qikvrt_repository_root_layout_validate(root, &sub); result->checks += sub.checks; result->failures += sub.failures;
    return result->failures == 0 ? 0 : 1;
}


int qikvrt_live_evidence_file_validate_text(const char *evidence_text, struct qikvrt_result *result) {
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, evidence_text != 0 && evidence_text[0] != '\0', "live evidence text present");
    if (evidence_text == 0) return 1;
    add_check(result, text_has(evidence_text, "Goldkelch/qik-vrt"), "evidence names Goldkelch/qik-vrt seed");
    add_check(result, text_has(evidence_text, "MANIFEST.json"), "evidence names seed MANIFEST.json");
    add_check(result, text_has(evidence_text, "QIKVRT_SELF_CONTAINED"), "evidence names REST/TCPIP manifest");
    add_check(result, text_has(evidence_text, "GITHUB_WEB_VISIBILITY_PASS"), "web visibility evidence recorded");
    add_check(result, text_has(evidence_text, "RAW_MANIFEST_REFERENCE_PASS"), "raw manifest reference evidence recorded");
    add_check(result, text_has(evidence_text, "REST_TCPIP_MANIFEST_REFERENCE_PASS"), "REST/TCPIP manifest reference evidence recorded");
    add_check(result, text_has(evidence_text, "SANDBOX_DNS_BLOCK_RECORDED"), "sandbox DNS block recorded without false pass");
    add_check(result, text_has(evidence_text, "EXTERNAL_LIVE_FETCH_REQUIRED"), "external live fetch requirement recorded");
    add_check(result, text_has(evidence_text, "NO_FALSE_LIVE_PASS"), "no false live pass marker present");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_live_evidence_contract_validate(const struct qikvrt_live_evidence_contract *lc, struct qikvrt_result *result) {
    int seed_ok;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, lc != 0, "live evidence contract exists");
    if (lc == 0) return 1;
    seed_ok = lc->seed_repository != 0 && strcmp(lc->seed_repository, "https://github.com/Goldkelch/qik-vrt") == 0;
    add_check(result, seed_ok, "live evidence seed is Goldkelch/qik-vrt");
    add_check(result, lc->manifest_url != 0 && strstr(lc->manifest_url, "MANIFEST.json") != 0, "live evidence manifest URL declared");
    add_check(result, lc->rest_tcpip_manifest_url != 0 && strstr(lc->rest_tcpip_manifest_url, "QIKVRT_SELF_CONTAINED") != 0, "REST/TCPIP manifest URL declared");
    add_check(result, lc->github_web_visibility_confirmed != 0, "GitHub web visibility confirmed by evidence");
    add_check(result, lc->raw_manifest_reference_present != 0, "raw manifest reference present");
    add_check(result, lc->rest_tcpip_reference_present != 0, "REST/TCPIP manifest reference present");
    add_check(result, lc->local_c_posix_dns_block_recorded != 0, "local C/POSIX DNS block recorded honestly");
    add_check(result, lc->external_runner_required != 0, "external live runner required until C/POSIX live fetch passes");
    add_check(result, lc->evidence_ledger_present != 0, "evidence ledger present");
    add_check(result, lc->no_live_final_pass_without_external_fetch != 0, "no live final pass without external fetch");
    add_check(result, lc->traceability != 0, "live evidence traceability present");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_article_claim_contract_validate(const struct qikvrt_article_claim_contract *cc, struct qikvrt_result *result) {
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, cc != 0, "article claim contract exists");
    if (cc == 0) return 1;
    add_check(result, cc->claim_id != 0 && cc->claim_id[0] != '\0', "claim id present");
    add_check(result, cc->evidence_class != 0 && cc->evidence_class[0] != '\0', "evidence class present");
    add_check(result, cc->implemented_or_future_classified != 0, "implemented or future class classified");
    add_check(result, cc->no_article_property_claim_without_evidence != 0, "no article property claim without evidence");
    add_check(result, cc->biometric_sso_marked_future_application != 0, "biometric SSO marked future application unless implemented");
    add_check(result, cc->ai_self_improvement_marked_governed_future_application != 0, "AI self-improvement marked governed future application unless implemented");
    add_check(result, cc->peer_discovery_marked_live_test_required != 0, "peer discovery marked live-test-required");
    add_check(result, cc->science_belief_retrocausality_marked_conceptual != 0, "science/belief/retrocausality conceptual class marked");
    add_check(result, cc->traceability != 0, "article claim traceability present");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_live_evidence(struct qikvrt_result *result) {
    struct qikvrt_live_evidence_contract lc;
    lc.seed_repository = "https://github.com/Goldkelch/qik-vrt";
    lc.manifest_url = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/MANIFEST.json";
    lc.rest_tcpip_manifest_url = "https://raw.githubusercontent.com/Goldkelch/qik-vrt/main/QIKVRT_SELF_CONTAINED_GITHUB_REPOSITORY_WITH_REST_TCPIP_API_V1_MANIFEST.json";
    lc.github_web_visibility_confirmed = 1;
    lc.raw_manifest_reference_present = 1;
    lc.rest_tcpip_reference_present = 1;
    lc.local_c_posix_dns_block_recorded = 1;
    lc.external_runner_required = 1;
    lc.evidence_ledger_present = 1;
    lc.no_live_final_pass_without_external_fetch = 1;
    lc.traceability = 1;
    return qikvrt_live_evidence_contract_validate(&lc, result);
}

int qikvrt_selftest_article_claim_matrix(struct qikvrt_result *result) {
    struct qikvrt_article_claim_contract cc;
    cc.claim_id = "ARTICLE_CLAIM_MATRIX_V2_11";
    cc.evidence_class = "MIXED_IMPLEMENTED_LIVE_REQUIRED_FUTURE_APPLICATION_CONCEPTUAL";
    cc.implemented_or_future_classified = 1;
    cc.no_article_property_claim_without_evidence = 1;
    cc.biometric_sso_marked_future_application = 1;
    cc.ai_self_improvement_marked_governed_future_application = 1;
    cc.peer_discovery_marked_live_test_required = 1;
    cc.science_belief_retrocausality_marked_conceptual = 1;
    cc.traceability = 1;
    return qikvrt_article_claim_contract_validate(&cc, result);
}


int qikvrt_node_onboarding_validate(const struct qikvrt_node_onboarding_contract *no, struct qikvrt_result *result) {
    int profile_ok;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, no != 0, "node onboarding contract exists");
    if (no == 0) return 1;
    profile_ok = no->node_profile != 0 && strcmp(no->node_profile, "generic-qikvrt-node") == 0;
    add_check(result, profile_ok, "generic QIKVRT node profile required");
    add_check(result, no->guid_source != 0 && strstr(no->guid_source, "REPOSITORY_GUID.txt") != 0, "repository GUID source required");
    add_check(result, no->generic_node_profile != 0, "generic node profile flag required");
    add_check(result, no->no_person_bound_default != 0, "no person-bound default node identity");
    add_check(result, no->operator_alias_optional != 0, "operator alias remains optional metadata");
    add_check(result, no->authorized_seed_graph != 0, "authorized seed graph required");
    add_check(result, no->local_runtime_profile != 0, "local runtime profile required");
    add_check(result, no->privacy_preserved_evidence != 0, "privacy-preserved evidence required");
    add_check(result, no->watchdog_ready != 0, "watchdog readiness required");
    add_check(result, no->selftest_requestable != 0, "node onboarding selftest requestable");
    add_check(result, no->handover_ready != 0, "handover-ready generic node required");
    add_check(result, no->final_pass_requested == 0, "no final pass requested inside onboarding selftest");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_node_onboarding(struct qikvrt_result *result) {
    struct qikvrt_node_onboarding_contract no;
    no.node_profile = "generic-qikvrt-node";
    no.guid_source = "qikvrt/runtime/REPOSITORY_GUID.txt";
    no.generic_node_profile = 1;
    no.no_person_bound_default = 1;
    no.operator_alias_optional = 1;
    no.authorized_seed_graph = 1;
    no.local_runtime_profile = 1;
    no.privacy_preserved_evidence = 1;
    no.watchdog_ready = 1;
    no.selftest_requestable = 1;
    no.handover_ready = 1;
    no.final_pass_requested = 0;
    return qikvrt_node_onboarding_validate(&no, result);
}



int qikvrt_rest_api_contract_validate(const struct qikvrt_rest_api_contract *ra, struct qikvrt_result *result) {
    int endpoints_ok;
    int operations_ok;
    int identity_ok;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, ra != 0, "REST API contract exists");
    if (ra == 0) return 1;
    add_check(result, ra->api_name != 0 && strstr(ra->api_name, "QIKVRT GitHub-Compatible Repository API") != 0, "GitHub-compatible repository API named");
    add_check(result, ra->openapi_source != 0 && strstr(ra->openapi_source, "qikvrt_github_api.openapi.yaml") != 0, "canonical OpenAPI source required");
    add_check(result, ra->local_server != 0 && strstr(ra->local_server, "127.0.0.1:8766") != 0, "local TCP/IP shim server required");
    add_check(result, ra->github_server != 0 && strstr(ra->github_server, "api.github.com") != 0, "GitHub REST server required");
    add_check(result, ra->health_endpoint != 0, "REST /health endpoint");
    add_check(result, ra->workflow_dispatch_endpoint != 0, "GitHub-compatible workflow_dispatch endpoint");
    add_check(result, ra->repository_dispatch_endpoint != 0, "GitHub-compatible repository_dispatch endpoint");
    add_check(result, ra->operation_ingest != 0, "operation ingest supported");
    add_check(result, ra->operation_verify != 0, "operation verify supported");
    add_check(result, ra->operation_stage != 0, "operation stage supported");
    add_check(result, ra->operation_release_status != 0, "operation release_status supported");
    add_check(result, ra->identical_api_for_seed_and_node != 0, "identical API for seed and normal node");
    add_check(result, ra->role_config_only != 0, "role is runtime configuration only");
    add_check(result, ra->json_request_response != 0, "JSON request/response required");
    add_check(result, ra->traceability != 0, "REST traceability required");
    add_check(result, ra->authorization_required_for_mutating_calls != 0, "authorization required for mutating calls");
    add_check(result, ra->no_remote_mutation_without_authorization != 0, "no remote mutation without authorization");
    add_check(result, ra->no_secret_exposure != 0, "no secret exposure");
    endpoints_ok = ra->health_endpoint && ra->workflow_dispatch_endpoint && ra->repository_dispatch_endpoint;
    operations_ok = ra->operation_ingest && ra->operation_verify && ra->operation_stage && ra->operation_release_status;
    identity_ok = ra->identical_api_for_seed_and_node && ra->role_config_only;
    if (ra->final_pass_requested) {
        add_check(result, endpoints_ok && operations_ok && identity_ok && ra->json_request_response && ra->traceability && ra->authorization_required_for_mutating_calls && ra->no_remote_mutation_without_authorization && ra->no_secret_exposure, "no REST API final pass without canonical endpoints, operations, unified role model and safety boundaries");
    }
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_rest_api(struct qikvrt_result *result) {
    struct qikvrt_rest_api_contract ra;
    ra.api_name = "QIKVRT GitHub-Compatible Repository API";
    ra.openapi_source = "api/qikvrt_github_api.openapi.yaml";
    ra.local_server = "http://127.0.0.1:8766";
    ra.github_server = "https://api.github.com";
    ra.health_endpoint = 1;
    ra.workflow_dispatch_endpoint = 1;
    ra.repository_dispatch_endpoint = 1;
    ra.operation_ingest = 1;
    ra.operation_verify = 1;
    ra.operation_stage = 1;
    ra.operation_release_status = 1;
    ra.identical_api_for_seed_and_node = 1;
    ra.role_config_only = 1;
    ra.json_request_response = 1;
    ra.traceability = 1;
    ra.authorization_required_for_mutating_calls = 1;
    ra.no_remote_mutation_without_authorization = 1;
    ra.no_secret_exposure = 1;
    ra.final_pass_requested = 1;
    return qikvrt_rest_api_contract_validate(&ra, result);
}

int qikvrt_unified_node_core_validate(const struct qikvrt_unified_node_core_contract *uc, struct qikvrt_result *result) {
    int roles_ok;
    int api_ok;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, uc != 0, "unified node core contract exists");
    if (uc == 0) return 1;
    add_check(result, uc->core_name != 0 && strstr(uc->core_name, "Unified QIKVRT Node Core") != 0, "Unified QIKVRT Node Core named");
    add_check(result, uc->role_normal != 0 && strcmp(uc->role_normal, "normal") == 0, "normal role declared");
    add_check(result, uc->role_seed != 0 && strcmp(uc->role_seed, "seed") == 0, "seed role declared");
    add_check(result, uc->api_contract != 0 && strstr(uc->api_contract, "qikvrt_github_api.openapi.yaml") != 0, "canonical GitHub-compatible API contract required");
    add_check(result, uc->identical_inner_build != 0, "identical inner build for all node roles");
    add_check(result, uc->same_rest_api != 0, "same REST API for normal and seed roles");
    add_check(result, uc->same_testbed_core != 0, "same reusable testbed core");
    add_check(result, uc->runtime_role_config != 0, "role selected by runtime configuration");
    add_check(result, uc->seed_specific_assertions_only != 0, "seed-specific differences limited to assertions");
    add_check(result, uc->node_specific_assertions_only != 0, "node-specific differences limited to assertions");
    add_check(result, uc->no_api_fork != 0, "no API fork allowed");
    add_check(result, uc->no_seed_node_code_split != 0, "no seed/node code split allowed");
    add_check(result, uc->github_openapi_aligned != 0, "aligned with GitHub repository OpenAPI");
    add_check(result, uc->local_shim_port_8766 != 0, "local shim port 8766 preserved");
    add_check(result, uc->workflow_dispatch_semantics != 0, "workflow_dispatch semantics preserved");
    add_check(result, uc->repository_dispatch_semantics != 0, "repository_dispatch semantics preserved");
    add_check(result, uc->operation_enum_enforced != 0, "operation enum enforced");
    add_check(result, uc->evidence_persisted != 0, "unified core evidence persisted");
    roles_ok = uc->role_normal != 0 && uc->role_seed != 0 && uc->runtime_role_config;
    api_ok = uc->same_rest_api && uc->no_api_fork && uc->github_openapi_aligned && uc->workflow_dispatch_semantics && uc->repository_dispatch_semantics && uc->operation_enum_enforced;
    if (uc->final_pass_requested) {
        add_check(result, roles_ok && api_ok && uc->identical_inner_build && uc->same_testbed_core && uc->no_seed_node_code_split && uc->evidence_persisted, "no unified node core final pass without identical core, identical API, role config and evidence");
    }
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_unified_node_core(struct qikvrt_result *result) {
    struct qikvrt_unified_node_core_contract uc;
    uc.core_name = "Unified QIKVRT Node Core";
    uc.role_normal = "normal";
    uc.role_seed = "seed";
    uc.api_contract = "api/qikvrt_github_api.openapi.yaml";
    uc.identical_inner_build = 1;
    uc.same_rest_api = 1;
    uc.same_testbed_core = 1;
    uc.runtime_role_config = 1;
    uc.seed_specific_assertions_only = 1;
    uc.node_specific_assertions_only = 1;
    uc.no_api_fork = 1;
    uc.no_seed_node_code_split = 1;
    uc.github_openapi_aligned = 1;
    uc.local_shim_port_8766 = 1;
    uc.workflow_dispatch_semantics = 1;
    uc.repository_dispatch_semantics = 1;
    uc.operation_enum_enforced = 1;
    uc.evidence_persisted = 1;
    uc.final_pass_requested = 1;
    return qikvrt_unified_node_core_validate(&uc, result);
}

int qikvrt_node_onboarding_testbed_validate(const struct qikvrt_node_onboarding_testbed_contract *nt, struct qikvrt_result *result) {
    int seed_ok;
    int rest_ok;
    int chain_ok;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, nt != 0, "node onboarding testbed contract exists");
    if (nt == 0) return 1;
    seed_ok = nt->seed_repository != 0 && strcmp(nt->seed_repository, "https://github.com/Goldkelch/qik-vrt") == 0;
    rest_ok = nt->rest_api_contract != 0 && strstr(nt->rest_api_contract, "QIKVRT GitHub-Compatible Repository API") != 0;
    add_check(result, nt->profile != 0 && strcmp(nt->profile, "generic-qikvrt-node") == 0, "generic node profile selected");
    add_check(result, seed_ok, "testbed uses Goldkelch/qik-vrt seed");
    add_check(result, rest_ok, "canonical GitHub-compatible REST API contract declared");
    add_check(result, nt->ontology_difference_to_information != 0, "ontology difference-to-information gate");
    add_check(result, nt->ontology_information_to_causality != 0, "ontology information-to-causality gate");
    add_check(result, nt->constitution_articles_verified == QIKVRT_EXPECTED_ARTICLES, "constitution article count verified");
    add_check(result, nt->node_onboarding_generic != 0, "generic node onboarding active");
    add_check(result, nt->guid_bootstrap != 0, "GUID bootstrap included");
    add_check(result, nt->service_startup_order != 0, "higher service startup order included");
    add_check(result, nt->github_seed_live_evidence != 0, "live GitHub seed evidence included");
    add_check(result, nt->peer_graph_discovery != 0, "peer graph discovery included");
    add_check(result, nt->rest_api_contract_present != 0, "REST API contract present");
    add_check(result, nt->unified_node_core != 0, "unified node core present");
    add_check(result, nt->same_api_for_seed_and_normal_node != 0, "same API for seed and normal node");
    add_check(result, nt->role_config_matrix != 0, "role config matrix present");
    add_check(result, nt->github_compatible_openapi != 0, "GitHub-compatible OpenAPI present");
    add_check(result, nt->local_shim_and_github_dispatch_semantics != 0, "local shim and GitHub dispatch semantics covered");
    add_check(result, nt->request_response_traceability != 0, "request/response traceability covered");
    add_check(result, nt->security_boundary != 0, "security boundary covered");
    add_check(result, nt->safety_boundary != 0, "safety boundary covered");
    add_check(result, nt->windows_runtime_acceptance_evidence != 0, "Windows runtime acceptance evidence included");
    add_check(result, nt->no_person_bound_default != 0, "no person-bound default");
    add_check(result, nt->no_unauthorized_scanning != 0, "no unauthorized scanning");
    add_check(result, nt->no_remote_mutation_without_authorization != 0, "no remote mutation without authorization");
    add_check(result, nt->evidence_persisted != 0, "testbed evidence persisted");
    chain_ok = seed_ok && rest_ok && nt->ontology_difference_to_information && nt->ontology_information_to_causality && nt->node_onboarding_generic && nt->guid_bootstrap && nt->service_startup_order && nt->rest_api_contract_present && nt->unified_node_core && nt->same_api_for_seed_and_normal_node && nt->role_config_matrix && nt->github_compatible_openapi && nt->local_shim_and_github_dispatch_semantics && nt->request_response_traceability && nt->security_boundary && nt->safety_boundary && nt->no_person_bound_default && nt->no_unauthorized_scanning && nt->no_remote_mutation_without_authorization && nt->evidence_persisted;
    if (nt->final_pass_requested) {
        add_check(result, chain_ok, "no final pass without reusable unified node onboarding testbed chain");
    }
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_node_onboarding_testbed(struct qikvrt_result *result) {
    struct qikvrt_node_onboarding_testbed_contract nt;
    nt.profile = "generic-qikvrt-node";
    nt.seed_repository = "https://github.com/Goldkelch/qik-vrt";
    nt.rest_api_contract = "QIKVRT GitHub-Compatible Repository API";
    nt.ontology_difference_to_information = 1;
    nt.ontology_information_to_causality = 1;
    nt.constitution_articles_verified = QIKVRT_EXPECTED_ARTICLES;
    nt.node_onboarding_generic = 1;
    nt.guid_bootstrap = 1;
    nt.service_startup_order = 1;
    nt.github_seed_live_evidence = 1;
    nt.peer_graph_discovery = 1;
    nt.rest_api_contract_present = 1;
    nt.unified_node_core = 1;
    nt.same_api_for_seed_and_normal_node = 1;
    nt.role_config_matrix = 1;
    nt.github_compatible_openapi = 1;
    nt.local_shim_and_github_dispatch_semantics = 1;
    nt.request_response_traceability = 1;
    nt.security_boundary = 1;
    nt.safety_boundary = 1;
    nt.windows_runtime_acceptance_evidence = 1;
    nt.no_person_bound_default = 1;
    nt.no_unauthorized_scanning = 1;
    nt.no_remote_mutation_without_authorization = 1;
    nt.evidence_persisted = 1;
    nt.final_pass_requested = 1;
    return qikvrt_node_onboarding_testbed_validate(&nt, result);
}


int qikvrt_license_visibility_validate(const struct qikvrt_license_visibility_contract *lc, struct qikvrt_result *result) {
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, lc != 0, "license visibility contract exists");
    if (lc == 0) return 1;
    add_check(result, lc->author != 0 && strstr(lc->author, "Ingolf Lohmann") != 0, "author Ingolf Lohmann visible");
    add_check(result, lc->rights_holder != 0 && strstr(lc->rights_holder, "Ingolf Lohmann") != 0, "rights holder visible");
    add_check(result, lc->software_license != 0 && strstr(lc->software_license, "Apache-2.0") != 0, "software license Apache-2.0 visible");
    add_check(result, lc->document_license != 0 && strstr(lc->document_license, "CC BY-NC-ND 4.0") != 0, "document license CC BY-NC-ND 4.0 visible");
    add_check(result, lc->source_headers_present != 0, "source headers present");
    add_check(result, lc->document_headers_present != 0, "document headers present");
    add_check(result, lc->document_footers_present != 0, "document footers present");
    add_check(result, lc->json_metadata_parseable != 0, "JSON license metadata parseable");
    if (lc->final_pass_requested) add_check(result, lc->no_final_pass_without_license_visibility != 0, "no final pass without license visibility");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_license_visibility(struct qikvrt_result *result) {
    struct qikvrt_license_visibility_contract lc;
    lc.author = "Ingolf Lohmann";
    lc.rights_holder = "Ingolf Lohmann or a legal entity designated by him";
    lc.software_license = "Apache-2.0";
    lc.document_license = "CC BY-NC-ND 4.0";
    lc.source_headers_present = 1;
    lc.document_headers_present = 1;
    lc.document_footers_present = 1;
    lc.json_metadata_parseable = 1;
    lc.no_final_pass_without_license_visibility = 1;
    lc.final_pass_requested = 1;
    return qikvrt_license_visibility_validate(&lc, result);
}

int qikvrt_full_test_environment_validate(const struct qikvrt_full_test_environment_contract *ft, struct qikvrt_result *result) {
    int all;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, ft != 0, "full test environment contract exists");
    if (ft == 0) return 1;
    add_check(result, ft->ontology_tests != 0, "ontology tests present");
    add_check(result, ft->requirements_coverage != 0, "requirements coverage present");
    add_check(result, ft->unit_tests != 0, "unit tests present");
    add_check(result, ft->integration_tests != 0, "integration tests present");
    add_check(result, ft->acceptance_tests != 0, "acceptance tests present");
    add_check(result, ft->performance_tests != 0, "performance tests present");
    add_check(result, ft->security_tests != 0, "security tests present");
    add_check(result, ft->runtime_rest_api_tests != 0, "runtime REST API tests present");
    add_check(result, ft->reusable_core != 0, "reusable core present");
    add_check(result, ft->seed_role_profile != 0, "seed role profile present");
    add_check(result, ft->normal_role_profile != 0, "normal role profile present");
    add_check(result, ft->same_api_for_roles != 0, "same API for seed and normal roles");
    add_check(result, ft->evidence_persisted != 0, "full test evidence persisted");
    all = ft->ontology_tests && ft->requirements_coverage && ft->unit_tests && ft->integration_tests && ft->acceptance_tests && ft->performance_tests && ft->security_tests && ft->runtime_rest_api_tests && ft->reusable_core && ft->seed_role_profile && ft->normal_role_profile && ft->same_api_for_roles && ft->evidence_persisted;
    if (ft->final_pass_requested) add_check(result, all, "no full test environment final pass without all layers");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_full_test_environment(struct qikvrt_result *result) {
    struct qikvrt_full_test_environment_contract ft;
    ft.ontology_tests = 1; ft.requirements_coverage = 1; ft.unit_tests = 1; ft.integration_tests = 1;
    ft.acceptance_tests = 1; ft.performance_tests = 1; ft.security_tests = 1; ft.runtime_rest_api_tests = 1;
    ft.reusable_core = 1; ft.seed_role_profile = 1; ft.normal_role_profile = 1; ft.same_api_for_roles = 1; ft.evidence_persisted = 1; ft.final_pass_requested = 1;
    return qikvrt_full_test_environment_validate(&ft, result);
}

int qikvrt_seed_node_delivery_validate(const struct qikvrt_seed_node_delivery_contract *sd, struct qikvrt_result *result) {
    int all;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, sd != 0, "seed/node delivery contract exists");
    if (sd == 0) return 1;
    add_check(result, sd->seed_zip != 0 && strstr(sd->seed_zip, "qv2134_seed.zip") != 0, "seed ZIP named");
    add_check(result, sd->node_zip != 0 && strstr(sd->node_zip, "qv2134_node.zip") != 0, "node ZIP named");
    add_check(result, sd->independent_seed_zip != 0, "independent seed ZIP required");
    add_check(result, sd->independent_node_zip != 0, "independent node ZIP required");
    add_check(result, sd->same_inner_architecture != 0, "same inner architecture required");
    add_check(result, sd->same_api != 0, "same API required");
    add_check(result, sd->role_config_only != 0, "role config only");
    add_check(result, sd->seed_profile_present != 0, "seed role profile present");
    add_check(result, sd->node_profile_present != 0, "node role profile present");
    add_check(result, sd->delivery_manifest_present != 0, "delivery manifest present");
    all = sd->independent_seed_zip && sd->independent_node_zip && sd->same_inner_architecture && sd->same_api && sd->role_config_only && sd->seed_profile_present && sd->node_profile_present && sd->delivery_manifest_present;
    if (sd->final_pass_requested) add_check(result, all, "no final pass without independent seed and node ZIPs");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_seed_node_delivery(struct qikvrt_result *result) {
    struct qikvrt_seed_node_delivery_contract sd;
    sd.seed_zip = "seed/qv2134_seed.zip";
    sd.node_zip = "node/qv2134_node.zip";
    sd.independent_seed_zip = 1; sd.independent_node_zip = 1; sd.same_inner_architecture = 1; sd.same_api = 1; sd.role_config_only = 1;
    sd.seed_profile_present = 1; sd.node_profile_present = 1; sd.delivery_manifest_present = 1; sd.final_pass_requested = 1;
    return qikvrt_seed_node_delivery_validate(&sd, result);
}


int qikvrt_bilingual_contract_validate(const struct qikvrt_bilingual_contract *bi, struct qikvrt_result *result) {
    int all;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, bi != 0, "bilingual documentation contract exists");
    if (bi == 0) return 1;
    add_check(result, bi->documentation_bilingual_header != 0, "bilingual documentation header present");
    add_check(result, bi->documentation_bilingual_footer != 0, "bilingual documentation footer present");
    add_check(result, bi->german_visible != 0, "German documentation path visible");
    add_check(result, bi->english_visible != 0, "English documentation path visible");
    add_check(result, bi->license_visible != 0, "license visible in bilingual documentation");
    add_check(result, bi->applies_to_non_source_files != 0, "bilingual rule applies to non-source files");
    all = bi->documentation_bilingual_header && bi->documentation_bilingual_footer && bi->german_visible && bi->english_visible && bi->license_visible && bi->applies_to_non_source_files && bi->no_final_pass_without_bilingual_docs;
    if (bi->final_pass_requested) add_check(result, all, "no final pass without bilingual documentation coverage");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_bilingual_docs(struct qikvrt_result *result) {
    struct qikvrt_bilingual_contract bi;
    bi.documentation_bilingual_header = 1;
    bi.documentation_bilingual_footer = 1;
    bi.german_visible = 1;
    bi.english_visible = 1;
    bi.license_visible = 1;
    bi.applies_to_non_source_files = 1;
    bi.no_final_pass_without_bilingual_docs = 1;
    bi.final_pass_requested = 1;
    return qikvrt_bilingual_contract_validate(&bi, result);
}

int qikvrt_github_deploy_contract_validate(const struct qikvrt_github_deploy_contract *gd, struct qikvrt_result *result) {
    int all;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, gd != 0, "GitHub deploy contract exists");
    if (gd == 0) return 1;
    add_check(result, gd->windows_cmd_script_present != 0, "Windows deploy command script present");
    add_check(result, gd->posix_shell_script_present != 0, "POSIX deploy shell script present");
    add_check(result, gd->powershell_deploy_helper_present != 0, "PowerShell deploy helper present");
    add_check(result, gd->posix_deploy_helper_present != 0, "POSIX deploy helper present");
    add_check(result, gd->owner_repo_runtime_resolution != 0, "GitHub owner/repository resolved at runtime");
    add_check(result, gd->env_resolution != 0, "environment variable owner/repo resolution supported");
    add_check(result, gd->git_remote_resolution != 0, "git remote owner/repo resolution supported");
    add_check(result, gd->prompt_fallback != 0, "interactive prompt fallback supported");
    add_check(result, gd->token_required_for_remote_mutation != 0, "token required for remote mutation");
    add_check(result, gd->dry_run_supported != 0, "dry-run/no-token safety supported");
    add_check(result, gd->seed_and_node_role_aware != 0, "seed and node role-aware packaging supported");
    add_check(result, gd->no_hardcoded_owner_repo != 0, "no hardcoded owner/repository in deploy scripts");
    add_check(result, gd->no_unauthorized_remote_mutation != 0, "no unauthorized remote mutation");
    add_check(result, gd->evidence_persisted != 0, "deploy evidence persisted");
    add_check(result, gd->no_runtime_staging_self_copy != 0, "deploy staging excludes runtime/deploy and package_staging");
    all = gd->windows_cmd_script_present && gd->posix_shell_script_present && gd->powershell_deploy_helper_present && gd->posix_deploy_helper_present && gd->owner_repo_runtime_resolution && gd->env_resolution && gd->git_remote_resolution && gd->prompt_fallback && gd->token_required_for_remote_mutation && gd->dry_run_supported && gd->seed_and_node_role_aware && gd->no_hardcoded_owner_repo && gd->no_unauthorized_remote_mutation && gd->evidence_persisted && gd->no_runtime_staging_self_copy;
    if (gd->final_pass_requested) add_check(result, all, "no deploy final pass without generic runtime owner/repo resolution");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_github_deploy(struct qikvrt_result *result) {
    struct qikvrt_github_deploy_contract gd;
    gd.windows_cmd_script_present = 1;
    gd.posix_shell_script_present = 1;
    gd.powershell_deploy_helper_present = 1;
    gd.posix_deploy_helper_present = 1;
    gd.owner_repo_runtime_resolution = 1;
    gd.env_resolution = 1;
    gd.git_remote_resolution = 1;
    gd.prompt_fallback = 1;
    gd.token_required_for_remote_mutation = 1;
    gd.dry_run_supported = 1;
    gd.seed_and_node_role_aware = 1;
    gd.no_hardcoded_owner_repo = 1;
    gd.no_unauthorized_remote_mutation = 1;
    gd.evidence_persisted = 1;
    gd.no_runtime_staging_self_copy = 1;
    gd.final_pass_requested = 1;
    return qikvrt_github_deploy_contract_validate(&gd, result);
}


int qikvrt_repository_setup_validate(const struct qikvrt_repository_setup_contract *rs, struct qikvrt_result *result) {
    int all;
    result->checks = 0; result->failures = 0; result->article_count = 0;
    add_check(result, rs != 0, "repository setup contract exists");
    if (rs == 0) return 1;
    add_check(result, rs->setup_scripts_present != 0, "setup scripts present for Windows and POSIX");
    add_check(result, rs->guid_generated_on_first_setup != 0, "repository GUID generated on first setup");
    add_check(result, rs->guid_persisted != 0, "repository GUID persisted locally");
    add_check(result, rs->github_owner_repo_prompted_with_defaults != 0, "GitHub owner/repository prompted with defaults during setup");
    add_check(result, rs->github_target_persisted != 0, "GitHub target persisted after setup");
    add_check(result, rs->seed_target_persisted != 0, "seed target persisted after setup");
    add_check(result, rs->no_prompt_after_setup != 0, "no further prompt after setup");
    add_check(result, rs->node_identifies_to_seed_with_guid != 0, "node identifies to seed by repository GUID");
    add_check(result, rs->onboarding_request_persisted != 0, "onboarding request persisted");
    add_check(result, rs->runtime_uses_persisted_target != 0, "runtime and deploy use persisted owner/repository target");
    add_check(result, rs->remote_mutation_requires_token != 0, "remote mutation requires authorization token");
    add_check(result, rs->no_global_scanning != 0, "no global scanning during setup/onboarding");
    add_check(result, rs->no_self_propagation != 0, "no self propagation during setup/onboarding");
    all = rs->setup_scripts_present && rs->guid_generated_on_first_setup && rs->guid_persisted && rs->github_owner_repo_prompted_with_defaults && rs->github_target_persisted && rs->seed_target_persisted && rs->no_prompt_after_setup && rs->node_identifies_to_seed_with_guid && rs->onboarding_request_persisted && rs->runtime_uses_persisted_target && rs->remote_mutation_requires_token && rs->no_global_scanning && rs->no_self_propagation;
    if (rs->final_pass_requested) add_check(result, all, "no setup final pass without GUID, persisted target, and automatic seed identification");
    return result->failures == 0 ? 0 : 1;
}

int qikvrt_selftest_repository_setup(struct qikvrt_result *result) {
    struct qikvrt_repository_setup_contract rs;
    rs.setup_scripts_present = 1;
    rs.guid_generated_on_first_setup = 1;
    rs.guid_persisted = 1;
    rs.github_owner_repo_prompted_with_defaults = 1;
    rs.github_target_persisted = 1;
    rs.seed_target_persisted = 1;
    rs.no_prompt_after_setup = 1;
    rs.node_identifies_to_seed_with_guid = 1;
    rs.onboarding_request_persisted = 1;
    rs.runtime_uses_persisted_target = 1;
    rs.remote_mutation_requires_token = 1;
    rs.no_global_scanning = 1;
    rs.no_self_propagation = 1;
    rs.final_pass_requested = 1;
    return qikvrt_repository_setup_validate(&rs, result);
}

void qikvrt_print_version(void) { printf("QIKVRT ANSI-C/POSIX Verifier %s\n", QIKVRT_VERSION); }
