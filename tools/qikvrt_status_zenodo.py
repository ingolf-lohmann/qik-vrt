#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed Zenodo client for exactly one new QIK-VRT status report.

This client intentionally does not implement Zenodo's ``newversion`` action.
It creates one fresh, empty report deposition and persists a token-authenticated
reservation bound to an exact DOI-template manifest.  Finalization accepts a
separate manifest only after proving that its bytes differ from the template
solely by one byte-exact replacement of ``10.5281/zenodo.__RESERVED__`` with the
server-reserved DOI in the explicitly authorized file.  The two already-
published EFFECT_ACK records are read-only safety anchors and can never be
mutation targets through this client.

The access token is accepted only through ``ZENODO_ACCESS_TOKEN``.  Network
transport, URL allowlisting, redirect refusal, bounded reads, safe diagnostics,
and file reads are shared with :mod:`qikvrt_zenodo_actions`.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import re
import sys
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import Any

if __package__:
    from . import qikvrt_zenodo_actions as shared
else:  # pragma: no cover - exercised by CLI invocation rather than import tests
    import qikvrt_zenodo_actions as shared


DEFAULT_BASE_URL = shared.DEFAULT_BASE_URL
TOKEN_ENVIRONMENT_VARIABLE = shared.TOKEN_ENVIRONMENT_VARIABLE
PROTECTED_RECORD_IDS = frozenset({21498773, 21498774})
PROTECTED_CONCEPT_IDS = frozenset({21498772, 21488115})
PROTECTED_ZENODO_IDS = PROTECTED_RECORD_IDS | PROTECTED_CONCEPT_IDS
RESERVATION_KIND = "qikvrt-single-status-report"
SAFE_REPORT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ZENODO_DOI = re.compile(r"^10\.5281/zenodo\.([1-9][0-9]*)$")
DOI_SENTINEL = "10.5281/zenodo.__RESERVED__"

ZenodoError = shared.ZenodoError


def _manifest_hashes(manifest: Mapping[str, Any]) -> tuple[str, str]:
    metadata_sha256 = hashlib.sha256(
        shared._json_bytes(manifest["metadata"])
    ).hexdigest()
    files_sha256 = hashlib.sha256(
        shared._json_bytes(manifest["files"])
    ).hexdigest()
    return metadata_sha256, files_sha256


