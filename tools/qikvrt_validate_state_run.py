#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed validation for a workflow-run state handoff.

The GitHub Actions workflow accepts a caller-supplied ``state_run_id``.  This
module resolves that identifier through GitHub's authenticated API and binds
the response to the current repository, workflow and commit before an artifact
download may occur.  It deliberately uses only the Python standard library.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

EXPECTED_WORKFLOW_PATH = ".github/workflows/qikvrt_mesh_api.yml"
ALLOWED_EVENTS = frozenset({"repository_dispatch", "workflow_dispatch"})
MAX_RESPONSE_BYTES = 256 * 1024
MAX_TOKEN_BYTES = 4096
RUN_ID_RE = re.compile(r"^[1-9][0-9]{0,31}$")
REPOSITORY_PART_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SHA_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class StateRunValidationError(ValueError):
    """A state handoff could not be proven safe."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Mapping[str, str],
        newurl: str,
    ) -> None:
        return None


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _unique_json_object(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def parse_run_metadata(raw: bytes) -> dict[str, Any]:
    """Decode one bounded, strict UTF-8 JSON object."""
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise StateRunValidationError("run metadata response is empty or oversized")
    try:
        text = raw.decode("utf-8", errors="strict")
        value = json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeError, ValueError, RecursionError, json.JSONDecodeError) as exc:
        raise StateRunValidationError("run metadata is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise StateRunValidationError("run metadata root must be a JSON object")
    return value


def _validated_repository(repository: str) -> tuple[str, str]:
    if len(repository) > 201 or repository.count("/") != 1:
        raise StateRunValidationError("repository must have the form owner/name")
    owner, name = repository.split("/", 1)
    if not REPOSITORY_PART_RE.fullmatch(owner) or not REPOSITORY_PART_RE.fullmatch(name):
        raise StateRunValidationError("repository contains an invalid component")
    return owner, name


def _validated_api_url(api_url: str, server_url: str) -> str:
    try:
        parsed = urllib.parse.urlsplit(api_url)
        port = parsed.port
    except ValueError as exc:
        raise StateRunValidationError("GitHub API URL is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or port not in (None, 443)
    ):
        raise StateRunValidationError("GitHub API URL must be credential-free HTTPS")
    try:
        server = urllib.parse.urlsplit(server_url)
    except ValueError as exc:
        raise StateRunValidationError("GitHub server URL is invalid") from exc
    if (
        server.scheme != "https"
        or not server.hostname
        or server.username is not None
        or server.password is not None
        or server.query
        or server.fragment
    ):
        raise StateRunValidationError("GitHub server URL must be credential-free HTTPS")
    expected_api_host = (
        "api.github.com" if server.hostname.lower() == "github.com" else server.hostname.lower()
    )
    if parsed.hostname.lower() != expected_api_host:
        raise StateRunValidationError("GitHub API host is not bound to GitHub server URL")
    path = parsed.path.rstrip("/")
    return urllib.parse.urlunsplit(("https", parsed.netloc, path, "", ""))


def build_run_url(
    api_url: str,
    repository: str,
    run_id: str,
    server_url: str = "https://github.com",
) -> str:
    if not RUN_ID_RE.fullmatch(run_id):
        raise StateRunValidationError("state_run_id must be a positive decimal identifier")
    owner, name = _validated_repository(repository)
    base = _validated_api_url(api_url, server_url)
    return (
        f"{base}/repos/{urllib.parse.quote(owner, safe='')}/"
        f"{urllib.parse.quote(name, safe='')}/actions/runs/{run_id}"
    )


def fetch_run_metadata(
    *,
    api_url: str,
    repository: str,
    run_id: str,
    token: str,
    server_url: str = "https://github.com",
    opener: Any | None = None,
) -> dict[str, Any]:
    """Fetch run metadata without redirects or unbounded response buffering."""
    if (
        not token
        or len(token.encode("utf-8")) > MAX_TOKEN_BYTES
        or "\r" in token
        or "\n" in token
    ):
        raise StateRunValidationError("GitHub token is missing or invalid")
    url = build_run_url(api_url, repository, run_id, server_url)
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "Authorization": f"Bearer {token}",
            "User-Agent": "qikvrt-state-run-validator/1",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    client = opener or urllib.request.build_opener(_NoRedirectHandler())
    try:
        with client.open(request, timeout=15) as response:
            status = getattr(response, "status", None)
            final_url = response.geturl()
            if status != 200:
                raise StateRunValidationError("GitHub run lookup did not return HTTP 200")
            if final_url != url:
                raise StateRunValidationError("GitHub run lookup attempted a redirect")
            content_encoding = response.headers.get("Content-Encoding", "").strip().lower()
            if content_encoding not in ("", "identity"):
                raise StateRunValidationError("encoded run metadata is not accepted")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length, 10)
                except ValueError as exc:
                    raise StateRunValidationError("invalid Content-Length") from exc
                if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
                    raise StateRunValidationError("run metadata response is oversized")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except StateRunValidationError:
        raise
    except (OSError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        raise StateRunValidationError("GitHub run lookup failed closed") from exc
    return parse_run_metadata(raw)


def validate_run_binding(
    metadata: Mapping[str, Any],
    *,
    run_id: str,
    repository: str,
    head_sha: str,
    workflow_path: str = EXPECTED_WORKFLOW_PATH,
) -> None:
    """Require an exact trusted binding for the selected prior run."""
    if not RUN_ID_RE.fullmatch(run_id):
        raise StateRunValidationError("state_run_id must be a positive decimal identifier")
    _validated_repository(repository)
    if not SHA_RE.fullmatch(head_sha):
        raise StateRunValidationError("expected head SHA is invalid")
    if workflow_path != EXPECTED_WORKFLOW_PATH:
        raise StateRunValidationError("unexpected state-producing workflow path")

    metadata_id = metadata.get("id")
    if isinstance(metadata_id, bool) or not isinstance(metadata_id, int):
        raise StateRunValidationError("run metadata id must be an integer")
    nested_repository = metadata.get("repository")
    actual_repository = (
        nested_repository.get("full_name") if isinstance(nested_repository, Mapping) else None
    )
    metadata_path = metadata.get("path")
    path_matches = metadata_path == workflow_path
    if isinstance(metadata_path, str) and metadata_path.startswith(workflow_path + "@"):
        path_ref = metadata_path[len(workflow_path) + 1 :]
        path_matches = bool(path_ref) and len(path_ref) <= 1024 and not any(
            ord(character) < 32 or ord(character) == 127 for character in path_ref
        )
    checks = {
        "run id": str(metadata_id) == run_id,
        "repository": actual_repository == repository,
        "workflow path": path_matches,
        "head SHA": metadata.get("head_sha") == head_sha,
        "allowed event": metadata.get("event") in ALLOWED_EVENTS,
        "completed status": metadata.get("status") == "completed",
        "successful conclusion": metadata.get("conclusion") == "success",
    }
    failed = [name for name, accepted in checks.items() if not accepted]
    if failed:
        raise StateRunValidationError("state run binding failed: " + ", ".join(failed))


def validate_state_run_from_environment() -> str:
    run_id = os.environ.get("QIKVRT_STATE_RUN_ID", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    head_sha = os.environ.get("GITHUB_SHA", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    api_url = os.environ.get("GITHUB_API_URL", "")
    server_url = os.environ.get("GITHUB_SERVER_URL", "")
    metadata = fetch_run_metadata(
        api_url=api_url,
        repository=repository,
        run_id=run_id,
        token=token,
        server_url=server_url,
    )
    validate_run_binding(
        metadata,
        run_id=run_id,
        repository=repository,
        head_sha=head_sha,
    )
    return run_id


def main() -> int:
    try:
        run_id = validate_state_run_from_environment()
    except StateRunValidationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 20
    print(f"PASS: state run {run_id} is bound to this repository, workflow and commit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
