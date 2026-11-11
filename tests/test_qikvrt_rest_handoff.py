# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Regression tests for REST handoff and followable writer journal."""
import unittest
from tools.qikvrt_rest_handoff import accepted_handoff, next_observation


class RestHandoffTests(unittest.TestCase):
    def setUp(self):
        self.receipt = accepted_handoff(
            request_id="req-1", head="a" * 40, tree="b" * 40,
            observation_url="https://api.github.com/repos/ingolf-lohmann/qik-vrt/actions/runs/1",
            journal_cursor="0")

    def event(self, **changes):
        result = dict(request_id="req-1", head="a" * 40, tree="b" * 40,
                      state="RUNNING", sequence=1, journal_cursor="1")
        result.update(changes)
        return result

    def test_acceptance_is_not_execution(self):
        self.assertEqual(self.receipt["state"], "ACCEPTED")
        self.assertFalse(self.receipt["effect_ack_done"])
        self.assertEqual(next_observation(self.receipt, None), self.receipt)

    def test_follow_worker_and_keep_cursor(self):
        running = next_observation(self.receipt, self.event())
        self.assertEqual(running["journal_cursor"], "1")
        self.assertEqual(next_observation(running, None), running)
        done = next_observation(running, self.event(
            sequence=2, journal_cursor="2", state="COMPLETED",
            independent_effect_ack=True))
        self.assertTrue(done["effect_ack_done"])

    def test_reject_false_completion_replay_and_cross_head(self):
        for event in (self.event(state="COMPLETED"),
                      self.event(head="c" * 40),
                      self.event(sequence=0),
                      self.event(journal_cursor="")):
            with self.subTest(event=event), self.assertRaises(ValueError):
                next_observation(self.receipt, event)


if __name__ == "__main__":
    unittest.main()
