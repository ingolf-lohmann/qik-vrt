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
from types import MappingProxyType
from urllib.parse import quote, urlencode, urlparse

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
API_CONTRACT_VERSION = "2.3.0"
SHA1_HEX = re.compile(r"^[0-9a-f]{40}$")
RULESET_OPERATIONS = {"ruleset_authority_dispatch", "ruleset_authority_readback"}
AMO_OPERATIONS = {"firefox_amo_access", "firefox_amo_dispatch"}
STATIC_OPERATIONS = {"static_readback", "static_upload", "static_reconcile", "static_public_readback"}
AMO_WORKFLOW_PATH = ".github/workflows/qikvrt_ci.yml"
AMO_SECRET_NAMES = ("AMO_JWT_ISSUER", "AMO_JWT_SECRET")
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
    "app-renewal-v3": ("05066f6fb83a7f3ba8799677db35647e06942fd2", RULESET_POST_SHA256),
    "principal-review-v4": ("3b9396f4b6415baff047526bd6ecb193f606863e", "59b80123aee14fd0f82a0af8a7e3265a2a5782f786785cf09be35f251b9c6999"),
})
JOURNAL_SCHEMA = "qikvrt-api-client-attempt/1"
WORK_SCHEMA = "qikvrt-api-client-work/1"
MAX_WORK_BYTES = 128 * 1024
MAX_RECOVERY_JOURNALS = 256
MAX_COMPLETED_REQUESTS = 32
MAX_JOURNAL_BYTES = 16 * 1024


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


def completion_evidence(record: dict):
    if record.get("completion_basis") == "INDEPENDENT_PR_READY_READBACK":
        return record.get("effect_readback_sha256")
    return record.get("response_sha256")


def completed_request_evidence(record: dict) -> dict:
    """Retain stable completion witnesses in the existing bounded journal."""
    completed = record.get("completed_requests", {})
    if (not isinstance(completed, dict) or len(completed) > MAX_COMPLETED_REQUESTS
            or any(not isinstance(key, str) or not SAFE_ID.fullmatch(key)
                   or not isinstance(value, str) or not SHA256_HEX.fullmatch(value)
                   for key, value in completed.items())):
        raise ValueError("invalid completed-request evidence")
    completed = dict(completed)
    if record["status"] == "completed":
        identifier, evidence = record.get("request_id"), completion_evidence(record)
        if (not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier)
                or not isinstance(evidence, str) or not SHA256_HEX.fullmatch(evidence)):
            raise ValueError("completed journal lacks its stable response binding")
        if identifier in completed and completed[identifier] != evidence:
            raise ValueError("completed-request evidence drift")
        completed[identifier] = evidence
    if len(completed) > MAX_COMPLETED_REQUESTS:
        raise ValueError("completion evidence limit exceeded; no witness discarded")
    return completed


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
        raw = read_regular_file(path, max_bytes=MAX_JOURNAL_BYTES)
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
        completed_request_evidence(record)
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


def preserve_attempt_evidence(root: Path, record: dict, raw: bytes) -> None:
    """Checkpoint the original journal before reserving an admitted successor.

    Reuse the private work-history namespace. These are original non-secret
    attempt bytes, not a new dispatch, effect witness or last-work cursor.
    """
    source_digest = hashlib.sha256(raw).hexdigest()
    identifier = record.get("execution_id")
    if not isinstance(identifier, str) or not identifier.strip():
        identifier = "legacy-durable-attempt:" + source_digest
    task = {"id": "api:" + record["subject_key"],
            "state": "VERIFIED" if record["status"] == "completed" else "OPEN",
            "evidence": completion_evidence(record) if record["status"] == "completed" else "",
            "next_action": "Resolve the preserved original attempt before any further effect"}
    checkpoint = {"schema": WORK_SCHEMA, "execution_id": identifier,
                  "state": "CONTINUE", "work": [task], "attempt_record": record,
                  "source_journal_sha256": source_digest,
                  "source_journal_json": raw.decode("utf-8"),
                  "scope": "ORIGINAL_ATTEMPT_METADATA_NOT_NEW_EFFECT_PROOF"}
    validate_client_work(checkpoint)
    encoded = json.dumps(checkpoint, sort_keys=True).encode("utf-8")
    if len(encoded) > MAX_WORK_BYTES:
        raise ValueError("attempt checkpoint exceeds bounded state; no original discarded")
    identity = hashlib.sha256(("original-attempt:" + source_digest).encode()).hexdigest()
    path = root / ("work-" + identity + ".data")
    _assert_safe_target(path)
    if path.exists():
        if path.stat().st_nlink != 1 or read_regular_file(path, max_bytes=MAX_WORK_BYTES) != encoded:
            raise ValueError("original attempt checkpoint drift")
        return
    atomic_write_bytes(path, encoded)


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
         "evidence": completion_evidence(record) if record["status"] == "completed" else "",
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
                 "ordinary_release": False, "attempt_record": record}
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
                          closure: dict, action_id: str, token: str, domain: str,
                          before_dispatch=None, intent_metadata=None, validate_transport=None,
                          interpret_response=None):
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
        previous_raw = None
        if path.exists():
            if path.stat().st_nlink != 1:
                raise OSError("client state must be a single-link regular file")
            previous_raw = read_regular_file(path, max_bytes=MAX_JOURNAL_BYTES)
            previous = unique_json(previous_raw)
            if (not isinstance(previous, dict) or previous.get("schema") != JOURNAL_SCHEMA
                    or previous.get("subject_key") != subject_key
                    or previous.get("status") not in ("in_flight", "failed", "ambiguous", "completed", "pending")):
                raise ValueError("invalid persisted client attempt")
            client_causal_key(previous["current"])
        completed = completed_request_evidence(previous) if previous else {}
        if args.request_id in completed:
            receipt.update(dispatch_count=0, state="NOOP",
                           reason="COMPLETED_STABLE_REQUEST_ALREADY_RECORDED",
                           recorded_response_sha256=completed[args.request_id],
                           previous_status=previous["status"])
            closure.update(closing_readback(opener, args, action_id=action_id,
                                           completed_at=utc_now(), token=token, domain=domain))
            # A historical completion does not close a later unresolved attempt
            # for the same semantic subject. Preserve the current durable state.
            receipt["continuation_work"] = persist_successor_work(
                root, args, subject_key=subject_key, record=previous,
                closure=closure, action_id=action_id, domain=domain, previous=previous_work)
            return 20
        if len(completed) == MAX_COMPLETED_REQUESTS:
            raise ValueError("completion evidence limit reached; no request replay admitted")
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
                if "transport_receipt" in previous:
                    receipt["previous_transport_receipt"] = previous["transport_receipt"]
                closure.update(closing_readback(opener, args, action_id=action_id,
                                               completed_at=utc_now(), token=token, domain=domain))
                receipt["continuation_work"] = persist_successor_work(
                    root, args, subject_key=subject_key, record=previous,
                    closure=closure, action_id=action_id, domain=domain, previous=previous_work)
                return 1
        if previous is not None:
            preserve_attempt_evidence(root, previous, previous_raw)
        record = {"schema": JOURNAL_SCHEMA, "subject_key": subject_key,
                  "current": current, "status": "in_flight",
                  "request_id": args.request_id, "execution_id": action_id,
                  "completed_requests": completed,
                  "request_metadata": {"repository": f"{args.owner}/{args.repo}", "ref": args.ref,
                                       "operation": args.operation, "artifact_id": args.artifact_id}}
        if intent_metadata is not None:
            # Only the fixed operation supplies non-secret exact-source inputs.
            # Generic ingest payloads and credentials are never copied here.
            record["operation_binding"] = intent_metadata

        def save():
            raw = json.dumps(record, sort_keys=True).encode("utf-8")
            if len(raw) > MAX_JOURNAL_BYTES:
                raise ValueError("journal exceeds its bounded state limit; no witness discarded")
            atomic_write_bytes(path, raw)

        if before_dispatch is not None:
            before_dispatch()  # Fresh source admission under the existing journal lock.
        save()  # Crash or timeout after this point must never silently redispatch.
        receipt["dispatch_count"] = 1
        result = 1
        try:
            with opener.open(request, timeout=10) as response:
                raw = read_response_bytes(response)
                receipt.update(http_status=response.status,
                               response_sha256=hashlib.sha256(raw).hexdigest())
                _, transport = (interpret_response or interpret_dispatch_response)(
                    response, request=request, repository=f"{args.owner}/{args.repo}",
                    ref=args.ref, request_id=args.request_id,
                    response_text=raw.decode("utf-8"),
                )
                if validate_transport is not None:
                    validate_transport(transport)
                receipt.update(transport)
                if transport.get("schema") == "qikvrt_dispatch_transport_receipt_v1":
                    record["transport_receipt"] = transport
                    record["status"] = "pending"
                    result = 20
                else:
                    handler = transport.get("handler_result")
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
            receipt.update(
                dispatch_outcome=("UNKNOWN_REQUIRES_AUTHORITATIVE_READBACK"
                                  if record["status"] == "ambiguous" else "DENIED_OR_FAILED"),
                retry_policy="REOBSERVE_BEFORE_ANY_NEW_DISPATCH",
            )
            record["current"] = dict(current, error=digest(receipt))
        closure.update(closing_readback(opener, args, action_id=action_id,
                                       completed_at=utc_now(), token=token, domain=domain))
        record["closing_verification"] = closure
        if "response_sha256" in receipt:
            record["response_sha256"] = receipt["response_sha256"]
        if record["status"] == "completed":
            record["completed_requests"][args.request_id] = record["response_sha256"]
        save()  # Keep the lock through closure; a crash retains in-flight intent.
        receipt["continuation_work"] = persist_successor_work(
            root, args, subject_key=subject_key, record=record,
            closure=closure, action_id=action_id, domain=domain, previous=previous_work)
        return result


