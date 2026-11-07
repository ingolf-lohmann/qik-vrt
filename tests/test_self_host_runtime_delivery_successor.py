#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Negative source/carrier tests; neither load nor accept a production effect."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from tools.qikvrt_runtime_delivery_successor import select_candidate, RECORD

ROOT = Path(__file__).resolve().parents[1]

class RuntimeDeliverySuccessorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "runtime/self-host").mkdir(parents=True)
        self.original_package = json.loads((ROOT / "runtime/self-host/PACKAGE.json").read_bytes())
        self.original_receipt = json.loads((ROOT / RECORD).read_bytes())
        self.package = copy.deepcopy(self.original_package)
        self.receipt = copy.deepcopy(self.original_receipt)
        self.write()

    def write(self):
        (self.root / "runtime/self-host/PACKAGE.json").write_text(
            json.dumps(self.package), encoding="utf-8")
        (self.root / RECORD).write_text(json.dumps(self.receipt), encoding="utf-8")

    def test_candidate_is_not_a_previous_pass_or_product_effect(self):
        candidate = select_candidate(self.root)
        self.assertNotEqual(candidate["artifact_id"],
                            self.original_package["runtime_delivery_baseline"]["artifact_id"])
        self.assertIs(self.receipt["claims"]["effect_ack_done"], False)
        self.assertIs(self.receipt["claims"]["product_delivery_verified"], False)

    def test_mutations_reject_identity_and_claim_elevation(self):
        for name, field, key, value in (
            ("baseline", "package", "artifact_id", 7),
            ("previous_bytes", "predecessor", "artifact_sha256", "0" * 64),
            ("artifact_alias", "candidate", "artifact_id",
             self.original_package["runtime_delivery_baseline"]["artifact_id"]),
            ("wrong_tree", "candidate", "source_tree", "f" * 40),
            ("same_digest", "candidate", "delivery_sha256",
             self.original_package["runtime_delivery_baseline"]["delivery_sha256"]),
            ("forged_review", "claims", "independent_review_verified", True),
            ("forged_effect", "claims", "effect_ack_done", True),
            ("forged_pass", "claims", "predecessor_pass_transferred", True),
            ("forged_source", "evidence", "source_run_url",
             "https://github.com/example/other"),
            ("extra_field", "candidate", "approved", True),
        ):
            with self.subTest(name=name):
                self.package = copy.deepcopy(self.original_package)
                self.receipt = copy.deepcopy(self.original_receipt)
                target = (self.package["runtime_delivery_baseline"] if field == "package" else
                          self.receipt["historical_predecessor"] if field == "predecessor" else
                          self.receipt[field])
                target[key] = value
                self.write()
                with self.assertRaises(ValueError):
                    select_candidate(self.root)

if __name__ == "__main__":
    unittest.main()
