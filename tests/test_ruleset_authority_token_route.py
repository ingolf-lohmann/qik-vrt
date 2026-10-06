# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import ast
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/qikvrt_goldkelch_ruleset_authority_effect.yml'
POLICY = ROOT / 'policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json'


def python_step(path, step):
    source = path.read_text()
    block = source.split(f'      - name: {step}\n', 1)[1].split('\n      - name:', 1)[0]
    lines = textwrap.dedent(block.split('        run: |\n', 1)[1]).splitlines()
    start = next(i for i, line in enumerate(lines) if "<<'PY'" in line) + 1
    end = lines.index('PY', start)
    return '\n'.join(lines[start:end]) + '\n'


def env_value(path, name):
    match = re.search(rf'^\s+{re.escape(name)}: (.+)$', path.read_text(), re.M)
    if match is None:
        raise AssertionError(f'missing environment binding: {name}')
    return match.group(1).strip().strip('"')


def required_gates(path):
    match = re.search(r'REQUIRED_GATES_JSON: >-\n\s+(\[.*\])', path.read_text())
    if match is None:
        raise AssertionError('missing required gate bindings')
    return json.loads(match.group(1))

class AuthorityTokenRouteTests(unittest.TestCase):
    def run_route(self, **values):
        source = WORKFLOW.read_text()
        block = source.split('      - name: Resolve least-privilege authority route\n', 1)[1]
        script = block.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'output'
            env = {'PATH': os.environ['PATH'], 'GITHUB_OUTPUT': str(output), **values}
            result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True, timeout=5)
            return result.returncode, output.read_text(), result.stderr

    def test_canonical_name_admits_direct_route(self):
        code, output, _ = self.run_route(RULESET_ADMIN_TOKEN='fixture-only')
        self.assertEqual(code, 0)
        self.assertIn('direct=true', output)
        self.assertNotIn('fixture-only', output)

    def test_empty_inputs_fail_closed(self):
        code, output, error = self.run_route()
        self.assertNotEqual(code, 0)
        self.assertIn('direct=false', output)
        self.assertIn('No repository-provided authority', error)

    def test_app_route_still_requires_both_inputs(self):
        self.assertNotEqual(self.run_route(RULESET_APP_ID='fixture')[0], 0)
        code, output, _ = self.run_route(RULESET_APP_ID='fixture', RULESET_APP_PRIVATE_KEY='fixture')
        self.assertEqual(code, 0)
        self.assertIn('app=true', output)
        self.assertIn('direct=false', output)

    def test_target_and_conditional_guards_are_retained(self):
        source = WORKFLOW.read_text()
        for guard in ['TARGET_REPOSITORY: ${{ github.repository }}', 'headers["If-Match"] = etag',
                      'if reobserved_hash != pre_hash:', 'if post_hash != expected_post:',
                      'RULESET_ADMIN_TOKEN: ${{ secrets.QIKVRT_RULESET_ADMIN_TOKEN }}']:
            self.assertIn(guard, source)
        self.assertLess(source.index('os.environ.get("RULESET_ADMIN_TOKEN"'), source.index('os.environ.get("ADMIN_TOKEN"'))

    def projection(self):
        source = WORKFLOW.read_text().split("          python3 - <<'PY'\n", 1)[1].rsplit('\n          PY', 1)[0]
        script = '\n'.join(line[10:] for line in source.splitlines())
        tree = ast.parse(script)
        desired = next(ast.literal_eval(node.value) for node in tree.body
                       if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == 'desired'
                               for target in node.targets))
        desired.update(id=42, source='ingolf-lohmann/qik-vrt')
        return script, desired

    def execute_projection(self, replies):
        script, _ = self.projection()
        calls = []
        def response(request, timeout):
            calls.append(request)
            value, etag = replies[len(calls) - 1]
            stream = io.BytesIO(json.dumps(value).encode())
            stream.headers = {'ETag': etag} if etag else {}
            return stream
        environment = {
            'TARGET_REPOSITORY': 'ingolf-lohmann/qik-vrt',
            'RULESET_NAME': 'QIK-VRT main protection',
            'RULESET_ADMIN_TOKEN': 'fixture-only',
            'EXPECTED_POST_SHA256': '45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd',
        }
        output = io.StringIO()
        with mock.patch.dict(os.environ, environment, clear=True), \
             mock.patch('urllib.request.urlopen', side_effect=response), \
             contextlib.redirect_stdout(output):
            try:
                exec(compile(script, str(WORKFLOW), 'exec'), {})
            except SystemExit as exc:
                if exc.code != 0:
                    return calls, output.getvalue(), str(exc)
        return calls, output.getvalue(), None

    def test_changed_preimage_never_updates(self):
        _, desired = self.projection()
        initial = copy.deepcopy(desired)
        initial['enforcement'] = 'evaluate'
        drifted = copy.deepcopy(initial)
        drifted['enforcement'] = 'disabled'
        calls, output, error = self.execute_projection([
            ([desired], None), (initial, 'v1'), (drifted, 'v2')])
        self.assertEqual([call.get_method() for call in calls], ['GET', 'GET', 'GET'])
        self.assertIn('drifted after planning', error)
        self.assertEqual(output, '')

    def test_missing_etag_never_updates(self):
        _, desired = self.projection()
        initial = copy.deepcopy(desired)
        initial['enforcement'] = 'evaluate'
        calls, output, error = self.execute_projection([
            ([desired], None), (initial, None), (initial, None)])
        self.assertEqual([call.get_method() for call in calls], ['GET', 'GET', 'GET'])
        self.assertIn('conditional update unavailable', error)
        self.assertEqual(output, '')

    def test_update_binds_reobserved_etag_and_protection_readback(self):
        _, desired = self.projection()
        initial = copy.deepcopy(desired)
        initial['enforcement'] = 'evaluate'
        calls, output, error = self.execute_projection([
            ([desired], None), (initial, 'v1'), (initial, 'v2'),
            (desired, 'v3'), (desired, 'v3')])
        self.assertIsNone(error)
        self.assertEqual([call.get_method() for call in calls], ['GET', 'GET', 'GET', 'PUT', 'GET'])
        self.assertEqual(calls[3].get_header('If-match'), 'v2')
        sent = json.loads(calls[3].data)
        self.assertEqual(sent['enforcement'], 'active')
        self.assertEqual(sent['bypass_actors'], [])
        rules = {rule['type']: rule for rule in sent['rules']}
        review = rules['pull_request']['parameters']
        self.assertTrue(review['require_code_owner_review'])
        self.assertTrue(review['require_last_push_approval'])
        self.assertTrue(review['dismiss_stale_reviews_on_push'])
        self.assertEqual(review['required_approving_review_count'], 1)
        self.assertEqual({check['context'] for check in rules['required_status_checks']['parameters']['required_status_checks']},
                         {'test', 'QIKVRT required code-owner review'})
        self.assertIn('non_fast_forward', rules)
        self.assertTrue(json.loads(output)['effect_observed'])

    def test_wrong_postimage_does_not_claim_effect(self):
        _, desired = self.projection()
        initial = copy.deepcopy(desired)
        initial['enforcement'] = 'evaluate'
        calls, output, error = self.execute_projection([
            ([desired], None), (initial, 'v1'), (initial, 'v2'),
            (desired, 'v3'), (initial, 'v3')])
        self.assertEqual(calls[-1].get_method(), 'GET')
        self.assertIn('post-effect digest mismatch', error)
        self.assertEqual(output, '')