def interpret_dispatch_response(response, *, request, repository, ref, request_id,
                                response_text=None):
    """Keep asynchronous transport acceptance distinct from handler effects."""
    status = response.status
    if response_text is None:
        response_text = read_response(response)
    if status == 204:
        if response_text:
            raise ValueError("204 dispatch response must be empty")
        parsed = None
    else:
        parsed = unique_json(response_text.encode("utf-8"))
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


CONTINUATION_READY_DOCUMENT = (
    "mutation QikvrtReady($input:MarkPullRequestReadyForReviewInput!){"
    "markPullRequestReadyForReview(input:$input){pullRequest{id isDraft headRefOid}}}"
)


def continuation_tested_subject(get, run, token):
    """Read the immutable small CI subject using the original artifact transport."""
    import io
    import tempfile
    import zipfile
    from tools.qikvrt_self_host_container import actions_archive_download
    name = f"qikvrt-ci-tested-subject-{run['id']}-{run['run_attempt']}"
    artifacts = ruleset_collection(get("actions/runs/" + str(run["id"]) + "/artifacts?per_page=100"), "artifacts")
    found = [a for a in artifacts if a.get("name") == name and a.get("expired") is False]
    if len(found) != 1:
        raise ValueError("CONTINUATION_TESTED_SUBJECT_UNAVAILABLE")
    artifact = found[0]
    if (type(artifact.get("id")) is not int or artifact["id"] <= 0
            or type(artifact.get("size_in_bytes")) is not int or not 0 < artifact["size_in_bytes"] <= 16384
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(artifact.get("digest", "")))
            or artifact.get("workflow_run", {}).get("id") != run["id"]
            or artifact.get("workflow_run", {}).get("head_sha") != run["head_sha"]):
        raise ValueError("CONTINUATION_TESTED_ARTIFACT_BINDING_INVALID")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "tested.zip"
        actions_archive_download(artifact["id"], artifact["size_in_bytes"], path, token)
        raw = read_regular_file(path, max_bytes=16384)
    if "sha256:" + hashlib.sha256(raw).hexdigest() != artifact["digest"]:
        raise ValueError("CONTINUATION_TESTED_ARTIFACT_DIGEST_MISMATCH")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if (archive.namelist() != ["TESTED_SUBJECT.json"]
                or archive.getinfo("TESTED_SUBJECT.json").file_size > 4096):
            raise ValueError("CONTINUATION_TESTED_ARTIFACT_CONTENT_INVALID")
        return unique_json(archive.read("TESTED_SUBJECT.json"))


