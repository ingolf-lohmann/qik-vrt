# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Actual recovered daemon in a Git-free S1 export, never a substitute fixture."""
from __future__ import annotations
import hashlib
import contextlib
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
        receipt_bytes = (ROOT / 'evidence/self_host/SOURCE_RECOVERY_20261005.json').read_bytes()
        r = json.loads(receipt_bytes)
        successor = json.loads((ROOT / 'evidence/self_host/SOURCE_RECOVERY_SUCCESSOR_20261013.json').read_bytes())
        self.assertEqual(successor['historical_receipt_sha256'], hashlib.sha256(receipt_bytes).hexdigest())
        self.assertFalse(successor['predecessor_pass_transferred'])
        update = successor['temdd_explicit_subject_20261018']
        previous_bytes = (ROOT / update['previous_receipt_path']).read_bytes()
        self.assertEqual(hashlib.sha256(previous_bytes).hexdigest(), update['previous_receipt_sha256'])
        self.assertFalse(update['predecessor_pass_transferred'])
        previous = json.loads(previous_bytes)
        self.assertEqual(previous['historical_receipt_sha256'], successor['historical_receipt_sha256'])
        previous_bindings = {entry['restored_path']: entry for entry in previous['changed_originals']}
        for entry in update['preserved_previous_successor_bindings']:
            self.assertEqual(entry, previous_bindings[entry['restored_path']])
        changed = {entry['restored_path']:entry for entry in successor['changed_originals']}
        self.assertEqual(set(changed), {f['restored_path'] for f in r['files'] if
            hashlib.sha256((ROOT/f['restored_path']).read_bytes()).hexdigest() != f['sha256']})
        self.assertEqual(r['result'], 'EXACT_HISTORICAL_ORIGINAL_BLOBS_RECOVERED')
        self.assertFalse(r['boundaries']['effect_ack_done'])
        for f in r['files']:
            current = (ROOT / f['restored_path']).read_bytes()
            if f['restored_path'] in changed:
                entry = changed[f['restored_path']]
                self.assertEqual(hashlib.sha256(current).hexdigest(), entry['successor_sha256'])
                self.assertEqual(host.git_blob_digest(current), entry['successor_git_blob'])
                raw = (ROOT / entry['historical_archive_path']).read_bytes()
            else: raw = current
            self.assertEqual(len(raw), f['bytes'], f['restored_path'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), f['sha256'])
            self.assertEqual(hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest(), f['git_blob_sha1'])

    def test_consolidation_preserves_both_predecessor_recovery_receipts(self):
        successor = json.loads((ROOT / 'evidence/self_host/SOURCE_RECOVERY_SUCCESSOR_20261013.json').read_bytes())
        update = successor['temdd_consolidation_20261019']
        self.assertEqual(update['integration_pr'], 535)
        self.assertFalse(update['predecessor_pass_transferred'])
        self.assertFalse(update['distributed_writer_exclusion_proved'])
        self.assertFalse(update['production_host_admitted'])
        self.assertEqual({item['pr'] for item in update['predecessors']}, {535, 536})
        for item in update['predecessors']:
            raw = (ROOT / item['receipt_path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item['receipt_sha256'])
            self.assertEqual(host.git_blob_digest(raw), item['receipt_git_blob'])
            self.assertEqual(json.loads(raw)['historical_receipt_sha256'], successor['historical_receipt_sha256'])

    def test_native_kernel_is_in_the_export_and_no_provider_is_required(self):
        definition = json.loads((ROOT / host.DEFINITION).read_bytes())
        self.assertTrue(definition['native_terminal_daemon_included'])
        self.assertIn('src/qikvrt_temdd_event_ledger.py', definition['files'])
        self.assertEqual(definition['providers_required'], [])


def transfer_fixture_writer(test, source, target, subject):
    """Use the real pinned CLI for an explicit stopped local relocation."""
    host.load_source(test.export, 'qikvrt_effect_ack_http_terminal')
    native = host.load_source(test.export, 'qikvrt_temdd_event_ledger')
    reader = native.Ledger(source, subject, read_only=True)
    try: frontier = reader.history_frontier()
    finally: reader.close()
    with test.assertRaisesRegex(native.Hold, 'COPIED_OR_UNADMITTED'):
        native.Ledger(target, subject)
    command = [sys.executable, '-B', str(test.export/'tools/qikvrt_self_host.py'),
        'transfer-local-writer', '--root', str(test.export), '--manifest-sha256', test.pin,
        '--config', str(test.config_path), '--source-state-dir', str(source), '--frontier-sha256', frontier]
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
    receipt = json.loads(result.stdout)
    test.assertFalse(receipt['distributed_fencing_verified'])
    test.assertFalse(receipt['host_admission_verified'])
    with test.assertRaisesRegex(native.Hold, 'COPIED_OR_UNADMITTED'):
        native.Ledger(source, subject)


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
        with contextlib.closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db:
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
        script = "import './docs/monitor/mesh-file-codec.js';process.stdout.write(await QikvrtMeshFile.create('snapshot-mesh-fixture'));"
        mesh = self.volume / 'repository.qmesh'
        mesh.write_bytes(subprocess.check_output(['node', '--input-type=module', '-e', script], cwd=ROOT))
        mesh.chmod(0o600)
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
        self.assertIn('repository.qmesh', source_bytes)
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
        host.load_source(self.export, 'qikvrt_effect_ack_http_terminal')
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger')
        subject = event['subject']
        with sqlite3.connect(saved/'temdd/events.sqlite3') as db:
            frontier = native.digest({'epoch':epoch,'rows':db.execute('SELECT * FROM events ORDER BY seq').fetchall()})
        with self.assertRaisesRegex(native.Hold, 'COPIED_OR_UNADMITTED'):
            native.Ledger(self.volume, subject)
        transferred = native.Ledger.transfer_local_writer(saved,self.volume,subject,frontier)
        self.assertFalse(transferred['distributed_fencing_verified'])
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
            transfer_fixture_writer(self,self.work/'preserved-original',self.volume,event['subject'])
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


class MonolithicStoreTests(unittest.TestCase):
    """Real original daemon, carrier bytes and input receipts in one SQLite file."""
    setUpClass = NativeStandaloneTests.__dict__['setUpClass']
    tearDownClass = NativeStandaloneTests.__dict__['tearDownClass']
    save_config = NativeStandaloneTests.save_config
    start = NativeStandaloneTests.start
    stop = NativeStandaloneTests.stop
    get = NativeStandaloneTests.get
    cli = NativeStandaloneTests.cli
    sql = NativeStandaloneTests.sql
    commit_input = NativeStandaloneTests.commit_input

    def setUp(self):
        NativeStandaloneTests.setUp(self)
        directory = self.volume / 'temdd'; directory.mkdir(mode=0o700)
        self.store = directory / 'events.sqlite3'
        self.created = host.pack_monolith(self.export, self.pin, self.store)

    def command(self, package=None, pin=None):
        return [sys.executable, '-B', str(self.export/'tools/qikvrt_self_host.py'), 'monolith-run',
                '--root', str(self.store), '--manifest-sha256', pin or self.pin, '--config', str(self.config_path)]

    def test_same_native_store_serves_both_roles_without_opening_or_inserting_input(self):
        runtime = self.start()
        self.assertEqual(runtime['deployment_object'], 'NATIVE_SQLITE_CARRIER_AND_LEDGER')
        self.assertEqual(runtime['local_url'], self.url+'/client')
        self.assertEqual(runtime['terminal_opening'], 'ON_DEMAND_URL')
        self.assertFalse(runtime['browser_startup_verified'])
        self.assertFalse(runtime['mobile_runtime_verified'])
        for path in ('/node', '/client', '/mesh'):
            status, html = self.get(path)
            self.assertEqual(status, 200)
            self.assertIn('qikvrt-react-runtime.js', html)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(0,)])
        status, js = self.get('/assets/js/qikvrt-react-runtime.js')
        self.assertEqual(status, 200)
        self.assertEqual(js.encode(), (self.export/'docs/monitor/react-runtime.js').read_bytes())

    def test_actual_input_and_restart_preserve_original_readback_in_the_carrier_database(self):
        self.start()
        prepared, event = self.commit_input()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM carrier'), [(len(self.manifest['files'])+1,)])
        self.stop(abrupt=True)
        self.start()
        code, receipt = self.cli('durable-readback', prepared)
        self.assertEqual(code, 0, receipt)
        self.assertEqual(receipt['durable_readback'], event)
        code, replay = self.cli('durable-commit', prepared)
        self.assertEqual(code, 2, replay)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])

    def test_checkpoint_blocks_live_writer_then_single_file_relocation_restores_state(self):
        self.start()
        _, event = self.commit_input()
        with self.assertRaises(BlockingIOError):
            host.checkpoint_monolith(self.store, self.pin, self.config_path)
        self.stop()
        receipt = host.checkpoint_monolith(self.store, self.pin, self.config_path)
        self.assertEqual(receipt['state'], 'STABLE_SINGLE_FILE_IMAGE')
        self.assertEqual(receipt['file_sha256'], host.digest(self.store.read_bytes()))
        self.assertEqual(receipt['ledger_records'], 1)
        self.assertTrue(receipt['both_writer_locks_held'])
        self.assertFalse(receipt['cloud_synchronization_verified'])
        self.assertFalse(receipt['effect_ack_done'])
        self.assertFalse(any(Path(str(self.store)+s).exists() for s in ('-wal','-shm','-journal')))
        # Only this file is copied. No old binding, node journal, code cache,
        # socket, token or process state is carried to the new private volume.
        original_volume = self.volume
        self.volume = self.work/'successor-volume'; self.volume.mkdir(mode=0o700)
        (self.volume/'temdd').mkdir(mode=0o700)
        successor = self.volume/'temdd/events.sqlite3'
        shutil.copy2(self.store, successor); self.store = successor
        self.config['state_dir'] = str(self.volume); self.save_config()
        transfer_fixture_writer(self,original_volume,self.volume,event['subject'])
        runtime = self.start()
        self.assertEqual(runtime['deployment_object'], 'NATIVE_SQLITE_CARRIER_AND_LEDGER')
        self.assertEqual(json.loads(self.sql('SELECT body FROM events WHERE seq=1')[0][0]),
                         {k:v for k,v in event.items() if k not in ('id','ledger_digest')})
        code, plan = self.cli('durable-prepare'); self.assertEqual(code, 0, plan)
        code, committed = self.cli('durable-commit', plan); self.assertEqual(code, 0, committed)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(2,)])

    def test_wrong_pin_embedded_bytes_and_schema_refuse_without_a_listener(self):
        for mutation in ('pin', 'bytes', 'trigger'):
            with self.subTest(mutation=mutation):
                original = self.store.read_bytes()
                try:
                    if mutation == 'bytes':
                        with sqlite3.connect(self.store) as db:
                            db.execute("UPDATE carrier SET body=? WHERE path=?", (b'unadmitted bytes','docs/monitor/react-runtime.js'))
                    elif mutation == 'trigger':
                        with sqlite3.connect(self.store) as db:
                            db.execute('CREATE TRIGGER unadmitted AFTER DELETE ON carrier BEGIN SELECT 1; END')
                    with self.assertRaises(ValueError):
                        with host.materialized_monolith(self.store, '0'*64 if mutation=='pin' else self.pin): pass
                finally: self.store.write_bytes(original)

    def test_pack_is_create_only_and_symlinked_or_public_objects_are_refused(self):
        original = self.store.read_bytes()
        with self.assertRaises(ValueError): host.pack_monolith(self.export,self.pin,self.store)
        self.assertEqual(self.store.read_bytes(), original)
        link = self.work/'link.sqlite3'; link.symlink_to(self.store)
        with self.assertRaises(ValueError):
            with host.materialized_monolith(link,self.pin): pass
        self.store.chmod(0o644)
        with self.assertRaises(ValueError):
            with host.materialized_monolith(self.store,self.pin): pass
        self.store.chmod(0o600)

    def test_browser_profile_cannot_silently_open_a_terminal_from_monolith_run(self):
        self.config['terminal_profile']='firefox'; self.save_config()
        result = subprocess.run(self.command(),capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2)
        self.assertIn('PASSIVE_PROFILE_REQUIRED',json.loads(result.stdout)['cause'])

    def test_original_sqlite_kernel_appends_replays_and_closes_with_carrier_bytes_intact(self):
        # Executes the real kernel without Unix ingress. This is useful bounded
        # evidence in sandboxes which deny AF_UNIX; it is not a process witness.
        host.load_source(self.export, 'qikvrt_effect_ack_http_terminal')
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger')
        subject = {'repository':'ingolf-lohmann/qik-vrt','pr':457,'head':self.head,'tree':self.tree}
        ledger = native.Ledger(self.volume, subject)
        input_event = {'schema':native.SCHEMA,'kind':'OBSERVE','subject':subject,
            'provenance':{'source':'transputer','native_event_id':'monolith-kernel-witness'},
            'observed_at':'2026-10-06T06:31:00Z','message':'synthetic local kernel witness',
            'payload':{'text':'Grüße Ω','effect_ack_done':False}}
        try:
            event = ledger.append(input_event)
            self.assertEqual(ledger.append(input_event), event)
            self.assertEqual(ledger.replay(0), [event])
        finally: ledger.close()
        ledger = native.Ledger(self.volume, subject)
        try: self.assertEqual(ledger.replay(0), [event])
        finally: ledger.close()
        with host.materialized_monolith(self.store,self.pin) as package:
            self.assertEqual((package/'docs/monitor/react-runtime.js').read_bytes(),
                             (self.export/'docs/monitor/react-runtime.js').read_bytes())
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])


