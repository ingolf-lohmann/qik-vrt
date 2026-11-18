# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest

from tools.qikvrt_fallback_reentry import decide_reentry


class FallbackReentryTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(continuation_required=True, active_writer=False,
                          lease_valid=True, fencing_verified=True,
                          checkpoint_verified=True, exact_head_verified=True,
                          consumer_authorized=True)

    def test_admitted_reentry(self):
        self.assertEqual(decide_reentry(self.state)["decision"],
                         "REENTER_EXISTING_CONSUMER")

    def test_existing_writer_not_preempted(self):
        self.state["active_writer"] = True
        self.assertEqual(decide_reentry(self.state)["decision"],
                         "OBSERVE_EXISTING_WRITER")

    def test_every_missing_gate_blocks(self):
        for gate in ("lease_valid", "fencing_verified", "checkpoint_verified",
                     "exact_head_verified", "consumer_authorized"):
            with self.subTest(gate=gate):
                value = dict(self.state, **{gate: False})
                self.assertEqual(decide_reentry(value)["decision"], "RECOVERY_REQUIRED")

    def test_unknown_is_fail_closed(self):
        del self.state["lease_valid"]
        self.assertEqual(decide_reentry(self.state)["decision"], "HOLD")

    def test_no_false_effect_ack(self):
        for active in (False, True):
            self.assertFalse(decide_reentry(dict(self.state, active_writer=active))["effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
