# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import os
import ast
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_goldkelch_ruleset_authority_effect.yml'

class AuthorityTokenRouteTests(unittest.TestCase):
    def run_route(self, **values):
        source = WORKFLOW.read_text()
        script = source.split('        run: |\n', 1)[1].split('\n      - name:', 1)[0]
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
