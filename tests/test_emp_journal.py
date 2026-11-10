import tempfile
import unittest
from pathlib import Path
from runtime.emp.journal import admit
from runtime.emp.transition import Objective


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "emp.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def test_persistent_deduplication(self):
        obj = Objective("obj", True, writer_epoch=2)
        first = admit(self.db, obj, "evt1")
        second = admit(self.db, obj, "evt1")
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["next_action"], second["next_action"])

    def test_stale_writer_rejected(self):
        admit(self.db, Objective("obj", True, writer_epoch=5), "evt1")
        with self.assertRaisesRegex(ValueError, "stale writer"):
            admit(self.db, Objective("obj", True, writer_epoch=4), "evt2")

    def test_ci_failure_is_durable(self):
        result = admit(self.db, Objective("obj", True, ci_failed=True), "evt1")
        self.assertEqual(result["next_action"], "TEMDD_DIAGNOSE")

    def test_unverified_never_succeeds(self):
        result = admit(self.db, Objective("obj", True, acceptance_observed=True), "evt1")
        self.assertNotEqual(result["state"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
