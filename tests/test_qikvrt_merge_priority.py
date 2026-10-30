# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
# Contribution: Claude (Anthropic), QIK-VRT Mirror node.
"""Owner merge priority (2026-10-30): order only, never a gate."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_pr_closure_engine as M

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/QIKVRT_MERGE_PRIORITY_V1.json"


def rows(*refs):
    return [{"number": n, "head_ref": ref, "created_at": f"2026-10-{n:02d}T00:00:00Z"}
            for n, ref in enumerate(refs, start=1)]


class MergePriorityTests(unittest.TestCase):
    def setUp(self):
        self.value = json.loads(POLICY.read_text(encoding="utf-8"))

    def write(self, value):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "policy.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_repository_policy_binds_the_owner_text_and_stays_order_only(self):
        decision = self.value["owner_decision"]
        self.assertEqual(hashlib.sha256(decision["text"].encode("utf-8")).hexdigest(), decision["sha256"])
        self.assertIn("Zenodo", decision["text"])
        self.assertIn("raumzeitterminal.de", decision["text"])
        self.assertEqual(self.value["scope"], "ORDER_ONLY")
        self.assertTrue(all(v is False for v in self.value["boundaries"].values()))
        self.assertEqual([c["id"] for c in self.value["priority_classes"]],
                         ["CI_BUILD_CHAIN_PERFORMANCE", "PUBLICATION_PATH_ZENODO_THEN_RAUMZEITTERMINAL"])
        self.assertIsNotNone(M.load_merge_priority(POLICY))

    def test_priority_classes_come_first_and_order_is_otherwise_stable(self):
        priority = M.load_merge_priority(POLICY)
        ordered = M.prioritized_pull_requests(
            rows("feat/a", "issue-agent/466", "publication/raumzeit", "fix/b", "ci/actions-node24", "release/r2"),
            priority)
        self.assertEqual([r["number"] for r in ordered], [3, 5, 6, 1, 2, 4])
        self.assertEqual(M.merge_priority_class({"head_ref": "ci/x"}, priority), "CI_BUILD_CHAIN_PERFORMANCE")
        self.assertEqual(M.merge_priority_class({"head_ref": "zenodo/x"}, priority),
                         "PUBLICATION_PATH_ZENODO_THEN_RAUMZEITTERMINAL")
        # A prefix must match a whole path segment, not a substring.
        self.assertIsNone(M.merge_priority_class({"head_ref": "cid/x"}, priority))
        self.assertIsNone(M.merge_priority_class({"head_ref": "feat/ci/x"}, priority))

    def test_absent_policy_keeps_historical_order(self):
        missing = ROOT / "policy/__absent_merge_priority__.json"
        self.assertIsNone(M.load_merge_priority(missing))
        original = rows("feat/a", "ci/b", "fix/c")
        self.assertEqual(M.prioritized_pull_requests(original, None), original)

    def test_tampered_or_widened_policy_fails_closed(self):
        tampered = copy.deepcopy(self.value)
        tampered["owner_decision"]["text"] += " und mergt alles"
        widened = copy.deepcopy(self.value)
        widened["boundaries"]["skips_or_relaxes_any_gate"] = True
        gate = copy.deepcopy(self.value)
        gate["scope"] = "MERGE_ADMISSION"
        bad_prefix = copy.deepcopy(self.value)
        bad_prefix["priority_classes"][0]["head_ref_prefixes"] = ["ci"]
        for name, value in (("tampered", tampered), ("widened", widened), ("gate", gate), ("prefix", bad_prefix)):
            with self.subTest(case=name), self.assertRaisesRegex(M.ClosureBlock, "MERGE_PRIORITY_POLICY_INVALID"):
                M.load_merge_priority(self.write(value))

    def test_select_step_reports_the_order_it_scanned(self):
        from tests.test_reciprocal_closure_step import FakeAPI
        api = FakeAPI()
        config = M.validate_policy(json.loads((ROOT / "state/autonomy/AUTONOMOUS_PR_CLOSURE_POLICY_V1.json").read_text()), api.repository)
        inventory = api.stable_inventory()
        plan = M.select_step(api, inventory, config, api.probe())
        self.assertEqual(plan["priority_order"], [row["number"] for row in inventory["pull_requests"]])


if __name__ == "__main__":
    unittest.main()
