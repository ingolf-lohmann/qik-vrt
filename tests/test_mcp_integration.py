#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Joint wire regressions of reused #509 evidence reads and #511 data effects."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

from tests import test_qikvrt_mcp_adapter as read_fixture
HEAD, PRINCIPAL, REPO = read_fixture.HEAD, read_fixture.PRINCIPAL, read_fixture.REPO
secret, shim = read_fixture.secret, read_fixture.shim


class McpIntegrationTests(unittest.TestCase):
    # Use the existing HTTP/GitHub fixtures without inheriting their tests.
    setUp = read_fixture.McpHTTPTests.setUp
    close_server = read_fixture.McpHTTPTests.close_server
    get_fixture = read_fixture.McpHTTPTests.get_fixture
    wire = read_fixture.McpHTTPTests.wire
    rpc = read_fixture.McpHTTPTests.rpc
    call = read_fixture.McpHTTPTests.call
    modern = read_fixture.McpHTTPTests.modern
    data = read_fixture.McpHTTPTests.data

    def both_permissions(self):
        os.environ['QIKVRT_MCP_SCOPES'] = ''
        os.environ['QIKVRT_MCP_READ_SCOPES'] = 'repository:read capability:read effect_ack:read'
        os.environ['QIKVRT_MCP_DATA_SCOPES'] = 'ingest readback'
        self.api_headers = {'Authorization': 'Bearer ' + secret(b'w' * 32)}

    def arguments(self):
        payload = b'Joint MCP original bytes\n\x00\xff'
        return payload, {
            'repository': REPO, 'artifact_id': 'joint-proof', 'request_id': 'joint-ingest',
            'expected_sha256': hashlib.sha256(payload).hexdigest(),
            'api_contract_version': '2.3.0',
            'expected_implementation_sha256': shim.mcp_implementation_binding()['sha256'],
        }

    def ingest(self, **changes):
        payload, args = self.arguments()
        args.update(payload_b64=base64.b64encode(payload).decode(), effect_accepted=True)
        args.update(changes)
        return self.modern('tools/call', {'name': 'qikvrt_ingest', 'arguments': args}, self.api_headers)

    def raw_readback(self, args, headers):
        query = urllib.parse.urlencode({k:v for k,v in args.items() if k not in {'repository','artifact_id'}})
        url = f'http://127.0.0.1:{self.server.server_port}/repos/{REPO}/qikvrt/artifacts/joint-proof/readback?{query}'
        request = urllib.request.Request(url, headers=headers)
        try:
            response = urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.code, response.read()

    def test_same_endpoint_preserves_disjoint_authenticated_catalogs(self):
        self.both_permissions()
        names = lambda result: {t['name'] for t in result[1]['result']['tools']}
        evidence = names(self.modern('tools/list'))
        data = names(self.modern('tools/list', headers=self.api_headers))
        self.assertEqual(evidence, {'qikvrt_repository_state','qikvrt_capabilities','qikvrt_effect_ack_result'})
        self.assertEqual(data, {'qikvrt_ingest','qikvrt_readback'})
        self.assertEqual(len(evidence | data), 5)
        self.assertFalse(evidence & data)
        self.assertEqual(self.paths, [])

    def test_cross_credential_calls_never_inherit_permissions(self):
        self.both_permissions()
        _, args = self.arguments()
        for name in ('qikvrt_ingest','qikvrt_readback'):
            self.assertEqual(self.modern('tools/call', {'name':name,'arguments':args})[0],403)
        for name in ('qikvrt_repository_state','qikvrt_capabilities','qikvrt_effect_ack_result'):
            self.assertEqual(self.modern('tools/call', {'name':name,'arguments':{'request_id':'denied'}},self.api_headers)[0],403)
        self.assertEqual(self.raw_readback(args, {'Authorization':'Bearer '+self.token})[0],403)
        self.assertFalse((self.root/'.qikvrt').exists())
        self.assertEqual(self.paths, [])

    def test_joint_write_and_both_independent_readbacks_keep_scope(self):
        self.both_permissions()
        payload,args=self.arguments()
        status,body,_ = self.ingest()
        self.assertEqual(status,200)
        wrapped=body['result']['structuredContent']
        self.assertFalse(body['result']['isError'])
        self.assertEqual(wrapped['handler_result']['effect_state'],'EFFECT_ACK_DONE')
        self.assertEqual(wrapped['handler_result']['effect_scope'],'opaque-byte-storage-only')
        self.assertEqual(wrapped['effect_state'],'EFFECT_ACK_CONTINUE')
        self.assertFalse(wrapped['ordinary_release'])
        self.assertFalse(wrapped['claude_connector_execution_verified'])
        self.assertEqual(self.raw_readback(args,self.api_headers),(200,payload))
        # Separate, explicitly granted read identity reads the same original bytes.
        os.environ['QIKVRT_MCP_READ_SCOPES'] += ' artifact:read'
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        response=self.modern('tools/call', {'name':'qikvrt_readback','arguments':args})
        self.assertEqual(response[0],200)
        result=response[1]['result']['structuredContent']['handler_result']
        self.assertEqual(base64.b64decode(result['payload_b64'],validate=True),payload)
        code,raw=self.raw_readback(args,{'Authorization':'Bearer '+self.token})
        self.assertEqual(code,200)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),args['expected_sha256'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(self.modern('tools/call',{'name':'qikvrt_ingest','arguments':args})[0],403)

    def test_artifact_read_scope_never_grants_write_or_foreign_principal(self):
        self.both_permissions();self.ingest()
        _,args=self.arguments()
        os.environ['QIKVRT_MCP_READ_SCOPES']='artifact:read'
        catalog=self.modern('tools/list')[1]['result']['tools']
        self.assertEqual([t['name'] for t in catalog],['qikvrt_readback'])
        self.assertTrue(catalog[0]['annotations']['readOnlyHint'])
        os.environ['QIKVRT_MCP_PRINCIPAL']='foreign-owner'
        self.assertEqual(self.raw_readback(args,{'Authorization':'Bearer '+self.token})[0],409)
        self.assertEqual(self.raw_readback(args,self.api_headers)[0],200)

    def test_revoke_each_domain_before_replayed_effect(self):
        self.both_permissions();self.ingest()
        target=self.root/'.qikvrt/api/inbox/joint-proof.bin'
        before=(target.read_bytes(),target.stat().st_mtime_ns)
        os.environ['QIKVRT_MCP_DATA_SCOPES']='readback'
        self.assertEqual(self.ingest()[0],403)
        self.assertEqual(before,(target.read_bytes(),target.stat().st_mtime_ns))
        os.environ['QIKVRT_MCP_DATA_SCOPES']='ingest readback'
        os.environ['QIKVRT_API_TOKEN_EXPIRES_UTC']='2000-01-01T00:00:00Z'
        self.assertEqual(self.ingest()[0],401)
        # Expiring a data credential does not expire the independent read key.
        self.assertEqual(self.call()[0],200)
        os.environ['QIKVRT_MCP_TOKEN_EXPIRES_UTC']='2000-01-01T00:00:00Z'
        self.assertEqual(self.call()[0],401)

    def test_handshake_and_catalog_do_not_grant_acceptance(self):
        self.both_permissions()
        self.assertEqual(self.modern('server/discover',headers=self.api_headers)[0],200)
        self.assertEqual(self.modern('tools/list',headers=self.api_headers)[0],200)
        self.assertFalse((self.root/'.qikvrt').exists())
        self.assertEqual(self.ingest(effect_accepted=False)[0],400)
        self.assertFalse((self.root/'.qikvrt').exists())

    def test_read_implementation_drift_is_rejected_before_state_or_network(self):
        self.both_permissions()
        with patch.object(shim,'mcp_implementation_binding',return_value={'sha256':'0'*64}):
            response=self.call()
        self.assertEqual(response[0],400)
        self.assertFalse((self.root/'.qikvrt').exists())
        self.assertEqual(self.paths,[])

    def test_known_legacy_read_versions_do_not_open_new_write_versions(self):
        self.both_permissions()
        for version in ('2025-03-26','2025-06-18'):
            self.assertEqual(self.rpc('ping',headers={'MCP-Protocol-Version':version})[0],200)
            self.assertEqual(self.rpc('ping',headers={**self.api_headers,'MCP-Protocol-Version':version})[0],400)

    def test_separate_allowlists_fail_closed_on_misclassified_scopes(self):
        self.both_permissions()
        os.environ['QIKVRT_MCP_READ_SCOPES']='repository:read ingest'
        self.assertEqual(self.modern('tools/list')[0],503)
        os.environ['QIKVRT_MCP_READ_SCOPES']='repository:read'
        os.environ['QIKVRT_MCP_DATA_SCOPES']='ingest repository:read'
        self.assertEqual(self.modern('tools/list',headers=self.api_headers)[0],503)
        self.assertFalse((self.root/'.qikvrt').exists())

    def test_key_alias_is_rejected_for_both_domains(self):
        self.both_permissions()
        os.environ['QIKVRT_MCP_TOKEN']=secret(b'w'*32)
        self.assertEqual(self.modern('tools/list',headers=self.api_headers)[0],401)
        self.assertEqual(self.call()[0],401)
        self.assertFalse((self.root/'.qikvrt').exists())


if __name__ == '__main__':
    unittest.main()
