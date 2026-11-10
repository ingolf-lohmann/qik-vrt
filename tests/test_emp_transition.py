import unittest
from runtime.emp.transition import Objective, State, transition


class TransitionTests(unittest.TestCase):
    def test_missing_authorization(self):
        d = transition(Objective("a", False), "event")
        self.assertEqual(d.state, State.PROPOSED)

    def test_no_false_success_without_eap(self):
        d = transition(Objective("a", True, acceptance_observed=True), "event")
        self.assertNotEqual(d.state, State.VERIFIED)

    def test_verified(self):
        d = transition(Objective("a", True, True, True), "event")
        self.assertEqual(d.state, State.VERIFIED)

    def test_revocation(self):
        d = transition(Objective("a", True, True, True, revoked=True), "event")
        self.assertEqual(d.state, State.ABORTED)

    def test_stale_writer(self):
        d = transition(Objective("a", True, writer_epoch=1, event_epoch=2), "event")
        self.assertEqual(d.next_action, "REACQUIRE_FENCED_WRITER")

    def test_duplicate_event(self):
        d = transition(Objective("a", True, previous_event_id="event"), "event")
        self.assertEqual(d.next_action, "READBACK_ONLY")

    def test_failed_ci(self):
        d = transition(Objective("a", True, ci_failed=True), "event")
        self.assertEqual(d.next_action, "TEMDD_DIAGNOSE")

    def test_external_blocker(self):
        d = transition(Objective("a", True, external_blocker="review required"), "event")
        self.assertEqual(d.state, State.BLOCKED)

    def test_missing_id(self):
        d = transition(Objective("", True), "event")
        self.assertEqual(d.state, State.BLOCKED)


if __name__ == "__main__":
    unittest.main()
