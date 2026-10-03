# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

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