class OriginExportTests(unittest.TestCase):
    setUpClass = classmethod(StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(StandaloneTests.tearDownClass.__func__)
    save_config = StandaloneTests.save_config
    stop = StandaloneTests.stop

    def setUp(self):
        StandaloneTests.setUp(self)
        self.config.update(terminal_profile='temdd',subject_pr=457,source_repository='ingolf-lohmann/qik-vrt')
        self.save_config()
        (self.volume/'temdd').mkdir(mode=0o700)
        self.store=self.volume/'temdd/events.sqlite3'
        host.pack_monolith(self.export,self.pin,self.store)
        host.load_source(self.export,'qikvrt_effect_ack_http_terminal')
        native=host.load_source(self.export,'qikvrt_temdd_event_ledger')
        self.subject={'repository':'ingolf-lohmann/qik-vrt','pr':457,'head':self.head,'tree':self.tree}
        ledger=native.Ledger(self.volume,self.subject)
        self.event=ledger.append({'schema':native.SCHEMA,'kind':'OBSERVE','subject':self.subject,
            'provenance':{'source':'transputer','native_event_id':'origin-adapter-synthetic-witness'},
            'observed_at':'2026-10-06T07:54:32Z','message':'Originalbytes: Grüße Ω',
            'payload':{'effect_ack_done':False}})
        ledger.close()
        _,binding=host.state_binding(self.export,self.pin,self.config_path)
        host.synced_private_file(self.volume/'binding.json',host.raw_json(binding))
        host.synced_private_file(self.volume/'node.lock',b'')

    def test_export_binds_original_identity_and_excludes_private_store_and_credentials(self):
        output=self.work/'origin'
        receipt=host.checkpoint_monolith(self.store,self.pin,self.config_path,output)
        profile=json.loads((output/'ORIGIN_PROFILE.json').read_bytes())
        self.assertEqual(profile['ledger_id'],self.event['id'].split(':')[0])
        self.assertEqual(profile['manifest_sha256'],self.pin)
        self.assertEqual(profile['subject'],self.subject)
        self.assertEqual(profile['store_sha256'],host.digest(self.store.read_bytes()))
        self.assertFalse(receipt['private_store_included'])
        self.assertFalse(receipt['mobile_runtime_verified'])
        for name,digest in receipt['shell_files_sha256'].items():
            self.assertEqual(host.digest((output/name).read_bytes()),digest)
        self.assertFalse(any(p.suffix in ('.db','.sqlite3') for p in output.rglob('*')))
        self.assertNotIn(self.event['message'].encode(),b''.join(p.read_bytes() for p in output.rglob('*') if p.is_file()))
        self.assertNotIn(self.token_file.read_bytes(),b''.join(p.read_bytes() for p in output.rglob('*') if p.is_file()))
        with self.assertRaises(ValueError):host.checkpoint_monolith(self.store,self.pin,self.config_path,output)
        # Optional export of this synthetic fixture for Node/real browser tests.
        destination=os.environ.get('QIKVRT_ORIGIN_FIXTURE_DIR')
        if destination:
            target=Path(destination);target.mkdir(mode=0o700,parents=True,exist_ok=True)
            shutil.copytree(output,target/'origin',dirs_exist_ok=True)
            shutil.copy2(self.store,target/'monolith.sqlite3')
            (target/'expected-event.json').write_bytes(host.raw_json(self.event))

    def test_locked_sqlite_dependency_corruption_fails_before_shell_creation(self):
        original=(self.export/'docs/monitor/origin/vendor/sql-wasm.wasm').read_bytes()
        try:
            (self.export/'docs/monitor/origin/vendor/sql-wasm.wasm').write_bytes(original+b'corrupt')
            with self.assertRaisesRegex(ValueError,'ORIGIN_SQLITE_ASSET_DRIFT'):
                host.verify_origin_sqlite_assets(self.export)
        finally:(self.export/'docs/monitor/origin/vendor/sql-wasm.wasm').write_bytes(original)

    def test_full_tree_extension_uses_the_same_original_sqlite_origin_reader(self):
        output = self.work/'full-tree'
        receipt = host.portable(self.source,output,self.head,self.tree)
        info = host.inspect_stable_monolith(output/'repository.sqlite3',receipt['manifest_sha256'])
        profile = {'schema':'qikvrt-origin-bootstrap/v1','ledger_id':info['ledger_id'],
            'store_sha256':info['file_sha256'],'manifest_sha256':info['manifest_sha256'],
            'subject':self.subject,'max_store_bytes':64*1024*1024,'max_events':10000,
            'native_execution':False,'mobile_runtime_verified':False,'effect_ack_done':False}
        self.assertTrue(info['full_tree_present'])
        destination = os.environ.get('QIKVRT_ORIGIN_FIXTURE_DIR')
        if destination:
            target = Path(destination); target.mkdir(mode=0o700,parents=True,exist_ok=True)
            shutil.copy2(output/'repository.sqlite3',target/'full-tree.sqlite3')
            (target/'full-tree-profile.json').write_bytes(host.raw_json(profile))

class NativePeerRuleTests(unittest.TestCase):
    """Original sealed S1 process, native SQLite and real HMAC HTTP, fixture peers only."""
    setUpClass = classmethod(StandaloneTests.setUpClass.__func__)
    tearDownClass = classmethod(StandaloneTests.tearDownClass.__func__)
    save_config = StandaloneTests.save_config
    command = StandaloneTests.command
    start = StandaloneTests.start
    stop = StandaloneTests.stop
    get = StandaloneTests.get
    sql = NativeStandaloneTests.sql

    def setUp(self):
        import base64
        StandaloneTests.setUp(self)
        self.rule_key = self.work/'peer.key'; self.rule_key.write_text('synthetic-distinct-native-peer-hmac-key-for-tests')
        self.rule_key.chmod(0o600)
        self.rule = json.loads((self.export/'policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json').read_bytes())['client_continuation']
        self.request = {'schema':'qikvrt-peer-rule-request/v1', 'request_id':'native-rule:fixture-001',
            'work_unit_id':'fixture:original-owner-unit', 'sender_node_id':'fixture:sender',
            'sender_repository':'ingolf-lohmann/qik-vrt', 'peer_node_id':self.config['node_id'],
            'subject':{'repository':'ingolf-lohmann/qik-vrt','pr':457,'head':self.head,'tree':self.tree},
            'rule_id':'fixture:native-communication-v1', 'rule':self.rule,
            'rule_sha256':'sha256:'+host.digest(host.mesh_wire(self.rule))}
        self.grant = {'peer_node_id':self.request['sender_node_id'], 'request_id':self.request['request_id'],
            'request_sha256':'sha256:'+host.digest(host.mesh_wire(self.request)),
            'rule_sha256':self.request['rule_sha256'], 'rule_path':'policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json',
            'rule_pointer':['client_continuation']}
        self.config.update(terminal_profile='temdd',subject_pr=457,source_repository='ingolf-lohmann/qik-vrt',unix_ingress=False,
            mesh_work_peers=[{'node_id':'fixture:sender','repository':'ingolf-lohmann/qik-vrt','secret_file':str(self.rule_key)}],
            mesh_rule_grants=[self.grant])
        self.save_config()
        self.peer = {'node_id':self.config['node_id'],'source_head':self.head,'source_tree':self.tree,
            'secret_file':str(self.rule_key),'url':'http://127.0.0.1:'+str(self.config['terminal_port'])}
        self.cache = host.MeshWorkCache(self.work/'rule-cache','ingolf-lohmann/qik-vrt','fixture:sender')
        self.calls = []

    def transport(self, url, method, raw, headers):
        self.calls.append((method,url))
        return host.mesh_work_transport(url,method,raw,headers)

    def confirm(self, apply=True, transport=None, request=None):
        return self.cache.confirm_rule(self.peer, request or self.request, apply=apply, transport=transport or self.transport)

    def test_receipt_and_application_are_separate_original_events_and_scoped_effect_ack(self):
        self.start()
        receipt = self.confirm(apply=False)
        self.assertEqual(receipt['rule_effect']['state'],'EFFECT_ACK_CONTINUE')
        self.assertIsNone(receipt['readback']['applied'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM meta WHERE key LIKE 'peer-rule-active:%'"),[(0,)])
        result = self.confirm()
        self.assertEqual(result['rule_effect']['state'],'EFFECT_ACK_DONE')
        self.assertEqual(result['scope'],'NATIVE_PEER_RULE_ACTIVATION_ONLY')
        self.assertFalse(result['effect_ack_done']);self.assertFalse(result['all_peer_adoption_verified'])
        readback=result['readback']; received=readback['received']['native_event']; applied=readback['applied']['native_event']
        self.assertNotEqual(received['id'],applied['id'])
        self.assertEqual(received['id'].split(':')[0],applied['id'].split(':')[0])
        self.assertEqual(received['payload']['request_sha256'],self.grant['request_sha256'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])
        self.assertEqual(len([c for c in self.calls if c[0]=='POST']),2)

    def test_repeat_restart_and_lost_application_ack_do_not_reexecute_or_replace_native_identity(self):
        self.start(); self.confirm(apply=False)
        def lose(url,method,raw,headers):
            response=self.transport(url,method,raw,headers)
            if method=='POST' and url.endswith('/apply'): raise TimeoutError('synthetic lost ACK')
            return response
        with self.assertRaises(TimeoutError): self.confirm(transport=lose)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])
        self.stop(abrupt=True); self.start(); self.calls.clear()
        first=self.confirm(); second=self.confirm()
        self.assertEqual(first['readback']['applied'],second['readback']['applied'])
        self.assertFalse(any(c[0]=='POST' for c in self.calls))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])

    def test_lost_receive_ack_is_resolved_by_challenged_readback_before_any_post(self):
        self.start()
        def lose(url,method,raw,headers):
            result=self.transport(url,method,raw,headers)
            if method=='POST': raise TimeoutError('synthetic receive reply lost')
            return result
        with self.assertRaises(TimeoutError): self.confirm(apply=False,transport=lose)
        self.calls.clear(); self.confirm(apply=False)
        self.assertTrue(all(c[0]=='GET' for c in self.calls))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])

    def test_each_request_identity_rule_and_subject_mutation_is_rejected_without_event(self):
        self.start()
        cases=[('request_id','different'),('work_unit_id','different'),('sender_node_id','different'),
            ('sender_repository','Goldkelch/qik-vrt'),('peer_node_id','different'),('rule_id','different'),
            ('rule_sha256','sha256:'+'0'*64)]
        for name,bad in cases:
            value=json.loads(host.mesh_wire(self.request));value[name]=bad
            with self.subTest(name=name),self.assertRaises(ValueError): self.confirm(request=value)
        for name,bad in [('head','0'*40),('tree','0'*40),('repository','Goldkelch/qik-vrt'),('pr',458)]:
            value=json.loads(host.mesh_wire(self.request));value['subject'][name]=bad
            with self.subTest(name=name),self.assertRaises(ValueError): self.confirm(request=value)
        value=json.loads(host.mesh_wire(self.request));value['rule']['binding_for_all_clients']=False
        value['rule_sha256']='sha256:'+host.digest(host.mesh_wire(value['rule']))
        with self.assertRaises(ValueError):self.confirm(request=value)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])

    def test_absent_local_grant_and_wrong_private_key_cannot_create_a_receipt(self):
        self.config['mesh_rule_grants']=[];self.save_config();self.start()
        with self.assertRaises(ValueError):self.confirm()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        wrong=self.work/'untrusted-peer.key';wrong.write_text('synthetic-wrong-untrusted-native-peer-hmac-key');wrong.chmod(0o600)
        self.peer['secret_file']=str(wrong)
        with self.assertRaises(ValueError):self.confirm()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])

    def test_apply_before_receive_is_refused_and_no_event_or_activation_appears(self):
        self.start()
        with self.assertRaises(ValueError):
            self.cache.peer_request(self.peer)('POST','/api/mesh-work/rule/apply',host.mesh_wire(self.request))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM meta WHERE key LIKE 'peer-rule-active:%'"),[(0,)])

    def rewrite_readback(self, mutate, *, sign=True):
        import hmac,base64
        def transport(url,method,raw,headers):
            status,data,signature=self.transport(url,method,raw,headers)
            if method=='GET':
                value=json.loads(data);mutate(value);data=host.mesh_wire(value)
                if sign:
                    path=urllib.parse.urlsplit(url).path
                    signature='sha256='+hmac.new(self.rule_key.read_bytes(),b'RESPONSE\n'+path.encode()+b'\n'+data,hashlib.sha256).hexdigest()
            return status,data,signature
        return transport

    def test_full_receipt_binding_survives_even_authentic_envelope_field_substitution(self):
        self.start();self.confirm()
        cases={'request_id':'wrong','work_unit_id':'wrong','request_sha256':'sha256:'+'f'*64,
            'rule_sha256':'sha256:'+'f'*64,'rule_id':'wrong','peer_node_id':'wrong','sender_node_id':'wrong','scope':'GLOBAL',
            'subject':dict(self.request['subject'],pr=458),'challenge':'0'*32}
        for name,bad in cases.items():
            def mutate(v):v[name]=bad
            with self.subTest(name=name),self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(mutate))
        for name,bad in cases.items():
            if name=='challenge':continue
            def mutate(v):v['applied'][name]=bad
            with self.subTest(receipt=name),self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(mutate))

    def test_native_event_id_epoch_digest_provenance_payload_and_source_are_required(self):
        self.start();self.confirm()
        for name in ('id','ledger_digest','provenance','payload','subject','payload_digest'):
            def mutate(v):
                event=v['applied']['native_event']
                event[name] = '0'*64 if name in ('ledger_digest','payload_digest') else ('f'*32+':999' if name=='id' else {})
            with self.subTest(name=name),self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(mutate))
        def mutate(v):v['applied']['native_digest']='0'*64
        with self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(mutate))

    def test_untrusted_or_replayed_challenge_and_request_hash_cannot_complete(self):
        self.start();self.confirm()
        def mutate(v):v['challenge']='0'*32
        with self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(mutate,sign=False))
        prior=self.confirm()['readback']
        def replay(v):v.clear();v.update(prior)
        with self.assertRaises(ValueError):self.confirm(transport=self.rewrite_readback(replay))

    def test_active_binding_corruption_and_deletion_of_acknowledged_event_fail_closed(self):
        self.start();result=self.confirm()
        self.stop()
        path=self.volume/'temdd/events.sqlite3'
        with sqlite3.connect(path) as db:
            db.execute("DELETE FROM meta WHERE key LIKE 'peer-rule-active:%'")
        self.start()
        with self.assertRaises(ValueError):self.confirm()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])

    def test_acknowledged_request_cannot_silently_disappear_and_be_reapplied(self):
        self.start();self.confirm();self.stop()
        with sqlite3.connect(self.volume/'temdd/events.sqlite3') as db:
            db.execute("DELETE FROM events");db.execute("DELETE FROM meta WHERE key LIKE 'peer-rule:%' OR key LIKE 'peer-rule-active:%'")
        self.start();self.calls.clear()
        with self.assertRaisesRegex(ValueError,'RECEIPT_LOST_HOLD'):self.confirm()
        self.assertFalse(any(c[0]=='POST' for c in self.calls))

    def test_readback_unavailable_does_not_trigger_another_effectful_attempt(self):
        self.start()
        def unavailable(url,method,raw,headers):
            self.calls.append((method,url));raise TimeoutError('synthetic unavailable original readback')
        with self.assertRaises(TimeoutError):self.confirm(transport=unavailable)
        self.assertEqual([c[0] for c in self.calls],['GET'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])

    def test_activation_is_enforced_on_subsequent_original_native_writes(self):
        self.owner_token=self.work/'owner.key';self.owner_token.write_text('synthetic-native-owner-rest-key-separated-from-peer');self.owner_token.chmod(0o600)
        self.config['owner_rest_grants']=[{'principal':'owner:fixture','token_file':str(self.owner_token),
            'permissions':['prepare','commit','readback']}]
        self.save_config();self.start();self.confirm()
        original=self.request
        self.request={'schema':'qikvrt_owner_rest_input_v1','request_id':'owner:after-active-guard',
            'subject':original['subject'],'input':{'schema':'qikvrt_terminal_input_v1','text':'Actual next native write through active guard'}}
        self.rest=OwnerRESTMonolithTests.rest.__get__(self)
        status,p=self.rest('prepare');self.assertEqual(status,200,p)
        status,r=self.rest('commit',prepared=p);self.assertEqual(status,200,r)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(3,)])
        self.stop()
        with sqlite3.connect(self.volume/'temdd/events.sqlite3') as db:db.execute("DELETE FROM meta WHERE key LIKE 'peer-rule-active:%'")
        self.start()
        self.request['request_id']='owner:corrupt-active-guard'
        status,p=self.rest('prepare');self.assertEqual(status,200,p)
        status,r=self.rest('commit',prepared=p);self.assertEqual(status,409,r)
        self.assertIn('ACTIVE_WRITER_GUARD',r['cause'] if 'cause' in r else str(r))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(3,)])

    def test_applied_peer_grant_revocation_blocks_fresh_confirmation(self):
        self.start();self.confirm();self.stop()
        self.config['mesh_rule_grants']=[];self.save_config()
        # Source/config binding cannot silently change on an admitted volume.
        denied=self.command()
        result=subprocess.run(denied,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])

    def test_signed_replaced_epoch_is_rejected_against_retained_original_receipt(self):
        self.start();self.confirm()
        def replace(v):
            for stage in ('received','applied'):
                event=v[stage]['native_event'];event['id']='f'*32+':'+event['id'].split(':')[1]
        with self.assertRaisesRegex(ValueError,'CHANGED_NATIVE_RECEIPT'):self.confirm(transport=self.rewrite_readback(replace))

    def test_cli_uses_the_same_existing_cache_and_native_adapter(self):
        self.start()
        request=self.work/'rule-request.json';request.write_bytes(host.mesh_wire(self.request));request.chmod(0o600)
        peer=self.work/'peer.json';peer.write_bytes(host.mesh_wire(self.peer));peer.chmod(0o600)
        result=subprocess.run([sys.executable,'-B',str(self.export/'tools/qikvrt_self_host.py'),'mesh-rule-confirm',
            '--mesh-cache',str(self.work/'cli-cache'),'--work-request',str(request),'--peer',str(peer),'--apply-rule'],
            capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(value['rule_effect']['state'],'EFFECT_ACK_DONE');self.assertFalse(value['effect_ack_done'])

    def test_fault_after_guard_commit_recovers_only_the_original_application_event(self):
        terminal=host.load_source(self.export,'qikvrt_effect_ack_http_terminal')
        native=host.load_source(self.export,'qikvrt_temdd_event_ledger')
        runtime=native.Runtime(self.source,self.volume,'ingolf-lohmann/qik-vrt',457)
        rules=terminal.NativePeerRules(runtime,self.config['node_id'],str(self.volume),[self.grant])
        peer=self.config['mesh_work_peers'][0]
        try:
            original=rules.receive(self.request,peer)
            with patch.object(runtime,'append',side_effect=OSError('injected failure after actual guard COMMIT')):
                with self.assertRaises(OSError):rules.apply(self.request,peer)
            observed=rules.readback(self.request,peer,'a'*32)
            self.assertIsNone(observed['applied'])
            self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
            event=rules.record(self.request)['events']['RECEIVED']
            with self.assertRaisesRegex(ValueError,'INTERRUPTED_ACTIVATION'):rules.enforce_event(event)
        finally:runtime.ledger.close()
        runtime=native.Runtime(self.source,self.volume,'ingolf-lohmann/qik-vrt',457)
        try:
            rules=terminal.NativePeerRules(runtime,self.config['node_id'],str(self.volume),[self.grant])
            result=rules.apply(self.request,peer)
            self.assertEqual(result['received'],original)
            self.assertIsNotNone(result['applied'])
            self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])
        finally:runtime.ledger.close()


