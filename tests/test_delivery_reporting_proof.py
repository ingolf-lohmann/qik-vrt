#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Differential bridge from actual Lean output, including an executable mutant."""
import contextlib
import copy
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import ai_handoff
from tests import test_ai_runtime_bootloader as client_fixtures

ROOT = Path(__file__).resolve().parents[1]


class DeliveryReportingProofTests(unittest.TestCase):
    def test_panic_followed_by_success_and_zero_exit_is_rejected(self):
        result = subprocess.run([sys.executable, "-c",
            "print('PANIC at fixture.checker: invalid declaration'); print('REPLAY_PASS')"],
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0)
        with self.assertRaisesRegex(RuntimeError, "panic/error"):
            ai_handoff.require_formal_command_success(result.returncode, result.stdout)
        ai_handoff.require_formal_command_success(0, "ordinary check completed\n")

    def vectors(self):
        policy = ai_handoff.formal_policy()
        path = ROOT / policy["vectors_path"]
        self.assertTrue(path.is_file(), "HOLD: original Lean-generated vectors missing")
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), policy["vectors_sha256"])
        values = json.loads(raw)
        self.assertTrue(values, "zero vectors must fail closed")
        return values

    def fixture(self):
        case = client_fixtures.ClientContinuationRegressionTests()
        case.setUp()
        return case

    def test_actual_client_receipt_path_matches_every_lean_vector(self):
        for vector in self.vectors():
            report = {k: v for k, v in vector.items() if k != "verdict"}
            case = self.fixture()
            case.receipt["delivery_report"] = report
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    ai_handoff.validate_client_receipt(case.receipt)
                    result = "accept"
                except SystemExit:
                    result = "reject"
            self.assertEqual(result, vector["verdict"], report)

    def test_original_cli_receipt_path_and_negative_controls(self):
        selected = {}
        for vector in self.vectors():
            if vector["claim"] != "delivered" or not vector["provenanceBound"]:
                continue
            obs = vector["observations"]
            if len(obs) == 1 and obs[0]["utc"] == 2:
                o = obs[0]
                if o["target"] == "local":
                    selected.setdefault("local", vector)
                elif o["status"] == 403:
                    selected.setdefault("403", vector)
                elif o["subjectRef"] != vector["subjectRef"]:
                    selected.setdefault("foreign-subject", vector)
                elif vector["verdict"] == "accept":
                    selected.setdefault("valid", vector)
            if len(obs) == 2:
                selected.setdefault("replay", vector)
        self.assertEqual(set(selected), {"local", "403", "foreign-subject", "valid", "replay"})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"
            for label, vector in selected.items():
                case = self.fixture()
                case.receipt["delivery_report"] = {k: v for k, v in vector.items() if k != "verdict"}
                path.write_text(json.dumps(case.receipt))
                proc = subprocess.run([sys.executable, "-B", "tools/ai_handoff.py", "--client-receipt", str(path)],
                    cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertEqual(proc.returncode == 0, vector["verdict"] == "accept", (label, proc.stderr))

    def test_status_condition_mutant_disagrees_with_lean(self):
        source = (ROOT / "tools/ai_handoff.py").read_text()
        original = 'and observation["status"] == 200'
        self.assertEqual(source.count(original), 1)
        mutant = source.replace(original, "and True", 1)
        scope = {"__file__": str(ROOT / "tools/ai_handoff.py"), "__name__": "delivery_mutant"}
        exec(compile(mutant, "delivery-mutant", "exec"), scope)
        mismatches = []
        for vector in self.vectors():
            report = {k: v for k, v in vector.items() if k != "verdict"}
            if scope["delivery_report_verdict"](report) != vector["verdict"]:
                mismatches.append(vector)
        self.assertTrue(mismatches, "status mutation escaped the bridge")

    def test_missing_vectors_and_zero_receipts_are_blocking(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                ai_handoff.formal_proof_gate(Path(tmp))

    def receipt_fixtures(self, directory):
        """Synthetic consistency inputs, never execution or proof receipts."""
        policy = ai_handoff.formal_policy()
        bundle, digests = ai_handoff.formal_source_binding(policy)
        (directory / "logs").mkdir()
        artifact = directory / "fixture-input.bin"
        artifact.write_bytes(b"TEST FIXTURE ONLY; NOT A PROOF")
        for checker in policy["checkers"]:
            log = directory / "logs" / (checker["id"] + ".log")
            log.write_text("TEST FIXTURE ONLY\nEXIT_CODE=0\n")
            receipt = {"checker": checker["id"], "commit": checker["commit"],
                "module": policy["module"], "source_sha256": digests[
                    ai_handoff.FORMAL_ROOT + "/QIKVRTEffectAck/DeliveryReporting.lean"],
                "source_bundle_sha256": bundle, "export_or_olean_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "axioms": policy["expected_axioms"], "result": "PASS", "exit_code": 0,
                "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(), "artifact": artifact.name,
                "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "command": ["TEST_FIXTURE_ONLY"],
                "executed_commands": [], "execution": {"head": ai_handoff.git_value("rev-parse", "HEAD"),
                    "tree": ai_handoff.git_value("rev-parse", "HEAD^{tree}"),
                    "run_id": ai_handoff.os.environ.get("GITHUB_RUN_ID"),
                    "run_attempt": ai_handoff.os.environ.get("GITHUB_RUN_ATTEMPT")}}
            (directory / (checker["id"] + ".json")).write_text(json.dumps(receipt))

    def test_six_of_seven_receipts_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            directory = Path(tmp)
            self.receipt_fixtures(directory)
            (directory / "nanoda.json").unlink()
            with self.assertRaises(SystemExit):
                ai_handoff.formal_proof_gate(directory)

    def test_zero_exit_checker_panic_and_changed_payload_fail_closed(self):
        for defect in ("panic", "payload", "log", "nonpass", "foreign-commit"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as tmp, \
                    contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                directory = Path(tmp)
                self.receipt_fixtures(directory)
                path = directory / "own-kernel.json"
                receipt = json.loads(path.read_text())
                log = directory / "logs/own-kernel.log"
                if defect == "panic":
                    log.write_text("PANIC at checker\nEXIT_CODE=0\n")
                    receipt["log_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
                elif defect == "payload":
                    (directory / receipt["artifact"]).write_bytes(b"changed")
                elif defect == "log":
                    log.write_text("changed")
                elif defect == "nonpass":
                    receipt["result"] = "UNVERIFIED"
                else:
                    receipt["commit"] = "f" * 40
                path.write_text(json.dumps(receipt))
                with self.assertRaises(SystemExit):
                    ai_handoff.formal_proof_gate(directory)

    def test_change_class_without_native_proof_run_blocks_rest_merge(self):
        from tests import test_qikvrt_expected_head_promotion as promotion_fixtures
        from tools import qikvrt_expected_head_promotion as promotion
        case = promotion_fixtures.ExpectedHeadPromotionTests()
        snapshot = case.bound_snapshot()
        snapshot.update(draft=False, changed_paths=["tools/ai_handoff.py"])
        snapshot["review_observation"]["pr"]["changed_files"] = 1
        snapshot["review_observation"]["reviews"][0]["user"]["login"] = "ingolf-lohmann"
        snapshot["review_observation"]["statuses"] = [{"id": 8,
            "context": "QIKVRT required code-owner review", "state": "success"}]
        result = promotion.evaluate_conditional_rest_merge(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_MISSING")
        snapshot.pop("changed_paths")
        self.assertEqual(promotion.evaluate_conditional_rest_merge(snapshot)["first_blocker"],
                         "FORMAL_CHANGE_SCOPE_UNVERIFIED")

    def test_classification_is_closed_and_policy_has_seven_resolved_names(self):
        self.assertTrue(ai_handoff.formal_proof_required(["src/qikvrt_effect_ack_http_service.py"]))
        self.assertTrue(ai_handoff.formal_proof_required(["tools/qikvrt_pr_closure_engine.py"]))
        self.assertFalse(ai_handoff.formal_proof_required(["README.md"]))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ai_handoff.formal_proof_required(None)

    def test_replayed_observation_across_distinct_messages_is_blocking(self):
        case = self.fixture()
        first = case.communication()
        second = copy.deepcopy(first)
        second["id"] += "-different-message"
        case.receipt["communications"] = [first, second]
        case.rejected("CLIENT_COMMUNICATION_OBSERVATION_REPLAY")

    def test_actual_remote_guard_rejects_foreign_subject_and_non200(self):
        for field, value in (("http_status", 201), ("subject", {"head": "f" * 40}),
                             ("observation_id", "")):
            case = self.fixture()
            remote = case.communication()["evidence"]["remote_readback"]
            remote[field] = value
            case.rejected("CLIENT_COMMUNICATION_REMOTE_READBACK_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
