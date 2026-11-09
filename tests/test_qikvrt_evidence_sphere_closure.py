"""Offline regressions for fail-closed evidence sphere closure."""
import copy
import json
import unittest
from pathlib import Path

from tools.qikvrt_evidence_sphere_closure import verify

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/notes/QIKVRT_MESH_EVIDENCE_SPHERE_MONOTONIC_V1.json"


class EvidenceSphereClosureTests(unittest.TestCase):
    def setUp(self):
        self.sphere = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_repository_seed_is_structurally_closed(self):
        result = verify(self.sphere)
        self.assertEqual(result["status"], "PASS_OFFLINE_STRUCTURE_ONLY", result)
        self.assertFalse(result["external_proof_admitted"])
        self.assertFalse(result["production_effect_ack_done"])

    def test_missing_record_is_rejected(self):
        broken = copy.deepcopy(self.sphere)
        broken["zenodo_core"]["records"].pop()
        self.assertEqual(verify(broken)["status"], "FAIL_CLOSED")

    def test_reference_cannot_become_unverified_proof(self):
        broken = copy.deepcopy(self.sphere)
        broken["edges"][0]["evidence_semantics"] = "ADMITTED_LOGICAL_DERIVATION"
        self.assertEqual(verify(broken)["status"], "FAIL_CLOSED")

    def test_missing_monotonicity_rule_is_rejected(self):
        broken = copy.deepcopy(self.sphere)
        broken["rules"]["existing_nodes_must_not_be_deleted"] = False
        self.assertEqual(verify(broken)["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
