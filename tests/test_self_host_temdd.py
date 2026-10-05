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
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import urllib.error
import urllib.request
from unittest.mock import patch

from tests.test_self_host import StandaloneTests, host, ROOT


def recovery_evidence(instance, name, snapshot_receipt, native_events, monitor_events, owner_unix):
    output = os.environ.get('QIKVRT_STATE_RECOVERY_TEST_EVIDENCE')
    if not output: return
    directory = Path(output); directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # CI gets synthetic test observations, never a private state snapshot,
    # configuration, credential, ledger body or production acceptance claim.
    receipt = {'schema':'qikvrt-self-host-state-recovery-readback/v1',
        'source_head':host.git(ROOT,'rev-parse','HEAD').decode(),
        'source_tree':host.git(ROOT,'rev-parse','HEAD^{tree}').decode(),
        'source_worktree_dirty':bool(host.git(ROOT,'status','--porcelain','--untracked-files=normal')),
        'fixture_head':instance.head,'fixture_tree':instance.tree,
        'package_manifest_sha256':instance.pin,
        'state_manifest_sha256':snapshot_receipt['state_manifest_sha256'],
        'native_event_count':len(native_events),
        'native_events_sha256':host.digest(host.raw_json(native_events)),
        'monitor_event_count':len(monitor_events),
        'monitor_events_sha256':host.digest(host.raw_json(monitor_events)),
        'original_state_bytes_preserved':True,'fresh_original_ledger_readback_verified':True,
        'actual_owner_unix_prepare_commit_and_daemon_restart':owner_unix,
        'private_state_snapshot_uploaded':False,'railway_data_exported':False,
        'host_admission_verified':False,'public_readback_verified':False,
        'deployed_restart_verified':False,'railway_cutover_verified':False,
        'review_governance_satisfied':False,'effect_ack_done':False}
    (directory/name).write_bytes(host.raw_json(receipt))


