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
import zipfile
from unittest import mock
from datetime import datetime, timedelta, timezone


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
        work_value: dict[str, object] | None = None,
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
            work_value=work_value if work_value is not None else self.work_inventory(now=now),
        )

    @staticmethod
    def work_inventory(*numbers: int, now: str = "2026-08-10T18:00:00Z") -> dict[str, object]:
        return {"schema": "qikvrt_open_work_inventory_v1", "repository": "example/qik-vrt",
                "head_sha": HEAD, "observed_at": now, "complete": True, "truncated": False,
                "total_count": len(numbers),
                "items": [{"id": number, "number": number, "kind": "ISSUE"} for number in numbers]}

    def test_open_work_without_a_runner_requires_continuation_instead_of_quiescence(self):
        value = self.analyze([], {}, work_value=self.work_inventory(682))
        self.assertEqual(value["state"], "CONTINUATION_REQUIRED_OPEN_WORK")
        self.assertFalse(value["continuation_obligation"]["silent_idle_allowed"])
        self.assertTrue(value["continuation_obligation"]["required"])
        self.assertFalse(value["continuation_obligation"]["effect_permission"])
        handoff = MODULE.repair_handoff(MODULE.canonical_json_bytes(value),
                    run_id=21, run_attempt=1, producer_event="issues")
        self.assertEqual(handoff["state"], "REPAIR_INPUT_REQUIRED")
        feedback = MODULE.repair_handoff(MODULE.canonical_json_bytes(value),
                    run_id=22, run_attempt=1, producer_event="workflow_run",
                    parent_workflow="QIK-VRT autonomous draft-PR continuation")
        self.assertEqual(feedback["state"], "NOOP")

    def test_unreadable_queue_cannot_be_called_empty(self):
        value = MODULE.analyze({"workflow_runs": []}, {}, expected_head=HEAD,
            expected_tree=TREE, repository="example/qik-vrt", now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
            node_liveness_dir=self.default_liveness_dir, authority_head=HEAD)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_WORK_INVENTORY")
        self.assertEqual(value["open_work"]["state"], "UNKNOWN")
        self.assertFalse(value["continuation_obligation"]["silent_idle_allowed"])

    def test_open_work_never_allows_silent_idle_across_supported_run_states(self):
        cases = [(None, None), ("queued", None), ("in_progress", None),
                 ("completed", "success"), ("completed", "failure"),
                 ("completed", "cancelled"), ("completed", "timed_out"),
                 ("completed", "action_required")]
        checked = 0
        for count in (1, 2, 169):
            work = self.work_inventory(*range(1, count + 1))
            for status, conclusion in cases:
                with self.subTest(work_items=count, status=status, conclusion=conclusion):
                    runs = [] if status is None else [run(91, "QIKVRT CI", status,
                        "2026-08-10T17:59:00Z", "2026-08-10T18:00:00Z", conclusion)]
                    evidence = {} if status is None else {"jobs_by_run": {"91": [{
                        "id": 910, "name": "tests", "status": status, "conclusion": conclusion}]}}
                    value = self.analyze(runs, evidence, work_value=work)
                    self.assertNotEqual(value["state"], "QUIESCENT_OBSERVATION")
                    self.assertFalse(value["continuation_obligation"]["silent_idle_allowed"])
                    self.assertTrue(value["continuation_obligation"]["required"])
                    self.assertFalse(value["continuation_obligation"]["effect_permission"])
                    checked += 1
        self.assertEqual(checked, 24)

    def test_native_container_acceptance_invokes_frozen_package_guard_tests(self):
        source = (ROOT / "Makefile").read_text()
        recipe = source.split("self-host-container-test: tool-cache-contract\n", 1)[1].split("\n\n", 1)[0]
        invoked = [token for line in recipe.splitlines()
                   if line.startswith("\t") and "-m unittest" in line
                   for token in line.split("-m unittest", 1)[1].split()]
        self.assertIn("tests.test_self_host_container", invoked)
        self.assertIn("tests.test_frozen_build_apt", invoked)
        self.assertNotIn("|| true", recipe)

    def test_incomplete_wrong_subject_stale_and_future_work_inventory(self):
        incomplete = self.work_inventory()
        incomplete["complete"] = False
        self.assertEqual(self.analyze([], {}, work_value=incomplete)["open_work"]["state"], "UNKNOWN")
        for key, changed in (("repository", "other/repo"), ("head_sha", "c" * 40),
                             ("observed_at", "2026-08-10T17:00:00Z"),
                             ("observed_at", "2026-08-10T18:01:00Z")):
            value = self.work_inventory()
            value[key] = changed
            with self.subTest(key=key, value=changed), self.assertRaises(MODULE.ReflexiveWatchdogBlock):
                self.analyze([], {}, work_value=value)

    def test_frequent_observations_do_not_reset_the_useful_progress_lease(self):
        runs = [run(31, "QIKVRT CI", "in_progress", "2026-08-10T17:43:00Z", "2026-08-10T17:44:00Z")]
        value = None
        for minute in (44, 49, 54, 59):
            value = self.analyze(runs, jobs(31), now=f"2026-08-10T17:{minute}:00Z", baseline=value)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION")
        self.assertEqual(value["last_progress_at"], "2026-08-10T17:44:00Z")
        self.assertEqual(value["unchanged_for_seconds"], 900)
        self.assertEqual(value["baseline"]["age_seconds"], 300)

    def test_heartbeat_and_identical_retry_are_not_useful_progress(self):
        now = "2026-08-10T17:44:00Z"
        runs = [run(32, "QIKVRT CI", "completed", now, now, "failure")]
        evidence = {"jobs_by_run": {"32": [{"name": "tests", "status": "completed", "conclusion": "failure"}]}}
        first = self.analyze(runs, evidence, now=now, work_value=self.work_inventory(682, now=now))
        retry = [run(33, "QIKVRT CI", "completed", "2026-08-10T17:59:00Z", "2026-08-10T17:59:00Z", "failure")]
        evidence["jobs_by_run"]["33"] = evidence["jobs_by_run"]["32"]
        value = self.analyze(retry, evidence, baseline=first, work_value=self.work_inventory(682))
        self.assertEqual(value["progress_fingerprint"], first["progress_fingerprint"])
        self.assertEqual(value["first_blocker"], "OPEN_WORK_WITHOUT_USEFUL_PROGRESS")
        self.assertEqual(value["unchanged_for_seconds"], 960)

    def test_new_executed_step_advances_the_progress_clock(self):
        runs = [run(34, "QIKVRT CI", "in_progress", "2026-08-10T17:43:00Z", "2026-08-10T17:44:00Z")]
        evidence = jobs(34)
        first = self.analyze(runs, evidence, now="2026-08-10T17:44:00Z")
        evidence["jobs_by_run"]["34"][0]["steps"] = [
            {"number": 1, "name": "tests", "status": "completed", "conclusion": "success"}]
        value = self.analyze(runs, evidence, baseline=first)
        self.assertNotEqual(value["progress_fingerprint"], first["progress_fingerprint"])
        self.assertEqual(value["last_progress_at"], "2026-08-10T18:00:00Z")
        self.assertEqual(value["unchanged_for_seconds"], 0)

    def test_foreign_baseline_does_not_transfer_a_progress_clock(self):
        first = self.analyze([], {}, now="2026-08-10T17:44:00Z")
        first["repository"] = "foreign/repo"
        value = self.analyze([], {}, baseline=first)
        self.assertFalse(value["baseline"]["same_head_and_tree"])
        self.assertEqual(value["unchanged_for_seconds"], 0)

    def test_future_or_corrupted_progress_baseline_fails_closed(self):
        for field, changed in (("last_progress_at", "2026-08-10T18:01:00Z"),
                               ("observed_at", "2026-08-10T18:01:00Z"),
                               ("progress_markers", ["invalid"])):
            first = self.analyze([], {}, now="2026-08-10T17:44:00Z")
            first[field] = changed
            with self.subTest(field=field), self.assertRaises(MODULE.ReflexiveWatchdogBlock):
                self.analyze([], {}, baseline=first)

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

    def test_selected_jobs_preserve_gate_decisions_and_mark_old_history_unobserved(self):
        runs = [run(i, "QIKVRT CI", "completed", f"2026-08-10T17:{i:02}:00Z",
                    f"2026-08-10T17:{i:02}:01Z", "success") for i in range(1, 31)]
        # Every active run remains an input, including an older same-name writer.
        runs.extend([run(40, WRITER_A, "in_progress", "2026-08-10T17:58:00Z",
                         "2026-08-10T17:59:59Z"),
                     run(41, WRITER_A, "completed", "2026-08-10T17:59:00Z",
                         "2026-08-10T17:59:01Z", "success")])
        inventory = {"total_count": len(runs), "workflow_runs": runs}
        plan = MODULE.job_readback_budget(inventory, expected_head=HEAD, required_jobs_only=True)
        self.assertEqual(set(plan['run_ids']), {30, 40, 41})
        for outcome in ('success', 'failure', 'zero_jobs'):
            with self.subTest(outcome=outcome):
                runs[29]['conclusion'] = 'failure' if outcome == 'failure' else 'success'
                plan = MODULE.job_readback_budget(inventory, expected_head=HEAD, required_jobs_only=True)
                all_jobs = {str(item['id']): [{'id': item['id'] * 10,
                    'head_sha': HEAD, 'run_id': item['id'], 'run_attempt': 1,
                    'status': 'in_progress' if item['id'] == 40 else 'completed',
                    'conclusion': None if item['id'] == 40 else 'success'}] for item in runs}
                if outcome == 'zero_jobs':
                    all_jobs['30'] = []
                full = self.analyze(runs, {'jobs_by_run': all_jobs})
                selected = {str(i): all_jobs[str(i)] for i in plan['run_ids']}
                bounded = MODULE.analyze(inventory, {'jobs_by_run': selected}, expected_head=HEAD,
                    expected_tree=TREE, repository='example/qik-vrt',
                    now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc), root=ROOT,
                    node_liveness_dir=self.default_liveness_dir, authority_head=HEAD, job_plan=plan,
                    work_value=self.work_inventory())
                for key in ('state', 'disposition', 'first_blocker', 'gatewatch', 'resource_graph'):
                    self.assertEqual(bounded[key], full[key], key)
                self.assertEqual(bounded['observations']['active_writers'], ['40'])
                older = bounded['observations']['runs'][0]
                self.assertFalse(older['jobs_observed'])
                self.assertIsNone(older['jobs'])
                self.assertEqual(len(bounded['observations']['runs']), len(runs))
                self.assertFalse(bounded['effect_ack_done'])

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
                "workflow_runs": [run(i + 1, f"workflow-{i}", "completed",
                                      "2026-11-04T00:00:00Z", "2026-11-04T00:00:01Z", "success")
                                  for i in range(count)]}

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

    def collect(self, page: dict | list, *, deny: str = "", checker_missing: bool = False,
                full_observation: bool = False, job_payload: dict | None = None,
                job_counts: dict | None = None) -> tuple:
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
        (root / "jobs.json").write_text(json.dumps(job_payload), encoding="utf-8")
        (root / "job-counts.json").write_text(json.dumps(job_counts or {}), encoding="utf-8")
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
            if '/issues?' in path:
                print('[]')
                raise SystemExit(0)
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
                log.write(json.dumps({{'kind': kind, 'path': path, 'args': sys.argv[3:]}}) + '\\n')
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
                pages = json.loads((root / 'runs.json').read_text())
                if isinstance(pages, list):
                    value = pages[page_number - 1] if page_number <= len(pages) else (
                        {{**pages[0], 'workflow_runs': []}} if pages else [])
                else:
                    value = {{**pages, 'workflow_runs': pages['workflow_runs'][start:start + 100]}}
                print(json.dumps(value))
            elif kind == 'jobs':
                payload = json.loads((root / 'jobs.json').read_text())
                if payload is None:
                    run_id = int(path.split('/runs/')[1].split('/')[0])
                    count = json.loads((root / 'job-counts.json').read_text()).get(str(run_id), 0)
                    entries = [{{'id': run_id * 1000 + i + 1, 'run_id': run_id,
                                'head_sha': '{HEAD}', 'run_attempt': 1,
                                'status': 'completed', 'conclusion': 'success'}} for i in range(count)]
                    payload = {{'total_count': count, 'jobs': entries[start:start + 100]}}
                print(json.dumps(payload))
            else:
                print(responses.get(kind, (root / 'runs.json').read_text()))
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
                self.assertTrue(all(r['kind'] == 'runs' for r in requests))
                self.assertEqual(plan["state"], "HOLD")

    @staticmethod
    def history_pages() -> list[dict]:
        runs = JobReadbackBudgetTests.page(213)["workflow_runs"]
        for item in runs:
            item["name"] = f"workflow-{item['id'] % 10}"
            item['created_at'] = (datetime(2026, 11, 4, tzinfo=timezone.utc)
                                  + timedelta(seconds=item['id'])).isoformat()
            item['updated_at'] = item['created_at']
        # Older than the latest terminal runs, but still active: must be read.
        runs[0]["status"] = "in_progress"
        runs[0]["conclusion"] = None
        return [{"total_count": 213, "workflow_runs": runs[start:start + 100]}
                for start in range(0, 213, 100)]

    def test_real_workflow_paginates_all_213_runs_and_reads_the_exact_required_union(self):
        pages = self.history_pages()
        result, requests, plan = self.collect(pages)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([r for r in requests if r['kind'] == 'runs']), 3)
        inventory = MODULE.merge_run_pages(pages)
        expected = set(range(204, 214)) | {1}
        self.assertEqual(plan['returned_run_count'], 213)
        self.assertEqual(plan['reported_run_count'], 213)
        self.assertEqual(set(plan['run_ids']), expected)
        self.assertEqual(len(plan['metadata_only_run_ids']), 213 - len(expected))
        self.assertEqual(len([r for r in requests if r['kind'] == 'jobs']), len(expected))
        self.assertLessEqual(len(expected), 20)

    def test_all_active_runs_count_even_when_the_workflow_has_a_newer_terminal_run(self):
        page = self.page(21)
        for item in page['workflow_runs']:
            item['name'] = 'one-workflow'
            item['status'] = 'queued'
            item['conclusion'] = None
        page['workflow_runs'][-1]['status'] = 'completed'
        page['workflow_runs'][-1]['conclusion'] = 'success'
        page['workflow_runs'][-1]['created_at'] = '2026-11-04T00:00:02Z'
        page['workflow_runs'][-1]['updated_at'] = '2026-11-04T00:00:03Z'
        result, requests, plan = self.collect(page)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(plan['first_blocker'], 'JOB_READBACK_REQUEST_BUDGET_EXCEEDED')
        self.assertEqual(plan['required_job_request_count'], 21)
        self.assertEqual([r['kind'] for r in requests], ['runs'])

    def test_inconsistent_duplicate_wrong_head_and_malformed_pages_stop_before_jobs(self):
        import copy
        cases = []
        drift = self.history_pages(); drift[-1]['total_count'] = 214; cases.append(drift)
        duplicate = self.history_pages(); duplicate[-1]['workflow_runs'][-1] = duplicate[0]['workflow_runs'][0]; cases.append(duplicate)
        wrong_head = self.page(1); wrong_head['workflow_runs'][0]['head_sha'] = TREE; cases.append([wrong_head])
        for key, value in [('status', 'unknown'), ('name', ''), ('created_at', 'invalid')]:
            page = self.page(1); page['workflow_runs'][0][key] = value; cases.append([page])
        cases.extend([[], [{}], [copy.deepcopy(self.history_pages()[0])]])
        for pages in cases:
            with self.subTest(pages=str(pages)[:80]):
                result, requests, _ = self.collect(pages)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(all(r['kind'] == 'runs' for r in requests))

    def test_truncated_or_malformed_jobs_stop_at_completeness_preflight(self):
        for payload in ({'total_count': 101, 'jobs': []},
                        {'total_count': True, 'jobs': []},
                        {'total_count': 1, 'jobs': [None]},
                        {'total_count': 1, 'jobs': [{'id': 7, 'status': 'completed', 'run_id': 999}]},
                        {'total_count': 1, 'jobs': [{'id': 7, 'status': 'completed', 'head_sha': TREE}]},
                        {'total_count': 1, 'jobs': [{'id': 7, 'status': 'completed', 'run_attempt': 2}]},
                        {'total_count': 2, 'jobs': [{'id': 7, 'status': 'completed'}] * 2},
                        {'total_count': 1, 'jobs': [{'id': 7, 'status': 'in_progress'}]}):
            with self.subTest(payload=payload):
                result, requests, _ = self.collect(self.page(1), job_payload=payload)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual([r['kind'] for r in requests], ['runs', 'jobs'])

    def test_job_plan_is_bound_to_inventory_and_requires_every_selected_job_file(self):
        inventory = MODULE.merge_run_pages(self.history_pages())
        plan = MODULE.job_readback_budget(inventory, expected_head=HEAD, required_jobs_only=True)
        complete = {str(run_id): [] for run_id in plan['run_ids']}
        MODULE.validate_job_plan(inventory, complete, plan, expected_head=HEAD)
        with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
            MODULE.validate_job_plan(inventory, {}, plan, expected_head=HEAD)
        with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
            MODULE.validate_job_plan(inventory, {**complete, '999': []}, plan, expected_head=HEAD)
        altered = {**inventory, 'page_count': 4}
        with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
            MODULE.validate_job_plan(altered, complete, plan, expected_head=HEAD)

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

    def test_job_continuation_pages_share_the_total_20_request_budget(self):
        result, requests, _ = self.collect(self.page(1), job_counts={'1': 101})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len([r for r in requests if r['kind'] == 'jobs']), 2)
        result, requests, _ = self.collect(self.page(20), job_counts={'1': 101})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len([r for r in requests if r['kind'] == 'jobs']), 20)

    def test_unrecognized_job_status_cannot_become_trusted_gate_success(self):
        entry = self.page(1)['workflow_runs'][0]
        entries = [{'id': i, 'run_id': 1, 'head_sha': HEAD, 'run_attempt': 1,
                    'status': status, 'conclusion': conclusion}
                   for i, status, conclusion in [(10, 'completed', 'success'),
                                                  (11, 'unrecognized', None)]]
        result, requests, _ = self.collect(self.page(1), job_payload={'total_count': 2, 'jobs': entries})
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(len([r for r in requests if r['kind'] == 'jobs']), 1)
        for status in ('unrecognized', 'queued', 'in_progress'):
            entries[1]['status'] = status
            self.assertEqual(MODULE._gate_state_for_run(entry, {'1': entries}, required=True)['state'], 'UNTRUSTED')

    def test_run_pagination_budget_and_numeric_latest_tie_break(self):
        result, requests, _ = self.collect(self.page(1001))
        self.assertNotEqual(result.returncode, 0)
        self.assertLessEqual(len(requests), MODULE.MAX_RUN_READBACK_REQUESTS)
        self.assertTrue(all(r['kind'] == 'runs' for r in requests))
        page = self.page(10)
        for entry in page['workflow_runs']:
            entry['name'] = 'same-workflow'
        plan = MODULE.job_readback_budget(page, expected_head=HEAD, required_jobs_only=True)
        self.assertEqual(plan['run_ids'], [10])

    def test_planned_analysis_never_filters_malformed_job_entries_into_success(self):
        for entries in ([{'id': 1, 'status': 'completed'}, None],
                        [{'id': 1, 'status': 'unrecognized'}],
                        [{'id': 1, 'status': 'completed'}] * 2):
            with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
                MODULE._jobs_by_run({'1': entries}, strict=True)
        page = self.page(1)
        plan = MODULE.job_readback_budget(page, expected_head=HEAD, required_jobs_only=True)
        valid = {'id': 1, 'status': 'completed', 'conclusion': 'success',
                 'head_sha': HEAD, 'run_id': 1, 'run_attempt': 1}
        MODULE.validate_job_plan(page, {'1': [valid]}, plan, expected_head=HEAD)
        for key, bad in [('head_sha', TREE), ('run_id', 2), ('run_attempt', 2)]:
            with self.assertRaises(MODULE.ReflexiveWatchdogBlock):
                MODULE.validate_job_plan(page, {'1': [{**valid, key: bad}]}, plan, expected_head=HEAD)