class RequiredReviewContextContractTests(unittest.TestCase):
    repository = 'ingolf-lohmann/qik-vrt'
    head = 'b' * 40
    base = 'a' * 40
    gate = ROOT / '.github/workflows/qikvrt_required_review_gate.yml'
    executor = ROOT / '.github/workflows/qikvrt_requested_review_executor.yml'
    promotion = ROOT / '.github/workflows/qikvrt_expected_head_promotion.yml'

    def setUp(self):
        model = json.loads(POLICY.read_text())['review_executor']
        self.context = model['native_governance_status_context']
        self.legacy = model['legacy_native_governance_status_alias']
        self.disposition = model['exact_head_status_context']

    def run_writer(self, *, calls=None, **overrides):
        if calls is None:
            calls = []
        created = None

        def urlopen(request, *, timeout):
            nonlocal created
            self.assertEqual(timeout, 30)
            method = request.get_method()
            payload = json.loads(request.data) if request.data is not None else None
            calls.append((method, request.full_url, payload))
            if method == 'GET' and request.full_url.endswith('/rulesets'):
                response = []
            elif method == 'POST' and request.full_url.endswith('/rulesets'):
                created = dict(payload, id=123, source=self.repository)
                response = created
            elif method == 'GET' and request.full_url.endswith('/rulesets/123'):
                response = created
            else:
                raise AssertionError(f'unexpected ruleset request: {method} {request.full_url}')
            stream = io.BytesIO(json.dumps(response).encode())
            stream.headers = {'ETag': '"fixture-only"'}
            return stream

        env = {
            'TARGET_REPOSITORY': self.repository,
            'RULESET_NAME': 'QIK-VRT main protection',
            'RULESET_ADMIN_TOKEN': 'fixture-only',
            'EXPECTED_POST_SHA256': env_value(WORKFLOW, 'EXPECTED_POST_SHA256'),
            **overrides,
        }
        namespace = {}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch('urllib.request.urlopen', side_effect=urlopen), contextlib.redirect_stdout(io.StringIO()):
            exec(compile(python_step(WORKFLOW, 'Conditional canonical projection with exact readback'), str(WORKFLOW), 'exec'), namespace)
        return created, namespace, calls

    def run_gate(self):
        calls = []
        pr = {'number': 641, 'state': 'open', 'base': {'ref': 'main', 'sha': self.base}, 'head': {'sha': self.head}, 'user': {'login': 'integration-author'}}

        def read(args, *, text):
            self.assertEqual(args[:2], ['gh', 'api'])
            path = args[-1]
            if path == f'repos/{self.repository}/pulls/641':
                return json.dumps(pr)
            if path == f'repos/{self.repository}/rules/branches/main':
                return '[]'
            if path == f'repos/{self.repository}/pulls/641/reviews?per_page=100':
                return '[[]]'
            raise AssertionError(f'unexpected gate read: {path}')

        env = {
            'REPOSITORY': self.repository,
            'REQUESTED_PR': '641',
            'EVENT_NAME': 'workflow_dispatch',
            'EVENT_PRS': '[]',
            'STATUS_CONTEXT': env_value(self.gate, 'STATUS_CONTEXT'),
            'LEGACY_STATUS_CONTEXT': env_value(self.gate, 'LEGACY_STATUS_CONTEXT'),
            'GITHUB_SERVER_URL': 'https://github.com',
            'GITHUB_RUN_ID': '123',
        }
        with tempfile.TemporaryDirectory() as directory:
            env['GITHUB_STEP_SUMMARY'] = str(Path(directory) / 'summary')
            with mock.patch.dict(os.environ, env, clear=True), mock.patch('subprocess.check_output', side_effect=read), mock.patch('subprocess.check_call', side_effect=lambda args: calls.append(args) or 0), contextlib.redirect_stdout(io.StringIO()):
                exec(compile(python_step(self.gate, 'Reobserve native rules and exact-head reviews'), str(self.gate), 'exec'), {})
        self.assertEqual(len(calls), 2)
        published=[]
        for command in calls:
            self.assertEqual(command[:5], ['gh', 'api', '--method', 'POST', f'repos/{self.repository}/statuses/{self.head}'])
            fields = dict(arg.split('=', 1) for arg in command[5:] if '=' in arg)
            self.assertEqual(fields['state'], 'failure')
            self.assertIn('CODE_OWNER_RULE_NOT_ENFORCED', fields['description'])
            published.append(fields)
        self.assertEqual({item['context'] for item in published}, {self.context,self.legacy})
        return published

    def run_promotion_snapshot(self, statuses, *, native_satisfied=False):
        gates = required_gates(self.promotion)
        pr = {'number': 641, 'state': 'open', 'base': {'ref': 'main', 'sha': self.base}, 'head': {'sha': self.head}, 'user': {'login':'integration-author'}, 'draft': False, 'mergeable': True}

        def read(args, *, text):
            self.assertEqual(args[:2], ['gh', 'api'])
            path = args[-1]
            if path == f'repos/{self.repository}/pulls/641':
                return json.dumps(pr)
            if path == f'repos/{self.repository}/commits/main':
                return json.dumps({'sha': self.base})
            if path == f'repos/{self.repository}/actions/runs?head_sha={self.head}&event=pull_request&per_page=100':
                return json.dumps([{'workflow_runs': [{'name': name, 'status': 'completed', 'conclusion': 'success', 'run_number': 1} for name in gates if name != self.context]}])
            if path == f'repos/{self.repository}/commits/{self.head}/statuses?per_page=100':
                return json.dumps([statuses])
            if path == f'repos/{self.repository}/rules/branches/main':
                return json.dumps([{'type':'pull_request','parameters':{'require_code_owner_review':True,'required_approving_review_count':1,'dismiss_stale_reviews_on_push':True,'require_last_push_approval':True}}]) if native_satisfied else '[]'
            if path == f'repos/{self.repository}/pulls/641/reviews?per_page=100':
                return json.dumps([[{'id':4,'user':{'login':'ingolf-lohmann','type':'User'},'state':'APPROVED','commit_id':self.head,'submitted_at':'2026-10-06T21:00:00Z'}]]) if native_satisfied else '[[]]'
            if path == f'repos/{self.repository}/pulls/641/files?per_page=100':
                return '[[{"filename":"fixture.txt"}]]'
            if path == f'repos/{self.repository}/pulls?state=open&base=main&per_page=100':
                return json.dumps([[pr]])
            raise AssertionError(f'unexpected promotion read: {path}')

        env = {'REPOSITORY': self.repository, 'PR_NUMBER': '641', 'REQUIRED_GATES_JSON': json.dumps(gates), 'REVIEW_STATUS_CONTEXT': env_value(self.promotion, 'REVIEW_STATUS_CONTEXT')}
        output = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), mock.patch('subprocess.check_output', side_effect=read), contextlib.redirect_stdout(output):
            exec(compile(python_step(self.promotion, 'Materialize exact live promotion snapshot including review receipt'), str(self.promotion), 'exec'), {})
        return json.loads(output.getvalue())

    def test_writer_and_generated_status_use_policy_context(self):
        desired, namespace, calls = self.run_writer()
        statuses = self.run_gate()
        fields = next(item for item in statuses if item['context'] == self.context)
        checks = next(rule['parameters']['required_status_checks'] for rule in desired['rules'] if rule['type'] == 'required_status_checks')
        self.assertEqual(self.context, 'QIKVRT required code-owner review')
        self.assertEqual(fields['context'], self.context)
        self.assertIn({'context': fields['context'], 'integration_id': 15368}, checks)
        # Name equality never turns publisher execution into native acceptance.
        self.assertNotEqual(self.context, self.disposition)
        self.assertNotEqual(self.context, self.legacy)
        self.assertEqual([call[0] for call in calls], ['GET', 'POST', 'GET'])
        self.assertEqual(namespace['post_hash'], env_value(WORKFLOW, 'EXPECTED_POST_SHA256'))

    def test_writer_retains_native_protection_without_bypasses(self):
        desired, _, _ = self.run_writer()
        self.assertEqual(desired['enforcement'], 'active')
        self.assertEqual(desired['conditions'], {'ref_name': {'exclude': [], 'include': ['refs/heads/main']}})
        self.assertEqual(desired['bypass_actors'], [])
        rules = {rule['type']: rule.get('parameters') for rule in desired['rules']}
        self.assertEqual(set(rules), {'pull_request', 'required_status_checks', 'non_fast_forward', 'deletion'})
        self.assertEqual(rules['pull_request'], {
            'allowed_merge_methods': ['merge', 'squash', 'rebase'],
            'dismiss_stale_reviews_on_push': True,
            'require_code_owner_review': True,
            'require_extra_approval_for_unattributed_changes': True,
            'require_last_push_approval': True,
            'required_approving_review_count': 1,
            'required_review_thread_resolution': True,
            'required_reviewers': [],
        })
        self.assertEqual(rules['required_status_checks'], {
            'do_not_enforce_on_create': False,
            'required_status_checks': [
                {'context': self.context, 'integration_id': 15368},
                {'context': 'test', 'integration_id': 15368},
            ],
            'strict_required_status_checks_policy': True,
        })

    def test_executor_binds_both_published_status_paths(self):
        self.assertEqual(env_value(self.executor, 'STATUS_CONTEXT'), self.disposition)
        source = self.executor.read_text()
        for step in ['Persist precise waiting state', 'Persist substantive review disposition']:
            block = source.split(f'      - name: {step}\n', 1)[1].split('\n      - name:', 1)[0]
            self.assertIn('/statuses/${EXPECTED_HEAD}', block)
            self.assertIn('-f context="$STATUS_CONTEXT"', block)

    def test_executor_generates_canonical_waiting_and_disposition_status(self):
        source = self.executor.read_text()
        for step, disposition, expected_state in [
            ('Persist precise waiting state', 'WAIT', 'pending'),
            ('Persist substantive review disposition', 'APPROVE', 'success'),
            ('Persist substantive review disposition', 'COMMENT_WITH_BLOCKER', 'failure'),
        ]:
            with self.subTest(disposition=disposition), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                decision = root / 'qikvrt-review-decision.json'
                decision.write_text(json.dumps({'detail': 'fixture-only', 'reviewed_scope': ['fixture.txt']}))
                gh = root / 'gh'
                gh.write_text(
                    f'#!{sys.executable}\n'
                    'import json, os, sys\n'
                    'with open(os.environ["QIKVRT_TEST_GH_CALLS"], "a") as out:\n'
                    '    out.write(json.dumps(sys.argv[1:]) + "\\n")\n'
                    'print(os.environ["EXPECTED_HEAD"] if "--jq" in sys.argv else "{}")\n'
                )
                gh.chmod(0o700)
                block = source.split(f'      - name: {step}\n', 1)[1].split('\n      - name:', 1)[0]
                script = textwrap.dedent(block.split('        run: |\n', 1)[1]).replace('/tmp/qikvrt-review-', str(root / 'qikvrt-review-'))
                env = {
                    'PATH': str(root) + os.pathsep + os.environ['PATH'],
                    'REPOSITORY': self.repository,
                    'PR_NUMBER': '641',
                    'EXPECTED_HEAD': self.head,
                    'EXPECTED_TREE': 'c' * 40,
                    'DISPOSITION': disposition,
                    'STATUS_CONTEXT': env_value(self.executor, 'STATUS_CONTEXT'),
                    'REVIEW_MARKER': 'fixture-only',
                    'GITHUB_SERVER_URL': 'https://github.com',
                    'GITHUB_REPOSITORY': self.repository,
                    'GITHUB_RUN_ID': '123',
                    'QIKVRT_TEST_GH_CALLS': str(root / 'calls.jsonl'),
                }
                result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]
                statuses = [args for args in calls if f'repos/{self.repository}/statuses/{self.head}' in args]
                self.assertEqual(len(statuses), 1)
                self.assertIn(f'context={self.disposition}', statuses[0])
                review_calls = [args for args in calls if f'repos/{self.repository}/pulls/641/reviews' in args]
                self.assertFalse(any('event=APPROVE' in args for args in review_calls))
                if disposition == 'APPROVE':
                    self.assertEqual(len(review_calls), 1)
                    self.assertIn('event=COMMENT', review_calls[0])
                self.assertIn(f'state={expected_state}', statuses[0])

    def test_policy_and_exact_head_contract_bind_every_consumer(self):
        policy = json.loads(POLICY.read_text())['review_executor']
        binding = policy['required_check_binding']
        self.assertEqual(binding['context_source'], 'review_executor.native_governance_status_context')
        self.assertEqual(ROOT / binding['ruleset_writer'], WORKFLOW)
        self.assertEqual(ROOT / binding['native_review_gate'], self.gate)
        self.assertFalse(binding['workflow_execution_success_satisfies_governance'])
        self.assertFalse(binding['technical_disposition_is_acceptance_substitute'])
        self.assertFalse(binding['legacy_alias_is_acceptance_substitute'])
        self.assertEqual(binding['trusted_status_integration_id'], 15368)
        from tools.qikvrt_required_review_gate import GOVERNANCE_STATUS_CONTEXT, LEGACY_GOVERNANCE_STATUS_CONTEXT, REVIEW_DISPOSITION_STATUS_CONTEXT
        self.assertEqual((self.context,self.legacy,self.disposition), (GOVERNANCE_STATUS_CONTEXT,LEGACY_GOVERNANCE_STATUS_CONTEXT,REVIEW_DISPOSITION_STATUS_CONTEXT))
        self.assertEqual(env_value(self.promotion, 'REVIEW_STATUS_CONTEXT'), self.context)
        self.assertIn(self.context, required_gates(self.promotion))
        self.assertNotIn(self.legacy, required_gates(self.promotion))
        self.assertNotIn(self.disposition, required_gates(self.promotion))
        self.assertTrue(binding['native_code_owner_approval_still_required'])
        self.assertEqual(binding['administrative_ruleset_activation'], 'SEPARATE_EFFECT')
        contract = (ROOT / policy['contract_gate']).read_text()
        for path in [WORKFLOW, self.gate, self.executor, self.promotion, Path(__file__)]:
            self.assertIn(f'"{path.relative_to(ROOT).as_posix()}"', contract)
        self.assertIn('github.event.pull_request.head.sha || github.sha', contract)
        self.assertIn('tests.test_ruleset_authority_token_route', contract)

    def test_promotion_consumes_generated_status_and_stays_closed(self):
        statuses = self.run_gate()
        fields = next(item for item in statuses if item['context'] == self.context)
        snapshot = self.run_promotion_snapshot([{'id': 7, 'context': fields['context'], 'state': fields['state']}])
        review = next(run for run in snapshot['workflow_runs'] if run['name'] == self.context)
        self.assertEqual(review, {'name': self.context, 'status': 'completed', 'conclusion': 'failure', 'run_number': 7})
        from tools.qikvrt_expected_head_promotion import evaluate_promotion
        result = evaluate_promotion(snapshot)
        self.assertEqual(result['state'], 'BLOCK')
        self.assertEqual(result['first_blocker'], 'CODE_OWNER_RULE_NOT_ENFORCED')

    def test_legacy_and_technical_statuses_cannot_satisfy_native_prerequisite(self):
        snapshot = self.run_promotion_snapshot([{'id': 8, 'context': context, 'state': 'success'} for context in [self.legacy,self.disposition]])
        review = next(run for run in snapshot['workflow_runs'] if run['name'] == self.context)
        self.assertEqual(review, {'name': self.context, 'status': 'in_progress', 'conclusion': None, 'run_number': 0})
        from tools.qikvrt_expected_head_promotion import evaluate_promotion
        result = evaluate_promotion(snapshot)
        self.assertEqual(result['state'], 'BLOCK')
        self.assertEqual(result['first_blocker'], 'CODE_OWNER_RULE_NOT_ENFORCED')

    def test_green_publisher_workflow_and_alias_cannot_supply_native_status(self):
        snapshot = self.run_promotion_snapshot([{'id':8,'context':context,'state':'success'} for context in [self.legacy,self.disposition]], native_satisfied=True)
        from tools.qikvrt_expected_head_promotion import evaluate_promotion
        self.assertEqual(evaluate_promotion(snapshot)['first_blocker'], 'NATIVE_GOVERNANCE_STATUS_MISSING')

    def test_generated_native_status_requires_separate_current_head_approval(self):
        snapshot = self.run_promotion_snapshot([{'id':8,'context':self.context,'state':'success'}], native_satisfied=True)
        from tools.qikvrt_expected_head_promotion import evaluate_promotion
        self.assertEqual(evaluate_promotion(snapshot)['state'], 'PROMOTABLE')
        self.assertEqual(snapshot['governance_projection']['native_review_gate']['review_id'], 4)

    def test_digest_drift_blocks_before_any_api_request(self):
        calls = []
        with self.assertRaisesRegex(SystemExit, 'desired digest mismatch'):
            self.run_writer(calls=calls, EXPECTED_POST_SHA256='0' * 64)
        self.assertEqual(calls, [])