class SourceRecoveryTests(unittest.TestCase):
    def test_novnc_startup_reads_actual_loopback_bytes_under_a_dead_inherited_proxy(self):
        raw = b'<!doctype html><title>actual local noVNC asset fixture</title>'
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(200); self.send_header('Content-Length', str(len(raw)))
                self.end_headers(); self.wfile.write(raw)
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp); asset = package/'runtime/self-host/novnc/vnc.html'
            asset.parent.mkdir(parents=True); asset.write_bytes(raw)
            server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
            thread = threading.Thread(target=server.serve_forever); thread.start()
            try:
                bad = 'http://127.0.0.1:1'
                with patch.dict(os.environ, {'HTTP_PROXY':bad,'http_proxy':bad,'NO_PROXY':'','no_proxy':''}):
                    with self.assertRaises(urllib.error.URLError):
                        urllib.request.build_opener().open('http://127.0.0.1:'+str(server.server_port)+'/vnc.html', timeout=1)
                    self.assertTrue(host.novnc_readback(package, server.server_port))
                    asset.write_bytes(b'unadmitted other asset')
                    self.assertFalse(host.novnc_readback(package, server.server_port))
            finally: server.shutdown(); server.server_close(); thread.join()

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

    def state_cli(self, operation, snapshot, pin=None):
        args = [sys.executable, '-B', str(self.export/'tools/qikvrt_self_host.py'), operation,
                '--root', str(self.export), '--manifest-sha256', self.pin, '--config', str(self.config_path)]
        args += ['--output', str(snapshot)] if operation == 'snapshot-state' else [
            '--state-snapshot', str(snapshot), '--state-manifest-sha256', pin or '0'*64]
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.returncode, json.loads(result.stdout)

    def test_private_snapshot_restore_keeps_actual_native_and_journal_acknowledgments(self):
        original = StandaloneTests.seed_acknowledged_event(self)
        self.start(); prepared, event = self.commit_input()
        epoch = self.get('/api/terminal')[1]['ledger_id']
        before = self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events')
        self.stop(abrupt=True)  # WAL may contain the acknowledged transaction.
        snapshot = self.work/'private-snapshot'
        code, receipt = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 0, receipt)
        self.assertFalse(receipt['effect_ack_done'])
        self.assertFalse(receipt['railway_data_exported'])
        source_bytes = {p: (self.volume/p).read_bytes() for p in host.STATE_FILES if (self.volume/p).exists()}
        self.assertEqual(set(source_bytes), set(json.loads((snapshot/'STATE_MANIFEST.json').read_bytes())['files']))
        for name, raw in source_bytes.items(): self.assertEqual((snapshot/name).read_bytes(), raw)
        # On a different host the same path is absent. Preserve the local source
        # under another name to model this; recovery itself deletes nothing.
        saved = self.work/'preserved-original'; self.volume.rename(saved)
        code, restored = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 0, restored)
        for key in ('effect_ack_done', 'host_admission_verified', 'runtime_readback_verified', 'railway_cutover_verified'):
            self.assertFalse(restored[key])
        for name, raw in source_bytes.items():
            self.assertEqual((self.volume/name).read_bytes(), raw)
            self.assertEqual((saved/name).read_bytes(), raw)
            self.assertEqual((self.volume/name).stat().st_mode & 0o777, 0o600)
        self.start()
        self.assertEqual(self.get('/api/terminal')[1]['ledger_id'], epoch)
        self.assertEqual(self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events'), before)
        code, readback = self.cli('durable-readback', prepared)
        self.assertEqual(code, 0, readback)
        self.assertEqual(readback['durable_readback'], event)
        journal = json.loads((self.volume/'monitor/node.json').read_bytes())
        self.assertEqual(journal['deliveries'], original)
        self.assertNotIn(self.token_file.read_text(), (snapshot/'STATE_MANIFEST.json').read_text())
        recovery_evidence(self, 'NATIVE_OWNER_STATE_RECOVERY.json', receipt, [event], original, True)

    def test_snapshot_blocks_active_native_or_monitor_writers_without_creating_output(self):
        self.start(); self.commit_input()
        snapshot = self.work/'private-snapshot'
        code, result = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())
        self.stop()
        import fcntl
        with (self.volume/'temdd/owner.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            code, result = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())

    def test_recovery_is_create_only_and_rejects_wrong_pins_config_and_tampering(self):
        StandaloneTests.seed_acknowledged_event(self)
        self.start(); self.commit_input(); self.stop()
        snapshot = self.work/'private-snapshot'
        code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
        code, again = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 2, again)
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('ALREADY_EXISTS', result['cause'])
        saved = self.work/'preserved-original'; self.volume.rename(saved)
        code, result = self.state_cli('restore-state', snapshot)
        self.assertEqual(code, 2, result); self.assertIn('PIN_MISMATCH', result['cause']); self.assertFalse(self.volume.exists())
        old = self.config_path.read_bytes(); self.config['node_id'] = 'unadmitted:replacement'; self.save_config()
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('BINDING', result['cause']); self.assertFalse(self.volume.exists())
        self.config_path.write_bytes(old)
        (snapshot/'monitor/node.json').write_bytes(b'corrupted original journal')
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('FILE_MISMATCH', result['cause']); self.assertFalse(self.volume.exists())

    def test_snapshot_rejects_symlinks_extra_files_and_public_modes(self):
        StandaloneTests.seed_acknowledged_event(self)
        self.start(); self.commit_input(); self.stop()
        snapshot = self.work/'private-snapshot'
        database = self.volume/'temdd/events.sqlite3'
        original = self.work/'original.sqlite3'; database.rename(original); database.symlink_to(original)
        code, result = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())
        database.unlink(); original.rename(database)
        code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
        self.volume.rename(self.work/'preserved-original')
        (snapshot/'unlisted.token').write_text('not admitted')
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('INVENTORY', result['cause']); self.assertFalse(self.volume.exists())
        (snapshot/'unlisted.token').unlink(); snapshot.chmod(0o755)
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('OWNER_ONLY', result['cause']); self.assertFalse(self.volume.exists())

    def test_private_state_recovery_executes_without_git_gh_or_provider_transport(self):
        StandaloneTests.seed_acknowledged_event(self)
        self.start(); prepared, event = self.commit_input(); self.stop()
        snapshot = self.work/'private-snapshot'
        bindir = self.work/'bin'; bindir.mkdir()
        commands = ('node', *host.BROWSER_COMMANDS) if 'browser_runtime' in self.manifest else ('node',)
        for name in commands:
            found = shutil.which(name); self.assertIsNotNone(found, name)
            (bindir/name).symlink_to(found)
        self.assertIsNone(shutil.which('git', path=str(bindir)))
        self.assertIsNone(shutil.which('gh', path=str(bindir)))
        with patch.dict(os.environ, {'PATH': str(bindir), 'HTTPS_PROXY': 'http://127.0.0.1:1'}):
            code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
            self.volume.rename(self.work/'preserved-original')
            code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
            self.assertEqual(code, 0, result)
        self.start(path=bindir)
        code, readback = self.cli('durable-readback', prepared, path=bindir)
        self.assertEqual(code, 0, readback); self.assertEqual(readback['durable_readback'], event)

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


