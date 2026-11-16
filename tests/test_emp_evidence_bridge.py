import tempfile
import unittest
from pathlib import Path
from runtime.emp.evidence_bridge import submit
from runtime.emp.transition import Objective


class EvidenceBridgeTests(unittest.TestCase):
    def test_intent_outcome_replay_and_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "emp.sqlite")
            objective = Objective("integration", authorized=True, writer_epoch=1)
            first = submit(db, objective, "event-1")
            self.assertEqual(first["evidence"]["count"], 2)
            self.assertFalse(first["effect_ack_done"])
            second = submit(db, objective, "event-1")
            self.assertTrue(second["decision"]["duplicate"])
            self.assertEqual(second["evidence"]["count"], 2)

    def test_conflicting_event_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            db = str(Path(directory) / "emp.sqlite")
            submit(db, Objective("integration", authorized=True, writer_epoch=1), "event-1")
            with self.assertRaises(ValueError):
                submit(db, Objective("integration", authorized=False, writer_epoch=1), "event-1")


if __name__ == "__main__":
    unittest.main()
