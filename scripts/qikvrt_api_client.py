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
from types import MappingProxyType
from urllib.parse import urlparse

SAFE_REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
API_CONTRACT_VERSION = "2.3.0"
SHA1_HEX = re.compile(r"^[0-9a-f]{40}$")
RULESET_OPERATIONS = {"ruleset_authority_dispatch", "ruleset_authority_readback"}
RULESET_REPOSITORY = "ingolf-lohmann/qik-vrt"
RULESET_WORKFLOW = "qikvrt_goldkelch_ruleset_authority_effect.yml"
RULESET_WORKFLOW_PATH = f".github/workflows/{RULESET_WORKFLOW}"
# Preserve the 2.2 legacy binding and default; no automatic version fallback.
RULESET_WORKFLOW_BLOB = "1202d24c2f23eb8fa52ab7c562a583e79f9e8444"
RULESET_POST_SHA256 = "45da27f3608b38f04b8252d7fc709a6337bff49d40fa2cf9baa4425dd36ec0dd"
DEFAULT_RULESET_WRITER_VERSION = "legacy-v1"
MAX_RULESET_WRITER_BYTES = 64 * 1024
# Exact reviewed source contracts, not native approval or Main activation.
# The lifecycle writer preserves the original canonical Ruleset projection.
RULESET_WRITER_VERSIONS = MappingProxyType({
    "legacy-v1": (RULESET_WORKFLOW_BLOB, RULESET_POST_SHA256),
    "lifecycle-v2": ("ab47a8ec98c39b39bda420050cb7c970a9da6165", RULESET_POST_SHA256),
})


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

def ruleset_json_get(opener, token, path):
    """Read only a caller-independent path below the fixed repository."""
    request = urllib.request.Request(
        f"https://api.github.com/repos/{RULESET_REPOSITORY}/{path}",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"}, method="GET",
    )
    with opener.open(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("readback requires HTTP 200")
        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate readback JSON member")
                value[key] = item
            return value
        def reject_constant(_value):
            raise ValueError("non-finite readback JSON value")
        return json.loads(read_response(response), object_pairs_hook=unique_object,
                          parse_constant=reject_constant)


def ruleset_main_readback(get, expected_sha):
    branch = get("branches/main")
    if (not isinstance(branch, dict) or branch.get("name") != "main"
            or branch.get("commit", {}).get("sha") != expected_sha):
        raise ValueError("Main binding changed or is invalid")
    return branch


def verify_ruleset_writer(writer, expected_blob):
    """Verify immutable Contents bytes as well as the provider's blob label."""
    if (not isinstance(writer, dict) or writer.get("type") != "file"
            or writer.get("path") != RULESET_WORKFLOW_PATH
            or writer.get("sha") != expected_blob
            or writer.get("encoding") != "base64"
            or type(writer.get("size")) is not int
            or not 0 < writer["size"] <= MAX_RULESET_WRITER_BYTES
            or not isinstance(writer.get("content"), str)
            or len(writer["content"]) > MAX_RULESET_WRITER_BYTES * 2):
        raise ValueError("reviewed Ruleset writer binding mismatch")
    content = base64.b64decode("".join(writer["content"].splitlines()), validate=True)
    actual_blob = hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content,
        usedforsecurity=False,
    ).hexdigest()
    if len(content) != writer["size"] or actual_blob != expected_blob:
        raise ValueError("reviewed Ruleset writer bytes mismatch")


def normalize_ruleset(value):
    """Use the existing writer's canonical projection and digest contract."""
    rules = []
    for raw in value.get("rules") or []:
        item = json.loads(json.dumps(raw))
        parameters = item.get("parameters")
        if isinstance(parameters, dict):
            checks = parameters.get("required_status_checks")
            if isinstance(checks, list):
                parameters["required_status_checks"] = sorted(
                    checks, key=lambda check: (str(check.get("context", "")),
                                               int(check.get("integration_id") or 0)),
                )
            reviewers = parameters.get("required_reviewers")
            if isinstance(reviewers, list):
                parameters["required_reviewers"] = sorted(
                    reviewers, key=lambda reviewer: json.dumps(reviewer, sort_keys=True),
                )
        rules.append(item)
    return {
        "name": value.get("name"), "target": value.get("target"),
        "enforcement": value.get("enforcement"), "conditions": value.get("conditions"),
        "bypass_actors": value.get("bypass_actors") or [],
        "rules": sorted(rules, key=lambda item: item["type"]),
    }


