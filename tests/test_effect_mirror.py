"""Regression tests for monotonic, fail-closed EAP mirror."""
import copy
import hashlib
import unittest
from scripts.check_effect_mirror import canonical, validate


def receipt(seq=1):
    return {
        "source_head": "a" * 40,
        "source_tree": "b" * 40,
        "writer_fence": "lease-1",
        "effect_id": "effect-" + str(seq),
        "effect_sha256": "c" * 64,
        "readback_sha256": "c" * 64,
        "sequence": seq,
        "previous_receipt_sha256": None,
        "emp_execution": "CONFIRMED",
        "eap_readback": "CONFIRMED",
        "effect_ack_done": True,
    }


class MirrorTests(unittest.TestCase):
    def test_genesis(self):
        self.assertEqual(validate(None, receipt()), (True, "GENESIS_CONFIRMED"))

    def test_unconfirmed_effect_cannot_become_one(self):
        r = receipt()
        r["eap_readback"] = "UNKNOWN"
        self.assertFalse(validate(None, r)[0])

    def test_missing_source_pin_fails_closed(self):
        r = receipt()
        r.pop("source_head")
        self.assertFalse(validate(None, r)[0])

    def test_mismatched_effect_fails_closed(self):
        r = receipt()
        r["readback_sha256"] = "d" * 64
        self.assertFalse(validate(None, r)[0])

    def test_successor_preserves_chain(self):
        first = receipt()
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        self.assertTrue(validate(first, second)[0])

    def test_rollback_and_fork_rejected(self):
        first = receipt()
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        second["sequence"] = 1
        self.assertFalse(validate(first, second)[0])
        second["sequence"] = 2
        second["previous_receipt_sha256"] = "0" * 64
        self.assertFalse(validate(first, second)[0])

    def test_source_drift_rejected(self):
        first = receipt()
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        second["source_head"] = "f" * 40
        self.assertEqual(validate(first, second)[1], "SOURCE_PIN_CHANGED")

    def test_fence_takeover_requires_handoff(self):
        first = receipt()
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        second["writer_fence"] = "lease-2"
        self.assertEqual(validate(first, second)[1], "UNVERIFIED_FENCE_HANDOFF")
        second["fence_handoff_receipt_sha256"] = second["previous_receipt_sha256"]
        self.assertTrue(validate(first, second)[0])

    def test_duplicate_effect_with_new_fence_rejected(self):
        first = receipt()
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        second["writer_fence"] = "lease-2"
        second["fence_handoff_receipt_sha256"] = second["previous_receipt_sha256"]
        second["effect_id"] = first["effect_id"]
        self.assertEqual(validate(first, second)[1], "DUPLICATE_EFFECT")

    def test_invalid_predecessor_sequence_rejected(self):
        first = receipt()
        first["sequence"] = 0
        second = receipt(2)
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        self.assertEqual(validate(first, second)[1], "INVALID_PREDECESSOR_SEQUENCE")

    def test_duplicate_effect_rejected(self):
        first = receipt()
        second = copy.deepcopy(first)
        second["sequence"] = 2
        second["previous_receipt_sha256"] = hashlib.sha256(canonical(first)).hexdigest()
        self.assertFalse(validate(first, second)[0])


if __name__ == "__main__":
    unittest.main()