def _validate_metadata(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not shared._is_json_value(value):
        raise ZenodoError(f"{where} must be a JSON object")
    shared._metadata_identity(value, "status-report")
    if value.get("upload_type") != "publication":
        raise ZenodoError("status-report metadata.upload_type must equal publication")
    if value.get("publication_type") != "report":
        raise ZenodoError("status-report metadata.publication_type must equal report")
    if value.get("prereserve_doi") is not True:
        raise ZenodoError("status-report metadata.prereserve_doi must equal true")
    if "doi" in value:
        raise ZenodoError("status-report DOI must be assigned by Zenodo")
    if DOI_SENTINEL in json.dumps(value, ensure_ascii=False):
        raise ZenodoError("the DOI sentinel is allowed only in the approved template file")
    return value


def validate_manifest(value: dict[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """Validate an exact template or final file manifest for the report."""
    shared._check_exact_keys(
        value,
        {"schema_version", "report_id", "metadata", "files"},
        "status-report manifest",
    )
    if value["schema_version"] != 1:
        raise ZenodoError("status-report manifest.schema_version must equal 1")
    report_id = value["report_id"]
    if not isinstance(report_id, str) or not SAFE_REPORT_ID.fullmatch(report_id):
        raise ZenodoError("status-report manifest.report_id is unsafe")

    metadata = _validate_metadata(value["metadata"], "status-report metadata")

    raw_files = value["files"]
    if not isinstance(raw_files, list) or not (1 <= len(raw_files) <= 100):
        raise ZenodoError("status-report files must contain between 1 and 100 files")
    files = [
        shared._validate_file_entry(item, root, f"files[{index}]")
        for index, item in enumerate(raw_files)
    ]
    if len({entry["name"] for entry in files}) != len(files):
        raise ZenodoError("status-report files contain duplicate upload names")
    if len({entry["path"] for entry in files}) != len(files):
        raise ZenodoError("status-report files contain duplicate repository paths")
    return {
        "schema_version": 1,
        "report_id": report_id,
        "metadata": metadata,
        "files": files,
    }


def validate_reservation_manifest(
    value: dict[str, Any], root: pathlib.Path
) -> dict[str, Any]:
    """Validate the immutable pre-DOI authorization for one empty draft."""
    shared._check_exact_keys(
        value,
        {
            "schema_version",
            "report_id",
            "metadata",
            "final_template_manifest_sha256",
            "doi_embedding",
        },
        "status-report reservation manifest",
    )
    if value["schema_version"] != 2:
        raise ZenodoError("status-report reservation manifest.schema_version must equal 2")
    report_id = value["report_id"]
    if not isinstance(report_id, str) or not SAFE_REPORT_ID.fullmatch(report_id):
        raise ZenodoError("status-report reservation manifest.report_id is unsafe")
    metadata = _validate_metadata(value["metadata"], "reservation metadata")
    template_sha256 = value["final_template_manifest_sha256"]
    if not isinstance(template_sha256, str) or not shared.HEX_64.fullmatch(
        template_sha256
    ):
        raise ZenodoError("final template manifest SHA-256 is invalid")
    embedding = value["doi_embedding"]
    if not isinstance(embedding, dict):
        raise ZenodoError("doi_embedding must be an object")
    shared._check_exact_keys(
        embedding,
        {"sentinel", "name", "template_path", "final_path"},
        "doi_embedding",
    )
    if embedding["sentinel"] != DOI_SENTINEL:
        raise ZenodoError("doi_embedding.sentinel is not the fixed DOI sentinel")
    name = embedding["name"]
    if (
        not isinstance(name, str)
        or not name
        or pathlib.PurePosixPath(name).name != name
        or any(ord(character) < 32 for character in name)
    ):
        raise ZenodoError("doi_embedding.name must be a safe upload basename")
    template_path = embedding["template_path"]
    final_path = embedding["final_path"]
    shared._relative_path(root, template_path, must_exist=True)
    shared._relative_path(root, final_path, must_exist=False)
    if template_path == final_path:
        raise ZenodoError("DOI template and final paths must be distinct")
    return {
        "schema_version": 2,
        "report_id": report_id,
        "metadata": metadata,
        "final_template_manifest_sha256": template_sha256,
        "doi_embedding": {
            "sentinel": DOI_SENTINEL,
            "name": name,
            "template_path": template_path,
            "final_path": final_path,
        },
    }


def verify_report_files(
    manifest: Mapping[str, Any], root: pathlib.Path, token: str
) -> dict[tuple[str, str], bytes]:
    """Read and hash every report file before any remote side effect."""
    verified: dict[tuple[str, str], bytes] = {}
    for entry in manifest["files"]:
        verified[("report", entry["name"])] = shared._file_bytes(
            root, entry, token
        )
    return verified


def _files_by_name(manifest: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {entry["name"]: entry for entry in manifest["files"]}


def validate_template_binding(
    reservation_manifest: Mapping[str, Any],
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    root: pathlib.Path,
    token: str,
) -> dict[tuple[str, str], bytes]:
    """Bind the reserve phase to one exact template and one sentinel byte run."""
    if (
        reservation_manifest["final_template_manifest_sha256"]
        != template_manifest_sha256
    ):
        raise ZenodoError("DOI template manifest bytes do not match the reserved hash")
    if template_manifest["report_id"] != reservation_manifest["report_id"]:
        raise ZenodoError("DOI template manifest identifies another report")
    if template_manifest["metadata"] != reservation_manifest["metadata"]:
        raise ZenodoError("DOI template metadata differs from reservation metadata")
    embedding = reservation_manifest["doi_embedding"]
    files = _files_by_name(template_manifest)
    entry = files.get(embedding["name"])
    if entry is None or entry["path"] != embedding["template_path"]:
        raise ZenodoError("approved DOI template file is absent or has another path")
    verified = verify_report_files(template_manifest, root, token)
    sentinel = DOI_SENTINEL.encode("ascii")
    occurrences = sum(data.count(sentinel) for data in verified.values())
    if occurrences != 1:
        raise ZenodoError("DOI template files must contain exactly one sentinel occurrence")
    if verified[("report", embedding["name"])].count(sentinel) != 1:
        raise ZenodoError("the DOI sentinel is outside the approved template file")
    return verified


def validate_final_transition(
    reservation_manifest: Mapping[str, Any],
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    final_manifest: Mapping[str, Any],
    reserved_doi: str,
    root: pathlib.Path,
    token: str,
) -> dict[tuple[str, str], bytes]:
    """Allow no delta except the one authorized sentinel-to-DOI substitution."""
    template_bytes = validate_template_binding(
        reservation_manifest,
        template_manifest,
        template_manifest_sha256,
        root,
        token,
    )
    if final_manifest["report_id"] != reservation_manifest["report_id"]:
        raise ZenodoError("final manifest identifies another report")
    if final_manifest["metadata"] != reservation_manifest["metadata"]:
        raise ZenodoError("final metadata differs from the reserved metadata")
    template_names = [entry["name"] for entry in template_manifest["files"]]
    final_names = [entry["name"] for entry in final_manifest["files"]]
    if final_names != template_names:
        raise ZenodoError("final file identity/order differs from the DOI template")
    final_bytes = verify_report_files(final_manifest, root, token)
    template_entries = _files_by_name(template_manifest)
    final_entries = _files_by_name(final_manifest)
    embedding = reservation_manifest["doi_embedding"]
    sentinel = DOI_SENTINEL.encode("ascii")
    doi_bytes = reserved_doi.encode("ascii")
    for name in template_names:
        template_entry = template_entries[name]
        final_entry = final_entries[name]
        before = template_bytes[("report", name)]
        after = final_bytes[("report", name)]
        if name == embedding["name"]:
            if template_entry["path"] != embedding["template_path"]:
                raise ZenodoError("approved DOI template path changed")
            if final_entry["path"] != embedding["final_path"]:
                raise ZenodoError("final DOI-bearing file path is not authorized")
            if after != before.replace(sentinel, doi_bytes):
                raise ZenodoError("final DOI-bearing bytes are not the exact reserved substitution")
        else:
            if final_entry != template_entry or after != before:
                raise ZenodoError("a non-DOI report file changed after reservation")
    if any(sentinel in data for data in final_bytes.values()):
        raise ZenodoError("final report files still contain the DOI sentinel")
    return final_bytes


def _zenodo_doi_record_id(doi: str, where: str) -> int:
    match = ZENODO_DOI.fullmatch(doi)
    if not match:
        raise ZenodoError(f"{where} is not a version-specific Zenodo DOI")
    return int(match.group(1))


def _assert_unprotected_record(record_id: int) -> None:
    if record_id in PROTECTED_ZENODO_IDS:
        raise ZenodoError(
            f"Zenodo ID {record_id} is an immutable pre-existing release anchor"
        )


class SingleReportClient(shared.ZenodoClient):
    """Zenodo client whose mutation surface is one newly-created deposition."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._allow_create = False
        self._creation_attempted = False
        self._authorized_report_id: int | None = None
        self._authorized_bucket_path: str | None = None

    @staticmethod
    def _record_ids_in_path(path: str) -> set[int]:
        return {
            int(match.group(1))
            for match in re.finditer(
                r"/api/(?:records|deposit/depositions)/([1-9][0-9]*)(?:/|$)",
                path,
            )
        }

    def _mutation_is_authorized(self, method: str, path: str) -> bool:
        if method == "POST" and path.rstrip("/") == "/api/deposit/depositions":
            return self._allow_create
        report_id = self._authorized_report_id
        if report_id is None:
            return False
        deposition = f"/api/deposit/depositions/{report_id}"
        if method == "PUT" and path.rstrip("/") == deposition:
            return True
        if method == "POST" and path.rstrip("/") == deposition + "/actions/publish":
            return True
        if method == "DELETE" and path.startswith(deposition + "/files/"):
            return True
        bucket = self._authorized_bucket_path
        if bucket and path.startswith(bucket + "/"):
            return method in {"PUT", "DELETE"}
        return False

    def request(
        self,
        method: str,
        url: str,
        *,
        payload: Any | None = None,
        data: bytes | None = None,
        content_type: str | None = None,
        accept: Sequence[int] = (200,),
        parse_json: bool = True,
        max_response_bytes: int = shared.MAX_RESPONSE_BYTES,
    ) -> tuple[shared.HttpResponse, dict[str, Any]]:
        safe_url = shared.validate_response_url(url, self.base_url)
        path = urllib.parse.urlsplit(safe_url).path
        method = method.upper()
        if re.search(r"/actions/newversion(?:/|$)", path):
            raise ZenodoError("Zenodo newversion is forbidden for a single report")
        if method != "GET" and self._record_ids_in_path(path) & PROTECTED_ZENODO_IDS:
            raise ZenodoError("mutation of an immutable pre-existing record is forbidden")
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise ZenodoError("HTTP method is outside the single-report policy")
        if method != "GET" and not self._mutation_is_authorized(method, path):
            raise ZenodoError("mutation is outside the authorized single-report deposition")
        return super().request(
            method,
            safe_url,
            payload=payload,
            data=data,
            content_type=content_type,
            accept=accept,
            parse_json=parse_json,
            max_response_bytes=max_response_bytes,
        )

    def authorize_draft(
        self,
        value: Mapping[str, Any],
        *,
        record_id: int,
        concept_record_id: int,
        doi: str,
    ) -> None:
        """Bind all later mutations to the signed reservation's draft."""
        _assert_unprotected_record(record_id)
        _assert_unprotected_record(concept_record_id)
        if shared._record_id(value, "status-report draft") != record_id:
            raise ZenodoError("status-report draft ID changed")
        if shared._concept_id(value, "status-report draft") != concept_record_id:
            raise ZenodoError("status-report concept record ID changed")
        actual_doi = shared._doi_from_deposition(value, "status-report draft")
        if actual_doi != doi or _zenodo_doi_record_id(actual_doi, "report DOI") != record_id:
            raise ZenodoError("status-report DOI and draft ID disagree")
        links = value.get("links")
        if not isinstance(links, dict):
            raise ZenodoError("status-report draft has no links object")
        self_link = links.get("self")
        bucket_link = links.get("bucket")
        if not isinstance(self_link, str) or not isinstance(bucket_link, str):
            raise ZenodoError("status-report draft has no safe self/bucket links")
        self_path = urllib.parse.urlsplit(
            shared.validate_response_url(self_link, self.base_url)
        ).path.rstrip("/")
        if self_path != f"/api/deposit/depositions/{record_id}":
            raise ZenodoError("status-report self link identifies another deposition")
        bucket_path = urllib.parse.urlsplit(
            shared.validate_response_url(bucket_link, self.base_url)
        ).path.rstrip("/")
        if not bucket_path.startswith("/api/files/"):
            raise ZenodoError("status-report bucket is outside the Zenodo file API")
        if self._authorized_report_id not in (None, record_id):
            raise ZenodoError("client is already bound to another report")
        if self._authorized_bucket_path not in (None, bucket_path):
            raise ZenodoError("status-report upload bucket changed")
        self._authorized_report_id = record_id
        self._authorized_bucket_path = bucket_path

    def create_report(self, metadata: Mapping[str, Any]) -> dict[str, Any]:
        if self._creation_attempted:
            raise ZenodoError("this client may create exactly one report")
        self._creation_attempted = True
        self._allow_create = True
        try:
            report = super().create_paper(metadata)
        finally:
            self._allow_create = False
        record_id = shared._record_id(report, "status-report deposition")
        concept_record_id = shared._concept_id(report, "status-report deposition")
        doi = shared._doi_from_deposition(report, "status-report deposition")
        self.authorize_draft(
            report,
            record_id=record_id,
            concept_record_id=concept_record_id,
            doi=doi,
        )
        return report

    def prepare_report(
        self,
        reservation: Mapping[str, Any],
        manifest: Mapping[str, Any],
        verified: Mapping[tuple[str, str], bytes],
    ) -> str:
        report = reservation["report"]
        record_id = report["deposition_id"]
        state, current = self.get_deposition_or_record(record_id)
        if state == "published":
            self.wait_for_gated_record(
                record_id,
                manifest["metadata"],
                manifest["files"],
                report["doi"],
                published=True,
                initial=current,
            )
            return "published"
        self.authorize_draft(
            current,
            record_id=record_id,
            concept_record_id=report["concept_record_id"],
            doi=report["doi"],
        )
        self.request(
            "PUT",
            f"/api/deposit/depositions/{record_id}",
            payload={"metadata": manifest["metadata"]},
            accept=(200, 202),
        )
        updated = self.wait_for_editable_metadata(record_id, manifest["metadata"])
        self.authorize_draft(
            updated,
            record_id=record_id,
            concept_record_id=report["concept_record_id"],
            doi=report["doi"],
        )
        self.delete_all_files(record_id, updated)
        self.upload_files(updated, manifest["files"], verified, "report")
        self.wait_for_gated_record(
            record_id,
            manifest["metadata"],
            manifest["files"],
            report["doi"],
            published=False,
        )
        return "draft"


def _sign_reservation(value: Mapping[str, Any], token: str) -> dict[str, Any]:
    signed = dict(value)
    signed.pop("authorization_mac", None)
    signed["authorization_mac"] = hmac.new(
        token.encode("utf-8"), shared._json_bytes(signed), hashlib.sha256
    ).hexdigest()
    return signed


def _validate_reservation(
    value: Mapping[str, Any],
    reservation_manifest: Mapping[str, Any],
    reservation_manifest_sha256: str,
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    root: pathlib.Path,
    client: SingleReportClient,
) -> None:
    shared._check_exact_keys(
        value,
        {
            "schema_version",
            "kind",
            "phase",
            "api_base_url",
            "report_id",
            "reservation_manifest_sha256",
            "template_manifest_sha256",
            "metadata_sha256",
            "template_files_sha256",
            "doi_embedding",
            "report",
            "authorization_mac",
        },
        "status-report reservation",
    )
    if value["schema_version"] != 2 or value["kind"] != RESERVATION_KIND:
        raise ZenodoError("status-report reservation schema/kind is unsupported")
    if value["phase"] != "reserved":
        raise ZenodoError("status-report reservation is not complete")
    if value["api_base_url"] != client.base_url:
        raise ZenodoError("status-report reservation belongs to another Zenodo API")
    if value["report_id"] != reservation_manifest["report_id"]:
        raise ZenodoError("status-report reservation identifies another report")
    if value["reservation_manifest_sha256"] != reservation_manifest_sha256:
        raise ZenodoError("reservation manifest bytes changed after reservation")
    if value["template_manifest_sha256"] != template_manifest_sha256:
        raise ZenodoError("DOI template manifest bytes changed after reservation")
    metadata_sha256, template_files_sha256 = _manifest_hashes(template_manifest)
    if value["metadata_sha256"] != metadata_sha256:
        raise ZenodoError("status-report metadata hash changed after reservation")
    if value["template_files_sha256"] != template_files_sha256:
        raise ZenodoError("DOI template file manifest hash changed after reservation")
    if value["doi_embedding"] != reservation_manifest["doi_embedding"]:
        raise ZenodoError("reserved DOI embedding authorization changed")

    supplied_mac = value.get("authorization_mac")
    if not isinstance(supplied_mac, str) or not shared.HEX_64.fullmatch(supplied_mac):
        raise ZenodoError("status-report reservation has no valid authorization MAC")
    unsigned = dict(value)
    unsigned.pop("authorization_mac", None)
    expected_mac = hmac.new(
        client.token.encode("utf-8"), shared._json_bytes(unsigned), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(supplied_mac, expected_mac):
        raise ZenodoError("status-report reservation authorization MAC mismatch")

    validate_template_binding(
        reservation_manifest,
        template_manifest,
        template_manifest_sha256,
        root,
        client.token,
    )

    report = value["report"]
    if not isinstance(report, dict):
        raise ZenodoError("status-report reservation report entry is invalid")
    shared._check_exact_keys(
        report, {"deposition_id", "concept_record_id", "doi"}, "reserved report"
    )
    record_id = shared._safe_int(report["deposition_id"], "reserved report ID")
    concept_record_id = shared._safe_int(
        report["concept_record_id"], "reserved concept record ID"
    )
    _assert_unprotected_record(record_id)
    _assert_unprotected_record(concept_record_id)
    doi = report["doi"]
    if not isinstance(doi, str) or _zenodo_doi_record_id(doi, "reserved DOI") != record_id:
        raise ZenodoError("reserved report DOI and deposition ID disagree")


def reserve(
    client: SingleReportClient,
    reservation_manifest: Mapping[str, Any],
    reservation_manifest_sha256: str,
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    root: pathlib.Path,
    reservation_path: pathlib.Path,
) -> dict[str, Any]:
    """Reserve one fresh report, or safely resume its existing reservation."""
    validate_template_binding(
        reservation_manifest,
        template_manifest,
        template_manifest_sha256,
        root,
        client.token,
    )
    if reservation_path.exists():
        existing, _ = shared._load_json_file(reservation_path, client.token)
        _validate_reservation(
            existing,
            reservation_manifest,
            reservation_manifest_sha256,
            template_manifest,
            template_manifest_sha256,
            root,
            client,
        )
        return existing

    created = client.create_report(reservation_manifest["metadata"])
    expected_metadata = dict(reservation_manifest["metadata"])
    expected_metadata.pop("prereserve_doi", None)
    if not shared._metadata_matches(created.get("metadata"), expected_metadata):
        raise ZenodoError("new status-report metadata differs from the manifest")
    if created.get("files") != []:
        raise ZenodoError("new status-report deposition is not an empty standalone draft")
    record_id = shared._record_id(created, "status-report deposition")
    concept_record_id = shared._concept_id(created, "status-report deposition")
    doi = shared._doi_from_deposition(created, "status-report deposition")
    metadata_sha256, template_files_sha256 = _manifest_hashes(template_manifest)
    reservation = _sign_reservation(
        {
            "schema_version": 2,
            "kind": RESERVATION_KIND,
            "phase": "reserved",
            "api_base_url": client.base_url,
            "report_id": reservation_manifest["report_id"],
            "reservation_manifest_sha256": reservation_manifest_sha256,
            "template_manifest_sha256": template_manifest_sha256,
            "metadata_sha256": metadata_sha256,
            "template_files_sha256": template_files_sha256,
            "doi_embedding": reservation_manifest["doi_embedding"],
            "report": {
                "deposition_id": record_id,
                "concept_record_id": concept_record_id,
                "doi": doi,
            },
        },
        client.token,
    )
    shared._atomic_json(reservation_path, reservation, client.token)
    return reservation


def _outcome(
    reservation_manifest: Mapping[str, Any],
    reservation_manifest_sha256: str,
    template_manifest_sha256: str,
    final_manifest: Mapping[str, Any],
    final_manifest_sha256: str,
    reservation: Mapping[str, Any],
    record: Mapping[str, Any],
    phase: str,
    token: str,
) -> dict[str, Any]:
    report = reservation["report"]
    record_id = shared._record_id(record, "observed status report")
    concept_record_id = shared._concept_id(record, "observed status report")
    doi = shared._doi_from_deposition(record, "observed status report")
    if (
        record_id != report["deposition_id"]
        or concept_record_id != report["concept_record_id"]
        or doi != report["doi"]
    ):
        raise ZenodoError("observed status-report identity changed")
    metadata_sha256, files_sha256 = _manifest_hashes(final_manifest)
    return _sign_reservation(
        {
            "schema_version": 2,
            "kind": RESERVATION_KIND,
            "phase": phase,
            "report_id": reservation_manifest["report_id"],
            "reservation_manifest_sha256": reservation_manifest_sha256,
            "template_manifest_sha256": template_manifest_sha256,
            "final_manifest_sha256": final_manifest_sha256,
            "metadata_sha256": metadata_sha256,
            "files_sha256": files_sha256,
            "record_id": record_id,
            "concept_record_id": concept_record_id,
            "doi": doi,
        },
        token,
    )


def finalize(
    client: SingleReportClient,
    reservation_manifest: Mapping[str, Any],
    reservation_manifest_sha256: str,
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    final_manifest: Mapping[str, Any],
    final_manifest_sha256: str,
    reservation: Mapping[str, Any],
    root: pathlib.Path,
    result_path: pathlib.Path,
) -> dict[str, Any]:
    """Reconcile, exactly gate, and publish the one reserved report."""
    _validate_reservation(
        reservation,
        reservation_manifest,
        reservation_manifest_sha256,
        template_manifest,
        template_manifest_sha256,
        root,
        client,
    )
    verified = validate_final_transition(
        reservation_manifest,
        template_manifest,
        template_manifest_sha256,
        final_manifest,
        reservation["report"]["doi"],
        root,
        client.token,
    )
    preparation = client.prepare_report(reservation, final_manifest, verified)
    report = reservation["report"]
    published = client.publish_and_poll(
        report["deposition_id"],
        final_manifest["metadata"],
        final_manifest["files"],
        report["doi"],
        preparation == "published",
    )
    outcome = _outcome(
        reservation_manifest,
        reservation_manifest_sha256,
        template_manifest_sha256,
        final_manifest,
        final_manifest_sha256,
        reservation,
        published,
        "published",
        client.token,
    )
    shared._atomic_json(result_path, outcome, client.token)
    return outcome


def status(
    client: SingleReportClient,
    reservation_manifest: Mapping[str, Any],
    reservation_manifest_sha256: str,
    template_manifest: Mapping[str, Any],
    template_manifest_sha256: str,
    final_manifest: Mapping[str, Any],
    final_manifest_sha256: str,
    reservation: Mapping[str, Any],
    root: pathlib.Path,
    result_path: pathlib.Path,
) -> dict[str, Any]:
    """Read and exactly gate the reserved report without any remote mutation."""
    _validate_reservation(
        reservation,
        reservation_manifest,
        reservation_manifest_sha256,
        template_manifest,
        template_manifest_sha256,
        root,
        client,
    )
    validate_final_transition(
        reservation_manifest,
        template_manifest,
        template_manifest_sha256,
        final_manifest,
        reservation["report"]["doi"],
        root,
        client.token,
    )
    report = reservation["report"]
    state, current = client.get_deposition_or_record(report["deposition_id"])
    if state == "draft":
        client.authorize_draft(
            current,
            record_id=report["deposition_id"],
            concept_record_id=report["concept_record_id"],
            doi=report["doi"],
        )
    gated = client.wait_for_gated_record(
        report["deposition_id"],
        final_manifest["metadata"],
        final_manifest["files"],
        report["doi"],
        published=state == "published",
        initial=current,
    )
    outcome = _outcome(
        reservation_manifest,
        reservation_manifest_sha256,
        template_manifest_sha256,
        final_manifest,
        final_manifest_sha256,
        reservation,
        gated,
        "published" if state == "published" else "draft",
        client.token,
    )
    shared._atomic_json(result_path, outcome, client.token)
    return outcome


def build_parser() -> argparse.ArgumentParser:
    parser = shared.SafeArgumentParser(
        description="Reserve, finalize, or inspect one new QIK-VRT status report."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=shared.SafeArgumentParser
    )
    reserve_parser = subparsers.add_parser("reserve")
    reserve_parser.add_argument(
        "--reservation-manifest", "--manifest", dest="manifest", required=True
    )
    reserve_parser.add_argument("--final-template-manifest", required=True)
    reserve_parser.add_argument(
        "--reservation", "--result", dest="reservation", required=True
    )
    for name in ("finalize", "status"):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--reservation-manifest", "--manifest", dest="manifest", required=True
        )
        command.add_argument("--final-template-manifest", required=True)
        command.add_argument("--final-manifest", required=True)
        command.add_argument("--reservation", required=True)
        command.add_argument("--result", required=True)
    for command in subparsers.choices.values():
        command.add_argument("--base-url", default=DEFAULT_BASE_URL, help=argparse.SUPPRESS)
        command.add_argument("--repository-root", default=".")
        command.add_argument("--poll-attempts", type=int, default=30)
        command.add_argument("--poll-interval", type=float, default=2.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "")
    try:
        args = build_parser().parse_args(argv)
        root = pathlib.Path(args.repository_root).resolve(strict=True)
        if not root.is_dir():
            raise ZenodoError("repository-root must identify a directory")
        manifest_path = shared._external_path_in_root(root, args.manifest, must_exist=True)
        manifest_value, manifest_raw = shared._load_json_file(manifest_path, token)
        reservation_manifest = validate_reservation_manifest(manifest_value, root)
        reservation_manifest_sha256 = hashlib.sha256(manifest_raw).hexdigest()
        template_path = shared._external_path_in_root(
            root, args.final_template_manifest, must_exist=True
        )
        template_value, template_raw = shared._load_json_file(template_path, token)
        template_manifest = validate_manifest(template_value, root)
        template_manifest_sha256 = hashlib.sha256(template_raw).hexdigest()
        client = SingleReportClient(
            token,
            args.base_url,
            poll_attempts=args.poll_attempts,
            poll_interval=args.poll_interval,
        )
        reservation_path = shared._external_path_in_root(
            root, args.reservation, must_exist=args.command != "reserve"
        )
        if args.command == "reserve":
            outcome = reserve(
                client,
                reservation_manifest,
                reservation_manifest_sha256,
                template_manifest,
                template_manifest_sha256,
                root,
                reservation_path,
            )
        else:
            reservation, _ = shared._load_json_file(reservation_path, token)
            final_path = shared._external_path_in_root(
                root, args.final_manifest, must_exist=True
            )
            final_value, final_raw = shared._load_json_file(final_path, token)
            final_manifest = validate_manifest(final_value, root)
            final_manifest_sha256 = hashlib.sha256(final_raw).hexdigest()
            result_path = shared._external_path_in_root(
                root, args.result, must_exist=False
            )
            if args.command == "finalize":
                outcome = finalize(
                    client,
                    reservation_manifest,
                    reservation_manifest_sha256,
                    template_manifest,
                    template_manifest_sha256,
                    final_manifest,
                    final_manifest_sha256,
                    reservation,
                    root,
                    result_path,
                )
            else:
                outcome = status(
                    client,
                    reservation_manifest,
                    reservation_manifest_sha256,
                    template_manifest,
                    template_manifest_sha256,
                    final_manifest,
                    final_manifest_sha256,
                    reservation,
                    root,
                    result_path,
                )
        print(json.dumps({"status": "ok", "phase": outcome["phase"]}, sort_keys=True))
        return 0
    except ZenodoError as exc:
        print("BLOCK " + shared.redact(str(exc), token), file=sys.stderr)
        return 1
    except Exception:
        print("BLOCK internal status-report Zenodo client failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
