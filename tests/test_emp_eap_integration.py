"""EMP/EAP integration proof obligations for the Trusted Mesh reference path.

This is an executable local conformance fixture, not a claim of production EAP.
"""
import hashlib
import tempfile
import unittest
from pathlib import Path

from runtime.emp.journal import admit
from runtime.emp.reference_executor import execute_file_effect
from runtime.emp.transition import Objective


def independent_eap_fixture(root, relative_path, expected_sha256):
    """Independent readback predicate; explicitly NOT the production EAP."""
    target = (Path(root) / relative_path).resolve()
    if not target.is_relative_to(Path(root).resolve()) or not target.is_file():
        return False
    return hashlib.sha256(target.read_bytes()).hexdigest() == expected_sha256


class EmpEapIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = str(self.root / "journal.sqlite")
        self.payload = b"qik-vrt-emp-eap-integration-v1"
        self.digest = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def test_authorized_effect_requires_separate_ack(self):
        obj = Objective("effect-1", authorized=True, writer_epoch=1)
        decision = admit(self.db, obj, "event-1")
        self.assertEqual(decision["next_action"], "DISPATCH_AUTHORIZED_STEP")
        result = execute_file_effect(
            str(self.root), "mesh/effect.bin", self.payload,
            authorized=True, expected_sha256=self.digest)
        self.assertTrue(result["observed"])
        self.assertFalse(result["effect_ack_done"])
        self.assertNotEqual(
            admit(self.db, Objective("effect-1", True, acceptance_observed=True,
                                     writer_epoch=1), "event-2")["state"], "VERIFIED")
        ack = independent_eap_fixture(self.root, "mesh/effect.bin", self.digest)
        self.assertTrue(ack)
        self.assertEqual(
            admit(self.db, Objective("effect-1", True, acceptance_observed=True,
                                     eap_verified=ack, writer_epoch=1),
                  "event-3")["state"], "VERIFIED")

    def test_tamper_blocks_ack(self):
        execute_file_effect(str(self.root), "mesh/effect.bin", self.payload,
                            authorized=True, expected_sha256=self.digest)
        (self.root / "mesh/effect.bin").write_bytes(b"tampered")
        self.assertFalse(independent_eap_fixture(self.root, "mesh/effect.bin", self.digest))
        self.assertNotEqual(
            admit(self.db, Objective("effect-2", True, acceptance_observed=True,
                                     eap_verified=False), "event-1")["state"], "VERIFIED")

    def test_unauthorized_effect_has_no_file(self):
        with self.assertRaises(PermissionError):
            execute_file_effect(str(self.root), "mesh/effect.bin", self.payload,
                                authorized=False, expected_sha256=self.digest)
        self.assertFalse((self.root / "mesh/effect.bin").exists())

    def test_replay_does_not_redispatch(self):
        obj = Objective("effect-3", True, writer_epoch=1)
        admit(self.db, obj, "event-1")
        replay = admit(self.db, obj, "event-1")
        self.assertTrue(replay["duplicate"])


if __name__ == "__main__":
    unittest.main()
