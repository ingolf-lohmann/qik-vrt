#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline tests for the one-version formalization v2 Zenodo client."""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import sys
import tempfile
import unittest
import urllib.parse

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_formalization_v2_zenodo as release  # noqa: E402
from tools import qikvrt_zenodo_actions as zenodo  # noqa: E402


TOKEN = "f" * 64
DRAFT_ID = 21510001
DRAFT_DOI = "10.5281/zenodo.21510001"


def json_response(status: int, value: object) -> zenodo.HttpResponse:
    return zenodo.HttpResponse(
        status=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(value, sort_keys=True).encode("utf-8"),
    )


class FakeTransport:
    """Stateful legacy-API simulation; no socket or external write is used."""

    def __init__(
        self,
        target_metadata: dict[str, object],
        *,
        existing_draft: bool,
        action_status: int = 201,
        draft_concept: int = release.CONCEPT_RECORD_ID,
        corrupt_download: bool = False,
        source_self_latest_draft: bool = False,
        action_self_latest_draft: bool = False,
        post_action_self_polls: int = 0,
        source_submitted: bool | None = True,
        source_state: str | None = "done",
        action_draft_id: int = DRAFT_ID,
    ) -> None:
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.target_metadata = copy.deepcopy(target_metadata)
        self.action_status = action_status
        self.corrupt_download = corrupt_download
        self.source_self_latest_draft = source_self_latest_draft
        self.action_self_latest_draft = action_self_latest_draft
        self.post_action_self_polls = post_action_self_polls
        self.source_submitted = source_submitted
        self.source_state = source_state
        self.action_draft_id = action_draft_id
        self.newversion_called = False
        self.published = False
        self.latest_record_id = release.SOURCE_RECORD_ID
        self.source_has_draft = existing_draft
        self.draft: dict[str, object] = {
            "id": DRAFT_ID,
            "conceptrecid": draft_concept,
            "doi": DRAFT_DOI,
            "metadata": {
                **copy.deepcopy(target_metadata),
                "prereserve_doi": {"doi": DRAFT_DOI},
            },
            "files": [
                self._file(
                    "inherited-formalization-v1.zip",
                    b"old inherited bytes",
                    "old-file",
                )
            ],
            "links": {
                "self": f"https://zenodo.org/api/deposit/depositions/{DRAFT_ID}",
                "bucket": "https://zenodo.org/api/files/formalization-v2-bucket",
            },
        }

    @staticmethod
    def _file(name: str, data: bytes, file_id: str) -> dict[str, object]:
        return {
            "id": file_id,
            "filename": name,
            "filesize": len(data),
            "checksum": "md5:" + hashlib.md5(data).hexdigest(),  # noqa: S324
            "_data": data,
            "links": {
                "self": (
                    "https://zenodo.org/api/files/formalization-v2-bucket/"
                    + urllib.parse.quote(name, safe="")
                ),
                "download": (
                    "https://zenodo.org/api/files/formalization-v2-bucket/"
                    + urllib.parse.quote(name, safe="")
                ),
            },
        }

    def _source_public(self) -> dict[str, object]:
        return {
            "id": release.SOURCE_RECORD_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "doi": release.SOURCE_VERSION_DOI,
            "metadata": {
                "relations": {"version": [{"index": 2, "is_last": not self.published}]}
            },
            "files": [],
            "links": {
                "latest": (
                    "https://zenodo.org/api/records/"
                    + str(self.latest_record_id)
                )
            },
        }

    def _source_owner(self) -> dict[str, object]:
        links: dict[str, object] = {
            "self": (
                "https://zenodo.org/api/deposit/depositions/"
                + str(release.SOURCE_RECORD_ID)
            )
        }
        if self.source_has_draft and not (
            self.newversion_called and self.post_action_self_polls > 0
        ):
            links["latest_draft"] = (
                "https://zenodo.org/api/deposit/depositions/" + str(DRAFT_ID)
            )
        elif self.source_self_latest_draft or self.newversion_called:
            links["latest_draft"] = (
                "https://zenodo.org/api/deposit/depositions/"
                + str(release.SOURCE_RECORD_ID)
            )
            if self.newversion_called and self.post_action_self_polls > 0:
                self.post_action_self_polls -= 1
        value: dict[str, object] = {
            "id": release.SOURCE_RECORD_ID,
            "conceptrecid": release.CONCEPT_RECORD_ID,
            "metadata": {},
            "files": [],
            "links": links,
        }
        if self.source_submitted is not None:
            value["submitted"] = self.source_submitted
        if self.source_state is not None:
            value["state"] = self.source_state
        return value

    def _public_draft(self) -> dict[str, object]:
        value = copy.deepcopy(self.draft)
        metadata = value["metadata"]
        assert isinstance(metadata, dict)
        metadata.pop("prereserve_doi", None)
        upload_type = metadata.pop("upload_type", None)
        if upload_type is not None:
            metadata["resource_type"] = {"type": upload_type}
        license_value = metadata.get("license")
        if isinstance(license_value, str):
            metadata["license"] = {"id": license_value}
        public_files: list[dict[str, object]] = []
        raw_files = value["files"]
        assert isinstance(raw_files, list)
        for raw in raw_files:
            item = copy.deepcopy(raw)
            item["key"] = item.pop("filename")
            item["size"] = item.pop("filesize")
            item.pop("_data", None)
            public_files.append(item)
        value["files"] = public_files
        value["links"] = {
            "latest": f"https://zenodo.org/api/records/{DRAFT_ID}"
        }
        value["submitted"] = True
        value["state"] = "done"
        return value

    @staticmethod
    def _clean(value: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(value)
        result.pop("_data", None)
        for item in result.get("files", []):
            assert isinstance(item, dict)
            item.pop("_data", None)
        return result

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = zenodo.MAX_RESPONSE_BYTES,
    ) -> zenodo.HttpResponse:
        del content_type, max_response_bytes
        method = method.upper()
        path = urllib.parse.urlsplit(url).path
        self.calls.append((method, path, body))

        if method == "GET" and path == f"/api/records/{release.SOURCE_RECORD_ID}":
            return json_response(200, self._source_public())
        if method == "GET" and path == f"/api/records/{DRAFT_ID}":
            if not self.published:
                return json_response(404, {"message": "not public"})
            return json_response(200, self._public_draft())
        if method == "GET" and path == (
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}"
        ):
            return json_response(200, self._source_owner())
        if method == "POST" and path == (
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion"
        ):
            self.newversion_called = True
            self.source_has_draft = True
            linked_id = (
                release.SOURCE_RECORD_ID
                if self.action_self_latest_draft
                else self.action_draft_id
            )
            return json_response(
                self.action_status,
                {
                    "id": 99999999,
                    "links": {
                        "latest_draft": (
                            "https://zenodo.org/api/deposit/depositions/"
                            + str(linked_id)
                        )
                    },
                },
            )
        if method == "GET" and path == f"/api/deposit/depositions/{DRAFT_ID}":
            if self.published:
                return json_response(404, {"message": "not editable"})
            return json_response(200, self._clean(self.draft))
        if method == "PUT" and path == f"/api/deposit/depositions/{DRAFT_ID}":
            payload = json.loads((body or b"{}").decode("utf-8"))
            self.draft["metadata"] = copy.deepcopy(payload["metadata"])
            return json_response(200, self._clean(self.draft))
        if method == "POST" and path == (
            f"/api/deposit/depositions/{DRAFT_ID}/actions/publish"
        ):
            self.published = True
            self.latest_record_id = DRAFT_ID
            return json_response(202, {"status": "queued"})

        if path.startswith("/api/files/formalization-v2-bucket/"):
            name = urllib.parse.unquote(path.rsplit("/", 1)[1])
            raw_files = self.draft["files"]
            assert isinstance(raw_files, list)
            existing = next(
                (
                    item
                    for item in raw_files
                    if isinstance(item, dict) and item.get("filename") == name
                ),
                None,
            )
            if method == "DELETE":
                if existing is None:
                    return json_response(404, {"message": "already absent"})
                raw_files.remove(existing)
                return zenodo.HttpResponse(204, {}, b"")
            if method == "PUT":
                if existing is not None:
                    raw_files.remove(existing)
                item = self._file(name, body or b"", "uploaded-" + name)
                raw_files.append(item)
                return json_response(201, self._clean(item))
            if method == "GET" and existing is not None:
                data = existing["_data"]
                assert isinstance(data, bytes)
                if self.corrupt_download:
                    data = data + b"!"
                return zenodo.HttpResponse(
                    200, {"Content-Type": "application/octet-stream"}, data
                )

        return json_response(
            500, {"message": f"unhandled fake request {method} {path}"}
        )