class StateSnapshotBackendTests(unittest.TestCase):
    """Original SQLite/journal storage controls; owner-Unix E2E stays above."""
    setUpClass = classmethod(StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(StandaloneTests.tearDownClass.__func__)
    setUp = NativeStandaloneTests.setUp
    save_config = StandaloneTests.save_config
    stop = StandaloneTests.stop
    state_cli = NativeStandaloneTests.state_cli
    sql = NativeStandaloneTests.sql

    def seed_stores(self, abrupt=False):
        journal = StandaloneTests.seed_acknowledged_event(self)
        _, binding = host.state_binding(self.export, self.pin, self.config_path)
        (self.volume/'binding.json').write_bytes(host.raw_json(binding))
        (self.volume/'binding.json').chmod(0o600)
        (self.volume/'node.lock').touch(mode=0o600)
        # Exercise the recovered original SQLite implementation in a separate
        # process. Abrupt exit retains the real acknowledged WAL transaction.
        script = '''
import importlib.util, json, os, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('selfhost', Path(sys.argv[1])/'tools/qikvrt_self_host.py')
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)
host.load_source(Path(sys.argv[1]), 'qikvrt_effect_ack_http_terminal')
native = host.load_source(Path(sys.argv[1]), 'qikvrt_temdd_event_ledger')
subject = json.loads(sys.argv[3])
ledger = native.Ledger(sys.argv[2], subject)
event = {'schema':native.SCHEMA,'kind':'OBSERVE','subject':subject,
    'provenance':{'source':'transputer','native_event_id':'synthetic:snapshot-control'},
    'observed_at':native.utc(),'message':'synthetic acknowledged state: Grüße Ω',
    'payload':{'synthetic':True}}
print(json.dumps({'epoch':ledger.epoch,'event':ledger.append(event)}), flush=True)
if sys.argv[4] == 'abrupt': os._exit(0)
ledger.close()
'''
        self.subject = {'repository':'ingolf-lohmann/qik-vrt','pr':457,'head':self.head,'tree':self.tree}
        result = subprocess.run([sys.executable,'-B','-c',script,str(self.export),str(self.volume),
            json.dumps(self.subject),'abrupt' if abrupt else 'close'],capture_output=True,text=True,timeout=8)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return journal, json.loads(result.stdout)

    def freeze_stores(self):
        self.seed_stores()
        snapshot = self.work/'private-snapshot'
        code, receipt = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 0, receipt)
        return snapshot, receipt['state_manifest_sha256']

    def test_real_acknowledged_wal_and_journal_survive_exact_private_restore(self):
        journal, acknowledged = self.seed_stores(abrupt=True)
        before = self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events')
        self.assertTrue((self.volume/'temdd/events.sqlite3-wal').stat().st_size)
        original = {name:(self.volume/name).read_bytes() for name in host.STATE_FILES if (self.volume/name).exists()}
        snapshot = self.work/'private-snapshot'
        code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
        self.assertFalse(receipt['effect_ack_done']); self.assertFalse(receipt['railway_data_exported'])
        for name, raw in original.items(): self.assertEqual((snapshot/name).read_bytes(), raw)
        preserved = self.work/'preserved-original'; self.volume.rename(preserved)
        code, receipt = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 0, receipt)
        self.assertFalse(receipt['runtime_readback_verified']); self.assertFalse(receipt['host_admission_verified'])
        for name, raw in original.items():
            self.assertEqual((preserved/name).read_bytes(), raw)
            self.assertEqual((self.volume/name).read_bytes(), raw)
            self.assertEqual((self.volume/name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events'), before)
        host.load_source(self.export, 'qikvrt_effect_ack_http_terminal')
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger')
        ledger = native.Ledger(self.volume, self.subject)
        try:
            self.assertEqual(ledger.epoch, acknowledged['epoch'])
            self.assertEqual(ledger.replay(0), [acknowledged['event']])
        finally: ledger.close()
        self.assertEqual(json.loads((self.volume/'monitor/node.json').read_bytes())['deliveries'], journal)
        self.assertNotIn(self.token_file.read_text(), (snapshot/'STATE_MANIFEST.json').read_text())
        recovery_evidence(self, 'ORIGINAL_SQLITE_BACKEND_STATE_RECOVERY.json', receipt, [acknowledged['event']], journal, False)

    def test_each_original_os_writer_lock_blocks_before_snapshot_creation(self):
        self.seed_stores()
        import fcntl
        host.load_source(self.export, 'qikvrt_effect_ack_http_terminal')
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger')
        ledger = native.Ledger(self.volume, self.subject)
        snapshot = self.work/'private-snapshot'
        try:
            code, result = self.state_cli('snapshot-state', snapshot)
            self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())
        finally: ledger.close()
        with (self.volume/'node.lock').open('rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            code, result = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())

    def test_create_only_restore_rejects_wrong_pin_binding_and_corruption(self):
        snapshot, pin = self.freeze_stores()
        for operation in ('snapshot-state', 'restore-state'):
            code, result = self.state_cli(operation, snapshot, pin)
            self.assertEqual(code, 2, result); self.assertIn('ALREADY_EXISTS', result['cause'])
        self.volume.rename(self.work/'preserved-original')
        code, result = self.state_cli('restore-state', snapshot)
        self.assertEqual(code, 2, result); self.assertIn('PIN_MISMATCH', result['cause']); self.assertFalse(self.volume.exists())
        config_raw = self.config_path.read_bytes(); self.config['node_id'] = 'unadmitted:replacement'; self.save_config()
        code, result = self.state_cli('restore-state', snapshot, pin)
        self.assertEqual(code, 2, result); self.assertIn('BINDING', result['cause']); self.assertFalse(self.volume.exists())
        self.config_path.write_bytes(config_raw)
        (snapshot/'monitor/node.json').write_bytes(b'corrupted original journal')
        code, result = self.state_cli('restore-state', snapshot, pin)
        self.assertEqual(code, 2, result); self.assertIn('FILE_MISMATCH', result['cause']); self.assertFalse(self.volume.exists())

    def test_symlinks_unlisted_files_and_public_snapshot_modes_are_refused(self):
        self.seed_stores(); snapshot = self.work/'private-snapshot'
        database = self.volume/'temdd/events.sqlite3'; original = self.work/'preserved.sqlite3'
        database.rename(original); database.symlink_to(original)
        code, result = self.state_cli('snapshot-state', snapshot)
        self.assertEqual(code, 2, result); self.assertFalse(snapshot.exists())
        database.unlink(); original.rename(database)
        code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
        self.volume.rename(self.work/'preserved-original')
        (snapshot/'unlisted.token').write_text('not admitted')
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('INVENTORY', result['cause']); self.assertFalse(self.volume.exists())
        (snapshot/'unlisted.token').unlink(); snapshot.chmod(0o755)
        code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
        self.assertEqual(code, 2, result); self.assertIn('OWNER_ONLY', result['cause']); self.assertFalse(self.volume.exists())

    def test_snapshot_and_restore_have_no_git_gh_or_remote_transport_requirement(self):
        journal, acknowledged = self.seed_stores()
        snapshot = self.work/'private-snapshot'; bindir = self.work/'bin'; bindir.mkdir()
        (bindir/'node').symlink_to(shutil.which('node'))
        self.assertIsNone(shutil.which('git',path=str(bindir))); self.assertIsNone(shutil.which('gh',path=str(bindir)))
        with patch.dict(os.environ, {'PATH':str(bindir),'HTTPS_PROXY':'http://127.0.0.1:1'}):
            code, receipt = self.state_cli('snapshot-state', snapshot); self.assertEqual(code, 0, receipt)
            self.volume.rename(self.work/'preserved-original')
            code, result = self.state_cli('restore-state', snapshot, receipt['state_manifest_sha256'])
            self.assertEqual(code, 0, result)
        host.load_source(self.export, 'qikvrt_effect_ack_http_terminal')
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger'); ledger = native.Ledger(self.volume, self.subject)
        try: self.assertEqual(ledger.replay(0), [acknowledged['event']])
        finally: ledger.close()
        self.assertEqual(json.loads((self.volume/'monitor/node.json').read_bytes())['deliveries'], journal)


if __name__ == '__main__': unittest.main()
