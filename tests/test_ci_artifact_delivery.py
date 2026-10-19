# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Regression for three finalized uploads followed by a two-item listing.

The workflow's real bounded downloader executes against in-memory HTTPS
responses; no provider credentials, network calls or production effect occur.
"""
import hashlib
import io
import os
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest import mock
from urllib.error import HTTPError
import zipfile


class FinalizedArtifactDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(os.environ.get('CI_ARTIFACT_WORKFLOW_PATH',
                    Path(__file__).resolve().parents[1] / '.github/workflows/qikvrt_ci.yml'))
        source = path.read_text()
        start = "          python3 -B - <<'PYFINALIZEDPARTS'\n"
        block = textwrap.dedent(source.split(start, 1)[1].split('          PYFINALIZEDPARTS', 1)[0])
        cls.namespace = {'__name__': 'workflow_delivery_regression'}
        exec(compile(block, str(path), 'exec'), cls.namespace)
        cls.workflow = source

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = {'PART_COUNT': '3', 'GITHUB_REPOSITORY': 'ingolf-lohmann/qik-vrt',
                    'ARTIFACT_TOKEN': 'fixture-token', 'RUNNER_TEMP': self.temp.name}
        self.ids = ['12185603647', '12186371554', '12185703447']
        self.archives = {}
        for index, artifact_id in enumerate(self.ids):
            self.set_archive(index, artifact_id, f'artifact.part-{index:03d}',
                             f'original-fixture-part-{index}'.encode())
        self.api_requests = []
        self.payload_requests = []

    def set_archive(self, index, artifact_id, filename, content):
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            archive.writestr(filename, content)
        data = output.getvalue()
        self.archives[artifact_id] = data
        self.env[f'PART{index}_ID'] = artifact_id
        self.env[f'PART{index}_DIGEST'] = 'sha256:' + hashlib.sha256(data).hexdigest()

    def run_delivery(self):
        case = self

        class API:
            def open(self, request, timeout):
                case.api_requests.append(request)
                artifact_id = request.full_url.rsplit('/', 2)[1]
                case.assertIn(artifact_id, case.ids)
                raise HTTPError(request.full_url, 302, 'Found',
                                {'Location': f'https://fixture.blob.core.windows.net/{artifact_id}'}, None)

        class Payload:
            def open(self, request, timeout):
                case.payload_requests.append(request)
                return io.BytesIO(case.archives[request.full_url.rsplit('/', 1)[1]])

        def opener(handler):
            return API() if isinstance(handler, case.namespace['NoCredentialRedirect']) else Payload()

        with mock.patch.dict(self.namespace, {'build_opener': opener}):
            return self.namespace['download_finalized_parts'](self.env)

    def test_all_three_finalized_parts_arrive_without_listing_selection(self):
        # These exact IDs were finalized in the observed failed run. Its list
        # response omitted the third ID; selection must use all upload receipts.
        stale_inventory = self.ids[:2]
        self.assertNotIn(self.ids[2], stale_inventory)
        result = self.run_delivery()
        self.assertEqual(result['artifact_ids'], self.ids)
        self.assertEqual(len(self.api_requests), 3)
        for index in range(3):
            self.assertEqual((Path(self.temp.name) / 's1-firefox158-delivered' /
                             f'artifact.part-{index:03d}').read_bytes(),
                             f'original-fixture-part-{index}'.encode())
        self.assertNotIn('pattern: qikvrt-s1-firefox158-runtime-${{ github.event.pull_request.head.sha || github.sha }}-part-*', self.workflow)

    def test_credential_never_reaches_payload_origin(self):
        self.run_delivery()
        self.assertTrue(all(r.get_header('Authorization') == 'Bearer fixture-token'
                            for r in self.api_requests))
        self.assertTrue(all(r.get_header('Authorization') is None for r in self.payload_requests))

    def test_corrupt_zip_digest_is_rejected_before_part_write(self):
        self.env['PART0_DIGEST'] = 'sha256:' + '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'ZIP_DIGEST_MISMATCH'):
            self.run_delivery()
        self.assertFalse((Path(self.temp.name) / 's1-firefox158-delivered/artifact.part-000').exists())

    def test_missing_finalized_id_is_rejected_before_any_request(self):
        self.env['PART2_ID'] = ''
        with self.assertRaisesRegex(RuntimeError, 'ARTIFACT_ID_REQUIRED'):
            self.run_delivery()
        self.assertEqual(self.api_requests, [])

    def test_duplicate_id_is_rejected_before_any_request(self):
        self.env['PART2_ID'] = self.env['PART1_ID']
        with self.assertRaisesRegex(RuntimeError, 'DISTINCT_FINALIZED'):
            self.run_delivery()
        self.assertEqual(self.api_requests, [])

    def test_traversal_member_is_not_extracted(self):
        self.set_archive(0, self.ids[0], '../escape', b'not admitted')
        with self.assertRaisesRegex(RuntimeError, 'EXACT_BOUNDED_ARTIFACT_PART_REQUIRED'):
            self.run_delivery()
        self.assertFalse((Path(self.temp.name) / 'escape').exists())

    def test_existing_delivery_is_not_silently_overwritten(self):
        self.run_delivery()
        with self.assertRaisesRegex(RuntimeError, 'EXISTING_DELIVERY_PART'):
            self.run_delivery()

    def test_original_manifest_join_remains_required(self):
        self.assertIn("'container-artifact-join'", self.workflow)
        self.assertIn("'--manifest-sha256',os.environ['MANIFEST_SHA256']", self.workflow)
        self.assertIn("'--transport-sha256',os.environ['ARCHIVE_SHA256']", self.workflow)

    def test_payload_redirect_cannot_downgrade_https_or_add_credentials(self):
        handler = self.namespace['HTTPSPayloadRedirect']()
        for url in ['http://fixture.invalid/part', 'https://user:secret@fixture.invalid/part']:
            with self.subTest(url=url), self.assertRaisesRegex(RuntimeError, 'HTTPS_REQUIRED'):
                handler.redirect_request(None, None, 302, '', {}, url)


if __name__ == '__main__':
    unittest.main()
