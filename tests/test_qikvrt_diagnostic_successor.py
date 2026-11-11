import json
import tempfile
import unittest
from pathlib import Path
from tools.qikvrt_client_continuation import decide
from tools.qikvrt_diagnostic_successor import materialize


class DiagnosticSuccessorTests(unittest.TestCase):
    def setUp(self):
        self.receipt = dict(
            schema="qikvrt_client_continuation_v1",
            repository="ingolf-lohmann/qik-vrt", work_unit_id="unit-1",
            writer_id="writer-1", head_sha="a" * 40,
            state="BLOCKED", blocker="CI", next_action="REPAIR",
            effect_ack_done=False,
        )

    def test_persist_idempotent_and_reenter_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            decision = decide(self.receipt)
            path = materialize(self.receipt, decision, directory)
            first = path.read_bytes()
            self.assertEqual(materialize(self.receipt, decision, directory), path)
            self.assertEqual(first, path.read_bytes())
            record = json.loads(first)
            self.assertEqual(record["writer_id"], "writer-1")
            self.assertEqual(record["next_action"], "READBACK")
            self.assertEqual(record["status"], "OPEN")
            self.assertFalse(record["effect_ack_done"])

    def test_external_gate_remains_nonexecuting(self):
        with tempfile.TemporaryDirectory() as directory:
            receipt = dict(self.receipt, blocker="WORKFLOW_APPROVAL")
            record = json.loads(materialize(receipt, decide(receipt), directory).read_text())
            self.assertIsNone(record["next_action"])

    def test_unresolved_predecessor_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            materialize(self.receipt, decide(self.receipt), directory)
            successor = dict(self.receipt, head_sha="b" * 40)
            with self.assertRaises(ValueError):
                materialize(successor, decide(successor), directory)

    def test_mismatched_identity_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            decision = dict(decide(self.receipt), writer_id="other")
            with self.assertRaises(ValueError):
                materialize(self.receipt, decision, directory)


if __name__ == "__main__":
    unittest.main()
