# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Actual recovered daemon in a Git-free S1 export, never a substitute fixture."""
from __future__ import annotations
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest

from tests.test_self_host import StandaloneTests, host, ROOT


class SourceRecoveryTests(unittest.TestCase):
    def test_every_recovered_source_keeps_its_original_blob_identity(self):
        r = json.loads((ROOT / 'evidence/self_host/SOURCE_RECOVERY_20261005.json').read_bytes())
        self.assertEqual(r['result'], 'EXACT_HISTORICAL_ORIGINAL_BLOBS_RECOVERED')
        self.assertFalse(r['boundaries']['effect_ack_done'])
        for f in r['files']:
            raw = (ROOT / f['restored_path']).read_bytes()
            self.assertEqual(len(raw), f['bytes'], f['restored_path'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), f['sha256'])
            self.assertEqual(hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest(), f['git_blob_sha1'])

    def test_native_kernel_is_in_the_export_and_no_provider_is_required(self):
        definition = json.loads((ROOT / host.DEFINITION).read_bytes())
        self.assertTrue(definition['native_terminal_daemon_included'])
        self.assertIn('src/qikvrt_temdd_event_ledger.py', definition['files'])
        self.assertEqual(definition['providers_required'], [])


class NativeStandaloneTests(unittest.TestCase):
    # Reuse the existing export/process helpers. Existing reference cases are
    # still executed unchanged; no duplicated test daemon implements this path.
    setUpClass = classmethod(StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(StandaloneTests.tearDownClass.__func__)
    save_config = StandaloneTests.save_config
    command = StandaloneTests.command
    start = StandaloneTests.start
    stop = StandaloneTests.stop
    get = StandaloneTests.get
    denied = StandaloneTests.denied

    def setUp(self):
        StandaloneTests.setUp(self)
        self.config.update(terminal_profile='temdd', subject_pr=457, source_repository='ingolf-lohmann/qik-vrt')
        self.save_config()

    def cli(self, operation, prepared=None, path=None):
        body = self.work / 'input.json'
        body.write_text(json.dumps({'schema':'qikvrt_terminal_input_v1','text':'private-test-input: Grüße Ω'}))
        args = [sys.executable,'-B',str(self.export/'src/qikvrt_effect_ack_http_terminal.py'),operation,
            '--root',str(self.export),'--state-dir',str(self.volume),'--repository','ingolf-lohmann/qik-vrt',
            '--pr','457','--expected-head',self.head,'--expected-tree',self.tree,'--manifest-sha256',self.pin,'--input',str(body)]
        if prepared:
            file = self.work / 'prepared.json'; file.write_bytes(host.raw_json(prepared)); file.chmod(0o600)
            args += ['--prepared',str(file),'--prepare-hash',prepared['prepare_hash']]
        env = dict(os.environ)
        if path is not None: env['PATH'] = str(path)
        result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=10)
        return result.returncode, json.loads(result.stdout)

    def sql(self, query):
        path = self.volume / 'temdd/events.sqlite3'
        with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as db:
            return db.execute(query).fetchall()

    def commit_input(self):
        code, prepared = self.cli('durable-prepare')
        self.assertEqual(code, 0, prepared)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(0,)])
        code, receipt = self.cli('durable-commit', prepared)
        self.assertEqual(code, 0, receipt)
        self.assertTrue(receipt['durable_persisted'])
        self.assertFalse(receipt['EFFECT_ACK_DONE'])
        return prepared, receipt['durable_readback']

    def test_actual_daemon_owner_commit_and_fresh_sqlite_sse_readback(self):
        runtime = self.start()
        self.assertTrue(runtime['native_terminal_daemon_available'])
        prepared, event = self.commit_input()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])
        self.assertEqual(event['subject']['head'], self.head)
        self.assertEqual(event['subject']['tree'], self.tree)
        self.assertFalse(event['dod'])
        c = http.client.HTTPConnection('127.0.0.1', self.config['terminal_port'], timeout=5)
        try:
            c.request('GET', '/api/temdd/events')
            response = c.getresponse(); self.assertEqual(response.status, 200)
            frames = []
            for _ in range(2):
                lines = []
                while True:
                    line = response.readline()
                    self.assertTrue(line)
                    if line == b'\n': break
                    lines.append(line)
                frames.append(b''.join(lines))
            data = next(line[6:] for line in frames[1].splitlines() if line.startswith(b'data: '))
            self.assertEqual(json.loads(data), event)
        finally:
            if 'response' in locals(): response.close()
            c.close()
        code, duplicate = self.cli('durable-commit', prepared)
        self.assertEqual(code, 2)
        self.assertIn('ALREADY_COMMITTED', duplicate['reason'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])

    def test_native_prepare_commit_and_readback_need_neither_git_nor_gh(self):
        binpath = self.work/'bin'; binpath.mkdir()
        commands = ('node','python3','python3.12')
        if 'browser_runtime' in self.manifest: commands += host.BROWSER_COMMANDS
        for name in commands:
            found = shutil.which(name)
            if found: (binpath/name).symlink_to(found)
        self.assertIsNone(shutil.which('git',path=str(binpath)))
        self.assertIsNone(shutil.which('gh',path=str(binpath)))
        self.start(path=binpath)
        code, prepared = self.cli('durable-prepare', path=binpath); self.assertEqual(code, 0, prepared)
        code, event = self.cli('durable-commit', prepared, path=binpath); self.assertEqual(code, 0, event)
        code, fresh = self.cli('durable-readback', prepared, path=binpath); self.assertEqual(code, 0, fresh)
        self.assertEqual(event['durable_readback'], fresh['durable_readback'])

    def test_sigkill_restart_keeps_epoch_native_id_and_original_event_bytes(self):
        self.start(); prepared, event = self.commit_input()
        before = self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events')
        epoch = self.get('/api/terminal')[1]['ledger_id']
        self.stop(abrupt=True); self.start()
        self.assertEqual(self.get('/api/terminal')[1]['ledger_id'], epoch)
        self.assertEqual(self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events'), before)
        code, fresh = self.cli('durable-readback', prepared); self.assertEqual(code, 0, fresh)
        self.assertEqual(fresh['durable_readback'], event)

    def test_public_monitor_has_no_private_event_body_or_durable_http_writer(self):
        self.start(); self.commit_input()
        code, body = self.get('/api/terminal'); self.assertEqual(code, 200)
        self.assertEqual(body['state'], 'NATIVE_TEMDD_READY')
        self.assertFalse(body['public_event_bodies'])
        self.assertNotIn('private-test-input', json.dumps(body))
        self.assertNotEqual(self.get('/api/temdd/events')[0], 200)
        for path in ('/terminal/input','/api/temdd/append'):
            self.assertEqual(self.get(path,method='POST',url='http://127.0.0.1:'+str(self.config['terminal_port']))[0], 405)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])

    def test_export_drift_holds_original_daemon_before_another_append(self):
        self.start()
        path = self.export/'src/qikvrt_temdd_event_ledger.py'; original = path.read_bytes()
        try:
            path.write_bytes(original+b'\n# unadmitted drift\n')
            code, body = self.get('/api/temdd/subject', url='http://127.0.0.1:'+str(self.config['terminal_port']))
            self.assertNotEqual(code, 200); self.assertFalse(body['dod'])
            self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(0,)])
        finally: path.write_bytes(original)

    def test_native_subject_is_explicit_and_wrong_bindings_never_start(self):
        self.config['subject_pr'] = 0; self.save_config()
        self.assertIn('NATIVE_TERMINAL_SUBJECT', self.denied())
        self.assertFalse((self.volume/'temdd/events.sqlite3').exists())


if __name__ == '__main__': unittest.main()