def continuation_result(args, token, *, write=False):
    """REST coordination of the original fixed GraphQL fallback; no merge.

    Provider evidence is read afresh. Learning changes verification order only;
    it never removes a gate or the fallback. The original durable journal owns
    the single POST and survives an unknown outcome or changed request ID.
    """
    from tools.qikvrt_workflow_executor import continuation_graph, continuation_frontier, load_repository_roles
    from tools.qikvrt_required_review_gate import (
        evaluate_required_review, resolve_required_code_owner,
    )
    if RULESET_REPOSITORY != load_repository_roles()["AUTHORITY"]:
        raise ValueError("CONTINUATION_AUTHORITY_MISMATCH")
    opener = urllib.request.build_opener(NoRedirectHandler())
    get = lambda path: ruleset_json_get(opener, token, path)
    result = {"schema": "qikvrt-continuation-rest/v1", "repository": RULESET_REPOSITORY,
              "pull_request": args.pull_request, "head_sha": args.expected_head,
              "tree_sha": args.expected_tree, "request_id": args.request_id,
              "dispatch_count": 0, "ready_verified": False, "merge_verified": False,
              "effect_ack_done": False, "ordinary_release": False}

    def source():
        main = get("branches/main")
        pr = get("pulls/" + str(args.pull_request))
        commit = get("git/commits/" + args.expected_head)
        current = ruleset_collection(get("actions/workflows/qikvrt_ci.yml/runs?head_sha="
                                     + args.expected_head + "&per_page=100"), "workflow_runs")
        if (main.get("commit", {}).get("sha") != args.expected_main_sha
                or pr.get("number") != args.pull_request or pr.get("state") != "open"
                or pr.get("merged") is not False or pr.get("base", {}).get("ref") != "main"
                or pr.get("base", {}).get("sha") != args.expected_main_sha
                or pr.get("base", {}).get("repo", {}).get("full_name") != RULESET_REPOSITORY
                or pr.get("head", {}).get("repo", {}).get("full_name") != RULESET_REPOSITORY
                or pr.get("head", {}).get("sha") != args.expected_head
                or commit.get("sha") != args.expected_head
                or commit.get("tree", {}).get("sha") != args.expected_tree
                or any(r.get("id") != args.ci_run_id and r.get("conclusion") not in {"action_required", "success", "skipped"}
                       for r in current)
                or type(pr.get("draft")) is not bool or not isinstance(pr.get("node_id"), str)):
            raise ValueError("CONTINUATION_SOURCE_DRIFT")
        return pr

    pr = source()
    binding = {"repository": RULESET_REPOSITORY, "pull_request": args.pull_request,
               "head_sha": args.expected_head, "tree_sha": args.expected_tree,
               "main_sha": args.expected_main_sha, "document_sha256": hashlib.sha256(
                   CONTINUATION_READY_DOCUMENT.encode()).hexdigest()}
    subject_key = digest({"operation": "markPullRequestReadyForReview", "repository": RULESET_REPOSITORY,
                          "pull_request": args.pull_request})
    run = get("actions/runs/" + str(args.ci_run_id))
    jobs = get("actions/runs/" + str(args.ci_run_id) + "/jobs?per_page=100")
    if (run.get("id") != args.ci_run_id
            or run.get("path") != ".github/workflows/qikvrt_ci.yml"
            or run.get("repository", {}).get("full_name") != RULESET_REPOSITORY
            or run.get("head_repository", {}).get("full_name") != RULESET_REPOSITORY
            or jobs.get("total_count") != len(jobs.get("jobs", []))
            or not 0 < len(jobs.get("jobs", [])) < 100):
        raise ValueError("CONTINUATION_EXACT_CI_EVIDENCE_REQUIRED")
    tested = continuation_tested_subject(get, run, token)
    graph = continuation_graph(run, jobs["jobs"], tested)
    if (not graph.get("tested_subject") or tested.get("head_sha") != args.expected_head
            or tested.get("tree_sha") != args.expected_tree):
        raise ValueError("CONTINUATION_TESTED_SUBJECT_MISMATCH")
    result["graph"] = graph
    reviews = ruleset_collection(get("pulls/" + str(args.pull_request) + "/reviews?per_page=100"))
    review = evaluate_required_review(pr, [], reviews,
        required_code_owner=resolve_required_code_owner(RULESET_REPOSITORY, pr_author=pr["user"]["login"]))
    result["review_gate"] = review["gate_state"]
    result["graph"] = continuation_frontier(graph, pr, review)
    result["ready_verified"] = pr["draft"] is False
    if not write or result["ready_verified"]:
        result["state"] = "READY_VERIFIED" if result["ready_verified"] else "PLAN_ONLY"
        # A GET stays read-only. An accepted POST may close the original
        # unknown attempt from this independent readback without another
        # GraphQL mutation. Retain the original response (if any) separately.
        root = Path(args.state_dir).absolute()
        if write and result["ready_verified"] and root.exists():
            for parent in (root, *root.parents):
                if parent.is_symlink():
                    raise OSError("client state directory must not traverse a symlink")
            if root.stat().st_mode & 0o022:
                raise OSError("client state directory must not be group/world writable")
            path = root / (subject_key + ".json")
            with _exclusive_integrity_lock(root):
                _assert_safe_target(path)
                if path.exists():
                    if path.stat().st_nlink != 1:
                        raise OSError("client state must be single-link")
                    raw = read_regular_file(path, max_bytes=MAX_JOURNAL_BYTES)
                    record = unique_json(raw)
                    if (record.get("schema") != JOURNAL_SCHEMA or record.get("subject_key") != subject_key):
                        raise ValueError("invalid original continuation attempt")
                    if (record.get("operation_binding") == binding
                            and record.get("status") in {"in_flight", "ambiguous", "pending"}):
                        preserve_attempt_evidence(root, record, raw)
                        record.update(status="completed", completion_basis="INDEPENDENT_PR_READY_READBACK",
                                      effect_readback_sha256=digest(pr), mutation_attribution_verified=False)
                        atomic_write_bytes(path, json.dumps(record, sort_keys=True).encode())
                        action_id = "ready-readback:" + args.request_id + ":" + utc_now()
                        domain = client_end_of_action_domain()
                        closure = closing_readback(opener, args, action_id=action_id,
                            completed_at=utc_now(), token=token, domain=domain)
                        result["continuation_work"] = persist_successor_work(root, args, subject_key=subject_key,
                            record=record, closure=closure, action_id=action_id, domain=domain,
                            previous=load_previous_work(root))
                        result["original_attempt_recovered"] = True
        return result
    if "graphql-fallback" not in result["graph"]["frontier"]:
        raise ValueError("CONTINUATION_GREEN_CI_AND_OWNER_REVIEW_REQUIRED")
    from tools.ai_handoff import github_graphql_fallback_allowed
    policy = unique_json((ROOT / "policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json").read_bytes())
    if not github_graphql_fallback_allowed({
            "subject": {"repository": RULESET_REPOSITORY}, "method": "POST",
            "operation": "markPullRequestReadyForReview", "endpoint": "https://api.github.com/graphql",
            "fallback_reason": "REST_OPERATION_UNAVAILABLE", "rest_effect_state": "NOT_ATTEMPTED",
            "owner_decision_sha256": policy.get("client_continuation", {}).get("github_fallback", {}).get("decision_sha256")}, policy):
        raise ValueError("CONTINUATION_OWNER_FALLBACK_DECISION_REQUIRED")

    body = json.dumps({"query": CONTINUATION_READY_DOCUMENT,
        "variables": {"input": {"pullRequestId": pr["node_id"],
                                  "clientMutationId": args.request_id}}}, separators=(",", ":")).encode()
    request = urllib.request.Request("https://api.github.com/graphql", data=body,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"}, method="POST")

    def interpret(response, **kwargs):
        parsed = unique_json(kwargs["response_text"].encode())
        if response.status != 200 or not isinstance(parsed, dict) or parsed.get("errors"):
            raise ValueError("CONTINUATION_GRAPHQL_RESPONSE_UNVERIFIED")
        observed = parsed.get("data", {}).get("markPullRequestReadyForReview", {}).get("pullRequest", {})
        if (observed.get("id") != pr["node_id"] or observed.get("isDraft") is not False
                or observed.get("headRefOid") != args.expected_head):
            raise ValueError("CONTINUATION_GRAPHQL_TARGET_MISMATCH")
        live = source()  # Independent REST read, even after HTTP200 GraphQL success.
        if live["draft"] is not False:
            raise ValueError("CONTINUATION_READY_READBACK_FAILED")
        result["ready_verified"] = True
        result["graph"] = continuation_frontier(graph, live, review)
        return 20, {"schema": "qikvrt-pr-ready-readback/v1", "ready_readback_sha256": digest(live),
                    "handler_result": {"effect_state": "EFFECT_ACK_DONE", "scope": "PR_READY_ONLY"}}

    domain = client_end_of_action_domain()
    def admission():
        live = source()
        fresh = get("actions/runs/" + str(args.ci_run_id))
        if any(fresh.get(k) != run.get(k) for k in ("id", "head_sha", "run_attempt", "status", "conclusion")):
            raise ValueError("CONTINUATION_CI_CHANGED_BEFORE_MUTATION")
        fresh_reviews = ruleset_collection(get("pulls/" + str(args.pull_request) + "/reviews?per_page=100"))
        fresh_review = evaluate_required_review(live, [], fresh_reviews,
            required_code_owner=resolve_required_code_owner(RULESET_REPOSITORY, pr_author=live["user"]["login"]))
        if fresh_review["gate_state"] != "success":
            raise ValueError("CONTINUATION_REVIEW_CHANGED_BEFORE_MUTATION")
    dispatch_with_journal(opener, request, args,
        subject_key=subject_key,
        receipt=result, closure={}, action_id="ready:" + args.request_id + ":" + utc_now(),
        token=token, domain=domain, before_dispatch=admission, intent_metadata=binding,
        interpret_response=interpret)
    result["state"] = "READY_VERIFIED" if result["ready_verified"] else "HOLD_READBACK_REQUIRED"
    return result


def ruleset_authority_result(args, token):
    """Shared fixed-writer controller for CLI and the admitted REST adapter.

    The existing private journal fences the POST before transport, including
    process loss. Changing request IDs, Main or writer versions cannot replay
    an unresolved administration request. No credential enters the journal.
    """
    # The pinned operation carrier cannot assign a second Authority.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.qikvrt_workflow_executor import load_repository_roles
    if RULESET_REPOSITORY != load_repository_roles()["AUTHORITY"]:
        raise ValueError("Ruleset carrier and canonical Authority policy disagree")
    opener = urllib.request.build_opener(NoRedirectHandler())
    get = lambda path: ruleset_json_get(opener, token, path)
    domain = client_end_of_action_domain()
    action_id = "ruleset:" + args.request_id + ":" + utc_now()
    closure = {}
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
            request = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json",
                "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"}, method="POST",
            )
            receipt.update(dispatch_url=url, request_sha256=hashlib.sha256(body).hexdigest())
            def fresh_source():
                ruleset_main_readback(get, args.expected_main_sha)
                verify_ruleset_writer(get(f"contents/{RULESET_WORKFLOW_PATH}?ref={args.expected_main_sha}"), writer_blob)
            subject_key = digest({"operation": "ruleset_authority_dispatch",
                "repository": RULESET_REPOSITORY, "ref": "main", "workflow": RULESET_WORKFLOW_PATH})
            code = dispatch_with_journal(opener, request, args, subject_key=subject_key,
                receipt=receipt, closure=closure, action_id=action_id, token=token, domain=domain,
                before_dispatch=fresh_source, intent_metadata={"main_sha": args.expected_main_sha,
                    "workflow_blob_sha": writer_blob, "expected_ruleset_sha256": post_sha256,
                    "dispatch_url": url, "request_sha256": hashlib.sha256(body).hexdigest()})
            if "error_category" in receipt:
                receipt["failure_class"] = receipt["error_category"]
            if receipt.get("http_status") in (401, 403) and receipt["dispatch_count"]:
                receipt["dispatch_outcome"] = "DENIED"
            receipt["next_checks"] = [
                "IDENTIFY_RUN_BY_REPOSITORY_WORKFLOW_EVENT_REF_AND_EXACT_HEAD",
                "RUN_RULESET_AUTHORITY_READBACK_WITH_VERIFIED_RUN_ID",
                "REOBSERVE_CURRENT_HEAD_CODE_OWNER_GATE_AND_NATIVE_REVIEW",
            ]
            return code, receipt

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
        observed_digest = None
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
            observed_digest = hashlib.sha256(canonical).hexdigest()
        branch = ruleset_main_readback(get, args.expected_main_sha)
        if ruleset_run_binding(get(f"actions/runs/{run_id}"), run_id, args.expected_main_sha) != binding:
            raise ValueError("workflow run drifted during readback")
        effect = execution and observed_digest == post_sha256 and branch.get("protected") is True
        receipt.update(
            workflow_run_id=run_id, run_attempt=run["run_attempt"],
            execution_verified=execution, main_protected=branch.get("protected") is True,
            ruleset_id=ruleset_id, observed_ruleset_sha256=observed_digest,
            expected_ruleset_sha256=post_sha256, ruleset_effect_verified=effect,
            readback_state="RULESET_POSTCONDITION_VERIFIED" if effect else "RULESET_EFFECT_UNVERIFIED",
            mutation_attribution_verified=False, native_review_verified=False,
            verification_scope="RULESET_POSTCONDITION_ONLY_NOT_MERGE_OR_RELEASE",
        )
        return (0 if effect else 20), receipt
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            RuntimeError, ValueError, TypeError, KeyError, AttributeError,
            RecursionError, IntegrityIsolationError) as exc:
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
        return 1, receipt
    finally:
        if not closure:
            closure.update(closing_readback(opener, args, action_id=action_id,
                                           completed_at=utc_now(), token=token, domain=domain))
        receipt["closing_verification"] = closure


