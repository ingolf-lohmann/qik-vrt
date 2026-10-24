#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Emit an exact connector-owned Git tree plan for the bounded Mirror candidate."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = ROOT / "work-units/HISTORY_PRESERVING_MIRROR_SYNC_REQUEST.json"


class PlanError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise PlanError(message)


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def remote_sha(url: str, ref: str) -> str:
    output = subprocess.check_output(
        ["git", "ls-remote", url, ref], cwd=ROOT, text=True
    ).strip()
    if not output:
        fail(f"remote ref absent: {url} {ref}")
    return output.split("\t", 1)[0]


def seed_blob(repo: str, token: str, content: bytes) -> str:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/git/blobs",
        data=json.dumps(
            {
                "content": base64.b64encode(content).decode("ascii"),
                "encoding": "base64",
            },
            separators=(",", ":"),
        ).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-mirror-tree-plan/1",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        fail(f"GitHub blob API failed: {exc.code}: {body}")
    sha = value.get("sha") if isinstance(value, dict) else None
    if not isinstance(sha, str):
        fail("GitHub blob API omitted SHA")
    return sha


def build_plan() -> dict[str, Any]:
    marker = json.loads(MARKER.read_text(encoding="utf-8"))
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    trigger_sha = os.environ.get("GITHUB_SHA", "")
    trigger_ref = os.environ.get("TARGET_REF") or os.environ.get("GITHUB_HEAD_REF") or ""

    if repo != "ingolf-lohmann/qik-vrt" or not token:
        fail("runtime repository or token unavailable")
    if git_text("rev-parse", "HEAD") != trigger_sha:
        fail("checkout is not immutable trigger head")
    if marker.get("schema") != "qikvrt_history_preserving_mirror_candidate_request_v4":
        fail("request schema drift")
    if marker.get("state") != "READY":
        fail("request state drift")
    if marker.get("execution_branch") != trigger_ref:
        fail("execution branch ownership drift")

    authority = marker["authority_main"]
    parent = marker["mirror_parent"]
    target = marker["target_branch"]
    execution = marker["execution_branch"]
    authority_url = f"https://github.com/{marker['authority_repository']}.git"

    if remote_sha("origin", f"refs/heads/{execution}") != trigger_sha:
        fail("execution branch lease drift")
    if remote_sha("origin", "refs/heads/main") != parent:
        fail("Mirror main lease drift")
    if remote_sha("origin", f"refs/heads/{target}") != parent:
        fail("target branch lease drift")
    if remote_sha(authority_url, "refs/heads/main") != authority:
        fail("Authority main lease drift")

    subprocess.check_call(
        [
            "git",
            "fetch",
            "--no-tags",
            authority_url,
            "refs/heads/main:refs/remotes/authority/main",
        ],
        cwd=ROOT,
    )
    if git_text("rev-parse", "refs/remotes/authority/main") != authority:
        fail("fetched Authority identity drift")

    manifest_blob = git_text("rev-parse", f"{authority}:REPOSITORY_FILE_MANIFEST.json")
    if manifest_blob != marker["authority_manifest_git_blob_sha1"]:
        fail("Authority manifest blob drift")
    manifest_bytes = git_bytes("show", f"{authority}:REPOSITORY_FILE_MANIFEST.json")
    if hashlib.sha256(manifest_bytes).hexdigest() != marker["authority_manifest_sha256"]:
        fail("Authority manifest digest drift")
    manifest = json.loads(manifest_bytes)
    if manifest.get("repository_content_tree_sha256") != marker["repository_content_tree_sha256"]:
        fail("Authority content-tree digest drift")

    authority_tree = git_text("rev-parse", f"{authority}^{{tree}}")
    parent_tree = git_text("rev-parse", f"{parent}^{{tree}}")
    fields = git_bytes("diff", "--name-status", "-z", "--no-renames", parent, authority).split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        fail("unexpected diff record shape")

    entries: list[dict[str, Any]] = []
    for index in range(0, len(fields), 2):
        status = fields[index].decode("ascii")
        path = fields[index + 1].decode("utf-8")
        if status == "D":
            entries.append({"path": path, "sha": None})
            continue
        line = git_text("ls-tree", authority, "--", path)
        if not line:
            fail(f"Authority tree entry absent: {path}")
        metadata, observed_path = line.split("\t", 1)
        mode, object_type, object_sha = metadata.split(" ", 2)
        if observed_path != path or object_type not in {"blob", "commit"}:
            fail(f"unexpected Authority tree entry: {line}")
        if object_type == "blob":
            seeded = seed_blob(repo, token, git_bytes("cat-file", "blob", object_sha))
            if seeded != object_sha:
                fail(f"content-addressed blob drift: {path}")
        entries.append(
            {"path": path, "mode": mode, "type": object_type, "sha": object_sha}
        )

    if not entries:
        fail("Authority and Mirror parent unexpectedly have identical trees")
    return {
        "state": "BLOCK",
        "failure_class": "CONNECTOR_TREE_WRITE_REQUIRED",
        "authority_main": authority,
        "authority_tree": authority_tree,
        "mirror_parent": parent,
        "parent_tree": parent_tree,
        "target_branch": target,
        "changed_file_count": len(entries),
        "entries": entries,
        "completion_claims": {
            "candidate_created": False,
            "mirror_promoted": False,
            "reciprocal_equality_refreshed": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }


def main() -> int:
    try:
        result = build_plan()
    except (PlanError, OSError, ValueError, subprocess.SubprocessError) as exc:
        result = {
            "state": "BLOCK",
            "failure_class": "MIRROR_TREE_PLAN_EMISSION_FAILED",
            "reason": str(exc),
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
