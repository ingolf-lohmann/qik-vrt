# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Persistent, fail-closed GitHub-Ref admission for the existing PR consumer.

The control commit is an immutable receipt. Every effecting Git-ref mutation uses
GitHub GraphQL updateRefs: control-ref CAS and target-ref CAS in one transaction.
This module grants no authority to a separate writer and never claims EAP ACK.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
from typing import Any, Mapping

SCHEMA = "qikvrt_fenced_writer_control_v1"
CONTROL_REF = "refs/qikvrt/pr-continuation/control"
ZERO = "0" * 40
LEASE_SECONDS = 3600
SHA = re.compile(r"^[0-9a-f]{40}$")
BOOTSTRAP_SCHEMA = "qikvrt_writer_bootstrap_request_v1"
BOOTSTRAP_INTENT_SCHEMA = "qikvrt_writer_bootstrap_intent_v1"
BOOTSTRAP_WORKFLOW = ".github/workflows/qikvrt_autonomous_pr_continuation.yml"
BOOTSTRAP_REF = "refs/heads/repair/writer-fencing-temdd-20261118"
BOOTSTRAP_PIN_PATHS = frozenset((
    "tools/qikvrt_autonomous_self_heal.py", "tools/qikvrt_writer_fence.py",
    BOOTSTRAP_WORKFLOW, "tests/test_qikvrt_writer_bootstrap.py",
))


class FenceBlocked(RuntimeError):
    """No permission to mutate; never auto-retry an ambiguous request."""


def _sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise FenceBlocked("FENCING_SHA_INVALID")
    return value


def _utc(value: str) -> dt.datetime:
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("missing timezone")
        return result.astimezone(dt.timezone.utc)
    except (ValueError, AttributeError, TypeError) as exc:
        raise FenceBlocked("FENCING_EXPIRY_INVALID") from exc


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _claim_identity(api: Any, run_id: int) -> str:
    if (os.environ.get("GITHUB_REPOSITORY") != api.repository or
        os.environ.get("GITHUB_RUN_ID") != str(run_id) or
        not os.environ.get("GITHUB_ACTOR")):
        raise FenceBlocked("GITHUB_ACTIONS_WRITER_IDENTITY_REQUIRED")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    if not attempt or not attempt.isdecimal() or int(attempt) <= 0:
        raise FenceBlocked("GITHUB_ACTIONS_WRITER_ATTEMPT_REQUIRED")
    return f"{os.environ['GITHUB_ACTOR']}:{run_id}:{attempt}"


def _git_tree(api: Any, sha: str) -> str:
    record = api.call("GET", "git/commits/" + _sha(sha))
    return _sha((record.get("tree") or {}).get("sha"))


def _read_control(api: Any) -> tuple[str, dict[str, Any]] | None:
    ref = api.ref(CONTROL_REF)
    if ref is None:
        return None
    if ref.get("ref") != CONTROL_REF:
        raise FenceBlocked("CONTROL_REF_IDENTITY_DRIFT")
    sha = _sha((ref.get("object") or {}).get("sha"))
    commit = api.call("GET", "git/commits/" + sha)
    message = commit.get("message")
    if not isinstance(message, str) or not message.startswith(SCHEMA + "\n"):
        raise FenceBlocked("CONTROL_COMMIT_SCHEMA_INVALID")
    try:
        value = json.loads(message.split("\n", 1)[1])
    except (ValueError, IndexError) as exc:
        raise FenceBlocked("CONTROL_COMMIT_INVALID") from exc
    if (not isinstance(value, dict) or value.get("schema") != SCHEMA or
        type(value.get("fencing_epoch")) is not int or value["fencing_epoch"] < 1 or
        value.get("state") not in ("CLAIMED", "PUBLISHED") or
        not isinstance(value.get("writer"), str) or not value["writer"] or
        not isinstance(value.get("work_unit"), str) or not value["work_unit"] or
        not isinstance(value.get("lease_expires_at"), str)):
        raise FenceBlocked("CONTROL_COMMIT_FIELDS_INVALID")
    for field in ("main_head", "main_tree", "source_head", "source_tree"):
        _sha(value.get(field))
    _utc(value["lease_expires_at"])
    return sha, value


