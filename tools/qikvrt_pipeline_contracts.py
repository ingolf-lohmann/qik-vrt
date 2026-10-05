#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Postcondition checks extracted from the existing continuation/CI/verifier.

No polling, merge, approval, permission change, or inference of acceptance.
API observations are bounded; uncertain writes are followed by independent GETs.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode
from datetime import datetime, timezone
from typing import Any

MARKER = "<!-- qikvrt-autonomous-self-heal:enabled -->"
VERIFIER_MARKER = "<!-- qikvrt-repair-exact-head:enabled -->"
CONTEXT = "QIKVRT autonomous exact-head verification"
WORKFLOW = "qikvrt_autonomous_exact_head_verify.yml"
ACTIVE = {"queued", "in_progress", "waiting", "requested", "pending"}
SHA = re.compile(r"[0-9a-f]{40}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class Block(RuntimeError):
    """Credential-free, stable causal code."""


class ApiError(Block):
    def __init__(self, status: int | None):
        self.status = status
        super().__init__(f"API_HTTP_{status}" if status else "API_TRANSPORT_UNCERTAIN")


def api(method: str, path: str, data: Any = None) -> Any:
    if method not in {"GET", "POST", "PATCH"} or not path.startswith("repos/"):
        raise Block("API_SCOPE_INVALID")
    if method == "PATCH" and (not re.fullmatch(r"repos/[^/]+/[^/]+/pulls/[1-9][0-9]*", path)
                              or not isinstance(data, dict) or set(data) != {"body"}):
        raise Block("API_SCOPE_INVALID")
    command = ["gh", "api", "--hostname", "github.com", "--method", method, path,
               "-H", "Accept: application/vnd.github+json"]
    if data is not None:
        command += ["--input", "-"]
    try:
        result = subprocess.run(command, input=None if data is None else json.dumps(data),
                                text=True, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ApiError(None) from exc
    if result.returncode:
        match = re.search(r"HTTP (\d{3})", result.stderr)
        raise ApiError(int(match[1]) if match else None)
    if not result.stdout.strip():
        return None  # The dispatch endpoint returns HTTP 204, not JSON evidence.
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise Block("API_RESPONSE_INVALID") from exc


def git(*args: str, root: Path = ROOT) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), *args], text=True,
                                capture_output=True, check=False, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Block("GIT_OPERATION_UNCERTAIN") from exc
    if result.returncode:
        raise Block("GIT_OPERATION_FAILED")
    return result.stdout.strip()


