# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded model tests; these fixtures are not live Mesh completion evidence."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tools.qikvrt_expected_head_promotion import evaluate_closure


class ReciprocalClosureTests(unittest.TestCase):
    def snapshot(self):
        repos = {"Goldkelch/qik-vrt": ("AUTHORITY", "a" * 40),
                 "ingolf-lohmann/qik-vrt": ("MIRROR", "b" * 40)}
        nodes = []
        for repo, (role, head) in repos.items():
            branch = {"name": "main", "sha": head, "reachable_from_main": True,
                      "verified_against_main": head, "object_closure_verified": True}
            quality = {k: True for k in (
                "all_applicable_gates_green", "native_code_owner_rule_enforced",
                "independent_exact_head_approval", "provenance_rights_security_verified",
                "no_unaccepted_known_defects", "fresh_main_readback")}
            quality.update(head_sha=head, tree_sha="c" * 40,
                           profile_id="fixture-quality", profile_version=1)
            nodes.append({"repository": repo, "role": role, "main_sha": head,
                          "main_tree": "c" * 40, "accessible": True,
                          "observed_utc": "2026-10-01T13:00:00Z",
                          "inventory_complete": True, "inventory_stable": True,
                          "origin_verified": True, "initial_branches": [branch],
                          "final_branches": [copy.deepcopy(branch)],
                          "initial_pull_requests": [], "final_open_pull_requests": [],
                          "quality": quality})
        witnesses = []
        for source, target in (tuple(repos), tuple(reversed(repos))):
            witnesses.append({"source": source, "target": target,
                              "source_head": repos[source][1], "target_before": "d" * 40,
                              "target_after": repos[target][1], "authenticated_executor": True,
                              "accepted_scoped_effect_ack_chain": True,
                              "post_effect_readback": True, "lossless_history_verified": True})
        public = [{"kind": kind, "url": "https://example.org/fixture/" + kind,
                   "sha256": "e" * 64, "public_byte_readback_verified": True,
                   "subject_heads": {k: v[1] for k, v in repos.items()},
                   "document": "draft-lohmann-qikvrt-effect-ack-03"}
                  for kind in ("REPOSITORY", "IETF", "ZENODO")]
        return {"schema": "qikvrt_reciprocal_devops_closure_snapshot_v1",
                "evaluated_utc": "2026-10-01T13:01:00Z", "max_observation_age_seconds": 120,
                "nodes": nodes, "reciprocal_witnesses": witnesses, "public_evidence": public}

    def blocked(self, s, blocker):
        result = evaluate_closure(s)
        self.assertEqual(result["state"], "BLOCK")
        self.assertIn(blocker, result["first_blocker"])
        self.assertFalse(result["ordinary_release"])

    def test_complete_model_is_acceptance_ready_without_effect_permission(self):
        result = evaluate_closure(self.snapshot())
        self.assertEqual(result["state"], "CLOSURE_READY_FOR_ACCEPTANCE")
        self.assertFalse(result["ordinary_release"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_inaccessible_authority_and_alias_cannot_satisfy_pair(self):
        s = self.snapshot(); s["nodes"][0]["accessible"] = False
        self.blocked(s, "NODE_ACCESS_NOT_ESTABLISHED")
        s = self.snapshot(); s["nodes"][0]["repository"] = s["nodes"][1]["repository"]
        self.blocked(s, "DUPLICATE_INVENTORY_ID")

    def test_truncation_and_concurrent_inventory_drift_block(self):
        for key, blocker in (("inventory_complete", "INVENTORY_INCOMPLETE"),
                             ("inventory_stable", "INVENTORY_DRIFT")):
            s = self.snapshot(); s["nodes"][0][key] = False
            self.blocked(s, blocker)

    def test_deleted_initial_branch_must_still_have_retained_history(self):
        s = self.snapshot(); n = s["nodes"][0]
        n["initial_branches"].append({"name": "lost", "sha": "f" * 40,
            "reachable_from_main": False, "verified_against_main": n["main_sha"],
            "object_closure_verified": True})
        self.blocked(s, "BRANCH_HISTORY_NOT_RETAINED")

    def test_closed_unmerged_or_squashed_pr_does_not_satisfy_lossless_merge(self):
        for flag in ("merged", "head_reachable_from_main", "merge_reachable_from_main"):
            s = self.snapshot(); n = s["nodes"][0]
            pr = {"number": 7, "head_sha": "f" * 40, "merge_commit_sha": "e" * 40,
                  "merged": True, "head_reachable_from_main": True,
                  "merge_reachable_from_main": True, "verified_against_main": n["main_sha"]}
            pr[flag] = False; n["initial_pull_requests"] = [pr]
            self.blocked(s, "PR_NOT_LOSSLESSLY_MERGED")

    def test_new_open_pr_prevents_final_acceptance(self):
        s = self.snapshot(); s["nodes"][1]["final_open_pull_requests"] = [99]
        self.blocked(s, "OPEN_PULL_REQUESTS_REMAIN")

    def test_empty_initial_inventory_cannot_claim_lossless_closure(self):
        s = self.snapshot(); s["nodes"][0]["initial_branches"] = []
        self.blocked(s, "INITIAL_MAIN_BINDING_MISSING")

    def test_quality_and_main_subject_drift_block(self):
        for key in ("head_sha", "tree_sha"):
            s = self.snapshot(); s["nodes"][0]["quality"][key] = "f" * 40
            self.blocked(s, "QUALITY_SUBJECT_DRIFT")

    def test_each_required_quality_check_remains_mandatory(self):
        for key in ("all_applicable_gates_green", "native_code_owner_rule_enforced",
                    "independent_exact_head_approval", "provenance_rights_security_verified",
                    "no_unaccepted_known_defects", "fresh_main_readback"):
            s = self.snapshot(); s["nodes"][0]["quality"][key] = False
            self.blocked(s, "QUALITY_NOT_ESTABLISHED")

    def test_stale_future_and_replayed_direction_evidence_block(self):
        for observed in ("2026-10-01T12:00:00Z", "2026-10-01T14:00:00Z"):
            s = self.snapshot(); s["nodes"][0]["observed_utc"] = observed
            self.blocked(s, "STALE_OR_FUTURE_OBSERVATION")
        s = self.snapshot(); s["reciprocal_witnesses"][0]["target_after"] = "f" * 40
        self.blocked(s, "DIRECTION_SUBJECT_DRIFT")

    def test_one_direction_and_duplicated_witness_block(self):
        s = self.snapshot(); s["reciprocal_witnesses"].pop()
        self.blocked(s, "BOTH_DIRECTIONS_REQUIRED")
        s = self.snapshot(); s["reciprocal_witnesses"][1] = s["reciprocal_witnesses"][0]
        self.blocked(s, "DUPLICATE_DIRECTION")

    def test_unverified_publication_or_old_subject_blocks(self):
        s = self.snapshot(); s["public_evidence"][2]["public_byte_readback_verified"] = False
        self.blocked(s, "PUBLIC_BYTE_READBACK_UNVERIFIED")
        s = self.snapshot(); s["public_evidence"][2]["subject_heads"]["Goldkelch/qik-vrt"] = "f" * 40
        self.blocked(s, "PUBLIC_EVIDENCE_SUBJECT_DRIFT")

    def test_unknown_version_and_truthy_strings_block(self):
        s = self.snapshot(); s["schema"] = "v2"
        self.blocked(s, "UNSUPPORTED_CLOSURE_VERSION")
        s = self.snapshot(); s["nodes"][0]["origin_verified"] = "true"
        self.blocked(s, "ORIGIN_NOT_VERIFIED")

    def test_record_order_does_not_change_acceptance(self):
        s = self.snapshot(); s["nodes"].reverse(); s["public_evidence"].reverse()
        self.assertEqual(evaluate_closure(s)["state"], "CLOSURE_READY_FOR_ACCEPTANCE")

    def test_duplicate_json_members_fail_in_closure_cli_schema(self):
        p = subprocess.run([sys.executable, str(Path(__file__).parents[1] /
            "tools/qikvrt_expected_head_promotion.py"), "evaluate-closure"],
            input='{"schema":"v1","schema":"v2"}', text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)["schema"],
                         "qikvrt_reciprocal_devops_closure_decision_v1")
        self.assertIn("duplicate snapshot member", json.loads(p.stdout)["detail"])

    def test_non_finite_json_is_rejected(self):
        p = subprocess.run([sys.executable, str(Path(__file__).parents[1] /
            "tools/qikvrt_expected_head_promotion.py"), "evaluate-closure"],
            input='{"metadata":NaN}', text=True, capture_output=True)
        self.assertEqual(p.returncode, 2)
        self.assertIn("non-finite snapshot number", json.loads(p.stdout)["detail"])
