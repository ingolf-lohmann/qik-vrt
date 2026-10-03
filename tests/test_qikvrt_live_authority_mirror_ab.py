# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from tools import qikvrt_live_authority_mirror_ab as bench
from tools.qikvrt_authority_credentials import credential, CREDENTIALS


class CredentialBoundaryTests(unittest.TestCase):
    def test_existing_priority_and_app_fallback(self):
        env={name: 'sentinel-'+str(i) for i,name in enumerate(CREDENTIALS)}
        for name in CREDENTIALS:
            token,source,present=credential(env)
            self.assertEqual((token,source),(env[name],name))
            self.assertTrue(present[name])
            del env[name]

    def test_missing_authority_and_mirror_only_fail_before_network(self):
        with patch.dict(os.environ,{'GITHUB_TOKEN':'mirror-sentinel'},clear=True), \
             patch.object(bench,'head') as network, \
             patch.object(bench,'run',return_value=subprocess.CompletedProcess([],0,'a'*40+'\n','')):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(bench.main(),0)
            result=json.loads(output.getvalue())
            self.assertEqual(result['status'],'HOLD_AUTHORITY_CREDENTIAL_DELIVERY_NOT_ESTABLISHED')
            self.assertFalse(result['speedup_claim'])
            self.assertNotIn('wall_speedup_x',result)
            self.assertNotIn('mirror-sentinel',output.getvalue())
            network.assert_not_called()

    def test_token_scope_environment_only_and_no_redirect(self):
        with patch.dict(os.environ,{'GIT_TRACE':'1','GIT_CONFIG_COUNT':'9','QIKVRT_MESH_TOKEN':'sentinel'},clear=True):
            authority=bench.network_environment(bench.AUTHORITY_URL,'sentinel')
            mirror=bench.network_environment(bench.MIRROR_URL,'sentinel')
        self.assertNotIn('GIT_TRACE',authority)
        self.assertNotIn('QIKVRT_MESH_TOKEN',authority)
        self.assertEqual(authority['GIT_CONFIG_KEY_2'],'http.'+bench.AUTHORITY_URL+'.extraheader')
        self.assertEqual(authority['GIT_CONFIG_VALUE_1'],'false')
        self.assertEqual(mirror['GIT_CONFIG_COUNT'],'2')
        self.assertFalse(any('AUTHORIZATION' in value for value in mirror.values()))
        with self.assertRaises(ValueError):
            bench.network_environment('https://example.com/repo','sentinel')

    def test_git_failure_cannot_expose_diagnostics(self):
        failure=subprocess.CompletedProcess([],1,'','sentinel-secret')
        with patch.object(bench.subprocess,'run',return_value=failure):
            with self.assertRaisesRegex(RuntimeError,'^GIT_OPERATION_FAILED$'):
                bench.run('git','fetch')
            self.assertEqual(bench.head(bench.AUTHORITY_URL,'sentinel'),(None,'MAIN_READ_FAILED'))

    def test_git_receives_auth_only_through_environment(self):
        success=subprocess.CompletedProcess([],0,'a'*40+'\trefs/heads/main\n','')
        with patch.object(bench.subprocess,'run',return_value=success) as call:
            self.assertEqual(bench.head(bench.AUTHORITY_URL,'sentinel'),('a'*40,None))
            args,kwargs=call.call_args
            self.assertNotIn('sentinel',repr(args))
            self.assertIn('extraheader',kwargs['env']['GIT_CONFIG_KEY_2'])

    def test_workflow_preserves_fixed_scope(self):
        workflow=(Path(__file__).resolve().parents[1]/'.github/workflows/qikvrt_live_authority_mirror_ab.yml').read_text()
        for text in ('owner: Goldkelch','repositories: qik-vrt','permission-contents: read','persist-credentials: false'):
            self.assertIn(text,workflow)
        self.assertNotIn('contents: write',workflow)
        self.assertNotIn('pull_request_target:',workflow)


if __name__=='__main__':
    unittest.main()
