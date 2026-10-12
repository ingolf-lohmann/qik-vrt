# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import copy
import pathlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_expected_head_promotion",
    ROOT / "tools/qikvrt_expected_head_promotion.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
from tools.qikvrt_required_review_gate import project_governance, GOVERNANCE_STATUS_CONTEXT


class ExpectedHeadPromotionTests(unittest.TestCase):
    def snapshot(self, **overrides):
        native_pr = {"number": 459, "head": {"sha": "b" * 40}, "base": {"sha": "a" * 40}, "user": {"login": "integration-author"}}
        rules = [{"type": "pull_request", "parameters": {"required_approving_review_count": 1, "require_code_owner_review": True, "dismiss_stale_reviews_on_push": True, "require_last_push_approval": True}}]
        reviews = [{"id": 7, "submitted_at": "2026-10-05T11:00:00Z", "state": "APPROVED", "commit_id": "b" * 40, "user": {"login": "ingolf-lohmann"}}]
        statuses = [{"id": 8, "context": GOVERNANCE_STATUS_CONTEXT, "state": "success"}]
        value = {
            "pr_number": 459,
            "repository": "ingolf-lohmann/qik-vrt",
            "expected_tree_sha": "d" * 40,
            "target_ref_cas": {
                "state": "VERIFIED",
                "repository": "ingolf-lohmann/qik-vrt",
                "ref": "refs/heads/main",
                "operation": "SERVER_ATOMIC_REF_COMPARE_AND_SWAP",
                "comparison_scope": "TARGET_REF",
                "expected_old_sha": "a" * 40,
                "candidate_head_sha": "b" * 40,
                "candidate_tree_sha": "d" * 40,
                "server_atomic_compare_and_update": True,
                "force_update": False,
                "evidence_sha256": "e" * 64,
            },
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "expected_head_sha": "b" * 40,
            "current_head_sha": "b" * 40,
            "draft": True,
            "mergeable": True,
            "external_effect": "NONE",
            "required_gates": [
                "QIKVRT CI",
                "QIKVRT repository evidence materialization",
                "QIKVRT Collective Proposal Review",
                "QIK-VRT global claim completion",
            ],
            "workflow_runs": [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "success", "run_number": 10},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "success", "run_number": 20},
                {"name": "QIKVRT Collective Proposal Review", "status": "completed", "conclusion": "success", "run_number": 30},
                {"name": "QIK-VRT global claim completion", "status": "completed", "conclusion": "success", "run_number": 40},
                {"name": "QIKVRT conditional probe", "status": "completed", "conclusion": "skipped", "run_number": 1},
            ],
            "competing_writer_overlaps": [],
            "governance_projection": project_governance(native_pr, rules, reviews, statuses),
        }
        value.update(overrides)
        return value

    def test_terminal_green_exact_head_is_promotable(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot())
        self.assertEqual(result["state"], "PROMOTABLE")
        self.assertEqual(result["expected_head_sha"], "b" * 40)
        self.assertEqual(result["first_blocker"], None)

    def test_old_action_required_run_is_superseded_by_newer_success(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].extend(
            [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "action_required", "run_number": 9},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "action_required", "run_number": 19},
            ]
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "PROMOTABLE")

    def test_missing_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"] = [
            run for run in snapshot["workflow_runs"] if run["name"] != "QIKVRT Collective Proposal Review"
        ]
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_MISSING")

    def test_active_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "in_progress", "conclusion": None, "run_number": 11}
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL")

    def test_failed_required_gate_blocks(self) -> None:
        snapshot = self.snapshot()
        snapshot["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate_promotion(snapshot)
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN")

    def test_head_drift_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(current_head_sha="c" * 40))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(current_main_sha="c" * 40))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_competing_writer_overlap_blocks(self) -> None:
        result = MODULE.evaluate_promotion(
            self.snapshot(competing_writer_overlaps=[{"pr_number": 452, "paths": ["REPOSITORY_FILE_MANIFEST.json"]}])
        )
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "COMPETING_WRITER_OVERLAP")

    def test_external_effect_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(external_effect="ZENODO"))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "EXTERNAL_EFFECT_BOUNDARY")

    def test_non_mergeable_candidate_blocks(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(mergeable=False))
        self.assertEqual(result["state"], "BLOCK")
        self.assertEqual(result["first_blocker"], "NOT_MERGEABLE")

    def test_green_observer_executor_and_legacy_status_do_not_replace_native_evidence(self):
        snapshot = self.snapshot()
        snapshot.pop("governance_projection")
        snapshot["workflow_runs"].extend([
            {"name": name, "status": "completed", "conclusion": "success", "run_number": 99}
            for name in ("QIKVRT code-owner review observer", "QIKVRT requested review executor", "QIKVRT requested review execution")
        ])
        self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "NATIVE_GOVERNANCE_EVIDENCE_MISSING")

    def test_blocked_native_evidence_remains_blocked_when_execution_is_green(self):
        snapshot = self.snapshot()
        snapshot["governance_projection"].update(gate_state="failure", acceptance="BLOCKED", first_blocker="CODE_OWNER_RULE_NOT_ENFORCED")
        self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_predecessor_governance_evidence_cannot_transfer(self):
        for field, value in (("head_sha", "c" * 40), ("base_sha", "c" * 40), ("pr_number", 448)):
            with self.subTest(field=field):
                snapshot = self.snapshot(); snapshot["governance_projection"][field] = value
                self.assertEqual(MODULE.evaluate_promotion(snapshot)["first_blocker"], "NATIVE_GOVERNANCE_EVIDENCE_MISMATCH")

    def test_actual_promotion_shell_stops_before_ready_or_merge_when_native_evidence_changes(self):
        workflow = (ROOT / ".github/workflows/qikvrt_expected_head_promotion.yml").read_text()
        step = workflow.split("      - name: Reobserve exact unchanged head and advance one promotion phase", 1)[1].split("      - name:", 1)[0]
        script = textwrap.dedent(step.split("        run: |\n", 1)[1])
        for draft in (True, False):
            with self.subTest(draft=draft), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                pr = {"number": 459, "head": {"sha": "b" * 40}, "base": {"sha": "a" * 40}, "user": {"login": "integration-author"}, "draft": draft, "merged": False}
                (root / "pr.json").write_text(json.dumps(pr))
                mock = root / "gh"
                mock.write_text(f"#!{sys.executable}\n" + textwrap.dedent('''\
                    import json, os, sys
                    from pathlib import Path
                    args=sys.argv[1:]
                    with open(os.environ['MOCK_API_LOG'],'a') as stream:
                        stream.write(json.dumps(args)+'\\n')
                    if '--method' in args or args[:1] == ['pr']:
                        raise SystemExit('unexpected promotion mutation')
                    path=args[-1] if '--slurp' in args else args[1]
                    if path.endswith('/commits/main'):
                        value={'sha':'a'*40}
                    elif path.endswith('/pulls/459'):
                        value=json.loads(Path(os.environ['MOCK_PR']).read_text())
                    elif '/rules/branches/' in path:
                        value=[]
                    elif '/reviews?' in path:
                        value=[[]]
                    elif '/statuses?' in path:
                        value=[[{'id':8,'state':'success','context':'QIKVRT required code-owner review'}]]
                    else:
                        raise SystemExit('unexpected API read '+path)
                    if '--jq' in args:
                        for key in args[args.index('--jq')+1].strip('.').split('.'):
                            value=value[key]
                    if isinstance(value,str): print(value)
                    else: print(json.dumps(value))
                '''))
                mock.chmod(0o755)
                env = {**os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"], "REPOSITORY": "ingolf-lohmann/qik-vrt", "PR_NUMBER": "459", "EXPECTED_BASE": "a" * 40, "EXPECTED_HEAD": "b" * 40, "MOCK_PR": str(root / "pr.json"), "MOCK_API_LOG": str(root / "api.jsonl")}
                result = subprocess.run(["bash", "-c", script], env=env, cwd=ROOT, text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("CODE_OWNER_RULE_NOT_ENFORCED", result.stderr)
                calls = [json.loads(line) for line in (root / "api.jsonl").read_text().splitlines()]
                self.assertFalse(any('--method' in call or call[:1] == ['pr'] for call in calls))
    def test_green_gates_without_server_ref_cas_hold(self) -> None:
        result = MODULE.evaluate_promotion(self.snapshot(target_ref_cas=None))
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "ATOMIC_TARGET_REF_CAS_UNVERIFIED")

    def test_pr_head_sha_precondition_is_not_main_ref_cas(self) -> None:
        value = self.snapshot()
        value["target_ref_cas"]["comparison_scope"] = "PR_HEAD"
        self.assertEqual(MODULE.evaluate_promotion(value)["state"], "HOLD")

    def test_cas_subject_capability_and_evidence_must_all_match(self) -> None:
        for key, wrong in [("repository", "Goldkelch/qik-vrt"), ("ref", "refs/heads/other"),
                           ("expected_old_sha", "f" * 40), ("candidate_head_sha", "f" * 40),
                           ("candidate_tree_sha", "f" * 40),
                           ("server_atomic_compare_and_update", False), ("force_update", True),
                           ("evidence_sha256", None), ("state", "UNAVAILABLE")]:
            with self.subTest(key=key):
                value = self.snapshot()
                value["target_ref_cas"][key] = wrong
                self.assertEqual(MODULE.evaluate_promotion(value)["state"], "HOLD")


class PublicationReadbackTests(unittest.TestCase):
    # VERIFICATION FIXTURE ONLY: this simulated capability is not live GitHub evidence.
    def publication(self):
        value = ExpectedHeadPromotionTests().snapshot()
        value["merge_response"] = {"merged": True, "sha": "c" * 40}
        return value

    def observations(self):
        ref = {"ref": "refs/heads/main", "object": {"type": "commit", "sha": "c" * 40}}
        commit = {"sha": "c" * 40, "tree": {"sha": "d" * 40},
                  "parents": [{"sha": "a" * 40}, {"sha": "b" * 40}]}
        return [copy.deepcopy(ref), commit, copy.deepcopy(ref)]

    def verify(self, values, snapshot=None):
        reads = []
        iterator = iter(values)
        def read(path):
            reads.append(path)
            return next(iterator)
        return MODULE.verify_publication_readback(snapshot or self.publication(), read), reads

    def test_ref_commit_ref_reads_bind_exact_tree_and_parents(self) -> None:
        result, reads = self.verify(self.observations())
        self.assertEqual(result["state"], "CONTINUE")
        self.assertEqual(reads, ["repos/ingolf-lohmann/qik-vrt/git/ref/heads/main",
                                "repos/ingolf-lohmann/qik-vrt/git/commits/" + "c" * 40,
                                "repos/ingolf-lohmann/qik-vrt/git/ref/heads/main"])
        self.assertFalse(result["completion_claims"]["PASS"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_different_main_head_is_not_promotion_readback(self) -> None:
        for index in (0, 2):
            with self.subTest(index=index):
                values = self.observations()
                values[index]["object"]["sha"] = "f" * 40
                result, _ = self.verify(values)
                self.assertEqual(result["first_blocker"], "PUBLISHED_REF_HEAD_DRIFT")
                self.assertEqual(result["state"], "HOLD")

    def test_tag_or_wrong_ref_does_not_satisfy_commit_readback(self) -> None:
        for key, wrong in [("ref", "refs/heads/other"), ("object", {"type": "tag", "sha": "c" * 40})]:
            values = self.observations()
            values[2][key] = wrong
            result, _ = self.verify(values)
            self.assertEqual(result["state"], "HOLD")

    def test_changed_tree_and_wrong_parents_hold(self) -> None:
        values = self.observations()
        values[1]["tree"]["sha"] = "f" * 40
        result, _ = self.verify(values)
        self.assertEqual(result["first_blocker"], "PUBLISHED_COMMIT_TREE_MISMATCH")
        values = self.observations()
        values[1]["parents"][0]["sha"] = "f" * 40
        result, _ = self.verify(values)
        self.assertEqual(result["first_blocker"], "PUBLISHED_MERGE_PARENT_MISMATCH")

    def test_transport_ack_and_capability_failure_cannot_continue(self) -> None:
        value = self.publication()
        value["merge_response"] = {"merged": False, "sha": "c" * 40}
        result, reads = self.verify([], value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(reads, [])
        value = self.publication()
        value["target_ref_cas"]["state"] = "UNAVAILABLE"
        result, reads = self.verify([], value)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(reads, [])

    def test_lost_readback_preserves_effect_identity_without_retry(self) -> None:
        calls = []
        def failed_read(path):
            calls.append(path)
            raise TimeoutError("injected readback outage")
        result = MODULE.verify_publication_readback(self.publication(), failed_read)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["published_head_sha"], "c" * 40)
        self.assertFalse(result["automatic_retry"])
        self.assertEqual(len(calls), 1)

    def test_malformed_provider_readback_holds(self) -> None:
        result, _ = self.verify([None, {}, {}])
        self.assertEqual(result["state"], "HOLD")


class GraphqlCasIntegrationTests(unittest.TestCase):
    """Local simulated qualification only; never a live server/Governance receipt."""

    def setUp(self):
        self.snapshot = ExpectedHeadPromotionTests().snapshot(draft=False)
        self.rules = [
            {"type": "pull_request", "ruleset_id": 1, "parameters": {
                "required_approving_review_count": 1, "require_code_owner_review": True,
                "dismiss_stale_reviews_on_push": True, "require_last_push_approval": True}},
            {"type": "non_fast_forward", "ruleset_id": 1},
            {"type": "required_status_checks", "ruleset_id": 1, "parameters": {
                "required_status_checks": [{"context": "test", "integration_id": 10},
                                           {"context": "QIKVRT required code-owner review", "integration_id": 10}]}}
        ]
        self.rulesets = [{"id": 1, "enforcement": "active", "target": "branch", "bypass_actors": []}]
        self.reviews = [{"id": 1, "user": {"login": "ingolf-lohmann"}, "commit_id": "b" * 40,
                         "state": "APPROVED", "submitted_at": "2026-10-12T17:00:00Z"}]
        self.pr = {"number": 459, "state": "open", "draft": False, "merged": False,
                   "mergeable": True, "merge_commit_sha": "c" * 40,
                   "user": {"login": "fixture-integration-author"},
                   "base": {"sha": "a" * 40, "ref": "main", "repo": {"full_name": "ingolf-lohmann/qik-vrt"}},
                   "head": {"sha": "b" * 40, "repo": {"full_name": "ingolf-lohmann/qik-vrt"}}}
        self.commit = {"sha": "c" * 40, "tree": {"sha": "d" * 40},
                       "parents": [{"sha": "a" * 40}, {"sha": "b" * 40}]}
        self.qualification = {
            "schema": "qikvrt_graphql_ref_cas_qualification_v1", "state": "VERIFIED",
            "repository": "ingolf-lohmann/qik-vrt", "repository_node_id": "R_fixture",
            "target_ref": "refs/heads/main", "endpoint": "https://api.github.com/graphql",
            "adapter_sha256": MODULE.hashlib.sha256(pathlib.Path(MODULE.__file__).read_bytes()).hexdigest(),
            "protected_test_ref": "refs/heads/fixture-qualified-target", "executor_login": "fixture-bot",
            "independent_verifier": "fixture-independent-reviewer", "executor_bypass": False,
            "native_governance_independently_verified": True,
            "effective_rules_sha256": MODULE._digest(self.rules), "rulesets_sha256": MODULE._digest(self.rulesets),
            "test_policy_sha256": MODULE._digest(self.rules), "evidence_sha256": "e" * 64,
            "cases": {name: {"result": "PASS", "repository": "ingolf-lohmann/qik-vrt",
                             "ref": "refs/heads/fixture-qualified-target", "ref_unchanged": True,
                             "receipt_sha256": "e" * 64, "receipt_url": "https://example.invalid/fixture"}
                      for name in MODULE.CAS_QUALIFICATION_CASES},
        }
        self.main = "a" * 40
        self.requests = []
        self.reads = []
        self.check_state = "success"
        self.check_missing = False
        self.check_wrong_head = False
        self.source_id = 10
        self.transport_mode = "success"
        self.readback_outage = False

    def read(self, path):
        self.reads.append(path)
        prefix = "repos/ingolf-lohmann/qik-vrt"
        if path == prefix:
            return {"node_id": "R_fixture", "full_name": "ingolf-lohmann/qik-vrt"}
        if path == prefix + "/pulls/459":
            return copy.deepcopy(self.pr)
        if path == prefix + "/rules/branches/main":
            return copy.deepcopy(self.rules)
        if path == prefix + "/rulesets/1":
            return copy.deepcopy(self.rulesets[0])
        if path == prefix + "/pulls/459/reviews?per_page=100":
            return copy.deepcopy(self.reviews)
        if "/statuses?" in path:
            return []
        if "/check-runs?" in path:
            sha = path.split("/commits/")[1].split("/")[0]
            checks = [{"id": 1, "name": context, "head_sha": "f" * 40 if self.check_wrong_head else sha,
                       "status": "completed", "conclusion": self.check_state, "app": {"id": self.source_id}}
                      for context in ("test", "QIKVRT required code-owner review")]
            if self.check_missing:
                checks.pop()
            return {"total_count": len(checks), "check_runs": checks}
        if path == prefix + "/git/ref/pull/459/merge":
            return {"ref": "refs/pull/459/merge", "object": {"type": "commit", "sha": "c" * 40}}
        if path == prefix + "/git/commits/" + "c" * 40:
            return copy.deepcopy(self.commit)
        if path == prefix + "/git/ref/heads/main":
            if self.readback_outage and self.requests:
                raise TimeoutError("simulated lost readback")
            return {"ref": "refs/heads/main", "object": {"type": "commit", "sha": self.main}}
        raise AssertionError("unexpected GET " + path)

    def graphql(self, request):
        if request["query"].startswith("query "):
            return {"data": {"viewer": {"login": "fixture-bot"}}}
        self.requests.append(copy.deepcopy(request))
        inputs = request["variables"]["input"]
        update = inputs["refUpdates"][0]
        if self.transport_mode == "race":
            self.main = "f" * 40  # Competing Main writer after every pre-effect GET.
        if update["beforeOid"] != self.main:
            return {"errors": [{"type": "STALE_DATA", "message": "beforeOid does not match"}], "data": {"updateRefs": None}}
        if self.transport_mode == "server_rejection":
            return {"errors": [{"type": "FORBIDDEN", "message": "native review/check/NFF rejected"}]}
        if self.transport_mode == "lost_before_effect":
            raise TimeoutError("simulated transport failure")
        self.main = update["afterOid"]
        if self.transport_mode == "lost_after_effect":
            raise TimeoutError("simulated lost response")
        if self.transport_mode == "empty":
            return {}
        if self.transport_mode == "raw":
            return "unparseable response"
        if self.transport_mode == "partial_error":
            return {"errors": [{"message": "ambiguous"}], "data": {"updateRefs": {"clientMutationId": inputs["clientMutationId"]}}}
        return {"data": {"updateRefs": {"clientMutationId": inputs["clientMutationId"]}}}

    def prepare(self):
        return MODULE.prepare_graphql_promotion(self.snapshot, self.qualification, self.read)

    def test_verified_cas_cannot_bypass_missing_native_governance_projection(self):
        self.snapshot.pop("governance_projection")
        result = self.prepare()
        self.assertEqual(result["first_blocker"], "NATIVE_GOVERNANCE_EVIDENCE_MISSING")
        self.assertEqual(self.requests, [])
        self.assertEqual(self.reads, [])

    def test_historical_mirror_owner_review_cannot_approve_authority_promotion(self):
        self.reviews[0]["user"]["login"] = "Goldkelch"
        result = self.prepare()
        self.assertEqual(result["state"], "HOLD")
        self.assertIn("CODE_OWNER_REVIEW_MISSING", result["detail"])
        self.assertEqual(self.requests, [])

    def execute(self, journal):
        return MODULE.execute_graphql_promotion(self.snapshot, self.qualification, journal, self.read, self.graphql)

    def test_exact_request_binds_repository_main_old_new_head_candidate_tree_and_parents(self):
        prepared = self.prepare()
        self.assertEqual(prepared["state"], "PREPARED")
        inputs = prepared["request"]["variables"]["input"]
        self.assertEqual(inputs["repositoryId"], "R_fixture")
        self.assertEqual(inputs["refUpdates"], [{"name": "refs/heads/main", "beforeOid": "a" * 40,
                                               "afterOid": "c" * 40, "force": False}])
        self.assertEqual(prepared["snapshot"]["ref_publication"]["candidate_head_sha"], "b" * 40)
        self.assertEqual(prepared["snapshot"]["ref_publication"]["tree_sha"], "d" * 40)

    def test_documentation_or_incomplete_or_wrongly_bound_qualification_cannot_admit(self):
        for key, wrong in [("state", "DOCUMENTED"), ("adapter_sha256", "f" * 64),
                           ("repository", "Goldkelch/qik-vrt"), ("target_ref", "refs/heads/other"),
                           ("protected_test_ref", "refs/heads/main"), ("endpoint", "https://example.invalid/graphql"),
                           ("executor_bypass", True), ("independent_verifier", "fixture-bot"),
                           ("native_governance_independently_verified", False), ("cases", {}),
                           ("test_policy_sha256", "f" * 64)]:
            with self.subTest(key=key):
                q = copy.deepcopy(self.qualification)
                q[key] = wrong
                result = MODULE.prepare_graphql_promotion(self.snapshot, q, self.read)
                self.assertEqual(result["state"], "HOLD")
                self.assertEqual(self.requests, [])
        self.assertEqual(self.reads, [])

    def test_stale_missing_withdrawn_changed_and_self_reviews_block_without_a_post(self):
        for state in ("STALE", "MISSING", "DISMISSED", "CHANGES_REQUESTED", "SELF"):
            with self.subTest(state=state):
                self.setUp()
                if state == "STALE": self.reviews[0]["commit_id"] = "f" * 40
                elif state == "MISSING": self.reviews = []
                elif state == "SELF": self.pr["user"]["login"] = "ingolf-lohmann"
                else: self.reviews[0]["state"] = state
                self.assertEqual(self.prepare()["state"], "HOLD")
                self.assertEqual(self.requests, [])

    def test_failed_missing_wrong_subject_or_wrong_source_checks_block(self):
        for mode in ("failure", "missing", "wrong_head", "wrong_source"):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "failure": self.check_state = "failure"
                if mode == "missing": self.check_missing = True
                if mode == "wrong_head": self.check_wrong_head = True
                if mode == "wrong_source": self.source_id = 99
                self.assertEqual(self.prepare()["state"], "HOLD")
                self.assertEqual(self.requests, [])

    def test_native_policy_change_bypass_or_missing_nff_blocks(self):
        for mode in ("bypass", "disabled", "no_nff", "drift", "empty"):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "bypass": self.rulesets[0]["bypass_actors"] = [{"actor_id": 1}]
                if mode == "disabled": self.rulesets[0]["enforcement"] = "disabled"
                if mode == "no_nff": self.rules = [r for r in self.rules if r["type"] != "non_fast_forward"]
                if mode == "drift": self.rules[0]["parameters"]["require_last_push_approval"] = False
                if mode == "empty": self.rules = []
                self.assertEqual(self.prepare()["state"], "HOLD")

    def test_wrong_repository_node_and_changed_pr_head_hold(self):
        self.qualification["repository_node_id"] = "wrong"
        self.assertEqual(self.prepare()["state"], "HOLD")
        self.setUp()
        self.pr["head"]["sha"] = "f" * 40
        self.assertEqual(self.prepare()["state"], "HOLD")

    def test_wrong_tree_and_non_ff_reversed_or_third_parent_hold(self):
        for mode in ("tree", "non_ff", "reverse", "third", "zero"):
            with self.subTest(mode=mode):
                self.setUp()
                if mode == "tree": self.commit["tree"]["sha"] = "f" * 40
                if mode == "non_ff": self.commit["parents"][0]["sha"] = "f" * 40
                if mode == "reverse": self.commit["parents"].reverse()
                if mode == "third": self.commit["parents"].append({"sha": "f" * 40})
                if mode == "zero": self.pr["merge_commit_sha"] = "0" * 40
                self.assertEqual(self.prepare()["state"], "HOLD")
                self.assertEqual(self.requests, [])

    def test_fsync_intent_precedes_single_mutation_and_exact_ref_readback_does_not_claim_pr_merge(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = pathlib.Path(directory) / "attempt.json"
            def guarded(request):
                if request["query"].startswith("mutation "):
                    saved = json.loads(journal.read_text())
                    self.assertEqual(saved["request"], request)
                return self.graphql(request)
            result = MODULE.execute_graphql_promotion(self.snapshot, self.qualification, journal, self.read, guarded)
            self.assertEqual(result["state"], "CONTINUE")
            self.assertEqual(len(self.requests), 1)
            self.assertEqual(result["pr_merge_state"], "NOT_INFERRED")
            self.assertFalse(result["automatic_retry"])
            self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])
            self.assertNotIn("merge_response", json.loads(journal.read_text())["snapshot"])

    def test_concurrent_main_change_rejects_cas_after_client_preflight(self):
        self.transport_mode = "race"
        with tempfile.TemporaryDirectory() as directory:
            result = self.execute(pathlib.Path(directory) / "attempt.json")
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(self.main, "f" * 40)
            self.assertEqual(len(self.requests), 1)

    def test_server_rejects_after_review_or_checks_change_during_race(self):
        self.transport_mode = "server_rejection"
        with tempfile.TemporaryDirectory() as directory:
            result = self.execute(pathlib.Path(directory) / "attempt.json")
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(self.main, "a" * 40)

    def test_ambiguous_responses_always_reconcile_and_never_replay(self):
        for mode in ("lost_before_effect", "lost_after_effect", "empty", "raw", "partial_error"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                self.setUp()
                self.transport_mode = mode
                journal = pathlib.Path(directory) / "attempt.json"
                result = self.execute(journal)
                self.assertEqual(result["state"], "HOLD")
                self.assertEqual(result["published_head_sha"], "c" * 40)
                self.assertTrue(any("git/commits/" in p for p in result["readback"].get("read_paths", []) ) or result["readback"]["state"] == "HOLD")
                self.assertEqual(self.execute(journal)["first_blocker"], "CAS_ATTEMPT_ALREADY_RECORDED")
                self.assertEqual(len(self.requests), 1)
                if mode != "lost_before_effect":
                    reconciled = MODULE.reconcile_graphql_attempt(json.loads(journal.read_text()), self.qualification, self.read)
                    self.assertEqual(reconciled["state"], "CONTINUE")
                    self.assertEqual(len(self.requests), 1)

    def test_lost_readback_preserves_exact_merge_and_request_digest(self):
        self.readback_outage = True
        with tempfile.TemporaryDirectory() as directory:
            result = self.execute(pathlib.Path(directory) / "attempt.json")
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(result["published_head_sha"], "c" * 40)
            self.assertEqual(len(result["request_sha256"]), 64)
            self.assertEqual(len(self.requests), 1)

    def test_existing_or_unwritable_journal_and_wrong_identity_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = pathlib.Path(directory) / "missing" / "attempt.json"
            self.assertEqual(self.execute(journal)["state"], "HOLD")
            self.assertEqual(self.requests, [])
            result = MODULE.execute_graphql_promotion(self.snapshot, self.qualification,
                pathlib.Path(directory) / "attempt.json", self.read,
                lambda request: {"data": {"viewer": {"login": "wrong-executor"}}})
            self.assertEqual(result["first_blocker"], "GRAPHQL_EXECUTOR_IDENTITY_UNVERIFIED")

    def test_tampered_journal_reconciliation_rejects_without_reads_or_writes(self):
        attempt = self.prepare()
        attempt["request"]["variables"]["input"]["refUpdates"][0]["force"] = True
        self.reads.clear()
        result = MODULE.reconcile_graphql_attempt(attempt, self.qualification, self.read)
        self.assertEqual(result["first_blocker"], "CAS_ATTEMPT_REQUEST_MISMATCH")
        self.assertEqual(self.reads, [])
        self.assertEqual(self.requests, [])

    def test_transport_is_one_pinned_graphql_post_with_structured_stdin(self):
        request = self.prepare()["request"]
        with mock.patch.object(MODULE.subprocess, "check_output", return_value='{"data":{}}') as run:
            MODULE._gh_graphql(request)
        args, kwargs = run.call_args
        self.assertEqual(args[0], ["gh", "api", "--hostname", "github.com", "--method", "POST", "graphql", "--input", "-"])
        self.assertEqual(json.loads(kwargs["input"]), request)
        self.assertEqual(run.call_count, 1)

    def test_wrong_correlation_id_cannot_close_even_with_matching_ref(self):
        with tempfile.TemporaryDirectory() as directory:
            def wrong_id(request):
                response = self.graphql(request)
                if request["query"].startswith("mutation "):
                    response["data"]["updateRefs"]["clientMutationId"] = "wrong"
                return response
            result = MODULE.execute_graphql_promotion(self.snapshot, self.qualification,
                pathlib.Path(directory) / "attempt.json", self.read, wrong_id)
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(result["readback"]["state"], "CONTINUE")
            self.assertEqual(len(self.requests), 1)

    def test_merge_result_checks_cannot_be_inherited_from_reviewed_head(self):
        def missing_merge_checks(path):
            value = self.read(path)
            if "/commits/" + "c" * 40 + "/check-runs?" in path:
                return {"total_count": 0, "check_runs": []}
            return value
        result = MODULE.prepare_graphql_promotion(self.snapshot, self.qualification, missing_merge_checks)
        self.assertIn("MERGE_RESULT_REQUIRED_CHECKS_NOT_GREEN", result["detail"])
        self.assertEqual(self.requests, [])

    def test_review_withdrawal_during_viewer_read_is_reobserved_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            def withdrawing_viewer(request):
                self.reviews[0]["state"] = "DISMISSED"
                return {"data": {"viewer": {"login": "fixture-bot"}}}
            result = MODULE.execute_graphql_promotion(self.snapshot, self.qualification,
                pathlib.Path(directory) / "attempt.json", self.read, withdrawing_viewer)
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(self.requests, [])

    def test_malformed_http_json_preserves_raw_bytes_and_reconciles(self):
        with tempfile.TemporaryDirectory() as directory:
            def malformed(request):
                if request["query"].startswith("query "):
                    return self.graphql(request)
                self.requests.append(request)
                self.main = "c" * 40
                return json.loads("{invalid-json")
            result = MODULE.execute_graphql_promotion(self.snapshot, self.qualification,
                pathlib.Path(directory) / "attempt.json", self.read, malformed)
            self.assertEqual(result["graphql_response"], "{invalid-json")
            self.assertEqual(result["state"], "HOLD")
            self.assertEqual(result["readback"]["state"], "CONTINUE")

    def test_zero_oid_cannot_be_used_for_create_or_delete(self):
        for key in ("current_main_sha", "base_sha", "expected_head_sha", "current_head_sha", "expected_tree_sha"):
            with self.subTest(key=key):
                value = copy.deepcopy(self.snapshot)
                value[key] = "0" * 40
                value["target_ref_cas"]["candidate_tree_sha"] = value["expected_tree_sha"]
                value["target_ref_cas"]["candidate_head_sha"] = value["expected_head_sha"]
                value["target_ref_cas"]["expected_old_sha"] = value["base_sha"]
                with self.assertRaises(MODULE.PromotionBlock):
                    MODULE.evaluate_promotion(value)

    def test_duplicate_nonfinite_and_nonobject_json_are_retained_as_ambiguous(self):
        request = self.prepare()["request"]
        for raw in ('{"data":{},"data":{"updateRefs":{}}}', '{"data":NaN}', '[]', '{'):
            with self.subTest(raw=raw), mock.patch.object(MODULE.subprocess, "check_output", return_value=raw):
                response = MODULE._gh_graphql(request)
                self.assertEqual(response["raw_response"], raw)
                self.assertNotIn("data", response)


if __name__ == "__main__":
    unittest.main()
