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

    def test_missing_writer_lease(self):
        self.assertFalse(validate(sample(writer_lease_id=""))[0])

if __name__ == "__main__":
    unittest.main()