def ruleset_collection(document, key=None):
    items = document.get(key) if key and isinstance(document, dict) else document
    if (not isinstance(items, list) or not all(isinstance(item, dict) for item in items)
            or len(items) >= 100
            or (key and (type(document.get("total_count")) is not int
                         or document["total_count"] != len(items)))):
        raise ValueError("incomplete or invalid readback collection; no effect inferred")
    return items


def ruleset_run_binding(run, run_id, expected_sha):
    if (not isinstance(run, dict) or type(run.get("id")) is not int
            or run["id"] != run_id
            or run.get("repository", {}).get("full_name") != RULESET_REPOSITORY
            or run.get("head_repository", {}).get("full_name") != RULESET_REPOSITORY
            or run.get("path") != RULESET_WORKFLOW_PATH
            or run.get("event") != "workflow_dispatch"
            or run.get("head_branch") != "main" or run.get("head_sha") != expected_sha
            or type(run.get("run_attempt")) is not int or run["run_attempt"] <= 0):
        raise ValueError("workflow run binding mismatch")
    return tuple(run.get(key) for key in (
        "id", "path", "event", "head_branch", "head_sha", "workflow_id",
        "run_attempt", "status", "conclusion",
    ))


def ruleset_authority_operation(args, token):
    """One bounded POST or independent GETs; never retry or grant a review."""
    # The pinned operation carrier cannot assign a second Authority.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.qikvrt_workflow_executor import load_repository_roles
    if RULESET_REPOSITORY != load_repository_roles()["AUTHORITY"]:
        raise ValueError("Ruleset carrier and canonical Authority policy disagree")
    opener = urllib.request.build_opener(NoRedirectHandler())
    get = lambda path: ruleset_json_get(opener, token, path)
    body = b'{"ref":"main"}'
    url = f"https://api.github.com/repos/{RULESET_REPOSITORY}/actions/workflows/{RULESET_WORKFLOW}/dispatches"
    writer_version = args.ruleset_writer_version or DEFAULT_RULESET_WRITER_VERSION
    writer_blob, post_sha256 = RULESET_WRITER_VERSIONS[writer_version]
    receipt = {
        "schema": "qikvrt_ruleset_authority_client_receipt_v1",
        "api_contract_version": API_CONTRACT_VERSION, "operation": args.operation,
        "repository": RULESET_REPOSITORY, "ref": "main", "main_sha": args.expected_main_sha,
        "workflow_path": RULESET_WORKFLOW_PATH, "workflow_blob_sha": writer_blob,
        "ruleset_writer_version": writer_version,
        "expected_ruleset_sha256": post_sha256, "writer_bytes_verified": False,
        "request_id": args.request_id,
        "request_id_scope": "LOCAL_CORRELATION_ONLY_NOT_GITHUB_IDEMPOTENCY",
        "dispatch_count": 0, "transport_acknowledged": False,
        "execution_verified": False, "ruleset_effect_verified": False,
        "effect_state": "EFFECT_ACK_CONTINUE", "ordinary_release": False,
        "retry_policy": "REOBSERVE_BEFORE_ANY_NEW_DISPATCH",
    }
    try:
        branch = ruleset_main_readback(get, args.expected_main_sha)
        writer = get(f"contents/{RULESET_WORKFLOW_PATH}?ref={args.expected_main_sha}")
        verify_ruleset_writer(writer, writer_blob)
        receipt["writer_bytes_verified"] = True
        if args.operation == "ruleset_authority_dispatch":
            runs = ruleset_collection(get(
                f"actions/workflows/{RULESET_WORKFLOW}/runs?branch=main&per_page=100"
            ), "workflow_runs")
            if any(run.get("status") != "completed"
                   or run.get("head_sha") == args.expected_main_sha for run in runs):
                raise ValueError("active or existing exact-head writer run requires readback")
            # The provider POST accepts a ref, not an atomic expected-SHA lease.
            # Recheck before POST and require the actual run SHA in readback.
            ruleset_main_readback(get, args.expected_main_sha)
            request = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json",
                "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"}, method="POST",
            )
            receipt.update(dispatch_url=url, request_sha256=hashlib.sha256(body).hexdigest(), dispatch_count=1)
            with opener.open(request, timeout=10) as response:
                if response.status != 204:
                    raise ValueError("Ruleset dispatch requires empty HTTP 204")
                code, transport = interpret_dispatch_response(
                    response, request=request, repository=RULESET_REPOSITORY,
                    ref="main", request_id=args.request_id,
                )
            receipt.update({key: transport[key] for key in (
                "transport_acknowledged", "http_status", "workflow_run_id",
                "run_url", "html_url",
            )})
            receipt["next_checks"] = [
                "IDENTIFY_RUN_BY_REPOSITORY_WORKFLOW_EVENT_REF_AND_EXACT_HEAD",
                "RUN_RULESET_AUTHORITY_READBACK_WITH_VERIFIED_RUN_ID",
                "REOBSERVE_CURRENT_HEAD_CODE_OWNER_GATE_AND_NATIVE_REVIEW",
            ]
            print(json.dumps(receipt, sort_keys=True))
            return code

        run_id = int(args.ruleset_run_id)
        run = get(f"actions/runs/{run_id}")
        binding = ruleset_run_binding(run, run_id, args.expected_main_sha)
        jobs = ruleset_collection(get(
            f"actions/runs/{run_id}/attempts/{run['run_attempt']}/jobs?per_page=100"
        ), "jobs")
        if any(type(job.get("run_id")) is not int or job["run_id"] != run_id
               or job.get("head_sha") != args.expected_main_sha
               or type(job.get("run_attempt")) is not int
               or job["run_attempt"] != run["run_attempt"] for job in jobs):
            raise ValueError("workflow job binding mismatch")
        execution = (run.get("status") == "completed" and run.get("conclusion") == "success"
                     and bool(jobs) and any(job.get("name") == "reconcile" for job in jobs)
                     and all(job.get("status") == "completed" and job.get("conclusion") == "success" for job in jobs))
        collection = ruleset_collection(get("rulesets?per_page=100&includes_parents=true"))
        matching = [item for item in collection if item.get("name") == "QIK-VRT main protection"]
        if len(matching) > 1:
            raise ValueError("multiple matching Rulesets; refusing effect inference")
        digest = None
        ruleset_id = None
        if matching:
            ruleset_id = matching[0].get("id")
            if type(ruleset_id) is not int or ruleset_id <= 0:
                raise ValueError("Ruleset ID is invalid")
            observed = get(f"rulesets/{ruleset_id}")
            if (not isinstance(observed, dict) or type(observed.get("id")) is not int
                    or observed["id"] != ruleset_id or observed.get("source") != RULESET_REPOSITORY):
                raise ValueError("Ruleset identity/source mismatch")
            canonical = (json.dumps(normalize_ruleset(observed), ensure_ascii=False,
                                   sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
            digest = hashlib.sha256(canonical).hexdigest()
        branch = ruleset_main_readback(get, args.expected_main_sha)
        if ruleset_run_binding(get(f"actions/runs/{run_id}"), run_id, args.expected_main_sha) != binding:
            raise ValueError("workflow run drifted during readback")
        effect = execution and digest == post_sha256 and branch.get("protected") is True
        receipt.update(
            workflow_run_id=run_id, run_attempt=run["run_attempt"],
            execution_verified=execution, main_protected=branch.get("protected") is True,
            ruleset_id=ruleset_id, observed_ruleset_sha256=digest,
            expected_ruleset_sha256=post_sha256, ruleset_effect_verified=effect,
            readback_state="RULESET_POSTCONDITION_VERIFIED" if effect else "RULESET_EFFECT_UNVERIFIED",
            mutation_attribution_verified=False, native_review_verified=False,
            verification_scope="RULESET_POSTCONDITION_ONLY_NOT_MERGE_OR_RELEASE",
        )
        print(json.dumps(receipt, sort_keys=True))
        return 0 if effect else 20
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        # Never echo provider bodies, URL error reasons or credential-bearing exceptions.
        receipt["failure_class"] = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            receipt["http_status"] = exc.code
        denied = isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403)
        receipt["dispatch_outcome"] = (
            "DENIED" if denied and receipt["dispatch_count"]
            else "UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK" if receipt["dispatch_count"]
            else "NO_POST_ATTEMPTED"
        )
        print("BLOCK Ruleset operation failed; inspect the non-secret receipt", file=sys.stderr)
        print(json.dumps(receipt, sort_keys=True), file=sys.stderr)
        return 1


def github_json_get(repository: str, path: str, *, token: str = "", opener=None) -> dict:
    """Bounded GET-only readback; reuse this client's no-redirect transport.

    Paths are supplied by trusted adapters, never an arbitrary client URL.
    The digest binds the exact received UTF-8 bytes, not reserialized JSON.
    """
    if len(repository.split("/")) != 2 or not all(
        SAFE_REPOSITORY_COMPONENT.fullmatch(part) and part not in (".", "..") for part in repository.split("/")
    ):
        raise ValueError("unsafe repository scope")
    if not re.fullmatch(r"(?:commits/[A-Za-z0-9_.-]+|git/(?:trees|blobs)/[0-9a-f]{40})(?:\?recursive=1)?", path):
        raise ValueError("readback path outside the bounded GitHub GET contract")
    if path.startswith("commits/") and ".." in path:
        raise ValueError("unsafe commit ref")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repository}/{path}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with (opener or urllib.request.build_opener(NoRedirectHandler())).open(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("readback requires HTTP 200")
        raw = read_response(response)
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate readback JSON member")
            result[key] = value
        return result
    def reject_constant(_value):
        raise ValueError("non-finite readback JSON value")
    document = json.loads(raw, object_pairs_hook=unique, parse_constant=reject_constant)
    if not isinstance(document, dict):
        raise ValueError("readback must be a JSON object")
    return {"document": document, "url": url, "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8766")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--operation", choices=["ingest", "verify", "stage", "release_status", *sorted(RULESET_OPERATIONS)], default="ingest")
    ap.add_argument("--artifact-id", default="qikvrt_artifact")
    ap.add_argument("--payload-file")
    ap.add_argument("--expected-sha256")
    ap.add_argument("--remote-evidence-file", help="Signed release-attestation JSON for release_status")
    ap.add_argument("--state-run-id", help="Prior state-producing Mesh API workflow run for verify/stage")
    ap.add_argument("--return-run-details", action="store_true", help="Request GitHub's asynchronous run ID/URLs; local evaluation remains synchronous")
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    ap.add_argument("--request-id", default="", help="Stable idempotency key; required for non-dry-run effects")
    ap.add_argument("--accept-effect", action="store_true", help="Explicitly accept the scoped non-dry-run effect")
    ap.add_argument("--expected-main-sha", help="Exact observed Main Git SHA-1 for the fixed Ruleset writer")
    ap.add_argument("--ruleset-run-id", help="Independently identified writer run; GET-only Ruleset readback")
    ap.add_argument("--ruleset-writer-version", choices=sorted(RULESET_WRITER_VERSIONS),
                    help="Exact reviewed writer contract; omitted preserves the 2.2 legacy-v1 pin")
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

    if args.operation in RULESET_OPERATIONS:
        if len(token) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in token):
            ap.error("Ruleset credential must be bounded printable ASCII without whitespace")
        if args.base_url.rstrip("/") != "https://api.github.com":
            ap.error("Ruleset operations require the canonical GitHub HTTPS endpoint")
        if f"{args.owner}/{args.repo}" != RULESET_REPOSITORY or args.ref != "main":
            ap.error("Ruleset operations allow only ingolf-lohmann/qik-vrt on main")
        if not args.expected_main_sha or not SHA1_HEX.fullmatch(args.expected_main_sha):
            ap.error("--expected-main-sha must be an observed lowercase Git SHA-1")
        if (args.payload_file or args.remote_evidence_file or args.expected_sha256
                or args.state_run_id is not None or args.return_run_details
                or args.artifact_id != "qikvrt_artifact"):
            ap.error("Mesh inputs and run-detail overrides are forbidden for the fixed Ruleset writer")
        if args.operation == "ruleset_authority_dispatch":
            if args.dry_run != "false" or not args.accept_effect or args.ruleset_run_id is not None:
                ap.error("Ruleset dispatch requires --dry-run false --accept-effect and no run ID")
        elif (args.ruleset_run_id is None
                or not re.fullmatch(r"[0-9]{1,32}", args.ruleset_run_id)
                or int(args.ruleset_run_id) <= 0 or args.dry_run != "true" or args.accept_effect):
            ap.error("Ruleset readback requires a positive --ruleset-run-id and read-only defaults")
        return ruleset_authority_operation(args, token)
    if (args.expected_main_sha is not None or args.ruleset_run_id is not None
            or args.ruleset_writer_version is not None):
        ap.error("Ruleset binding arguments require a Ruleset operation")

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
        print(f"BLOCK API HTTP {exc.code}; provider error body omitted", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        detail = str(exc).replace(token, "[REDACTED]") if type(exc) is ValueError else type(exc).__name__
        print(f"BLOCK API request failed: {detail}", file=sys.stderr)
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