class OwnerRESTMonolithTests(unittest.TestCase):
    """Actual S1 process, authenticated HTTP and original SQLite; no AF_UNIX."""
    setUpClass = MonolithicStoreTests.__dict__['setUpClass']
    tearDownClass = MonolithicStoreTests.__dict__['tearDownClass']
    save_config = NativeStandaloneTests.save_config
    start = NativeStandaloneTests.start
    stop = NativeStandaloneTests.stop
    get = NativeStandaloneTests.get
    sql = NativeStandaloneTests.sql
    command = MonolithicStoreTests.command

    def setUp(self):
        MonolithicStoreTests.setUp(self)
        self.refusals=[]
        self.owner_token = self.work/'owner.token'
        self.owner_token.write_text('synthetic-owner-rest-key-separate-from-read-only-token')
        self.owner_token.chmod(0o600)
        self.reader_token = self.work/'reader.token'
        self.reader_token.write_text('synthetic-reader-rest-key-without-write-authorization')
        self.reader_token.chmod(0o600)
        self.config.update(unix_ingress=False, owner_rest_grants=[
            {'principal':'owner:fixture','token_file':str(self.owner_token),'permissions':['prepare','commit','readback']},
            {'principal':'reader:fixture','token_file':str(self.reader_token),'permissions':['readback']}])
        self.save_config()
        self.request = {'schema':'qikvrt_owner_rest_input_v1','request_id':'rest:synthetic-001',
            'subject':{'repository':'ingolf-lohmann/qik-vrt','pr':457,'head':self.head,'tree':self.tree},
            'input':{'schema':'qikvrt_terminal_input_v1','text':'synthetic private REST input: Grüße Ω'}}

    def rest(self, operation, body=None, prepared=None, token=None, principal='owner:fixture', extra=None):
        headers = {'Authorization':'Bearer '+(token or self.owner_token.read_text()),'QIKVRT-Owner':principal}
        if operation == 'readback':
            method='GET'; path='/api/owner/receipts/'+self.request['request_id']
            raw=None; headers['QIKVRT-Subject']=json.dumps(self.request['subject'])
        else:
            method='POST'; path='/api/owner/'+operation
            raw=host.mesh_wire(body or self.request)
            headers.update({'Content-Type':'application/json','Effect-Ack-Request':'v=1, mode=prepare'})
            if operation == 'commit':
                import base64
                sf=lambda b: ':'+base64.b64encode(b).decode('ascii')+':'
                headers['Effect-Ack-Request']='v=1, mode=commit, token='+sf(prepared['commit_token'].encode())+', hash='+sf(bytes.fromhex(prepared['record_hash']))
        if extra:
            for k,v in extra.items():
                if v is None: headers.pop(k,None)
                else: headers[k]=v
        conn=http.client.HTTPConnection('127.0.0.1',self.config['terminal_port'],timeout=6)
        try:
            conn.request(method,path,body=raw,headers=headers)
            reply=conn.getresponse(); payload=reply.read()
            self.assertNotIn('state=done',reply.getheader('Effect-Ack',''))
            return reply.status,json.loads(payload)
        finally: conn.close()

    def prepared(self):
        status,prepared=self.rest('prepare'); self.assertEqual(status,200,prepared)
        self.assertEqual(prepared['state'],'PREPARED')
        self.assertFalse(prepared['EFFECT_ACK_DONE'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        self.assertEqual(self.rest('prepare'),(200,prepared))
        return prepared

    def assert_refusal(self, status, reason, operation, **kwargs):
        before=self.sql('SELECT seq,body FROM events')
        code,result=self.rest(operation,**kwargs)
        self.assertEqual(code,status,result); self.assertEqual(result['reason'],reason)
        self.assertFalse(result['ordinary_release'])
        self.assertEqual(self.sql('SELECT seq,body FROM events'),before)
        self.refusals.append({'operation':operation,'status':code,'reason':reason,
            'event_count':len(before),'no_additional_event':True})

    def test_rest_persists_in_same_monolith_and_independent_readback_replays_after_sigkill(self):
        self.start()
        self.assertFalse((self.volume/'temdd/ingress.sock').exists())
        metadata=self.get('/api/terminal')[1]
        self.assertTrue(metadata['owner_rest_input_enabled']); self.assertFalse(metadata['unix_ingress_enabled'])
        prepared=self.prepared()
        status,receipt=self.rest('commit',prepared=prepared); self.assertEqual(status,200,receipt)
        event=receipt['durable_readback']
        self.assertTrue(receipt['independent_sqlite_readback']); self.assertFalse(receipt['replayed'])
        self.assertFalse(receipt['EFFECT_ACK_DONE']); self.assertFalse(receipt['ordinary_release'])
        # New independent readonly DB connection, outside the native process.
        row=self.sql('SELECT seq,binding,native_digest,body,body_digest FROM events')[0]
        self.assertEqual(json.loads(row[3]),{k:v for k,v in event.items() if k not in ('id','ledger_digest')})
        self.assertEqual(row[1],host.digest(host.mesh_wire(self.request['subject'])))
        self.assertEqual(row[2],host.digest(host.mesh_wire(prepared['preparation']['event'])))
        self.assertEqual(row[4],host.digest(host.mesh_wire(json.loads(row[3]))))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM carrier'),[(len(self.manifest['files'])+1,)])
        for secret in (self.owner_token.read_text(),self.reader_token.read_text(),self.token_file.read_text()):
            self.assertNotIn(secret,json.dumps(self.sql('SELECT value FROM meta'))+row[3]+json.dumps(receipt))
        status,observed=self.rest('readback'); self.assertEqual(status,200,observed)
        self.assertEqual(observed['durable_readback'],event)
        status,replay=self.rest('commit',prepared=prepared); self.assertEqual(status,200,replay)
        self.assertTrue(replay['replayed']); self.assertEqual(replay['durable_readback'],event)
        self.stop(abrupt=True); self.start()
        self.assertFalse((self.volume/'temdd/ingress.sock').exists())
        self.assertEqual(self.rest('prepare'),(200,prepared))
        self.assertEqual(self.rest('readback')[1]['durable_readback'],event)
        self.assertEqual(self.rest('commit',prepared=prepared)[1]['durable_readback'],event)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
        self.stop()
        checkpoint=host.checkpoint_monolith(self.store,self.pin,self.config_path)
        self.assertEqual(checkpoint['ledger_records'],1)
        # Restore only the monolith. Preparation and event survive without Unix.
        successor=self.work/'rest-successor'; successor.mkdir(mode=0o700)
        (successor/'temdd').mkdir(mode=0o700)
        shutil.copy2(self.store,successor/'temdd/events.sqlite3')
        original_volume=self.volume
        self.volume=successor; self.store=successor/'temdd/events.sqlite3'
        self.config['state_dir']=str(successor); self.save_config()
        transfer_fixture_writer(self,original_volume,successor,event['subject'])
        self.start()
        self.assertEqual(self.rest('readback')[1]['durable_readback'],event)
        self.assertEqual(self.rest('commit',prepared=prepared)[1]['durable_readback'],event)
        output=os.environ.get('QIKVRT_OWNER_REST_TEST_EVIDENCE')
        if output:
            directory=Path(output); directory.mkdir(parents=True,exist_ok=True)
            evidence={'schema':'qikvrt-owner-rest-monolith-e2e/v1',
                'source_head':host.git(ROOT,'rev-parse','HEAD').decode(),
                'source_tree':host.git(ROOT,'rev-parse','HEAD^{tree}').decode(),
                'source_worktree_dirty':bool(host.git(ROOT,'status','--porcelain','--untracked-files=normal')),
                'fixture_head':self.head,'fixture_tree':self.tree,'manifest_sha256':self.pin,
                'original_ledger_event_sha256':host.digest(host.mesh_wire(event)),
                'rest_to_original_sqlite':True,'independent_sqlite_readback':True,
                'prepare_and_commit_idempotent':True,'actual_sigkill_restart':True,
                'single_file_restore':True,'unix_ingress_present':False,
                'public_deployment_verified':False,'effect_ack_done':False}
            (directory/'OWNER_REST_MONOLITH_E2E.json').write_bytes(host.raw_json(evidence))

    def test_identity_subject_conflict_and_authorization_fail_closed_without_effect(self):
        self.start(); prepared=self.prepared()
        for operation in ('prepare','commit','readback'):
            kwargs={'prepared':prepared} if operation=='commit' else {}
            self.assert_refusal(401,'OWNER_REST_AUTHENTICATION_REQUIRED',operation,extra={'Authorization':None},**kwargs)
            self.assert_refusal(401,'OWNER_REST_AUTHENTICATION_REQUIRED',operation,token='invalid-synthetic-token',**kwargs)
            self.assert_refusal(401,'OWNER_REST_AUTHENTICATION_REQUIRED',operation,token=self.token_file.read_text(),**kwargs)
            self.assert_refusal(403,'OWNER_REST_IDENTITY_MISMATCH',operation,principal='wrong:identity',**kwargs)
            self.assert_refusal(403,'OWNER_REST_SAME_ORIGIN_LOOPBACK_REQUIRED',operation,extra={'Origin':'https://untrusted.invalid'},**kwargs)
        for operation in ('prepare','commit'):
            self.assert_refusal(403,'OWNER_REST_PERMISSION_REQUIRED',operation,prepared=prepared,
                principal='reader:fixture',token=self.reader_token.read_text())
        for field,replacement in [('repository','wrong/repo'),('pr',458),('head','0'*40),('tree','0'*40)]:
            wrong=json.loads(json.dumps(self.request)); wrong['subject'][field]=replacement
            for operation in ('prepare','commit'):
                self.assert_refusal(409,'EXACT_OWNER_REST_SUBJECT_MISMATCH',operation,body=wrong,prepared=prepared)
            self.assert_refusal(409,'EXACT_OWNER_REST_SUBJECT_MISMATCH','readback',extra={'QIKVRT-Subject':json.dumps(wrong['subject'])})
        conflict=json.loads(json.dumps(self.request)); conflict['input']['text']='changed exact input'
        for operation in ('prepare','commit'):
            self.assert_refusal(409,'OWNER_REST_REPLAY_CONFLICT',operation,body=conflict,prepared=prepared)
        for field,value in [('record_hash','0'*64),('commit_token','0'*64)]:
            wrong={**prepared,field:value}
            self.assert_refusal(409,'OWNER_REST_COMMIT_BINDING_MISMATCH','commit',prepared=wrong)
        self.assertEqual(self.rest('commit',prepared=prepared)[0],200)
        self.assert_refusal(409,'OWNER_REST_REPLAY_CONFLICT','commit',body=conflict,prepared=prepared)
        self.stop(abrupt=True); self.start()
        self.assert_refusal(409,'OWNER_REST_REPLAY_CONFLICT','prepare',body=conflict)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
        output=os.environ.get('QIKVRT_OWNER_REST_TEST_EVIDENCE')
        if output:
            directory=Path(output); directory.mkdir(parents=True,exist_ok=True)
            (directory/'OWNER_REST_NEGATIVE_CONTROLS.json').write_bytes(host.raw_json({
                'schema':'qikvrt-owner-rest-negative-controls/v1',
                'source_head':host.git(ROOT,'rev-parse','HEAD').decode(),
                'source_tree':host.git(ROOT,'rev-parse','HEAD^{tree}').decode(),
                'source_worktree_dirty':bool(host.git(ROOT,'status','--porcelain','--untracked-files=normal')),
                'fixture_head':self.head,'fixture_tree':self.tree,'controls':self.refusals,
                'private_inputs_or_credentials_uploaded':False,'effect_ack_done':False}))

    def test_prepare_and_permission_survive_restart_concurrent_commits_append_once(self):
        self.start(); prepared=self.prepared(); self.stop(abrupt=True); self.start()
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:self.rest('commit',prepared=prepared),range(8)))
        self.assertTrue(all(code==200 for code,_ in results),results)
        events=[body['durable_readback'] for _,body in results]
        self.assertTrue(all(event==events[0] for event in events))
        self.assertEqual(sum(not body['replayed'] for _,body in results),1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
        # Rotation revokes the old bearer on the next request. Existing reads
        # remain recoverable by the explicitly configured principal's new key.
        old=self.owner_token.read_text()
        self.owner_token.write_text('synthetic-rotated-owner-rest-key-at-least-thirty-two-bytes')
        self.assert_refusal(401,'OWNER_REST_AUTHENTICATION_REQUIRED','readback',token=old)
        self.assertEqual(self.rest('readback')[1]['durable_readback'],events[0])

    def test_absent_grant_and_public_secret_mode_never_enable_a_writer(self):
        self.config['owner_rest_grants']=[]; self.save_config(); self.start()
        self.assert_refusal(503,'OWNER_REST_NOT_AUTHORIZED','prepare')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        self.stop()
        self.config['owner_rest_grants']=[{'principal':'owner:fixture','token_file':str(self.owner_token),
            'permissions':['prepare','commit','readback']}]
        self.owner_token.chmod(0o644); self.save_config()
        result=subprocess.run(self.command(),capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,2,result.stdout+result.stderr)
        self.assertIn('OWNER_ONLY_PRIVATE_PATH_REQUIRED',result.stdout)

    def test_lost_commit_response_recovers_by_get_without_resubmitting(self):
        self.start(); prepared=self.prepared()
        import base64, time
        sf=lambda b: ':'+base64.b64encode(b).decode('ascii')+':'
        headers={'Authorization':'Bearer '+self.owner_token.read_text(),'QIKVRT-Owner':'owner:fixture',
            'Content-Type':'application/json','Effect-Ack-Request':'v=1, mode=commit, token='+
            sf(prepared['commit_token'].encode())+', hash='+sf(bytes.fromhex(prepared['record_hash']))}
        conn=http.client.HTTPConnection('127.0.0.1',self.config['terminal_port'],timeout=5)
        conn.request('POST','/api/owner/commit',host.mesh_wire(self.request),headers)
        conn.close()  # No status, header or body is read and no POST is repeated.
        until=time.monotonic()+5
        while time.monotonic()<until and self.sql('SELECT COUNT(*) FROM events')!=[(1,)]:
            time.sleep(0.01)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])
        self.stop(abrupt=True); self.start()
        status,receipt=self.rest('readback'); self.assertEqual(status,200,receipt)
        self.assertTrue(receipt['independent_sqlite_readback'])
        self.assertEqual(receipt['durable_readback']['payload']['terminal_input'],self.request['input'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])