def sha(value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise Block("INVALID_GIT_IDENTITY")
    return value


def repo(value: str) -> str:
    if not REPO.fullmatch(value):
        raise Block("INVALID_REPOSITORY")
    return value


def branch(value: Any) -> str:
    # Values enter GITHUB_OUTPUT and are then used only as quoted arguments.
    if (not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", value)
            or any(p in value for p in ("..", "//", "@{")) or value.endswith(("/", ".", ".lock"))):
        raise Block("INVALID_BRANCH")
    return value


def receipt(kind: str, **values: Any) -> dict[str, Any]:
    return {"schema": kind, "state": "HOLD", "classification": "BLOCKADE",
            "first_blocker": None, "PREDECESSOR_EVIDENCE_TRANSFER": False,
            "EFFECT_ACK_DONE": False, "transport_ack_is_effect_ack": False, **values}


def fingerprint(value: dict[str, Any]) -> str:
    fields = ("repository", "head", "tree", "base", "pr_number", "verification",
              "first_blocker", "status_delivery", "comment_delivery")
    semantic = {key: value.get(key) for key in fields}
    return hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    value["transition_fingerprint"] = fingerprint(value)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def listing(call: Any, path: str, key: str | None = None) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for page in range(1, 11):
        raw = call("GET", path + ("&" if "?" in path else "?") + f"per_page=100&page={page}")
        batch = raw if key is None else raw[key]
        if not isinstance(batch, list) or any(not isinstance(x, dict) for x in batch):
            raise Block("INVENTORY_SCHEMA_INVALID")
        values.extend(batch)
        if len(batch) < 100:
            return values
    raise Block("INVENTORY_BOUND_EXCEEDED")


def eligible(pr: dict[str, Any], repository: str) -> bool:
    return (pr.get("state") == "open" and pr.get("draft") is True
            and MARKER in (pr.get("body") or "")
            and ((pr.get("head") or {}).get("repo") or {}).get("full_name") == repository
            and ((pr.get("base") or {}).get("repo") or {}).get("full_name") == repository
            and (pr.get("base") or {}).get("ref") == "main")


def select(prs: list[dict[str, Any]], repository: str, opportunity: int) -> dict[str, Any] | None:
    repo(repository)
    if type(opportunity) is not int or opportunity < 1:
        raise Block("INVALID_OPPORTUNITY")
    candidates = [p for p in prs if eligible(p, repository)]
    for p in candidates:
        if type(p.get("number")) is not int or p["number"] < 1:
            raise Block("INVALID_PR_NUMBER")
        branch(p["head"]["ref"])
        sha(p["head"]["sha"])
        sha(p["base"]["sha"])
    if len({p["number"] for p in candidates}) != len(candidates):
        raise Block("DUPLICATE_PR_INVENTORY")
    candidates.sort(key=lambda p: p["number"])
    # No clock, mutable PR comment, or timestamp is used as progress evidence.
    # For N stable candidates, N consecutive opportunities serve each once.
    return candidates[(opportunity - 1) % len(candidates)] if candidates else None


def remote_identity(call: Any, repository: str, ref: str) -> tuple[str, str]:
    repo(repository)
    ref = ref.removeprefix("refs/")
    if not ref.startswith(("heads/", "tags/")):
        raise Block("INVALID_REF")
    branch(ref.split("/", 1)[1])
    prefix = f"repos/{repository}"
    obj = call("GET", f"{prefix}/git/ref/{ref}")["object"]
    for _ in range(8):
        if obj["type"] == "commit":
            head = sha(obj["sha"])
            commit = call("GET", f"{prefix}/git/commits/{head}")
            if commit["sha"] != head:
                raise Block("COMMIT_READBACK_MISMATCH")
            return head, sha(commit["tree"]["sha"])
        if obj["type"] != "tag":
            raise Block("REF_OBJECT_TYPE_INVALID")
        obj = call("GET", f"{prefix}/git/tags/{sha(obj['sha'])}")["object"]
    raise Block("TAG_CHAIN_BOUND_EXCEEDED")


def run_title(pr: int, head: str, base: str, base_ref: str = "main") -> str:
    suffix = "" if branch(base_ref) == "main" else "-ref-" + base_ref
    return f"qikvrt-exact-pr-{pr}-{sha(head)}-{sha(base)}{suffix}"


def verifier_protocol(call: Any, repository: str, base: str, base_ref: str) -> dict[str, str]:
    """A dispatch always executes Main's carrier, even for a candidate PR.

    Legacy unbound run titles cannot establish an exact-subject postcondition.
    Do not send an unobservable write while the reviewed Main protocol is old.
    """
    main, tree = remote_identity(call, repository, "heads/main")
    if base_ref == "main" and main != base:
        raise Block("BASE_DRIFT")
    path = ".github/workflows/" + WORKFLOW
    try:
        raw = call("GET", f"repos/{repository}/contents/{path}?ref={main}")
    except ApiError as exc:
        if exc.status == 404:
            raise Block("TRUSTED_MAIN_VERIFIER_PROTOCOL_UNAVAILABLE") from exc
        raise
    if raw.get("type") != "file" or raw.get("path") != path or raw.get("encoding") != "base64":
        raise Block("VERIFIER_PROTOCOL_READBACK_INVALID")
    try:
        source = base64.b64decode("".join(raw["content"].split()), validate=True)
        blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\0" + source).hexdigest()
        if blob != sha(raw["sha"]):
            raise Block("VERIFIER_PROTOCOL_READBACK_INVALID")
        text = source.decode("utf-8")
    except (binascii.Error, UnicodeError) as exc:
        raise Block("VERIFIER_PROTOCOL_READBACK_INVALID") from exc
    lines = [line for line in text.splitlines() if line.startswith("run-name:")]
    prefix = ("run-name: qikvrt-exact-pr-${{ github.event.client_payload.pull_request }}-"
              "${{ github.event.client_payload.head_sha }}-${{ github.event.client_payload.base_sha }}")
    if len(lines) != 1 or not lines[0].startswith(prefix):
        raise Block("TRUSTED_MAIN_VERIFIER_PROTOCOL_UNAVAILABLE")
    if base_ref != "main" and ("github.event.client_payload.base_ref" not in lines[0]
                               or "TARGET_BASE_REF:" not in text):
        raise Block("TRUSTED_MAIN_STAGING_VERIFIER_PROTOCOL_UNAVAILABLE")
    return {"trusted_main_head": main, "trusted_main_tree": tree, "verifier_protocol_blob": blob}


def draft_postcondition(call: Any, repository: str, ref: str, head: str, tree: str,
                        base: str, *, base_ref: str = "main", required_marker: str = "", body: str = "",
                        title: str = "repair: resume repository-internal candidate") -> dict[str, Any]:
    """Finish the PR portion of an admitted internal writer, even on byte NOOP.

    No branch writer, scheduler, permission escalation, review or merge lives
    here. Closed/ready/staging/foreign candidates cannot gain continuation.
    A body PATCH is bounded but is not an atomic metadata compare-and-swap.
    """
    value = receipt("qikvrt_draft_postcondition_v1", repository=repo(repository),
                    ref=branch(ref), head=sha(head), tree=sha(tree), base=sha(base),
                    base_ref=branch(base_ref), pr_number=None, pr_create_attempted=False,
                    continuation_bind_attempted=False, continuation_enabled=False)
    prefix = f"repos/{repository}"

    def bind() -> None:
        if remote_identity(call, repository, "heads/" + ref) != (head, tree):
            raise Block("CANDIDATE_HEAD_DRIFT")
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")

    def inventory() -> list[dict[str, Any]]:
        query = urlencode({"state": "all", "head": repository.split('/')[0] + ':' + ref,
                           "per_page": 100})
        rows = call("GET", f"{prefix}/pulls?{query}")
        if not isinstance(rows, list) or len(rows) >= 100:
            raise Block("PR_ENUMERATION_INCOMPLETE")
        if len(rows) > 1:
            raise Block("DUPLICATE_CANDIDATE_PRS")
        return rows

    def verify(pr: dict[str, Any]) -> None:
        if pr["state"] != "open":
            raise Block("CANDIDATE_PR_CLOSED")
        if (pr["head"]["sha"] != head or pr["head"]["ref"] != ref
                or pr["head"]["repo"]["full_name"] != repository
                or pr["base"]["sha"] != base or pr["base"]["ref"] != base_ref
                or pr["base"]["repo"]["full_name"] != repository
                or required_marker not in (pr.get("body") or "")):
            raise Block("PR_EXACT_BINDING_MISMATCH")
        if pr.get("draft") is not True:
            raise Block("READY_PR_REQUIRES_NATIVE_REVIEW_BOUNDARY")

    try:
        if ref in {"main", base_ref}:
            raise Block("REVIEW_BRANCH_REQUIRED")
        bind()
        rows = inventory()
        existed = bool(rows)
        error = None
        if not rows:
            bind()
            value["pr_create_attempted"] = True
            text = (body.rstrip() + f"\n\n{required_marker}\n{VERIFIER_MARKER}\n" + (MARKER + "\n" if base_ref == "main" else "") + "\n"
                    f"Exact repository-internal candidate: HEAD `{head}`, TREE `{tree}`, "
                    f"current base `{base_ref}` at `{base}`.\n"
                    "PREDECESSOR_EVIDENCE_TRANSFER=false. EFFECT_ACK_DONE=false.\n"
                    "Independent review, native governance and external-effect gates remain mandatory.\n")
            try:
                call("POST", f"{prefix}/pulls", {"head": ref, "base": base_ref, "draft": True,
                                                "title": title, "body": text})
            except Block as exc:
                error = exc
            rows = inventory()  # Neither a response nor an exception proves effect.
        if not rows:
            if isinstance(error, ApiError) and error.status in (401, 403):
                raise Block("PR_WRITER_CAPABILITY_UNAVAILABLE")
            raise Block("PR_CREATION_NOT_READ_BACK")
        number = rows[0]["number"]
        if type(number) is not int or number < 1:
            raise Block("PR_NUMBER_INVALID")
        value["pr_number"] = number
        pr = call("GET", f"{prefix}/pulls/{number}")
        verify(pr)
        marker = MARKER if base_ref == "main" else VERIFIER_MARKER
        if marker not in (pr.get("body") or ""):
            bind()
            fresh = call("GET", f"{prefix}/pulls/{number}")
            verify(fresh)
            if fresh.get("body") != pr.get("body"):
                raise Block("PR_CONTINUATION_METADATA_DRIFT")
            value["continuation_bind_attempted"] = True
            error = None
            try:
                call("PATCH", f"{prefix}/pulls/{number}", {
                    "body": (pr.get("body") or "").rstrip() + f"\n\n{marker}\n"})
            except Block as exc:
                error = exc
            pr = call("GET", f"{prefix}/pulls/{number}")
            verify(pr)
            if marker not in (pr.get("body") or ""):
                if isinstance(error, ApiError) and error.status in (401, 403):
                    raise Block("PR_CONTINUATION_WRITER_CAPABILITY_UNAVAILABLE")
                raise Block("PR_CONTINUATION_BINDING_NOT_READ_BACK")
        value["continuation_enabled"] = base_ref == "main"
        bind()
        value.update(state="PR_ALREADY_MATERIALIZED" if existed else "PR_MATERIALIZED",
                     classification="IDLE" if existed and not value["continuation_bind_attempted"] else "WORK")
    except (Block, KeyError, TypeError, ValueError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    return value


def candidate_postcondition(call: Any, repository: str, ref: str, head: str,
                            tree: str, base: str, **metadata: Any) -> dict[str, Any]:
    """One shared Branch -> Draft PR -> existing Exact-Head verifier handoff."""
    value = draft_postcondition(call, repository, ref, head, tree, base, **metadata)
    value["materialization_state"] = value["state"]
    if value["classification"] != "BLOCKADE":
        verifier = resume(call, repository, value["pr_number"], head, tree, base, ref, value["base_ref"])
        value["verifier"] = verifier
        value["verification"] = verifier["state"]
        if verifier["classification"] == "BLOCKADE":
            value.update(state="HOLD", classification="BLOCKADE", first_blocker=verifier["first_blocker"])
        elif verifier["dispatch_attempted"]:
            value["classification"] = "WORK"
    return value


def push_postcondition(call: Any, push: Any, repository: str, ref: str,
                       head: str, tree: str, base: str, predecessor: str | None,
                       base_ref: str = "main", pr_number: int | None = None) -> dict[str, Any]:
    """Resolve uncertain non-force writes from remote identity, never retry them."""
    value = receipt("qikvrt_branch_write_postcondition_v1", repository=repo(repository),
                    ref=branch(ref), head=sha(head), tree=sha(tree), base=sha(base),
                    base_ref=branch(base_ref), push_attempted=False)
    try:
        if ref in {"main", base_ref}:
            raise Block("REVIEW_BRANCH_REQUIRED")
        if predecessor is not None:
            sha(predecessor)
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")
        if pr_number is not None:
            if type(pr_number) is not int or pr_number < 1:
                raise Block("PR_NUMBER_INVALID")
            pr = call("GET", f"repos/{repository}/pulls/{pr_number}")
            if (pr.get("state") != "open" or pr.get("draft") is not True
                    or pr["head"]["repo"]["full_name"] != repository
                    or pr["base"]["repo"]["full_name"] != repository
                    or pr["head"]["ref"] != ref or pr["head"]["sha"] not in {head, predecessor}
                    or pr["base"]["ref"] != base_ref or pr["base"]["sha"] != base):
                raise Block("PR_WRITER_ADMISSION_CHANGED")
        try:
            before = remote_identity(call, repository, "heads/" + ref)
        except ApiError as exc:
            if exc.status != 404:
                raise
            before = None
        if before != (head, tree):
            if (before[0] if before else None) != predecessor:
                raise Block("COMPETING_BRANCH_WRITER")
            value["push_attempted"] = True
            try:
                push()
            except Block:
                pass
            # This GET also runs after a denied/lost/malformed write response.
            if remote_identity(call, repository, "heads/" + ref) != (head, tree):
                raise Block("BRANCH_WRITE_NOT_READ_BACK")
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")
        value.update(state="BRANCH_READ_BACK", classification="WORK" if value["push_attempted"] else "IDLE")
    except (Block, KeyError, TypeError, ValueError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    return value


def observe_writer(call: Any, root: Path, repository: str, ref: str, base_ref: str = "main") -> dict[str, Any]:
    """Bind the existing workflow's source before generation, without effects."""
    head = sha(git("rev-parse", "HEAD", root=root))
    tree = sha(git("rev-parse", "HEAD^{tree}", root=root))
    branch(ref)
    existed = True
    try:
        remote = remote_identity(call, repository, "heads/" + ref)
    except ApiError as exc:
        if exc.status != 404:
            raise
        existed, remote = False, None
    if existed and remote != (head, tree):
        raise Block("WRITER_SOURCE_DRIFT")
    base, base_tree = remote_identity(call, repository, "heads/" + branch(base_ref))
    if not existed and (head, tree) != (base, base_tree):
        raise Block("NEW_BRANCH_SOURCE_NOT_CURRENT_MAIN")
    return receipt("qikvrt_writer_input_v1", repository=repository, ref=ref, head=head, tree=tree,
                   base=base, base_tree=base_tree, base_ref=base_ref, branch_existed=existed,
                   state="WRITER_INPUT_BOUND", classification="WORK")


def publish_writer(call: Any, root: Path, observed: dict[str, Any],
                   *, push: Any = None) -> dict[str, Any]:
    """Postcondition step of an existing writer; never schedules or generates work."""
    value = receipt("qikvrt_writer_postcondition_v1")
    try:
        if observed.get("schema") != "qikvrt_writer_input_v1" or observed.get("state") != "WRITER_INPUT_BOUND":
            raise Block("WRITER_INPUT_NOT_BOUND")
        repository, source_ref = repo(observed["repository"]), branch(observed["ref"])
        source, base = sha(observed["head"]), sha(observed["base"])
        base_ref = branch(observed.get("base_ref", "main"))
        remote_url = git("remote", "get-url", "origin", root=root)
        if remote_url not in {f"https://github.com/{repository}.git", f"https://github.com/{repository}",
                              f"git@github.com:{repository}.git"}:
            raise Block("WRITER_REMOTE_REPOSITORY_MISMATCH")
        head, tree = sha(git("rev-parse", "HEAD", root=root)), sha(git("rev-parse", "HEAD^{tree}", root=root))
        value.update(repository=repository, head=head, tree=tree, base=base, base_ref=base_ref, source_head=source)
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")
        if git("diff", "--name-only", root=root) or git("diff", "--cached", "--name-only", root=root):
            raise Block("WRITER_TRACKED_WORKTREE_DIRTY")
        # The source must remain an ancestor; no force update or history rewrite.
        git("merge-base", "--is-ancestor", source, head, root=root)
        if source_ref == base_ref:
            if source != base:
                raise Block("BASE_DRIFT")
            if head == source:
                value.update(state="NOOP", classification="IDLE")
                return value
            identity = hashlib.sha256((repository + base_ref + base + tree).encode()).hexdigest()[:24]
            ref, predecessor = "automation/repair-" + identity, None
            try:
                remote_head, remote_tree = remote_identity(call, repository, "heads/" + ref)
            except ApiError as exc:
                if exc.status != 404:
                    raise
            else:
                commit = call("GET", f"repos/{repository}/git/commits/{remote_head}")
                if remote_tree != tree or [p["sha"] for p in commit["parents"]] != [base]:
                    raise Block("EXISTING_BRANCH_BINDING_MISMATCH")
                # Reconstructed identical bytes use the immutable remote subject;
                # its verifier still executes freshly on that exact subject.
                head = remote_head
                value["head"] = head
        else:
            ref, predecessor = source_ref, source if observed.get("branch_existed") is True else None
            query = urlencode({"state": "all", "head": repository.split('/')[0] + ':' + ref,
                               "per_page": 100})
            rows = call("GET", f"repos/{repository}/pulls?{query}")
            if not isinstance(rows, list) or len(rows) >= 100:
                raise Block("PR_ENUMERATION_INCOMPLETE")
            if len(rows) > 1:
                raise Block("DUPLICATE_CANDIDATE_PRS")
            if rows:
                pr = rows[0]
                if pr.get("state") != "open":
                    raise Block("CANDIDATE_PR_CLOSED")
                if pr.get("draft") is not True:
                    raise Block("READY_PR_REQUIRES_NATIVE_REVIEW_BOUNDARY")
                if (pr["head"]["repo"]["full_name"] != repository
                        or pr["base"]["repo"]["full_name"] != repository
                        or pr["head"]["ref"] != ref or pr["head"]["sha"] not in {source, head}
                        or pr["base"]["ref"] != base_ref or pr["base"]["sha"] != base):
                    raise Block("PR_EXACT_BINDING_MISMATCH")
        value["ref"] = ref
        written = push_postcondition(call, push or (lambda: git(
            "push", "origin", f"HEAD:refs/heads/{ref}", root=root)), repository, ref, head, tree, base, predecessor, base_ref)
        value["branch_write"] = written
        if written["classification"] == "BLOCKADE":
            raise Block(written["first_blocker"])
        completed = candidate_postcondition(call, repository, ref, head, tree, base, base_ref=base_ref)
        value["postcondition"] = completed
        value.update(state=completed["state"], classification=completed["classification"],
                     first_blocker=completed["first_blocker"], pr_number=completed["pr_number"])
    except (Block, KeyError, TypeError, ValueError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    return value


def resume(call: Any, repository: str, pr_number: int, head: str, tree: str,
           base: str, ref: str, base_ref: str = "main") -> dict[str, Any]:
    value = receipt("qikvrt_continuation_postcondition_v1", repository=repo(repository),
                    pr_number=pr_number, head=sha(head), tree=sha(tree), base=sha(base),
                    base_ref=branch(base_ref), dispatch_attempted=False, verification="UNVERIFIED")
    prefix = f"repos/{repository}"

    def bind() -> None:
        pr = call("GET", f"{prefix}/pulls/{pr_number}")
        verification_eligible = (eligible(pr, repository) if base_ref == "main" else (
            pr.get("state") == "open" and pr.get("draft") is True
            and VERIFIER_MARKER in (pr.get("body") or "")
            and pr["head"]["repo"]["full_name"] == repository
            and pr["base"]["repo"]["full_name"] == repository and pr["base"]["ref"] == base_ref))
        if not verification_eligible or pr["head"]["ref"] != branch(ref):
            raise Block("PR_ELIGIBILITY_CHANGED")
        if pr["head"]["sha"] != head or pr["base"]["sha"] != base:
            raise Block("PR_BINDING_DRIFT")
        if remote_identity(call, repository, "heads/" + ref) != (head, tree):
            raise Block("REMOTE_HEAD_TREE_DRIFT")
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")

    def observe() -> list[dict[str, Any]]:
        runs = listing(call, f"{prefix}/actions/workflows/{WORKFLOW}/runs?event=repository_dispatch", "workflow_runs")
        # repository_dispatch head_sha names main, not the PR subject.
        return [r for r in runs if r.get("event") == "repository_dispatch"
                and r.get("display_title") == run_title(pr_number, head, base, base_ref)
                and r.get("path", "").split("@", 1)[0] == ".github/workflows/" + WORKFLOW]

    try:
        bind()
        value.update(verifier_protocol(call, repository, base, base_ref))
        runs = observe()
        error = None
        if not runs:
            # Never blindly retry legacy terminal results without exact provenance.
            statuses = listing(call, f"{prefix}/commits/{head}/statuses")
            if any(s.get("context") == CONTEXT for s in statuses):
                raise Block("LEGACY_VERIFIER_REQUIRES_EXACT_RUN_EVIDENCE")
            bind()
            if remote_identity(call, repository, "heads/main") != (
                    value["trusted_main_head"], value["trusted_main_tree"]):
                raise Block("TRUSTED_MAIN_VERIFIER_SOURCE_DRIFT")
            value["dispatch_attempted"] = True
            try:
                call("POST", f"{prefix}/dispatches", {
                    "event_type": "qikvrt_autonomous_exact_head_verify", "client_payload": {
                        "repository": repository, "pull_request": pr_number, "head_ref": ref,
                        "head_sha": head, "base_sha": base, "base_ref": base_ref, "source_head_sha": head}})
            except Block as exc:
                error = str(exc)
            runs = observe()  # Includes timeout/403/204: none is acceptance.
        bind()
        if not runs:
            raise Block(error or "VERIFIER_DISPATCH_NOT_READ_BACK")
        if len(runs) != 1:
            raise Block("DUPLICATE_EXACT_VERIFIER_RUNS")
        run = runs[0]
        value["verifier_run_id"] = run["id"]
        if run.get("status") in ACTIVE:
            value.update(state="VERIFIER_ACTIVE", classification="WORK")
        else:
            jobs = listing(call, f"{prefix}/actions/runs/{run['id']}/jobs", "jobs")
            if not jobs or run.get("conclusion") in {None, "action_required", "skipped"}:
                raise Block("VERIFIER_NOT_ADMITTED_OR_UNEXECUTED")
            statuses = listing(call, f"{prefix}/commits/{head}/statuses")
            bound = [s for s in statuses if s.get("context") == CONTEXT
                     and s.get("target_url") == run.get("html_url")]
            if not bound or bound[0].get("state") not in {"success", "failure"}:
                raise Block("VERIFICATION_STATUS_NOT_READ_BACK")
            value["verification"] = bound[0]["state"]
            if bound[0]["state"] == "failure":
                raise Block("EXACT_VERIFICATION_FAILED")
            if run.get("conclusion") != "success":
                raise Block("VERIFIER_DELIVERY_OR_EXECUTION_FAILED")
            value.update(state="VERIFIER_TERMINAL_REOBSERVED", classification="IDLE")
    except (Block, KeyError, TypeError, ValueError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    return value


def technical_result(outcomes: dict[str, str], qce_required: bool) -> tuple[str, str | None]:
    required = ["envelope", "checkout", "contracts"]
    optional = ["qce_setup", "qce_tools", "qce"]
    for phase in required + (optional if qce_required else []):
        if outcomes.get(phase) != "success":
            return "failure", f"{phase.upper()}_{outcomes.get(phase, 'NOT_EXECUTED').upper()}"
    if not qce_required and any(outcomes.get(p) not in {"skipped", None} for p in optional):
        return "failure", "UNEXPECTED_QCE_EXECUTION"
    return "success", None


def deliver(call: Any, repository: str, pr_number: int, head: str, base: str,
            run_url: str, outcomes: dict[str, str], qce_required: bool,
            local_identity: tuple[str, str, bool] | None = None, base_ref: str = "main") -> dict[str, Any]:
    technical, causal = technical_result(outcomes, qce_required)
    value = receipt("qikvrt_verifier_phase_results_v1", repository=repo(repository), head=sha(head),
                    base=sha(base), base_ref=branch(base_ref), pr_number=pr_number, verification=technical,
                    verification_first_blocker=causal, raw_outcomes=outcomes,
                    status_delivery="UNVERIFIED", comment_delivery="NOT_ATTEMPTED")
    prefix = f"repos/{repository}"
    try:
        if outcomes.get("envelope") != "success":
            raise Block("ENVELOPE_NOT_VALIDATED_NO_STATUS_WRITE")
        if not re.fullmatch(rf"https://github\.com/{re.escape(repository)}/actions/runs/[0-9]+", run_url):
            raise Block("RUN_URL_INVALID")
        pr = call("GET", f"{prefix}/pulls/{pr_number}")
        if pr["head"]["sha"] != head or pr["base"]["sha"] != base or pr["base"]["ref"] != base_ref:
            raise Block("SUBJECT_SUPERSEDED")
        if remote_identity(call, repository, "heads/" + base_ref)[0] != base:
            raise Block("BASE_DRIFT")
        if technical == "success":
            if (local_identity is None or local_identity[0] != head or local_identity[2] is not True
                    or remote_identity(call, repository, "heads/" + branch(pr["head"]["ref"])) != local_identity[:2]):
                value["verification"] = "UNVERIFIED"
                raise Block("FINAL_CHECKOUT_NOT_BOUND")
            value["tree"] = sha(local_identity[1])
        target = f"{prefix}/statuses/{head}"
        try:
            call("POST", target, {"state": technical, "context": CONTEXT,
                                  "description": "Exact technical checks: " + technical,
                                  "target_url": run_url})
        except Block:
            pass
        values = listing(call, f"{prefix}/commits/{head}/statuses")
        found = [v for v in values if v.get("context") == CONTEXT]
        if not found or found[0].get("state") != technical or found[0].get("target_url") != run_url:
            raise Block("STATUS_DELIVERY_NOT_READ_BACK")
        value["status_delivery"] = "READ_BACK"
        if technical == "failure":
            value["first_blocker"] = causal
            return value
        text = (f"<!-- qikvrt-exact-verification:{head}:{base} -->\n"
                f"Technical verification succeeded for exact HEAD `{head}`, base `{base}`.\n"
                "Independent review, admission, integration and effect readback remain separate.\n"
                "PREDECESSOR_EVIDENCE_TRANSFER=false. EFFECT_ACK_DONE=false.")
        comments_path = f"{prefix}/issues/{pr_number}/comments"
        comments = listing(call, comments_path)
        found = [c for c in comments if c.get("body") == text
                 and c.get("user", {}).get("login") == "github-actions[bot]"]
        if not found:
            try:
                call("POST", comments_path, {"body": text})
            except Block:
                pass
            comments = listing(call, comments_path)
            found = [c for c in comments if c.get("body") == text
                     and c.get("user", {}).get("login") == "github-actions[bot]"]
        if not found:
            raise Block("COMMENT_DELIVERY_NOT_READ_BACK")
        value["comment_delivery"] = "READ_BACK"
        if (remote_identity(call, repository, "heads/" + branch(pr["head"]["ref"])) != (head, value["tree"])
                or remote_identity(call, repository, "heads/" + base_ref)[0] != base):
            raise Block("SUBJECT_SUPERSEDED_AFTER_DELIVERY")
        value.update(state="VERIFIED_AND_REPORTED", classification="WORK")
    except (Block, KeyError, TypeError, ValueError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    # No second technical status is emitted for a reporting failure.
    return value


def final_ci(call: Any, root: Path, repository: str, ref: str,
             evidence_dir: Path, outcomes: dict[str, str]) -> dict[str, Any]:
    value = receipt("qikvrt_ci_final_evidence_v1", repository=repo(repository),
                    event_sha=os.environ.get("GITHUB_SHA"),
                    initial_subject_head=os.environ.get("INITIAL_SUBJECT_HEAD"),
                    observed_at_utc=datetime.now(timezone.utc).isoformat(), run_id=os.environ.get("GITHUB_RUN_ID"),
                    run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"), raw_outcomes=outcomes,
                    test_scope="EXPLICIT_CONTRACT_SUITE_PLUS_MAKE_COMMAND_OUTCOME",
                    historical_evidence_imported=False, test_receipts=[])
    try:
        value.update(head=sha(git("rev-parse", "HEAD", root=root)),
                     tree=sha(git("rev-parse", "HEAD^{tree}", root=root)))
        if outcomes.get("fixpoint_required") == "true":
            if outcomes.get("fixpoint") != "success":
                raise Block("FIXPOINT_NOT_VERIFIED")
        elif outcomes.get("fixpoint_required") == "false":
            if outcomes.get("fixpoint") != "skipped" or outcomes.get("full_test") != "success":
                raise Block("EXACT_TEST_NOT_SUCCESSFUL")
        else:
            raise Block("CI_SCOPE_INVALID")
        from tools.qikvrt_contract_test_runner import MANIFEST, coverage, source_digests
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
        expected_sources = source_digests(root, [MANIFEST] + manifest["source_paths"])
        expected_requirements = manifest["requirements"]
        executed_plans = []
        for mode in ("normal", "optimized"):
            path = evidence_dir / "tests" / (mode + ".json")
            tested = json.loads(path.read_text(encoding="utf-8"))
            if (tested.get("schema") != "qikvrt_executed_contract_tests_v1"
                    or tested.get("head") != value["head"] or tested.get("tree") != value["tree"]
                    or tested.get("committed_subject") is not True
                    or tested.get("run_id") != value["run_id"]
                    or tested.get("run_attempt") != value["run_attempt"]
                    or tested.get("state") != "TESTS_PASSED" or tested.get("optimization") != (mode == "optimized")
                    or tested.get("requirements") != expected_requirements
                    or not coverage(expected_requirements, tested.get("planned_test_ids", []), tested.get("executed", []))
                    or tested.get("source_sha256") != expected_sources
                    or not tested.get("requirements_satisfied")):
                raise Block("TEST_EXECUTION_EVIDENCE_UNBOUND")
            executed_plans.append(tested["planned_test_ids"])
            value["test_receipts"].append({"mode": mode, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                           "test_ids": [r["id"] for r in tested["executed"]]})
        if executed_plans[0] != executed_plans[1]:
            raise Block("OPTIMIZED_TEST_INVENTORY_DRIFT")
        if git("status", "--porcelain=v1", "--untracked-files=all", root=root):
            raise Block("TESTED_WORKTREE_DIRTY")
        if remote_identity(call, repository, ref) != (value["head"], value["tree"]):
            raise Block("FINAL_REMOTE_HEAD_TREE_DRIFT")
        if (git("rev-parse", "HEAD", root=root), git("rev-parse", "HEAD^{tree}", root=root)) != (value["head"], value["tree"]):
            raise Block("FINAL_LOCAL_HEAD_TREE_DRIFT")
        if (git("status", "--porcelain=v1", "--untracked-files=all", root=root)
                or source_digests(root, [MANIFEST] + manifest["source_paths"]) != expected_sources):
            raise Block("FINAL_TESTED_SOURCE_DRIFT")
        value["evidence_files"] = [
            {"path": str(p.relative_to(evidence_dir)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(evidence_dir.rglob("*"))
            if p.is_file() and p.name not in {"FINAL_EVIDENCE.json", "FINAL_EVIDENCE.json.tmp"}]
        value.update(state="EXACT_TESTS_AND_READBACK_VERIFIED", classification="WORK")
    except (Block, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "FINAL_EVIDENCE_MISSING_OR_INVALID"
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("select", "resume", "deliver", "ci-final", "observe-writer", "publish-writer", "push-readback"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()
    value = receipt("qikvrt_pipeline_operation_failure_v1")
    try:
        repository = repo(os.environ["GITHUB_REPOSITORY"])
        if args.command == "observe-writer":
            value = observe_writer(api, Path.cwd(), repository, os.environ["TARGET_REF"], os.environ.get("TARGET_BASE_REF", "main"))
        elif args.command == "publish-writer":
            if args.input is None:
                raise Block("WRITER_INPUT_NOT_BOUND")
            observed = json.loads(args.input.read_text(encoding="utf-8"))
            if observed.get("repository") != repository:
                raise Block("WRITER_REPOSITORY_MISMATCH")
            value = publish_writer(api, Path.cwd(), observed)
        elif args.command == "push-readback":
            ref = branch(os.environ["TARGET_REF"])
            value = push_postcondition(api, lambda: git("push", "origin", "HEAD:refs/heads/" + ref,
                                                       root=Path.cwd()), repository, ref,
                                       os.environ["CANDIDATE_HEAD"], os.environ["CANDIDATE_TREE"],
                                       os.environ["CURRENT_BASE"], os.environ["PREDECESSOR_HEAD"],
                                       pr_number=int(os.environ["PR_NUMBER"]) if os.environ.get("PR_NUMBER") else None)
        elif args.command == "select":
            chosen = select(listing(api, f"repos/{repository}/pulls?state=open"), repository,
                            int(os.environ["GITHUB_RUN_NUMBER"]))
            selected = None if chosen is None else {"number": chosen["number"], "head": chosen["head"]["sha"],
                                                      "base": chosen["base"]["sha"], "ref": chosen["head"]["ref"]}
            value.update(repository=repository, selected=selected,
                         state="SELECTED" if chosen else "NO_ELIGIBLE_WORK",
                         classification="WORK" if chosen else "IDLE")
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
                print("found=" + str(bool(chosen)).lower(), file=stream)
                if chosen:
                    for k, v in {"pr_number": chosen["number"], "head_ref": chosen["head"]["ref"],
                                 "head_sha": chosen["head"]["sha"], "base_ref": "main",
                                 "base_sha": chosen["base"]["sha"]}.items():
                        print(f"{k}={v}", file=stream)
        elif args.command == "resume":
            value = resume(api, repository, int(os.environ["PR_NUMBER"]), os.environ["CANDIDATE_HEAD"],
                           os.environ["CANDIDATE_TREE"], os.environ["CURRENT_BASE"], os.environ["HEAD_REF"])
        elif args.command == "deliver":
            if os.environ.get("VERIFICATION_CONTEXT") != CONTEXT:
                raise Block("VERIFICATION_CONTEXT_MISMATCH")
            steps = json.loads(os.environ["STEPS_JSON"])
            outcomes = {k: v.get("outcome", "NOT_EXECUTED") for k, v in steps.items()}
            value = deliver(api, repository, int(os.environ["TARGET_PR"]), os.environ["TARGET_SHA"],
                            os.environ["TARGET_BASE_SHA"],
                            f"https://github.com/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
                            outcomes, os.environ["QCE_REQUIRED"] == "true",
                            (git("rev-parse", "HEAD", root=Path.cwd()),
                             git("rev-parse", "HEAD^{tree}", root=Path.cwd()),
                             not bool(git("status", "--porcelain=v1", "--untracked-files=all", root=Path.cwd()))),
                            os.environ.get("TARGET_BASE_REF", "main"))
        else:
            value = final_ci(api, Path.cwd(), os.environ.get("SUBJECT_REPOSITORY", repository),
                             os.environ["SUBJECT_REF"], args.output.parent,
                             {"full_test": os.environ["FULL_TEST_OUTCOME"], "fixpoint": os.environ["FIXPOINT_OUTCOME"],
                              "fixpoint_required": os.environ["FIXPOINT_REQUIRED"]})
    except (Block, OSError, KeyError, ValueError, TypeError, AttributeError) as exc:
        value["first_blocker"] = str(exc) if isinstance(exc, Block) else "INPUT_OR_READBACK_INVALID"
    save(args.output, value)
    print(json.dumps(value, sort_keys=True))
    return 2 if value["classification"] == "BLOCKADE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
