# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import base64
import copy
import hashlib
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class NativeReviewAPI:
    """Independent REST fault model; records every effectful call."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.repo = snapshot['repository']
        self.author = {'login': 'integration-author', 'id': 1, 'type': 'User'}
        self.reviewer = {'login': 'Goldkelch', 'id': 2, 'type': 'User'}
        self.calls = []
        self.reviews = []
        self.commit_statuses = []
        self.files_override = None
        self.post_mode = 'accept'
        self.responses = {
            f'repos/{self.repo}': {'full_name': self.repo, 'owner': dict(self.author)},
            f'repos/{self.repo}/codeowners/errors?ref={snapshot["current_main_sha"]}': {'errors': []},
            f'repos/{self.repo}/pulls/{snapshot["pr_number"]}/requested_reviewers': {'users': [dict(self.reviewer)] if snapshot['requested_reviewers'] else [], 'teams': []},
            'users/Goldkelch': dict(self.reviewer),
            f'repos/{self.repo}/collaborators/Goldkelch': None,
            f'repos/{self.repo}/collaborators/Goldkelch/permission': {'permission': 'write', 'user': dict(self.reviewer)},
            f'repos/{self.repo}/pulls/{snapshot["pr_number"]}': {'number': snapshot['pr_number'], 'state': 'open', 'draft': False, 'user': dict(self.author), 'head': {'sha': snapshot['head_sha']}, 'base': {'sha': snapshot['base_sha']}},
            f'repos/{self.repo}/commits/main': {'sha': snapshot['current_main_sha']},
            f'repos/{self.repo}/git/commits/{snapshot["head_sha"]}': {'tree': {'sha': snapshot['tree_sha']}},
        }
        self.statuses = {f'repos/{self.repo}/collaborators/Goldkelch': 204}
        self.codeowners('* @Goldkelch\n')

    def codeowners(self, content):
        raw = content.encode()
        self.responses[f'repos/{self.repo}/contents/.github/CODEOWNERS?ref={self.snapshot["current_main_sha"]}'] = {
            'encoding': 'base64', 'content': base64.b64encode(raw).decode(),
            'sha': hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),
        }

    def get(self, path):
        self.calls.append(('GET', path))
        if path.startswith(f'repos/{self.repo}/statuses/{self.snapshot["head_sha"]}?'):
            return {'status':200,'data':copy.deepcopy(self.commit_statuses)}
        if path.startswith(f'repos/{self.repo}/pulls/{self.snapshot["pr_number"]}/reviews?'):
            return {'status': 200, 'data': copy.deepcopy(self.reviews)}
        if path.startswith(f'repos/{self.repo}/pulls/{self.snapshot["pr_number"]}/files?'):
            return {'status': 200, 'data': copy.deepcopy(self.files_override) if self.files_override is not None else [{'filename': path} for path in self.snapshot['changed_paths']]}
        if path not in self.responses:
            return {'status': 404, 'data': {'message': 'Not Found'}}
        return {'status': self.statuses.get(path, 200), 'data': copy.deepcopy(self.responses[path])}

    def post(self, path, payload):
        self.calls.append(('POST', path, copy.deepcopy(payload)))
        if self.post_mode == 'reject':
            return {'status': 422, 'data': {'message': 'do not disclose TOKEN_SECRET'}}
        self.reviews.append({'id': 17, 'commit_id': payload['commit_id'], 'body': payload['body'], 'user': {'id': 41898282, 'login': 'github-actions[bot]', 'type': 'Bot'}, 'state': {'APPROVE':'APPROVED','REQUEST_CHANGES':'CHANGES_REQUESTED','COMMENT':'COMMENTED'}[payload['event']]})
        if self.post_mode == 'lost':
            raise OSError('lost acknowledgement')
        return {'status': 200, 'data': self.reviews[-1]}

    @property
    def posts(self):
        return [call for call in self.calls if call[0] == 'POST']


class RequestedReviewExecutorTests(unittest.TestCase):
    def snapshot(self, **overrides):
        value = {
            "repository": "example/qik-vrt",
            "pr_number": 349,
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "observed_head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "draft": False,
            "pr_author": {"login": "integration-author", "id": 1, "type": "User"},
            "requested_reviewers": ["Goldkelch"],
            "requested_team_reviewers": [],
            "changed_paths": ["src/a.py", "tests/test_a.py"],
            "unresolved_review_threads": 0,
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
                {"name": "QIKVRT requested review executor", "status": "in_progress", "conclusion": None, "run_number": 1},
            ],
        }
        value.update(overrides)
        value['reviewer_admission'] = MODULE.collect_reviewer_admission(value, NativeReviewAPI(value))
        return value

    def test_terminal_green_requested_review_approves(self):
        result = MODULE.evaluate(self.snapshot())
        self.assertEqual(result["state"], "APPROVE")
        self.assertIsNone(result["first_blocker"])

    def test_nonterminal_gate_waits_without_false_review(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "in_progress", "conclusion": None, "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_NOT_TERMINAL")

    def test_failed_gate_requests_changes(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_FAILED")

    def test_head_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(observed_head_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(current_main_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_unresolved_thread_blocks(self):
        result = MODULE.evaluate(self.snapshot(unresolved_review_threads=1))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "UNRESOLVED_REVIEW_THREADS")

    def test_draft_waits(self):
        result = MODULE.evaluate(self.snapshot(draft=True))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "DRAFT")

    def test_no_active_request_is_noop_wait(self):
        result = MODULE.evaluate(self.snapshot(requested_reviewers=[]))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "NO_ACTIVE_REVIEW_REQUEST")


class ReviewerAdmissionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = RequestedReviewExecutorTests().snapshot()
        self.api = NativeReviewAPI(self.snapshot)
        self.signer = {'login': 'github-actions[bot]', 'id': 41898282, 'type': 'Bot'}

    def admission(self):
        value = MODULE.collect_reviewer_admission(self.snapshot, self.api)
        self.snapshot['reviewer_admission'] = value
        return value

    def persist(self):
        return MODULE.persist_review(self.snapshot, MODULE.evaluate(self.snapshot), self.api, signer=self.signer, body='exact review bytes')

    def test_write_projection_does_not_override_identity_404_or_trigger_post(self):
        self.api.statuses['users/Goldkelch'] = 404
        admission = self.admission()
        self.assertEqual(admission['first_blocker'], 'CODEOWNER_IDENTITY_UNRESOLVABLE')
        self.assertFalse(admission['reachable_independent_reviewer'])
        self.assertEqual(self.persist()['review_post_count'], 0)
        self.assertEqual(self.api.posts, [])

    def test_empty_codeowners_errors_are_not_identity_evidence(self):
        self.api.statuses['users/Goldkelch'] = 403
        self.assertEqual(self.admission()['state'], 'HOLD')

    def test_write_projection_without_stable_user_identity_is_blocked(self):
        self.api.responses[f'repos/{self.api.repo}/collaborators/Goldkelch/permission'] = {'permission': 'write'}
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_PERMISSION_IDENTITY_UNVERIFIED')

    def test_permission_and_user_identity_mismatch_is_blocked(self):
        self.api.responses[f'repos/{self.api.repo}/collaborators/Goldkelch/permission']['user']['id'] = 99
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_PERMISSION_IDENTITY_UNVERIFIED')

    def test_native_collaborator_check_overrules_projection(self):
        self.api.statuses[f'repos/{self.api.repo}/collaborators/Goldkelch'] = 404
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_COLLABORATION_NOT_CONFIRMED')
        self.assertFalse(MODULE.evaluate(self.snapshot)['review_effect_allowed'])

    def test_native_metadata_permission_denial_is_not_membership_success(self):
        self.api.statuses[f'repos/{self.api.repo}/collaborators/Goldkelch'] = 403
        self.assertEqual(self.admission()['state'], 'HOLD')

    def test_read_access_cannot_satisfy_codeowner_write_requirement(self):
        self.api.responses[f'repos/{self.api.repo}/collaborators/Goldkelch/permission']['permission'] = 'read'
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_WRITE_PERMISSION_MISSING')

    def test_renamed_author_identity_cannot_be_independent(self):
        self.api.responses['users/Goldkelch']['id'] = self.snapshot['pr_author']['id']
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_SELF_REVIEW')

    def test_bot_codeowner_cannot_be_independent_human_account(self):
        self.api.responses['users/Goldkelch']['type'] = 'Bot'
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_IDENTITY_UNRESOLVABLE')

    def test_same_login_with_different_id_is_not_native_accepted_request(self):
        self.api.responses[f'repos/{self.api.repo}/pulls/349/requested_reviewers']['users'][0]['id'] = 88
        self.assertEqual(self.admission()['first_blocker'], 'NO_ACTIVE_REVIEW_REQUEST')
        self.assertEqual(self.api.posts, [])

    def test_no_native_request_never_becomes_reachable_from_permissions(self):
        self.api.responses[f'repos/{self.api.repo}/pulls/349/requested_reviewers']['users'] = []
        admission = self.admission()
        self.assertEqual(admission['state'], 'WAIT')
        self.assertFalse(admission['reachable_independent_reviewer'])
        self.assertEqual(self.persist()['review_post_count'], 0)

    def test_existing_request_does_not_override_removed_write_access(self):
        self.api.responses[f'repos/{self.api.repo}/collaborators/Goldkelch/permission']['permission'] = 'none'
        self.assertEqual(self.admission()['state'], 'HOLD')

    def test_native_codeowners_errors_block_all_review_effects(self):
        self.api.responses[f'repos/{self.api.repo}/codeowners/errors?ref={self.snapshot["current_main_sha"]}']['errors'] = [{'line': 1, 'kind': 'Invalid owner'}]
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNERS_NATIVE_ERRORS')

    def test_candidate_codeowners_is_never_used_as_authority(self):
        self.admission()
        source = self.snapshot['reviewer_admission']['codeowners_source']
        self.assertEqual(source['ref'], self.snapshot['current_main_sha'])
        self.assertTrue(all(self.snapshot['head_sha'] not in call[1] for call in self.api.calls))

    def test_codeowners_blob_mismatch_fails_closed(self):
        self.api.responses[f'repos/{self.api.repo}/contents/.github/CODEOWNERS?ref={self.snapshot["current_main_sha"]}']['sha'] = 'f'*40
        self.assertEqual(self.admission()['state'], 'HOLD')

    def test_last_matching_ownerless_override_cannot_be_skipped(self):
        self.api.codeowners('* @Goldkelch\n/tests/\n')
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_SCOPE_UNCOVERED')

    def test_codeowners_pattern_precedence_and_recursive_directory(self):
        value = MODULE.codeowners_for_paths('* @first\n/src/ @second\n/src/deep/*.py @third\n', ['src/a.py', 'src/deep/x.py', 'tests/a.py'])
        self.assertEqual(value, {'src/a.py':['@second'], 'src/deep/x.py':['@third'], 'tests/a.py':['@first']})

    def test_unsupported_patterns_and_email_owners_fail_closed(self):
        for text in ['!src/ @Goldkelch', '*.py nobody@example.org', '[abc] @Goldkelch']:
            with self.subTest(text=text), self.assertRaises(MODULE.ReviewSnapshotError):
                MODULE.codeowners_for_paths(text, ['src/a.py'])

    def test_missing_or_tampered_admission_cannot_reach_writer(self):
        self.snapshot.pop('reviewer_admission')
        self.assertEqual(MODULE.evaluate(self.snapshot)['first_blocker'], 'REVIEWER_ADMISSION_MISSING')
        self.admission()
        self.snapshot['reviewer_admission']['binding']['head_sha'] = 'f'*40
        self.assertEqual(MODULE.evaluate(self.snapshot)['first_blocker'], 'REVIEWER_ADMISSION_DRIFT')

    def team(self):
        self.api.codeowners('* @example/reviewers\n')
        self.api.responses[f'repos/{self.api.repo}']['owner'] = {'login':'example','id':10,'type':'Organization'}
        self.api.responses['orgs/example/teams/reviewers'] = {'id':20,'slug':'reviewers','privacy':'closed','organization':{'id':10}}
        self.api.responses[f'orgs/example/teams/reviewers/repos/{self.api.repo}'] = {'full_name':self.api.repo,'permissions':{'push':True}}
        self.api.responses['orgs/example/teams/reviewers/members?role=all&per_page=100&page=1'] = [dict(self.api.reviewer)]
        self.api.responses[f'repos/{self.api.repo}/pulls/349/requested_reviewers'] = {'users':[],'teams':[{'id':20,'slug':'reviewers'}]}

    def test_personal_repository_cannot_silently_acquire_team_reviewer(self):
        self.api.codeowners('* @example/reviewers\n')
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_TEAM_REPOSITORY_MISMATCH')

    def test_legitimate_visible_write_team_with_independent_member_is_bound(self):
        self.team()
        admission = self.admission()
        self.assertEqual(admission['state'], 'VERIFIED_ACTIVE_REQUEST')
        self.assertEqual(admission['active_codeowners'], ['@example/reviewers'])

    def test_secret_or_foreign_team_cannot_carry_codeowner_review(self):
        for field, value, blocker in [('privacy','secret','CODEOWNER_TEAM_NOT_VISIBLE'),('organization',{'id':30},'CODEOWNER_TEAM_IDENTITY_UNVERIFIED')]:
            self.team()
            self.api.responses['orgs/example/teams/reviewers'][field] = value
            with self.subTest(field=field):
                self.assertEqual(self.admission()['first_blocker'], blocker)

    def test_team_member_write_access_does_not_replace_team_write_grant(self):
        self.team()
        self.api.responses[f'orgs/example/teams/reviewers/repos/{self.api.repo}']['permissions']['push'] = False
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_TEAM_WRITE_PERMISSION_MISSING')

    def test_team_containing_only_author_is_not_independent(self):
        self.team()
        self.api.responses['orgs/example/teams/reviewers/members?role=all&per_page=100&page=1'] = [self.snapshot['pr_author']]
        self.assertEqual(self.admission()['first_blocker'], 'CODEOWNER_TEAM_NO_INDEPENDENT_MEMBER')

    def test_incomplete_team_member_pagination_fails_closed(self):
        self.team()
        self.api.responses['orgs/example/teams/reviewers/members?role=all&per_page=100&page=1'] = [self.snapshot['pr_author']]*100
        self.assertEqual(self.admission()['first_blocker'], 'REVIEWER_ADMISSION_METADATA_INVALID')

    def test_every_changed_owner_scope_requires_active_request(self):
        self.team()
        self.api.codeowners('* @Goldkelch\n/tests/ @example/reviewers\n')
        self.assertEqual(self.admission()['state'], 'WAIT')

    def test_good_disposition_posts_once_and_independently_reads_back(self):
        self.admission()
        receipt = self.persist()
        self.assertEqual(receipt['state'], 'VERIFIED_NATIVE_REVIEW')
        self.assertEqual(receipt['review_post_count'], 1)
        self.assertEqual(len(self.api.posts), 1)
        self.assertFalse(receipt['independent_code_owner_approval'])
        repeated = self.persist()
        self.assertEqual(repeated['state'], 'VERIFIED_NATIVE_REVIEW')
        self.assertEqual(repeated['review_post_count'], 0)
        self.assertEqual(len(self.api.posts), 1)

    def test_platform_422_has_no_comment_fallback_no_success_and_no_secret(self):
        self.admission()
        self.api.post_mode = 'reject'
        receipt = self.persist()
        self.assertEqual(receipt['state'], 'HOLD')
        self.assertEqual(receipt['first_blocker'], 'NATIVE_REVIEW_REJECTED')
        self.assertEqual(len(self.api.posts), 1)
        self.assertNotIn('TOKEN_SECRET', json.dumps(receipt))

    def test_persisted_unchanged_native_rejection_forbids_later_post(self):
        self.admission()
        self.api.post_mode = 'reject'
        receipt = self.persist()
        self.api.commit_statuses = [{'context':'QIKVRT requested review execution','state':'failure','description':'review rejection: '+receipt['native_rejection_fingerprint']}]
        repeated = self.persist()
        self.assertEqual(repeated['first_blocker'], 'UNCHANGED_NATIVE_REVIEW_REJECTION')
        self.assertEqual(repeated['review_post_count'], 0)
        self.assertEqual(len(self.api.posts), 1)

    def test_lost_acknowledgement_is_read_back_without_retry(self):
        self.admission()
        self.api.post_mode = 'lost'
        self.assertEqual(self.persist()['state'], 'VERIFIED_NATIVE_REVIEW')
        self.assertEqual(len(self.api.posts), 1)

    def test_identity_disappearing_between_decision_and_post_blocks_write(self):
        self.admission()
        self.api.statuses['users/Goldkelch'] = 404
        self.assertEqual(self.persist()['first_blocker'], 'CODEOWNER_IDENTITY_UNRESOLVABLE')
        self.assertEqual(self.api.posts, [])

    def test_head_tree_base_and_scope_drift_before_post_are_read_only(self):
        for path, value in [
            (f'repos/{self.api.repo}/pulls/349', {'state':'open','draft':False,'head':{'sha':'f'*40}}),
            (f'repos/{self.api.repo}/git/commits/{self.snapshot["head_sha"]}', {'tree':{'sha':'f'*40}}),
            (f'repos/{self.api.repo}/commits/main', {'sha':'f'*40}),
        ]:
            self.api = NativeReviewAPI(self.snapshot)
            self.admission()
            self.api.responses[path] = value
            with self.subTest(path=path):
                self.assertEqual(self.persist()['state'], 'HOLD')
                self.assertEqual(self.api.posts, [])

    def test_signer_alias_with_author_id_cannot_self_approve(self):
        self.admission()
        self.signer = {'login':'renamed-author','type':'User','id':1}
        self.assertEqual(self.persist()['first_blocker'], 'NATIVE_REVIEW_SIGNER_SELF_APPROVAL')
        self.assertEqual(self.api.posts, [])

    def test_native_scope_drift_before_post_is_read_only(self):
        self.admission()
        self.api.files_override = [{'filename':'different/scope.py'}]
        self.assertEqual(self.persist()['first_blocker'], 'PREWRITE_SCOPE_DRIFT')
        self.assertEqual(self.api.posts, [])

    def test_successful_old_head_post_cannot_claim_current_head_effect(self):
        self.admission()
        original = self.api.post
        def post(path, payload):
            response = original(path, payload)
            self.api.responses[f'repos/{self.api.repo}/pulls/349']['head']['sha'] = 'f'*40
            return response
        self.api.post = post
        result = self.persist()
        self.assertEqual(result['first_blocker'], 'POSTWRITE_HEAD_DRIFT')
        self.assertEqual(result['review_post_count'], 1)
        self.assertEqual(result['state'], 'HOLD')

    def test_malformed_native_review_id_cannot_be_an_effect_receipt(self):
        self.admission()
        original = self.api.post
        def post(path, payload):
            response = original(path, payload)
            self.api.reviews[-1]['id'] = True
            return response
        self.api.post = post
        result = self.persist()
        self.assertEqual(result['state'], 'HOLD')
        self.assertEqual(result['first_blocker'], 'NATIVE_REVIEW_READBACK_UNVERIFIED')
        self.assertEqual(len(self.api.posts), 1)

    def test_native_http_adapter_discards_secret_bearing_stderr_and_headers(self):
        process = SimpleNamespace(stdout='HTTP/2.0 404 Not Found\nX-Sensitive: SECRET_HEADER\n\n{"message":"Not Found"}\n',stderr='TOKEN_SECRET',returncode=1,timed_out=False,output_limit_exceeded=False)
        with patch.object(MODULE, 'run_bounded', return_value=process):
            result = MODULE.GitHubRest().get('users/Goldkelch')
        self.assertEqual(result['status'], 404)
        self.assertNotIn('SECRET', json.dumps(result))

    def test_workflow_cannot_bypass_native_guard_or_retry_as_comment(self):
        workflow = (ROOT/'.github/workflows/qikvrt_requested_review_executor.yml').read_text()
        self.assertIn('collect_reviewer_admission(snapshot,GitHubRest())', workflow)
        self.assertIn('tools/qikvrt_requested_review_executor.py persist', workflow)
        self.assertNotIn('persisted as COMMENT', workflow)
        self.assertNotIn('if not people and not teams: continue', workflow)
        self.assertIn("steps.decision.outputs.effect_allowed == 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
