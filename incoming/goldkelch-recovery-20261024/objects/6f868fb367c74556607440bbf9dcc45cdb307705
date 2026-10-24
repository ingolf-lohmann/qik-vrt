/*
 * QIKVRT Artifact Header
 * Version: 2.13.4
 * Author / Urheber: Ingolf Lohmann
 * Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
 * License: Software source code licensed under Apache-2.0 unless otherwise stated.
 * Non-software texts/docs in this repository: CC BY-NC-ND 4.0 unless otherwise stated.
 * Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; NO_TRACEABILITY_NO_FINAL_PASS.
 */

#ifndef QIKVRT_H
#define QIKVRT_H

#define QIKVRT_VERSION "2.13.4"
#define QIKVRT_EXPECTED_ARTICLES 44
#define QIKVRT_MAX_NODES 16

struct qikvrt_result {
    int checks;
    int failures;
    int article_count;
};

struct qikvrt_payload {
    const char *id;
    const char *difference;
    const char *information;
    const char *causality;
    int trace;
};

struct qikvrt_node {
    const char *id;
    int zustandig;
    int delivered;
    int feedback;
};


struct qikvrt_active_candidate {
    const char *repository_id;
    int opt_in;
    int authorized;
    int no_unauthorized_scanning;
    int no_self_propagation;
    int no_surveillance;
    int traceability;
    int multicast;
    int ontology;
    int governance_review;
    int nonregression;
    int audit_log;
    int final_pass_requested;
};


struct qikvrt_watchdog_node {
    const char *id;
    const char *location_hint;
    int opt_in;
    int authorized;
    long expected_interval_seconds;
    long last_seen_epoch;
    long observed_epoch;
    int heartbeat_valid;
    int traceability;
    int location_claim_present;
    int privacy_preserved;
};

struct qikvrt_watchdog_event {
    const char *node_id;
    const char *status;
    long observed_epoch;
    long last_seen_epoch;
    long lost_since_epoch;
    const char *location_hint;
    int trace;
};



struct qikvrt_bootstrap_state {
    const char *guid;
    const char *repository_root;
    int guid_persisted;
    int services_started;
    int network_login_attempted;
    int network_login_authorized;
    int constitution_gates;
    int multicast_gate;
    int ontology_gate;
    int governance_gate;
    int watchdog_gate;
    int active_layer_gate;
    int audit_log;
    int no_remote_side_effects_without_authorization;
    int final_pass_requested;
};

struct qikvrt_case {
    const char *id;
    const char *assertion_class;
    const char *evidence_class;
    int counter_evidence_checked;
    int roles_assigned;
    int multicast_delivered;
    int feedback_received;
    int traceability;
    int privacy_gate;
    int proportionality_gate;
    int emergency_used;
    int emergency_reviewable;
    int correction_path;
    int nonregression_anchor;
    int final_pass_requested;
};

int qikvrt_verify_file(const char *path, struct qikvrt_result *result);
int qikvrt_verify_repo(const char *root, struct qikvrt_result *result);
int qikvrt_multicast_validate(const struct qikvrt_payload *payload, const struct qikvrt_node *nodes, int count, struct qikvrt_result *result);
int qikvrt_ontology_validate(const struct qikvrt_payload *payload, struct qikvrt_result *result);
int qikvrt_governance_validate(const struct qikvrt_case *qc, struct qikvrt_result *result);
int qikvrt_selftest_multicast(struct qikvrt_result *result);
int qikvrt_selftest_ontology(struct qikvrt_result *result);
int qikvrt_selftest_governance(struct qikvrt_result *result);
int qikvrt_active_layer_validate(const struct qikvrt_active_candidate *ac, struct qikvrt_result *result);
int qikvrt_selftest_active(struct qikvrt_result *result);

int qikvrt_guid_format_validate(const char *guid);
int qikvrt_bootstrap_ensure_guid(const char *root, char *guid_out, int outsz);
int qikvrt_bootstrap_validate(const struct qikvrt_bootstrap_state *bs, struct qikvrt_result *result);
int qikvrt_selftest_bootstrap(struct qikvrt_result *result);
int qikvrt_watchdog_validate(const struct qikvrt_watchdog_node *nodes, int count, struct qikvrt_result *result);
int qikvrt_selftest_watchdog(struct qikvrt_result *result);

struct qikvrt_tcpip_selftest_request {
    const char *requester_guid;
    const char *target_guid;
    const char *purpose;
    int opt_in_peer;
    int authorized;
    int traceability;
    int no_remote_mutation;
    int no_scanning;
};

