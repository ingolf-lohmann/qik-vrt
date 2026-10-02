#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline acceptance and rejection tests for the exact original-sketch fileset."""
from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_machine_proof as proof
from tools import qikvrt_zenodo_publish as publish

REL = 'docs/publications/2026-10-02-qik-vrt-originalskizzen'
REQUEST = REL + '/publish-request.json'


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')


class OriginalSketchPublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix='qikvrt-originals-offline-')
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        request = json.loads((ROOT / REQUEST).read_text())
        paths = [entry['path'] for entry in request['files']] + [REQUEST, request['owner_authorization']['path']]
        paths += [proof.POLICY_PATH, proof.BUNDLE_SCHEMA_PATH, proof.RETURN_SCHEMA_PATH,
                  proof.LEGACY_POLICY_PATH, proof.LEGACY_BUNDLE_SCHEMA_PATH, proof.LEGACY_RETURN_SCHEMA_PATH]
        for path in paths:
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, destination)
        self.bundle = self.root / REL / 'MACHINE_PROOF_BUNDLE.json'
        self.request = self.root / REQUEST
        self.uploads = [entry['path'] for entry in request['files']]

    def validate(self) -> dict[str, object]:
        return proof.validate_bundle(self.root, self.bundle, upload_paths=self.uploads)

    def mutate_bundle(self, change) -> None:
        value = json.loads(self.bundle.read_text())
        change(value)
        write_json(self.bundle, value)

    def synthetic_authorization(self) -> pathlib.Path:
        """Create an authorization ONLY inside the disposable offline fixture."""
        request = json.loads(self.request.read_text())
        draft = json.loads((self.root / request['owner_authorization']['path']).read_text())
        value = copy.deepcopy(draft['proposed_authorization'])
        returned = json.loads((self.root / value['candidate_return_receipt']['path']).read_text())
        event_time = datetime.datetime.fromisoformat(returned['return']['returned_at'].replace('Z', '+00:00')) + datetime.timedelta(seconds=1)
        value['authorization_event']['channel'] = 'OFFLINE_TEST_FIXTURE_NO_OWNER_DECISION'
        value['authorization_event']['authorized_at'] = event_time.isoformat()
        value['authorization_event']['decision'] = 'AUTHORIZE_EXACT_UPLOAD'
        value['authorized_effects'] = list(publish.OWNER_AUTHORIZED_EFFECTS)
        authorization = self.root / REL / 'OWNER_ZENODO_AUTHORIZATION_TEST_ONLY.json'
        write_json(authorization, value)
        request['owner_authorization'] = publish._identity(authorization.relative_to(self.root).as_posix(), authorization.read_bytes())
        write_json(self.request, request)
        return authorization

    def test_full_originals_bundle_has_exact_claim_inventory(self) -> None:
        receipt = self.validate()
        self.assertEqual(receipt['claim_count'], 11)
        self.assertEqual(receipt['candidate_file_count'], 8)
        self.assertEqual(receipt['artifact_count'], 9)
        value = json.loads(self.bundle.read_text())
        self.assertFalse(any(c['classification'] in {'FORMAL_PROVED', 'EMPIRICALLY_EVIDENCED'} for c in value['claims']))
        originals = [c for c in value['candidate']['files'] if c['name'].endswith('.jpeg')]
        self.assertEqual([c['name'] for c in originals], [f'IMG_{i}.jpeg' for i in range(1096, 1102)])

    def test_manifest_bytes_validate_with_synthetic_fixture_authorization(self) -> None:
        self.synthetic_authorization()
        with mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': publish.PRODUCTION_REPOSITORY}, clear=True):
            manifest = publish.load_manifest(self.request, self.root)
        files = publish.verify_files(manifest, self.root, 'OFFLINE_FIXTURE_NO_CREDENTIAL')
        self.assertEqual(len(files), 18)
        self.assertEqual(manifest['metadata']['upload_type'], 'image')
        self.assertEqual(manifest['metadata']['image_type'], 'drawing')
        self.assertEqual(manifest['repository'], 'Goldkelch/qik-vrt')

    def test_actual_owner_draft_stops_before_credentials_lock_and_client(self) -> None:
        with mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': publish.PRODUCTION_REPOSITORY}, clear=True), \
             mock.patch.object(publish, '_validated_network_secrets') as credentials, \
             mock.patch.object(publish, '_acquire_remote_consumption_lock') as lock, \
             mock.patch.object(zenodo, 'ZenodoClient') as client:
            with self.assertRaisesRegex(zenodo.ZenodoError, 'owner authorization'):
                publish.publish(self.request, self.root)
            credentials.assert_not_called()
            lock.assert_not_called()
            client.assert_not_called()
        self.assertFalse((self.root / REL / 'zenodo-publication.json').exists())

    def test_general_approval_is_not_an_exact_owner_statement(self) -> None:
        authorization = self.synthetic_authorization()
        value = json.loads(authorization.read_text())
        value['authorization_event']['exact_statement'] = 'Freigabe erteilt.'
        value['authorization_event']['statement_sha256'] = hashlib.sha256(b'Freigabe erteilt.').hexdigest()
        write_json(authorization, value)
        request = json.loads(self.request.read_text())
        request['owner_authorization'] = publish._identity(authorization.relative_to(self.root).as_posix(), authorization.read_bytes())
        write_json(self.request, request)
        with mock.patch.dict(os.environ, {'GITHUB_REPOSITORY': publish.PRODUCTION_REPOSITORY}, clear=True):
            with self.assertRaisesRegex(zenodo.ZenodoError, 'canonical authorization statement'):
                publish.load_manifest(self.request, self.root)

    def test_original_byte_drift_is_rejected(self) -> None:
        path = self.root / REL / 'originals/IMG_1096.jpeg'
        raw = path.read_bytes()
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        with self.assertRaisesRegex(proof.ProofGateError, 'mismatch'):
            self.validate()

    def test_extra_missing_or_duplicate_upload_is_rejected(self) -> None:
        cases = [self.uploads[:-1], self.uploads + [self.uploads[0]], self.uploads + [REQUEST]]
        for uploads in cases:
            with self.subTest(uploads=uploads):
                with self.assertRaises(proof.ProofGateError):
                    proof.validate_bundle(self.root, self.bundle, upload_paths=uploads)

    def test_unresolved_claim_identifier_is_rejected(self) -> None:
        self.mutate_bundle(lambda b: b['claims'][0]['source_refs'].__setitem__(0, REL + '/SOURCE_EVIDENCE_BINDINGS.json#MISSING-SOURCE-ID'))
        with self.assertRaisesRegex(proof.ProofGateError, 'unresolved exact identifier'):
            self.validate()

    def test_open_claim_cannot_become_established(self) -> None:
        self.mutate_bundle(lambda b: next(c for c in b['claims'] if c['classification'] == 'OPEN').update(publication_wording='ESTABLISHED_WITHIN_SCOPE'))
        with self.assertRaisesRegex(proof.ProofGateError, 'inconsistent with OPEN'):
            self.validate()

    def test_documentary_source_cannot_masquerade_as_kernel_proof(self) -> None:
        self.mutate_bundle(lambda b: b['claims'][0].update(classification='FORMAL_PROVED', status='PROVED', publication_wording='ESTABLISHED_WITHIN_SCOPE'))
        with self.assertRaisesRegex(proof.ProofGateError, 'lacks a proof reference'):
            self.validate()

    def test_return_receipt_digest_drift_is_rejected(self) -> None:
        path = self.root / REL / 'PREPUBLICATION_RETURN_RECEIPT.json'
        value = json.loads(path.read_text())
        value['candidate_files'][0]['sha256'] = '0' * 64
        write_json(path, value)
        self.mutate_bundle(lambda b: next(a for a in b['artifacts'] if a['kind'] == 'RETURN_RECEIPT').update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), git_blob_sha1=proof.git_blob_sha1(path.read_bytes())))
        with self.assertRaisesRegex(proof.ProofGateError, 'returned candidate SHA-256 mismatch'):
            self.validate()


if __name__ == '__main__':
    unittest.main()
