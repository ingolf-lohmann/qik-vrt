#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.ai_handoff import (  # noqa: E402
    client_causal_key, client_end_of_action_domain, validate_client_readback,
    validate_client_work,
)
from tools.qikvrt_integrity import _exclusive_integrity_lock  # noqa: E402
from qikvrt_api_handler import (  # noqa: E402
    IntegrityIsolationError, _assert_safe_target, atomic_write_bytes,
)

SAFE_REPOSITORY_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9_.=-]{1,128}$")
SHA256_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SHA1_HEX = re.compile(r"^[0-9a-f]{40}$")
JOURNAL_SCHEMA = "qikvrt-api-client-attempt/1"
WORK_SCHEMA = "qikvrt-api-client-work/1"
MAX_WORK_BYTES = 128 * 1024
MAX_RECOVERY_JOURNALS = 256


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


def read_response_bytes(response) -> bytes:
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("API response exceeds the 2 MiB client limit")
    return data


def read_response(response) -> str:
    return read_response_bytes(response).decode("utf-8")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode("utf-8")).hexdigest()


def unique_json(raw: bytes):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON member")
            result[key] = value
        return result

    def invalid_constant(_value):
        raise ValueError("non-finite JSON value")

    return json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                      parse_constant=invalid_constant)


def closing_readback(opener, args, *, action_id: str, completed_at: str, token: str, domain: str):
    """One bounded closing pair, including when either observation fails."""
    repository = f"{args.owner}/{args.repo}"
    repo_url = f"https://api.github.com/repos/{repository}/commits/{quote(args.ref, safe='')}"
    public_url = "https://" + domain + "/"
    readback = {}
    for kind, url in (("repository", repo_url), ("delivery", public_url)):
        headers = {"Cache-Control": "no-cache", "Accept": "application/vnd.github+json"}
        # An adapter credential is never a GitHub credential. Reuse it only
        # when dispatch itself was bound to this exact GitHub API origin.
        if kind == "repository" and args.base_url.rstrip("/") == "https://api.github.com":
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        observation = {"source": url, "action_id": action_id, "method": "GET"}
        if kind == "repository":
            observation.update(repository=repository, ref=args.ref, head=None, tree=None)
        else:
            observation.update(hostname=domain, url=url,
                               state="UNKNOWN", working_software=False)
        try:
            with opener.open(request, timeout=10) as response:
                raw = read_response_bytes(response)
                observation.update(http_status=response.status, final_url=response.geturl(),
                                   response_sha256=hashlib.sha256(raw).hexdigest())
                if response.status != 200 or response.geturl() != url:
                    raise ValueError("closing GET requires HTTP 200 at its exact URL")
                if kind == "repository":
                    document = unique_json(raw)
                    head = document.get("sha") if isinstance(document, dict) else None
                    tree = document.get("commit", {}).get("tree", {}).get("sha") if isinstance(document, dict) else None
                    if not isinstance(head, str) or not SHA1_HEX.fullmatch(head) or not isinstance(tree, str) or not SHA1_HEX.fullmatch(tree):
                        raise ValueError("repository readback lacks exact HEAD/TREE")
                    observation.update(head=head, tree=tree)
                else:
                    # Reachability and TLS are observable; working software
                    # bound to this HEAD/TREE is not proved by a page GET.
                    observation.update(state="PENDING", tls=True)
        except (urllib.error.URLError, TimeoutError, OSError, UnicodeError,
                ValueError, AttributeError, TypeError, RecursionError) as exc:
            observation["error_category"] = type(exc).__name__
            if isinstance(exc, urllib.error.HTTPError):
                observation["http_status"] = exc.code
                exc.close()
        observation["observed_at"] = utc_now()
        readback[kind] = observation
    window = {"id": action_id, "completed_at": completed_at, "closed_at": utc_now()}
    valid = not any("error_category" in item for item in readback.values())
    if valid:
        subject = {key: readback["repository"][key] for key in ("repository", "ref", "head", "tree")}
        try:
            validate_client_readback(readback, subject, window)
        except SystemExit:
            valid = False
    return {"action_window": window, "readback": readback, "valid": valid}


