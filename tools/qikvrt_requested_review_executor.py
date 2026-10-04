#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for requested-review execution.

The decision core is GitHub-write-free. A workflow supplies one live,
exact-head-bound snapshot; this core returns WAIT, APPROVE, REQUEST_CHANGES,
or COMMENT_WITH_BLOCKER. The workflow persists the disposition and an
exact-head commit status without impersonating a requested GitHub identity.
The native adapter rechecks admission before its single review POST. It never
requests an unverified owner, retries a rejected review, or substitutes a signer.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.qikvrt_subprocess import run_bounded

SUCCESS = {"success"}
NON_ADVERSE = {"success", "skipped"}
SELF_WORKFLOW = "QIKVRT requested review executor"


class ReviewSnapshotError(ValueError):
    pass


class GitHubRest:
    """Existing gh credential route; bounded output, no credential diagnostics."""

    def _call(self, method: str, path: str, payload: Any = None) -> dict[str, Any]:
        command = ["gh", "api", "--include", "--method", method, path]
        with tempfile.TemporaryDirectory(prefix="qikvrt-review-rest-") as directory:
            if payload is not None:
                body = pathlib.Path(directory) / "body.json"
                body.write_text(json.dumps(payload), encoding="utf-8")
                command.extend(["--input", str(body)])
            try:
                process = run_bounded(command, timeout=30, max_output_bytes=2_097_152)
            except OSError:
                return {"status": 0, "data": None}
        # Never forward gh stderr, auth headers, or an unbounded server error.
        output = process.stdout.replace("\r\n", "\n")
        match = re.search(r"^HTTP/\S+ (\d{3})[^\n]*\n", output)
        if process.timed_out or process.output_limit_exceeded or not match:
            return {"status": 0, "data": None}
        status = int(match.group(1))
        _, separator, body = output.partition("\n\n")
        try:
            data = json.loads(body) if separator and body.strip() else None
        except ValueError:
            data = None
        return {"status": status, "data": data}

    def get(self, path: str) -> dict[str, Any]:
        return self._call("GET", path)

    def post(self, path: str, payload: Any) -> dict[str, Any]:
        return self._call("POST", path, payload)


def _native_user(value: Any, login: str | None = None) -> bool:
    return (
        isinstance(value, Mapping) and value.get("type") == "User"
        and isinstance(value.get("id"), int) and not isinstance(value["id"], bool)
        and value["id"] > 0 and isinstance(value.get("login"), str)
        and bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", value["login"]))
        and (login is None or value["login"].casefold() == login.casefold())
    )


def _get(api: Any, path: str) -> dict[str, Any]:
    value = api.get(path)
    if not isinstance(value, Mapping) or not isinstance(value.get("status"), int):
        raise ReviewSnapshotError("invalid native API observation")
    return dict(value)


