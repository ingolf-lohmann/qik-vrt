#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import http.client
import importlib.util
import io
import json
import pathlib
import unittest
import zipfile
from unittest import mock

from tools import qikvrt_batch003_remaining_archive_probe as probe

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "tools/qikvrt_content_disposition_batch_003_dispatch.py"
S = importlib.util.spec_from_file_location("batch003_dispatch", P)
m = importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)


def load(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dispatch = load(m.DISPATCH)
        cls.package = load(m.WORK_PACKAGE)
        cls.work = load(m.WORK_UNIT)
        cls.queue = load(m.QUEUE)
        cls.corpus = load(m.CORPUS)
        cls.envelope = load(m.PROOF_ENVELOPE)
        cls.progress = load(m.AI_PROGRESS)

    def test_positive(self):
        result = m.verify()
        self.assertEqual(result["batch_id"], "CONTENT-DISPOSITION-BATCH-003")
        stage = m.projection_stage()
        if stage == m.STAGE_FINAL_CORPUS:
            self.assertEqual(
                result["state"],
                "ALL_19_SUBJECTS_DISPOSITIONED_PROOF_CORPUS_VERIFIED_PUBLICATION_NOT_AUTHORIZED",
            )
            self.assertEqual(result["active_subject"], "NONE")
            self.assertEqual(result["open_subject_count"], 0)
            self.assertTrue(result["claim_extraction_complete"])
            self.assertIs(result["proof_corpus_published_on_zenodo"], False)
        elif stage == m.STAGE_SECOND_SUBJECT:
            self.assertEqual(result["state"], "BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT")
            self.assertEqual(result["active_subject"], "SUBJECT-b4849e1a2d6b2270")
            self.assertEqual(result["open_subject_count"], 5)
            self.assertTrue(result["claim_extraction_complete"])
        elif stage == m.STAGE_FIRST_SUBJECT:
            self.assertEqual(result["state"], "BATCH_003_DISPATCH_PRESERVED_ADVANCED_PROJECTION_CURRENT")
            self.assertEqual(result["active_subject"], "SUBJECT-172dd9bc2738fa43")
            self.assertEqual(result["open_subject_count"], 6)
            self.assertTrue(result["claim_extraction_complete"])
        else:
            self.assertEqual(result["state"], "BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT")
            self.assertEqual(result["active_subject"], m.FIRST_SUBJECT_ID)
            self.assertEqual(result["open_subject_count"], 7)
            self.assertFalse(result["claim_extraction_complete"])
        for key in ("zenodo_mutation_authorized", "pass", "final_pass", "effect_ack_done"):
            self.assertIs(result[key], False)

    def test_exact_dispatch_partition_and_priority(self):
        m.validate_queue(self.queue)
        m.validate_corpus(self.corpus)
        m.validate_dispatch(self.dispatch, self.package, self.work)
        rows = self.dispatch["batch"]["subjects"]
        self.assertEqual(tuple(row["subject_id"] for row in rows), m.ACTIVE_SUBJECT_IDS)
        self.assertEqual(rows[0]["queue_priority"], 2)
        self.assertTrue(all(row["queue_priority"] == 3 for row in rows[1:]))
        self.assertEqual(tuple(self.dispatch["outside_active_batch"]["subject_ids"]), m.OUTSIDE_SUBJECT_IDS)

    def test_public_source_boundary_is_fail_closed(self):
        m.validate_public_sources(self.envelope)
        files = {row["name"]: row for row in self.package["public_source_files"]}
        receipt = files[m.PUBLIC_RECEIPT["name"]]
        index = files[m.PUBLIC_INDEX["name"]]
        self.assertEqual(receipt["state"], "LOCAL_EXACT_PUBLIC_BYTES_AVAILABLE")
        self.assertEqual(index["state"], "PUBLIC_FREEZE_RECOVERY_REQUIRED_BEFORE_EXTRACTION")
        self.assertTrue(receipt["current_repository_binding"]["repository_byte_match"])
        self.assertFalse(index["current_repository_binding"]["current_repository_byte_match"])
        self.assertNotEqual(m.sha256_bytes(m.LIVE_INDEX.read_bytes()), m.PUBLIC_INDEX["sha256"])

    def test_immutable_dispatch_projection_is_preserved(self):
        progress, status = m.base_expected_projection()
        corpus = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
        self.assertEqual(progress["percent"], 63)
        self.assertEqual(progress["next_action"], m.NEXT_EFFECT)
        self.assertEqual(corpus["counts"]["dispositioned_subjects"], 12)
        self.assertEqual(corpus["counts"]["open_subjects"], 7)
        self.assertEqual(corpus["batch_003"]["state"], "DISPATCHED_FIRST_SUBJECT_ACTIVE")
        self.assertIn(m.NEXT_EFFECT, status)

    def test_final_corpus_precedes_historical_projectors_and_workflow(self):
        if m.FINAL_CORPUS_RECEIPT.is_file():
            self.assertEqual(m.projection_stage(), m.STAGE_FINAL_CORPUS)
            self.assertTrue(m._advanced_module().__name__.endswith("qikvrt_content_disposition_batch_003_all_subjects_compat"))
            workflow = (ROOT / ".github/workflows/qikvrt_batch04_integrity.yml").read_text(encoding="utf-8")
            final_guard = 'if [ -f "$final_script" ] && [ -f "$final_receipt" ]; then'
            second_guard = 'elif [ -f "$second_script" ] && [ -f "$recursive_probe" ]; then'
            self.assertIn(final_guard, workflow)
            self.assertIn(second_guard, workflow)
            self.assertLess(workflow.index(final_guard), workflow.index(second_guard))

    def test_root_projection_is_owned_by_most_advanced_projector(self):
        expected, status = m.expected_projection()
        self.assertEqual(self.progress, expected)
        renderer = m.pretty
        if m.projection_stage() != m.STAGE_DISPATCH:
            renderer = m._advanced_module().pretty
        self.assertEqual(m.AI_PROGRESS.read_text(encoding="utf-8"), renderer(expected))
        self.assertEqual(m.AI_STATUS.read_text(encoding="utf-8"), status)
        corpus = expected["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
        stage = m.projection_stage()
        if stage == m.STAGE_FINAL_CORPUS:
            self.assertEqual(expected["percent"], 100)
            self.assertEqual(corpus["counts"]["dispositioned_subjects"], 19)
            self.assertEqual(corpus["counts"]["open_subjects"], 0)
            self.assertTrue(corpus["batch_003"]["terminal"])
            self.assertIs(corpus["retrospective_proof_corpus"]["published_on_zenodo"], False)
        elif stage == m.STAGE_SECOND_SUBJECT:
            self.assertEqual(expected["percent"], 74)
            self.assertEqual(corpus["counts"]["dispositioned_subjects"], 14)
            self.assertEqual(corpus["counts"]["open_subjects"], 5)
            self.assertEqual(corpus["batch_003"]["active_subject"], "SUBJECT-b4849e1a2d6b2270")
        elif stage == m.STAGE_FIRST_SUBJECT:
            self.assertEqual(expected["percent"], 68)
            self.assertEqual(corpus["counts"]["dispositioned_subjects"], 13)
            self.assertEqual(corpus["counts"]["open_subjects"], 6)
            self.assertEqual(corpus["batch_003"]["active_subject"], "SUBJECT-172dd9bc2738fa43")

    def test_wrong_first_subject_blocks(self):
        bad = copy.deepcopy(self.dispatch)
        bad["batch"]["subjects"][0]["subject_id"] = "SUBJECT-172dd9bc2738fa43"
        with self.assertRaises(m.E):
            m.validate_dispatch(bad, self.package, self.work)

    def test_false_completion_blocks(self):
        for key in (
            "all_content_claims_dispositioned",
            "batch_003_terminal",
            "first_subject_claim_extraction_complete",
            "pass",
            "final_pass",
            "effect_ack_done",
            "zenodo_mutation_authorized",
        ):
            bad = copy.deepcopy(self.dispatch)
            bad["completion_claims"][key] = True
            with self.assertRaises(m.E, msg=key):
                m.validate_dispatch(bad, self.package, self.work)

    def test_live_index_substitution_blocks(self):
        bad = copy.deepcopy(self.package)
        row = next(item for item in bad["public_source_files"] if item["name"] == m.PUBLIC_INDEX["name"])
        row["current_repository_binding"]["current_repository_byte_match"] = True
        with self.assertRaises(m.E):
            m.validate_work_package(bad)

    def test_projection_release_inflation_blocks(self):
        progress, _ = m.expected_projection()
        if m.projection_stage() != m.STAGE_DISPATCH:
            advanced = m._advanced_module()
            validator = advanced.validate_progress_projection
            error_type = advanced.SubjectDispositionError
        else:
            validator = m.validate_progress
            error_type = m.E
        for path in ("top", "corpus"):
            bad = copy.deepcopy(progress)
            if path == "top":
                bad["claims"]["PASS"] = True
            else:
                bad["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]["claims"]["PASS"] = True
            with self.assertRaises(error_type):
                validator(bad)


class ArchiveDownloadTests(unittest.TestCase):
    URL = "https://zenodo.org/api/records/21252649/files/ingolf-lohmann/qik-vrt-v2.13.4-node-r.zip/content"

    class Response(io.BytesIO):
        def __init__(self, data, *, headers=None, status=200, failure=None):
            super().__init__(data)
            self.headers = headers or {}
            self.status = status
            self.failure = failure

        def geturl(self):
            return ArchiveDownloadTests.URL

        def read(self, size=-1):
            if self.failure is not None:
                raise self.failure
            return super().read(size)

    @classmethod
    def setUpClass(cls):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("README.md", "Frozen test archive; no completion claim.\n")
        cls.payload = archive.getvalue()
        cls.headers = {"Content-Length": str(len(cls.payload))}

    def test_complete_download_with_or_without_content_length(self):
        for headers in (self.headers, {}):
            with self.subTest(headers=headers), mock.patch.object(
                probe.urllib.request, "urlopen",
                return_value=self.Response(self.payload, headers=headers),
            ), mock.patch.object(probe.time, "sleep") as sleep:
                self.assertEqual(probe.get(self.URL, "application/octet-stream", 1024), self.payload)
                sleep.assert_not_called()

    def test_truncated_http_200_retries_same_get_and_recovers(self):
        responses = [
            self.Response(self.payload[:17], headers=self.headers),
            self.Response(self.payload, headers=self.headers),
        ]
        with mock.patch.object(probe.urllib.request, "urlopen", side_effect=responses) as opening, mock.patch.object(probe.time, "sleep") as sleep:
            self.assertEqual(probe.get(self.URL, "application/octet-stream", 1024), self.payload)
        self.assertEqual(opening.call_count, 2)
        for call in opening.call_args_list:
            self.assertEqual(call.args[0].full_url, self.URL)
            self.assertEqual(call.args[0].get_method(), "GET")
        sleep.assert_called_once_with(1)

    def test_persistent_truncation_fails_after_five_attempts(self):
        responses = [self.Response(self.payload[:17], headers=self.headers) for _ in range(5)]
        with mock.patch.object(probe.urllib.request, "urlopen", side_effect=responses) as opening, mock.patch.object(probe.time, "sleep") as sleep, self.assertRaisesRegex(probe.E, "GET failed.*IncompleteRead\\(17 bytes read"):
            probe.get(self.URL, "application/octet-stream", 1024)
        self.assertEqual(opening.call_count, 5)
        self.assertEqual(sleep.call_args_list, [mock.call(1), mock.call(2), mock.call(4), mock.call(8)])

    def test_raised_incomplete_read_retries(self):
        responses = [
            self.Response(b"", failure=http.client.IncompleteRead(b"prefix", 100)),
            self.Response(self.payload, headers=self.headers),
        ]
        with mock.patch.object(probe.urllib.request, "urlopen", side_effect=responses) as opening, mock.patch.object(probe.time, "sleep"):
            self.assertEqual(probe.get(self.URL, "application/octet-stream", 1024), self.payload)
        self.assertEqual(opening.call_count, 2)

    def test_partial_and_invalid_length_responses_fail_closed(self):
        cases = [
            ({"Content-Length": "invalid"}, 200),
            ({"Content-Length": "-1"}, 200),
            ({"Content-Length": "1025"}, 200),
            ({"Content-Range": "bytes 0-16/305905", "Content-Length": "17"}, 200),
            ({"Content-Length": "17"}, 206),
        ]
        for headers, status in cases:
            with self.subTest(headers=headers, status=status), mock.patch.object(
                probe.urllib.request, "urlopen",
                return_value=self.Response(self.payload[:17], headers=headers, status=status),
            ) as opening, mock.patch.object(probe.time, "sleep") as sleep, self.assertRaises(probe.E):
                probe.get(self.URL, "application/octet-stream", 1024)
            opening.assert_called_once()
            sleep.assert_not_called()

    def test_body_over_bound_still_fails_without_declared_length(self):
        with mock.patch.object(probe.urllib.request, "urlopen", return_value=self.Response(b"x" * 1025)), mock.patch.object(probe.time, "sleep") as sleep, self.assertRaisesRegex(probe.E, "download bound exceeded"):
            probe.get(self.URL, "application/octet-stream", 1024)
        sleep.assert_not_called()

    def test_exact_byte_mismatches_never_populate_inventory_cache(self):
        rec = probe.SUBJECTS[2]["records"][0]
        for field in ("bytes", "md5", "sha256"):
            expected = probe.dig(self.payload)
            expected[field] = expected[field] + 1 if field == "bytes" else "0" * len(expected[field])
            metadata = {"id": rec["id"], "doi": rec["doi"], "files": [{
                "key": rec["name"], "size": expected["bytes"],
                "checksum": "md5:" + expected["md5"], "links": {"self": self.URL},
            }]}
            cache = {}
            with self.subTest(field=field), mock.patch.object(
                probe, "get", side_effect=[json.dumps(metadata).encode(), self.payload],
            ), mock.patch.object(probe, "inspect_zip") as inspection, self.assertRaisesRegex(
                probe.E, "exact public byte mismatch 21252649:" + field + "; expected=.*observed=",
            ):
                probe.record({"file": expected}, rec, cache)
            self.assertEqual(cache, {})
            inspection.assert_not_called()

    def test_record_requires_exact_payload_after_transport_recovery(self):
        rec = probe.SUBJECTS[2]["records"][0]
        expected = probe.dig(self.payload)
        metadata = {"id": rec["id"], "doi": rec["doi"], "files": [{
            "key": rec["name"], "size": expected["bytes"],
            "checksum": "md5:" + expected["md5"], "links": {"self": self.URL},
        }]}
        body = json.dumps(metadata).encode()
        responses = [
            self.Response(body, headers={"Content-Length": str(len(body))}),
            self.Response(self.payload[:17], headers=self.headers),
            self.Response(self.payload, headers=self.headers),
        ]
        cache = {}
        with mock.patch.object(probe.urllib.request, "urlopen", side_effect=responses) as opening, mock.patch.object(probe.time, "sleep"):
            observed = probe.record({"file": expected}, rec, cache)
        self.assertEqual(opening.call_count, 3)
        self.assertEqual({k: observed[k] for k in expected}, expected)
        self.assertEqual(set(cache), {expected["sha256"]})
        self.assertEqual(cache[expected["sha256"]]["rows"][0]["content_class"], "TEXT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