def _control_commit(api: Any, *, prior_sha: str | None, base: str,
                    value: Mapping[str, Any], schema: str = SCHEMA) -> str:
    parent = _sha(prior_sha or base)
    expected_tree = _git_tree(api, parent)
    message = schema + "\n" + json.dumps(value, sort_keys=True, separators=(",", ":"))
    response = api.call("POST", "git/commits", {
        "message": message, "tree": expected_tree, "parents": [parent],
    })
    sha = _sha(response.get("sha"))
    observed = api.call("GET", "git/commits/" + sha)
    if (observed.get("message") != message or
        (observed.get("tree") or {}).get("sha") != expected_tree or
        [x.get("sha") for x in observed.get("parents", [])] != [parent]):
        raise FenceBlocked("CONTROL_COMMIT_READBACK_MISMATCH")
    return sha


def acquire(api: Any, plan: Mapping[str, Any], run_id: int) -> dict[str, Any]:
    """Atomic durable ownership plus legacy receipt refs; no partial claim."""
    selected = plan["selected"]
    if selected is None:
        raise FenceBlocked("NO_WORK_UNIT")
    writer = _claim_identity(api, run_id)
    base = _sha(plan["base_sha"])
    source = _sha(selected["head_sha"])
    branch = selected["head_ref"]
    if not isinstance(branch, str) or not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        raise FenceBlocked("TARGET_BRANCH_INVALID")
    if (api.ref("refs/heads/main") or {}).get("object", {}).get("sha") != base or (
        api.ref("refs/heads/" + branch) or {}).get("object", {}).get("sha") != source:
        raise FenceBlocked("EXACT_HEAD_DRIFT")
    source_tree, base_tree = _git_tree(api, source), _git_tree(api, base)
    previous = _read_control(api)
    now = _now()
    if previous and previous[1]["state"] == "CLAIMED" and _utc(previous[1]["lease_expires_at"]) > now:
        # A finite completed Actions run must not strand an hour-long lease.
        # Unknown/running predecessors retain HOLD. The new control CAS still
        # fences every delayed publication from a completed predecessor.
        try:
            prior_run = previous[1].get("run_id")
            observed_run = api.call("GET", f"actions/runs/{prior_run}")
            finished = (type(prior_run) is int and observed_run.get("id") == prior_run
                        and observed_run.get("status") == "completed")
        except (RuntimeError, ValueError, OSError):
            finished = False
        if not finished:
            raise FenceBlocked("ACTIVE_EXCLUSIVE_WRITER_LEASE")
    epoch = previous[1]["fencing_epoch"] + 1 if previous else 1
    turn = plan["turn_number"]
    if type(turn) is not int or turn < 1:
        raise FenceBlocked("TURN_INVALID")
    number = selected["pull_request"]
    if type(number) is not int or number < 1:
        raise FenceBlocked("PR_INVALID")
    run_ref = f"refs/qikvrt/pr-continuation/runs/{run_id}"
    turn_ref = f"refs/qikvrt/pr-continuation/turns/{turn}"
    attempt_ref = (f"refs/qikvrt/pr-continuation/attempts/{turn}-{number}-"
                   f"{source}-{base}-{run_id}")
    expires = now + dt.timedelta(seconds=LEASE_SECONDS)
    record = {
        "schema": SCHEMA, "state": "CLAIMED", "fencing_epoch": epoch,
        "writer": writer, "run_id": run_id, "work_unit": attempt_ref,
        "main_head": base, "main_tree": base_tree,
        "source_head": source, "source_tree": source_tree,
        "target_ref": "refs/heads/" + branch,
        "lease_expires_at": expires.isoformat(),
    }
    control_sha = _control_commit(api, prior_sha=previous[0] if previous else None,
                                  base=base, value=record)
    changes = [
        {"name": CONTROL_REF, "beforeOid": previous[0] if previous else ZERO,
         "afterOid": control_sha},
        {"name": f"refs/qikvrt/pr-continuation/epochs/{epoch}",
         "beforeOid": ZERO, "afterOid": control_sha},
        {"name": run_ref, "beforeOid": ZERO, "afterOid": base},
        {"name": turn_ref, "beforeOid": ZERO, "afterOid": source},
        {"name": attempt_ref, "beforeOid": ZERO, "afterOid": source},
        {"name": "refs/heads/main", "beforeOid": base, "afterOid": base},
        {"name": "refs/heads/" + branch, "beforeOid": source, "afterOid": source},
    ]
    api.atomic_refs(changes, operation_id=f"acquire-{run_id}-{turn}-{epoch}")
    current = _read_control(api)
    if current is None or current[0] != control_sha or current[1] != record:
        raise FenceBlocked("CLAIM_READBACK_MISMATCH")
    if api.ref(attempt_ref).get("object", {}).get("sha") != source:
        raise FenceBlocked("ATTEMPT_READBACK_MISMATCH")
    return {"writer_claim": record, "control_sha": control_sha,
            "fencing_epoch": epoch, "attempt_ref": attempt_ref,
            "lease_expires_at": record["lease_expires_at"]}


