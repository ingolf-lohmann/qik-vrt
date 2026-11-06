#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Separate noVNC denial overlay, preserving pinned recovery originals."""
import http.client
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'deploy/universal-terminal/nginx-native-cutover.conf'
COMPOSE = ROOT / 'deploy/universal-terminal/compose.native-cutover.yaml'
SCRIPT = ROOT / 'deploy/universal-terminal/native-cutover-gateway.sh'
ORIGINAL = ROOT / 'deploy/universal-terminal/nginx.conf'


class NativeCutoverGatewayTests(unittest.TestCase):
    def test_explicit_overlay_keeps_original_unchanged(self):
        compose = COMPOSE.read_text(encoding='utf-8')
        self.assertIn('qikvrt-gateway:', compose)
        self.assertIn('native-cutover-gateway.sh', compose)
        self.assertNotIn('privileged: true', compose)
        script = SCRIPT.read_text(encoding='utf-8')
        for term in ('CUTOVER_GATEWAY_UID_NOT_NOBODY',
                     'ORIGINAL_TERMINAL_ENDPOINTS_NOT_READY',
                     'nginx-native-cutover.conf', 'exec nginx -c'):
            self.assertIn(term, script)

    def test_separate_overlay_denies_anonymous_vnc(self):
        source = CONFIG.read_text(encoding='utf-8')
        marker = 'location ^~ /qik-vrt/mesh/v1/terminal/ {'
        self.assertEqual(source.count(marker), 1)
        block = source.split(marker, 1)[1].split('}', 1)[0]
        self.assertIn('return 403;', block)
        self.assertNotIn('proxy_pass', block)
        self.assertIn('proxy_pass http://127.0.0.1:6080/;',
                      ORIGINAL.read_text(encoding='utf-8'))

    def test_native_nginx_denies_html_and_websocket(self):
        nginx = shutil.which('nginx')
        if not nginx:
            self.skipTest('nginx missing: native image test remains pending')
        with tempfile.TemporaryDirectory(prefix='qikvrt-native-gate-') as tmp:
            work = Path(tmp)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            source = CONFIG.read_text(encoding='utf-8')
            source = source.replace('listen 8080;', 'listen 127.0.0.1:%d;' % port)
            source = source.replace('/tmp/nginx', str(work / 'nginx'))
            source = source.replace('/tmp/qikvrt-mesh-health.json', str(work / 'health.json'))
            source = source.replace('/opt/qikvrt/deploy/universal-terminal', str(work))
            for name in ('client-body', 'proxy', 'fastcgi', 'uwsgi', 'scgi'):
                (work / ('nginx-' + name)).mkdir()
            (work / 'mesh-index.html').write_text('fixture')
            (work / 'health.json').write_text('{"state":"fixture"}')
            config = work / 'nginx.conf'
            config.write_text(source, encoding='utf-8')
            syntax = subprocess.run([nginx, '-t', '-c', str(config)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            proc = subprocess.Popen([nginx, '-c', str(config), '-g', 'daemon off;'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=.1):
                            break
                    except OSError:
                        if proc.poll() is not None:
                            self.fail('nginx exited')
                        time.sleep(.02)
                else:
                    self.fail('nginx readiness timeout')
                probes = [
                    ('/qik-vrt/mesh/v1/terminal/vnc.html', {}),
                    ('/qik-vrt/mesh/v1/terminal/vnc.html?autoconnect=true',
                     {'Cookie':'session=synthetic','Authorization':'Bearer synthetic'}),
                    ('/qik-vrt/mesh/v1/terminal/websockify',
                     {'Connection':'Upgrade','Upgrade':'websocket',
                      'Sec-WebSocket-Key':'dGhlIHNhbXBsZSBub25jZQ==',
                      'Sec-WebSocket-Version':'13'}),
                ]
                for path, headers in probes:
                    with self.subTest(path=path):
                        c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
                        try:
                            c.request('GET', path, headers=headers)
                            res = c.getresponse()
                            self.assertEqual(res.status, 403)
                            self.assertEqual(res.getheader('Cache-Control'), 'no-store')
                            res.read()
                        finally:
                            c.close()
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