class StorageTransportTests(unittest.TestCase):
    """Actual Owner REST and original SQLite; QIKMESH is only a frozen carrier."""
    setUpClass = OwnerRESTMonolithTests.__dict__['setUpClass']
    tearDownClass = OwnerRESTMonolithTests.__dict__['tearDownClass']
    setUp = OwnerRESTMonolithTests.setUp
    save_config = OwnerRESTMonolithTests.save_config
    start = OwnerRESTMonolithTests.start
    stop = OwnerRESTMonolithTests.stop
    get = OwnerRESTMonolithTests.get
    sql = OwnerRESTMonolithTests.sql
    command = OwnerRESTMonolithTests.command
    rest = OwnerRESTMonolithTests.rest
    prepared = OwnerRESTMonolithTests.prepared

    def export_transport(self):
        target = self.work/'transport.qmesh'
        receipt = host.transport_export(self.store, self.pin, self.config_path, target)
        self.assertEqual(receipt['state'], 'DERIVED_SQLITE_TRANSPORT_EXPORTED')
        self.assertFalse(receipt['effect_ack_done'])
        self.assertEqual(receipt['canonical_sha256'], host.digest(self.store.read_bytes()))
        self.assertEqual(receipt['transport_sha256'], host.digest(target.read_bytes()))
        return target, receipt

    def import_file(self, source, receipt, output):
        return host.transport_import(source, self.pin, receipt['canonical_sha256'], receipt['transport_sha256'], output)

    def test_rest_pending_prepare_committed_effect_and_replay_survive_byte_exact_roundtrip_and_restart(self):
        self.start()
        first_request = json.loads(json.dumps(self.request))
        first_prepared = self.prepared()
        status, first_receipt = self.rest('commit', prepared=first_prepared)
        self.assertEqual(status, 200)
        self.request = dict(first_request, request_id='rest:pending-after-export',
                            input={'schema':'qikvrt_terminal_input_v1','text':'pending through export Grüße Ω'})
        status, pending = self.rest('prepare')
        self.assertEqual(status, 200)
        before_events = self.sql('SELECT * FROM events ORDER BY seq')
        before_meta = self.sql('SELECT * FROM meta ORDER BY key')
        before_sequence = self.sql('SELECT * FROM sqlite_sequence')
        self.stop(abrupt=True)
        transport, receipt = self.export_transport()
        original_bytes = self.store.read_bytes()
        successor = self.work/'restored-volume'; successor.mkdir(mode=0o700)
        directory = successor/'temdd'; directory.mkdir(mode=0o700)
        restored = directory/'events.sqlite3'
        binaries = self.work/'without-git'; binaries.mkdir(mode=0o700)
        (binaries/'node').symlink_to(shutil.which('node'))
        with patch.dict(os.environ, {'PATH':str(binaries)}):
            self.assertIsNone(shutil.which('git'))
            imported = self.import_file(transport, receipt, restored)
        self.assertEqual(restored.read_bytes(), original_bytes)
        self.assertFalse(imported['predecessor_evidence_transfer'])
        self.assertFalse(imported['native_runtime_executed'])
        self.assertTrue(imported['same_node_client_bytes'])
        original_volume = self.volume
        self.volume, self.store = successor, restored
        self.config['state_dir'] = str(successor); self.save_config()
        transfer_fixture_writer(self,original_volume,successor,first_receipt['durable_readback']['subject'])
        self.start()
        self.assertEqual(self.sql('SELECT * FROM events ORDER BY seq'), before_events)
        after_meta = self.sql('SELECT * FROM meta ORDER BY key')
        self.assertEqual([row for row in after_meta if row[0] != 'writer_seal'],
                         [row for row in before_meta if row[0] != 'writer_seal'])
        self.assertNotEqual(dict(after_meta)['writer_seal'],dict(before_meta)['writer_seal'])
        self.assertEqual(self.sql('SELECT * FROM sqlite_sequence'), before_sequence)
        self.assertEqual(self.rest('prepare'), (200, pending))
        status, committed = self.rest('commit', prepared=pending)
        self.assertEqual(status, 200)
        self.assertEqual(self.rest('commit', prepared=pending)[1]['durable_readback'], committed['durable_readback'])
        self.request = first_request
        self.assertEqual(self.rest('readback')[1]['durable_readback'], first_receipt['durable_readback'])
        self.assertEqual(self.rest('commit', prepared=first_prepared)[1]['durable_readback'], first_receipt['durable_readback'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(2,)])
        self.assertFalse(committed['EFFECT_ACK_DONE'])
        self.stop()
        output = os.environ.get('QIKVRT_STORAGE_CONTRACT_TEST_EVIDENCE')
        if output:
            directory = Path(output); directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            evidence = {'schema':'qikvrt-canonical-storage-roundtrip-witness/v1',
                'source_head':host.git(ROOT,'rev-parse','HEAD').decode(),
                'source_tree':host.git(ROOT,'rev-parse','HEAD^{tree}').decode(),
                'source_worktree_dirty':bool(host.git(ROOT,'status','--porcelain','--untracked-files=normal')),
                'canonical_format':'SQLITE3_WITH_CARRIER_META_AND_EVENTS',
                'transport_role':'DERIVED_BYTE_EXACT_SQLITE_EXPORT_ONLY',
                'fixture_head':self.head,'fixture_tree':self.tree,
                'canonical_sha256':receipt['canonical_sha256'],'transport_sha256':receipt['transport_sha256'],
                'byte_identical_roundtrip':True,'original_meta_events_and_sqlite_sequence_preserved':True,
                'pending_prepare_committed_after_restore':True,'prior_ack_replayed_without_duplicate':True,
                'actual_sigkill_and_native_restart':True,'unix_ingress':False,
                'git_absent_during_import':True,
                'public_mobile_or_mesh_acceptance':False,'effect_ack_done':False}
            (directory/'roundtrip.json').write_bytes(host.raw_json(evidence))

    def test_export_refuses_both_running_writer_locks_and_never_copies_a_live_main_file(self):
        self.start()
        with self.assertRaises((ValueError, OSError)):
            host.transport_export(self.store, self.pin, self.config_path, self.work/'live.qmesh')
        self.assertFalse((self.work/'live.qmesh').exists())
        self.stop()
        transport, receipt = self.export_transport()
        self.assertTrue(transport.is_file())
        # Transaction companions and WAL headers must never masquerade as a cut.
        wal = Path(str(self.store)+'-wal'); wal.write_bytes(b'partial live WAL'); wal.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'STOPPED_CHECKPOINTED'):
            host.inspect_stable_monolith(self.store, self.pin)
        wal.unlink()
        raw = bytearray(self.store.read_bytes()); raw[18:20] = b'\2\2'
        changed = self.work/'wal-header.sqlite3'; changed.write_bytes(raw); changed.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'STOPPED_CHECKPOINTED'):
            host.inspect_stable_monolith(changed, self.pin)

    def test_wrong_pins_truncation_corruption_legacy_transport_and_existing_target_never_install(self):
        self.start(); self.prepared(); self.stop()
        transport, receipt = self.export_transport()
        output = self.work/'canonical.sqlite3'
        for field in ('package','image','transport'):
            args = [self.pin, receipt['canonical_sha256'], receipt['transport_sha256']]
            args[('package','image','transport').index(field)] = '0'*64
            with self.subTest(field=field), self.assertRaises((ValueError, subprocess.CalledProcessError)):
                host.transport_import(transport,*args,output)
            self.assertFalse(output.exists())
        for label, raw in [('truncated',transport.read_bytes()[:-1]),
                           ('corrupt',transport.read_bytes()[:100]+b'\xff'+transport.read_bytes()[101:])]:
            source = self.work/(label+'.qmesh'); source.write_bytes(raw); source.chmod(0o600)
            changed = dict(receipt, transport_sha256=host.digest(raw))
            with self.subTest(label=label), self.assertRaises((ValueError, subprocess.CalledProcessError)):
                self.import_file(source,changed,output)
            self.assertFalse(output.exists())
        script = "import './docs/monitor/mesh-file-codec.js';process.stdout.write(await QikvrtMeshFile.create('legacy-source-only'));"
        legacy = self.work/'legacy.qmesh'
        legacy.write_bytes(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT)); legacy.chmod(0o600)
        with self.assertRaises(subprocess.CalledProcessError):
            self.import_file(legacy,dict(receipt,transport_sha256=host.digest(legacy.read_bytes())),output)
        self.assertFalse(output.exists())
        output.write_bytes(b'existing state must remain unchanged'); output.chmod(0o600)
        with self.assertRaises(ValueError): self.import_file(transport,receipt,output)
        self.assertEqual(output.read_bytes(), b'existing state must remain unchanged')
        alias = self.work/'alias.qmesh'; alias.symlink_to(transport)
        with self.assertRaises(ValueError): self.import_file(alias,receipt,self.work/'absent.sqlite3')
        self.assertFalse((self.work/'absent.sqlite3').exists())
        absent = self.work/'target-with-stale-wal.sqlite3'
        wal = Path(str(absent)+'-wal'); wal.write_bytes(b'stale WAL must remain quarantined'); wal.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'TRANSACTION_COMPANION'):
            self.import_file(transport,receipt,absent)
        self.assertFalse(absent.exists())
        self.assertEqual(wal.read_bytes(), b'stale WAL must remain quarantined')

    def test_forged_transport_hashes_do_not_admit_corrupt_ledger_schema_or_replay_sequence(self):
        self.start(); prepared = self.prepared()
        self.assertEqual(self.rest('commit',prepared=prepared)[0], 200)
        self.stop()
        host.checkpoint_monolith(self.store,self.pin,self.config_path)
        good = host.inspect_stable_monolith(self.store,self.pin)
        mutations = {"body":"UPDATE events SET body_digest='"+'0'*64+"'",
                     "sequence":"UPDATE sqlite_sequence SET seq=0 WHERE name='events'",
                     "identity":"UPDATE meta SET value='broken' WHERE key='epoch'",
                     "trigger":"CREATE TRIGGER unadmitted AFTER INSERT ON events BEGIN SELECT 1; END"}
        for label, sql in mutations.items():
            image = self.work/(label+'.sqlite3'); image.write_bytes(self.store.read_bytes()); image.chmod(0o600)
            with sqlite3.connect(image) as db: db.execute(sql)
            data = dict(good, store=str(image), output=str(self.work/(label+'.qmesh')),
                        file_sha256=host.digest(image.read_bytes()), bytes=image.stat().st_size,
                        repositoryId='synthetic-forged-transport')
            # The transport codec attests bytes only. Native semantic validation
            # must still refuse even when every attacker-supplied hash is coherent.
            raw = subprocess.check_output(['node',str(ROOT/'docs/monitor/mesh-file-store.mjs'),'transport-export'],
                                          input=host.raw_json(data),cwd=ROOT)
            wire = json.loads(raw)
            output = self.work/(label+'-restored.sqlite3')
            with self.subTest(label=label), self.assertRaises((ValueError, sqlite3.Error)):
                self.import_file(Path(data['output']),wire,output)
            self.assertFalse(output.exists())


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
        script = "import './docs/monitor/mesh-file-codec.js';process.stdout.write(await QikvrtMeshFile.create('backend-snapshot-mesh'));"
        mesh = self.volume / 'repository.qmesh'
        mesh.write_bytes(subprocess.check_output(['node','--input-type=module','-e',script],cwd=ROOT))
        mesh.chmod(0o600)
        journal, acknowledged = self.seed_stores(abrupt=True)
        before = self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events')
        self.assertTrue((self.volume/'temdd/events.sqlite3-wal').stat().st_size)
        original = {name:(self.volume/name).read_bytes() for name in host.STATE_FILES if (self.volume/name).exists()}
        self.assertIn('repository.qmesh', original)
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
        ledger = native.Ledger(self.volume, self.subject, read_only=True)
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
        native = host.load_source(self.export, 'qikvrt_temdd_event_ledger'); ledger = native.Ledger(self.volume, self.subject, read_only=True)
        try: self.assertEqual(ledger.replay(0), [acknowledged['event']])
        finally: ledger.close()
        self.assertEqual(json.loads((self.volume/'monitor/node.json').read_bytes())['deliveries'], journal)