def publish(api: Any, plan: Mapping[str, Any], candidate: str,
            *, effect_ref: str) -> dict[str, Any]:
    """Branch and fence advance atomically; stale writer cannot publish."""
    source = _sha(plan["selected"]["head_sha"])
    candidate = _sha(candidate)
    if source == candidate:
        raise FenceBlocked("NOOP_BRANCH_PUBLICATION")
    claim = plan.get("writer_claim")
    old_control = _sha(plan.get("control_sha"))
    if not isinstance(claim, Mapping) or claim.get("state") != "CLAIMED":
        raise FenceBlocked("FENCED_CLAIM_REQUIRED")
    if _claim_identity(api, claim.get("run_id")) != claim.get("writer"):
        raise FenceBlocked("CLAIM_WRITER_IDENTITY_DRIFT")
    current = _read_control(api)
    if current is None or current[0] != old_control or current[1] != claim:
        raise FenceBlocked("STALE_FENCING_TOKEN")
    if _utc(claim["lease_expires_at"]) <= _now():
        raise FenceBlocked("WRITER_LEASE_EXPIRED")
    if (claim["source_head"] != source or claim["main_head"] != plan["base_sha"] or
        claim["source_tree"] != _git_tree(api, source) or
        claim["main_tree"] != _git_tree(api, plan["base_sha"])):
        raise FenceBlocked("CLAIM_HEAD_TREE_DRIFT")
    branch = claim["target_ref"]
    if (not isinstance(effect_ref, str) or
        not effect_ref.startswith("refs/qikvrt/pr-continuation/effects/") or
        not re.fullmatch(r"refs/[A-Za-z0-9._/-]+", effect_ref)):
        raise FenceBlocked("EFFECT_REF_INVALID")
    if (api.ref(branch) or {}).get("object", {}).get("sha") != source:
        raise FenceBlocked("BRANCH_DRIFT")
    if (api.ref("refs/heads/main") or {}).get("object", {}).get("sha") != plan["base_sha"]:
        raise FenceBlocked("MAIN_DRIFT")
    new = dict(claim, state="PUBLISHED", lease_expires_at=_now().isoformat(), successor_head=candidate,
               successor_tree=_git_tree(api, candidate))
    new_control = _control_commit(api, prior_sha=old_control,
                                  base=plan["base_sha"], value=new)
    api.atomic_refs([
        {"name": CONTROL_REF, "beforeOid": old_control, "afterOid": new_control},
        {"name": branch, "beforeOid": source, "afterOid": candidate},
        {"name": effect_ref, "beforeOid": ZERO, "afterOid": candidate},
        {"name": "refs/heads/main", "beforeOid": plan["base_sha"],
         "afterOid": plan["base_sha"]},
    ], operation_id=f"publish-{claim['run_id']}-{claim['fencing_epoch']}")
    verified = _read_control(api)
    if (verified is None or verified[0] != new_control or verified[1] != new or
        (api.ref(branch) or {}).get("object", {}).get("sha") != candidate or
        (api.ref(effect_ref) or {}).get("object", {}).get("sha") != candidate):
        raise FenceBlocked("PUBLICATION_READBACK_UNVERIFIED")
    return {"state": "FENCED_BRANCH_PUBLISHED", "control_sha": new_control,
            "fencing_epoch": claim["fencing_epoch"], "candidate_head": candidate,
            "effect_ack_done": False}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _checked_head(root: pathlib.Path) -> str:
    return _sha(subprocess.check_output(
        ["git", "rev-parse", "--verify", "HEAD^{commit}"], cwd=root,
        timeout=30, stderr=subprocess.PIPE).decode().strip())


