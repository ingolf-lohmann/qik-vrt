#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

SAFE_REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
API_CONTRACT_VERSION = "2.1.0"


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never forward a bearer credential through an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_regular_file(path: Path, *, max_bytes: int) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise OSError("path is not a regular file")
        if before.st_size > max_bytes:
            raise OSError(f"file exceeds {max_bytes} bytes")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise OSError(f"file exceeds {max_bytes} bytes")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise OSError("file changed while being read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_response(response) -> str:
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("API response exceeds the 2 MiB client limit")
    return data.decode("utf-8")


def interpret_dispatch_response(response, *, request, repository, ref, request_id):
    """Keep asynchronous transport acceptance distinct from handler effects."""
    status = response.status
    response_text = read_response(response)
    if status == 204:
        if response_text:
            raise ValueError("204 dispatch response must be empty")
        parsed = None
    else:
        parsed = json.loads(response_text)
        if not isinstance(parsed, dict):
            raise ValueError("dispatch response must be a JSON object")

    github_endpoint = request.full_url.startswith("https://api.github.com/")
    if github_endpoint and status not in (200, 204):
        raise ValueError(f"unexpected GitHub dispatch response status {status}")
    if status == 204 or (status == 200 and github_endpoint):
        run_id = None
        run_url = None
        html_url = None
        if status == 200:
            run_id = parsed.get("workflow_run_id")
            if type(run_id) is not int or run_id <= 0:
                raise ValueError("GitHub dispatch response omitted a positive workflow_run_id")
            run_url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}"
            html_url = f"https://github.com/{repository}/actions/runs/{run_id}"
            if parsed.get("run_url") != run_url or parsed.get("html_url") != html_url:
                raise ValueError("GitHub dispatch run URLs do not match the requested repository/run")
        return 20, {
            "schema": "qikvrt_dispatch_transport_receipt_v1",
            "api_contract_version": API_CONTRACT_VERSION,
            "transport_acknowledged": True,
            "http_status": status,
            "repository": repository,
            "ref": ref,
            "request_id": request_id,
            "request_sha256": hashlib.sha256(request.data).hexdigest(),
            "dispatch_url": request.full_url,
            "dispatch_count": 1,
            "workflow_run_id": run_id,
            "run_url": run_url,
            "html_url": html_url,
            "execution_verified": False,
            "effect_state": "EFFECT_ACK_CONTINUE",
            "ordinary_release": False,
            "next_checks": [
                "READ_WORKFLOW_RUN_AND_VERIFY_REPOSITORY_WORKFLOW_EVENT_HEAD_BINDING",
                "READ_QIKVRT_API_STATE_ARTIFACT_AND_VERIFY_REQUEST_ID_AND_EFFECT_SCOPE",
            ],
            "retry_policy": "REOBSERVE_BEFORE_ANY_NEW_DISPATCH",
        }

    if status not in (200, 202):
        raise ValueError(f"unexpected dispatch response status {status}")
    result = parsed.get("handler_result")
    if not isinstance(result, dict):
        raise ValueError("local adapter response omitted handler_result")
    effect_state = result.get("effect_state")
    return ({"EFFECT_ACK_DONE": 0, "EFFECT_ACK_CONTINUE": 20}.get(effect_state, 1), parsed)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8766")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--operation", choices=["ingest", "verify", "stage", "release_status"], default="ingest")
    ap.add_argument("--artifact-id", default="qikvrt_artifact")
    ap.add_argument("--payload-file")
    ap.add_argument("--expected-sha256")
    ap.add_argument("--remote-evidence-file", help="Signed release-attestation JSON for release_status")
    ap.add_argument("--state-run-id", help="Prior state-producing Mesh API workflow run for verify/stage")
    ap.add_argument("--return-run-details", action="store_true", help="Request GitHub's asynchronous run ID/URLs; local evaluation remains synchronous")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    ap.add_argument("--request-id", default="", help="Stable idempotency key; required for non-dry-run effects")
    ap.add_argument("--accept-effect", action="store_true", help="Explicitly accept the scoped non-dry-run effect")
    args = ap.parse_args()

    token = os.environ.get("QIKVRT_API_TOKEN", "")
    if not token:
        ap.error("QIKVRT_API_TOKEN must be supplied through the environment")
    if not SAFE_REPOSITORY_COMPONENT.fullmatch(args.owner):
        ap.error("--owner contains unsafe characters")
    if not SAFE_REPOSITORY_COMPONENT.fullmatch(args.repo):
        ap.error("--repo contains unsafe characters")
    if not SAFE_ID.fullmatch(args.artifact_id):
        ap.error("--artifact-id contains unsafe characters")
    if not SAFE_ID.fullmatch(args.request_id):
        ap.error("--request-id is required and must be a safe identifier")
    if not args.ref.strip() or len(args.ref) > 255:
        ap.error("--ref must contain 1 to 255 characters")
    if args.expected_sha256 and not SHA256_HEX.fullmatch(args.expected_sha256):
        ap.error("--expected-sha256 must be exactly 64 hexadecimal characters")
    if args.state_run_id is not None and not re.fullmatch(r"[0-9]{1,32}", args.state_run_id):
        ap.error("--state-run-id must contain 1 to 32 decimal digits")
    parsed_base = urlparse(args.base_url)
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
        ap.error("--base-url must be an absolute HTTP(S) URL")
    if parsed_base.scheme != "https" and parsed_base.hostname not in loopback_hosts:
        ap.error("non-loopback API endpoints require HTTPS to protect the bearer token")
    if parsed_base.username or parsed_base.password or parsed_base.query or parsed_base.fragment:
        ap.error("--base-url must not contain credentials, query parameters, or a fragment")
    if parsed_base.path not in ("", "/"):
        ap.error("--base-url must not contain a path")
    try:
        parsed_base.port
    except ValueError:
        ap.error("--base-url contains an invalid port")
    if args.dry_run == "false":
        if not args.accept_effect:
            ap.error("--accept-effect is required when --dry-run=false")

    payload_b64 = ""
    remote_evidence_b64 = ""
    expected = args.expected_sha256 or ""
    if args.payload_file:
        p = Path(args.payload_file)
        try:
            payload = read_regular_file(p, max_bytes=700 * 1024)
        except OSError as exc:
            ap.error(f"payload file cannot be read: {exc}")
        payload_b64 = base64.b64encode(payload).decode("ascii")
        expected = expected or hashlib.sha256(payload).hexdigest()
    if args.remote_evidence_file:
        evidence_path = Path(args.remote_evidence_file)
        try:
            evidence = read_regular_file(evidence_path, max_bytes=192 * 1024)
        except OSError as exc:
            ap.error(f"remote evidence file cannot be read: {exc}")
        try:
            evidence_document = json.loads(evidence.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ap.error(f"remote evidence must be a UTF-8 JSON document: {exc}")
        if not isinstance(evidence_document, dict):
            ap.error("remote evidence JSON must be an object")
        remote_evidence_b64 = base64.b64encode(evidence).decode("ascii")

    body = {
        "ref": args.ref,
        "inputs": {
            "operation": args.operation,
            "artifact_id": args.artifact_id,
            "payload_b64": payload_b64,
            "expected_sha256": expected,
            "dry_run": args.dry_run,
            "request_id": args.request_id,
            "effect_accepted": args.accept_effect,
            "remote_evidence_b64": remote_evidence_b64,
        },
    }
    if args.state_run_id is not None:
        body["inputs"]["state_run_id"] = args.state_run_id
    if args.return_run_details:
        body["return_run_details"] = True
    encoded_body = json.dumps(body).encode("utf-8")
    if len(encoded_body) > 1024 * 1024:
        ap.error("encoded JSON request exceeds the 1 MiB transport limit")
    url = f"{args.base_url.rstrip('/')}/repos/{args.owner}/{args.repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches"
    req = urllib.request.Request(url, data=encoded_body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}, method="POST")
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(req, timeout=10) as resp:
            result, receipt = interpret_dispatch_response(
                resp, request=req, repository=f"{args.owner}/{args.repo}",
                ref=args.ref, request_id=args.request_id,
            )
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
            return result
    except urllib.error.HTTPError as exc:
        try:
            print(read_response(exc), file=sys.stderr)
        except (UnicodeDecodeError, ValueError) as response_exc:
            print(f"BLOCK API returned an unreadable error response: {response_exc}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"BLOCK API request failed: {exc}", file=sys.stderr)
        print(json.dumps({
            "schema": "qikvrt_dispatch_transport_receipt_v1",
            "api_contract_version": API_CONTRACT_VERSION,
            "transport_acknowledged": False,
            "dispatch_outcome": "UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK",
            "repository": f"{args.owner}/{args.repo}",
            "ref": args.ref,
            "request_id": args.request_id,
            "request_sha256": hashlib.sha256(encoded_body).hexdigest(),
            "dispatch_url": url,
            "dispatch_count": 1,
            "execution_verified": False,
            "ordinary_release": False,
            "retry_policy": "REOBSERVE_BEFORE_ANY_NEW_DISPATCH",
        }, sort_keys=True), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
