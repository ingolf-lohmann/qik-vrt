# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Cold exported S1 + original Owner guard + real monitor proxy, local only."""
import base64
import contextlib
import http.client
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import unittest
import urllib.error
import urllib.request

from tests import test_self_host as standalone

host = standalone.host


class EapExportTests(unittest.TestCase):
    setUpClass = classmethod(standalone.StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(standalone.StandaloneTests.tearDownClass.__func__)
    save_config = standalone.StandaloneTests.save_config
    start = standalone.StandaloneTests.start
    stop = standalone.StandaloneTests.stop
    get = standalone.StandaloneTests.get
    denied = standalone.StandaloneTests.denied

    def command(self, package=None, pin=None):
        command = standalone.StandaloneTests.command(self, package, pin)
        return [command[0], '-S', *command[1:]]

    def setUp(self):
        standalone.StandaloneTests.setUp(self)
        self.owner = 'fixture:owner'
        self.owner_key = 'local-export-fixture-capability-' + 'a' * 40
        token = self.work / 'owner.token'; token.write_text(self.owner_key); token.chmod(0o600)
        self.config.update(terminal_profile='temdd', subject_pr=457, source_repository='ingolf-lohmann/qik-vrt',
            unix_ingress=False, effect_ack_http={'enabled': True, 'public_origin': 'https://raumzeitterminal.de'},
            owner_rest_grants=[{'principal': self.owner, 'token_file': str(token), 'permissions': ['prepare', 'commit', 'readback']}])
        self.save_config()

    def call(self, path, value=None, headers=None):
        fields = {'Authorization': 'Bearer ' + self.owner_key, 'QIKVRT-Owner': self.owner,
                  'Origin': 'https://raumzeitterminal.de', **(headers or {})}
        request = urllib.request.Request(self.url + path, method='POST' if value is not None else 'GET',
            data=host.raw_json(value) if value is not None else None, headers=fields)
        try: response = urllib.request.urlopen(request, timeout=6)
        except urllib.error.HTTPError as error: response = error
        return response.status, dict(response.headers), json.loads(response.read())

    def inputs(self):
        with contextlib.closing(sqlite3.connect((self.volume / 'temdd/events.sqlite3').as_uri() + '?mode=ro', uri=True)) as db:
            return [json.loads(row[0]) for row in db.execute('SELECT body FROM events')
                    if json.loads(row[0]).get('payload', {}).get('adapter') == 'QIKVRT_OWNER_REST_TERMINAL_V1']

    def test_cold_export_owns_complete_public_route_and_original_durable_commit_after_restart(self):
        self.start()
        code, workspace = self.get('/workspace'); self.assertEqual(code, 200)
        self.assertEqual(self.get('/workspace/')[0], 200)
        for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', workspace):
            self.assertEqual(self.get(asset)[0], 200, asset)
        code, access = self.get('/workspace/access.json'); self.assertEqual(code, 200)
        self.assertEqual(access['workspace']['access_release'], 'HOLD')
        self.assertFalse(access['effect_ack_done'])
        original = urllib.request.urlopen(self.url + '/workspace/original.html', timeout=6)
        self.assertEqual(host.digest(original.read()), access['original']['sha256'])
        self.assertIn("style-src 'sha256-", original.headers['Content-Security-Policy'])
        checked = subprocess.run(['node', str(standalone.ROOT / 'tests/test_workspace_live_client.mjs'), self.url],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertIn('WORKSPACE_EXPORTED_CLIENT_PASS', checked.stdout)
        for license_name in ['CC-BY-NC-ND-4.0.txt', 'PolyForm-Noncommercial-1.0.0.txt', 'Apache-2.0.txt', 'REACT_LICENSE.txt']:
            self.assertEqual(self.get('/workspace/licenses/' + license_name)[0], 200)
        request = urllib.request.Request(self.url + '/workspace', data=b'{}', headers={'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(request, timeout=6)
        self.assertEqual(denied.exception.code, 405)
        code, page = self.get('/devops'); self.assertEqual(code, 200)
        for asset in re.findall(r'(?:src|href)="(/assets/[^\"]+)"', page):
            self.assertEqual(self.get(asset)[0], 200, asset)
        self.assertEqual(self.get('/.well-known/effect-ack')[0], 200)
        code, state = self.get('/api/eap/state'); self.assertEqual(code, 200)
        self.assertEqual(state['subject']['head'], self.head)
        self.assertEqual(state['subject']['tree'], self.tree)
        value = {'schema': 'qikvrt_owner_rest_input_v1', 'request_id': 'cold-export-eap-one', 'subject': state['subject'],
                 'input': {'schema': 'qikvrt_terminal_input_v1', 'text': 'Original exported HTTP path: Grüße Ω', 'audio': None, 'video': None}}
        fields = {'Content-Type': 'application/json', 'Effect-Ack-Request': 'v=1, mode=prepare'}
        self.assertEqual(self.call('/api/eap/effect', value, {**fields, 'Origin': 'https://other.example.invalid'})[0], 403)
        self.assertEqual(self.call('/api/eap/effect', value, {**fields, 'Authorization': 'Bearer ' + self.token_file.read_text().strip()})[0], 401)
        self.assertEqual(self.call('/api/eap/effect', value, {**fields, 'QIKVRT-Owner': 'another:owner'})[0], 403)
        code, _, prepared = self.call('/api/eap/effect', value, fields)
        self.assertEqual(code, 200, prepared)
        self.assertEqual(prepared['state'], 'EFFECT_ACK_DONE')
        self.assertEqual(self.inputs(), [])
        self.assertEqual(self.call(prepared['record_url'])[2], prepared['record'])
        context = self.call(prepared['context_url'])[2]
        self.assertEqual(context['latest_hash'], prepared['record']['protocol_hash'])
        raw_hash = bytes.fromhex(prepared['record']['protocol_hash'][7:])
        sf = lambda raw: ':' + base64.b64encode(raw).decode() + ':'
        fields['Effect-Ack-Request'] = 'v=1, mode=commit, token=' + sf(prepared['commit_token'].encode()) + ', hash=' + sf(raw_hash)
        code, _, committed = self.call('/api/eap/effect', value, fields)
        self.assertEqual(code, 200, committed)
        self.assertTrue(committed['independent_readback_verified'])
        self.assertEqual(len(self.inputs()), 1)
        self.assertNotIn(self.owner_key, json.dumps(self.inputs()))
        self.assertFalse((self.volume / 'temdd/ingress.sock').exists())
        self.stop(abrupt=True); self.start()
        code, _, replay = self.call('/api/eap/effect', value, fields)
        self.assertEqual(code, 200, replay)
        self.assertTrue(replay['native_receipt']['replayed'])
        self.assertEqual(replay['native_receipt']['durable_readback'], committed['native_receipt']['durable_readback'])
        self.assertEqual(self.call('/api/eap/receipts/' + value['request_id'])[2]['durable_readback'], committed['native_receipt']['durable_readback'])
        self.assertEqual(len(self.inputs()), 1)

    def test_profile_refuses_alternate_ingress_missing_grants_or_wrong_origin_before_listener(self):
        original = dict(self.config)
        for change in ({'unix_ingress': True}, {'owner_rest_grants': []}, {'terminal_profile': 'reference'},
                {'effect_ack_http': {'enabled': True, 'public_origin': 'https://other.example.invalid'}}):
            with self.subTest(change=change):
                self.config = {**original, **change}; self.save_config()
                self.assertIn('EXPLICIT_EAP_NATIVE_PROFILE_WITHOUT_ALTERNATE_INPUT_PATH_REQUIRED', self.denied())

    def test_monitor_rejects_duplicate_security_headers_and_bounded_route_without_effect(self):
        self.start()
        connection = http.client.HTTPConnection('127.0.0.1', self.config['port'], timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest('GET', '/api/eap/records/' + 'a' * 64)
        for _ in range(2): connection.putheader('Authorization', 'Bearer ' + self.owner_key)
        connection.putheader('QIKVRT-Owner', self.owner); connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 400); self.assertEqual(json.loads(response.read())['error'], 'DUPLICATE_EAP_SECURITY_HEADER')
        self.assertEqual(self.get('/api/eap/state?changed=1')[0], 405)
        self.assertEqual(self.get('/api/eap/effect')[0], 405)
        self.assertEqual(self.get('/api/eap/records/' + 'a' * 64)[0], 401)
        self.assertEqual(self.inputs(), [])


if __name__ == '__main__':
    unittest.main()