def ruleset_authority_operation(args, token):
    """Preserve the original CLI and receipt format over the shared controller."""
    code, receipt = ruleset_authority_result(args, token)
    stream = sys.stderr if code == 1 and receipt.get("state") != "NOOP" else sys.stdout
    if stream is sys.stderr:
        print("BLOCK Ruleset operation failed; inspect the non-secret receipt", file=stream)
    print(json.dumps(receipt, sort_keys=True), file=stream)
    return code


def recorded_ruleset_run(args):
    """Recover only this original intent's run ID, without writes or a POST."""
    root = Path(args.state_dir).absolute()
    if any(parent.is_symlink() for parent in (root, *root.parents)):
        raise OSError("private Ruleset state must not traverse symlinks")
    key = digest({"operation": "ruleset_authority_dispatch", "repository": RULESET_REPOSITORY,
                  "ref": "main", "workflow": RULESET_WORKFLOW_PATH})
    path = root / (key + ".json")
    _assert_safe_target(path)
    if path.stat().st_nlink != 1:
        raise OSError("private Ruleset state must be single-link")
    record = unique_json(read_regular_file(path, max_bytes=MAX_JOURNAL_BYTES))
    blob, post = RULESET_WRITER_VERSIONS[args.ruleset_writer_version or DEFAULT_RULESET_WRITER_VERSION]
    binding = record.get("operation_binding") if isinstance(record, dict) else None
    if (not isinstance(binding, dict) or record.get("schema") != JOURNAL_SCHEMA
            or record.get("subject_key") != key or record.get("request_id") != args.request_id
            or record.get("status") not in {"in_flight", "pending", "ambiguous", "failed", "completed"}
            or binding.get("main_sha") != args.expected_main_sha or binding.get("workflow_blob_sha") != blob
            or binding.get("expected_ruleset_sha256") != post):
        raise ValueError("original Ruleset journal binding mismatch")
    transport = record.get("transport_receipt", {})
    run_id = transport.get("workflow_run_id")
    if type(run_id) is int and run_id > 0:
        if (transport.get("schema") != "qikvrt_dispatch_transport_receipt_v1"
                or transport.get("repository") != RULESET_REPOSITORY or transport.get("ref") != "main"
                or transport.get("request_id") != args.request_id
                or transport.get("run_url") != f"https://api.github.com/repos/{RULESET_REPOSITORY}/actions/runs/{run_id}"
                or transport.get("html_url") != f"https://github.com/{RULESET_REPOSITORY}/actions/runs/{run_id}"):
            raise ValueError("original Ruleset transport identity mismatch")
        return run_id, None
    return None, {"schema": "qikvrt_ruleset_authority_client_receipt_v1", "operation": args.operation,
        "repository": RULESET_REPOSITORY, "ref": "main", "main_sha": args.expected_main_sha,
        "request_id": args.request_id, "workflow_path": RULESET_WORKFLOW_PATH, "workflow_blob_sha": blob,
        "expected_ruleset_sha256": post, "writer_bytes_verified": True,
        "writer_verification_scope": "ORIGINAL_PRE_DISPATCH_IMMUTABLE_BYTES_ONLY",
        "workflow_run_id": None, "dispatch_count": 0, "journal_status": record["status"],
        "readback_state": "ORIGINAL_INTENT_RETAINED_RUN_ID_UNRESOLVED",
        "execution_verified": False, "ruleset_effect_verified": False,
        "effect_state": "EFFECT_ACK_CONTINUE", "ordinary_release": False,
        "retry_policy": "AUTHORITATIVE_READBACK_ONLY_NO_POST"}