def _pages(api: Any, path: str) -> list[Any]:
    out: list[Any] = []
    for page in range(1, 21):
        value = _get(api, f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        if value["status"] != 200 or not isinstance(value.get("data"), list):
            raise ReviewSnapshotError("native collection unavailable or incomplete")
        out.extend(value["data"])
        if len(value["data"]) < 100:
            return out
    raise ReviewSnapshotError("native collection exceeds bounded pagination")


def codeowners_for_paths(content: str, paths: list[str]) -> dict[str, list[str]]:
    """Use Git's last matching gitignore rule, including ownerless overrides.

    Unsupported CODEOWNERS constructs fail closed. Candidate CODEOWNERS bytes
    never replace the current base-branch authority.
    """
    if not isinstance(content, str) or len(content.encode("utf-8")) > 3_000_000:
        raise ReviewSnapshotError("CODEOWNERS content is missing or oversized")
    if not paths or len(paths) > 1000:
        raise ReviewSnapshotError("CODEOWNERS scope is empty or exceeds bound")
    for path in paths:
        if (not isinstance(path, str) or not path or path.startswith("/")
                or "\\" in path or ".." in pathlib.PurePosixPath(path).parts
                or any(ord(c) < 32 for c in path)):
            raise ReviewSnapshotError("invalid CODEOWNERS scope path")
    rules: list[tuple[str, list[str]]] = []
    for line in content.splitlines():
        parts = line.split("#", 1)[0].split()
        if not parts:
            continue
        pattern, *owners = parts
        if pattern.startswith("!") or any(c in pattern for c in "[]\\"):
            raise ReviewSnapshotError("unsupported CODEOWNERS pattern")
        if not all(re.fullmatch(r"@[A-Za-z0-9][A-Za-z0-9-]{0,38}(?:/[A-Za-z0-9][A-Za-z0-9_-]{0,99})?", owner) for owner in owners):
            raise ReviewSnapshotError("unsupported CODEOWNERS identity")
        if len(pattern) > 512 or len(rules) >= 256:
            raise ReviewSnapshotError("CODEOWNERS pattern bound exceeded")
        rules.append((pattern, owners))
    scopes = {path: [] for path in paths}
    with tempfile.TemporaryDirectory(prefix="qikvrt-codeowners-") as directory:
        root = pathlib.Path(directory)
        initialized = run_bounded(["git", "init", "--quiet", directory], timeout=10)
        if initialized.returncode:
            raise ReviewSnapshotError("CODEOWNERS matcher unavailable")
        empty = root / "empty-global-ignore"
        empty.write_text("", encoding="utf-8")
        # Evaluate patterns separately. Gitignore's excluded-parent pruning
        # must not conceal a later, more specific CODEOWNERS override.
        for pattern, owners in rules:
            (root / ".gitignore").write_text(pattern + "\n", encoding="utf-8")
            result = run_bounded(["git", "-c", f"core.excludesFile={empty}", "-c", "core.quotePath=false", "check-ignore", "--no-index", "--verbose", "--non-matching", "--", *paths], cwd=root, timeout=10)
            if result.returncode not in (0, 1) or result.output_limit_exceeded or result.timed_out:
                raise ReviewSnapshotError("CODEOWNERS matching failed")
            observed = set()
            for line in result.stdout.splitlines():
                source, separator, path = line.partition("\t")
                if not separator:
                    raise ReviewSnapshotError("CODEOWNERS scope matching incomplete")
                if path.startswith('"'):
                    path = json.loads(path)
                if path not in scopes or path in observed:
                    raise ReviewSnapshotError("CODEOWNERS scope mismatch")
                observed.add(path)
                origin, number, _ = source.split(":", 2)
                if origin:
                    if origin != ".gitignore" or number != "1":
                        raise ReviewSnapshotError("foreign CODEOWNERS pattern source")
                    scopes[path] = owners
            if observed != set(paths):
                raise ReviewSnapshotError("CODEOWNERS scope matching incomplete")
    return scopes


def collect_reviewer_admission(snapshot: Mapping[str, Any], api: Any) -> dict[str, Any]:
    """Read-only native admission. Permission projections alone cannot pass.

    GitHub exposes no REST dry-run of reviewer request validation. A current
    accepted native request is therefore required before calling a reviewer
    reachable. Potentially valid metadata without that request remains WAIT.
    """
    binding = {key: snapshot.get(key) for key in ("repository", "pr_number", "current_main_sha", "head_sha", "tree_sha")}
    result: dict[str, Any] = {
        "schema": "qikvrt_reviewer_admission_v1", "binding": binding,
        "state": "HOLD", "first_blocker": None, "detail": "",
        "codeowners_source": None, "scope_owners": {}, "candidates": [],
        "active_codeowners": [], "reachable_independent_reviewer": False,
        "independent_natural_person_verified": False, "review_request_post_count": 0,
    }

    def finish(state: str, blocker: str | None, detail: str) -> dict[str, Any]:
        result.update(state=state, first_blocker=blocker, detail=detail)
        result["transition_fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return result

    try:
        repo = snapshot.get("repository")
        if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo):
            raise ReviewSnapshotError("invalid repository identity")
        main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
        metadata = _get(api, f"repos/{repo}")
        if metadata["status"] != 200 or not isinstance(metadata.get("data"), Mapping):
            return finish("HOLD", "REPOSITORY_METADATA_UNAVAILABLE", "native repository metadata unavailable")
        repository = metadata["data"]
        if repository.get("full_name", "").casefold() != repo.casefold():
            raise ReviewSnapshotError("native repository identity differs")
        author = snapshot.get("pr_author")
        if not _native_user(author):
            raise ReviewSnapshotError("native PR-author identity is missing")
        files = snapshot.get("changed_paths")
        if not isinstance(files, list):
            raise ReviewSnapshotError("native changed scope is missing")
        owner_file = None
        for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
            response = _get(api, f"repos/{repo}/contents/{path}?ref={main}")
            if response["status"] == 404:
                continue
            if response["status"] != 200 or not isinstance(response.get("data"), Mapping):
                return finish("HOLD", "CODEOWNERS_METADATA_UNAVAILABLE", "base CODEOWNERS could not be read")
            owner_file = response["data"]
            encoded = owner_file.get("content")
            if owner_file.get("encoding") != "base64" or not isinstance(encoded, str):
                raise ReviewSnapshotError("native CODEOWNERS bytes unavailable")
            raw = base64.b64decode("".join(encoded.split()), validate=True)
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if blob != owner_file.get("sha"):
                raise ReviewSnapshotError("native CODEOWNERS blob mismatch")
            result["codeowners_source"] = {"path": path, "ref": main, "git_blob_sha1": blob}
            result["scope_owners"] = codeowners_for_paths(raw.decode("utf-8"), files)
            break
        if owner_file is None:
            return finish("HOLD", "CODEOWNERS_MISSING", "no CODEOWNERS authority on current base branch")
        errors = _get(api, f"repos/{repo}/codeowners/errors?ref={main}")
        if errors["status"] != 200 or not isinstance(errors.get("data"), Mapping) or not isinstance(errors["data"].get("errors"), list):
            return finish("HOLD", "CODEOWNERS_VALIDATION_UNAVAILABLE", "native CODEOWNERS validation unavailable")
        if errors["data"]["errors"]:
            return finish("HOLD", "CODEOWNERS_NATIVE_ERRORS", "GitHub reports invalid base CODEOWNERS entries")
        requested = _get(api, f"repos/{repo}/pulls/{snapshot['pr_number']}/requested_reviewers")
        if requested["status"] != 200 or not isinstance(requested.get("data"), Mapping):
            return finish("HOLD", "NATIVE_REVIEW_REQUESTS_UNAVAILABLE", "native review requests could not be observed")
        people = requested["data"].get("users")
        teams = requested["data"].get("teams")
        if not isinstance(people, list) or not isinstance(teams, list):
            raise ReviewSnapshotError("invalid native request collection")
        for target in sorted({owner for owners in result["scope_owners"].values() for owner in owners}):
            candidate: dict[str, Any] = {"target": target, "metadata_verified": False, "active_request": False, "first_blocker": None}
            result["candidates"].append(candidate)
            if "/" not in target:
                login = target[1:]
                user = _get(api, f"users/{login}")
                candidate["identity_http_status"] = user["status"]
                if user["status"] != 200 or not _native_user(user.get("data"), login):
                    candidate["first_blocker"] = "CODEOWNER_IDENTITY_UNRESOLVABLE"
                    continue
                native = user["data"]
                candidate["identity"] = {k: native[k] for k in ("login", "id", "type")}
                if native["id"] == author["id"] or native["login"].casefold() == author["login"].casefold():
                    candidate["first_blocker"] = "CODEOWNER_SELF_REVIEW"
                    continue
                member = _get(api, f"repos/{repo}/collaborators/{login}")
                candidate["collaborator_http_status"] = member["status"]
                if member["status"] != 204:
                    candidate["first_blocker"] = "CODEOWNER_COLLABORATION_NOT_CONFIRMED"
                    continue
                permission = _get(api, f"repos/{repo}/collaborators/{login}/permission")
                value = permission.get("data")
                candidate["permission_http_status"] = permission["status"]
                if permission["status"] != 200 or not isinstance(value, Mapping) or not _native_user(value.get("user"), login) or value["user"]["id"] != native["id"]:
                    candidate["first_blocker"] = "CODEOWNER_PERMISSION_IDENTITY_UNVERIFIED"
                    continue
                candidate["permission"] = value.get("permission")
                if value.get("permission") not in {"write", "admin"}:
                    candidate["first_blocker"] = "CODEOWNER_WRITE_PERMISSION_MISSING"
                    continue
                candidate["metadata_verified"] = True
                candidate["active_request"] = any(_native_user(person, login) and person["id"] == native["id"] for person in people)
            else:
                org, slug = target[1:].split("/", 1)
                repo_owner = repository.get("owner", {})
                if repo_owner.get("type") != "Organization" or repo_owner.get("login", "").casefold() != org.casefold():
                    candidate["first_blocker"] = "CODEOWNER_TEAM_REPOSITORY_MISMATCH"
                    continue
                team = _get(api, f"orgs/{org}/teams/{slug}")
                value = team.get("data")
                if team["status"] != 200 or not isinstance(value, Mapping) or value.get("slug", "").casefold() != slug.casefold() or not isinstance(value.get("id"), int) or isinstance(value["id"], bool) or value["id"] <= 0 or value.get("organization", {}).get("id") != repo_owner.get("id"):
                    candidate["first_blocker"] = "CODEOWNER_TEAM_IDENTITY_UNVERIFIED"
                    continue
                if value.get("privacy") != "closed":
                    candidate["first_blocker"] = "CODEOWNER_TEAM_NOT_VISIBLE"
                    continue
                access = _get(api, f"orgs/{org}/teams/{slug}/repos/{repo}")
                data = access.get("data")
                if access["status"] != 200 or not isinstance(data, Mapping) or data.get("full_name", "").casefold() != repo.casefold() or data.get("permissions", {}).get("push") is not True:
                    candidate["first_blocker"] = "CODEOWNER_TEAM_WRITE_PERMISSION_MISSING"
                    continue
                members = _pages(api, f"orgs/{org}/teams/{slug}/members?role=all")
                if not any(_native_user(member) and member["id"] != author["id"] and member["login"].casefold() != author["login"].casefold() for member in members):
                    candidate["first_blocker"] = "CODEOWNER_TEAM_NO_INDEPENDENT_MEMBER"
                    continue
                candidate["identity"] = {"id": value["id"], "slug": value["slug"], "organization_id": repo_owner["id"]}
                candidate["metadata_verified"] = True
                candidate["active_request"] = any(isinstance(t, Mapping) and t.get("id") == value["id"] and t.get("slug", "").casefold() == slug.casefold() for t in teams)
            if candidate["active_request"]:
                result["active_codeowners"].append(target)
        for path, owners in result["scope_owners"].items():
            matching = [c for c in result["candidates"] if c["target"] in owners]
            if not matching:
                return finish("HOLD", "CODEOWNER_SCOPE_UNCOVERED", f"base CODEOWNERS does not cover {path}")
            if not any(c["metadata_verified"] for c in matching):
                failed = matching[0]
                return finish("HOLD", failed["first_blocker"], f"{failed['target']} cannot carry independent review for {path}")
        if any(not any(c["target"] in owners and c["active_request"] for c in result["candidates"]) for owners in result["scope_owners"].values()):
            return finish("WAIT", "NO_ACTIVE_REVIEW_REQUEST", "verified CODEOWNER metadata has no current native accepted review request; no request retry or substitute reviewer")
        result["reachable_independent_reviewer"] = True
        return finish("VERIFIED_ACTIVE_REQUEST", None, "native accepted request, stable CODEOWNER identity and write access verified; no independent approval implied")
    except (KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        # No remote response body or credential-bearing subprocess error.
        return finish("HOLD", "REVIEWER_ADMISSION_METADATA_INVALID", f"reviewer metadata invalid or incomplete ({type(exc).__name__})")


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewSnapshotError(f"{label} is not a Git SHA-1")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ReviewSnapshotError(f"{label} is not lowercase hexadecimal")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReviewSnapshotError("workflow run_number must be an integer")
    return value


def collapse_latest(runs: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise ReviewSnapshotError("workflow run name is missing")
        if name == SELF_WORKFLOW:
            continue
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _result(snapshot: Mapping[str, Any], state: str, blocker: str | None, detail: str) -> dict[str, Any]:
    admission = snapshot.get("reviewer_admission", {})
    return {
        "schema": "qikvrt_requested_review_decision_v1",
        "state": state,
        "first_blocker": blocker,
        "detail": detail,
        "repository": snapshot.get("repository"),
        "pr_number": snapshot.get("pr_number"),
        "base_sha": snapshot.get("base_sha"),
        "head_sha": snapshot.get("head_sha"),
        "tree_sha": snapshot.get("tree_sha"),
        "reviewed_scope": snapshot.get("changed_paths", []),
        "reviewer_admission": admission,
        "review_effect_allowed": (
            isinstance(admission, Mapping) and admission.get("state") == "VERIFIED_ACTIVE_REQUEST"
            and admission.get("reachable_independent_reviewer") is True
            and state in {"APPROVE", "REQUEST_CHANGES", "COMMENT_WITH_BLOCKER"}
            and snapshot.get("head_sha") == snapshot.get("observed_head_sha")
            and snapshot.get("base_sha") == snapshot.get("current_main_sha")
            and snapshot.get("draft") is False
        ),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "INDEPENDENT_CODE_OWNER_APPROVAL": False,
        },
    }


def evaluate(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ReviewSnapshotError("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    head = _sha(snapshot.get("head_sha"), "head_sha")
    observed_head = _sha(snapshot.get("observed_head_sha"), "observed_head_sha")
    _sha(snapshot.get("tree_sha"), "tree_sha")

    if observed_head != head:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "HEAD_DRIFT", f"observed head {observed_head} != bound head {head}")
    admission = snapshot.get("reviewer_admission")
    if not isinstance(admission, Mapping):
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "REVIEWER_ADMISSION_MISSING", "native reviewer admission must be observed before review effects")
    binding = {key: snapshot.get(key) for key in ("repository", "pr_number", "current_main_sha", "head_sha", "tree_sha")}
    digest = hashlib.sha256(json.dumps({k: v for k, v in admission.items() if k != "transition_fingerprint"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if admission.get("schema") != "qikvrt_reviewer_admission_v1" or admission.get("binding") != binding or admission.get("transition_fingerprint") != digest:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "REVIEWER_ADMISSION_DRIFT", "native reviewer admission does not bind this exact subject")
    if admission.get("state") != "VERIFIED_ACTIVE_REQUEST" or admission.get("reachable_independent_reviewer") is not True:
        return _result(snapshot, "WAIT" if admission.get("state") == "WAIT" else "COMMENT_WITH_BLOCKER", admission.get("first_blocker") or "REVIEWER_ADMISSION_UNVERIFIED", admission.get("detail") or "native review admission is not verified")
    if base != current_main:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "BASE_DRIFT", f"base {base} != current main {current_main}")
    if snapshot.get("draft") is True:
        return _result(snapshot, "WAIT", "DRAFT", "requested candidate is still draft")

    requested = snapshot.get("requested_reviewers", [])
    requested_teams = snapshot.get("requested_team_reviewers", [])
    if not isinstance(requested, list) or not isinstance(requested_teams, list):
        raise ReviewSnapshotError("requested reviewer collections must be lists")
    if not requested and not requested_teams:
        return _result(snapshot, "WAIT", "NO_ACTIVE_REVIEW_REQUEST", "no requested reviewer remains")

    changed_paths = snapshot.get("changed_paths")
    if not isinstance(changed_paths, list) or not all(isinstance(path, str) and path for path in changed_paths):
        raise ReviewSnapshotError("changed_paths must be a list of non-empty strings")
    if not changed_paths:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "EMPTY_SCOPE", "requested review has no changed paths")

    unresolved = snapshot.get("unresolved_review_threads", 0)
    if isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0:
        raise ReviewSnapshotError("unresolved_review_threads must be a non-negative integer")
    if unresolved:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "UNRESOLVED_REVIEW_THREADS", f"{unresolved} unresolved review thread(s)")

    required = snapshot.get("required_gates")
    runs = snapshot.get("workflow_runs")
    if not isinstance(required, list) or not required or not all(isinstance(name, str) and name for name in required):
        raise ReviewSnapshotError("required_gates must be a non-empty list")
    if not isinstance(runs, list):
        raise ReviewSnapshotError("workflow_runs must be a list")
    latest = collapse_latest(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _result(snapshot, "WAIT", "REQUIRED_GATE_MISSING", f"required exact-head gate is absent: {gate}")
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "REQUIRED_GATE_NOT_TERMINAL", f"required exact-head gate is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS:
            return _result(snapshot, "REQUEST_CHANGES", "REQUIRED_GATE_FAILED", f"required exact-head gate failed: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "APPLICABLE_GATE_NOT_TERMINAL", f"applicable exact-head gate is not terminal: {name}")
        if run.get("conclusion") not in NON_ADVERSE:
            return _result(snapshot, "REQUEST_CHANGES", "APPLICABLE_GATE_FAILED", f"applicable exact-head gate is adverse: {name}={run.get('conclusion')}")

    return _result(snapshot, "APPROVE", None, "exact-head scope inspected; all observed applicable gates are terminal non-adverse and no unresolved review thread remains")


def persist_review(snapshot: Mapping[str, Any], decision: Mapping[str, Any], api: Any, *, signer: Mapping[str, Any], body: str) -> dict[str, Any]:
    """One guarded POST and independent native readback; never blind retry.

    Metadata failure is persisted as an artifact/status by the wrapper, never
    as a fabricated review. This adapter cannot POST requested_reviewers.
    """
    receipt = {"schema": "qikvrt_native_review_effect_v1", "state": "HOLD", "first_blocker": None,
               "head_sha": snapshot.get("head_sha"), "review_post_count": 0,
               "independent_code_owner_approval": False, "effect_ack_done": False}

    def block(reason: str) -> dict[str, Any]:
        receipt["first_blocker"] = reason
        return receipt

    recomputed = evaluate(snapshot)
    if decision != recomputed or decision.get("review_effect_allowed") is not True:
        return block("REVIEW_EFFECT_NOT_ADMITTED")
    repo, number, head = snapshot["repository"], snapshot["pr_number"], snapshot["head_sha"]
    try:
        pr = _get(api, f"repos/{repo}/pulls/{number}")
        if pr["status"] != 200 or not isinstance(pr.get("data"), Mapping):
            return block("PREWRITE_PR_UNAVAILABLE")
        current = pr["data"]
        if (current.get("state") != "open" or current.get("draft") is not False
                or current.get("head", {}).get("sha") != head):
            return block("PREWRITE_HEAD_OR_STAGE_DRIFT")
        if (not isinstance(signer, Mapping) or not isinstance(signer.get("id"), int)
                or isinstance(signer["id"], bool) or signer["id"] <= 0
                or signer.get("type") not in {"User", "Bot"} or not isinstance(signer.get("login"), str)):
            return block("NATIVE_REVIEW_SIGNER_UNVERIFIED")
        author = current.get("user", {})
        if author.get("id") == signer["id"] or author.get("login", "").casefold() == signer["login"].casefold():
            return block("NATIVE_REVIEW_SIGNER_SELF_APPROVAL")
        main = _get(api, f"repos/{repo}/commits/main")
        tree = _get(api, f"repos/{repo}/git/commits/{head}")
        if (main["status"] != 200 or tree["status"] != 200
                or not isinstance(main.get("data"), Mapping) or not isinstance(tree.get("data"), Mapping)
                or main["data"].get("sha") != snapshot["current_main_sha"]
                or current.get("base", {}).get("sha") != snapshot["base_sha"]
                or tree["data"].get("tree", {}).get("sha") != snapshot["tree_sha"]):
            return block("PREWRITE_BASE_OR_TREE_DRIFT")
        paths = _pages(api, f"repos/{repo}/pulls/{number}/files")
        if sorted(file["filename"] for file in paths) != sorted(snapshot["changed_paths"]):
            return block("PREWRITE_SCOPE_DRIFT")
        fresh = dict(snapshot, pr_author=author)
        admission = collect_reviewer_admission(fresh, api)
        if admission != snapshot["reviewer_admission"]:
            return block(admission.get("first_blocker") or "PREWRITE_REVIEWER_ADMISSION_DRIFT")
        event = "COMMENT" if decision["state"] == "COMMENT_WITH_BLOCKER" else decision["state"]
        expected_state = {"APPROVE": "APPROVED", "COMMENT": "COMMENTED", "REQUEST_CHANGES": "CHANGES_REQUESTED"}[event]
        receipt["native_rejection_fingerprint"] = hashlib.sha256(json.dumps({
            "admission": admission["transition_fingerprint"], "signer": dict(signer), "event": event,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

        def matching_reviews() -> list[Mapping[str, Any]]:
            return [review for review in _pages(api, f"repos/{repo}/pulls/{number}/reviews")
                    if isinstance(review, Mapping) and isinstance(review.get("id"), int)
                    and not isinstance(review["id"], bool) and review["id"] > 0 and review.get("commit_id") == head
                    and review.get("body") == body and review.get("user", {}).get("id") == signer["id"]
                    and review.get("state") == expected_state]

        prior = matching_reviews()
        if len(prior) > 1:
            return block("DUPLICATE_NATIVE_REVIEW_EFFECT")
        if not prior:
            statuses = _pages(api, f"repos/{repo}/statuses/{head}")
            previous = next((s for s in statuses if isinstance(s, Mapping) and s.get("context") == "QIKVRT requested review execution"), None)
            if previous and previous.get("state") == "failure" and previous.get("description") == "review rejection: " + receipt["native_rejection_fingerprint"]:
                return block("UNCHANGED_NATIVE_REVIEW_REJECTION")
            last = _get(api, f"repos/{repo}/pulls/{number}")
            if last["status"] != 200 or last.get("data", {}).get("head", {}).get("sha") != head:
                return block("PREWRITE_HEAD_DRIFT")
            receipt["review_post_count"] = 1
            try:
                response = api.post(f"repos/{repo}/pulls/{number}/reviews", {"commit_id": head, "event": event, "body": body})
            except OSError:
                response = {"status": 0}
            receipt["post_http_status"] = response.get("status", 0)
            # Read even after transport loss. No second POST, including COMMENT.
            prior = matching_reviews()
            if len(prior) != 1:
                return block("NATIVE_REVIEW_REJECTED" if response.get("status") in {401, 403, 422} else "NATIVE_REVIEW_READBACK_UNVERIFIED")
        receipt.update(review_id=prior[0].get("id"), platform_state=expected_state)
        final = _get(api, f"repos/{repo}/pulls/{number}")
        if final["status"] != 200 or final.get("data", {}).get("head", {}).get("sha") != head:
            return block("POSTWRITE_HEAD_DRIFT")
        receipt["state"] = "VERIFIED_NATIVE_REVIEW"
        return receipt
    except (KeyError, TypeError, ValueError, AttributeError, OSError):
        return block("NATIVE_REVIEW_METADATA_UNAVAILABLE")


def _load(path: str) -> Mapping[str, Any]:
    value = json.load(sys.stdin) if path == "-" else json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate", "preflight", "persist"))
    parser.add_argument("--input", default="-")
    parser.add_argument("--decision")
    parser.add_argument("--signer")
    parser.add_argument("--body")
    args = parser.parse_args(argv)
    try:
        snapshot = _load(args.input)
        if args.command == "preflight":
            result = collect_reviewer_admission(snapshot, GitHubRest())
        elif args.command == "persist":
            if not args.decision or not args.signer or not args.body:
                raise ReviewSnapshotError("persist requires decision, signer and body")
            result = persist_review(snapshot, _load(args.decision), GitHubRest(), signer=json.loads(args.signer), body=pathlib.Path(args.body).read_text(encoding="utf-8"))
        else:
            result = evaluate(snapshot)
    except (OSError, ValueError, json.JSONDecodeError, ReviewSnapshotError) as exc:
        result = {
            "schema": "qikvrt_requested_review_decision_v1",
            "state": "COMMENT_WITH_BLOCKER",
            "first_blocker": "INVALID_REVIEW_SNAPSHOT",
            "detail": str(exc),
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"WAIT", "APPROVE", "VERIFIED_ACTIVE_REQUEST", "VERIFIED_NATIVE_REVIEW"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