def _bootstrap_admission(api: Any, request: Mapping[str, Any], root: pathlib.Path) -> tuple[str, int]:
    """Direct Owner instruction plus the actual bound Actions run, not a forged run ID."""
    if (request.get("schema") != BOOTSTRAP_SCHEMA
            or api.repository != "ingolf-lohmann/qik-vrt"
            or request.get("repository") != api.repository
            or request.get("principal") != {"name": "Ingolf Lohmann", "github_login": "ingolf-lohmann", "github_id": 294949349}
            or request.get("pull_request") != 756 or request.get("target_ref") != BOOTSTRAP_REF
            or request.get("scope") != "INITIAL_CONTROL_EPOCH_AND_EXACT_HEAD_GUARDS"
            or request.get("effect_ack_done") is not False):
        raise FenceBlocked("BOOTSTRAP_OWNER_SCOPE_INVALID")
    instructions = request.get("instructions")
    if (not isinstance(instructions, list) or len(instructions) != 2 or
            any(not isinstance(item, dict) or item.get("source") != "DIRECT_HUMAN_INSTRUCTION_IN_CURRENT_SESSION"
                or not isinstance(item.get("text"), str) or not item["text"].strip()
                or hashlib.sha256(item["text"].encode()).hexdigest() != item.get("sha256")
                for item in instructions)):
        raise FenceBlocked("BOOTSTRAP_OWNER_INSTRUCTION_UNBOUND")
    pins = request.get("source_pins")
    if not isinstance(pins, dict) or set(pins) != BOOTSTRAP_PIN_PATHS:
        raise FenceBlocked("BOOTSTRAP_SOURCE_PINS_INVALID")
    for relative, expected in pins.items():
        path = root / relative
        if (path.is_symlink() or not path.is_file()
                or path.resolve().is_relative_to(root.resolve()) is not True
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise FenceBlocked("BOOTSTRAP_SOURCE_PIN_DRIFT:" + relative)
    source = _sha(os.environ.get("GITHUB_SHA"))
    raw_id = os.environ.get("GITHUB_RUN_ID", "")
    if not raw_id.isdecimal() or int(raw_id) <= 0:
        raise FenceBlocked("BOOTSTRAP_ACTIONS_RUN_REQUIRED")
    run_id = int(raw_id)
    _claim_identity(api, run_id)
    if (os.environ.get("GITHUB_ACTOR_ID") != "294949349"
            or os.environ.get("GITHUB_ACTOR") != "ingolf-lohmann"
            or os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != BOOTSTRAP_REF
            or _checked_head(root) != source):
        raise FenceBlocked("BOOTSTRAP_ACTIONS_SOURCE_BINDING_INVALID")
    run = api.call("GET", f"actions/runs/{run_id}")
    if (run.get("id") != run_id or run.get("head_sha") != source
            or run.get("head_branch") != BOOTSTRAP_REF.removeprefix("refs/heads/")
            or run.get("event") != "push" or run.get("path") != BOOTSTRAP_WORKFLOW
            or run.get("run_attempt") != int(os.environ["GITHUB_RUN_ATTEMPT"])
            or (run.get("actor") or {}).get("id") != 294949349
            or (run.get("head_repository") or {}).get("id") != 1273784147):
        raise FenceBlocked("BOOTSTRAP_ORIGINAL_RUN_READBACK_MISMATCH")
    commit = api.call("GET", "git/commits/" + source)
    if [p.get("sha") for p in commit.get("parents", [])] != [_sha(request.get("expected_parent"))]:
        raise FenceBlocked("BOOTSTRAP_SOURCE_PARENT_DRIFT")
    pr = api.call("GET", "pulls/756")
    if (pr.get("state") != "open" or pr.get("number") != 756
            or (pr.get("head") or {}).get("sha") != source
            or (pr.get("head") or {}).get("ref") != BOOTSTRAP_REF.removeprefix("refs/heads/")
            or ((pr.get("head") or {}).get("repo") or {}).get("full_name") != api.repository
            or ((pr.get("base") or {}).get("repo") or {}).get("full_name") != api.repository
            or (pr.get("base") or {}).get("ref") != "main"):
        raise FenceBlocked("BOOTSTRAP_PR_BINDING_INVALID")
    return source, run_id


def _bootstrap_readback(api: Any, intent: Mapping[str, Any]) -> dict[str, Any]:
    """Each exact ref and the original control commit are read independently."""
    observations = []
    verified = True
    for change in intent["request"]["variables"]["input"]["refUpdates"]:
        try:
            ref = api.ref(change["name"])
            sha = (ref or {}).get("object", {}).get("sha")
            match = bool(ref and ref.get("ref") == change["name"] and sha == change["afterOid"])
            observations.append({"ref": change["name"], "observed": sha, "expected": change["afterOid"], "verified": match})
            verified &= match
        except (RuntimeError, ValueError, OSError) as exc:
            verified = False
            observations.append({"ref": change["name"], "state": "UNKNOWN", "error_type": type(exc).__name__})
    try:
        control = _read_control(api)
        verified &= bool(control and control[0] == intent["control_sha"] and control[1] == intent["control"])
    except (RuntimeError, ValueError, OSError) as exc:
        verified = False
        observations.append({"control": "UNKNOWN", "error_type": type(exc).__name__})
    return {"readback_verified": bool(verified), "refs": observations,
            "control_sha": intent["control_sha"], "fencing_epoch": 1,
            "source_head": intent["source_head"], "main_head": intent["main_head"],
            "active_writer_lease": False, "main_activation": False,
            "ordinary_release": False, "effect_ack_done": False}


def bootstrap(api: Any, request: Mapping[str, Any], *, root: pathlib.Path,
              journal: pathlib.Path) -> dict[str, Any]:
    """Execute and collect one authorized bootstrap in the existing consumer.

    A create-only remote intent precedes the single updateRefs. Re-entry after
    a crash or lost response reconciles that original intent, never resubmits.
    The completed zero-duration bootstrap installs the initial fence ledger;
    it does not assert that legacy Main writers have adopted the new protocol.
    """
    source, run_id = _bootstrap_admission(api, request, root)
    request_digest = _digest(request)
    intent_ref = "refs/qikvrt/pr-continuation/bootstrap/" + request_digest
    previous = api.ref(intent_ref)
    if previous is not None:
        record = api.call("GET", "git/commits/" + _sha(previous.get("object", {}).get("sha")))
        message = record.get("message", "")
        if not message.startswith(BOOTSTRAP_INTENT_SCHEMA + "\n"):
            raise FenceBlocked("BOOTSTRAP_PRIOR_INTENT_INVALID")
        intent = json.loads(message.split("\n", 1)[1])
        if (intent.get("schema") != BOOTSTRAP_INTENT_SCHEMA
                or intent.get("owner_request_sha256") != request_digest
                or intent.get("source_head") != source):
            raise FenceBlocked("BOOTSTRAP_PRIOR_INTENT_BINDING_DRIFT")
        result = _bootstrap_readback(api, intent)
        result.update(state="BOOTSTRAP_READBACK_CONFIRMED" if result["readback_verified"] else "BOOTSTRAP_PRIOR_INTENT_HOLD",
                      submission_count=0, intent_ref=intent_ref, automatic_retry=False)
        api.record_once(journal / "readback.json", result)
        api.record_once(journal / "result.json", result)
        return result
    base = _sha(request.get("expected_main"))
    if ((api.ref("refs/heads/main") or {}).get("object", {}).get("sha") != base
            or (api.ref(BOOTSTRAP_REF) or {}).get("object", {}).get("sha") != source):
        raise FenceBlocked("BOOTSTRAP_EXACT_HEAD_DRIFT")
    epoch_ref = "refs/qikvrt/pr-continuation/epochs/1"
    if api.ref(CONTROL_REF) is not None or api.ref(epoch_ref) is not None:
        raise FenceBlocked("BOOTSTRAP_CONTROL_OR_EPOCH_ALREADY_EXISTS")
    control = {
        "schema": SCHEMA, "state": "PUBLISHED", "fencing_epoch": 1,
        "writer": _claim_identity(api, run_id), "run_id": run_id, "work_unit": intent_ref,
        "main_head": base, "main_tree": _git_tree(api, base),
        "source_head": source, "source_tree": _git_tree(api, source),
        "target_ref": BOOTSTRAP_REF, "successor_head": source,
        "successor_tree": _git_tree(api, source), "lease_expires_at": _now().isoformat(),
        "owner_request_sha256": request_digest, "active_writer_lease": False,
        "scope": "INITIAL_CONTROL_EPOCH_AND_EXACT_HEAD_GUARDS",
    }
    control_sha = _control_commit(api, prior_sha=None, base=base, value=control)
    changes = [
        {"name": CONTROL_REF, "beforeOid": ZERO, "afterOid": control_sha},
        {"name": epoch_ref, "beforeOid": ZERO, "afterOid": control_sha},
        {"name": "refs/heads/main", "beforeOid": base, "afterOid": base},
        {"name": BOOTSTRAP_REF, "beforeOid": source, "afterOid": source},
    ]
    operation = "bootstrap-" + request_digest
    payload = api.atomic_request(changes, operation_id=operation)
    intent = {"schema": BOOTSTRAP_INTENT_SCHEMA, "owner_request_sha256": request_digest,
              "source_head": source, "main_head": base, "control_sha": control_sha,
              "control": control, "request": payload, "run_id": run_id}
    intent_sha = _control_commit(api, prior_sha=None, base=base, value=intent,
                                 schema=BOOTSTRAP_INTENT_SCHEMA)
    api.record_once(journal / "intent.json", dict(intent, intent_sha=intent_sha, intent_ref=intent_ref))
    if not api.create_once(intent_ref, intent_sha):
        raise FenceBlocked("BOOTSTRAP_INTENT_ALREADY_RESERVED; reconcile only")
    error = None
    response = None
    try:
        response = api.atomic_refs(changes, operation_id=operation,
                                   journal=journal, expected_request=payload)
    except (RuntimeError, ValueError, OSError) as exc:
        error = {"error_type": type(exc).__name__, "reason": str(exc)}
    # This is part of this invocation on success, rejection and lost response.
    result = _bootstrap_readback(api, intent)
    if result["readback_verified"]:
        state = "BOOTSTRAP_APPLIED" if error is None else "BOOTSTRAP_APPLIED_RESPONSE_UNCONFIRMED"
    else:
        state = "BOOTSTRAP_HOLD"
    result.update(state=state, submission_count=int((journal / "response.json").exists()), response=response, error=error,
                  intent_ref=intent_ref, intent_sha=intent_sha,
                  owner_request_sha256=request_digest, automatic_retry=False)
    api.record_once(journal / "readback.json", result)
    api.record_once(journal / "result.json", result)
    return result