def bound_ruleset_rest_response(value, args):
    """Bind a remote observation to this request; never infer global release."""
    result = value.get("handler_result") if isinstance(value, dict) else None
    version = args.ruleset_writer_version or DEFAULT_RULESET_WRITER_VERSION
    blob, post = RULESET_WRITER_VERSIONS[version]
    if (not isinstance(result, dict) or value.get("schema") != "qikvrt-ruleset-authority-rest/v1"
            or value.get("api_contract_version") != API_CONTRACT_VERSION
            or value.get("ordinary_release") is not False or value.get("effect_ack_done") is not False
            or result.get("operation") != args.operation or result.get("repository") != RULESET_REPOSITORY
            or result.get("request_id") != args.request_id or result.get("ref") != "main"
            or result.get("main_sha") != args.expected_main_sha
            or result.get("workflow_path") != RULESET_WORKFLOW_PATH
            or result.get("workflow_blob_sha") != blob or result.get("expected_ruleset_sha256") != post
            or result.get("writer_bytes_verified") is not True
            or result.get("effect_state") != "EFFECT_ACK_CONTINUE" or result.get("ordinary_release") is not False):
        raise ValueError("remote Ruleset REST response binding mismatch")
    if (args.operation == "ruleset_authority_readback" and args.ruleset_run_id is not None
            and result.get("workflow_run_id") != int(args.ruleset_run_id)):
        raise ValueError("remote Ruleset run binding mismatch")
    if (type(result.get("execution_verified")) is not bool
            or type(result.get("ruleset_effect_verified")) is not bool):
        raise ValueError("remote Ruleset verification predicates invalid")
    if args.operation == "ruleset_authority_dispatch" and (
            result["execution_verified"] or result["ruleset_effect_verified"]):
        raise ValueError("dispatch acceptance cannot establish a Ruleset effect")
    if result["ruleset_effect_verified"] and (
            result["execution_verified"] is not True or result.get("main_protected") is not True
            or result.get("observed_ruleset_sha256") != post
            or result.get("readback_state") != "RULESET_POSTCONDITION_VERIFIED"
            or type(result.get("workflow_run_id")) is not int or result["workflow_run_id"] <= 0):
        raise ValueError("remote Ruleset postcondition evidence incomplete")
    return result


def ruleset_mesh_operation(args, token):
    """Use the same fixed operation through an explicitly selected Mesh REST origin.

    The caller token is sent only to that origin. The server's protected
    Authority binding supplies its own GitHub credential and original writer.
    """
    opener = urllib.request.build_opener(NoRedirectHandler())
    url = args.base_url + f"/repos/{RULESET_REPOSITORY}/qikvrt/ruleset-authority"
    action_id = "ruleset-rest:" + args.request_id + ":" + utc_now()
    domain, closure = client_end_of_action_domain(), {}
    receipt, code = {"dispatch_count": 0, "effect_state": "EFFECT_ACK_CONTINUE", "ordinary_release": False}, 1
    try:
        fields = {"request_id": args.request_id, "expected_main_sha": args.expected_main_sha,
                  "writer_version": args.ruleset_writer_version or DEFAULT_RULESET_WRITER_VERSION}
        headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
        if args.operation == "ruleset_authority_readback":
            query = {**fields, **({"run_id": args.ruleset_run_id} if args.ruleset_run_id is not None else {})}
            request = urllib.request.Request(url + "?" + urlencode(query),
                                             headers=headers, method="GET")
            with opener.open(request, timeout=10) as response:
                if response.status not in (200, 202):
                    raise ValueError("remote Ruleset readback status invalid")
                observed = unique_json(read_response_bytes(response))
                result = bound_ruleset_rest_response(observed, args)
                receipt["remote_readback"] = observed
                code = 0 if result.get("ruleset_effect_verified") is True else 20
        else:
            body = {**fields, "schema": "qikvrt-ruleset-authority-rest/v1", "effect_accepted": True}
            request = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
            code = dispatch_with_journal(opener, request, args,
                subject_key=digest({"url": url, "operation": args.operation, "repository": RULESET_REPOSITORY}),
                receipt=receipt, closure=closure, action_id=action_id, token=token, domain=domain,
                validate_transport=lambda value: bound_ruleset_rest_response(value, args),
                intent_metadata={"main_sha": args.expected_main_sha, "writer_version": fields["writer_version"]})
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError,
            KeyError, RuntimeError, IntegrityIsolationError) as exc:
        receipt["error_category"] = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            receipt["http_status"] = exc.code
            exc.close()
    finally:
        if not closure:
            closure.update(closing_readback(opener, args, action_id=action_id,
                                           completed_at=utc_now(), token=token, domain=domain))
    print(json.dumps({"schema": "qikvrt-ruleset-rest-client/v1", "result": receipt,
                      "closing_verification": closure, "effect_state": "EFFECT_ACK_CONTINUE",
                      "ordinary_release": False}, sort_keys=True))
    return code