class FormalizationV2ZenodoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="qikvrt-formalization-v2-zenodo-test-"
        )
        self.root = pathlib.Path(self.temporary.name)
        self.payload = self.root / "formalization-v2.tar.gz"
        self.payload.write_bytes(b"deterministic formalization v2 archive\n")
        self.metadata: dict[str, object] = {
            "title": "QIK-VRT manuscript formalization v2.0 alpha",
            "upload_type": "software",
            "description": "Partial machine formalization with explicit boundaries.",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "version": "2.0.0-alpha",
            "access_right": "open",
            "license": "other-nc",
            "keywords": ["Lean 4", "formalization", "QIK-VRT"],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def entry(self) -> dict[str, object]:
        data = self.payload.read_bytes()
        return {
            "path": self.payload.name,
            "name": self.payload.name,
            "size": len(data),
            "md5": hashlib.md5(data).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def manifest(self) -> dict[str, object]:
        return {
            "schema": release.MANIFEST_SCHEMA,
            "software": {
                "source_record_id": release.SOURCE_RECORD_ID,
                "concept_record_id": release.CONCEPT_RECORD_ID,
                "metadata": copy.deepcopy(self.metadata),
                "files": [self.entry()],
            },
        }

    @staticmethod
    def client(transport: FakeTransport, *, attempts: int = 2) -> zenodo.ZenodoClient:
        return zenodo.ZenodoClient(
            TOKEN,
            zenodo.DEFAULT_BASE_URL,
            transport=transport,
            poll_attempts=attempts,
            poll_interval=0,
            sleeper=lambda _seconds: None,
        )

    def invoke(self, transport: FakeTransport) -> dict[str, object]:
        return release.publish_release(
            self.client(transport),
            self.manifest(),
            self.root,
            "a" * 64,
        )

    def test_resumes_only_identified_source_latest_draft_and_publishes(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        result = self.invoke(transport)
        paths = [(method, path) for method, path, _body in transport.calls]
        self.assertNotIn(
            (
                "POST",
                f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion",
            ),
            paths,
        )
        self.assertIn(
            (
                "DELETE",
                "/api/files/formalization-v2-bucket/inherited-formalization-v1.zip",
            ),
            paths,
        )
        publish_call = paths.index(
            ("POST", f"/api/deposit/depositions/{DRAFT_ID}/actions/publish")
        )
        download_calls = [
            index
            for index, call in enumerate(paths)
            if call
            == ("GET", "/api/files/formalization-v2-bucket/formalization-v2.tar.gz")
        ]
        self.assertLess(min(download_calls), publish_call)
        self.assertGreater(max(download_calls), publish_call)
        self.assertEqual(result["published_record_id"], DRAFT_ID)
        self.assertEqual(result["doi"], DRAFT_DOI)
        self.assertTrue(result["published_by_this_run"])
        self.assertTrue(result["public_record_verified"])
        names = [item["filename"] for item in transport.draft["files"]]
        self.assertEqual(names, [self.payload.name])

    def test_new_201_draft_is_initialized_and_response_id_is_ignored(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            action_status=201,
        )
        transport.draft["metadata"] = {
            "title": "Inherited predecessor metadata",
            "version": "1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "software",
            "prereserve_doi": {"doi": DRAFT_DOI},
        }
        result = self.invoke(transport)
        self.assertEqual(result["published_record_id"], DRAFT_ID)
        action_paths = [
            path
            for method, path, _body in transport.calls
            if method == "POST" and path.endswith("/actions/newversion")
        ]
        self.assertEqual(
            action_paths,
            [
                f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion"
            ],
        )
        self.assertFalse(any("99999999" in path for _m, path, _b in transport.calls))

    def test_newversion_200_and_202_responses_remain_fail_closed_and_publish(self) -> None:
        for action_status in (200, 202):
            with self.subTest(action_status=action_status):
                transport = FakeTransport(
                    self.metadata,
                    existing_draft=False,
                    action_status=action_status,
                )
                result = self.invoke(transport)
                self.assertEqual(result["published_record_id"], DRAFT_ID)
                self.assertTrue(result["published_by_this_run"])

    def test_published_source_self_link_creates_and_publishes_new_version(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            source_self_latest_draft=True,
            action_self_latest_draft=True,
            post_action_self_polls=1,
        )
        result = self.invoke(transport)
        action = (
            "POST",
            f"/api/deposit/depositions/{release.SOURCE_RECORD_ID}/actions/newversion",
        )
        paths = [(method, path) for method, path, _body in transport.calls]
        self.assertEqual(paths.count(action), 1)
        self.assertEqual(result["published_record_id"], DRAFT_ID)
        self.assertTrue(result["published_by_this_run"])

    def test_source_self_link_accepts_done_state_without_submitted_field(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            source_self_latest_draft=True,
            source_submitted=None,
            source_state="done",
        )
        result = self.invoke(transport)
        self.assertEqual(result["published_record_id"], DRAFT_ID)

    def test_source_self_link_without_published_state_fails_before_newversion(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            source_self_latest_draft=True,
            source_submitted=False,
            source_state="inprogress",
        )
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "self latest_draft is not a completed published"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method == "POST" and path.endswith("/actions/newversion")
                for method, path, _body in transport.calls
            )
        )

    def test_action_self_link_timeout_fails_before_draft_mutation(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            action_self_latest_draft=True,
            post_action_self_polls=99,
        )
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "new-version response has no source latest_draft"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_action_and_owner_draft_ids_must_match(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            action_draft_id=DRAFT_ID + 1,
        )
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "identify different drafts"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_completed_rerun_reconciles_exact_public_latest_without_mutation(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        first = self.invoke(transport)
        calls_after_first = len(transport.calls)
        second = self.invoke(transport)
        rerun_calls = transport.calls[calls_after_first:]
        self.assertTrue(first["published_by_this_run"])
        self.assertFalse(second["published_by_this_run"])
        self.assertEqual(second["published_record_id"], DRAFT_ID)
        self.assertFalse(
            any(method in {"POST", "PUT", "DELETE"} for method, _path, _body in rerun_calls)
        )

    def test_completed_rerun_blocks_if_public_latest_is_not_exact_manifest(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        self.invoke(transport)
        metadata = transport.draft["metadata"]
        assert isinstance(metadata, dict)
        metadata["version"] = "different-version"
        calls_after_first = len(transport.calls)
        with self.assertRaisesRegex(zenodo.ZenodoError, "final GET gate"):
            self.invoke(transport)
        rerun_calls = transport.calls[calls_after_first:]
        self.assertFalse(
            any(method in {"POST", "PUT", "DELETE"} for method, _path, _body in rerun_calls)
        )

    def test_completed_rerun_requires_doi_bound_to_latest_record_id(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        self.invoke(transport)
        transport.draft["doi"] = "10.5281/zenodo.99999999"
        calls_after_first = len(transport.calls)
        with self.assertRaisesRegex(zenodo.ZenodoError, "DOI is not bound"):
            self.invoke(transport)
        rerun_calls = transport.calls[calls_after_first:]
        self.assertFalse(
            any(method in {"POST", "PUT", "DELETE"} for method, _path, _body in rerun_calls)
        )

    def test_existing_unidentified_draft_fails_before_remote_mutation(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        transport.draft["metadata"] = {
            "title": "Some unrelated draft",
            "version": "9.9.9",
            "creators": [{"name": "Other, Person"}],
            "upload_type": "software",
            "prereserve_doi": {"doi": DRAFT_DOI},
        }
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "metadata does not match this exact release"
        ):
            self.invoke(transport)
        mutating = [
            (method, path)
            for method, path, _body in transport.calls
            if method in {"PUT", "DELETE"}
            or (method == "POST" and path.endswith("/actions/publish"))
        ]
        self.assertEqual(mutating, [])

    def test_409_unidentified_draft_is_never_repurposed(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            action_status=409,
        )
        transport.draft["metadata"] = {
            "title": "Unrelated already-open draft",
            "version": "3.0.0",
            "creators": [{"name": "Other, Person"}],
            "upload_type": "software",
            "prereserve_doi": {"doi": DRAFT_DOI},
        }
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "metadata does not match this exact release"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_matching_identity_with_different_description_is_not_resumed(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        metadata = copy.deepcopy(transport.draft["metadata"])
        assert isinstance(metadata, dict)
        metadata["description"] = "Unrelated concurrent release"
        transport.draft["metadata"] = metadata
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "metadata does not match this exact release"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_matching_target_with_unrelated_extra_metadata_is_not_resumed(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        metadata = copy.deepcopy(transport.draft["metadata"])
        assert isinstance(metadata, dict)
        metadata["communities"] = [{"identifier": "unrelated-release"}]
        transport.draft["metadata"] = metadata
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "metadata outside this exact release"
        ):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_409_exact_release_draft_is_resumed_and_gated(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=False,
            action_status=409,
        )
        result = self.invoke(transport)
        self.assertEqual(result["published_record_id"], DRAFT_ID)
        self.assertTrue(result["published_by_this_run"])
        self.assertTrue(
            any(
                method == "POST" and path.endswith("/actions/newversion")
                for method, path, _body in transport.calls
            )
        )
        self.assertTrue(
            any(
                method == "POST" and path.endswith("/actions/publish")
                for method, path, _body in transport.calls
            )
        )

    def test_local_hash_mismatch_blocks_before_any_transport_call(self) -> None:
        transport = FakeTransport(self.metadata, existing_draft=True)
        manifest = self.manifest()
        manifest["software"]["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(zenodo.ZenodoError, "SHA-256 mismatch"):
            release.publish_release(
                self.client(transport), manifest, self.root, "b" * 64
            )
        self.assertEqual(transport.calls, [])

    def test_wrong_draft_concept_blocks_before_edit_or_publish(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=True,
            draft_concept=999999,
        )
        with self.assertRaisesRegex(zenodo.ZenodoError, "changed formalization concept"):
            self.invoke(transport)
        self.assertFalse(
            any(
                method in {"PUT", "DELETE"}
                or (method == "POST" and path.endswith("/actions/publish"))
                for method, path, _body in transport.calls
            )
        )

    def test_download_hash_gate_blocks_publish(self) -> None:
        transport = FakeTransport(
            self.metadata,
            existing_draft=True,
            corrupt_download=True,
        )
        with self.assertRaisesRegex(zenodo.ZenodoError, "final GET gate"):
            self.invoke(transport)
        self.assertFalse(
            any(
                method == "POST" and path.endswith("/actions/publish")
                for method, path, _body in transport.calls
            )
        )

    def test_manifest_is_singular_and_rejects_unknown_effect_fields(self) -> None:
        manifest = self.manifest()
        manifest["second_software_release"] = copy.deepcopy(manifest["software"])
        with self.assertRaisesRegex(zenodo.ZenodoError, "invalid manifest keys"):
            release.validate_manifest(manifest, self.root)
        manifest = self.manifest()
        manifest["software"]["metadata"]["communities"] = [
            {"identifier": "external-community"}
        ]
        with self.assertRaisesRegex(
            zenodo.ZenodoError, "invalid software.metadata keys"
        ):
            release.validate_manifest(manifest, self.root)


if __name__ == "__main__":
    unittest.main()
