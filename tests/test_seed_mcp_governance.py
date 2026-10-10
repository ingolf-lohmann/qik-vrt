#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Joint Seed/lifecycle/MCP wire regressions with explicit remote fixtures."""
from __future__ import annotations

import base64
import copy
import hashlib
import os
import unittest

from tests import test_mcp_integration as mcp_fixture
from tests import test_seed_workflows as seed_fixture
from tests import test_mirror_lifecycle_publication as lifecycle_fixture
from tools import qikvrt_seed_common as seed
from tools import qikvrt_mirror_node_lifecycle as lifecycle


class SeedMcpGovernanceTests(unittest.TestCase):
    # Reuse existing transport/credential fixtures without rerunning their tests.
    setUp = mcp_fixture.McpIntegrationTests.setUp
    close_server = mcp_fixture.McpIntegrationTests.close_server
    get_fixture = mcp_fixture.McpIntegrationTests.get_fixture
    wire = mcp_fixture.McpIntegrationTests.wire
    rpc = mcp_fixture.McpIntegrationTests.rpc
    call = mcp_fixture.McpIntegrationTests.call
    modern = mcp_fixture.McpIntegrationTests.modern
    both_permissions = mcp_fixture.McpIntegrationTests.both_permissions
    arguments = mcp_fixture.McpIntegrationTests.arguments
    ingest = mcp_fixture.McpIntegrationTests.ingest
    raw_readback = mcp_fixture.McpIntegrationTests.raw_readback

    def seed_case(self):
        case = seed_fixture.SeedWorkflowTests()
        case.setUp()
        self.addCleanup(case.tearDown)
        os.environ['QIKVRT_REPO_ROOT'] = str(case.root)
        return case

    def lifecycle_case(self):
        case = lifecycle_fixture.LifecyclePublicationTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        os.environ['QIKVRT_REPO_ROOT'] = str(case.root)
        return case

    @staticmethod
    def node_files(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
                if p.is_file() and '.qikvrt' not in p.relative_to(root).parts}

    def store_node_bytes(self, raw):
        _, args = self.arguments()
        args['expected_sha256'] = hashlib.sha256(raw).hexdigest()
        response = self.ingest(payload_b64=base64.b64encode(raw).decode(),
                               expected_sha256=args['expected_sha256'])
        self.assertEqual(response[0], 200)
        self.assertFalse(response[1]['result']['isError'])
        wrapped = response[1]['result']['structuredContent']
        self.assertEqual(wrapped['handler_result']['effect_scope'], 'opaque-byte-storage-only')
        self.assertEqual(wrapped['effect_state'], 'EFFECT_ACK_CONTINUE')
        self.assertFalse(wrapped['ordinary_release'])
        return args

    def test_fresh_seed_acknowledgement_survives_separate_mcp_byte_readback(self):
        self.both_permissions()
        case = self.seed_case()
        fetch = case.acknowledgement_fetcher()
        result = seed.run_acknowledgement(case.root, 'joint-ack', fetch, now=seed_fixture.NOW)
        ack = result['acknowledgement']
        self.assertEqual(ack['observed_authority_commit'], '1' * 40)
        self.assertEqual(fetch.calls[0], fetch.calls[-1])
        seed._validate_ack(ack, seed.load_handshake(case.root))
        raw = (case.root / 'qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json').read_bytes()
        before = self.node_files(case.root)
        args = self.store_node_bytes(raw)
        os.environ['QIKVRT_MCP_READ_SCOPES'] += ' artifact:read'
        code, original = self.raw_readback(args, {'Authorization': 'Bearer ' + self.token})
        self.assertEqual((code, original), (200, raw))
        self.assertEqual(hashlib.sha256(original).hexdigest(), args['expected_sha256'])
        self.assertEqual(before, self.node_files(case.root))

    def test_stored_historical_ack_cannot_register_or_replace_fresh_seed_evidence(self):
        self.both_permissions()
        case = self.seed_case()
        fetch = case.acknowledgement_fetcher()
        historical = {'schema': 'historical-ack', 'guid': seed_fixture.GUID,
                      'repository': seed_fixture.SOURCE, 'seed_repository': seed_fixture.SEED,
                      'status': 'ACCEPTED_BY_SEED'}
        pending = case.root / 'qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json'
        pending.write_bytes(b'{"status":"PENDING_SEED_ACCEPTANCE"}\n')
        before = self.node_files(case.root)
        raw = seed.canonical_json_bytes(historical)
        args = self.store_node_bytes(raw)
        self.assertEqual(self.raw_readback(args, self.api_headers), (200, raw))
        with self.assertRaises(seed.SeedError):
            seed._validate_ack(historical, seed.load_handshake(case.root))
        entry_url = next(p for p in fetch.documents if '/nodes/' in p)
        for change in ({'schema': 'historical'}, {'seed_repository': 'foreign/seed'},
                       {'accepted_utc': '2026-07-01T00:00:00Z'}, {'node_request_sha256': '0' * 64}):
            with self.subTest(change=change):
                values = copy.deepcopy(fetch.documents)
                values[entry_url].update(change)
                with self.assertRaises(seed.SeedError):
                    seed.run_acknowledgement(case.root, 'joint-rejected',
                                             seed_fixture.FakeFetcher(values), now=seed_fixture.NOW)
                self.assertEqual(before, self.node_files(case.root))

    def test_mcp_storage_grant_cannot_bypass_native_lifecycle_code_owner_rule(self):
        self.both_permissions()
        case = self.lifecycle_case()
        raw = (case.root / 'qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json').read_bytes()
        before = self.node_files(case.root)
        args = self.store_node_bytes(raw)
        self.assertEqual(self.raw_readback(args, self.api_headers), (200, raw))
        case.api.rules = []
        with self.assertRaisesRegex(lifecycle.Block, 'CODE_OWNER_RULE_NOT_ENFORCED'):
            case.publish()
        self.assertTrue(all(method == 'GET' for method, _, _ in case.api.calls))
        self.assertEqual(case.api.refs, {'main': lifecycle_fixture.SOURCE})
        self.assertEqual(before, self.node_files(case.root))

    def test_lifecycle_readback_and_mcp_permissions_keep_independent_proof_scopes(self):
        self.both_permissions()
        case = self.lifecycle_case()
        result = case.publish()
        documents, head = lifecycle.read_public(case.node, case.api, lifecycle_fixture.NOW)
        self.assertEqual(head, result['head'])
        self.assertEqual(case.api.refs['main'], lifecycle_fixture.SOURCE)
        self.assertFalse(result['main_persisted'])
        raw = seed.canonical_json_bytes(documents[0].value)
        args = self.store_node_bytes(raw)
        os.environ['QIKVRT_MCP_READ_SCOPES'] += ' artifact:read'
        self.assertEqual(self.raw_readback(args, {'Authorization': 'Bearer ' + self.token}), (200, raw))
        refs = dict(case.api.refs)
        os.environ['QIKVRT_MCP_READ_SCOPES'] = 'repository:read'
        self.assertEqual(self.raw_readback(args, {'Authorization': 'Bearer ' + self.token})[0], 403)
        self.assertEqual(self.raw_readback(args, self.api_headers), (200, raw))
        tree = case.api.trees[case.api.commits[head]['tree']['sha']]
        blob = next(e['sha'] for e in tree if e['path'] == lifecycle.FILES[0])
        case.api.blobs[blob] += b' '
        with self.assertRaises(lifecycle.Block):
            lifecycle.read_public(case.node, case.api, lifecycle_fixture.NOW)
        self.assertEqual(case.api.refs, refs)

    def test_mcp_catalog_and_credentials_expose_no_seed_or_governance_writer(self):
        self.both_permissions()
        case = self.seed_case()
        pending = case.root / 'qikvrt/runtime/onboarding/SEED_ACCEPTANCE_STATUS.json'
        pending.write_bytes(b'{"status":"PENDING_SEED_ACCEPTANCE"}\n')
        before = self.node_files(case.root)
        for name in ('qikvrt_seed_register', 'qikvrt_lifecycle_publish', 'workflowDispatch', 'rulesetDispatch'):
            for headers in ({'Authorization': 'Bearer ' + self.token}, self.api_headers):
                with self.subTest(name=name, data_credential=headers == self.api_headers):
                    response = self.modern('tools/call', {'name': name, 'arguments': {}}, headers)
                    body = response[1]
                    self.assertTrue('error' in body or body['result']['isError'])
        response = self.wire({'event_type': 'qikvrt_mesh_api', 'client_payload': {}},
                             path=f'/repos/{mcp_fixture.REPO}/dispatches')
        self.assertEqual(response[0], 401)
        self.assertEqual(self.paths, [])
        self.assertEqual(before, self.node_files(case.root))


if __name__ == '__main__':
    unittest.main()