struct qikvrt_damage_containment_event {
    const char *node_id;
    const char *reason;
    int selftest_requested;
    int selftest_passed;
    int quarantine_required;
    int multicast_notice_required;
    int remote_mutation_attempted;
    int traceability;
};

int qikvrt_tcpip_selftest_request_validate(const struct qikvrt_tcpip_selftest_request *rq, struct qikvrt_result *result);
int qikvrt_damage_containment_validate(const struct qikvrt_damage_containment_event *ev, struct qikvrt_result *result);
int qikvrt_selftest_tcpip_autonomy(struct qikvrt_result *result);
int qikvrt_selftest_damage_containment(struct qikvrt_result *result);

struct qikvrt_autonomous_discovery_contract {
    const char *local_guid;
    int opt_in_manifest;
    int authorized_seed_peers;
    int reachable_endpoint_declared;
    int tcp_listener_ready;
    int local_multicast_allowed;
    int no_third_party_service_required;
    int no_global_address_scan;
    int no_unauthorized_probing;
    int watchdog_enabled;
    int sanity_selftest_requestable;
    int persistent_operation;
    int audit_log;
    int final_pass_requested;
};

int qikvrt_autonomous_discovery_validate(const struct qikvrt_autonomous_discovery_contract *dc, struct qikvrt_result *result);
int qikvrt_selftest_autonomous_discovery(struct qikvrt_result *result);

struct qikvrt_github_seed_discovery_contract {
    const char *seed_repository;
    int seed_is_goldkelch_qikvrt;
    int seed_manifest_authorized;
    int no_service_except_seed;
    int graph_reachability_model;
    int all_known_peers_reachable_from_seed;
    int peer_manifest_required;
    int repository_guid_required;
    int tcpip_endpoint_or_local_policy_required;
    int no_global_address_scan;
    int no_unauthorized_probing;
    int no_self_propagation;
    int persistent_operation;
    int watchdog_keepalive;
    int peer_requestable_sanity;
    int audit_log;
    int final_pass_requested;
};

int qikvrt_github_seed_discovery_validate(const struct qikvrt_github_seed_discovery_contract *gd, struct qikvrt_result *result);
int qikvrt_selftest_github_seed_discovery(struct qikvrt_result *result);

struct qikvrt_real_github_seed_integration_contract {
    const char *seed_repository;
    const char *raw_manifest_url;
    const char *api_manifest_url;
    int github_repository_reachable;
    int raw_manifest_reachable;
    int manifest_parseable;
    int manifest_has_package;
    int manifest_has_version;
    int manifest_has_entries;
    int manifest_has_qikvrt_paths;
    int manifest_has_license_paths;
    int rest_tcpip_manifest_reachable;
    int rest_tcpip_manifest_parseable;
    int rest_tcpip_capabilities_present;
    int no_service_except_github_seed;
    int no_global_address_scan;
    int no_unauthorized_probing;
    int audit_log;
    int reference_result_persisted;
    int final_pass_requested;
};

int qikvrt_real_github_seed_manifest_validate_text(const char *manifest_text, struct qikvrt_result *result);
int qikvrt_real_github_seed_integration_validate(const struct qikvrt_real_github_seed_integration_contract *gi, struct qikvrt_result *result);
int qikvrt_selftest_real_github_seed_integration(struct qikvrt_result *result);

struct qikvrt_zip_layout_contract {
    int root_readme_present;
    int root_makefile_present;
    int root_sha256sums_present;
    int root_src_present;
    int root_tests_present;
    int root_docs_present;
    int flat_archive_required;
    int no_wrapper_only_extraction;
    int windows_tar_compatible;
    int acceptance_runner_compatible;
    int traceability;
};

int qikvrt_zip_layout_contract_validate(const struct qikvrt_zip_layout_contract *zc, struct qikvrt_result *result);
int qikvrt_repository_root_layout_validate(const char *root, struct qikvrt_result *result);
int qikvrt_selftest_zip_layout(struct qikvrt_result *result);

struct qikvrt_windows_shell_zip_contract {
    int explicit_directory_entries;
    int dos_create_system;
    int dos_archive_attribute_for_files;
    int dos_directory_attribute_for_dirs;
    int flat_root_content_visible;
    int no_absolute_paths;
    int no_drive_letters;
    int no_parent_traversal;
    int sha256_payload_only;
    int no_windows_shell_empty_extraction_final_pass;
    int traceability;
};

int qikvrt_windows_shell_zip_contract_validate(const struct qikvrt_windows_shell_zip_contract *wc, struct qikvrt_result *result);
int qikvrt_selftest_windows_shell_zip(struct qikvrt_result *result);


