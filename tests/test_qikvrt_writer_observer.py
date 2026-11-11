import unittest
from tools.qikvrt_writer_observer import observe


class WriterObserverTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "repository": "ingolf-lohmann/qik-vrt",
            "writer_id": "writer-734", "work_unit_id": "pr-734",
            "head_sha": "a" * 40,
            "runs": [{"id": 10, "status": "in_progress", "conclusion": None}],
        }

    def test_active_writer_never_declared_done(self):
        result = observe(None, self.snapshot)
        self.assertEqual(result["state"], "RUNNING")
        self.assertEqual(result["next_action"], "READBACK")
        self.assertFalse(result["effect_ack_done"])

    def test_completed_ci_is_not_effect_ack(self):
        self.snapshot["runs"] = [{"id": 10, "status": "completed", "conclusion": "success"}]
        result = observe(None, self.snapshot)
        self.assertEqual(result["state"], "BLOCKED")
        self.assertEqual(result["next_action"], "RECONCILE_SUCCESSOR")
        self.assertFalse(result["effect_ack_done"])

    def test_action_required_does_not_terminate_work_unit(self):
        self.snapshot["runs"] = [{"id": 10, "status": "completed", "conclusion": "action_required"}]
        result = observe(None, self.snapshot)
        self.assertEqual(result["blocked_runs"][0]["conclusion"], "action_required")
        self.assertNotEqual(result["state"], "DONE")

    def test_same_writer_reentry(self):
        first = observe(None, self.snapshot)
        second = observe(first, self.snapshot)
        self.assertEqual(second["writer_id"], first["writer_id"])

    def test_wrong_writer_rejected(self):
        first = observe(None, self.snapshot)
        self.snapshot["writer_id"] = "other"
        with self.assertRaises(ValueError):
            observe(first, self.snapshot)

    def test_unverified_head_change_rejected(self):
        first = observe(None, self.snapshot)
        self.snapshot["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            observe(first, self.snapshot)

    def test_empty_evidence_rejected(self):
        self.snapshot["runs"] = []
        with self.assertRaises(ValueError):
            observe(None, self.snapshot)


if __name__ == "__main__":
    unittest.main()