def amo_candidate_readback(get, args):
    """The direct Owner path signs the current PR, without a prior Main merge."""
    pr = get("pulls/523")
    if (not isinstance(pr, dict) or pr.get("state") != "open"
            or pr.get("head", {}).get("sha") != args.amo_expected_head
            or pr.get("head", {}).get("ref") != args.ref
            or pr.get("head", {}).get("repo", {}).get("full_name") != RULESET_REPOSITORY
            or pr.get("base", {}).get("ref") != "main"
            or pr.get("base", {}).get("repo", {}).get("full_name") != RULESET_REPOSITORY):
        raise ValueError("AMO_CURRENT_OWNER_PR_REQUIRED")
    commit = get("git/commits/" + args.amo_expected_head)
    if (not isinstance(commit, dict) or commit.get("sha") != args.amo_expected_head
            or commit.get("tree", {}).get("sha") != args.amo_expected_tree):
        raise ValueError("AMO_CURRENT_HEAD_TREE_REQUIRED")


def amo_workflow_readback(get, args):
    writer = get("contents/" + AMO_WORKFLOW_PATH + "?ref=" + args.amo_expected_head)
    if (not isinstance(writer, dict) or writer.get("type") != "file"
            or writer.get("path") != AMO_WORKFLOW_PATH
            or writer.get("sha") != args.amo_workflow_blob
            or writer.get("encoding") != "base64"
            or type(writer.get("size")) is not int or not 0 < writer["size"] <= 128 * 1024
            or not isinstance(writer.get("content"), str) or len(writer["content"]) > 256 * 1024):
        raise ValueError("AMO_REVIEWED_WORKFLOW_REQUIRED")
    raw = base64.b64decode("".join(writer["content"].splitlines()), validate=True)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw,
                        usedforsecurity=False).hexdigest()
    if len(raw) != writer["size"] or blob != args.amo_workflow_blob:
        raise ValueError("AMO_REVIEWED_WORKFLOW_BYTES_REQUIRED")


def firefox_amo_operation(args, token):
    """Reuse the REST transport/journal; never export secrets or grant a review.

    This is a client operation, not a new server or an activation of ChatGPT's
    connector registry. Its caller must already have a securely bound token.
    """
    opener = urllib.request.build_opener(NoRedirectHandler())
    get = lambda path: ruleset_json_get(opener, token, path)
    domain = client_end_of_action_domain()
    action_id = "client:" + args.request_id + ":" + utc_now()
    receipt = {"schema": "qikvrt-firefox-amo-client/1", "operation": args.operation,
               "repository": RULESET_REPOSITORY, "dispatch_count": 0,
               "credential_values_read": False, "configuration_status": "NOT_INSPECTED",
               "job_credential_delivery": "NOT_OBSERVED", "amo_authentication_verified": False,
               "execution_verified": False, "signing_verified": False,
               "native_independent_review": False, "main_merge_verified": False}
    closure = {}
    result = 1
    try:
        if args.operation == "firefox_amo_access":
            metadata = []
            for name in AMO_SECRET_NAMES:
                observed = get("actions/secrets/" + name)
                if (not isinstance(observed, dict) or observed.get("name") != name
                        or any(not isinstance(observed.get(field), str)
                               or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", observed[field])
                               for field in ("created_at", "updated_at"))):
                    raise ValueError("AMO_SECRET_METADATA_UNVERIFIED")
                # Copy only known metadata, never an unexpected provider field.
                metadata.append({field: observed[field] for field in ("name", "created_at", "updated_at")})
            receipt.update(configuration_status="REPOSITORY_METADATA_OBSERVED",
                           configuration_scope="REPOSITORY_SECRET_METADATA_ONLY", secrets=metadata)
            result = 0
        else:
            from tools.qikvrt_self_host import firefox_amo_input
            from tools.qikvrt_workflow_executor import amo_request
            _xpi, subject = firefox_amo_input(ROOT, args.amo_expected_head, args.amo_expected_tree)
            if subject["unsigned_xpi_sha256"] != amo_request(ROOT)["unsigned_xpi_sha256"]:
                raise ValueError("AMO_OWNER_PACKAGE_CHANGED")
            amo_candidate_readback(get, args)
            amo_workflow_readback(get, args)
            body = {"ref": args.ref, "return_run_details": True, "inputs": {
                "amo_sign_unlisted": True, "amo_expected_head": args.amo_expected_head,
                "amo_expected_tree": args.amo_expected_tree,
                "amo_previous_run_id": args.amo_previous_run_id or "0",
                "amo_executor_run_id": "0", "amo_readback_only": False}}
            url = f"https://api.github.com/repos/{RULESET_REPOSITORY}/actions/workflows/qikvrt_ci.yml/dispatches"
            request = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                         "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
            receipt.update(source_head=args.amo_expected_head, source_tree=args.amo_expected_tree,
                           unsigned_xpi_sha256=subject["unsigned_xpi_sha256"],
                           workflow_blob_sha=args.amo_workflow_blob, actor_admission="NATIVE_DIRECT_OWNER_CHECK_REQUIRED")
            # Unrelated HEAD/TREE/ref/request-id changes must not replay a
            # pending/failed signing attempt for this official add-on/version.
            subject_key = digest({"operation": "firefox_amo_dispatch", "repository": RULESET_REPOSITORY,
                                  "extension_id": subject["extension_id"],
                                  "extension_version": subject["extension_version"]})
            result = dispatch_with_journal(opener, request, args, subject_key=subject_key,
                receipt=receipt, closure=closure, action_id=action_id, token=token, domain=domain,
                before_dispatch=lambda: amo_candidate_readback(get, args),
                intent_metadata={"source_head": args.amo_expected_head, "source_tree": args.amo_expected_tree,
                    "workflow_blob_sha": args.amo_workflow_blob,
                    "unsigned_xpi_sha256": subject["unsigned_xpi_sha256"], "dispatch_url": url,
                    "request_sha256": hashlib.sha256(request.data).hexdigest(), "request_body": body})
            receipt["execution_verified"] = False
            receipt["next_checks"] = ["VERIFY_NATIVE_RUN_EVENT_REF_HEAD_TREE_AND_OWNER_ACTOR",
                "READ_ORIGINAL_AMO_JOURNAL_RECEIPT_AND_SIGNED_XPI_BYTES",
                "VERIFY_DEFAULT_POLICY_FIREFOX_ACTIVATION_AND_PERSISTENT_RESTART"]
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            RuntimeError, ValueError, KeyError, TypeError, AttributeError, IntegrityIsolationError) as exc:
        receipt["failure_class"] = type(exc).__name__
        if isinstance(exc, urllib.error.HTTPError):
            receipt["http_status"] = exc.code
        # Provider exception messages/bodies can contain credentials.
        print("BLOCK AMO client operation; inspect the non-secret receipt", file=sys.stderr)
    finally:
        if not closure:
            closure.update(closing_readback(opener, args, action_id=action_id,
                                           completed_at=utc_now(), token=token, domain=domain))
    print(json.dumps({"schema": "qikvrt-firefox-amo-client-readback/1", "dispatch": receipt,
                      "closing_verification": closure, "effect_ack_done": False,
                      "ordinary_release": False}, sort_keys=True))
    return result if closure["valid"] else 1


