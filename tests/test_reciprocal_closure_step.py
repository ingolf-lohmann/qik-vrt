# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Transport-bound negative controls; fake GitHub is not live closure proof."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from tools import qikvrt_pr_closure_engine as M
from src.qikvrt_effect_ack import ResponsibilityProtocol, verify_protocol_chain
from tests import test_qikvrt_pr_closure_engine as fixtures


REPO = "example/qik-vrt"
BASE, HEAD, TREE = "a" * 40, "b" * 40, "c" * 40


class FakeAPI(M.GitHubAPI):
    def __init__(self):
        super().__init__(REPO, "fixture-not-a-secret")
        fixture = fixtures.ClosureEngineTests()
        self.pr = fixture.pr()
        self.pr.update(created_at="2026-10-01T00:00:00Z", updated_at="2026-10-01T00:00:00Z",
                       requested_reviewers=[], merged=False)
        self.observed = fixture.obs(reviews=[])
        for run in self.observed["check_runs"]:
            run["head_sha"] = HEAD
        self.branches = [{"name": "main", "commit": {"sha": BASE}},
                         {"name": "feature", "commit": {"sha": HEAD}}]
        self.calls = []
        self.mutations = []
        self.compare = "ahead"
        self.permission = True
        self.timeout_after_apply = False
        self.discard_effect = False
        self.lose_tip = False
        self.bad_readback = False
        self.missing_repo = False

    def request(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        prefix = self.repo_path("")
        if path == "/user":
            return {"login": "owner"}
        if path == prefix:
            if self.missing_repo:
                raise M.ClosureBlock("HTTP_404:GET:" + path)
            return {"full_name": REPO, "archived": False, "permissions": {"push": self.permission}}
        suffix = path[len(prefix):]
        parsed = urlsplit(suffix)
        query = parse_qs(parsed.query)
        page = int(query.get("page", [1])[0])
        if method != "GET":
            self.mutations.append((method, path, payload))
            if parsed.path.endswith("requested_reviewers") and not self.discard_effect:
                self.pr["requested_reviewers"] = [{"login": "Goldkelch"}]
                self.pr["updated_at"] = "2026-10-01T00:01:00Z"
            elif parsed.path.endswith("update-branch") and not self.discard_effect:
                self.pr["head"]["sha"] = "d" * 40
                self.branches[1]["commit"]["sha"] = "d" * 40
            if self.lose_tip:
                self.branches[1]["commit"]["sha"] = "e" * 40
            if self.bad_readback:
                self.pr["head"]["sha"] = "e" * 40
            if self.timeout_after_apply:
                raise M.ClosureBlock("TRANSPORT_UNCERTAIN")
            return {"fixture_transport_ack": True}
        if parsed.path == "/branches/main":
            return copy.deepcopy(self.branches[0])
        if parsed.path == "/collaborators/Goldkelch/permission":
            return {"permission": "write", "user": {"login": "Goldkelch"}}
        if parsed.path == "/collaborators/Goldkelch":
            return None
        if parsed.path == "/branches":
            return copy.deepcopy(self.branches[(page - 1) * 100:page * 100])
        if parsed.path.startswith("/git/commits/"):
            return {"tree": {"sha": TREE}}
        if parsed.path == "/pulls":
            return [copy.deepcopy(self.pr)] if page == 1 else []
        if parsed.path == "/pulls/7":
            return copy.deepcopy(self.pr)
        if parsed.path.startswith("/compare/"):
            pair = parsed.path.split("/")[-1].split("...")
            old, new = pair
            return {"status": self.compare if old == BASE and new == HEAD else ("diverged" if new == "e" * 40 else "ahead"),
                    "merge_base_commit": {"sha": old}}
        if parsed.path.endswith("check-runs"):
            rows = self.observed["check_runs"]
            return {"total_count": len(rows), "check_runs": copy.deepcopy(rows[(page - 1) * 100:page * 100])}
        if parsed.path.endswith("statuses"):
            return copy.deepcopy(self.observed["statuses"]) if page == 1 else []
        if parsed.path.endswith("reviews"):
            return copy.deepcopy(self.observed["reviews"]) if page == 1 else []
        raise AssertionError((method, path, payload))


class ReciprocalStepTests(unittest.TestCase):
    def policy(self):
        return fixtures.ClosureEngineTests().policy()

    def run_step(self, api, path, **kw):
        return M.execute(api, self.policy(), apply=True, journal_dir=Path(path), **kw)

    def test_one_authenticated_effect_full_recensus_bound_continue_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            api = FakeAPI(); r = self.run_step(api, d)
            self.assertEqual(r["state"], "STEP_EFFECT_VERIFIED_CONTINUE")
            self.assertEqual(len(api.mutations), 1)
            self.assertEqual(r["selected_action"]["action"], "REQUEST_REVIEW")
            self.assertEqual(r["post_effect_readback"]["original_branch_tips_preserved"], 2)
            self.assertFalse(any(r["completion_claims"].values()))
            protocols = [ResponsibilityProtocol.from_dict(x) for x in r["effect_ack_chain"]]
            verify_protocol_chain(protocols)
            self.assertTrue(all(p.state.value == "EFFECT_ACK_CONTINUE" for p in protocols))
            for payload, p in zip(r["protocol_payloads"], protocols):
                self.assertEqual(p.input_hash, "sha256:" + M.digest(payload["intent"]))
            self.assertEqual(r["receipt_sha256"], M.digest({k: v for k, v in r.items() if k != "receipt_sha256"}))

    def test_dry_plan_never_mutates_or_requires_done_acceptance(self):
        api = FakeAPI(); r = M.execute(api, self.policy(), apply=False)
        self.assertEqual(r["state"], "STEP_PREPARED")
        self.assertEqual(api.mutations, [])
        self.assertEqual(r["closure_evaluation"]["state"], "BLOCK")

    def test_missing_or_read_only_capability_is_exact_blocker(self):
        for missing in (False, True):
            api = FakeAPI(); api.missing_repo = missing; api.permission = False
            with tempfile.TemporaryDirectory() as d:
                r = self.run_step(api, d)
            self.assertEqual(r["state"], "BLOCK")
            self.assertIn("HTTP_404" if missing else "REPOSITORY_WRITE_CAPABILITY_UNAVAILABLE", r["first_blocker"])
            self.assertEqual(api.mutations, [])

    def test_forged_acceptance_readiness_never_grants_capability(self):
        from tests.test_reciprocal_devops_closure import ReciprocalClosureTests
        api = FakeAPI(); api.permission = False
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d, closure_snapshot=ReciprocalClosureTests().snapshot())
        self.assertEqual(r["closure_evaluation"]["state"], "CLOSURE_READY_FOR_ACCEPTANCE")
        self.assertEqual(api.mutations, [])
        self.assertFalse(r["completion_claims"]["EFFECT_ACK_DONE"])

    def test_inventory_drift_and_truncation_never_enable_mutation(self):
        api = FakeAPI(); original = api.inventory
        count = 0
        def inventory():
            nonlocal count
            count += 1
            result = original()
            if count == 2:
                result["branches"].append({"name": "concurrent", "sha": HEAD})
            return result
        api.inventory = inventory
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertIn("INVENTORY_DRIFT", r["first_blocker"])
        self.assertEqual(api.mutations, [])
        api = FakeAPI(); api.request = lambda *a, **k: [{"name": "x"}] * 100
        with self.assertRaisesRegex(M.ClosureBlock, "INVENTORY_TRUNCATED"):
            api.collection("/branches?")

    def test_all_pages_are_captured_including_exact_multiple(self):
        api = FakeAPI()
        api.branches.extend({"name": str(i), "commit": {"sha": HEAD}} for i in range(98))
        r = api.stable_inventory()
        self.assertEqual(len(r["branches"]), 100)
        self.assertTrue(any("page=2" in p for _, p, _ in api.calls))

    def test_pre_effect_gate_changes_fail_closed(self):
        api = FakeAPI(); original = api.inspect; count = 0
        def inspect(*args):
            nonlocal count
            count += 1
            pr, obs = original(*args)
            if count == 2:
                obs["check_runs"][0]["conclusion"] = "failure"
            return pr, obs
        api.inspect = inspect
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertIn("PRE_EFFECT_GATE_DRIFT", r["first_blocker"])
        self.assertEqual(api.mutations, [])

    def test_transport_ack_and_lost_tips_do_not_prove_effect(self):
        for flag, blocker in (("discard_effect", "REVIEW_REQUEST_READBACK_MISMATCH"),
                              ("lose_tip", "ORIGINAL_BRANCH_TIP_LOST"),
                              ("bad_readback", "REVIEW_REQUEST_READBACK_MISMATCH")):
            api = FakeAPI(); setattr(api, flag, True)
            with tempfile.TemporaryDirectory() as d:
                r = self.run_step(api, d)
            self.assertIn(blocker, r["first_blocker"])
            self.assertFalse(r["post_effect_verified"])
            self.assertEqual(len(api.mutations), 1)

    def test_ambiguous_response_readback_has_no_retry(self):
        api = FakeAPI(); api.timeout_after_apply = True
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertTrue(r["post_effect_verified"])
        self.assertIn("TRANSPORT_UNCERTAIN", r["transport_uncertainty"])
        self.assertEqual(len(api.mutations), 1)

    def test_unresolved_intent_blocks_new_effect_and_recovery_is_read_only(self):
        api = FakeAPI(); api.discard_effect = True
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
            api.mutation_attempted = False
            again = self.run_step(api, d)
            self.assertIn("UNRESOLVED_INTENT", again["first_blocker"])
            api.pr["requested_reviewers"] = [{"login": "Goldkelch"}]
            recovered = M.recover(api, next(Path(d).glob("*.intent.json")))
            self.assertTrue(recovered["recovery_readback_only"])
            self.assertFalse(recovered["mutation_attempted"])
            self.assertEqual(len(api.mutations), 1)

    def test_native_protection_self_review_and_closed_equal_tree_are_not_bypassed(self):
        for kind in ("native", "self", "equal_tree"):
            api = FakeAPI()
            if kind == "native":
                api.observed["reviews"] = fixtures.ClosureEngineTests().obs()["reviews"]
                api.protection = lambda cfg: (_ for _ in ()).throw(M.ClosureBlock("NATIVE_PROTECTION_NOT_BOUND"))
            elif kind == "self":
                api.pr["user"]["login"] = "Goldkelch"
            else:
                api.pr["changed_files"] = 0
            with tempfile.TemporaryDirectory() as d:
                r = self.run_step(api, d)
            self.assertEqual(api.mutations, [])
            self.assertFalse(r["post_effect_verified"])

    def test_unsupported_host_operation_is_skipped_deterministically(self):
        api = FakeAPI(); original = api.probe
        api.probe = lambda: {**original(), "operations": []}
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertIn("BLOCK_MUTATION_CAPABILITY", r["first_blocker"])
        self.assertEqual(api.mutations, [])

    def test_later_dismissal_and_wrong_head_checks_never_transfer(self):
        fixture = fixtures.ClosureEngineTests()
        reviews = fixture.obs()["reviews"] + [{"state": "DISMISSED", "commit_id": "d" * 40,
            "submitted_at": "2026-10-01T00:00:00Z", "user": {"login": "Goldkelch"}}]
        self.assertFalse(M.exact_head_approval(reviews, "Goldkelch", HEAD, "author"))
        api = FakeAPI(); api.observed["check_runs"][0]["head_sha"] = BASE
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertIn("CHECK_HEAD_DRIFT", r["first_blocker"])
        self.assertEqual(api.mutations, [])

    def test_second_mutation_is_rejected_before_io(self):
        api = FakeAPI()
        action = {"pr": 7, "action": "REQUEST_REVIEW", "reviewer": "Goldkelch"}
        api.mutate(action)
        with self.assertRaisesRegex(M.ClosureBlock, "ONE_EFFECT_BUDGET"):
            api.mutate(action)
        self.assertEqual(len(api.mutations), 1)

    def test_missing_reviewer_collaborator_capability_blocks_before_post(self):
        api = FakeAPI()
        api.reviewer_capability = lambda reviewer: (_ for _ in ()).throw(M.ClosureBlock("REVIEWER_NOT_REPOSITORY_COLLABORATOR:" + reviewer))
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertIn("REVIEWER_NOT_REPOSITORY_COLLABORATOR:Goldkelch", r["first_blocker"])
        self.assertEqual(api.mutations, [])

    def test_native_merge_requires_two_parents_and_original_head_reachability(self):
        before = FakeAPI().inventory(); after = copy.deepcopy(before)
        after['main_sha'] = 'd' * 40
        after['branches'][1 if after['branches'][0]['name'] == 'feature' else 0]['sha'] = 'd' * 40
        after['pull_requests'] = []
        action = {'pr': 7, 'action': 'MERGE', 'head_sha': HEAD}
        for parents, merged, accepted in (([BASE, HEAD], True, True), ([BASE], True, False),
                                          ([BASE, TREE], True, False), ([BASE, HEAD], False, False)):
            api = FakeAPI(); api.pr.update(merged=merged, merge_commit_sha='d' * 40)
            original = api.request
            def request(method, path, payload=None):
                if '/git/commits/' in path:
                    return {'parents': [{'sha': p} for p in parents]}
                return original(method, path, payload)
            api.request = request
            if accepted:
                self.assertEqual(M.verify_post_effect(api, before, after, action)['merge_commit_sha'], 'd' * 40)
            else:
                with self.assertRaisesRegex(M.ClosureBlock, 'NATIVE_MERGE_READBACK_MISMATCH'):
                    M.verify_post_effect(api, before, after, action)

    def test_branch_update_retains_original_tip_and_old_main(self):
        api = FakeAPI(); api.compare = 'diverged'
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertEqual(r['selected_action']['action'], 'UPDATE_BRANCH')
        self.assertTrue(r['post_effect_verified'])
        self.assertEqual(api.mutations[0][2], {'expected_head_sha': HEAD})
        self.assertNotIn('force', api.mutations[0][2])

    def test_recovery_rejects_tampered_binding_without_mutation(self):
        api = FakeAPI(); api.discard_effect = True
        with tempfile.TemporaryDirectory() as d:
            self.run_step(api, d)
            path = next(Path(d).glob('*.intent.json'))
            saved = json.loads(path.read_text()); saved['inventory_before']['main_sha'] = TREE
            path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(M.ClosureBlock, 'RECOVERY_EVIDENCE_BINDING_MISMATCH'):
                M.recover(api, path)
        self.assertEqual(len(api.mutations), 1)

    def test_hard_boundaries_cannot_be_disabled(self):
        for key in ('predecessor_evidence_transfer', 'self_review_counts_as_independent',
                    'force_push_main', 'force_ref_update', 'effect_ack_done_claim'):
            p = self.policy(); p['hard_boundaries'][key] = True
            with self.assertRaisesRegex(M.ClosureBlock, 'hard boundaries'):
                M.validate_policy(p, REPO)

    def test_foreign_ref_does_not_disappear_from_inventory_or_get_selected(self):
        api = FakeAPI(); api.pr['head']['repo']['full_name'] = 'foreign/repo'
        with tempfile.TemporaryDirectory() as d:
            r = self.run_step(api, d)
        self.assertEqual(len(r['inventory_before']['pull_requests']), 1)
        self.assertIn('BLOCK_NON_ROLE_LOCAL_HEAD', r['first_blocker'])
        self.assertEqual(api.mutations, [])


if __name__ == "__main__":
    unittest.main()