def load_previous_work(root: Path) -> dict | None:
    path = root / "CONTINUATION.data"
    _assert_safe_target(path)
    if not path.exists():
        return None
    if path.stat().st_nlink != 1:
        raise OSError("continuation work must be a single-link regular file")
    previous = unique_json(read_regular_file(path, max_bytes=MAX_WORK_BYTES))
    if (not isinstance(previous, dict) or previous.get("schema") != WORK_SCHEMA
            or not isinstance(previous.get("execution_id"), str)
            or not previous["execution_id"].strip()):
        raise ValueError("invalid previous client work")
    validate_client_work(previous)
    return previous


def recover_journal_work(root: Path, previous: dict | None, domain: str) -> dict | None:
    """Recover open duties even if a crash prevented the last-work cursor.

    The pre-POST journal is the durable authority for unresolved intent. A
    missing work projection is never permission to forget it or redispatch it.
    This reads only the existing digest-named journal namespace under its lock.
    """
    work = {task["id"]: dict(task) for task in previous["work"]} if previous else {}
    sources = []
    for path in sorted(root.glob("*.json")):
        if not SHA256_HEX.fullmatch(path.stem):
            continue
        if len(sources) >= MAX_RECOVERY_JOURNALS:
            raise ValueError("journal recovery limit exceeded; no predecessor discarded")
        _assert_safe_target(path)
        if path.stat().st_nlink != 1:
            raise OSError("recovery journal must be a single-link regular file")
        raw = read_regular_file(path, max_bytes=16 * 1024)
        try:
            record = unique_json(raw)
        except RecursionError as exc:
            raise ValueError("recovery journal JSON nesting exceeds the decoder limit") from exc
        if (not isinstance(record, dict) or record.get("schema") != JOURNAL_SCHEMA
                or record.get("subject_key") != path.stem
                or record.get("status") not in ("in_flight", "failed", "ambiguous", "completed", "pending")
                or not isinstance(record.get("current"), dict)
                or record["current"].get("subject") != path.stem):
            raise ValueError("invalid recovery journal binding")
        client_causal_key(record["current"])
        source = {"state_file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                  "status": record["status"]}
        sources.append(source)
        if record["status"] != "completed":
            identifier = "api:" + path.stem
            task = dict(work.get(identifier, {}))
            task.update(id=identifier, state="OPEN", evidence="", state_file=path.name,
                        source_record_sha256=source["sha256"], source_status=record["status"],
                        next_action="Resolve the original durable intent or failure in " + path.name
                                    + "; observe its effect before any admitted retry")
            work[identifier] = task
        closing_receipt = record.get("closing_verification", {})
        if not isinstance(closing_receipt, dict) or not isinstance(closing_receipt.get("readback", {}), dict):
            raise ValueError("invalid recovery closing receipt")
        closing = closing_receipt.get("readback", {}).get("repository", {})
        metadata = record.get("request_metadata", {})
        if not isinstance(closing, dict) or not isinstance(metadata, dict):
            raise ValueError("invalid recovery repository or request metadata")
        repository, ref = closing.get("repository", metadata.get("repository")), closing.get("ref", metadata.get("ref"))
        exact = (isinstance(closing.get("head"), str) and SHA1_HEX.fullmatch(closing["head"])
                 and isinstance(closing.get("tree"), str) and SHA1_HEX.fullmatch(closing["tree"])
                 and "error_category" not in closing)
        if not exact:
            known = (isinstance(repository, str) and isinstance(ref, str) and repository and ref)
            identifier = "repository:" + repository + "@" + ref if known else "repository-intent:" + path.stem
            work[identifier] = {"id": identifier, "state": "OPEN", "evidence": "",
                                "state_file": path.name, "source_record_sha256": source["sha256"],
                                "next_action": "Recover the original repository/ref and obtain its missing fresh HEAD/TREE readback using " + path.name}
    if not sources:
        return previous
    work["delivery:" + domain] = {"id": "delivery:" + domain, "state": "OPEN", "evidence": "",
                                   "next_action": "Verify Working Software, TLS and exact-build delivery at https://" + domain + "/"}
    recovered = dict(previous) if previous else {"schema": WORK_SCHEMA, "state": "CONTINUE",
                                                "execution_id": "durable-intents:" + digest(sources)}
    recovered["work"] = list(work.values())
    recovered["recovery_sources"] = sources
    recovered["recovery_scope"] = "DURABLE_METADATA_RECONSTRUCTION_NOT_EFFECT_PROOF"
    validate_client_work(recovered)
    if len(json.dumps(recovered, sort_keys=True).encode("utf-8")) > MAX_WORK_BYTES:
        raise ValueError("recovered work exceeds the bounded state limit; no tasks discarded")
    return recovered


def persist_successor_work(root: Path, args, *, subject_key: str, record: dict,
                           closure: dict, action_id: str, domain: str,
                           previous: dict | None) -> dict:
    """Retain every previous open duty in the same serialized client path.

    Readbacks are fresh observations. A public GET does not close the delivery
    duty, and a different request cannot close an earlier failed operation.
    """
    work = {task["id"]: dict(task) for task in previous["work"]
            if task["state"] == "OPEN"} if previous else {}
    repository = f"{args.owner}/{args.repo}"
    repo = closure["readback"]["repository"]
    repo_valid = (isinstance(repo.get("head"), str) and SHA1_HEX.fullmatch(repo["head"])
                  and isinstance(repo.get("tree"), str) and SHA1_HEX.fullmatch(repo["tree"])
                  and "error_category" not in repo)
    current = [
        {"id": "api:" + subject_key, "state": "VERIFIED" if record["status"] == "completed" else "OPEN",
         "repository": repository, "ref": args.ref, "operation": args.operation,
         "artifact_id": args.artifact_id, "state_file": subject_key + ".json",
         "evidence": record.get("response_sha256", "") if record["status"] == "completed" else "",
         "next_action": "Resolve " + args.operation + " for " + repository + "@" + args.ref
                        + " artifact " + args.artifact_id + " using recorded subject " + subject_key},
        {"id": "repository:" + repository + "@" + args.ref, "state": "VERIFIED" if repo_valid else "OPEN",
         "evidence": digest(repo) if repo_valid else "",
         "next_action": "Obtain fresh bound-ref HEAD/TREE through " + repo["source"]},
        {"id": "delivery:" + domain, "state": "OPEN", "evidence": "",
         "next_action": "Verify Working Software, TLS and exact-build delivery at https://" + domain + "/"},
    ]
    work.update({task["id"]: task for task in current})
    successor = {"schema": WORK_SCHEMA, "execution_id": action_id, "state": "CONTINUE",
                 "work": list(work.values()), "action_window": closure["action_window"],
                 "readback": closure["readback"], "effect_state": "EFFECT_ACK_CONTINUE",
                 "ordinary_release": False}
    if previous:
        successor["previous_run"] = {"execution_id": previous["execution_id"],
                                     "open_work": [task["id"] for task in previous["work"] if task["state"] == "OPEN"]}
    validate_client_work(successor)
    raw = json.dumps(successor, sort_keys=True).encode("utf-8")
    if len(raw) > MAX_WORK_BYTES:
        raise ValueError("continuation backlog exceeds the bounded state limit; no tasks discarded")
    # Existing private atomic writer, under the existing process lock. Retain
    # original per-run evidence before replacing the last-run cursor.
    history = root / ("work-" + hashlib.sha256(action_id.encode()).hexdigest() + ".data")
    _assert_safe_target(history)
    atomic_write_bytes(history, raw)
    atomic_write_bytes(root / "CONTINUATION.data", raw)
    return successor


def dispatch_with_journal(opener, request, args, *, subject_key: str, receipt: dict,
                          closure: dict, action_id: str, token: str, domain: str):
    """Persist intent before POST; unchanged failures survive client restarts."""
    root = Path(args.state_dir).absolute()
    # Reuse the handler's no-symlink target checks and durable private writer,
    # and the existing nonblocking process lock. This contains metadata only.
    for parent in (root, *root.parents):
        if parent.is_symlink():
            raise OSError("client state directory must not traverse a symlink")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.stat().st_mode & 0o022:
        raise OSError("client state directory must not be group/world writable")
    path = root / (subject_key + ".json")
    _assert_safe_target(path)
    with _exclusive_integrity_lock(root):
        previous_work = recover_journal_work(root, load_previous_work(root), domain)
        previous = None
        if path.exists():
            if path.stat().st_nlink != 1:
                raise OSError("client state must be a single-link regular file")
            previous = unique_json(read_regular_file(path, max_bytes=16 * 1024))
            if (not isinstance(previous, dict) or previous.get("schema") != JOURNAL_SCHEMA
                    or previous.get("subject_key") != subject_key
                    or previous.get("status") not in ("in_flight", "failed", "ambiguous", "completed", "pending")):
                raise ValueError("invalid persisted client attempt")
            client_causal_key(previous["current"])
        current = {"subject": subject_key, "error": digest("no previous failure"),
                   "cause": digest("no new causal evidence"),
                   "capability": digest({"url": request.full_url, "method": "POST"})}
        if previous and previous["status"] != "completed":
            current = previous["current"]
            if args.retry_evidence_file:
                current = unique_json(read_regular_file(Path(args.retry_evidence_file), max_bytes=16 * 1024))
                if (not isinstance(current, dict) or current.get("subject") != subject_key
                        or current.get("error") != previous["current"]["error"]):
                    raise ValueError("retry evidence is not bound to the failed subject/error")
            changed = client_causal_key(current) != client_causal_key(previous["current"])
            current = {key: current[key] for key in ("subject", "error", "cause", "capability")}
            # A changed causal receipt does not establish the outcome of an
            # ambiguous or asynchronous dispatch. That needs operation-scoped
            # observation through its existing executor, not another POST.
            if not changed or previous["status"] != "failed":
                receipt.update(dispatch_count=0, state="NOOP",
                               reason="UNCHANGED_FAILURE_OR_UNRESOLVED_DISPATCH",
                               previous_status=previous["status"])
                closure.update(closing_readback(opener, args, action_id=action_id,
                                               completed_at=utc_now(), token=token, domain=domain))
                receipt["continuation_work"] = persist_successor_work(
                    root, args, subject_key=subject_key, record=previous,
                    closure=closure, action_id=action_id, domain=domain, previous=previous_work)
                return 1
        record = {"schema": JOURNAL_SCHEMA, "subject_key": subject_key,
                  "current": current, "status": "in_flight",
                  "request_id": args.request_id, "execution_id": action_id,
                  "request_metadata": {"repository": f"{args.owner}/{args.repo}", "ref": args.ref,
                                       "operation": args.operation, "artifact_id": args.artifact_id}}

        def save():
            atomic_write_bytes(path, json.dumps(record, sort_keys=True).encode("utf-8"))

        save()  # Crash or timeout after this point must never silently redispatch.
        receipt["dispatch_count"] = 1
        result = 1
        try:
            with opener.open(request, timeout=10) as response:
                raw = read_response_bytes(response)
                receipt.update(http_status=response.status,
                               response_sha256=hashlib.sha256(raw).hexdigest())
                if response.status == 204 and not raw:
                    record["status"] = "pending"
                    result = 20
                else:
                    parsed = unique_json(raw)
                    if not isinstance(parsed, dict) or response.status not in (200, 202):
                        raise ValueError("invalid dispatch response")
                    handler = parsed.get("handler_result")
                    state = handler.get("effect_state") if isinstance(handler, dict) else None
                    receipt["scoped_handler_effect_state"] = state
                    if state in ("EFFECT_ACK_DONE", "EFFECT_ACK_CONTINUE"):
                        record["status"] = "completed" if state == "EFFECT_ACK_DONE" else "pending"
                        result = 20
                    else:
                        record["status"] = "failed"
        except urllib.error.HTTPError as exc:
            receipt.update(http_status=exc.code, error_category="HTTPError")
            try:
                receipt["response_sha256"] = hashlib.sha256(read_response_bytes(exc)).hexdigest()
            except (OSError, ValueError):
                pass
            finally:
                exc.close()
            # A denial precedes execution; server errors may hide an effect.
            record["status"] = "failed" if exc.code in (400, 401, 403, 404, 405, 422, 429) else "ambiguous"
            print(f"BLOCK API request failed: HTTP {exc.code}", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, OSError, UnicodeError,
                ValueError, AttributeError, TypeError, RecursionError) as exc:
            receipt["error_category"] = type(exc).__name__
            record["status"] = "ambiguous"
            print(f"BLOCK API request failed: {type(exc).__name__}", file=sys.stderr)
        if record["status"] in ("failed", "ambiguous"):
            record["current"] = dict(current, error=digest(receipt))
        closure.update(closing_readback(opener, args, action_id=action_id,
                                       completed_at=utc_now(), token=token, domain=domain))
        record["closing_verification"] = closure
        if "response_sha256" in receipt:
            record["response_sha256"] = receipt["response_sha256"]
        save()  # Keep the lock through closure; a crash retains in-flight intent.
        receipt["continuation_work"] = persist_successor_work(
            root, args, subject_key=subject_key, record=record,
            closure=closure, action_id=action_id, domain=domain, previous=previous_work)
        return result

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
    ap.add_argument("--dry-run", default="true", choices=["true", "false"])
    ap.add_argument("--request-id", default="", help="Stable idempotency key; required for non-dry-run effects")
    ap.add_argument("--accept-effect", action="store_true", help="Explicitly accept the scoped non-dry-run effect")
    ap.add_argument("--state-dir", default=os.environ.get("QIKVRT_API_CLIENT_STATE_DIR", str(Path.home() / ".local/state/qikvrt/api-client")), help="Private persistent non-secret attempt metadata")
    ap.add_argument("--retry-evidence-file", help="New failure-bound subject/error/cause/capability digests; observation clocks do not admit retry")
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
    host = parsed_base.hostname
    if ":" in host:
        host = "[" + host + "]"
    default_port = 443 if parsed_base.scheme == "https" else 80
    port = "" if parsed_base.port in (None, default_port) else f":{parsed_base.port}"
    args.base_url = f"{parsed_base.scheme}://{host}{port}"
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
    encoded_body = json.dumps(body).encode("utf-8")
    if len(encoded_body) > 1024 * 1024:
        ap.error("encoded JSON request exceeds the 1 MiB transport limit")
    url = f"{args.base_url.rstrip('/')}/repos/{args.owner}/{args.repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches"
    req = urllib.request.Request(url, data=encoded_body, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}, method="POST")
    opener = urllib.request.build_opener(NoRedirectHandler())
    # A new request-id alone must not bypass an unchanged admission failure.
    semantic_body = unique_json(encoded_body)
    semantic_body["inputs"].pop("request_id")
    semantic_url = f"{args.base_url}/repos/{args.owner.lower()}/{args.repo.lower()}/actions/workflows/qikvrt_mesh_api.yml/dispatches"
    subject_key = digest({"url": semantic_url, "body": semantic_body})
    action_id = "client:" + args.request_id + ":" + utc_now()
    dispatch = {"dispatch_count": 0}
    result = 1
    closure = {}
    # Load and verify the unchanged Owner contract before any effect.
    domain = client_end_of_action_domain()
    try:
        result = dispatch_with_journal(
            opener, req, args, subject_key=subject_key, receipt=dispatch,
            closure=closure, action_id=action_id, token=token, domain=domain)
    except (OSError, RuntimeError, ValueError, KeyError, SystemExit, IntegrityIsolationError) as exc:
        dispatch["error_category"] = type(exc).__name__
        print(f"BLOCK API request failed: {type(exc).__name__}", file=sys.stderr)
    finally:
        if not closure:
            closure.update(closing_readback(opener, args, action_id=action_id,
                                           completed_at=utc_now(), token=token, domain=domain))
    # The adapter's scoped effect is retained as evidence, never promoted to
    # delivery. The transport client cannot prove working-software behavior.
    print(json.dumps({"schema": "qikvrt-api-client-readback/1", "dispatch": dispatch,
                      "closing_verification": closure,
                      "effect_state": "EFFECT_ACK_CONTINUE", "ordinary_release": False}))
    return result if closure["valid"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
