#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline fake-transport tests for the single-status-report Zenodo client."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import pathlib
import sys
import tempfile
import unittest
import urllib.parse

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_status_zenodo as status_zenodo  # noqa: E402
from tools import qikvrt_zenodo_actions as shared  # noqa: E402


TOKEN = "s" * 64
REPORT_RECORD_ID = 30000001
REPORT_CONCEPT_ID = 30000000
REPORT_DOI = f"10.5281/zenodo.{REPORT_RECORD_ID}"


def json_response(status: int, value: object) -> shared.HttpResponse:
    return shared.HttpResponse(
        status=status,
        headers={"Content-Type": "application/json"},
        body=json.dumps(value, sort_keys=True).encode("utf-8"),
    )


class FakeTransport:
    """Stateful legacy-API simulation; no call can reach the network."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes | None]] = []
        self.create_count = 0
        self.published = False
        self.corrupt_download = False
        self.deposition: dict[str, object] | None = None

    @staticmethod
    def _clean(value: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(value)
        result.pop("_data", None)
        for item in result.get("files", []):  # type: ignore[union-attr]
            item.pop("_data", None)
        return result

    @staticmethod
    def _public(value: dict[str, object]) -> dict[str, object]:
        result = FakeTransport._clean(value)
        metadata = result["metadata"]  # type: ignore[index]
        metadata.pop("prereserve_doi", None)
        upload_type = metadata.pop("upload_type")
        publication_type = metadata.pop("publication_type")
        metadata["resource_type"] = {
            "type": upload_type,
            "subtype": publication_type,
        }
        if isinstance(metadata.get("license"), str):
            metadata["license"] = {"id": metadata["license"]}
        public_files: list[dict[str, object]] = []
        for item in result["files"]:  # type: ignore[index]
            public_item = dict(item)
            public_item["key"] = public_item.pop("filename")
            public_item["size"] = public_item.pop("filesize")
            public_files.append(public_item)
        result["files"] = public_files
        return result

    @staticmethod
    def _file(name: str, data: bytes) -> dict[str, object]:
        return {
            "id": "file-" + name,
            "filename": name,
            "filesize": len(data),
            "checksum": "md5:" + hashlib.md5(data).hexdigest(),  # noqa: S324
            "_data": data,
            "links": {
                "self": f"https://zenodo.org/api/files/report-bucket/{name}",
                "download": f"https://zenodo.org/api/files/report-bucket/{name}",
            },
        }

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        content_type: str | None = None,
        max_response_bytes: int = shared.MAX_RESPONSE_BYTES,
    ) -> shared.HttpResponse:
        del content_type, max_response_bytes
        method = method.upper()
        path = urllib.parse.urlsplit(url).path
        self.calls.append((method, path, body))

        if method == "POST" and path == "/api/deposit/depositions":
            self.create_count += 1
            payload = json.loads((body or b"{}").decode("utf-8"))
            metadata = copy.deepcopy(payload["metadata"])
            metadata["prereserve_doi"] = {"doi": REPORT_DOI}
            self.deposition = {
                "id": REPORT_RECORD_ID,
                "conceptrecid": REPORT_CONCEPT_ID,
                "doi": REPORT_DOI,
                "metadata": metadata,
                "files": [],
                "links": {
                    "self": (
                        "https://zenodo.org/api/deposit/depositions/"
                        f"{REPORT_RECORD_ID}"
                    ),
                    "bucket": "https://zenodo.org/api/files/report-bucket",
                },
            }
            return json_response(201, self._clean(self.deposition))

        deposition_path = f"/api/deposit/depositions/{REPORT_RECORD_ID}"
        if path == deposition_path:
            if self.deposition is None or self.published:
                return json_response(404, {"message": "not editable"})
            if method == "GET":
                return json_response(200, self._clean(self.deposition))
            if method == "PUT":
                payload = json.loads((body or b"{}").decode("utf-8"))
                metadata = copy.deepcopy(payload["metadata"])
                metadata["prereserve_doi"] = {"doi": REPORT_DOI}
                self.deposition["metadata"] = metadata
                return json_response(200, self._clean(self.deposition))

        if (
            method == "POST"
            and path == deposition_path + "/actions/publish"
            and self.deposition is not None
        ):
            self.published = True
            return json_response(202, {"status": "queued"})

        if method == "GET" and path == f"/api/records/{REPORT_RECORD_ID}":
            if self.deposition is None or not self.published:
                return json_response(404, {"message": "not published"})
            return json_response(200, self._public(self.deposition))

        prefix = "/api/files/report-bucket/"
        if path.startswith(prefix) and self.deposition is not None:
            name = urllib.parse.unquote(path[len(prefix):])
            files = self.deposition["files"]  # type: ignore[index]
            existing = next(
                (item for item in files if item["filename"] == name), None
            )
            if method == "DELETE":
                if existing is not None:
                    files.remove(existing)
                return shared.HttpResponse(204, {}, b"")
            if method == "PUT":
                if existing is not None:
                    files.remove(existing)
                item = self._file(name, body or b"")
                files.append(item)
                return json_response(201, self._clean(item))
            if method == "GET" and existing is not None:
                data = existing["_data"]
                if self.corrupt_download and data:
                    data = bytes([data[0] ^ 1]) + data[1:]
                return shared.HttpResponse(
                    200, {"Content-Type": "application/octet-stream"}, data
                )

        return json_response(500, {"message": f"unhandled {method} {path}"})


class StatusZenodoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temporary.name)
        self.template_path = self.root / "CITATION.cff.doi-template"
        self.final_path = self.root / "CITATION.cff"
        template_data = (
            "title: QIK-VRT status report\n"
            f"doi: {status_zenodo.DOI_SENTINEL}\n"
        ).encode("utf-8")
        final_data = template_data.replace(
            status_zenodo.DOI_SENTINEL.encode("ascii"), REPORT_DOI.encode("ascii")
        )
        self.template_path.write_bytes(template_data)
        self.final_path.write_bytes(final_data)
        self.metadata: dict[str, object] = {
            "title": "QIK-VRT verified status report",
            "version": "1.0.0",
            "creators": [{"name": "Lohmann, Ingolf"}],
            "upload_type": "publication",
            "publication_type": "report",
            "prereserve_doi": True,
            "license": "cc-by-nc-4.0",
        }
        self.template_manifest_value: dict[str, object] = {
            "schema_version": 1,
            "report_id": "qikvrt-status-2026-07-22",
            "metadata": copy.deepcopy(self.metadata),
            "files": [self.entry(self.template_path, "CITATION.cff")],
        }
        self.template_raw = json.dumps(
            self.template_manifest_value, sort_keys=True
        ).encode("utf-8")
        self.template_sha256 = hashlib.sha256(self.template_raw).hexdigest()
        self.template_manifest = status_zenodo.validate_manifest(
            self.template_manifest_value, self.root
        )
        self.reservation_manifest_value: dict[str, object] = {
            "schema_version": 2,
            "report_id": "qikvrt-status-2026-07-22",
            "metadata": copy.deepcopy(self.metadata),
            "final_template_manifest_sha256": self.template_sha256,
            "doi_embedding": {
                "sentinel": status_zenodo.DOI_SENTINEL,
                "name": "CITATION.cff",
                "template_path": self.template_path.name,
                "final_path": self.final_path.name,
            },
        }
        self.reservation_manifest_raw = json.dumps(
            self.reservation_manifest_value, sort_keys=True
        ).encode("utf-8")
        self.reservation_manifest_sha256 = hashlib.sha256(
            self.reservation_manifest_raw
        ).hexdigest()
        self.reservation_manifest = status_zenodo.validate_reservation_manifest(
            self.reservation_manifest_value, self.root
        )
        self.final_manifest_value: dict[str, object] = {
            "schema_version": 1,
            "report_id": "qikvrt-status-2026-07-22",
            "metadata": copy.deepcopy(self.metadata),
            "files": [self.entry(self.final_path, "CITATION.cff")],
        }
        self.final_raw = json.dumps(
            self.final_manifest_value, sort_keys=True
        ).encode("utf-8")
        self.final_sha256 = hashlib.sha256(self.final_raw).hexdigest()
        self.final_manifest = status_zenodo.validate_manifest(
            self.final_manifest_value, self.root
        )
        self.reservation_path = self.root / "reservation.json"
        self.result_path = self.root / "result.json"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def client(transport: FakeTransport) -> status_zenodo.SingleReportClient:
        return status_zenodo.SingleReportClient(
            TOKEN,
            status_zenodo.DEFAULT_BASE_URL,
            transport,
            poll_attempts=2,
            poll_interval=0,
            sleeper=lambda _: None,
        )

    def entry(self, path: pathlib.Path, name: str) -> dict[str, object]:
        data = path.read_bytes()
        return {
            "path": path.relative_to(self.root).as_posix(),
            "name": name,
            "size": len(data),
            "md5": hashlib.md5(data).hexdigest(),  # noqa: S324
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def reserve_once(
        self, transport: FakeTransport
    ) -> dict[str, object]:
        return status_zenodo.reserve(
            self.client(transport),
            self.reservation_manifest,
            self.reservation_manifest_sha256,
            self.template_manifest,
            self.template_sha256,
            self.root,
            self.reservation_path,
        )

    def finalize_once(
        self, transport: FakeTransport, reservation: dict[str, object]
    ) -> dict[str, object]:
        return status_zenodo.finalize(
            self.client(transport),
            self.reservation_manifest,
            self.reservation_manifest_sha256,
            self.template_manifest,
            self.template_sha256,
            self.final_manifest,
            self.final_sha256,
            reservation,
            self.root,
            self.result_path,
        )

    def status_once(
        self, transport: FakeTransport, reservation: dict[str, object], path: pathlib.Path
    ) -> dict[str, object]:
        return status_zenodo.status(
            self.client(transport),
            self.reservation_manifest,
            self.reservation_manifest_sha256,
            self.template_manifest,
            self.template_sha256,
            self.final_manifest,
            self.final_sha256,
            reservation,
            self.root,
            path,
        )

    def test_manifest_is_exactly_one_new_report(self) -> None:
        invalid = copy.deepcopy(self.final_manifest_value)
        invalid["software"] = {}
        with self.assertRaises(status_zenodo.ZenodoError):
            status_zenodo.validate_manifest(invalid, self.root)
        invalid = copy.deepcopy(self.final_manifest_value)
        invalid["metadata"]["publication_type"] = "workingpaper"  # type: ignore[index]
        with self.assertRaises(status_zenodo.ZenodoError):
            status_zenodo.validate_manifest(invalid, self.root)

    def test_reserve_creates_once_and_rerun_has_no_network_calls(self) -> None:
        first_transport = FakeTransport()
        first = self.reserve_once(first_transport)
        self.assertEqual(first_transport.create_count, 1)
        self.assertEqual(
            [(method, path) for method, path, _ in first_transport.calls],
            [("POST", "/api/deposit/depositions")],
        )
        self.assertEqual(first["report"]["deposition_id"], REPORT_RECORD_ID)  # type: ignore[index]
        self.assertNotIn(TOKEN, self.reservation_path.read_text(encoding="utf-8"))

        second_transport = FakeTransport()
        second = self.reserve_once(second_transport)
        self.assertEqual(second, first)
        self.assertEqual(second_transport.calls, [])

    def test_reserve_requires_exactly_one_sentinel_before_network(self) -> None:
        self.template_path.write_text(
            f"doi: {status_zenodo.DOI_SENTINEL}\n"
            f"duplicate: {status_zenodo.DOI_SENTINEL}\n",
            encoding="utf-8",
        )
        template_value = copy.deepcopy(self.template_manifest_value)
        template_value["files"] = [self.entry(self.template_path, "CITATION.cff")]
        template_raw = json.dumps(template_value, sort_keys=True).encode("utf-8")
        template_sha256 = hashlib.sha256(template_raw).hexdigest()
        template = status_zenodo.validate_manifest(template_value, self.root)
        reservation_value = copy.deepcopy(self.reservation_manifest_value)
        reservation_value["final_template_manifest_sha256"] = template_sha256
        reservation_manifest = status_zenodo.validate_reservation_manifest(
            reservation_value, self.root
        )
        transport = FakeTransport()
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "exactly one sentinel"):
            status_zenodo.reserve(
                self.client(transport),
                reservation_manifest,
                hashlib.sha256(
                    json.dumps(reservation_value, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                template,
                template_sha256,
                self.root,
                self.reservation_path,
            )
        self.assertEqual(transport.calls, [])

    def test_signed_hash_bound_reservation_blocks_tamper_before_network(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        tampered = copy.deepcopy(reservation)
        tampered["report"]["deposition_id"] += 1  # type: ignore[index]
        transport.calls.clear()
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "MAC mismatch"):
            status_zenodo.finalize(
                self.client(transport),
                self.reservation_manifest,
                self.reservation_manifest_sha256,
                self.template_manifest,
                self.template_sha256,
                self.final_manifest,
                self.final_sha256,
                tampered,
                self.root,
                self.result_path,
            )
        self.assertEqual(transport.calls, [])

        with self.assertRaisesRegex(status_zenodo.ZenodoError, "manifest bytes changed"):
            status_zenodo.finalize(
                self.client(transport),
                self.reservation_manifest,
                hashlib.sha256(self.reservation_manifest_raw + b"\n").hexdigest(),
                self.template_manifest,
                self.template_sha256,
                self.final_manifest,
                self.final_sha256,
                reservation,
                self.root,
                self.result_path,
            )
        self.assertEqual(transport.calls, [])

    def test_newversion_and_all_protected_record_mutations_are_blocked(self) -> None:
        transport = FakeTransport()
        client = self.client(transport)
        forbidden = [
            ("POST", "/api/deposit/depositions/21498773/actions/newversion"),
            ("POST", "/api/deposit/depositions/21498774/actions/publish"),
            ("PUT", "/api/deposit/depositions/21498773"),
            ("DELETE", "/api/deposit/depositions/21498774/files/x"),
            ("PATCH", "/api/records/21498773"),
            ("PUT", "/api/deposit/depositions/21498772"),
            ("DELETE", "/api/records/21488115"),
        ]
        for method, path in forbidden:
            with self.subTest(method=method, path=path), self.assertRaises(
                status_zenodo.ZenodoError
            ):
                client.request(method, path)
        self.assertEqual(transport.calls, [])

    def test_one_client_cannot_create_a_second_report(self) -> None:
        transport = FakeTransport()
        client = self.client(transport)
        client.create_report(self.reservation_manifest["metadata"])
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "exactly one"):
            client.create_report(self.reservation_manifest["metadata"])
        self.assertEqual(transport.create_count, 1)

    def test_finalize_exactly_gates_and_publishes(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        outcome = self.finalize_once(transport, reservation)
        self.assertEqual(outcome["phase"], "published")
        self.assertEqual(outcome["record_id"], REPORT_RECORD_ID)
        self.assertTrue(transport.published)
        self.assertTrue(any(
            method == "POST" and path.endswith("/actions/publish")
            for method, path, _ in transport.calls
        ))
        unsigned = dict(outcome)
        supplied_mac = unsigned.pop("authorization_mac")
        expected_mac = hmac.new(
            TOKEN.encode("utf-8"),
            shared._json_bytes(unsigned),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(supplied_mac, expected_mac)
        self.assertNotIn(TOKEN, self.result_path.read_text(encoding="utf-8"))

    def test_downloaded_sha256_mismatch_blocks_publish(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        transport.corrupt_download = True
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "hash|mismatch"):
            self.finalize_once(transport, reservation)
        self.assertFalse(transport.published)

    def test_finalize_rejects_every_delta_beyond_exact_reserved_doi(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        transport.calls.clear()
        self.final_path.write_bytes(
            self.final_path.read_bytes() + b"unauthorized extra byte\n"
        )
        changed_value = copy.deepcopy(self.final_manifest_value)
        changed_value["files"] = [self.entry(self.final_path, "CITATION.cff")]
        changed_raw = json.dumps(changed_value, sort_keys=True).encode("utf-8")
        changed_manifest = status_zenodo.validate_manifest(changed_value, self.root)
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "exact reserved substitution"):
            status_zenodo.finalize(
                self.client(transport),
                self.reservation_manifest,
                self.reservation_manifest_sha256,
                self.template_manifest,
                self.template_sha256,
                changed_manifest,
                hashlib.sha256(changed_raw).hexdigest(),
                reservation,
                self.root,
                self.result_path,
            )
        self.assertEqual(transport.calls, [])

    def test_finalize_rejects_metadata_delta_before_network(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        transport.calls.clear()
        changed_value = copy.deepcopy(self.final_manifest_value)
        changed_value["metadata"]["title"] = "unreserved title"  # type: ignore[index]
        changed_raw = json.dumps(changed_value, sort_keys=True).encode("utf-8")
        changed_manifest = status_zenodo.validate_manifest(changed_value, self.root)
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "final metadata differs"):
            status_zenodo.finalize(
                self.client(transport),
                self.reservation_manifest,
                self.reservation_manifest_sha256,
                self.template_manifest,
                self.template_sha256,
                changed_manifest,
                hashlib.sha256(changed_raw).hexdigest(),
                reservation,
                self.root,
                self.result_path,
            )
        self.assertEqual(transport.calls, [])

    def test_finalize_rejects_a_non_reserved_doi_before_network(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        transport.calls.clear()
        self.final_path.write_bytes(
            self.template_path.read_bytes().replace(
                status_zenodo.DOI_SENTINEL.encode("ascii"),
                b"10.5281/zenodo.39999999",
            )
        )
        changed_value = copy.deepcopy(self.final_manifest_value)
        changed_value["files"] = [self.entry(self.final_path, "CITATION.cff")]
        changed_raw = json.dumps(changed_value, sort_keys=True).encode("utf-8")
        changed_manifest = status_zenodo.validate_manifest(changed_value, self.root)
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "reserved substitution"):
            status_zenodo.finalize(
                self.client(transport),
                self.reservation_manifest,
                self.reservation_manifest_sha256,
                self.template_manifest,
                self.template_sha256,
                changed_manifest,
                hashlib.sha256(changed_raw).hexdigest(),
                reservation,
                self.root,
                self.result_path,
            )
        self.assertEqual(transport.calls, [])

    def test_finalize_resumes_published_report_without_mutation(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        self.finalize_once(transport, reservation)
        transport.calls.clear()
        outcome = self.finalize_once(transport, reservation)
        self.assertEqual(outcome["phase"], "published")
        self.assertTrue(transport.calls)
        self.assertTrue(all(method == "GET" for method, _, _ in transport.calls))

    def test_status_is_read_only_and_enforces_exact_metadata(self) -> None:
        transport = FakeTransport()
        reservation = self.reserve_once(transport)
        self.finalize_once(transport, reservation)
        transport.calls.clear()
        outcome = self.status_once(transport, reservation, self.root / "status.json")
        self.assertEqual(outcome["phase"], "published")
        self.assertTrue(all(method == "GET" for method, _, _ in transport.calls))

        transport.deposition["metadata"]["title"] = "tampered"  # type: ignore[index]
        with self.assertRaisesRegex(status_zenodo.ZenodoError, "metadata"):
            self.status_once(
                transport, reservation, self.root / "status-tampered.json"
            )

    def test_cli_has_no_token_argument_and_redaction_is_inherited(self) -> None:
        with self.assertRaises(SystemExit):
            status_zenodo.build_parser().parse_args(
                [
                    "reserve",
                    "--manifest",
                    "m",
                    "--final-template-manifest",
                    "t",
                    "--reservation",
                    "r",
                    "--token",
                    TOKEN,
                ]
            )
        self.assertNotIn(
            TOKEN,
            shared.redact(f"Authorization: Bearer {TOKEN}", TOKEN),
        )
        self.assertIsNone(
            shared.NoRedirectHandler().redirect_request(
                object(), None, 302, "Found", {}, "https://evil.example/steal"
            )
        )


if __name__ == "__main__":
    unittest.main()
