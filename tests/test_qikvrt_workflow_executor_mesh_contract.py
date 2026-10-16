# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import base64
import hashlib
import importlib.util
import json
import io
import os
import pathlib
import subprocess
import sys
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SELF_HEALING_CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
NODE_POLICY = ROOT / "registry/NODE_DISCOVERY_POLICY.json"
EXECUTOR_WORKFLOW = ROOT / ".github/workflows/qikvrt_workflow_executor.yml"
WATCHDOG_WORKFLOW = ROOT / ".github/workflows/qikvrt_workflow_executor_watchdog.yml"
LIVE_WATCH = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"

SPEC = importlib.util.spec_from_file_location(
    "qikvrt_workflow_executor",
    ROOT / "tools/qikvrt_workflow_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def active_role_policy() -> dict:
    return json.loads((ROOT / MODULE.ROLE_POLICY_PATH).read_text(encoding="utf-8"))


def active_governance_policy() -> dict:
    return json.loads((ROOT / MODULE.GOVERNANCE_POLICY_PATH).read_text(encoding="utf-8"))


class WorkflowExecutorMeshContractTests(unittest.TestCase):
    def test_contract_is_authority_first_and_effect_bounded(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "qikvrt_workflow_executor_mesh_contract_v1")
        self.assertEqual(contract["authority"]["repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(contract["authority"]["mirror_repositories"], ["Goldkelch/qik-vrt"])
        self.assertEqual(contract["authority"]["entrypoint"], "AI")
        self.assertEqual(
            contract["executor"]["single_writer_order"],
            ["AUTHORITY", "MIRROR", "MESH_NODE"],
        )
        self.assertEqual(
            contract["dispatch_policy"]["authorized_workflows"],
            [
                {
                    "workflow_id": "qikvrt_workflow_executor_watchdog.yml",
                    "workflow_path": ".github/workflows/qikvrt_workflow_executor_watchdog.yml",
                    "workflow_name": "QIKVRT workflow executor watchdog",
                    "allowed_events": ["workflow_dispatch"],
                    "external_effect": "NONE",
                    "is_writer": False,
                    "required_artifact_prefix": "qikvrt-workflow-executor-watchdog-",
                }
            ],
        )
        boundaries = contract["boundaries"]
        self.assertEqual(boundaries["direct_repository_mutation"], "FORBIDDEN")
        self.assertFalse(boundaries["watchdog_terminality_is_gate_success"])
        self.assertFalse(boundaries["action_required_is_trusted_execution"])
        self.assertFalse(boundaries["zero_job_is_trusted_execution"])
        continuity = contract["mesh_node_split_acceptance"]
        self.assertEqual(continuity["applies_to"], "EVERY_FUTURE_NODE_ADDED_BY_QUEUE_ROW")
        self.assertEqual(
            continuity["required_acceptance_tests"],
            [
                "tests/test_qikvrt_workflow_executor_mesh_contract.py",
                "tests/test_seed_workflows.py",
            ],
        )
        self.assertEqual(
            continuity["connection_order"],
            [
                "AUTHORITY_CONTRACT_BOUND",
                "NODE_RECEIPT_DECLARED",
                "NODE_STRUCTURAL_ACCEPTANCE",
                "SEED_QUEUE_ACCEPTANCE",
                "WATCHDOG_OBSERVATION",
            ],
        )

    def test_self_healing_and_node_policy_point_to_the_same_continuity_contract(self) -> None:
        self_healing = json.loads(SELF_HEALING_CONTRACT.read_text(encoding="utf-8"))
        bridge = self_healing["workflow_executor_mesh_continuity"]
        self.assertEqual(bridge["contract_path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(bridge["controller_path"], "tools/qikvrt_workflow_executor.py")
        self.assertEqual(bridge["external_effect"], "FORBIDDEN")
        policy = json.loads(NODE_POLICY.read_text(encoding="utf-8"))
        future = policy["future_node_split_acceptance"]
        self.assertTrue(policy["future_nodes_added_by_queue_rows"])
        self.assertTrue(future["required_for_queue_rows"])
        self.assertEqual(future["contract_path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(
            future["acceptance_test_path"],
            "tests/test_qikvrt_workflow_executor_mesh_contract.py",
        )

    def test_snapshot_binds_every_workflow_to_the_exact_head_and_tree(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
            text=True,
        ).strip()
        tree = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{tree}"],
            text=True,
        ).strip()
        self.assertEqual(snapshot["head_sha"], head)
        self.assertEqual(snapshot["tree_sha"], tree)
        self.assertRegex(snapshot["workflow_inventory_sha256"], r"^[0-9a-f]{64}$")
        paths = {entry["path"] for entry in snapshot["workflow_inventory"]}
        self.assertIn(".github/workflows/qikvrt_workflow_executor.yml", paths)
        self.assertIn(".github/workflows/qikvrt_workflow_executor_watchdog.yml", paths)
        self.assertEqual(snapshot["workflow_delta"]["state"], "BASELINE_UNAVAILABLE")
        baseline = {"workflow_inventory": [{"path": path, "blob_sha": "0" * 40} for path in paths]}
        delta = MODULE.workflow_delta(snapshot["workflow_inventory"], baseline)
        self.assertEqual(delta["state"], "COMPARED")
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(sorted(delta["changed"]), sorted(paths))

    def test_plan_is_exact_head_deduplicated_and_writer_serialized(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        empty_plan = MODULE.dispatch_plan(snapshot, {"workflow_runs": []}, "main")
        candidate = empty_plan["candidates"][0]
        self.assertEqual(empty_plan["state"], "DISPATCH_CANDIDATE_READY")
        self.assertEqual(candidate["disposition"], "DISPATCH")
        self.assertEqual(candidate["head_sha"], snapshot["head_sha"])
        self.assertEqual(candidate["tree_sha"], snapshot["tree_sha"])
        self.assertRegex(candidate["workflow_blob_sha"], r"^[0-9a-f]{40}$")

        terminal = MODULE.dispatch_plan(
            snapshot,
            {
                "workflow_runs": [
                    {
                        "id": 7,
                        "name": "QIKVRT workflow executor watchdog",
                        "head_sha": snapshot["head_sha"],
                        "status": "completed",
                        "conclusion": "action_required",
                    }
                ]
            },
            "main",
        )
        self.assertEqual(terminal["candidates"][0]["disposition"], "HOLD")
        self.assertEqual(
            terminal["candidates"][0]["first_blocker"],
            "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE",
        )
        writer = MODULE.dispatch_plan(
            snapshot,
            {
                "workflow_runs": [
                    {
                        "id": 8,
                        "name": "QIK-VRT autonomous bounded self-heal",
                        "head_sha": snapshot["head_sha"],
                        "status": "in_progress",
                    }
                ]
            },
            "main",
        )
        self.assertEqual(writer["candidates"][0]["first_blocker"], "COMPETING_WRITER_ACTIVE")

    def test_pending_role_policy_prevents_dispatch(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        with mock.patch.object(MODULE, "_read_json_file", return_value={"status": "ACTIVE"}):
            value = MODULE.dispatch_plan(snapshot, {"workflow_runs": []}, "main")
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["candidates"][0]["first_blocker"], "CANONICAL_ROLE_POLICY_INVALID")

    def test_dispatch_wrapper_reads_authority_with_the_mandatory_job_token_before_planning(self) -> None:
        step = EXECUTOR_WORKFLOW.read_text().split("      - name: Build exact-head dispatch plan\n", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("GH_TOKEN: ${{ github.token }}", step)
        self.assertLess(step.index("readback_args=(authority-readback --json)"), step.index("args=(plan"))

    def test_authority_targets_must_agree_and_mirror_is_never_authority(self) -> None:
        contract = MODULE.load_contract(ROOT)
        for change in ("liveness", "mirror"):
            damaged = copy.deepcopy(contract)
            if change == "liveness":
                damaged["reflexive_deadlock_prevention"]["gatewatch"]["node_liveness"]["authority_repository"] = "Goldkelch/qik-vrt"
            else:
                damaged["authority"]["mirror_repositories"].append("INGOLF-LOHMANN/QIK-VRT")
            with self.subTest(change=change), self.assertRaises(MODULE.ExecutorBlock):
                MODULE._validate_contract_shape(damaged, ROOT)

    def test_mirror_receipt_with_equal_head_cannot_supply_authority_continuity(self) -> None:
        receipt = MODULE.build_node_receipt("example/node", "main", ROOT)
        receipt["authority"]["repository"] = "Goldkelch/qik-vrt"
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "authority binding"):
            MODULE.validate_node_receipt(receipt, "example/node", "main", ROOT)


    def test_node_receipt_requires_the_declared_acceptance_order(self) -> None:
        receipt = MODULE.build_node_receipt("example/node", "main", ROOT)
        validation = MODULE.validate_node_receipt(receipt, "example/node", "main", ROOT)
        self.assertEqual(validation["state"], "NODE_SPLIT_CONTINUITY_ACCEPTANCE_READY")
        declaration = {
            "workflow_executor_continuity": {
                "schema": "qikvrt_workflow_executor_mesh_continuity_declaration_v1",
                "receipt_path": "state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json",
                "receipt_url": MODULE.expected_node_receipt_url("example/node", "main"),
                "acceptance_required": True,
            }
        }
        self.assertEqual(
            MODULE.validate_node_continuity_declaration(declaration, "example/node", "main"),
            declaration["workflow_executor_continuity"]["receipt_url"],
        )
        damaged = copy.deepcopy(receipt)
        damaged["acceptance"]["required_tests"] = []
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "acceptance tests"):
            MODULE.validate_node_receipt(damaged, "example/node", "main", ROOT)

    def test_executor_and_watchdogs_cannot_cross_the_effect_boundary(self) -> None:
        executor = EXECUTOR_WORKFLOW.read_text(encoding="utf-8")
        watchdog = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
        live_watch = LIVE_WATCH.read_text(encoding="utf-8")
        self.assertIn("actions: write", executor)
        self.assertIn("qikvrt_workflow_executor.py", executor)
        self.assertIn("/dispatches", executor)
        self.assertIn("test \"$refreshed_head\" = \"$head\"", executor)
        self.assertNotIn("gh pr merge", executor)
        self.assertNotIn("zenodo", executor.casefold())
        self.assertNotIn("ietf", executor.casefold())
        self.assertIn("contents: read", watchdog)
        self.assertIn("tests.test_qikvrt_workflow_executor_mesh_contract", watchdog)
        self.assertIn("qikvrt-workflow-executor-watchdog-", watchdog)
        self.assertNotIn("/dispatches", watchdog)
        self.assertIn("github.event_name == 'pull_request'", live_watch)

    def test_watchdog_binds_the_literal_pull_request_head(self) -> None:
        watchdog = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
        exact_event_head = "${{ github.event.pull_request.head.sha || github.sha }}"
        self.assertIn(f"ref: {exact_event_head}", watchdog)
        self.assertIn(f"EXPECTED_HEAD: {exact_event_head}", watchdog)
        self.assertIn('test "$head" = "$EXPECTED_HEAD"', watchdog)
        self.assertIn('snapshot --expect-head "$EXPECTED_HEAD"', watchdog)
        self.assertNotIn('snapshot --expect-head "$head"', watchdog)



class RepositoryRoleResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        paths = [MODULE.ROLE_POLICY_PATH, MODULE.GOVERNANCE_POLICY_PATH,
                 MODULE.CONTRACT_RELATIVE_PATH,
                 "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json",
                 "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json",
                 "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json",
                 "policy/QIKVRT_ETHICAL_EVOLUTIONARY_DIGITAL_TWIN_MESH_V1.json",
                 "tools/qikvrt_workflow_executor.py",
                 ".github/workflows/qikvrt_workflow_executor.yml",
                 ".github/workflows/qikvrt_reflexive_repository_watchdog.yml"]
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)

    def test_one_normative_policy_resolves_both_roles_and_all_projections(self) -> None:
        self.assertEqual(MODULE.validate_role_projections(self.root), {
            "AUTHORITY": "ingolf-lohmann/qik-vrt", "MIRROR": "Goldkelch/qik-vrt"})

    def test_historical_publication_or_tag_requests_cannot_reassign_live_roles(self) -> None:
        for nested in (False, True):
            binding = {"authority_repository": "Goldkelch/qik-vrt",
                       "mirror_repository": "ingolf-lohmann/qik-vrt"}
            document = {"repository_policy": binding} if nested else binding
            with self.subTest(nested=nested), self.assertRaisesRegex(MODULE.ExecutorBlock, "HISTORICAL_ROLE_REQUEST_NOT_CURRENT"):
                MODULE.validate_request_roles(document, self.root)
            binding.update(authority_repository="ingolf-lohmann/qik-vrt", mirror_repository="Goldkelch/qik-vrt")
            self.assertEqual(MODULE.validate_request_roles(document, self.root)["AUTHORITY"], "ingolf-lohmann/qik-vrt")

    def test_legacy_effect_wrappers_use_the_shared_projection_guard(self) -> None:
        for name in ("qikvrt_zenodo_reserve.yml", "qikvrt_effect_ack_finalize.yml",
                     "qikvrt_status_report_reserve.yml", "qikvrt_status_report_finalize.yml",
                     "qikvrt_formalization_v2_zenodo.yml", "qikvrt_formalization_v2_zenodo_finalize.yml",
                     "qikvrt_repository_mesh_sync_tag.yml", "publish_ontology_difference_article_zenodo_v3.yml"):
            workflow = (ROOT / ".github/workflows" / name).read_text()
            with self.subTest(name=name):
                self.assertIn("roles --projection-file", workflow)
                self.assertLess(workflow.index("roles --projection-file"), workflow.index("urllib.request"))

    def test_issue_autofinish_cannot_be_a_second_authority_or_ungoverned_writer(self) -> None:
        workflow = (ROOT / ".github/workflows/issue-agent-autofinish.yml").read_text()
        self.assertIn("validate_role_projections()", workflow)
        self.assertIn("evaluate_required_review", workflow)
        self.assertIn("qikvrt_expected_head_promotion.yml", workflow)
        for forbidden in ("AUTHORITY_REPOSITORY:", "MIRROR_REPOSITORY:", "gh pr merge",
                          "git push", "--force", "gh issue close", "QIKVRT_MESH_TOKEN"):
            self.assertNotIn(forbidden, workflow)

    def test_missing_or_malformed_policy_never_falls_back_to_a_repository_name(self) -> None:
        path = self.root / MODULE.ROLE_POLICY_PATH
        for raw in (b"{", b"[]", b"{}"):
            path.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(MODULE.ExecutorBlock):
                MODULE.load_repository_roles(self.root)
        path.unlink()
        with self.assertRaises(MODULE.ExecutorBlock):
            MODULE.load_repository_roles(self.root)

    def test_conflicting_or_overlapping_role_definitions_are_rejected(self) -> None:
        original = active_role_policy()
        mutations = [("canonical_upstream", "role", "MIRROR"),
                     ("mirror", "repository", "INGOLF-LOHMANN/QIK-VRT"),
                     ("canonical_upstream", "canonical_api_repository", "https://api.github.com/repos/Goldkelch/qik-vrt")]
        for binding, key, value in mutations:
            policy = copy.deepcopy(original)
            policy[binding][key] = value
            with self.subTest(key=key), self.assertRaises(MODULE.ExecutorBlock):
                MODULE.resolve_repository_roles(policy)
        for key in ("selection_rule", "exact_head_contract", "promotion_contract"):
            policy = copy.deepcopy(original)
            policy[key] = []
            with self.subTest(key=key), self.assertRaises(MODULE.ExecutorBlock):
                MODULE.resolve_repository_roles(policy)

    def test_every_live_projection_rejects_a_conflicting_authority(self) -> None:
        for relative, pointer in (
            (MODULE.CONTRACT_RELATIVE_PATH, ("authority", "repository")),
            (MODULE.GOVERNANCE_POLICY_PATH, ("mesh_authority", "authority_repository")),
            ("policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json", ("authority_repository",)),
            ("policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json", ("authority_repository",)),
            ("policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json", ("authority_repository",)),
            ("policy/QIKVRT_ETHICAL_EVOLUTIONARY_DIGITAL_TWIN_MESH_V1.json", ("reciprocal_rest", "authority_repository")),
        ):
            path = self.root / relative
            original = path.read_bytes()
            document = json.loads(original)
            parent = document
            for key in pointer[:-1]:
                parent = parent[key]
            parent[pointer[-1]] = "Goldkelch/qik-vrt"
            path.write_text(json.dumps(document))
            with self.subTest(relative=relative), self.assertRaises(MODULE.ExecutorBlock):
                MODULE.validate_role_projections(self.root)
            path.write_bytes(original)

    def test_unrelated_lifecycle_progress_cannot_admit_an_unchanged_denied_retry(self) -> None:
        before = MODULE.authority_retry_binding(self.root)
        path = self.root / MODULE.CONTRACT_RELATIVE_PATH
        document = json.loads(path.read_bytes())
        document["unrelated_progress_at"] = "2026-10-10T23:59:59Z"
        path.write_text(json.dumps(document))
        self.assertEqual(MODULE.authority_retry_binding(self.root), before)
        with (self.root / ".github/workflows/qikvrt_workflow_executor.yml").open("a") as stream:
            stream.write("\n# changed token/transport carrier\n")
        self.assertNotEqual(MODULE.authority_retry_binding(self.root), before)


class AuthorityReadbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = []
        self.head = "a" * 40
        self.tree = "c" * 40
        self.api_root = "https://api.github.com/repos/ingolf-lohmann/qik-vrt/git"
        self.ref = {
            "ref": "refs/heads/main", "url": self.api_root + "/refs/heads/main",
            "object": {"type": "commit", "sha": self.head,
                       "url": self.api_root + "/commits/" + self.head},
        }
        self.policy = active_role_policy()
        self.governance = active_governance_policy()
        self.codeowners = (ROOT / ".github/CODEOWNERS").read_bytes()
        self.environment = mock.patch.dict(MODULE.os.environ, {"GH_TOKEN": "test-job-token"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def get(self, argv, **kwargs):
        self.calls.append(argv)
        self.assertEqual(argv[:6], ["gh", "api", "--hostname", "github.com", "--method", "GET"])
        self.assertTrue(argv[-1].startswith("repos/ingolf-lohmann/qik-vrt/"))
        if "/contents/" in argv[-1]:
            self.assertTrue(argv[-1].endswith("?ref=" + self.head))
            path = argv[-1].split("/contents/", 1)[1].split("?ref=", 1)[0]
            documents = {MODULE.ROLE_POLICY_PATH: json.dumps(self.policy).encode(),
                         MODULE.GOVERNANCE_POLICY_PATH: json.dumps(self.governance).encode(),
                         ".github/CODEOWNERS": self.codeowners}
            raw = documents[path]
            blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            value = {"path": path, "type": "file", "encoding": "base64", "size": len(raw),
                     "content": base64.b64encode(raw).decode(), "sha": blob,
                     "git_url": self.api_root + "/blobs/" + blob}
        elif "/git/commits/" in argv[-1]:
            value = {"sha": self.head, "tree": {"sha": self.tree,
                     "url": self.api_root + "/trees/" + self.tree}}
        else:
            value = self.ref
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")

    def test_exact_authority_main_readback_checks_all_roles_and_reobserves_head(self) -> None:
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            value = MODULE.read_authority_main(ROOT)
        self.assertEqual(value["repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(value["main_head"], self.head)
        self.assertEqual(value["main_tree"], self.tree)
        self.assertEqual(value["required_code_owner"], "ingolf-lohmann")
        self.assertEqual(value["state"], "AUTHORITY_MAIN_ROLE_POLICY_REOBSERVED")
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(self.calls[0], self.calls[5])
        self.assertFalse(value["native_activation_verified"])
        self.assertFalse(any(value["completion_claims"].values()))

    def test_access_denials_have_no_mirror_or_anonymous_fallback(self) -> None:
        for status in (403, 404):
            for denied_call in range(1, 7):
                self.calls = []
                def denied(argv, **kwargs):
                    if len(self.calls) + 1 == denied_call:
                        self.calls.append(argv)
                        return subprocess.CompletedProcess(argv, 1, "", f"gh: Forbidden (HTTP {status})")
                    return self.get(argv, **kwargs)
                with self.subTest(status=status, call=denied_call), mock.patch.object(MODULE.subprocess, "run", side_effect=denied):
                    with self.assertRaisesRegex(MODULE.ExecutorBlock, f"AUTHORITY_READBACK_DENIED HTTP_{status}"):
                        MODULE.read_authority_main(ROOT)
                self.assertEqual(len(self.calls), denied_call)
                self.assertTrue(all("Goldkelch" not in call[-1] for call in self.calls))

    def test_same_denied_read_prerequisites_never_repeat_an_http_request(self) -> None:
        previous = {"retry_binding_sha256": MODULE.authority_retry_binding(ROOT),
                    "first_blocker": "AUTHORITY_READBACK_DENIED HTTP_404",
                    "head_sha": "b" * 40, "observed_at": "2026-10-09T00:00:00Z"}
        with mock.patch.object(MODULE.subprocess, "run") as api:
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "HTTP_404"):
                MODULE.read_authority_main(ROOT, previous)
        api.assert_not_called()

    def test_changed_causal_binding_permits_one_fresh_read_sequence(self) -> None:
        previous = {"retry_binding_sha256": "0" * 64,
                    "first_blocker": "AUTHORITY_READBACK_DENIED HTTP_404"}
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            value = MODULE.read_authority_main(ROOT, previous)
        self.assertEqual(value["main_head"], self.head)
        self.assertEqual(len(self.calls), 6)

    def test_http_200_without_main_role_activation_remains_hold(self) -> None:
        # A successful GET of the personal repository cannot activate its old Main policy.
        authority = self.policy["canonical_upstream"]["repository"]
        mirror = self.policy["mirror"]["repository"]
        for key, repository in (("canonical_upstream", mirror), ("mirror", authority)):
            self.policy[key]["repository"] = repository
            self.policy[key]["canonical_https_url"] = f"https://github.com/{repository}.git"
            self.policy[key]["canonical_api_repository"] = f"https://api.github.com/repos/{repository}"
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "AUTHORITY_ROLE_BINDING_NOT_ACTIVE"):
                MODULE.read_authority_main(ROOT)
        self.assertEqual(len(self.calls), 3)

    def test_missing_job_token_never_attempts_a_get(self) -> None:
        with mock.patch.dict(MODULE.os.environ, {"GH_TOKEN": ""}), mock.patch.object(MODULE.subprocess, "run") as api:
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "JOB_TOKEN_REQUIRED"):
                MODULE.read_authority_main(ROOT)
        api.assert_not_called()

    def test_native_review_requirement_and_code_owner_cannot_be_downgraded(self) -> None:
        self.governance["mesh_authority"]["independent_native_code_owner_review_required"] = False
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "PROTECTION_BOUNDARY_INVALID"):
                MODULE.read_authority_main(ROOT)
        self.governance = active_governance_policy()
        self.codeowners = b"* @Goldkelch\n"
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "CODE_OWNER_POLICY_MISMATCH"):
                MODULE.read_authority_main(ROOT)

    def test_timeout_and_invalid_response_are_fail_closed(self) -> None:
        for response in (subprocess.TimeoutExpired("gh", 30), subprocess.CompletedProcess([], 0, "not JSON", "")):
            with self.subTest(response=type(response).__name__), mock.patch.object(MODULE.subprocess, "run", side_effect=response if isinstance(response, Exception) else None, return_value=response):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.read_authority_main(ROOT)

    def test_policy_blob_commit_identity_and_main_head_drift_are_rejected(self) -> None:
        for fault in ("blob", "head", "ref", "mirror_repository", "commit", "tree", "size", "content_repository"):
            self.calls = []
            def damaged(argv, **kwargs):
                response = self.get(argv, **kwargs)
                value = json.loads(response.stdout)
                if fault == "blob" and "/contents/" in argv[-1]:
                    value["sha"] = "b" * 40
                elif fault == "head" and len(self.calls) == 6:
                    value["object"]["sha"] = "b" * 40
                    value["object"]["url"] = value["object"]["url"].replace(self.head, "b" * 40)
                elif fault == "ref" and "/git/ref/" in argv[-1]:
                    value["ref"] = "refs/heads/mirror"
                elif fault == "mirror_repository" and "/git/ref/" in argv[-1]:
                    value["url"] = value["url"].replace("ingolf-lohmann", "Goldkelch")
                elif fault == "commit" and "/git/commits/" in argv[-1]:
                    value["sha"] = "b" * 40
                elif fault == "tree" and "/git/commits/" in argv[-1]:
                    value["tree"]["url"] = value["tree"]["url"].replace("ingolf-lohmann", "Goldkelch")
                elif fault == "size" and "/contents/" in argv[-1]:
                    value["size"] += 1
                elif fault == "content_repository" and "/contents/" in argv[-1]:
                    value["git_url"] = value["git_url"].replace("ingolf-lohmann", "Goldkelch")
                return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
            with self.subTest(fault=fault), mock.patch.object(MODULE.subprocess, "run", side_effect=damaged):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.read_authority_main(ROOT)


class OwnerSigningContinuationTests(unittest.TestCase):
    """Provider fixtures verify routing and failure semantics, never live signing."""

    def setUp(self):
        self.head, self.tree = "a" * 40, "b" * 40
        self.contract = json.loads(CONTRACT.read_bytes())
        self.request = self.contract["owner_authorized_operations"][MODULE.AMO_SCOPE]
        self.package = self.request["unsigned_xpi_sha256"]
        patch = mock.patch.object(MODULE, "load_contract", return_value=self.contract)
        patch.start(); self.addCleanup(patch.stop)
        self.context = {"repository": MODULE.AMO_REPOSITORY, "ref": "refs/heads/main",
            "event": "push", "workflow_ref": f"{MODULE.AMO_REPOSITORY}/{MODULE.AMO_NATIVE_WORKFLOW}@refs/heads/main",
            "head": self.head, "tree": self.tree, "run_id": 500, "run_attempt": 1,
            "issuer_present": True, "secret_present": True, "binding_revision": "initial"}
        self.authority = {"repository": MODULE.AMO_REPOSITORY, "main_head": self.head,
            "main_tree": self.tree, "state": "AUTHORITY_MAIN_ROLE_POLICY_REOBSERVED"}
        self.branch = {"name": "main", "protected": True}
        self.rules = [{"type": "pull_request", "parameters": {"required_approving_review_count": 1,
            "require_code_owner_review": True, "require_last_push_approval": True}},
            {"type": "non_fast_forward"}, {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True, "required_status_checks": [
                    {"context": "test"}, {"context": "QIKVRT required code-owner review"}]}}]
        self.subject = {"repository": MODULE.AMO_REPOSITORY, "source_head": self.head,
            "source_tree": self.tree, "unsigned_xpi_sha256": self.package}

    def plan(self, previous=None, **overrides):
        context = {**self.context, **overrides}
        authority = {**self.authority, "main_head": context["head"]}
        subject = {**self.subject, "source_head": context["head"]}
        return MODULE.amo_intent(ROOT, context, authority, self.branch, self.rules, subject, previous, True)

    def response(self, target=600):
        return {"workflow_run_id": target,
            "run_url": f"https://api.github.com/repos/{MODULE.AMO_REPOSITORY}/actions/runs/{target}",
            "html_url": f"https://github.com/{MODULE.AMO_REPOSITORY}/actions/runs/{target}"}

    def attempt(self, state="ACCEPTED", readback=False):
        intent = self.plan(readback_only=readback)
        intent["readback_only"] = readback
        receipt = MODULE.amo_dispatch_record(intent, self.response())
        receipt["last_attempt"]["state"] = state
        return receipt

    def provider_run(self, run_id, workflow=None, status="completed", conclusion="success", **changes):
        return {"id": run_id, "path": workflow or MODULE.AMO_CI_WORKFLOW,
            "name": "QIKVRT CI", "repository": {"full_name": MODULE.AMO_REPOSITORY},
            "head_repository": {"full_name": MODULE.AMO_REPOSITORY}, "head_branch": "main",
            "head_sha": self.head, "run_attempt": 1, "event": "workflow_dispatch",
            "created_at": "2026-10-17T00:00:00Z", "status": status, "conclusion": conclusion, **changes}

    def job(self, status="completed", conclusion="success", name="Mozilla AMO unlisted access and exact-source signing"):
        return {"id": 700, "name": name, "status": status, "conclusion": conclusion,
                "steps": [{"number": 1, "name": "Official source-bound unlisted signing and original-byte readback",
                           "status": status, "conclusion": conclusion, "started_at": "2026-10-17T00:00:01Z"}]}

    def original(self, executor=500, signed=True):
        value = {"ACCESS_PREFLIGHT.json": MODULE.canonical_json_bytes({"executor_run_id": executor})}
        if signed:
            raw = b"synthetic original XPI; no real signature claim"
            value.update({"standard-signed.xpi": raw,
                "AMO_SIGNING_RECEIPT.json": MODULE.canonical_json_bytes({
                    "source_head": self.head, "source_tree": self.tree, "unsigned_xpi_sha256": self.package,
                    "signed_original_returned": True, "xpi_sha256": hashlib.sha256(raw).hexdigest(),
                    "xpi_bytes": len(raw)})})
        return value

    def test_exact_protected_main_and_presence_are_required(self):
        self.assertTrue(self.plan()["dispatch"])
        for changes in ({"ref": "refs/heads/feature"}, {"event": "schedule"}, {"run_attempt": 2},
                        {"repository": "Goldkelch/qik-vrt"}, {"workflow_ref": "other"}):
            with self.subTest(changes=changes), self.assertRaises(MODULE.ExecutorBlock):
                self.plan(**changes)
        self.branch["protected"] = False
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "PROTECTION"):
            self.plan()
        self.branch["protected"] = True
        for key in ("issuer_present", "secret_present"):
            self.assertFalse(self.plan(**{key: False})["dispatch"])
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "HISTORY"):
            MODULE.amo_intent(ROOT, self.context, self.authority, self.branch, self.rules, self.subject, None, False)
        self.subject["unsigned_xpi_sha256"] = "0" * 64
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "PACKAGE_CHANGED"):
            self.plan()

    def test_unrelated_commits_do_not_retry_failure_or_fabricate_done(self):
        previous = self.attempt("FAILED")
        for head in (self.head, "c" * 40):
            value = self.plan(previous, head=head)
            self.assertEqual(value["state"], "NOOP_UNCHANGED_SIGNING_FAILURE")
            self.assertFalse(value["dispatch"])
            self.assertFalse(value["effect_ack_done"])
        self.assertTrue(self.plan(previous, binding_revision="new-authorized-binding")["dispatch"])

    def test_ambiguous_ack_and_existing_run_never_start_replacement_upload(self):
        intent = self.plan()
        for response in (None, {}, {"workflow_run_id": 600}, {**self.response(), "run_url": "https://foreign.invalid/"}):
            previous = MODULE.amo_dispatch_record(intent, response)
            self.assertEqual(previous["last_attempt"]["state"], "AMBIGUOUS")
            self.assertFalse(self.plan(previous)["dispatch"])
        body = MODULE.amo_dispatch_body(intent, "f" * 64)
        self.assertTrue(body["return_run_details"])
        self.assertEqual(body["ref"], "main")
        self.assertEqual(body["inputs"]["amo_executor_run_id"], "500")

    def test_provider_abort_admits_only_one_independent_readback(self):
        for state in ("ABORTED", "READBACK_PENDING"):
            value = self.plan(self.attempt(state))
            self.assertTrue(value["dispatch"])
            self.assertTrue(value["readback_only"])
            body = MODULE.amo_dispatch_body(value, "f" * 64)
            self.assertTrue(body["inputs"]["amo_readback_only"])
            repeated = self.plan(self.attempt(state, readback=True))
            self.assertFalse(repeated["dispatch"])
            self.assertEqual(repeated["state"], "NOOP_AWAIT_NEW_PROVIDER_EVIDENCE")

    def test_provider_feedback_preserves_abort_status_without_inventing_cause(self):
        for conclusion in ("cancelled", "timed_out", "failure"):
            value = MODULE.amo_feedback(self.provider_run(600, conclusion=conclusion), [self.job(conclusion=conclusion)])
            self.assertEqual(value["conclusion"], conclusion)
            self.assertEqual(value["jobs"][0]["steps"][0]["conclusion"], conclusion)
            self.assertEqual(value["reason"], "NOT_EXPOSED_BY_GITHUB")

    def test_finished_signing_is_read_even_if_entire_workflow_never_returns(self):
        run = self.provider_run(600, status="in_progress", conclusion=None)
        jobs = {"total_count": 2, "jobs": [self.job(), self.job("in_progress", None, "Full test still running")]}
        def get(root, endpoint, **kwargs):
            if endpoint.endswith("/600"): return run
            if endpoint.endswith("/600/jobs?per_page=100"): return jobs
            self.fail("unexpected wait or GET: " + endpoint)
        with mock.patch.object(MODULE, "_amo_get", side_effect=get), mock.patch.object(MODULE, "amo_artifact", return_value=self.original()):
            value = MODULE.amo_reconcile(ROOT, self.attempt())
        self.assertEqual(value["last_attempt"]["state"], "SIGNED")
        self.assertEqual(value["github_feedback"]["status"], "in_progress")
        self.assertEqual(self.plan(value)["state"], "SIGNING_SOURCE_BOUND")
        self.assertFalse(value["public_production_verified"])

    def test_missing_original_on_cancel_is_readback_only_never_age_based_retry(self):
        for conclusion in ("cancelled", "timed_out"):
            def get(root, endpoint, **kwargs):
                if endpoint.endswith("/600"): return self.provider_run(600, conclusion=conclusion)
                return {"total_count": 1, "jobs": [self.job(conclusion=conclusion)]}
            with mock.patch.object(MODULE, "_amo_get", side_effect=get), mock.patch.object(MODULE, "amo_artifact", return_value=None):
                value = MODULE.amo_reconcile(ROOT, self.attempt())
            self.assertEqual(value["last_attempt"]["state"], "ABORTED")
            self.assertTrue(self.plan(value)["readback_only"])

    def test_altered_signed_bytes_or_foreign_caller_fail_closed(self):
        jobs = {"total_count": 1, "jobs": [self.job()]}
        for original in (self.original(executor=999), {**self.original(), "standard-signed.xpi": b"tampered"}):
            with mock.patch.object(MODULE, "amo_run", return_value=self.provider_run(600)), \
                    mock.patch.object(MODULE, "_amo_get", return_value=jobs), \
                    mock.patch.object(MODULE, "amo_artifact", return_value=original):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.amo_reconcile(ROOT, self.attempt())

    def test_still_running_caller_does_not_block_original_intent_recovery(self):
        intent = self.plan(run_id=499)
        caller = self.provider_run(499, MODULE.AMO_NATIVE_WORKFLOW, "in_progress", None)
        current = self.provider_run(500, MODULE.AMO_NATIVE_WORKFLOW, created_at="2026-10-17T00:00:02Z")
        job = self.job("in_progress", None, MODULE.AMO_JOB)
        job["steps"][0]["name"] = MODULE.AMO_DISPATCH_STEP
        def get(root, endpoint, **kwargs):
            if endpoint.endswith("/500"): return current
            if endpoint.endswith("/499"): return caller
            if "/workflows/" in endpoint: return {"workflow_runs": [current, caller]}
            if endpoint.endswith("/499/jobs?per_page=100"): return {"total_count": 1, "jobs": [job]}
            self.fail(endpoint)
        def artifact(root, run_id, name, allowed):
            return {"intent.json": MODULE.canonical_json_bytes(intent)} if name == "qikvrt-amo-intent-499" else None
        with mock.patch.object(MODULE, "_amo_get", side_effect=get), \
                mock.patch.object(MODULE, "amo_artifact", side_effect=artifact), \
                mock.patch.object(MODULE, "amo_reconcile", side_effect=lambda root, value: value):
            receipt, verified = MODULE.amo_previous(ROOT, 500)
        self.assertTrue(verified)
        self.assertEqual(receipt["last_attempt"]["state"], "AMBIGUOUS")
        self.assertEqual(receipt["last_attempt"]["executor_run_id"], 499)

    def test_completed_event_is_checked_against_original_github_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "event.json"
            original = self.provider_run(600, conclusion="cancelled")
            event = {"action": "completed", "repository": {"full_name": MODULE.AMO_REPOSITORY}, "workflow_run": original}
            path.write_text(json.dumps(event))
            with mock.patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(path)}), mock.patch.object(MODULE, "amo_run", return_value=original):
                self.assertEqual(MODULE.amo_event(ROOT, {**self.context, "event": "workflow_run"})["conclusion"], "cancelled")
                path.write_text(json.dumps({**event, "workflow_run": {**original, "conclusion": "success"}}))
                with self.assertRaisesRegex(MODULE.ExecutorBlock, "EVENT_MISMATCH"):
                    MODULE.amo_event(ROOT, {**self.context, "event": "workflow_run"})

    def test_bot_delegation_returns_without_caller_completion_or_later_ack(self):
        intent = self.plan()
        raw = MODULE.canonical_json_bytes(intent)
        env = {"AMO_EXECUTOR_RUN_ID": "500", "GITHUB_RUN_ID": "600", "GITHUB_ACTOR": "github-actions[bot]",
            "GITHUB_REPOSITORY": MODULE.AMO_REPOSITORY, "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
            "GITHUB_WORKFLOW_REF": f"{MODULE.AMO_REPOSITORY}/{MODULE.AMO_CI_WORKFLOW}@refs/heads/main",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": self.head, "EXPECTED_HEAD": self.head, "EXPECTED_TREE": self.tree,
            "AMO_INTENT_SHA256": hashlib.sha256(raw).hexdigest(), "AMO_READBACK_ONLY": "false"}
        job = self.job("in_progress", None, MODULE.AMO_JOB); job["steps"][0]["name"] = MODULE.AMO_DISPATCH_STEP
        def get(root, endpoint, **kwargs):
            if endpoint.endswith("/heads/main"): return {"object": {"sha": self.head}}
            if endpoint.endswith("/rules/branches/main"): return self.rules
            if endpoint.endswith("/branches/main"): return self.branch
            if endpoint.endswith("/500/jobs?per_page=100"): return {"total_count": 1, "jobs": [job]}
            self.fail("unexpected ACK wait: " + endpoint)
        from tools import qikvrt_self_host as host
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(MODULE, "_amo_get", side_effect=get), \
                mock.patch.object(MODULE, "_git", side_effect=lambda root, *args: self.tree if "HEAD^{tree}" in args else self.head), \
                mock.patch.object(MODULE, "read_authority_main", return_value=self.authority), \
                mock.patch.object(MODULE, "amo_run", return_value=self.provider_run(500, MODULE.AMO_NATIVE_WORKFLOW, "in_progress", None)), \
                mock.patch.object(MODULE, "amo_artifact", return_value={"intent.json": raw}) as artifact, \
                mock.patch.object(host, "firefox_amo_input", return_value=(b"", self.subject)):
            MODULE.amo_validate_delegation(ROOT)
            self.assertEqual(artifact.call_count, 1)

    def test_original_artifact_digest_and_closed_inventory_are_enforced(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive: archive.writestr("intent.json", b"{}")
        raw = stream.getvalue()
        metadata = {"total_count": 1, "artifacts": [{"id": 800, "name": "expected", "expired": False,
            "workflow_run": {"id": 500}, "size_in_bytes": len(raw), "digest": "sha256:" + hashlib.sha256(raw).hexdigest()}]}
        with mock.patch.object(MODULE, "_amo_get", side_effect=[metadata, raw]):
            self.assertEqual(MODULE.amo_artifact(ROOT, 500, "expected", {"intent.json"}), {"intent.json": b"{}"})
        for allowed, data in ((set(), raw), ({"intent.json"}, raw + b"altered")):
            with mock.patch.object(MODULE, "_amo_get", side_effect=[metadata, data]), self.assertRaises(MODULE.ExecutorBlock):
                MODULE.amo_artifact(ROOT, 500, "expected", allowed)

    def test_lost_dispatch_ack_is_recovered_from_original_ci_backlink(self):
        previous = MODULE.amo_dispatch_record(self.plan(), None)
        def get(root, endpoint, **kwargs):
            if "/workflows/qikvrt_ci.yml/runs?" in endpoint:
                return {"workflow_runs": [self.provider_run(600, actor={"login": "github-actions[bot]"})]}
            if "/600/jobs?" in endpoint: return {"total_count": 1, "jobs": [self.job()]}
            self.fail(endpoint)
        def run(root, run_id, workflow): return self.provider_run(run_id, workflow)
        with mock.patch.object(MODULE, "_amo_get", side_effect=get), \
                mock.patch.object(MODULE, "amo_run", side_effect=run), \
                mock.patch.object(MODULE, "amo_artifact", return_value=self.original()):
            result = MODULE.amo_reconcile(ROOT, previous)
        self.assertEqual(result["last_attempt"]["target_run_id"], 600)
        self.assertEqual(result["last_attempt"]["state"], "SIGNED")

    def test_out_of_order_event_keeps_newer_obligation_without_dispatch(self):
        context = {**self.context, "event": "workflow_run"}
        previous = self.attempt()
        previous["last_attempt"]["target_run_id"] = 601
        with mock.patch.object(MODULE, "amo_context", return_value=context), \
                mock.patch.object(MODULE, "_git", side_effect=lambda root, *args: self.tree if "HEAD^{tree}" in args else self.head), \
                mock.patch.object(MODULE, "amo_event", return_value=self.provider_run(600)), \
                mock.patch.object(MODULE, "amo_previous", return_value=(previous, True)):
            result = MODULE.amo_live_plan(ROOT)
        self.assertFalse(result["dispatch"])
        self.assertEqual(result["last_attempt"]["target_run_id"], 601)
        self.assertEqual(result["first_boundary"], "AMO_UNRELATED_OR_SUPERSEDED_COMPLETION_EVENT")

    def test_receiver_cannot_wait_behind_caller_or_poll_for_workflow_return(self):
        workflow = EXECUTOR_WORKFLOW.read_text()
        self.assertNotIn("\nconcurrency:", workflow)
        receiver = workflow.split("  github-run-feedback:\n")[1].split("  owner-firefox-signing:\n")[0]
        self.assertNotIn("    needs:", receiver)
        self.assertNotIn("    concurrency:", receiver)
        self.assertIn('types: [completed]', workflow)
        self.assertIn("format('feedback-{0}', github.event.workflow_run.id)", workflow)
        self.assertNotIn("sleep ", workflow)
        self.assertNotIn("seq 1 12", workflow)
        self.assertIn('return_run_details:true', workflow)


if __name__ == "__main__":
    unittest.main()