struct qikvrt_short_path_contract {
    int short_external_archive_name_required;
    int max_archive_name_length;
    int max_internal_path_length;
    int flat_root_content_visible;
    int no_wrapper_directory;
    int no_absolute_paths;
    int no_drive_letters;
    int no_parent_traversal;
    int windows_max_path_margin;
    int no_short_path_final_pass_without_evidence;
    int traceability;
};

int qikvrt_short_path_contract_validate(const struct qikvrt_short_path_contract *sp, struct qikvrt_result *result);
int qikvrt_selftest_short_path(struct qikvrt_result *result);


struct qikvrt_live_evidence_contract {
    const char *seed_repository;
    const char *manifest_url;
    const char *rest_tcpip_manifest_url;
    int github_web_visibility_confirmed;
    int raw_manifest_reference_present;
    int rest_tcpip_reference_present;
    int local_c_posix_dns_block_recorded;
    int external_runner_required;
    int evidence_ledger_present;
    int no_live_final_pass_without_external_fetch;
    int traceability;
};

struct qikvrt_article_claim_contract {
    const char *claim_id;
    const char *evidence_class;
    int implemented_or_future_classified;
    int no_article_property_claim_without_evidence;
    int biometric_sso_marked_future_application;
    int ai_self_improvement_marked_governed_future_application;
    int peer_discovery_marked_live_test_required;
    int science_belief_retrocausality_marked_conceptual;
    int traceability;
};

int qikvrt_live_evidence_contract_validate(const struct qikvrt_live_evidence_contract *lc, struct qikvrt_result *result);
int qikvrt_article_claim_contract_validate(const struct qikvrt_article_claim_contract *cc, struct qikvrt_result *result);
int qikvrt_live_evidence_file_validate_text(const char *evidence_text, struct qikvrt_result *result);
int qikvrt_selftest_live_evidence(struct qikvrt_result *result);
int qikvrt_selftest_article_claim_matrix(struct qikvrt_result *result);


struct qikvrt_node_onboarding_contract {
    const char *node_profile;
    const char *guid_source;
    int generic_node_profile;
    int no_person_bound_default;
    int operator_alias_optional;
    int authorized_seed_graph;
    int local_runtime_profile;
    int privacy_preserved_evidence;
    int watchdog_ready;
    int selftest_requestable;
    int handover_ready;
    int final_pass_requested;
};

int qikvrt_node_onboarding_validate(const struct qikvrt_node_onboarding_contract *no, struct qikvrt_result *result);
int qikvrt_selftest_node_onboarding(struct qikvrt_result *result);



struct qikvrt_rest_api_contract {
    const char *api_name;
    const char *openapi_source;
    const char *local_server;
    const char *github_server;
    int health_endpoint;
    int workflow_dispatch_endpoint;
    int repository_dispatch_endpoint;
    int operation_ingest;
    int operation_verify;
    int operation_stage;
    int operation_release_status;
    int identical_api_for_seed_and_node;
    int role_config_only;
    int json_request_response;
    int traceability;
    int authorization_required_for_mutating_calls;
    int no_remote_mutation_without_authorization;
    int no_secret_exposure;
    int final_pass_requested;
};

int qikvrt_rest_api_contract_validate(const struct qikvrt_rest_api_contract *ra, struct qikvrt_result *result);
int qikvrt_selftest_rest_api(struct qikvrt_result *result);

struct qikvrt_unified_node_core_contract {
    const char *core_name;
    const char *role_normal;
    const char *role_seed;
    const char *api_contract;
    int identical_inner_build;
    int same_rest_api;
    int same_testbed_core;
    int runtime_role_config;
    int seed_specific_assertions_only;
    int node_specific_assertions_only;
    int no_api_fork;
    int no_seed_node_code_split;
    int github_openapi_aligned;
    int local_shim_port_8766;
    int workflow_dispatch_semantics;
    int repository_dispatch_semantics;
    int operation_enum_enforced;
    int evidence_persisted;
    int no_runtime_staging_self_copy;
    int final_pass_requested;
};

int qikvrt_unified_node_core_validate(const struct qikvrt_unified_node_core_contract *uc, struct qikvrt_result *result);
int qikvrt_selftest_unified_node_core(struct qikvrt_result *result);

