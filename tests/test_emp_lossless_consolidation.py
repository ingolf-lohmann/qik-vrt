import sqlite3
import tempfile
import unittest
from pathlib import Path
from runtime.emp.lossless_consolidation import append, replay, consolidate


class LosslessConsolidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "emp.sqlite")

    def tearDown(self):
        self.tmp.cleanup()

    def test_byte_exact_ordered_replay(self):
        original = [b"\x00\xff\n", b"", b"\xc3\xa4"]
        for n, payload in enumerate(original):
            append(self.db, "task", f"event-{n}", payload)
        result = replay(self.db, "task")
        self.assertEqual([bytes.fromhex(e["payload_hex"]) for e in result["events"]], original)
        self.assertEqual(consolidate(self.db, "task")["count"], 3)
        self.assertFalse(result["effect_ack_done"])

    def test_idempotent_duplicate(self):
        append(self.db, "task", "same", b"payload")
        self.assertTrue(append(self.db, "task", "same", b"payload")["duplicate"])
        self.assertEqual(replay(self.db, "task")["count"], 1)

    def test_conflicting_duplicate_rejected(self):
        append(self.db, "task", "same", b"a")
        with self.assertRaises(ValueError):
            append(self.db, "task", "same", b"b")

    def test_tamper_detected(self):
        append(self.db, "task", "a", b"original")
        with sqlite3.connect(self.db) as db:
            db.execute("UPDATE emp_lossless_events SET payload=? WHERE stream=?",
                       (b"tampered", "task"))
        with self.assertRaises(ValueError):
            replay(self.db, "task")

    def test_stream_isolation(self):
        append(self.db, "one", "a", b"1")
        append(self.db, "two", "a", b"2")
        self.assertEqual(bytes.fromhex(replay(self.db, "two")["events"][0]["payload_hex"]), b"2")


if __name__ == "__main__":
    unittest.main()
