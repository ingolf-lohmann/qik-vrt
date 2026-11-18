# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Persistent, fail-closed GitHub-Ref admission for the existing PR consumer.

The control commit is an immutable receipt. Every effecting Git-ref mutation uses
GitHub GraphQL updateRefs: control-ref CAS and target-ref CAS in one transaction.
This module grants no authority to a separate writer and never claims EAP ACK.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from typing import Any, Mapping

SCHEMA = "qikvrt_fenced_writer_control_v1"
CONTROL_REF = "refs/qikvrt/pr-continuation/control"
ZERO = "0" * 40
LEASE_SECONDS = 3600
SHA = re.compile(r"^[0-9a-f]{40}$")


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
                    value: Mapping[str, Any]) -> str:
    parent = _sha(prior_sha or base)
    expected_tree = _git_tree(api, parent)
    message = SCHEMA + "\n" + json.dumps(value, sort_keys=True, separators=(",", ":"))
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
    if previous and _utc(previous[1]["lease_expires_at"]) > now:
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
    new = dict(claim, state="PUBLISHED", successor_head=candidate,
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
