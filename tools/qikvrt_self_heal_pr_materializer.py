#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Resume the existing self-heal branch/PR transaction by verified postcondition.

Reuses the materializer prepared in PR #455 at d893de1d, narrowed to the
self-heal branch/PR postcondition without its unactivated verifier dependency.
It never merges, approves, edits an existing PR, changes permissions, or retries
an ambiguous POST. All remote GitHub reads and writes use REST.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode


MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SHA1 = re.compile(r"[0-9a-f]{40}")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")


class Block(RuntimeError):
    """Credential-free, stable causal code."""


class ApiFailure(Block):
    def __init__(self, status: int | None):
        self.status = status
        super().__init__(f"API_HTTP_{status}" if status else "API_TRANSPORT_UNCERTAIN")


def api(method: str, path: str, data: Any = None) -> Any:
    if method not in {"GET", "POST"} or not path.startswith("repos/"):
        raise Block("API_SCOPE_INVALID")
    if method == "POST" and not re.fullmatch(
            r"repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(git/(blobs|trees|commits|refs)|pulls)", path):
        raise Block("API_SCOPE_INVALID")
    command = ["gh", "api", "--hostname", "github.com", "--method", method, path,
               "-H", "Accept: application/vnd.github+json",
               "-H", "X-GitHub-Api-Version: 2022-11-28"]
    if data is not None:
        command += ["--input", "-"]
    try:
        result = subprocess.run(command, input=None if data is None else json.dumps(data),
                                text=True, capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ApiFailure(None) from exc
    if result.returncode:
        match = re.search(r"HTTP (\d{3})", result.stderr)
        raise ApiFailure(int(match[1]) if match else None)
    if not result.stdout.strip():
        raise Block("API_RESPONSE_INVALID")
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise Block("API_RESPONSE_INVALID") from exc


class GitHubAPI:
    def __call__(self, method: str, path: str, data: Any = None) -> Any:
        return api(method, path, data)


class Git:
    def __call__(self, *args: str) -> str:
        return self.bytes(*args).decode("utf-8").strip()

    def bytes(self, *args: str) -> bytes:
        try:
            result = subprocess.run(["git", *args], capture_output=True,
                                    timeout=120, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise Block("GIT_OPERATION_UNCERTAIN") from exc
        if result.returncode:
            raise Block("GIT_OPERATION_FAILED")
        return result.stdout


@dataclass(frozen=True)
class Candidate:
    repository: str
    base: str
    tree: str
    identity: str
    paths: tuple[str, ...]
    fingerprint: str

    @property
    def branch(self) -> str:
        return f"automation/self-heal-{self.identity[:24]}"


def prepare(receipt: dict[str, Any], repository: str, git: Git) -> Candidate:
    # Reuse the existing allowlist, authorization, fingerprint and identity.
    from tools import qikvrt_autonomous_self_heal as controller
    try:
        contract = controller.load_contract()
    except controller.SelfHealBlock as exc:
        raise Block("CONTROLLER_CONTRACT_INVALID") from exc
    if contract.get("candidate_contract", {}).get("materialization", {}).get(
            "completion_predicate") != "EXACT_CURRENT_BASE_HEAD_TREE_PR_READBACK":
        raise Block("MATERIALIZATION_CONTRACT_MISMATCH")
    if not isinstance(receipt, dict):
        raise Block("CANDIDATE_RECEIPT_INVALID")
    base = receipt.get("observed_base_revision", "")
    paths = receipt.get("changed_paths", [])
    if (not REPOSITORY.fullmatch(repository) or not isinstance(base, str) or not SHA1.fullmatch(base)
            or receipt.get("state") != "CANDIDATE_READY"
            or receipt.get("external_effect") != "NONE"
            or receipt.get("completion_claims", {}).get("EFFECT_ACK_DONE") is not False):
        raise Block("CANDIDATE_RECEIPT_INVALID")
    if (not isinstance(paths, list) or not paths
            or any(not isinstance(p, str) for p in paths)
            or len(paths) != len(set(paths))
            or not set(paths).issubset(controller.allowed_paths(contract))):
        raise Block("CANDIDATE_PATHS_NOT_ALLOWLISTED")
    if (git("remote", "get-url", "--all", "origin").removesuffix(".git")
            != f"https://github.com/{repository}"
            or git("rev-parse", "HEAD") != base
            or git("diff", "--cached", "--name-only")
            or git("ls-files", "--others", "--exclude-standard")
            or sorted(git("diff", "--name-only").splitlines()) != sorted(paths)):
        raise Block("LOCAL_CANDIDATE_BINDING_MISMATCH")
    fingerprint = controller.semantic_fingerprint(paths)
    identity = controller.candidate_identity(base, fingerprint)
    if (fingerprint != receipt.get("semantic_fingerprint")
            or identity != receipt.get("candidate_identity")):
        raise Block("CANDIDATE_FINGERPRINT_MISMATCH")
    git("add", "--", *paths)
    for path in paths:
        mode = git("ls-files", "--stage", "--", path).split(" ", 1)[0]
        if mode not in ("100644", "100755"):
            raise Block("CANDIDATE_FILE_MODE_INVALID")
    return Candidate(repository, base, git("write-tree"), identity, tuple(sorted(paths)), fingerprint)


def materialize(candidate: Candidate, api: Any, git: Any) -> dict[str, Any]:
    """One bounded attempt; a later invocation resumes from remote observations."""
    c = candidate
    prefix = f"repos/{c.repository}"
    ref_path = f"{prefix}/git/ref/heads/{c.branch}"
    result: dict[str, Any] = {
        "schema": "qikvrt_self_heal_materialization_v1",
        "repository": c.repository, "base_head": c.base, "candidate_tree": c.tree,
        "candidate_identity": c.identity, "semantic_fingerprint": c.fingerprint, "branch": c.branch,
        "candidate_head": None, "pr_number": None, "state": "HOLD",
        "classification": "BLOCKADE", "first_blocker": None,
        "PREDECESSOR_EVIDENCE_TRANSFER": False, "EFFECT_ACK_DONE": False,
        "transport_ack_is_effect_ack": False, "pr_create_attempted": False,
        "handoff_effect_verified": False, "code_owner_approval_verified": False,
        "main_activation_verified": False, "github_route": "REST_API_ONLY",
    }

    def current_base() -> None:
        value = api("GET", f"{prefix}/git/ref/heads/main")["object"]
        if value["type"] != "commit" or value["sha"] != c.base:
            raise Block("BASE_DRIFT")

    def branch_head() -> str | None:
        try:
            value = api("GET", ref_path)["object"]
            if value["type"] != "commit":
                raise Block("CANDIDATE_HEAD_INVALID")
            return value["sha"]
        except ApiFailure as exc:
            if exc.status == 404:
                return None  # Only after a successful current-main read.
            raise

    def verify_commit(head: str) -> None:
        if not SHA1.fullmatch(head):
            raise Block("CANDIDATE_HEAD_INVALID")
        commit = api("GET", f"{prefix}/git/commits/{head}")
        if (commit["sha"] != head or commit["tree"]["sha"] != c.tree
                or [p["sha"] for p in commit["parents"]] != [c.base]):
            raise Block("EXISTING_BRANCH_BINDING_MISMATCH")

    def pull_requests() -> list[dict[str, Any]]:
        # All states, no base filter: closed/wrong-base PRs must not be hidden.
        query = urlencode({"state": "all", "head": f"{c.repository.split('/')[0]}:{c.branch}",
                           "per_page": 100})
        values = api("GET", f"{prefix}/pulls?{query}")
        if not isinstance(values, list) or len(values) >= 100:
            raise Block("PR_ENUMERATION_INCOMPLETE")
        if len(values) > 1:
            raise Block("DUPLICATE_CANDIDATE_PRS")
        return values

    try:
        from tools import qikvrt_autonomous_self_heal as controller
        if (not REPOSITORY.fullmatch(c.repository) or not SHA1.fullmatch(c.base)
                or not SHA1.fullmatch(c.tree)
                or controller.candidate_identity(c.base, c.fingerprint) != c.identity
                or not c.paths or len(set(c.paths)) != len(c.paths)
                or not set(c.paths).issubset(controller.allowed_paths(controller.load_contract()))):
            raise Block("CANDIDATE_IDENTITY_MISMATCH")
        current_base()
        head = branch_head()
        if head is None:
            if pull_requests():
                raise Block("PR_EXISTS_WITHOUT_CANDIDATE_BRANCH")
            # Upload immutable objects, then create the ref with REST create-only
            # semantics. No force push, ref update, or Git hook is involved.
            entries = []
            for path in c.paths:
                row = git("ls-tree", c.tree, "--", path)
                metadata, actual_path = row.split("\t", 1)
                mode, kind, blob = metadata.split()
                if actual_path != path or mode not in ("100644", "100755") or kind != "blob":
                    raise Block("CANDIDATE_FILE_MODE_INVALID")
                payload = git.bytes("cat-file", "blob", blob)
                created = api("POST", f"{prefix}/git/blobs", {
                    "encoding": "base64", "content": base64.b64encode(payload).decode("ascii")})
                if created["sha"] != blob:
                    raise Block("BLOB_WRITE_READBACK_MISMATCH")
                entries.append({"path": path, "mode": mode, "type": "blob", "sha": blob})
            base_tree = api("GET", f"{prefix}/git/commits/{c.base}")["tree"]["sha"]
            tree = api("POST", f"{prefix}/git/trees", {"base_tree": base_tree, "tree": entries})
            if tree["sha"] != c.tree:
                raise Block("TREE_WRITE_READBACK_MISMATCH")
            commit = api("POST", f"{prefix}/git/commits", {
                "message": f"fix(autonomy): apply bounded deterministic self-heal {c.identity[:16]}",
                "tree": c.tree, "parents": [c.base]})
            verify_commit(commit["sha"])
            current_base()
            ref_error = None
            try:
                api("POST", f"{prefix}/git/refs", {
                    "ref": f"refs/heads/{c.branch}", "sha": commit["sha"]})
            except Block as exc:
                ref_error = exc
            # A lost response or a concurrent create is resolved by readback.
            head = branch_head()
            if head is None:
                if isinstance(ref_error, ApiFailure) and ref_error.status in (401, 403):
                    raise Block("BRANCH_WRITER_CAPABILITY_UNAVAILABLE")
                raise Block("BRANCH_CREATION_NOT_READ_BACK")
        result["candidate_head"] = head
        verify_commit(head)
        current_base()
        def stable_subject() -> None:
            current_base()
            if branch_head() != head:
                raise Block("CANDIDATE_HEAD_DRIFT")
            verify_commit(head)

        def read_pr() -> dict[str, Any] | None:
            values = pull_requests()
            if not values:
                return None
            number = values[0]["number"]
            if isinstance(number, bool) or not isinstance(number, int) or number < 1:
                raise Block("PR_READBACK_INVALID")
            # Never accept the list or POST response as the independent PR readback.
            pr = api("GET", f"{prefix}/pulls/{number}")
            if pr["number"] != number:
                raise Block("PR_EXACT_BINDING_MISMATCH")
            if pr["state"] != "open":
                raise Block("CANDIDATE_PR_CLOSED")
            for side, ref, sha in (("head", c.branch, head), ("base", "main", c.base)):
                binding = pr[side]
                listed = values[0][side]
                if (binding["repo"]["full_name"] != c.repository
                        or binding["ref"] != ref or binding["sha"] != sha
                        or (listed["repo"]["full_name"], listed["ref"], listed["sha"])
                        != (c.repository, ref, sha)):
                    raise Block("PR_EXACT_BINDING_MISMATCH")
            return pr

        pr = read_pr()
        created = pr is None
        if created:
            stable_subject()
            result["pr_create_attempted"] = True
            post_error = None
            # Keep the existing proposal-only marker; do not opt an existing PR in.
            body = (f"{MARKER}\n\nRepository-native bounded repair.\n\n"
                    f"- repository: `{c.repository}`\n"
                    f"- observed main base: `{c.base}`\n"
                    f"- candidate head: `{head}`\n"
                    f"- candidate tree: `{c.tree}`\n"
                    f"- semantic fingerprint: `{c.fingerprint}`\n"
                    f"- candidate identity: `{c.identity}`\n\n"
                    + "\n".join(f"- `{p}`" for p in c.paths)
                    + "\n\nDraft handoff only. Native Code-Owner approval, enforced "
                      "governance, all exact-head gates and Main activation remain separate. "
                      "No merge, approval, permission change or external effect is performed. "
                      "PREDECESSOR_EVIDENCE_TRANSFER=false; EFFECT_ACK_DONE=false.\n")
            try:
                api("POST", f"{prefix}/pulls", {
                    "draft": True, "base": "main", "head": c.branch,
                    "title": f"fix(autonomy): bounded deterministic self-heal {c.identity[:16]}",
                    "body": body})
            except Block as exc:
                post_error = exc
            # A permission denial, duplicate race or lost response never causes a
            # blind POST retry. Only independently verified remote effect can pass.
            pr = read_pr()
            if pr is None:
                if isinstance(post_error, ApiFailure) and post_error.status in (401, 403):
                    raise Block("PR_WRITER_CAPABILITY_UNAVAILABLE")
                raise Block("PR_CREATION_NOT_READ_BACK")
            if pr.get("draft") is not True:
                raise Block("CREATED_PR_DRAFT_BOUNDARY_MISMATCH")
        result["pr_number"] = pr["number"]
        stable_subject()
        # Reobserve the full PR after the final head/base read; detect concurrent
        # retargeting or closure instead of carrying the previous GET forward.
        if read_pr()["number"] != pr["number"]:
            raise Block("PR_EXACT_BINDING_MISMATCH")
        stable_subject()
        result.update(state="PR_MATERIALIZED" if created else "NOOP",
                      classification="HANDOFF_VERIFIED" if created else "NOOP",
                      handoff_effect_verified=True)

    except (Block, controller.SelfHealBlock, KeyError, TypeError, ValueError, AttributeError) as exc:
        result.update(state="HOLD", classification="BLOCKADE", handoff_effect_verified=False)
        result["first_blocker"] = str(exc) if isinstance(exc, Block) else "READBACK_SCHEMA_INVALID"
    # Run IDs/timestamps/attempt counts do not turn an unchanged state into progress.
    semantic = {key: result[key] for key in (
        "repository", "base_head", "candidate_head", "candidate_tree", "pr_number", "first_blocker",
        "handoff_effect_verified")}
    result["transition_fingerprint"] = hashlib.sha256(
        json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        git = Git()
        if not os.environ.get("GH_TOKEN"):
            raise Block("PR_WRITER_CAPABILITY_UNAVAILABLE")
        candidate = prepare(json.loads(args.controller_receipt.read_text(encoding="utf-8")),
                            os.environ.get("GITHUB_REPOSITORY", ""), git)
        result = materialize(candidate, GitHubAPI(), git)
    except (Block, OSError, ValueError) as exc:
        result = {"schema": "qikvrt_self_heal_materialization_v1", "state": "HOLD",
                  "classification": "BLOCKADE", "first_blocker": str(exc) if isinstance(exc, Block)
                  else "MATERIALIZATION_INPUT_INVALID", "PREDECESSOR_EVIDENCE_TRANSFER": False,
                  "EFFECT_ACK_DONE": False, "transport_ack_is_effect_ack": False}
    text = json.dumps(result, sort_keys=True, indent=2) + "\n"
    args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 2 if result["state"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())

