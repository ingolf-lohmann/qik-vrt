import tempfile
import unittest
from pathlib import Path
from runtime.emp.workflow_event import process


class WorkflowEventTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "events.db")

    def tearDown(self):
        self.tmp.cleanup()

    def payload(self, conclusion="failure", repo="ingolf-lohmann/qik-vrt"):
        return {"repository": {"full_name": repo},
                "workflow_run": {"id": 42872598486, "status": "completed",
                                 "conclusion": conclusion,
                                 "html_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/42872598486"}}

    def test_failure_requests_temdd(self):
        r = process(self.payload(), self.db)
        self.assertEqual(r["decision"]["next_action"], "TEMDD_DIAGNOSE")
        self.assertFalse(r["effect_ack_done"])

    def test_success_does_not_claim_effect(self):
        r = process(self.payload("success"), self.db)
        self.assertEqual(r["decision"]["state"], "BLOCKED")
        self.assertFalse(r["effect_ack_done"])

    def test_replay_deduplicated(self):
        process(self.payload(), self.db)
        self.assertTrue(process(self.payload(), self.db)["decision"]["duplicate"])

    def test_wrong_repository_rejected(self):
        with self.assertRaises(ValueError):
            process(self.payload(repo="other/repository"), self.db)

    def test_incomplete_run_rejected(self):
        p = self.payload()
        p["workflow_run"]["status"] = "in_progress"
        with self.assertRaises(ValueError):
            process(p, self.db)


if __name__ == "__main__":
    unittest.main()