class LargeRunInventoryTests(unittest.TestCase):
    def inventory(self, count=2500, *, same_second=False):
        start = datetime(2026, 11, 12, tzinfo=timezone.utc)
        return [run(i, f"workflow-{i % 10}", "completed",
                    (start + timedelta(seconds=0 if same_second else i // 3)).isoformat(),
                    (start + timedelta(seconds=900)).isoformat(), "success")
                for i in range(count, 0, -1)]

    def collect(self, runs, *, corrupt=None, budget=None):
        from urllib.parse import parse_qs, urlsplit
        requests = []
        def read(endpoint, destination):
            requests.append(endpoint)
            query = parse_qs(urlsplit(endpoint).query)
            self.assertEqual(query['head_sha'], [HEAD])
            page = int(query['page'][0])
            self.assertLessEqual(page, 10, 'GitHub filtered searches cap at 1,000 results')
            selected = runs
            interval = query.get('created', [None])[0]
            if interval:
                stamp = lambda text: datetime.fromisoformat(text.replace('Z', '+00:00'))
                if '..' in interval:
                    lo, hi = map(stamp, interval.split('..'))
                    selected = [r for r in runs if lo <= stamp(r['created_at']) <= hi]
                elif interval.startswith('>='):
                    selected = [r for r in runs if stamp(r['created_at']) >= stamp(interval[2:])]
                else:
                    selected = [r for r in runs if stamp(r['created_at']) <= stamp(interval[2:])]
            result = {'total_count': len(selected),
                      'workflow_runs': selected[(page - 1) * 100:page * 100]}
            return corrupt(result, endpoint, len(requests)) if corrupt else result
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(MODULE, '_readback_page', side_effect=read):
            if budget is None:
                value = MODULE.collect_runs(repository='example/qik-vrt', expected_head=HEAD,
                                            directory=pathlib.Path(temporary))
            else:
                with mock.patch.object(MODULE, 'MAX_RUN_READBACK_REQUESTS', budget):
                    value = MODULE.collect_runs(repository='example/qik-vrt', expected_head=HEAD,
                                                directory=pathlib.Path(temporary))
        return value, requests

    def test_2500_runs_are_complete_across_disjoint_time_queries(self):
        runs = self.inventory()
        result, requests = self.collect(runs)
        self.assertFalse(result['truncated'], result)
        self.assertEqual(result['total_count'], 2500)
        self.assertEqual({r['id'] for r in result['workflow_runs']}, set(range(1, 2501)))
        self.assertEqual(len(result['workflow_runs']), 2500)
        self.assertTrue(any('created=' in query for query in requests))
        self.assertLessEqual(len(requests), 64)
        plan = MODULE.job_readback_budget(result, expected_head=HEAD, required_jobs_only=True)
        self.assertEqual(plan['state'], 'READY')
        self.assertFalse(plan['effect_ack_done'])

    def test_single_second_overflow_holds_without_retry_or_missing_success(self):
        result, requests = self.collect(self.inventory(1001, same_second=True))
        self.assertTrue(result['truncated'])
        self.assertEqual(result['first_blocker'], 'RUN_TIME_PARTITION_UNSPLITTABLE')
        self.assertLessEqual(len(requests), 5)

    def test_total_request_budget_remains_bounded(self):
        result, requests = self.collect(self.inventory(), budget=3)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['first_blocker'], 'READBACK_REQUEST_BUDGET_EXCEEDED')
        self.assertEqual(len(requests), 3)

    def test_exactly_1000_runs_in_one_second_keep_the_older_run(self):
        runs = self.inventory(1001, same_second=True)
        runs[-1]['created_at'] = '2026-11-11T23:59:59Z'
        result, _ = self.collect(runs)
        self.assertFalse(result['truncated'], result)
        self.assertEqual(len(result['workflow_runs']), 1001)

    def test_partition_count_drift_and_wrong_head_remain_unverified(self):
        def drift(value, endpoint, count):
            if 'created=' in endpoint:
                value['total_count'] += 1
            return value
        def foreign(value, endpoint, count):
            if 'created=' in endpoint and value['workflow_runs']:
                value['workflow_runs'][0] = {**value['workflow_runs'][0], 'head_sha': TREE}
            return value
        for corrupt in (drift, foreign):
            result, _ = self.collect(self.inventory(), corrupt=corrupt)
            self.assertTrue(result['truncated'])
            self.assertNotEqual(MODULE.job_readback_budget(result, expected_head=HEAD,
                             required_jobs_only=True)['state'], 'READY')

    def test_changed_root_readback_rejects_snapshot(self):
        def mutate(value, endpoint, count):
            if count > 1 and 'created=' not in endpoint and 'page=1&' in endpoint + '&':
                value['workflow_runs'][0] = {**value['workflow_runs'][0], 'run_attempt': 2}
            return value
        result, _ = self.collect(self.inventory(), corrupt=mutate)
        self.assertTrue(result['truncated'])
        self.assertEqual(result['first_blocker'], 'READBACK_INVENTORY_CHANGED_OR_TRUNCATED')


class OpenWorkCollectionTests(unittest.TestCase):
    def test_runner_context_is_not_evaluated_in_job_level_environment(self):
        # GitHub's context-availability contract permits runner at step.env,
        # but not jobs.<job_id>.env. Plain YAML parsing cannot detect this.
        source = (ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml").read_text()
        before_steps = source.split('    steps:', 1)[0]
        self.assertNotIn('${{ runner.', before_steps)
        step = source.split('      - name: Admit the exact watchdog repair input before continuing existing work', 1)[1]
        self.assertIn('          WATCHDOG_REPAIR_ROOT: ${{ runner.temp }}', step.split('        run:', 1)[0])

    def test_actual_consumer_shell_retains_bound_analysis_without_executing_its_text(self):
        from tools import qikvrt_autonomous_self_heal as consumer
        analysis = {"schema": "qikvrt_reflexive_repository_watchdog_receipt_v1",
            "repository": "example/qik-vrt", "head_sha": HEAD, "tree_sha": TREE,
            "disposition": "HOLD", "first_blocker": "OPEN_WORK_WITHOUT_PRODUCTIVE_EXECUTION",
            "safe_continuation": "$(touch MUST_NOT_EXECUTE); exit 99"}
        envelope = MODULE.repair_handoff(MODULE.canonical_json_bytes(analysis),
            run_id=123, run_attempt=1, producer_event="issues")
        source = {"repository": {"full_name": "example/qik-vrt"}, "head_sha": HEAD,
            "path": envelope["origin"]["workflow_path"], "id": 123, "run_attempt": 1,
            "event": "issues", "status": "completed", "conclusion": "success"}
        source_jobs = {"total_count": 1, "jobs": [{"id": 124, "run_id": 123,
            "head_sha": HEAD, "run_attempt": 1, "status": "completed", "steps": [{
                "name": "Bind error analysis for the existing repair consumer",
                "status": "completed", "conclusion": "success"}]}]}
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "tools").mkdir()
            (root / "state/autonomy").mkdir(parents=True)
            shutil.copyfile(pathlib.Path(consumer.__file__), root / "tools/qikvrt_autonomous_self_heal.py")
            shutil.copyfile(ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json",
                            root / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json")
            (root / "bin").mkdir()
            for name, value in (("source-run", source), ("source-jobs", source_jobs),
                ("source-artifacts", {"artifacts": [{"id": 125, "expired": False,
                    "name": "qikvrt-reflexive-repository-watchdog-123-1"}]})):
                (root / f"{name}.json").write_text(json.dumps(value))
            with zipfile.ZipFile(root / "artifact.zip", "w") as archive:
                archive.writestr("error-analysis-handoff.json", MODULE.canonical_json_bytes(envelope))
            gh = root / "bin/gh"
            gh.write_text(f'#!{sys.executable}\nimport pathlib,sys\nr=pathlib.Path({str(root)!r})\np=sys.argv[2]\n'
                "name='artifact.zip' if p.endswith('/zip') else 'source-artifacts.json' if '/artifacts?' in p else 'source-jobs.json' if '/jobs?' in p else 'source-run.json'\n"
                "sys.stdout.buffer.write((r/name).read_bytes())\n")
            gh.chmod(0o700)
            git = root / "bin/git"
            git.write_text(f'#!{sys.executable}\nimport sys\nprint({TREE!r} if "tree" in sys.argv[-1] else {HEAD!r})\n')
            git.chmod(0o700)
            workflow = (ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml").read_text()
            section = workflow.split('      - name: Admit the exact watchdog repair input before continuing existing work\n', 1)[1]
            shell = textwrap.dedent(section.split('\n      - name:', 1)[0].split('        run: |\n', 1)[1])
            environment = {**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"],
                "WATCHDOG_REPAIR_ROOT": str(root / "runner-temp/repair"),
                "GITHUB_REPOSITORY": "example/qik-vrt", "SOURCE_RUN_ID": "123", "SOURCE_RUN_ATTEMPT": "1"}
            result = subprocess.run(["bash", "-c", shell], cwd=root, env=environment,
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((root / 'runner-temp/repair/consumer-receipt.json').read_text())
            self.assertTrue(receipt["inbox_readback_verified"])
            self.assertFalse(receipt["writer_admitted"])
            self.assertFalse(receipt["repair_executed"])
            self.assertFalse((root / "MUST_NOT_EXECUTE").exists())
            source["head_sha"] = "c" * 40
            with self.assertRaisesRegex(consumer.SelfHealBlock, "producer"):
                consumer.consume_repair_input(envelope, source, source_jobs, repository="example/qik-vrt",
                    head=HEAD, tree=TREE, inbox=root / "rejected")

    @staticmethod
    def entries(count, start=1):
        return [{"id": i, "number": i, "state": "open",
                 "url": f"https://api.github.com/repos/example/qik-vrt/issues/{i}",
                 **({"pull_request": {}} if i % 2 == 0 else {})}
                for i in range(start, start + count)]

    def collect(self):
        with tempfile.TemporaryDirectory() as directory:
            return MODULE.collect_work(repository="example/qik-vrt", expected_head=HEAD,
                directory=pathlib.Path(directory), now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc))

    def test_full_open_issue_and_pr_inventory_requires_terminal_and_stability_reads(self):
        first, last = self.entries(100), self.entries(2, 101)
        with mock.patch.object(MODULE, "_readback_page", side_effect=[first, last, first]) as read:
            value = self.collect()
        self.assertTrue(value["complete"])
        self.assertEqual(value["total_count"], 102)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(value["items"][1]["kind"], "PULL_REQUEST")
        self.assertNotIn("state", value["items"][0])

    def test_denial_stops_without_retry_or_empty_queue_success(self):
        with mock.patch.object(MODULE, "_readback_page", side_effect=MODULE.ReflexiveWatchdogBlock("HTTP 403")) as read:
            with self.assertRaisesRegex(MODULE.ReflexiveWatchdogBlock, "HTTP 403"):
                self.collect()
        self.assertEqual(read.call_count, 1)

    def test_changing_or_duplicate_inventory_cannot_prove_an_empty_or_complete_queue(self):
        with mock.patch.object(MODULE, "_readback_page", side_effect=[[], self.entries(1)]):
            value = self.collect()
        self.assertFalse(value["complete"])
        self.assertEqual(value["first_blocker"], "WORK_READBACK_CHANGED_DURING_COLLECTION")
        with mock.patch.object(MODULE, "_readback_page", side_effect=[self.entries(100), self.entries(1)]):
            with self.assertRaisesRegex(MODULE.ReflexiveWatchdogBlock, "DUPLICATED"):
                self.collect()

    def test_inventory_budget_exhaustion_is_hold(self):
        pages = [self.entries(100, 1 + 100 * i) for i in range(MODULE.MAX_WORK_READBACK_PAGES)]
        with mock.patch.object(MODULE, "_readback_page", side_effect=pages) as read:
            value = self.collect()
        self.assertFalse(value["complete"])
        self.assertTrue(value["truncated"])
        self.assertEqual(read.call_count, MODULE.MAX_WORK_READBACK_PAGES)

    def test_producer_and_consumer_are_connected_without_a_completion_feedback_loop(self):
        producer = WORKFLOW.read_text()
        consumer = (ROOT / ".github/workflows/qikvrt_autonomous_pr_continuation.yml").read_text()
        self.assertIn("--work-file", producer)
        self.assertIn("Bind error analysis for the existing repair consumer", producer)
        self.assertIn("steps.analyze.outcome == 'failure'", producer)
        self.assertIn('"QIKVRT reflexive repository watchdog"', consumer.split('permissions:')[0])
        self.assertNotIn('"QIK-VRT autonomous draft-PR continuation"', producer.split('permissions:')[0])
        self.assertIn("repair-consume", consumer)
        self.assertIn("--source-jobs", consumer)


if __name__ == "__main__":
    unittest.main()