struct qikvrt_node_onboarding_testbed_contract {
    const char *profile;
    const char *seed_repository;
    const char *rest_api_contract;
    int ontology_difference_to_information;
    int ontology_information_to_causality;
    int constitution_articles_verified;
    int node_onboarding_generic;
    int guid_bootstrap;
    int service_startup_order;
    int github_seed_live_evidence;
    int peer_graph_discovery;
    int rest_api_contract_present;
    int unified_node_core;
    int same_api_for_seed_and_normal_node;
    int role_config_matrix;
    int github_compatible_openapi;
    int local_shim_and_github_dispatch_semantics;
    int request_response_traceability;
    int security_boundary;
    int safety_boundary;
    int windows_runtime_acceptance_evidence;
    int no_person_bound_default;
    int no_unauthorized_scanning;
    int no_remote_mutation_without_authorization;
    int evidence_persisted;
    int no_runtime_staging_self_copy;
    int final_pass_requested;
};

int qikvrt_node_onboarding_testbed_validate(const struct qikvrt_node_onboarding_testbed_contract *nt, struct qikvrt_result *result);
int qikvrt_selftest_node_onboarding_testbed(struct qikvrt_result *result);


struct qikvrt_license_visibility_contract {
    const char *author;
    const char *rights_holder;
    const char *software_license;
    const char *document_license;
    int source_headers_present;
    int document_headers_present;
    int document_footers_present;
    int json_metadata_parseable;
    int no_final_pass_without_license_visibility;
    int final_pass_requested;
};

struct qikvrt_full_test_environment_contract {
    int ontology_tests;
    int requirements_coverage;
    int unit_tests;
    int integration_tests;
    int acceptance_tests;
    int performance_tests;
    int security_tests;
    int runtime_rest_api_tests;
    int reusable_core;
    int seed_role_profile;
    int normal_role_profile;
    int same_api_for_roles;
    int evidence_persisted;
    int no_runtime_staging_self_copy;
    int final_pass_requested;
};

struct qikvrt_seed_node_delivery_contract {
    const char *seed_zip;
    const char *node_zip;
    int independent_seed_zip;
    int independent_node_zip;
    int same_inner_architecture;
    int same_api;
    int role_config_only;
    int seed_profile_present;
    int node_profile_present;
    int delivery_manifest_present;
    int final_pass_requested;
};

int qikvrt_license_visibility_validate(const struct qikvrt_license_visibility_contract *lc, struct qikvrt_result *result);
int qikvrt_full_test_environment_validate(const struct qikvrt_full_test_environment_contract *ft, struct qikvrt_result *result);
int qikvrt_seed_node_delivery_validate(const struct qikvrt_seed_node_delivery_contract *sd, struct qikvrt_result *result);
int qikvrt_selftest_license_visibility(struct qikvrt_result *result);
int qikvrt_selftest_full_test_environment(struct qikvrt_result *result);
int qikvrt_selftest_seed_node_delivery(struct qikvrt_result *result);


struct qikvrt_bilingual_contract {
    int documentation_bilingual_header;
    int documentation_bilingual_footer;
    int german_visible;
    int english_visible;
    int license_visible;
    int applies_to_non_source_files;
    int no_final_pass_without_bilingual_docs;
    int final_pass_requested;
};

struct qikvrt_github_deploy_contract {
    int windows_cmd_script_present;
    int posix_shell_script_present;
    int powershell_deploy_helper_present;
    int posix_deploy_helper_present;
    int owner_repo_runtime_resolution;
    int env_resolution;
    int git_remote_resolution;
    int prompt_fallback;
    int token_required_for_remote_mutation;
    int dry_run_supported;
    int seed_and_node_role_aware;
    int no_hardcoded_owner_repo;
    int no_unauthorized_remote_mutation;
    int evidence_persisted;
    int no_runtime_staging_self_copy;
    int final_pass_requested;
};

int qikvrt_bilingual_contract_validate(const struct qikvrt_bilingual_contract *bi, struct qikvrt_result *result);
int qikvrt_github_deploy_contract_validate(const struct qikvrt_github_deploy_contract *gd, struct qikvrt_result *result);
int qikvrt_selftest_bilingual_docs(struct qikvrt_result *result);
int qikvrt_selftest_github_deploy(struct qikvrt_result *result);

void qikvrt_print_version(void);

struct qikvrt_repository_setup_contract {
    int setup_scripts_present;
    int guid_generated_on_first_setup;
    int guid_persisted;
    int github_owner_repo_prompted_with_defaults;
    int github_target_persisted;
    int seed_target_persisted;
    int no_prompt_after_setup;
    int node_identifies_to_seed_with_guid;
    int onboarding_request_persisted;
    int runtime_uses_persisted_target;
    int remote_mutation_requires_token;
    int no_global_scanning;
    int no_self_propagation;
    int final_pass_requested;
};

int qikvrt_repository_setup_validate(const struct qikvrt_repository_setup_contract *rs, struct qikvrt_result *result);
int qikvrt_selftest_repository_setup(struct qikvrt_result *result);

#endif
