# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_self_heal",
    ROOT / "tools/qikvrt_autonomous_self_heal.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousSelfHealTests(unittest.TestCase):
    def test_expected_head_bound_promotion_is_exact_and_fail_closed(self) -> None:
        contract = MODULE.load_contract()
        delegation = MODULE.load_delegation()
        expected = list(MODULE.PROMOTION_CONDITIONS)
        self.assertEqual(
            contract["execution_model"]["promotion"],
            "expected_head_bound_only",
        )
        self.assertEqual(
            contract["promotion_policy"]["unconditional_automatic_merge"],
            "FORBIDDEN",
        )
        self.assertEqual(
            contract["promotion_policy"]["expected_head_bound_promotion"],
            "ALLOWED_ONLY_IF",
        )
        self.assertEqual(contract["promotion_policy"]["conditions"], expected)
        self.assertFalse(
            contract["promotion_policy"]["proposal_workflow_may_merge"]
        )
        self.assertFalse(
            contract["promotion_policy"]["general_auto_merge_authorization"]
        )
        self.assertTrue(
            delegation["promotion_policy"]["standing_delegation"]
        )
        self.assertEqual(
            delegation["promotion_policy"]["conditions"],
            expected,
        )
        forbidden = set(contract["forbidden_effects"])
        self.assertIn("unconditional_automatic_merge", forbidden)
        self.assertIn("unbound_or_stale_head_promotion", forbidden)
        self.assertIn("zenodo_mutation", forbidden)
        self.assertIn("ietf_mutation", forbidden)
        self.assertIn("deployment", forbidden)

    def test_allowlist_is_exactly_handler_owned(self) -> None:
        contract = MODULE.load_contract()
        allowed = MODULE.allowed_paths(contract)
        self.assertIn("anticipation/next-effect.json", allowed)
        self.assertIn("docs/publications/index.json", allowed)
        self.assertIn("docs/publications/index.html", allowed)
        self.assertIn("REPOSITORY_FILE_MANIFEST.json", allowed)
        self.assertNotIn("AI_STATUS.md", allowed)
        self.assertNotIn(
            ".github/workflows/qikvrt_autonomous_self_heal.yml",
            allowed,
        )

    def test_publication_overview_precedes_integrity(self) -> None:
        handlers = MODULE.load_contract()["allowlisted_handlers"]
        order = [handler["failure_class"] for handler in handlers]
        self.assertLess(
            order.index("PUBLICATION_OVERVIEW_DRIFT"),
            order.index("REPOSITORY_NATIVE_INTEGRITY_STALE"),
        )
        publication = next(
            handler
            for handler in handlers
            if handler["failure_class"] == "PUBLICATION_OVERVIEW_DRIFT"
        )
        self.assertEqual(
            publication["failure_signature"],
            "publication overview drift:",
        )

    def test_pr_continuation_is_explicitly_opt_in_and_external_gate_bounded(self) -> None:
        continuation = MODULE.load_contract()["pull_request_continuation"]
        self.assertEqual(
            continuation["opt_in_marker"],
            "<!-- qikvrt-autonomous-self-heal:enabled -->",
        )
        self.assertTrue(continuation["same_repository_only"])
        self.assertTrue(continuation["draft_only"])
        self.assertEqual(continuation["maximum_pull_requests_per_run"], 1)
        self.assertIn(
            "IDENTIFIED_HUMAN_PHYSICS_REVIEW_WHEN_REQUIRED",
            continuation["external_gates"],
        )
        self.assertIn(
            "SEPARATE_EXPLICIT_ZENODO_AUTHORIZATION",
            continuation["external_gates"],
        )

    def test_semantic_fingerprint_is_path_and_byte_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "a").write_bytes(b"one")
            (root / "b").write_bytes(b"two")
            with mock.patch.object(MODULE, "ROOT", root):
                first = MODULE.semantic_fingerprint(["a", "b"])
                second = MODULE.semantic_fingerprint(["b", "a"])
                self.assertEqual(first, second)
                (root / "b").write_bytes(b"three")
                self.assertNotEqual(
                    first,
                    MODULE.semantic_fingerprint(["a", "b"]),
                )

    def test_candidate_identity_binds_base_and_fingerprint(self) -> None:
        fingerprint = "1" * 64
        first = MODULE.candidate_identity("a" * 40, fingerprint)
        self.assertEqual(
            first,
            MODULE.candidate_identity("a" * 40, fingerprint),
        )
        self.assertNotEqual(
            first,
            MODULE.candidate_identity("b" * 40, fingerprint),
        )

    def test_non_projection_anticipation_failure_blocks(self) -> None:
        handler = {
            "failure_class": "ANTICIPATION_PROJECTION_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "projection drift:",
        }
        result = MODULE.CommandResult(
            ("probe",),
            2,
            "BLOCK",
            "source binding drift",
        )
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_generic_failure_signature_blocks_unrecognized_failure(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        result = MODULE.CommandResult(("probe",), 2, "", "different failure")
        with mock.patch.object(MODULE, "run", return_value=result):
            with self.assertRaises(MODULE.SelfHealBlock):
                MODULE.repair_handler(handler)

    def test_recognized_failure_runs_exact_repair(self) -> None:
        handler = {
            "failure_class": "PUBLICATION_OVERVIEW_DRIFT",
            "probe": ["probe"],
            "repair": ["repair"],
            "failure_signature": "publication overview drift:",
        }
        results = [
            MODULE.CommandResult(
                ("probe",), 2, "publication overview drift: missing", ""
            ),
            MODULE.CommandResult(("repair",), 0, "MATERIALIZED", ""),
        ]
        with mock.patch.object(MODULE, "run", side_effect=results) as mocked:
            value = MODULE.repair_handler(handler)
        self.assertEqual(value["state"], "REPAIRED")
        self.assertEqual(mocked.call_count, 2)


class RepairInputTests(unittest.TestCase):
    def test_missing_or_weakened_delivery_contract_cannot_be_admitted(self):
        import json, copy
        value=json.loads(MODULE.CONTRACT.read_text())
        MODULE.validate_repair_handoff_contract(value)
        for field in value['error_analysis_handoff']:
            if field not in {'manual_owner_relay_required','new_executor','maximum_hops','consumer','activation'}:
                continue
            with self.subTest(field=field):
                changed=copy.deepcopy(value);del changed['error_analysis_handoff'][field]
                with self.assertRaises(MODULE.SelfHealBlock):
                    MODULE.validate_repair_handoff_contract(changed)
    def fixture(self):
        import json
        spec = importlib.util.spec_from_file_location("repair_watchdog", ROOT / "tools/qikvrt_reflexive_repository_watchdog.py")
        watchdog = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(watchdog)
        analysis = {"schema": "qikvrt_reflexive_repository_watchdog_receipt_v1",
                    "repository": "ingolf-lohmann/qik-vrt", "head_sha": "a"*40,
                    "tree_sha": "b"*40, "disposition": "HOLD",
                    "first_blocker": "REQUIRED_GATE_EXECUTION_FAILED"}
        raw = json.dumps(analysis, indent=2).encode()
        envelope = watchdog.repair_handoff(raw, run_id=7, run_attempt=2, producer_event="pull_request")
        source = {"repository": {"full_name": analysis['repository']}, "head_sha": "a"*40,
                  "path": envelope['origin']['workflow_path'], "id": 7, "run_attempt": 2,
                  "event": "pull_request", "status": "completed", "conclusion": "success"}
        jobs = {"total_count": 1, "jobs": [{"id": 8, "run_id": 7, "run_attempt": 2,
                "head_sha": "a"*40, "status": "completed", "steps": [{
                "name": "Bind error analysis for the existing repair consumer",
                "status": "completed", "conclusion": "success"}]}]}
        return watchdog, raw, envelope, source, jobs

    def consume(self, env, source, jobs, inbox):
        return MODULE.consume_repair_input(env, source, jobs, repository="ingolf-lohmann/qik-vrt",
                   head="a"*40, tree="b"*40, inbox=pathlib.Path(inbox))

    def test_actual_producer_to_existing_consumer_preserves_analysis_and_readback(self):
        import json
        _, raw, env, source, jobs = self.fixture()
        with tempfile.TemporaryDirectory() as inbox:
            with mock.patch.object(MODULE, "execute", side_effect=AssertionError("no unadmitted repair")):
                receipt = self.consume(env, source, jobs, inbox)
                self.assertEqual(receipt['state'], 'ADMITTED_ANALYSIS_HOLD')
                saved = json.loads(next(pathlib.Path(inbox).glob('*.json')).read_text())
                self.assertEqual(saved['analysis_utf8'].encode(), raw)
                self.assertTrue(receipt['inbox_readback_verified'])
                self.assertFalse(receipt['writer_admitted'])
                self.assertFalse(receipt['effect_ack_done'])
                second = self.consume(env, source, jobs, inbox)
                self.assertEqual(second['state'], 'DUPLICATE_READBACK')
                self.assertEqual(len(list(pathlib.Path(inbox).glob('*.json'))), 1)

    def test_each_foreign_stale_replay_tampered_input_is_blocked_before_inbox(self):
        import copy
        _, _, env, source, jobs = self.fixture()
        changes = [
            ('subject', lambda e,s,j: e['subject'].update(head='c'*40)),
            ('tree', lambda e,s,j: e['subject'].update(tree='c'*40)),
            ('repository', lambda e,s,j: s['repository'].update(full_name='foreign/repo')),
            ('attempt', lambda e,s,j: s.update(run_attempt=3)),
            ('run', lambda e,s,j: s.update(id=9)),
            ('workflow', lambda e,s,j: s.update(path='evil.yml')),
            ('zero jobs', lambda e,s,j: j.update(total_count=0,jobs=[])),
            ('step skipped', lambda e,s,j: j['jobs'][0]['steps'][0].update(conclusion='skipped')),
            ('foreign job', lambda e,s,j: j['jobs'][0].update(head_sha='c'*40)),
            ('job attempt', lambda e,s,j: j['jobs'][0].update(run_attempt=1)),
            ('analysis bytes', lambda e,s,j: e.update(analysis_utf8=e['analysis_utf8']+' ')),
            ('permission', lambda e,s,j: e.update(effect_permission=True)),
            ('recursive', lambda e,s,j: e.update(hop_count=2)),
            ('work unit', lambda e,s,j: e.update(work_unit_id='0'*64)),
        ]
        for label, change in changes:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as inbox:
                e,s,j = copy.deepcopy((env,source,jobs)); change(e,s,j)
                with self.assertRaises(MODULE.SelfHealBlock): self.consume(e,s,j,inbox)
                self.assertEqual(list(pathlib.Path(inbox).iterdir()), [])

    def test_consumer_feedback_is_a_bounded_noop(self):
        watchdog, raw, _, _, _ = self.fixture()
        env = watchdog.repair_handoff(raw, run_id=7, run_attempt=2,
              producer_event='workflow_run', parent_workflow='QIK-VRT autonomous draft-PR continuation')
        self.assertEqual(env['state'], 'NOOP')

    def test_inbox_conflict_does_not_overwrite_predecessor(self):
        _, _, env, source, jobs = self.fixture()
        with tempfile.TemporaryDirectory() as inbox:
            path = pathlib.Path(inbox) / (env['work_unit_id']+'.json'); path.write_bytes(b'conflicting state')
            with self.assertRaises(MODULE.SelfHealBlock): self.consume(env,source,jobs,inbox)
            self.assertEqual(path.read_bytes(),b'conflicting state')

    def test_real_cli_roundtrip_and_replay_keep_the_same_analysis_bytes(self):
        import json, subprocess
        _, raw, _, source, jobs = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root/'analysis.json').write_bytes(raw)
            for name, value in [('run',source),('jobs',jobs)]:
                (root/(name+'.json')).write_text(json.dumps(value))
            producer = subprocess.run([sys.executable, '-B', str(ROOT/'tools/qikvrt_reflexive_repository_watchdog.py'),
                'repair-handoff', '--analysis-file', str(root/'analysis.json'), '--run-id','7',
                '--run-attempt','2','--event','pull_request','--json'], capture_output=True, check=True)
            (root/'envelope.json').write_bytes(producer.stdout)
            command = [sys.executable,'-B',str(ROOT/'tools/qikvrt_autonomous_self_heal.py'),
                'repair-consume','--envelope',str(root/'envelope.json'),'--source-run',str(root/'run.json'),
                '--source-jobs',str(root/'jobs.json'),'--repository-name','ingolf-lohmann/qik-vrt',
                '--expected-head','a'*40,'--expected-tree','b'*40,'--inbox',str(root/'inbox')]
            for expected in ['ADMITTED_ANALYSIS_HOLD','DUPLICATE_READBACK']:
                result = subprocess.run(command,capture_output=True,text=True,check=True)
                receipt = json.loads(result.stdout)
                self.assertEqual(receipt['state'],expected)
                self.assertFalse(receipt['repair_executed'])
                saved=json.loads(next((root/'inbox').glob('*.json')).read_text())
                self.assertEqual(saved['analysis_utf8'].encode(),raw)
            command[command.index('--expected-head')+1]='c'*40
            bad=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(bad.returncode,2)
            self.assertEqual(json.loads(bad.stdout)['state'],'BLOCK')

if __name__ == "__main__":
    unittest.main()
