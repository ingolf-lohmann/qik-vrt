# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
from tools.qikvrt_devops_ring import plan

HEAD = "a" * 40
class DevOpsRingTests(unittest.TestCase):
    def observation(self, runs=None, work=None):
        return {"repository": "ingolf-lohmann/qik-vrt", "head": HEAD,
                "runs": [] if runs is None else runs,
                "work": [] if work is None else work}

    def test_idle_is_not_effect(self):
        r = plan(self.observation())
        self.assertEqual(r["state"], "IDLE")
        self.assertFalse(r["effect_ack_done"])
        self.assertFalse(r["dispatch_executed"])

    def test_failure_does_not_hide_independent_work(self):
        r = plan(self.observation(
            [{"id": 5, "status": "completed", "conclusion": "failure"}],
            [{"id": 9, "state": "open"}]))
        self.assertEqual(len(r["tasks"]), 2)
        self.assertEqual({t["kind"] for t in r["tasks"]},
                         {"TEMDD_DIAGNOSE", "CONTINUATION_CANDIDATE"})

    def test_permutation_is_lossless(self):
        runs = [{"id": 2, "status": "completed", "conclusion": "success"},
                {"id": 1, "status": "in_progress", "conclusion": None}]
        a = plan(self.observation(runs))
        b = plan(self.observation(list(reversed(runs))))
        self.assertEqual(a["semantic_fingerprint"], b["semantic_fingerprint"])
        self.assertEqual(a["evidence_count"], 2)

    def test_duplicate_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_IDENTITY"):
            plan(self.observation([{"id": 1}, {"id": 1}]))

    def test_missing_inventory_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_INVENTORY"):
            plan({"repository": "ingolf-lohmann/qik-vrt", "head": HEAD, "runs": []})

    def test_replay_does_not_renew_progress(self):
        a = plan(self.observation([{"id": 1, "status": "completed", "conclusion": "success"}]))
        b = plan(self.observation([{"id": 1, "status": "completed", "conclusion": "success"}]), a)
        self.assertFalse(b["changed"])

if __name__ == "__main__":
    unittest.main()
