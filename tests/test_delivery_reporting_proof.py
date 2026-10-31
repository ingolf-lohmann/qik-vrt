#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Differential bridge from actual Lean output, including an executable mutant."""
import contextlib
import copy
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
