"""Negative regression tests for fail-closed COMMIT effect admission."""
import unittest
from scripts.commit_effect_gate import validate

BASE = {
    "intent_id": "intent-749",
    "principal_authorization": "principal-approved",
    "authority_repo": "ingolf-lohmann/qik-vrt",
    "exact_head": "a" * 40,
    "events": [
        {"state": "RECEIVED"}, {"state": "PERSISTED"},
        {"state": "ADMITTED"}, {"state": "EXECUTING"},
        {"state": "EFFECT_VERIFIED"},
    ],
    "commit_sha": "b" * 40,
    "readback_sha": "b" * 40,
    "eap_receipt_id": "eap-749",
    "writer_lease_id": "lease-749",
}

def sample(**changes):
    return {**BASE, "events": [dict(x) for x in BASE["events"]], **changes}

class CommitEffectGateTests(unittest.TestCase):
    def test_valid_evidence(self):
        self.assertEqual(validate(sample()), (True, "effect_verified"))

    def test_chat_only_no_events(self):
        self.assertFalse(validate(sample(events=[]))[0])

    def test_read_only_never_completes(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "PERSISTED"}]))[0])

    def test_missing_persistence_rejected(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "ADMITTED"}]))[0])

    def test_missing_authorization(self):
        self.assertFalse(validate(sample(principal_authorization=""))[0])

    def test_missing_eap_receipt(self):
        self.assertFalse(validate(sample(eap_receipt_id=""))[0])

    def test_commit_readback_mismatch(self):
        self.assertFalse(validate(sample(readback_sha="c" * 40))[0])

    def test_wrong_authority(self):
        self.assertFalse(validate(sample(authority_repo="elsewhere/repo"))[0])

    def test_blocked_never_completes(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "PERSISTED"}, {"state": "BLOCKED"}]))[0])

    def test_repair_required_never_completes(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "PERSISTED"}, {"state": "REPAIR_REQUIRED"}]))[0])

    def test_duplicate_success_event_rejected(self):
        self.assertFalse(validate(sample(events=BASE["events"] + [{"state": "EFFECT_VERIFIED"}]))[0])

    def test_missing_intent_id(self):
        self.assertFalse(validate(sample(intent_id=""))[0])

    def test_missing_exact_head(self):
        self.assertFalse(validate(sample(exact_head=""))[0])

    def test_missing_commit_sha(self):
        self.assertFalse(validate(sample(commit_sha=""))[0])

    def test_missing_readback_sha(self):
        self.assertFalse(validate(sample(readback_sha=""))[0])

    def test_invalid_event_state(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "DONE"}]))[0])

    def test_missing_received_event(self):
        self.assertFalse(validate(sample(events=[{"state": "PERSISTED"}]))[0])

    def test_executing_without_admission(self):
        self.assertFalse(validate(sample(events=[{"state": "RECEIVED"}, {"state": "PERSISTED"}, {"state": "EXECUTING"}]))[0])

    def test_malformed_exact_head(self):
        self.assertEqual(validate(sample(exact_head="not-a-sha"))[1], "invalid_commit_identity")

    def test_malformed_commit_sha(self):
        self.assertEqual(validate(sample(commit_sha="not-a-sha"))[1], "invalid_commit_identity")

    def test_malformed_readback_sha(self):
        self.assertEqual(validate(sample(readback_sha="not-a-sha"))[1], "invalid_commit_identity")

    def test_missing_writer_lease(self):
        self.assertFalse(validate(sample(writer_lease_id=""))[0])

class CommitObservationContractTests(unittest.TestCase):
    """Prevent regression to chat-turn completion of an open acceptance."""

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        cls.contract = (root / "docs/commit-execution-evidence-contract-749.md").read_text(encoding="utf-8")

    def test_chat_turn_is_not_acceptance_completion(self):
        self.assertIn("end of a chat turn", self.contract)
        self.assertIn("not termination", self.contract)

    def test_independent_productive_eap_is_required(self):
        self.assertIn("independently read-back productive EAP acknowledgment", self.contract)

    def test_unknown_gate_requires_continuation(self):
        self.assertIn("CONTINUATION_REQUIRED", self.contract)
        self.assertIn("UNKNOWN", self.contract)

    def test_observer_is_read_only(self):
        self.assertIn("must not itself dispatch CI, merge, deploy", self.contract)

    def test_no_delta_does_not_terminate_observation(self):
        self.assertIn("NO_DELTA observation", self.contract)
        self.assertIn("MUST NOT suppress subsequent authorized checks", self.contract)

    def test_duplicate_blockers_do_not_require_new_principal_decision(self):
        self.assertIn("do not repeatedly request Principal confirmation", self.contract)

    def test_failed_new_regression_never_counts_as_pass(self):
        self.assertIn("never a PASS", self.contract)


if __name__ == "__main__":
    unittest.main()
