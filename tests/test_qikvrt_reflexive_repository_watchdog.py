# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
NODE_POLICY = ROOT / "registry/NODE_DISCOVERY_POLICY.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_reflexive_repository_watchdog.yml"

SPEC = importlib.util.spec_from_file_location(
    "qikvrt_reflexive_repository_watchdog",
    ROOT / "tools/qikvrt_reflexive_repository_watchdog.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

HEAD = "a" * 40
TREE = "b" * 40
WRITER_A = "QIK-VRT autonomous bounded self-heal"
WRITER_B = "QIK-VRT autonomous draft-PR continuation"


def run(
    run_id: int,
    name: str,
    status: str,
    created_at: str,
    updated_at: str,
    conclusion: str | None = None,
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "event": "workflow_dispatch",
        "head_sha": HEAD,
        "run_attempt": 1,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def jobs(*run_ids: int) -> dict[str, object]:
    return {
        "jobs_by_run": {
            str(run_id): [
                {
                    "id": run_id * 10,
                    "name": "job",
                    "status": "in_progress",
                    "conclusion": None,
                }
            ]
            for run_id in run_ids
        }
    }


class ReflexiveRepositoryWatchdogTests(unittest.TestCase):
    def test_restored_observer_uses_current_roles_and_rejects_historical_authority(self):
        import copy
        contract = MODULE.load_contract()
        self.assertEqual(MODULE.authority_repository_binding(contract), 'ingolf-lohmann/qik-vrt')
        old = copy.deepcopy(contract)
        old['authority']['repository'] = 'Goldkelch/qik-vrt'
        with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
            MODULE.authority_repository_binding(old)
        unavailable = {'schema': 'qikvrt_authority_readback_v1', 'repository': 'ingolf-lohmann/qik-vrt',
            'endpoint': 'repos/ingolf-lohmann/qik-vrt/git/ref/heads/main', 'method': 'GET',
            'state': 'AUTHORITY_UNAVAILABLE', 'http_status': 403, 'exit_code': 1, 'head_sha': None,
            'disposition': 'HOLD', 'cause': 'UNESTABLISHED',
            'capability_blocker': 'AUTHORITY_MAIN_READ_CAPABILITY_UNAVAILABLE',
            'authority_destroyed': False, 'takeover_allowed': False,
            'writer_admission_allowed': False, 'effect_ack_done': False}
        self.assertEqual(MODULE.validate_authority_observation(unavailable, contract)['state'], 'AUTHORITY_UNAVAILABLE')
        unavailable['takeover_allowed'] = True
        with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
            MODULE.validate_authority_observation(unavailable, contract)


    def setUp(self) -> None:
        self.fixture_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture_directory.cleanup)
        self.default_liveness_dir = pathlib.Path(self.fixture_directory.name) / "liveness"
        self.write_liveness(self.default_liveness_dir)

    def analyze(
        self,
        runs: list[dict[str, object]],
        job_value: dict[str, object],
        *,
        now: str = "2026-08-10T18:00:00Z",
        baseline: dict[str, object] | None = None,
        scope: str = "MAIN",
        liveness_dir: pathlib.Path | None = None,
        authority_head: str | None = HEAD,
    ) -> dict[str, object]:
        return MODULE.analyze(
            {"workflow_runs": runs},
            job_value,
            expected_head=HEAD,
            expected_tree=TREE,
            repository="example/qik-vrt",
            now=datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone(timezone.utc),
            baseline=baseline,
            root=ROOT,
            observation_scope=scope,
            node_liveness_dir=(
                liveness_dir if liveness_dir is not None else self.default_liveness_dir
            ),
            authority_head=authority_head,
        )

    @staticmethod
    def write_liveness(
        directory: pathlib.Path,
        *,
        acceptance_head: str = HEAD,
        renewal_due: str = "2026-08-11T18:00:00Z",
        health_expiry: str = "2026-08-11T18:00:00Z",
    ) -> None:
        directory.mkdir(parents=True)
        records = {
            "SEED_ACCEPTANCE_STATUS.json": {
                "observed_authority_commit": acceptance_head,
                "seed_repository": "ingolf-lohmann/qik-vrt",
            },
            "NODE_REGISTRATION_RENEWAL.json": {"next_renewal_due_utc": renewal_due},
            "NODE_HEALTH.json": {"expires_utc": health_expiry},
        }
        for name, value in records.items():
            (directory / name).write_text(json.dumps(value), encoding="utf-8")

    def test_contract_binds_every_repository_instance_and_preemptive_admission(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        prevention = contract["reflexive_deadlock_prevention"]
        self.assertTrue(prevention["enabled"])
        self.assertEqual(
            prevention["applies_to"],
            ["AUTHORITY", "MIRROR", "EVERY_FUTURE_MESH_NODE"],
        )
        self.assertEqual(prevention["observation_cadence"], "PT5M")
        self.assertEqual(
            prevention["admission_policy"],
            "PREEMPTIVE_HOLD_BEFORE_SECOND_WRITER",
        )
        gatewatch = prevention["gatewatch"]
        self.assertTrue(gatewatch["enabled"])
        self.assertEqual(gatewatch["observation_freshness_seconds"], 900)
        self.assertEqual(
            gatewatch["required_workflow_names_by_scope"]["PULL_REQUEST_MAIN"],
            ["QIKVRT CI", "QIKVRT repository evidence materialization"],
        )
        self.assertEqual(
            gatewatch["required_workflow_names_by_scope"]["PULL_REQUEST_STACKED"],
            ["QIKVRT CI"],
        )
        self.assertTrue(gatewatch["node_liveness"]["artifact_only_materialization"])
        self.assertEqual(
            prevention["observer_run_policy"],
            "CANCEL_SUPERSEDED_OBSERVER_ONLY",
        )
        node_policy = json.loads(NODE_POLICY.read_text(encoding="utf-8"))
        node_acceptance = node_policy["reflexive_watchdog_acceptance"]
        self.assertTrue(node_acceptance["required_for_authority_mirror_and_future_nodes"])
        self.assertEqual(node_acceptance["maximum_observation_interval"], "PT5M")
        self.assertEqual(node_acceptance["gatewatch_receipt_path"], "gatewatch-receipt.json")
        self.assertEqual(node_acceptance["trusted_gate_matrix"], "EXACT_HEAD_ARTIFACT_ONLY")

    def test_recent_single_writer_is_observed_without_overclaim(self) -> None:
        value = self.analyze(
            [run(1, WRITER_A, "in_progress", "2026-08-10T17:57:00Z", "2026-08-10T17:59:00Z")],
            jobs(1),
        )
        self.assertEqual(value["state"], "SAFE_PROGRESS")
        self.assertEqual(value["disposition"], "OBSERVE")
        self.assertFalse(value["completion_claims"]["DEADLOCK_FREEDOM_PROVED"])

    def test_second_active_writer_is_held_before_a_cycle_exists(self) -> None:
        value = self.analyze(
            [
                run(1, WRITER_A, "in_progress", "2026-08-10T17:58:00Z", "2026-08-10T17:59:00Z"),
                run(2, WRITER_B, "queued", "2026-08-10T17:59:00Z", "2026-08-10T17:59:00Z"),
            ],
            jobs(1, 2),
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_COMPETING_WRITERS")
        self.assertEqual(value["first_blocker"], "MORE_THAN_ONE_ACTIVE_REPOSITORY_WRITER")
        self.assertFalse(value["resource_graph"]["cycle_detected"])
        self.assertTrue(value["resource_graph"]["pre_cycle_conflict_detected"])

    def test_stale_writer_lease_is_blocked_before_a_replacement_writer(self) -> None:
        value = self.analyze(
            [run(3, WRITER_A, "in_progress", "2026-08-10T17:20:00Z", "2026-08-10T17:30:00Z")],
            jobs(3),
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_STALE_WRITER_LEASE")
        self.assertEqual(value["productive_edge"], "REOBSERVE_STALE_WRITER_JOBS_STEPS_AND_RECEIPT")

    def test_unchanged_active_topology_crosses_the_progress_lease(self) -> None:
        runs = [run(4, "QIKVRT CI", "in_progress", "2026-08-10T17:43:00Z", "2026-08-10T17:44:00Z")]
        first = self.analyze(runs, jobs(4), now="2026-08-10T17:44:00Z")
        baseline = {
            "head_sha": HEAD,
            "tree_sha": TREE,
            "observed_at": "2026-08-10T17:44:00Z",
            "progress_fingerprint": first["progress_fingerprint"],
        }
        value = self.analyze(runs, jobs(4), now="2026-08-10T18:00:00Z", baseline=baseline)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION")
        self.assertEqual(
            value["first_blocker"],
            "ACTIVE_TOPOLOGY_UNCHANGED_BEYOND_PROGRESS_LEASE",
        )

    def test_post_pr326_cancelled_observer_burst_requires_a_fresh_successor_receipt(self) -> None:
        observer = "QIKVRT reflexive repository watchdog"
        runs = [
            run(701, observer, "completed", "2026-08-11T13:39:35Z", "2026-08-11T13:39:38Z", "cancelled"),
            run(702, observer, "completed", "2026-08-11T13:39:38Z", "2026-08-11T13:39:55Z", "cancelled"),
            run(703, observer, "completed", "2026-08-11T13:39:55Z", "2026-08-11T13:40:39Z", "success"),
        ]
        job_value = {
            "jobs_by_run": {
                "701": [],
                "702": [],
                "703": [
                    {
                        "id": 7030,
                        "name": "exact-head-watchdog",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            }
        }
        fingerprint = MODULE.sha256_bytes(MODULE.canonical_json_bytes([]))
        coalesced = self.analyze(
            runs,
            job_value,
            now="2026-08-11T13:40:39Z",
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-11T13:39:55Z",
                "progress_fingerprint": fingerprint,
            },
        )
        self.assertEqual(coalesced["state"], "QUIESCENT_OBSERVATION")
        self.assertEqual(coalesced["disposition"], "OBSERVE")
        self.assertIsNone(coalesced["first_blocker"])
        self.assertEqual(coalesced["observations"]["active_productive_runs"], [])
        self.assertEqual(coalesced["observations"]["waiting_productive_runs"], [])
        self.assertEqual(coalesced["observations"]["untrusted_terminal_runs"], [])

        starved = self.analyze(
            runs,
            job_value,
            now="2026-08-11T13:40:39Z",
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-11T13:25:00Z",
                "progress_fingerprint": fingerprint,
            },
        )
        self.assertEqual(starved["state"], "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH")
        self.assertEqual(
            starved["first_blocker"],
            "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND",
        )

    def test_action_required_and_zero_job_terminal_runs_are_untrusted(self) -> None:
        value = self.analyze(
            [
                run(
                    5,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "action_required",
                )
            ],
            {"jobs_by_run": {"5": []}},
        )
        self.assertEqual(value["state"], "UNTRUSTED_EXECUTION_GAP")
        self.assertFalse(value["boundaries"]["action_required_is_trusted_execution"])
        self.assertFalse(value["boundaries"]["zero_job_is_trusted_execution"])

    def test_terminal_exact_head_gate_failure_is_held_with_job_evidence(self) -> None:
        value = self.analyze(
            [
                run(
                    6,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "failure",
                )
            ],
            {
                "jobs_by_run": {
                    "6": [
                        {
                            "id": 60,
                            "name": "failing job",
                            "status": "completed",
                            "conclusion": "failure",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_MAIN",
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_EXECUTED_GATE_FAILURE")
        self.assertEqual(value["first_blocker"], "TRUSTED_GATE_EXECUTED_FAILURE")
        gates = {gate["name"]: gate for gate in value["gatewatch"]["gates"]}
        self.assertEqual(gates["QIKVRT CI"]["state"], "FAILED")

    def test_missing_required_pull_request_gate_is_held_without_overclaiming_success(self) -> None:
        value = self.analyze(
            [
                run(
                    7,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "success",
                )
            ],
            {
                "jobs_by_run": {
                    "7": [
                        {
                            "id": 70,
                            "name": "verified job",
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_MAIN",
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_REQUIRED_GATE_EVIDENCE")
        self.assertEqual(
            value["first_blocker"],
            "REQUIRED_TRUSTED_GATE_EVIDENCE_MISSING_OR_UNTRUSTED",
        )

    def test_stacked_pull_request_requires_only_gates_its_base_can_trigger(self) -> None:
        value = self.analyze(
            [
                run(
                    71,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "success",
                )
            ],
            {
                "jobs_by_run": {
                    "71": [
                        {
                            "id": 710,
                            "name": "verified job",
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_STACKED",
        )
        gates = {gate["name"]: gate for gate in value["gatewatch"]["gates"]}
        self.assertEqual(value["gatewatch"]["required_workflow_names"], ["QIKVRT CI"])
        self.assertEqual(gates["QIKVRT CI"]["state"], "SUCCESS")
        self.assertEqual(gates["QIKVRT repository evidence materialization"]["state"], "NOT_OBSERVED")
        self.assertFalse(value["gatewatch"]["required_evidence_gaps"])

    def test_overdue_renewal_is_a_read_only_liveness_hold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary) / "onboarding"
            self.write_liveness(directory, renewal_due="2026-08-10T17:59:00Z")
            value = self.analyze([], {"jobs_by_run": {}}, liveness_dir=directory)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NODE_LIVENESS")
        self.assertEqual(value["first_blocker"], "NODE_REGISTRATION_RENEWAL_OVERDUE")
        self.assertFalse(value["boundaries"]["liveness_record_observation_mutates_repository"])

    def test_expired_health_and_stale_seed_acceptance_are_reported_from_exact_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary) / "onboarding"
            self.write_liveness(
                directory,
                acceptance_head="c" * 40,
                health_expiry="2026-08-10T17:59:00Z",
            )
            value = self.analyze([], {"jobs_by_run": {}}, liveness_dir=directory)
        liveness = value["gatewatch"]["node_liveness"]
        self.assertEqual(liveness["records"]["seed_acceptance"]["state"], "STALE")
        self.assertEqual(liveness["records"]["health"]["state"], "EXPIRED")
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NODE_LIVENESS")

    def test_absent_node_liveness_records_are_not_misreported_on_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self.analyze(
                [],
                {"jobs_by_run": {}},
                liveness_dir=pathlib.Path(temporary) / "absent-onboarding",
            )
        self.assertEqual(value["gatewatch"]["node_liveness"]["state"], "NOT_APPLICABLE")
        self.assertEqual(value["state"], "QUIESCENT_OBSERVATION")

    def test_mirror_or_missing_repository_is_held_even_with_equal_authority_commit(self) -> None:
        for repository in ("Goldkelch/qik-vrt", None):
            path = self.default_liveness_dir / "SEED_ACCEPTANCE_STATUS.json"
            document = {"observed_authority_commit": HEAD}
            if repository:
                document["seed_repository"] = repository
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.subTest(repository=repository):
                value = self.analyze([], {"jobs_by_run": {}})
                self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NODE_LIVENESS")
                self.assertEqual(value["first_blocker"], "SEED_ACCEPTANCE_AUTHORITY_REPOSITORY_MISMATCH")
                self.assertFalse(any(value["completion_claims"].values()))

    def test_old_same_head_receipt_detects_a_missed_gatewatch_tick(self) -> None:
        value = self.analyze(
            [],
            {"jobs_by_run": {}},
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-10T17:40:00Z",
                "progress_fingerprint": MODULE.sha256_bytes(MODULE.canonical_json_bytes([])),
            },
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH")
        self.assertEqual(
            value["first_blocker"], "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND"
        )

    def test_stale_baseline_from_a_different_head_is_discarded(self) -> None:
        value = self.analyze(
            [],
            {"jobs_by_run": {}},
            baseline={
                "head_sha": "c" * 40,
                "tree_sha": TREE,
                "observed_at": "2026-08-10T17:40:00Z",
                "progress_fingerprint": MODULE.sha256_bytes(MODULE.canonical_json_bytes([])),
            },
        )
        self.assertFalse(value["baseline"]["same_head_and_tree"])
        self.assertEqual(value["state"], "QUIESCENT_OBSERVATION")

    def test_workflow_is_transition_driven_reflexive_and_read_only(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn('  schedule:', workflow)
        self.assertIn("workflow_run:", workflow)
        # Main #610 serializes observations instead of cancelling the active
        # read on each lifecycle notification. Provider completion transitions
        # replace timer activation; liveness checks still run on observation.
        self.assertIn("types: [completed]", workflow)
        self.assertNotIn("types: [requested, in_progress, completed]", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotIn("cancel-in-progress: true", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("qikvrt_reflexive_repository_watchdog.py", workflow)
        self.assertIn("qikvrt-reflexive-repository-watchdog-", workflow)
        self.assertIn("QIKVRT CI", workflow)
        self.assertIn("QIKVRT repository evidence materialization", workflow)
        self.assertIn("observed-authority-main-head.txt", workflow)
        self.assertIn("gatewatch-receipt.json", workflow)
        self.assertIn("job-readback-budget", workflow)
        self.assertIn("collect-runs", workflow)
        self.assertIn("collect-jobs", workflow)
        self.assertIn("select(.id != $current)", workflow)
        self.assertIn("--previous-readback", workflow)
        self.assertIn(".semantic_fingerprint", workflow)
        self.assertNotIn(".workflow_runs[0:20]", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("issues/comments", workflow)


class ReflexiveObservationFailureTests(unittest.TestCase):
    @staticmethod
    def step_body(name: str) -> str:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        section = workflow.split(f"      - name: {name}\n", 1)[1]
        section = section.split("\n      - name:", 1)[0]
        body = section.split("        run: |\n", 1)[1]
        return textwrap.dedent(body).replace(
            "${{ github.event.pull_request.base.ref }}", "main"
        )

    def test_authority_404_preserves_a_failure_receipt_without_hiding_the_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            binary = root / "bin"
            binary.mkdir()
            (root / "tools").mkdir()
            shutil.copyfile(
                ROOT / "tools/qikvrt_reflexive_repository_watchdog.py",
                root / "tools/qikvrt_reflexive_repository_watchdog.py",
            )
            shutil.copyfile(ROOT / "tools/qikvrt_workflow_executor.py", root / "tools/qikvrt_workflow_executor.py")
            contract_path = root / CONTRACT.relative_to(ROOT)
            contract_path.parent.mkdir(parents=True)
            shutil.copyfile(CONTRACT, contract_path)
            policy_path = root / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
            policy_path.parent.mkdir(parents=True)
            shutil.copyfile(ROOT / policy_path.relative_to(root), policy_path)
            for name in ("qikvrt_workflow_executor.yml", "qikvrt_reflexive_repository_watchdog.yml"):
                target = root / ".github/workflows" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / target.relative_to(root), target)
            stubs = {
                "git": f'#!/bin/bash\nif [[ "$*" == *"HEAD^{{tree}}"* ]]; then echo {TREE}; else echo {HEAD}; fi\n',
                # jq consumes its pipeline input even when the selected value is empty.
                # An early-exiting stub races the producer into SIGPIPE under pipefail.
                "jq": '#!/bin/bash\nif [[ "$1" == *"first_blocker"* ]]; then cat "${@: -1}"; else cat >/dev/null; fi\nexit 0\n',
                "gh": f'#!/bin/bash\nif [[ "$2" == "repos/example/qik-vrt/git/ref/heads/main" ]]; then echo {HEAD}; elif [[ "$2" == *"/actions/workflows/"* ]]; then echo \'{{"workflow_runs":[]}}\'; else echo "gh: Not Found (HTTP 404)" >&2; exit 1; fi\n',
            }
            for name, source in stubs.items():
                path = binary / name
                path.write_text(source, encoding="utf-8")
                path.chmod(0o700)
            environment = {
                **os.environ,
                "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                "REPOSITORY": "example/qik-vrt",
                "EVENT_NAME": "workflow_run",
                "EVENT_PR": "",
                "EXPECTED_HEAD": HEAD,
                "CURRENT_RUN_ID": "12345",
                "CURRENT_RUN_ATTEMPT": "2",
                "GH_TOKEN": "test-job-token",
            }
            observed = subprocess.run(
                ["bash", "-c", self.step_body("Reobserve exact head, tree, runs, jobs, and previous reflexive receipt")],
                cwd=root, env=environment, capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(observed.returncode, 0)
            authority_readback = json.loads((root / ".qikvrt/reflexive-repository-watchdog/authority-role-readback.json").read_text())
            self.assertEqual(authority_readback["first_blocker"], "AUTHORITY_READBACK_DENIED HTTP_404")
            self.assertFalse(authority_readback["native_activation_verified"])
            fallback = subprocess.run(
                ["bash", "-c", self.step_body("Preserve failed observation as machine-readable HOLD")],
                cwd=root, env=environment, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(fallback.returncode, 0, fallback.stderr)
            self.assertIn("AUTHORITY_READBACK_DENIED HTTP_404", fallback.stdout)
            receipt_path = root / ".qikvrt/reflexive-repository-watchdog/reflexive-watchdog-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            failure_contract = json.loads(CONTRACT.read_text(encoding="utf-8"))["reflexive_deadlock_prevention"]["observation_failure"]
            self.assertEqual(receipt["schema"], failure_contract["receipt_schema"])
            self.assertEqual(receipt["state"], "OBSERVATION_FAILED")
            self.assertEqual(receipt["disposition"], "HOLD")
            self.assertEqual(receipt["failure"]["stage"], "AUTHORITY_READBACK")
            self.assertEqual(receipt["head_sha"], HEAD)
            self.assertEqual(receipt["tree_sha"], TREE)
            self.assertEqual(receipt["run_id"], 12345)
            self.assertEqual(receipt["run_attempt"], 2)
            self.assertFalse(receipt["live_subject_reobserved"])
            self.assertFalse(receipt["productive_edge"])
            self.assertFalse(any(receipt["completion_claims"].values()))
            self.assertEqual(
                receipt_path.read_bytes(),
                (receipt_path.parent / "gatewatch-receipt.json").read_bytes(),
            )

    def test_failure_receipt_rejects_invalid_identity_and_zero_exit(self) -> None:
        arguments = dict(
            expected_head=HEAD, observed_head=HEAD, observed_tree=TREE,
            repository="example/qik-vrt", now=datetime.now(timezone.utc),
            run_id=12345, run_attempt=1, stage="AUTHORITY_READBACK", exit_code=1,
        )
        for replacement in ({"expected_head": "unknown"}, {"exit_code": 0}):
            with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
                MODULE.observation_failure_receipt(**{**arguments, **replacement})

    def test_drifted_checkout_is_recorded_as_failure_not_exact_binding(self) -> None:
        receipt = MODULE.observation_failure_receipt(
            expected_head=HEAD, observed_head="c" * 40, observed_tree=TREE,
            repository="example/qik-vrt", now=datetime.now(timezone.utc),
            run_id=12345, run_attempt=1, stage="CHECKOUT_BINDING", exit_code=1,
        )
        self.assertFalse(receipt["expected_head_matches_checkout"])
        self.assertFalse(receipt["completion_claims"]["EFFECT_ACK_DONE"])


class JobReadbackBudgetTests(unittest.TestCase):
    @staticmethod
    def page(count: int, *, total: int | None = None) -> dict:
        return {"total_count": count if total is None else total,
                "workflow_runs": [run(i + 1, f"workflow-{i + 1}", "completed",
                                      "2026-08-10T17:00:00Z", "2026-08-10T17:01:00Z",
                                      "success") for i in range(count)]}

    @classmethod
    def history(cls, count=213):
        value = cls.page(count)
        for entry in value["workflow_runs"]:
            entry["name"] = f"workflow-{entry['id'] % 3}"
        return value

    def test_incomplete_over_budget_and_invalid_pages_never_admit_job_reads(self):
        cases = [
            (self.page(21), "JOB_READBACK_REQUEST_BUDGET_EXCEEDED"),
            (self.page(100, total=101), "RUN_INVENTORY_INCOMPLETE"),
            (self.page(3, total=4), "RUN_INVENTORY_INCOMPLETE"),
            ({**self.page(1), "truncated": True}, "RUN_INVENTORY_INCOMPLETE"),
            ({**self.page(1), "total_count": True}, "RUN_INVENTORY_INVALID"),
            ({"workflow_runs": []}, "RUN_INVENTORY_INVALID"),
            ({"total_count": 1, "workflow_runs": [{"id": True, "head_sha": HEAD}]},
             "RUN_INVENTORY_INVALID"),
            ({"total_count": 1, "workflow_runs": [{"id": 1, "head_sha": TREE}]},
             "RUN_INVENTORY_INVALID"),
            ({"total_count": 2, "workflow_runs": [{"id": 1, "head_sha": HEAD}] * 2},
             "RUN_INVENTORY_INVALID"),
        ]
        for page, blocker in cases:
            with self.subTest(blocker=blocker, page=page):
                result = MODULE.job_readback_budget(page, expected_head=HEAD)
                self.assertEqual(result["state"], "HOLD")
                self.assertEqual(result["first_blocker"], blocker)
                self.assertEqual(result["run_ids"], [])
                self.assertFalse(result["effect_ack_done"])

    def test_complete_pages_include_zero_and_the_exact_budget_boundary(self):
        for count in (0, 1, 20):
            with self.subTest(count=count):
                result = MODULE.job_readback_budget(self.page(count), expected_head=HEAD)
                self.assertEqual(result["state"], "READY")
                self.assertEqual(result["run_ids"], list(range(1, count + 1)))

    def collect(self, page: dict, *, deny: str = "", checker_missing: bool = False,
                full_observation: bool = False, run_pages=None, job_counts=None,
                job_override=None) -> tuple:
        """Run the real workflow collection body against an isolated REST fixture."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = pathlib.Path(temporary.name)
        (root / "bin").mkdir()
        (root / "tools").mkdir()
        observation = root / (".qikvrt/reflexive-repository-watchdog"
                              if full_observation else "observation")
        (observation / "jobs").mkdir(parents=True)
        (root / "runs.json").write_text(json.dumps(page), encoding="utf-8")
        (root / "pages.json").write_text(json.dumps(run_pages), encoding="utf-8")
        (root / "job-counts.json").write_text(json.dumps(job_counts or {}), encoding="utf-8")
        (root / "job-override.json").write_text(json.dumps(job_override or {}), encoding="utf-8")
        shutil.copyfile(ROOT / "tools/qikvrt_reflexive_repository_watchdog.py",
                        root / "tools/qikvrt_reflexive_repository_watchdog.py")
        if checker_missing:
            (root / "tools/qikvrt_reflexive_repository_watchdog.py").unlink()
        stub = root / "bin/gh"
        stub.write_text(textwrap.dedent(f"""\
            #!{sys.executable}
            import json, os, pathlib, sys, urllib.parse
            root = pathlib.Path(os.environ['FIXTURE_ROOT'])
            path = sys.argv[2]
            if '/git/ref/' in path:
                kind = 'subject'
            elif '/workflows/' in path:
                kind = 'baseline-runs'
            elif '/runs/900/artifacts?' in path:
                kind = 'baseline-artifacts'
            elif '/artifacts/901/zip' in path:
                kind = 'baseline-zip'
            else:
                kind = 'jobs' if '/jobs?' in path else 'runs'
            with (root / 'requests.jsonl').open('a') as log:
                log.write(json.dumps({{'kind': kind, 'path': path}}) + '\\n')
            if os.environ['DENY'] == kind:
                print('gh: API rate limit exceeded (HTTP 403)', file=sys.stderr)
                raise SystemExit(1)
            responses = {{'subject': '{HEAD}',
                         'baseline-runs': '{{"workflow_runs":[{{"id":900}}]}}',
                         'baseline-artifacts': '{{"artifacts":[{{"id":901,"name":"qikvrt-reflexive-repository-watchdog-previous"}}]}}',
                         }}
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
            page_number = int(query.get('page', ['1'])[0])
            start = (page_number - 1) * 100
            if kind == 'runs':
                pages = json.loads((root / 'pages.json').read_text())
                value = json.loads((root / 'runs.json').read_text())
                value['workflow_runs'] = value['workflow_runs'][start:start + 100]
                print(json.dumps(pages[page_number - 1] if pages is not None else value))
            elif kind == 'jobs':
                run_id = int(path.split('/runs/')[1].split('/')[0])
                count = json.loads((root / 'job-counts.json').read_text()).get(str(run_id), 0)
                override = json.loads((root / 'job-override.json').read_text())
                entries = [{{'id': run_id * 1000 + i + 1, 'run_id': run_id,
                            'head_sha': '{HEAD}', 'run_attempt': 1, 'name': 'job', 'status': 'completed',
                            'conclusion': 'success', **override}} for i in range(count)]
                print(json.dumps({{'total_count': count, 'jobs': entries[start:start + 100]}}))
            else:
                print(responses[kind])
            """), encoding="utf-8")
        stub.chmod(0o700)
        body = ReflexiveObservationFailureTests.step_body(
            "Reobserve exact head, tree, runs, jobs, and previous reflexive receipt")
        if full_observation:
            git_stub = root / "bin/git"
            git_stub.write_text(f"#!{sys.executable}\nimport sys\n"
                                f"print('{TREE}' if 'tree' in sys.argv[-1] else '{HEAD}')\n",
                                encoding="utf-8")
            git_stub.chmod(0o700)
            (root / "tools/qikvrt_workflow_executor.py").write_text(
                f"import json; print(json.dumps({{'main_head': '{HEAD}'}}))\n",
                encoding="utf-8")
        else:
            body = body[body.index("observation_stage=RUNS_READBACK"):]
        environment = {**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
                       "root": str(observation), "FIXTURE_ROOT": str(root), "DENY": deny,
                       "EXPECTED_HEAD": HEAD, "REPOSITORY": "example/qik-vrt",
                       "EVENT_NAME": "push", "EVENT_PR": "", "CURRENT_RUN_ID": "10"}
        result = subprocess.run(["bash", "-c", "set -euo pipefail\n" + body], cwd=root,
                                env=environment, capture_output=True, text=True, timeout=15)
        log = root / "requests.jsonl"
        requests = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        plan_path = observation / "job-readback-budget.json"
        plan_bytes = plan_path.read_text() if plan_path.exists() else ""
        plan = json.loads(plan_bytes) if plan_bytes.strip() else None
        return result, requests, plan

    def test_real_workflow_sends_zero_job_gets_for_21_runs_or_incomplete_100_run_page(self):
        for page in (self.page(21), self.page(100, total=101), self.page(3, total=4)):
            with self.subTest(total=page["total_count"]):
                result, requests, plan = self.collect(page)
                self.assertNotEqual(result.returncode, 0, result.stderr)
                self.assertTrue(all(r["kind"] == "runs" for r in requests))
                self.assertEqual(plan["state"], "HOLD")

    def test_real_workflow_reads_every_job_for_a_complete_admitted_page(self):
        for count in (0, 3, 20):
            with self.subTest(count=count):
                result, requests, plan = self.collect(self.page(count))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), count)
                self.assertEqual(plan["state"], "READY")

    def test_http_403_stops_collection_without_an_automatic_retry(self):
        for denied, expected_job_gets in (("runs", 0), ("jobs", 1)):
            with self.subTest(denied=denied):
                result, requests, _ = self.collect(self.page(3), deny=denied)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("HTTP 403", result.stderr)
                self.assertEqual(len([r for r in requests if r["kind"] == "runs"]), 1)
                self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), expected_job_gets)

    def test_prior_artifact_http_403_stops_before_runs_and_jobs(self):
        result, requests, plan = self.collect(
            self.page(3), deny="baseline-zip", full_observation=True)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn("HTTP 403", result.stderr)
        self.assertEqual([r["kind"] for r in requests],
                         ["subject", "baseline-runs", "baseline-artifacts", "baseline-zip"])
        self.assertIsNone(plan)

    def test_unavailable_budget_checker_cannot_start_job_reads(self):
        result, requests, plan = self.collect(self.page(3), checker_missing=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("can't open file", result.stderr)
        self.assertEqual(requests, [])
        self.assertIsNone(plan)

    def test_paginated_history_reaches_job_analysis_without_sampling_topology(self):
        page = self.history()
        page["workflow_runs"][0]["status"] = "in_progress"
        result, requests, plan = self.collect(page)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([r for r in requests if r["kind"] == "runs"]), 3)
        self.assertEqual(plan["reported_run_count"], 213)
        self.assertEqual(plan["returned_run_count"], 213)
        self.assertEqual(plan["selection_scope"], "ALL_ACTIVE_AND_LATEST_PER_WORKFLOW_NAME")
        self.assertIn(1, plan["run_ids"])
        self.assertEqual(plan["run_ids"], [1, 211, 212, 213])
        self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), 4)
        self.assertEqual(len(plan["excluded_historical_run_ids"]), 209)

    def test_analysis_retains_all_runs_and_rejects_missing_selected_readback(self):
        page = self.history()
        plan = MODULE.job_readback_budget(page, expected_head=HEAD)
        arguments = dict(expected_head=HEAD, expected_tree=TREE, repository="example/qik-vrt",
                         now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc))
        observed = {str(run_id): [] for run_id in plan["run_ids"]}
        receipt = MODULE.analyze(page, observed, **arguments)
        self.assertEqual(receipt["observations"]["exact_head_run_count"], 213)
        self.assertEqual(len(receipt["observations"]["runs"]), 213)
        self.assertEqual(sum(r["job_readback_observed"]
                             for r in receipt["observations"]["runs"]), 3)
        self.assertFalse(receipt["effect_ack_done"])
        with self.assertRaisesRegex(MODULE.ReflexiveWatchdogBlock, "SELECTED_JOB_READBACK_MISSING"):
            MODULE.analyze(page, {}, **arguments)
        with self.assertRaisesRegex(MODULE.ReflexiveWatchdogBlock, "RUN_INVENTORY_INCOMPLETE"):
            MODULE.analyze({**page, "total_count": 214}, observed, **arguments)

    def test_all_active_runs_and_latest_names_must_fit_before_first_job_request(self):
        page = self.history(21)
        for entry in page["workflow_runs"]:
            entry["status"] = "queued"
        result, requests, plan = self.collect(page)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(plan["first_blocker"], "JOB_READBACK_REQUEST_BUDGET_EXCEEDED")
        self.assertFalse(any(r["kind"] == "jobs" for r in requests))

    def test_changed_duplicate_wrong_head_and_short_pages_hold_without_job_reads(self):
        page = self.history()
        first = {**page, "workflow_runs": page["workflow_runs"][:100]}
        second = {**page, "workflow_runs": page["workflow_runs"][100:200]}
        cases = [
            [first, {**second, "total_count": 214}],
            [first, {**second, "workflow_runs": first["workflow_runs"]}],
            [first, {**second, "workflow_runs": [{**r, "head_sha": TREE}
                                                 for r in second["workflow_runs"]]}],
            [first, {**second, "workflow_runs": []}],
        ]
        for pages in cases:
            with self.subTest(pages=pages):
                result, requests, plan = self.collect(page, run_pages=pages)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(plan["first_blocker"], "RUN_INVENTORY_INCOMPLETE")
                self.assertFalse(any(r["kind"] == "jobs" for r in requests))

    def test_run_page_budget_is_bounded_and_not_reported_as_complete(self):
        result, requests, plan = self.collect(self.history(1001))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len(requests), MODULE.MAX_RUN_READBACK_PAGES)
        self.assertEqual(plan["returned_run_count"], 1000)
        self.assertEqual(plan["first_blocker"], "RUN_INVENTORY_INCOMPLETE")

    def test_job_pagination_counts_each_http_request_against_the_shared_budget(self):
        result, requests, plan = self.collect(self.page(2), job_counts={"1": 101})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), 3)
        result, requests, plan = self.collect(self.page(20), job_counts={"1": 101})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), 20)
        self.assertEqual(plan["state"], "READY")  # Actual pagination budget failed later.

    def test_job_wrong_head_or_run_identity_stops_without_another_get(self):
        for override in ({"head_sha": TREE}, {"run_id": 999}, {"run_attempt": 2}):
            result, requests, _ = self.collect(self.page(3), job_counts={"1": 1},
                                                job_override=override)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(len([r for r in requests if r["kind"] == "jobs"]), 1)

    def test_completed_success_with_active_job_evidence_is_untrusted(self):
        entry = run(1, "QIKVRT CI", "completed", "2026-08-10T17:00:00Z",
                    "2026-08-10T17:01:00Z", "success")
        result = MODULE._gate_state_for_run(entry, {"1": [
            {"status": "completed", "conclusion": "success"},
            {"status": "queued", "conclusion": None},
        ]}, required=True)
        self.assertEqual(result["state"], "UNTRUSTED")


if __name__ == "__main__":
    unittest.main()