def _github_readback(repository: str, path: str, *, token: str, opener,
                     accept: str, max_bytes: int) -> tuple[str, str]:
    """One bounded GET through the existing no-redirect read transport."""
    if len(repository.split("/")) != 2 or not all(
        SAFE_REPOSITORY_COMPONENT.fullmatch(part) and part not in (".", "..") for part in repository.split("/")
    ):
        raise ValueError("unsafe repository scope")
    if not re.fullmatch(r"(?:commits/[A-Za-z0-9_.-]+|git/(?:trees|blobs|commits)/[0-9a-f]{40})(?:\?recursive=1)?", path):
        raise ValueError("readback path outside the bounded GitHub GET contract")
    if path.startswith("commits/") and ".." in path:
        raise ValueError("unsafe commit ref")
    headers = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repository}/{path}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with (opener or urllib.request.build_opener(NoRedirectHandler())).open(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError("readback requires HTTP 200")
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("API readback exceeds its bounded response limit")
        raw = data.decode("utf-8")
    return raw, url


def github_json_get(repository: str, path: str, *, token: str = "", opener=None) -> dict:
    """Bounded GET-only JSON readback, with exact received-byte provenance."""
    raw, url = _github_readback(repository, path, token=token, opener=opener,
                                accept="application/vnd.github+json", max_bytes=MAX_RESPONSE_BYTES)
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


def github_commit_identity_get(repository: str, ref: str, *, token: str = "", opener=None) -> dict:
    """Resolve a ref without downloading diffs, then read its immutable tree.

    Both original response digests are retained. Ref resolution is not a review,
    effect grant or proof of a running consumer. No full-diff fallback is used.
    """
    raw, url = _github_readback(repository, "commits/" + ref, token=token, opener=opener,
                                accept="application/vnd.github.sha", max_bytes=41)
    head = raw.removesuffix("\n")
    if not SHA1_HEX.fullmatch(head):
        raise ValueError("invalid commit identity response")
    source = github_json_get(repository, "git/commits/" + head, token=token, opener=opener)
    doc = source["document"]
    tree = doc.get("tree", {}).get("sha") if isinstance(doc.get("tree"), dict) else None
    if doc.get("sha") != head or not isinstance(tree, str) or not SHA1_HEX.fullmatch(tree):
        raise ValueError("immutable commit/tree identity mismatch")
    return {**source, "document": {"sha": head, "commit": {"tree": {"sha": tree}}},
            "ref_resolution": {"source_url": url, "head": head,
                               "response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}}

def static_mesh_operation(args, token):
    """One original S1 request, no retries and no caller-supplied server paths."""
    mode = args.operation.removeprefix("static_").replace("_", "-")
    value = {"schema": "qikvrt-static-delivery-rest/v1", "mode": mode,
             "request_id": args.request_id, "expected_implementation_sha256": args.static_implementation_sha256,
             "binding_sha256": args.static_binding_sha256, "static_file_sha256": args.expected_sha256}
    url = args.base_url + f"/repos/{args.owner}/{args.repo}/qikvrt/static-delivery"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if mode == "upload":
        value.update(expected_static_sha256=args.static_previous_sha256, effect_accepted=True)
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=json.dumps(value).encode(), headers=headers, method="POST")
    else:
        url += "?" + urlencode(value)
        request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.build_opener(NoRedirectHandler()).open(request, timeout=120) as response:
            if response.geturl() != url or response.status != 200:
                raise ValueError("unverified response")
            result = unique_json(read_response_bytes(response))
        if (not isinstance(result, dict) or result.get("schema") != value["schema"]
                or result.get("mode") != mode or result.get("request_id") != args.request_id
                or result.get("implementation_sha256") != args.static_implementation_sha256
                or result.get("binding_sha256") != args.static_binding_sha256
                or result.get("static_file_sha256") != args.expected_sha256
                or result.get("status") != "VERIFIED" or result.get("effect_ack_done") is not False
                or not isinstance(result.get("handler_result"), dict)):
            raise ValueError("unbound response")
        handler = result["handler_result"]
        if mode in {"upload", "reconcile"} and (handler.get("state") != "FILE_BYTES_VERIFIED"
                or handler.get("sha256") != args.expected_sha256):
            raise ValueError("file effect unverified")
        if mode == "public-readback" and handler.get("state") != "PUBLIC_STATIC_BYTES_VERIFIED":
            raise ValueError("public effect unverified")
        if mode == "public-readback":
            observations = handler.get("observations")
            if (not isinstance(observations, list) or len(observations) != 2
                    or {x.get("url") for x in observations if isinstance(x, dict)} != {
                        "https://raumzeitterminal.de/", "https://www.raumzeitterminal.de/"}
                    or any(not isinstance(x, dict) or x.get("verified") is not True
                           or x.get("status") != 200 or x.get("sha256") != args.expected_sha256
                           for x in observations)):
                raise ValueError("exact public observations missing")
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, urllib.error.URLError):
        print(json.dumps({"schema": value["schema"], "mode": mode, "request_id": args.request_id,
                          "state": "HOLD_STATIC_REST_OUTCOME_UNVERIFIED", "retry_permitted": False,
                          "next_operation": "static_reconcile" if mode == "upload" else "readback",
                          "effect_ack_done": False}, sort_keys=True))
        return 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8766")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--operation", choices=["ingest", "verify", "stage", "release_status", *sorted(RULESET_OPERATIONS), *sorted(AMO_OPERATIONS), *sorted(STATIC_OPERATIONS)], default="ingest")
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
    ap.add_argument("--ruleset-via-mesh", action="store_true",
                    help="Use the fixed Ruleset REST route at the explicitly configured Mesh base URL")
    ap.add_argument("--static-implementation-sha256", help="Independently obtained static REST implementation digest")
    ap.add_argument("--static-binding-sha256", help="Protected existing VPS binding digest; no credential/path upload")
    ap.add_argument("--static-previous-sha256", help="Fresh remote index.html hash, or ABSENT after original SSH readback")
    ap.add_argument("--amo-expected-head", help="Exact current PR523 commit for direct Owner signing")
    ap.add_argument("--amo-expected-tree", help="Exact current PR523 tree for direct Owner signing")
    ap.add_argument("--amo-workflow-blob", help="Independently reviewed qikvrt_ci.yml Git blob SHA-1")
    ap.add_argument("--amo-previous-run-id", help="Prior actual signing run; existing producer resolves its original journal")
    ap.add_argument("--state-dir", default=os.environ.get("QIKVRT_API_CLIENT_STATE_DIR", str(Path.home() / ".local/state/qikvrt/api-client")), help="Private persistent non-secret attempt metadata")
    ap.add_argument("--retry-evidence-file", help="New failure-bound subject/error/cause/capability digests; observation clocks do not admit retry")
    args = ap.parse_args()
    if args.ruleset_via_mesh and args.operation not in RULESET_OPERATIONS:
        ap.error("--ruleset-via-mesh requires a Ruleset operation")

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
    host = parsed_base.hostname
    if ":" in host:
        host = "[" + host + "]"
    default_port = 443 if parsed_base.scheme == "https" else 80
    port = "" if parsed_base.port in (None, default_port) else f":{parsed_base.port}"
    args.base_url = f"{parsed_base.scheme}://{host}{port}"
    if args.dry_run == "false":
        if not args.accept_effect:
            ap.error("--accept-effect is required when --dry-run=false")

    static_pins = (args.static_implementation_sha256, args.static_binding_sha256)
    if args.operation in STATIC_OPERATIONS:
        if (args.base_url == "https://api.github.com" or f"{args.owner}/{args.repo}" != RULESET_REPOSITORY
                or any(not isinstance(p, str) or not re.fullmatch(r"[0-9a-f]{64}", p)
                       for p in (*static_pins, args.expected_sha256))):
            ap.error("Static operations require explicit Mesh origin, Authority and lowercase implementation/target/page pins")
        if (args.payload_file or args.remote_evidence_file or args.state_run_id or args.return_run_details
                or args.expected_main_sha or args.ruleset_run_id or args.ruleset_writer_version
                or any((args.amo_expected_head, args.amo_expected_tree, args.amo_workflow_blob, args.amo_previous_run_id))):
            ap.error("Unrelated inputs and caller file paths are forbidden for static REST")
        if args.operation == "static_upload":
            prior = args.static_previous_sha256
            if (args.dry_run != "false" or not args.accept_effect or not isinstance(prior, str)
                    or prior != "ABSENT" and not re.fullmatch(r"[0-9a-f]{64}", prior)):
                ap.error("Static upload requires explicit effect acceptance and fresh predecessor hash or ABSENT")
        elif args.dry_run != "true" or args.accept_effect or args.static_previous_sha256 is not None:
            ap.error("Static readbacks require read-only defaults")
        return static_mesh_operation(args, token)
    if any(p is not None for p in (*static_pins, args.static_previous_sha256)):
        ap.error("Static binding arguments require a static operation")
    amo_bindings = (args.amo_expected_head, args.amo_expected_tree,
                    args.amo_workflow_blob, args.amo_previous_run_id)
    if args.operation in AMO_OPERATIONS:
        if (args.base_url != "https://api.github.com"
                or f"{args.owner}/{args.repo}" != RULESET_REPOSITORY):
            ap.error("AMO operations require the fixed Authority at https://api.github.com")
        if len(token) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in token):
            ap.error("AMO credential must be bounded printable ASCII without whitespace")
        if (args.payload_file or args.remote_evidence_file or args.expected_sha256
                or args.state_run_id is not None or args.return_run_details
                or args.artifact_id != "qikvrt_artifact" or args.expected_main_sha is not None
                or args.ruleset_run_id is not None or args.ruleset_writer_version is not None):
            ap.error("Mesh/Ruleset inputs are forbidden for AMO operations")
        if args.operation == "firefox_amo_dispatch":
            if args.dry_run != "false" or not args.accept_effect:
                ap.error("AMO dispatch requires --dry-run false --accept-effect")
            if any(not isinstance(v, str) or not SHA1_HEX.fullmatch(v) for v in amo_bindings[:3]):
                ap.error("AMO dispatch requires exact lowercase HEAD/TREE/workflow blob SHA-1 pins")
            if args.amo_previous_run_id is not None and not re.fullmatch(r"0|[1-9][0-9]{0,19}", args.amo_previous_run_id):
                ap.error("AMO previous run ID is invalid")
        elif any(v is not None for v in amo_bindings) or args.dry_run != "true" or args.accept_effect:
            ap.error("AMO metadata access uses read-only defaults without dispatch bindings")
        return firefox_amo_operation(args, token)
    if any(v is not None for v in amo_bindings):
        ap.error("AMO binding arguments require an AMO operation")
    if args.operation in RULESET_OPERATIONS:
        if len(token) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in token):
            ap.error("Ruleset credential must be bounded printable ASCII without whitespace")
        if args.ruleset_via_mesh and args.base_url == "https://api.github.com":
            ap.error("Mesh REST mode requires its own explicit origin")
        if not args.ruleset_via_mesh and args.base_url != "https://api.github.com":
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
        elif ((args.ruleset_run_id is None and not args.ruleset_via_mesh)
                or (args.ruleset_run_id is not None and (not re.fullmatch(r"[0-9]{1,32}", args.ruleset_run_id)
                    or int(args.ruleset_run_id) <= 0)) or args.dry_run != "true" or args.accept_effect):
            ap.error("Ruleset readback requires a positive --ruleset-run-id and read-only defaults")
        return ruleset_mesh_operation(args, token) if args.ruleset_via_mesh else ruleset_authority_operation(args, token)
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