class NativeMigrationTests(unittest.TestCase):
    """Real owner ingress/restart of an imported nonempty historical volume."""
    from tests import test_self_host_migration as migration_controls
    _fixture = migration_controls.MigrationTests
    setUpClass = classmethod(_fixture.setUpClass.__func__)
    tearDownClass = classmethod(_fixture.tearDownClass.__func__)
    setUp = _fixture.setUp
    save_config = _fixture.save_config
    seal = _fixture.seal
    native_event = _fixture.native_event
    cli = _fixture.cli
    exported = _fixture.exported
    imported = _fixture.imported
    command = StandaloneTests.command
    start = StandaloneTests.start
    stop = StandaloneTests.stop
    get = StandaloneTests.get
    owner_cli = NativeStandaloneTests.cli
    sql = NativeStandaloneTests.sql

    def test_imported_history_new_subject_owner_commit_and_actual_restart(self):
        imported = self.imported()
        historical = self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events')
        journal = json.loads((self.snapshot/'monitor/node.json').read_bytes())['deliveries']
        epoch = self.event['id'].split(':')[0]
        with sqlite3.connect(self.writer_source/'temdd/events.sqlite3') as db:
            frontier = self.native.digest({'epoch':epoch,'rows':db.execute('SELECT * FROM events ORDER BY seq').fetchall()})
        with self.assertRaisesRegex(self.native.Hold, 'COPIED_OR_UNADMITTED'):
            self.native.Ledger(self.volume,self.subject)
        self.native.Ledger.transfer_local_writer(self.writer_source,self.volume,self.subject,frontier)
        self.start()
        self.assertEqual(self.get('/api/terminal')[1]['ledger_id'], epoch)
        code, prepared = self.owner_cli('durable-prepare'); self.assertEqual(code, 0, prepared)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'), [(1,)])
        code, committed = self.owner_cli('durable-commit', prepared); self.assertEqual(code, 0, committed)
        self.assertEqual(committed['durable_readback']['subject']['head'], self.head)
        self.assertNotEqual(committed['durable_readback']['subject'], self.subject)
        self.assertFalse(committed['EFFECT_ACK_DONE'])
        acknowledged = self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events ORDER BY seq')
        self.assertEqual(acknowledged[:1], historical)
        self.stop(abrupt=True); self.start()
        self.assertEqual(self.get('/api/terminal')[1]['ledger_id'], epoch)
        self.assertEqual(self.sql('SELECT seq,binding,source,native_id,native_digest,body,body_digest FROM events ORDER BY seq'), acknowledged)
        code, fresh = self.owner_cli('durable-readback', prepared); self.assertEqual(code, 0, fresh)
        self.assertEqual(fresh['durable_readback'], committed['durable_readback'])
        self.assertEqual(json.loads((self.volume/'monitor/node.json').read_bytes())['deliveries'], journal)
        migration = self.migration_controls.migration
        self.assertEqual(migration.inventory(self.snapshot), self.before)
        migration.same_bytes(self.volume/'legacy/railway', self.before)
        output = os.environ.get('QIKVRT_STATE_RECOVERY_TEST_EVIDENCE')
        if output:
            directory = Path(output); directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            # Hash-only synthetic observations; never publish a captured volume.
            receipt = {'schema':'qikvrt-railway-migration-native-readback/v1',
                'source_head':host.git(ROOT,'rev-parse','HEAD').decode(),
                'source_tree':host.git(ROOT,'rev-parse','HEAD^{tree}').decode(),
                'source_worktree_dirty':bool(host.git(ROOT,'status','--porcelain','--untracked-files=normal')),
                'fixture_head':self.head,'fixture_tree':self.tree,
                'package_manifest_sha256':self.pin,
                'source_inventory_sha256':self.declaration['inventory_sha256'],
                'export_sha256':self.export_pin,'import_sha256':self.import_pin,
                'completion_sha256':imported['completion_sha256'],
                'historical_rows_sha256':host.digest(host.raw_json(historical)),
                'acknowledged_rows_sha256':host.digest(host.raw_json(acknowledged)),
                'historical_monitor_events_sha256':host.digest(host.raw_json(journal)),
                'historical_row_count':len(historical),'acknowledged_row_count':len(acknowledged),
                'original_epoch_preserved':True,'historical_rows_and_monitor_events_preserved':True,
                'offline_source_and_legacy_bytes_unchanged':True,
                'actual_owner_unix_prepare_commit_and_daemon_restart':True,
                'new_subject_fresh_durable_readback_verified':True,
                'private_state_snapshot_uploaded':False,'railway_data_exported':False,
                'host_admission_verified':False,'public_readback_verified':False,
                'deployed_restart_verified':False,'railway_cutover_verified':False,
                'review_governance_satisfied':False,'effect_ack_done':False}
            (directory/'MIGRATION_NATIVE_OWNER_READBACK.json').write_bytes(host.raw_json(receipt))


if __name__ == '__main__': unittest.main()
