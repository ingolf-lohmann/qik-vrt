# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import unittest
from scripts.qikvrt_effect_ack_gate import STAGES, EVIDENCE_KEYS, validate


def chain():
    values = {
        "issue": "649", "claim_run": "1", "head": "abc", "tree": "def",
        "test_run": "2", "ci_run": "3", "approval": "4",
        "merge_commit": "5", "deployment_id": "6", "target": "host",
        "readback": "7", "effect_id": "8", "observation": "9",
    }
    return {"events": [
        dict(stage=stage, **{key: values[key] for key in EVIDENCE_KEYS[stage]},
             **({"effect_ack_done": True} if stage == "effect_ack" else {}))
        for stage in STAGES
    ]}


class EffectAckGateTest(unittest.TestCase):
    def test_complete_evidence(self):
        self.assertEqual(validate(chain()), (True, "effect_ack"))

    def test_claim_is_not_done(self):
        self.assertEqual(validate({"events": chain()["events"][:2]}), (True, "claimed"))

    def test_no_skipped_gates(self):
        record = chain()
        record["events"].pop(4)
        self.assertFalse(validate(record)[0])

    def test_subject_drift_blocked(self):
        record = chain()
        record["events"][4]["tree"] = "changed"
        self.assertFalse(validate(record)[0])

    def test_effect_not_acknowledged(self):
        record = chain()
        record["events"][-1]["effect_ack_done"] = False
        self.assertFalse(validate(record)[0])

    def test_missing_readback(self):
        record = chain()
        del record["events"][-2]["readback"]
        self.assertFalse(validate(record)[0])


if __name__ == "__main__":
    unittest.main()
