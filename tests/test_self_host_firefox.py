# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Actual immutable candidate export + Firefox/X11/VNC/WebSocket runtime.

No provider network, no borrowed production profile, no deployed/public claim.
Run only in the declared Firefox dependency carrier. Missing tools are errors.
"""
from __future__ import annotations
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

from tests.test_self_host_temdd import NativeStandaloneTests
from tests.test_self_host import host, ROOT


class FirefoxCarrierTests(NativeStandaloneTests):
    # The inherited native controls also execute against this browser profile.
    START_TIMEOUT = 60
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory(prefix='qikvrt-firefox-exact-')
        cls.base = Path(cls.scratch.name)
        cls.source = ROOT
        cls.head = host.git(ROOT,'rev-parse','HEAD').decode()
        cls.tree = host.git(ROOT,'rev-parse','HEAD^{tree}').decode()
        cls.export = cls.base/'export'
        cls.receipt = host.freeze(ROOT,cls.export,cls.head,cls.tree,Path('/usr/share/novnc'))
        cls.pin = cls.receipt['manifest_sha256']
        cls.manifest = json.loads((cls.export/'MANIFEST.json').read_bytes())

    def setUp(self):
        super().setUp()
        def port():
            with socket.socket() as s:
                s.bind(('127.0.0.1',0)); return s.getsockname()[1]
        password = self.work/'vnc.password'; password.write_text('Test9Vnc'); password.chmod(0o600)
        self.config.update(terminal_profile='firefox',display=':'+str(100 + os.getpid()%5000),
            novnc_port=port(),vnc_port=port(),browser_password_file=str(password))
        self.save_config()

    def start(self,path=None):
        # Build-time Git is available, but no Git/gh/provider is in runtime PATH.
        binpath=self.work/'runtime-bin';binpath.mkdir(exist_ok=True)
        for name in ('node','python3','python3.12',*host.BROWSER_COMMANDS):
            found=shutil.which(name)
            self.assertIsNotNone(found, name)
            if not (binpath/name).exists(): (binpath/name).symlink_to(found)
        self.assertIsNone(shutil.which('git',path=str(binpath)))
        self.assertIsNone(shutil.which('gh',path=str(binpath)))
        from tests.test_self_host import StandaloneTests
        try:
            return StandaloneTests.start(self,path=binpath)
        except AssertionError as exc:
            # These are isolated synthetic fixtures, never a production profile.
            # Retain bounded diagnostics before the private fixture is deleted.
            evidence = os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
            if evidence:
                p=Path(evidence);p.mkdir(parents=True,exist_ok=True)
                logs={f.name:f.read_bytes()[-65536:].decode('utf-8','replace').replace('Test9Vnc','<synthetic-password>')
                    for f in (self.volume/'browser/logs').glob('*.log')}
                (p/('FAILURE_'+self._testMethodName+'.json')).write_bytes(host.raw_json({
                    'source_head':self.head,'source_tree':self.tree,'manifest_sha256':self.pin,
                    'runtime_failure':str(exc),'fixture_component_logs':logs,'effect_ack_done':False}))
            raise

    def websocket_rfb_auth(self):
        with socket.create_connection(('127.0.0.1',self.config['novnc_port']),timeout=5) as s:
            key=base64.b64encode(b'QIKVRT-test-key16').decode()
            s.sendall(('GET /websockify HTTP/1.1\r\nHost: 127.0.0.1:'+str(self.config['novnc_port'])+
                '\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+
                '\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Protocol: binary\r\n\r\n').encode())
            f=s.makefile('rb')
            header=[]
            while True:
                line=f.readline();self.assertTrue(line)
                if line==b'\r\n':break
                header.append(line)
            self.assertIn(b'101',header[0])
            def frame():
                first=f.read(2);self.assertEqual(len(first),2)
                length=first[1]&127
                if length==126:length=int.from_bytes(f.read(2),'big')
                if length==127:length=int.from_bytes(f.read(8),'big')
                self.assertLess(length,65536)
                data=f.read(length);self.assertEqual(len(data),length)
                return data
            banner=frame();self.assertEqual(banner,b'RFB 003.008\n')
            mask=b'QIKV';payload=b'RFB 003.008\n'
            s.sendall(bytes([0x82,0x80|len(payload)])+mask+bytes(v^mask[i%4] for i,v in enumerate(payload)))
            schemes=frame();self.assertGreater(len(schemes),1)
            count=schemes[0];self.assertEqual(len(schemes),count+1)
            self.assertIn(2,schemes[1:]);self.assertNotIn(1,schemes[1:])
            f.close()
            return {'websocket_status':101,'rfb_version':banner.decode().strip(),'vnc_authentication_required':True}

    def kernel_listeners(self):
        listeners=[]
        for name in ('tcp','tcp6'):
            for line in Path('/proc/net/'+name).read_text().splitlines()[1:]:
                row=line.split()
                if row[3] != '0A': continue
                address,port=row[1].split(':')
                self.assertEqual(name, 'tcp', 'The IPv4-only carrier must have no extra IPv6 listener')
                self.assertEqual(address, '0100007F', 'All carrier listeners must be loopback')
                listeners.append({'address':'127.0.0.1','port':int(port,16)})
        self.assertEqual({e['port'] for e in listeners}, {self.config[k] for k in ('port','terminal_port','novnc_port','vnc_port')})
        return sorted(listeners,key=lambda e:e['port'])

    def test_actual_firefox_window_novnc_websocket_and_candidate_binding(self):
        interfaces = sorted(name for _, name in socket.if_nameindex())
        self.assertEqual(interfaces, ['lo'], 'This acceptance requires the declared network-none carrier')
        init_name=Path('/proc/1/comm').read_text().strip()
        self.assertIn(init_name, ('docker-init','tini'), 'The declared container must have a real child reaper')
        init_binding={'name':init_name,'executable_sha256':host.digest(Path('/proc/1/exe').read_bytes())}
        runtime=self.start()
        self.assertTrue(runtime['browser_startup_verified'])
        self.assertTrue(runtime['native_terminal_daemon_available'])
        self.assertEqual(runtime['source_head'], self.head)
        self.assertFalse((self.export/'.git').exists())
        readback=self.websocket_rfb_auth()
        listeners=self.kernel_listeners()
        prepared,event=self.commit_input()
        terminal=self.get('/api/terminal')[1]
        self.assertEqual(terminal['subject'],event['subject'])
        evidence=os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
        if evidence:
            p=Path(evidence);p.mkdir(parents=True,exist_ok=True)
            receipt={'schema':'qikvrt-self-host-firefox-runtime-readback/v1',
                'observed_at':datetime.now(timezone.utc).isoformat(),'source_head':self.head,'source_tree':self.tree,
                'manifest_sha256':self.pin,'config_sha256':host.digest(self.config_path.read_bytes()),
                'native_subject':terminal['subject'],'ledger_id':terminal['ledger_id'],
                'native_durable_event':event,'firefox_version':self.manifest['browser_runtime']['firefox_version'],
                'browser_executables':self.manifest['browser_runtime']['executables'],'transport':readback,
                'firefox_navigator_window_observed':True,'git_in_runtime_path':False,'gh_in_runtime_path':False,
                'native_terminal_document_title_observed':True,
                'outbound_network':'DOCKER_NETWORK_NONE','observed_network_interfaces':interfaces,
                'observed_listeners':listeners,'container_init':init_binding,
                'scope':'ACTUAL_EXACT_CANDIDATE_RUNTIME_IN_CI_CONTAINER',
                'independent_host_identity_verified':False,'public_https_readback_verified':False,
                'deployment_performed':False,'effect_ack_done':False}
            (p/'FIREFOX_NATIVE_READBACK.json').write_bytes(host.raw_json(receipt))
            (p/'MANIFEST.json').write_bytes((self.export/'MANIFEST.json').read_bytes())
            (p/'DISTRIBUTION_PACKAGES.tsv').write_bytes(Path('/usr/local/share/qikvrt-distribution-packages.tsv').read_bytes())

    def test_crash_restart_preserves_firefox_profile_and_acknowledged_native_bytes(self):
        self.start(); prepared,event=self.commit_input()
        marker=self.volume/'browser/profile/qikvrt-test-restart-marker'
        marker.write_bytes(b'private fixture marker; no credentials')
        before=self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events')
        old_xvfb=[]
        for p in Path('/proc').glob('[0-9]*'):
            try:
                if p.joinpath('comm').read_text().strip()=='Xvfb' and os.getpgid(int(p.name))==self.process.pid:
                    old_xvfb.append(int(p.name))
            except (OSError,ValueError): pass
        self.assertEqual(len(old_xvfb),1)
        self.stop(abrupt=True);self.start()
        self.assertTrue(all(not Path('/proc/'+str(pid)).exists() for pid in old_xvfb))
        listeners_after_restart=self.kernel_listeners()
        self.assertEqual(marker.read_bytes(),b'private fixture marker; no credentials')
        self.assertEqual(self.sql('SELECT binding,source,native_id,native_digest,body,body_digest FROM events'),before)
        code,readback=self.cli('durable-readback',prepared)
        self.assertEqual(code,0,readback);self.assertEqual(readback['durable_readback'],event)
        self.websocket_rfb_auth()
        evidence=os.environ.get('QIKVRT_BROWSER_TEST_EVIDENCE')
        if evidence:
            (Path(evidence)/'FIREFOX_NATIVE_RESTART_READBACK.json').write_bytes(host.raw_json({
                'schema':'qikvrt-self-host-firefox-restart-readback/v1','source_head':self.head,'source_tree':self.tree,
                'manifest_sha256':self.pin,'native_durable_event':event,'profile_marker_preserved':True,
                'native_original_rows_preserved':True,'crashed_xvfb_pids':old_xvfb,
                'crashed_xvfb_reaped':True,'observed_listeners_after_restart':listeners_after_restart,
                'public_https_readback_verified':False,'effect_ack_done':False}))

    # The inherited adversarial native controls apply to this actual browser
    # variant too. They exercise the same kernel, with actual GUI children.


if __name__=='__main__':unittest.main()
