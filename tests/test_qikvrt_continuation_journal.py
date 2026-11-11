# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest
from tools.qikvrt_continuation_journal import (
    SCHEMA, JournalError, encode, decode, receipt, verify_receipt,
)


def sample():
    return {"schema": SCHEMA, "events": [
        {"event_id": "observed", "status": "HOLD", "effect_ack_done": False}],
        "units": [{"id": "fix", "dedupe_key": "cause:manifest", "priority": "P0",
                   "state": "HOLD", "head": "a" * 40, "dependencies": []}],
        "continuation": {"next": "REGENERATE_MANIFEST", "ordinal": 3,
                         "evidence": ["sha256:abc"], "effect_ack_done": False}}


class JournalTests(unittest.TestCase):
    def test_lossless_roundtrip(self):
        value = sample()
        self.assertEqual(decode(encode(value)), value)

    def test_deterministic_bytes(self):
        a = sample()
        b = dict(reversed(list(a.items())))
        self.assertEqual(encode(a), encode(b))

    def test_digest_receipt(self):
        raw = encode(sample())
        self.assertEqual(verify_receipt(raw, receipt(raw)["sha256"]), sample())

    def test_mutation_rejected(self):
        raw = encode(sample())
        with self.assertRaises(JournalError):
            verify_receipt(raw + b" ", receipt(raw)["sha256"])

    def test_noncanonical_rejected(self):
        raw = encode(sample())
        with self.assertRaises(JournalError):
            decode(b" " + raw)

    def test_duplicate_key_rejected(self):
        with self.assertRaises(JournalError):
            decode(b'{"schema":"x","schema":"y"}')

    def test_duplicate_event_rejected(self):
        state = sample()
        state["events"].append(state["events"][0])
        with self.assertRaises(JournalError):
            decode(encode(state))

    def test_missing_dependency_rejected(self):
        state = sample()
        state["units"][0]["dependencies"] = ["missing"]
        with self.assertRaises(JournalError):
            decode(encode(state))

    def test_unacknowledged_effect_preserved(self):
        state = sample()
        restored = decode(encode(state))
        self.assertIs(restored["continuation"]["effect_ack_done"], False)
        self.assertEqual(restored["continuation"]["next"], "REGENERATE_MANIFEST")


if __name__ == "__main__":
    unittest.main()
