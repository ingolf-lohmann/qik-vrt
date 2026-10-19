# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real original native journal/readback; identity and vault are explicit doubles."""
import copy
import io
import os
from email.message import Message
from types import SimpleNamespace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src import qikvrt_personal_assistant as p
from src import qikvrt_personal_auth as a
if sys.platform == 'linux':
    from src import qikvrt_temdd_event_ledger as n
else:
    n = None
from src import qikvrt_effect_ack_http_terminal as t
from src.qikvrt_effect_ack import ResponsibilityProtocol, verify_protocol, verify_protocol_chain
from tests.test_qikvrt_personal_auth import VaultDouble, IdPDouble, CONFIG


@unittest.skipUnless(n is not None, 'original admitted native writer requires Linux; no other-platform acceptance inferred')
class PersonalTerminalTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / 'source'; source.mkdir()
        for args in [('init',), ('config', 'user.name', 'Native fixture'), ('config', 'user.email', 'fixture@example.invalid')]:
            subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
        (source / 'binding').write_text('native source fixture, not deployed software\n')
        subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(source), 'commit', '-qm', 'fixture'], check=True)
        self.source = source
        exact = n.subject(source, 'ingolf-lohmann/qik-vrt', 542)
        self.current = {**exact, 'worktree_dirty': False, 'sources': {}}
        self.source_patch = patch.object(p, 'subject', side_effect=lambda: copy.deepcopy(self.current))
        self.source_patch.start(); self.addCleanup(self.source_patch.stop)
        self.runtime = p.PersonalRuntime(self.root / 'personal', 'explicit-test-model', 'SIMULATED_MODEL_SECRET', 'L' * 40, transport=object())
        self.addCleanup(self.runtime.close)
        self.runtime.native_terminal = n.Runtime(source, self.root / 'native', exact['repository'], exact['pr'])
        self.vault, self.idp = VaultDouble(), IdPDouble()
        self.auth = a.PersonalAuth(self.vault, CONFIG, transport=self.idp, clock=lambda: 1000)
        with patch.object(a, 'require_crypto_runtime'), patch.object(a, 'verify_id_token'):
            login = self.auth.begin()
            self.bearer = self.auth.complete({'state': login['state'], 'code': 'SIMULATED_CODE'})
        self.runtime.personal_auth = self.auth

    def prepare(self):
        return self.runtime.prepare_terminal_transition(self.bearer)

    def commit(self, prepared):
        return self.runtime.commit_terminal_transition(self.bearer, {'v': 1, 'mode': 'commit', 'token': prepared['commit_token'], 'hash': prepared['record_hash']})

    def test_original_native_commit_cold_readback_and_protocol_chain(self):
        plan = self.prepare()
        self.assertEqual(self.runtime.native_terminal.ledger.replay(0), [])
        result = self.commit(plan)
        self.assertTrue(result['readback_verified'])
        self.assertEqual(result['state'], 'EFFECT_ACK_DONE')
        self.assertEqual(result['effect_scope'], 'AUTHENTICATED_NATIVE_PERSONAL_BINDING_ONLY')
        self.assertFalse(result['productive_sso_verified'])
        self.assertFalse(result['live_identity_observed'])
        first = ResponsibilityProtocol.from_dict(result['protocol'])
        verify_protocol(first)
        read = self.runtime.read_terminal_transition(self.bearer)
        second = ResponsibilityProtocol.from_dict(read['protocol'])
        verify_protocol_chain([first])
        self.assertEqual(first.protocol_hash, second.protocol_hash)  # Existing engine deduplicates unchanged decisions.
        self.assertEqual(result['event_id'], read['event_id'])
        event = self.runtime.terminal_binding['event']
        code = "import json,sys;from src.qikvrt_effect_ack_http_terminal import _durable_read;d=json.load(sys.stdin);print(json.dumps(_durable_read(d['state'],d['event'])[1],sort_keys=True))"
        cold = subprocess.run([sys.executable, '-B', '-c', code], input=json.dumps({'state': str(self.root / 'native'), 'event': event}), text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(cold.stdout), read['native_event'])
        raw = json.dumps(read)
        for secret in [self.bearer, 'SIMULATED_MODEL_SECRET', *self.auth.sensitive_values()]:
            self.assertNotIn(secret, raw)

    def test_fresh_auth_refreshes_exactly_once_before_preparation(self):
        self.auth.observed = False
        before = self.idp.n
        self.prepare()
        self.assertEqual(self.idp.n, before + 1)

    def test_pending_authorization_rejects_transition_without_refresh(self):
        with patch.object(a, 'require_crypto_runtime'):
            self.auth.begin()
        before = self.idp.n
        with self.assertRaisesRegex(ValueError, 'AUTHORIZATION_ALREADY_PENDING'): self.prepare()
        self.assertEqual(self.idp.n, before)

    def test_changed_or_foreign_commit_cannot_append(self):
        plan = self.prepare()
        with self.assertRaises(ValueError):
            self.runtime.commit_terminal_transition(self.bearer, {'v': 1, 'mode': 'commit', 'token': plan['commit_token'], 'hash': '0' * 64})
        self.assertEqual(self.runtime.native_terminal.ledger.replay(0), [])
        self.commit(plan)
        with self.assertRaises(ValueError):
            self.commit(plan)
        self.assertEqual(len(self.runtime.native_terminal.ledger.replay(0)), 1)

    def test_expired_preparation_cannot_append(self):
        plan = self.prepare()
        self.runtime.terminal_prepared['until'] = 0
        with self.assertRaises(ValueError): self.commit(plan)
        self.assertEqual(self.runtime.native_terminal.ledger.replay(0), [])

    def test_source_mutation_invalidates_preparation_and_readback(self):
        plan = self.prepare()
        (self.source / 'binding').write_text('changed')
        with self.assertRaises(ValueError): self.commit(plan)
        self.assertEqual(self.runtime.native_terminal.ledger.replay(0), [])

    def test_personal_payload_mutation_is_rejected_before_refresh(self):
        self.current['sources']['changed'] = {'sha256': 'a' * 64}
        before = self.idp.n
        with self.assertRaises(ValueError): self.prepare()
        self.assertEqual(self.idp.n, before)

    def test_foreign_bearer_logout_and_pending_auth_fail_closed(self):
        with self.assertRaises(ValueError): self.runtime.prepare_terminal_transition('foreign')
        plan = self.prepare()
        self.auth.logout()
        with self.assertRaises(ValueError): self.commit(plan)
        with self.assertRaises(ValueError): self.runtime.read_terminal_transition(self.bearer)

    def test_legacy_mode_cannot_promote_to_personal_binding(self):
        self.runtime.personal_auth = None
        with self.assertRaises(ValueError): self.prepare()

    def test_unadmitted_native_runtime_is_rejected(self):
        native = self.runtime.native_terminal
        self.runtime.native_terminal = None
        try:
            with self.assertRaises(ValueError): self.prepare()
        finally: self.runtime.native_terminal = native

    def test_lost_commit_response_uses_readback_without_duplicate(self):
        plan = self.prepare()
        self.commit(plan)  # Deliberately discard the returned acknowledgement.
        read = self.runtime.read_terminal_transition(self.bearer)
        self.assertTrue(read['readback_verified'])
        self.assertEqual(len(self.runtime.native_terminal.ledger.replay(0)), 1)

    def test_cold_read_failure_holds_and_later_read_recovers_without_write(self):
        plan = self.prepare()
        with patch.object(t, '_durable_read', side_effect=t.DurableHold('READ_UNAVAILABLE')):
            with self.assertRaises(ValueError): self.commit(plan)
        with self.assertRaises(ValueError): self.commit(plan)
        self.assertTrue(self.runtime.read_terminal_transition(self.bearer)['readback_verified'])
        self.assertEqual(len(self.runtime.native_terminal.ledger.replay(0)), 1)

    def http(self, path, *, body=None, bearer=None, origin='http://127.0.0.1:8771', binding=None):
        # Exercise the actual handler without assuming a socket capability.
        handler = p.personal_handler(t.Handler, self.runtime).__new__(p.personal_handler(t.Handler, self.runtime))
        handler.server = SimpleNamespace(server_port=8771)
        handler.path, handler.requestline, handler.request_version = path, 'test', 'HTTP/1.1'
        handler.command = 'GET' if body is None else 'POST'
        handler.headers = Message()
        for key, value in {'Host':'127.0.0.1:8771','Origin':origin,'Authorization':'Bearer ' + (bearer or self.bearer),
                'Content-Type':'application/json', 'Content-Length':str(len(json.dumps(body).encode()))}.items():
            if value is not None: handler.headers[key] = value
        if binding is not None: handler.headers['Effect-Ack-Request'] = binding
        handler.wfile, handler.rfile = io.BytesIO(), io.BytesIO(json.dumps(body).encode())
        if body is None: handler.do_GET()
        else: handler.do_POST()
        header, raw = handler.wfile.getvalue().split(b'\r\n\r\n', 1)
        return int(header.split()[1]), json.loads(raw), header.decode()

    def test_http_origin_confirmation_eap_and_bearer_fail_before_write(self):
        for changes in [{'origin':'moz-extension://foreign'}, {'body':{}}, {'bearer':'foreign'}, {'binding':None}]:
            args={'body':{'confirmed':True}, 'binding':'v=1, mode=prepare', **changes}
            code, _, _ = self.http('/personal/terminal/prepare', **args)
            self.assertNotEqual(code, 200)
        self.assertEqual(self.runtime.native_terminal.ledger.replay(0), [])

    def test_http_handoff_and_authenticated_get_have_eap_without_cors(self):
        code, plan, header = self.http('/personal/terminal/prepare', body={'confirmed':True}, binding='v=1, mode=prepare')
        self.assertEqual(code, 200)
        self.assertIn('state=continue', header)
        sf='v=1, mode=commit, token='+t.sf_bytes(plan['commit_token'].encode())+', hash='+t.sf_bytes(bytes.fromhex(plan['record_hash']))
        code, result, header = self.http('/personal/terminal/commit', body={'confirmed':True}, binding=sf)
        self.assertEqual(code, 200)
        self.assertIn('state=done', header)
        self.assertNotIn('Access-Control-Allow-Origin', header)
        code, read, _ = self.http('/personal/terminal/readback')
        self.assertEqual(code, 200)
        self.assertEqual(result['event_id'], read['event_id'])

    def test_native_mode_cannot_read_sessions_before_binding(self):
        code, _, _ = self.http('/personal/sessions')
        self.assertNotEqual(code, 200)
        self.commit(self.prepare())
        code, result, _ = self.http('/personal/sessions')
        self.assertEqual(code, 200)
        self.assertEqual(result['sessions'], [])

    def test_ambiguous_native_append_reconciles_exact_event_without_retry(self):
        plan = self.prepare()
        append = self.runtime.native_terminal.append
        def lost_ack(event):
            append(event)
            raise n.Hold('SIMULATED_LOST_NATIVE_ACK')
        with patch.object(self.runtime.native_terminal, 'append', side_effect=lost_ack):
            with self.assertRaises(ValueError): self.commit(plan)
        with self.assertRaises(ValueError): self.commit(plan)
        read = self.runtime.read_terminal_transition(self.bearer)
        self.assertTrue(read['readback_verified'])
        self.assertEqual(len(self.runtime.native_terminal.ledger.replay(0)), 1)


if __name__ == '__main__':
    unittest.main()
