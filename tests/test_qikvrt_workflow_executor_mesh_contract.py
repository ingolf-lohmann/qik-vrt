# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import base64
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest
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
    return {
        "schema": "qikvrt_requested_review_and_issue_lifecycle_policy_v1",
        "status": "ACTIVE",
        "mandatory_boundaries": {"github_platform_protections_may_be_bypassed": False},
        "mesh_authority": {
            "authority_repository": "ingolf-lohmann/qik-vrt",
            "repository": {"full_name": "ingolf-lohmann/qik-vrt", "may_submit_native_approve": False},
            "executor": {"may_submit_native_approve": False},
            "former_authority_repository": "Goldkelch/qik-vrt",
            "former_authority_permission_required": False,
            "independent_native_code_owner_review_required": True,
            "github_platform_effects_are_separate": True,
        },
    }


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

    @mock.patch.object(MODULE, "_read_json_file", return_value=active_role_policy())
    def test_plan_is_exact_head_deduplicated_and_writer_serialized(self, _read_policy) -> None:
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
        with mock.patch.object(MODULE, "_read_json_file", return_value={"status": "ACTIVE"}):
            value = MODULE.dispatch_plan(MODULE.snapshot(ROOT), {"workflow_runs": []}, "main")
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["candidates"][0]["first_blocker"], "AUTHORITY_ROLE_BINDING_NOT_ACTIVE")

    def test_dispatch_wrapper_reads_authority_with_the_mandatory_job_token_before_planning(self) -> None:
        step = EXECUTOR_WORKFLOW.read_text().split("      - name: Build exact-head dispatch plan\n", 1)[1].split("\n      - name:", 1)[0]
        self.assertIn("GH_TOKEN: ${{ github.token }}", step)
        self.assertLess(step.index("authority-readback --json"), step.index("args=(plan"))

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



class AuthorityReadbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.calls = []
        self.head = "a" * 40
        self.ref = {
            "ref": "refs/heads/main",
            "url": "https://api.github.com/repos/ingolf-lohmann/qik-vrt/git/refs/heads/main",
            "object": {"type": "commit", "sha": self.head,
                       "url": "https://api.github.com/repos/ingolf-lohmann/qik-vrt/git/commits/" + self.head},
        }
        self.policy = active_role_policy()
        self.environment = mock.patch.dict(MODULE.os.environ, {"GH_TOKEN": "test-job-token"})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def get(self, argv, **kwargs):
        self.calls.append(argv)
        self.assertEqual(argv[:6], ["gh", "api", "--hostname", "github.com", "--method", "GET"])
        self.assertTrue(argv[-1].startswith("repos/ingolf-lohmann/qik-vrt/"))
        if "/contents/" in argv[-1]:
            self.assertTrue(argv[-1].endswith("?ref=" + self.head))
            raw = json.dumps(self.policy).encode()
            value = {"path": MODULE.ROLE_POLICY_PATH, "type": "file", "encoding": "base64",
                     "content": base64.b64encode(raw).decode(),
                     "sha": hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()}
        else:
            value = self.ref
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")

    def test_exact_authority_main_readback_checks_policy_and_reobserves_head(self) -> None:
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            value = MODULE.read_authority_main(ROOT)
        self.assertEqual(value["repository"], "ingolf-lohmann/qik-vrt")
        self.assertEqual(value["main_head"], self.head)
        self.assertEqual(value["state"], "AUTHORITY_MAIN_ROLE_POLICY_REOBSERVED")
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(self.calls[0], self.calls[2])
        self.assertFalse(any(value["completion_claims"].values()))

    def test_ref_and_policy_access_denials_have_no_mirror_or_anonymous_fallback(self) -> None:
        for status in (403, 404):
            for denied_call in (1, 2):
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

    def test_http_200_without_main_role_activation_remains_hold(self) -> None:
        self.policy.pop("mesh_authority")
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "AUTHORITY_ROLE_BINDING_NOT_ACTIVE"):
                MODULE.read_authority_main(ROOT)
        self.assertEqual(len(self.calls), 2)

    def test_missing_job_token_never_attempts_a_get(self) -> None:
        with mock.patch.dict(MODULE.os.environ, {"GH_TOKEN": ""}), mock.patch.object(MODULE.subprocess, "run") as api:
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "JOB_TOKEN_REQUIRED"):
                MODULE.read_authority_main(ROOT)
        api.assert_not_called()

    def test_native_review_requirement_cannot_be_downgraded(self) -> None:
        self.policy["mesh_authority"]["independent_native_code_owner_review_required"] = False
        with mock.patch.object(MODULE.subprocess, "run", side_effect=self.get):
            with self.assertRaisesRegex(MODULE.ExecutorBlock, "PROTECTION_BOUNDARY_INVALID"):
                MODULE.read_authority_main(ROOT)

    def test_timeout_and_invalid_response_are_fail_closed(self) -> None:
        for response in (subprocess.TimeoutExpired("gh", 30), subprocess.CompletedProcess([], 0, "not JSON", "")):
            with self.subTest(response=type(response).__name__), mock.patch.object(MODULE.subprocess, "run", side_effect=response if isinstance(response, Exception) else None, return_value=response):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.read_authority_main(ROOT)

    def test_policy_blob_and_main_head_drift_are_rejected(self) -> None:
        for fault in ("blob", "head", "ref", "mirror_repository"):
            self.calls = []
            def damaged(argv, **kwargs):
                response = self.get(argv, **kwargs)
                value = json.loads(response.stdout)
                if fault == "blob" and "/contents/" in argv[-1]:
                    value["sha"] = "b" * 40
                elif fault == "head" and len(self.calls) == 3:
                    value["object"]["sha"] = "b" * 40
                    value["object"]["url"] = value["object"]["url"].replace(self.head, "b" * 40)
                elif fault == "ref" and "/contents/" not in argv[-1]:
                    value["ref"] = "refs/heads/mirror"
                elif fault == "mirror_repository" and "/contents/" not in argv[-1]:
                    value["url"] = value["url"].replace("ingolf-lohmann", "Goldkelch")
                return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
            with self.subTest(fault=fault), mock.patch.object(MODULE.subprocess, "run", side_effect=damaged):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.read_authority_main(ROOT)



if __name__ == "__main__":
    unittest.main()
