#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Create an unreferenced exact Authority-tree Mirror candidate under leases."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
MARKER = ROOT / "work-units/HISTORY_PRESERVING_MIRROR_SYNC_REQUEST.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_BRANCH = re.compile(r"^[A-Za-z0-9._/-]+$")


class CandidateError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise CandidateError(message)


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def remote_sha(url: str, ref: str) -> str:
    value = subprocess.check_output(
        ["git", "ls-remote", url, ref], cwd=ROOT, text=True
    ).strip()
    if not value:
        fail(f"remote ref is absent: {url} {ref}")
    return value.split("\t", 1)[0]


def api_post(repo: str, token: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}{path}",
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "qikvrt-history-preserving-mirror-sync/4",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            value = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        fail(f"GitHub API {path} failed: {exc.code}: {body}")
    if not isinstance(value, dict):
        fail(f"GitHub API {path} returned a non-object")
    return value


def validate(marker: dict[str, Any], trigger_ref: str) -> None:
    if marker.get("schema") != "qikvrt_history_preserving_mirror_candidate_request_v4":
        fail("request schema drift")
    if marker.get("state") != "READY":
        fail("request state is not READY")
    if marker.get("operation") != "DISPOSITION_BATCH_003_FIRST_SUBJECT_FROM_EXACT_PUBLIC_FREEZE":
        fail("request operation drift")
    if marker.get("authority_repository") != "Goldkelch/qik-vrt":
        fail("Authority repository drift")
    if marker.get("mirror_repository") != "ingolf-lohmann/qik-vrt":
        fail("Mirror repository drift")
    if marker.get("authority_pull_request") != 225:
        fail("Authority PR drift")
    if marker.get("authority_main") != "0fea97ca7957c1ea76611fb9eb6c39f558f33355":
        fail("Authority main drift")
    if marker.get("authority_exact_green_head") != "0a760662fca8796117430ff4be452b47e959b6bb":
        fail("Authority exact green head drift")
    if marker.get("authority_manifest_git_blob_sha1") != "901daa49e5bb9c03b7ce523d6b56f6e1392a4314":
        fail("Authority manifest blob drift")
    if marker.get("authority_manifest_sha256") != "3b077ff0574719ced950deb357f44935685a9e93123deb9ec29d33c20e4ab7a9":
        fail("Authority manifest SHA-256 drift")
    if marker.get("repository_content_tree_sha256") != "975c76ef7b2743a2b1502eabe240adf5375e43e5641eee388e925354de9d8c37":
        fail("Authority content-tree digest drift")
    if marker.get("authority_file_count") != 2967:
        fail("Authority file count drift")
    if marker.get("authority_immutable_file_count") != 2958:
        fail("Authority immutable file count drift")
    if marker.get("execution_branch") != trigger_ref:
        fail("execution branch does not own trigger ref")
    for key in ("execution_branch", "target_branch"):
        value = marker.get(key)
        if not isinstance(value, str) or not SAFE_BRANCH.fullmatch(value) or ".." in value:
            fail(f"unsafe branch name: {key}")
    if not marker["execution_branch"].startswith("execution/history-preserving-mirror-sync-"):
        fail("execution branch prefix drift")
    if not marker["target_branch"].startswith("sync/"):
        fail("target branch prefix drift")
    for key in (
        "authority_main",
        "authority_exact_green_head",
        "mirror_parent",
        "authority_manifest_git_blob_sha1",
    ):
        value = marker.get(key)
        if not isinstance(value, str) or not SHA40.fullmatch(value):
            fail(f"invalid SHA-1 field: {key}")
    for key in ("authority_manifest_sha256", "repository_content_tree_sha256"):
        value = marker.get(key)
        if not isinstance(value, str) or not SHA64.fullmatch(value):
            fail(f"invalid SHA-256 field: {key}")
    expected_corpus = {
        "subject_count": 19,
        "dispositioned_subject_count": 13,
        "open_subject_count": 6,
        "active_batch": "CONTENT-DISPOSITION-BATCH-003",
        "terminal_subject": "SUBJECT-2581811b342e505d",
        "active_subject": "SUBJECT-172dd9bc2738fa43",
        "batch_state": "FIRST_SUBJECT_TERMINAL_NEXT_SUBJECT_READY",
    }
    if marker.get("corpus_binding") != expected_corpus:
        fail("corpus binding drift")
    if marker.get("projected_next_effect") != (
        "EXTRACT_ARCHIVE_CONTENT_THEN_DISPOSITION_CLAIMS_"
        "BATCH_003_SUBJECT_172DD9BC2738FA43"
    ):
        fail("projected next effect drift")
    if marker.get("next_deterministic_effect_after_sync") != (
        "REOBSERVE_AND_PERSIST_RECIPROCAL_EQUALITY_RECEIPT_FOR_"
        "BATCH003_FIRST_SUBJECT_DISPOSITION"
    ):
        fail("post-sync next effect drift")
    expected_completion = {
        "candidate_created": False,
        "mirror_promoted": False,
        "reciprocal_equality_refreshed": False,
        "first_subject_disposition_synchronized": False,
        "batch_003_terminal": False,
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }
    if marker.get("completion_claims") != expected_completion:
        fail("completion boundary drift")


def construct(marker: dict[str, Any]) -> dict[str, Any]:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    trigger_sha = os.environ.get("GITHUB_SHA", "")
    trigger_ref = os.environ.get("TARGET_REF") or os.environ.get("GITHUB_HEAD_REF") or ""
    if repo != marker["mirror_repository"]:
        fail("runtime repository drift")
    if not token:
        fail("GitHub token is absent")
    if git_text("rev-parse", "HEAD") != trigger_sha:
        fail("checkout is not immutable trigger head")
    validate(marker, trigger_ref)

    authority_url = f"https://github.com/{marker['authority_repository']}.git"
    origin_url = "origin"
    authority = marker["authority_main"]
    parent = marker["mirror_parent"]
    target = marker["target_branch"]
    execution = marker["execution_branch"]

    if remote_sha(origin_url, f"refs/heads/{execution}") != trigger_sha:
        fail("execution branch lease drift")
    if remote_sha(origin_url, "refs/heads/main") != parent:
        fail("Mirror main lease drift")
    if remote_sha(origin_url, f"refs/heads/{target}") != parent:
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
    if git_text("rev-parse", f"{authority}:REPOSITORY_FILE_MANIFEST.json") != marker["authority_manifest_git_blob_sha1"]:
        fail("Authority manifest Git blob drift")
    raw_manifest = git_bytes("show", f"{authority}:REPOSITORY_FILE_MANIFEST.json")
    manifest = json.loads(raw_manifest)
    if hashlib.sha256(raw_manifest).hexdigest() != marker["authority_manifest_sha256"]:
        fail("Authority manifest byte digest drift")
    if manifest.get("repository_content_tree_sha256") != marker["repository_content_tree_sha256"]:
        fail("Authority content-tree digest mismatch")
    if manifest.get("file_count") != marker["authority_file_count"]:
        fail("Authority manifest file count mismatch")
    if manifest.get("immutable_file_count") != marker["authority_immutable_file_count"]:
        fail("Authority immutable file count mismatch")

    authority_tree = git_text("rev-parse", f"{authority}^{{tree}}")
    parent_tree = git_text("rev-parse", f"{parent}^{{tree}}")
    fields = git_bytes("diff", "--name-status", "-z", "--no-renames", parent, authority).split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        fail("unexpected diff record shape")

    entries: list[dict[str, Any]] = []
    changed_paths: list[str] = []
    for index in range(0, len(fields), 2):
        status = fields[index].decode("ascii")
        path = fields[index + 1].decode("utf-8", "surrogateescape")
        changed_paths.append(path)
        if status == "D":
            entries.append({"path": path, "sha": None})
            continue
        line = git_text("ls-tree", authority, "--", path)
        if not line:
            fail(f"Authority tree entry missing: {path}")
        metadata, observed_path = line.split("\t", 1)
        mode, object_type, object_sha = metadata.split(" ", 2)
        if observed_path != path or object_type not in {"blob", "commit"}:
            fail(f"unexpected Authority tree entry: {line}")
        if object_type == "blob":
            content = git_bytes("cat-file", "blob", object_sha)
            created = api_post(
                repo,
                token,
                "/git/blobs",
                {
                    "content": base64.b64encode(content).decode("ascii"),
                    "encoding": "base64",
                },
            )
            if created.get("sha") != object_sha:
                fail(f"content-addressed blob identity drift: {path}")
        entries.append(
            {"path": path, "mode": mode, "type": object_type, "sha": object_sha}
        )

    if not entries:
        fail("Authority and Mirror parent unexpectedly have identical trees")
    tree = api_post(repo, token, "/git/trees", {"base_tree": parent_tree, "tree": entries})
    if tree.get("sha") != authority_tree:
        fail(f"constructed tree differs from Authority: {tree.get('sha')} != {authority_tree}")

    message = f"""Synchronize Batch-003 first-subject disposition from Authority {authority[:8]}

Authority repository: {marker['authority_repository']}
Authority main: {authority}
Authority PR: {marker['authority_pull_request']}
Authority tree: {authority_tree}
Mirror parent: {parent}
Repository manifest SHA-256: {marker['authority_manifest_sha256']}
Repository content-tree SHA-256: {marker['repository_content_tree_sha256']}
Operation: {marker['operation']}
Next content effect: {marker['projected_next_effect']}
Preserved corpus: 19 subjects, 13 dispositioned, 6 open
Terminal subject: SUBJECT-2581811b342e505d
Active subject: SUBJECT-172dd9bc2738fa43

The sole parent is the frozen Mirror main and the complete Git tree is the exact Authority tree. This candidate does not complete Batch 003, process the remaining six corpus subjects, authorize Zenodo mutation, publish a proof corpus, establish Mirror promotion or reciprocal equality, or claim repository-wide PASS, FINAL_PASS, or EFFECT_ACK_DONE."""
    commit = api_post(
        repo,
        token,
        "/git/commits",
        {"message": message, "tree": authority_tree, "parents": [parent]},
    )
    candidate = commit.get("sha")
    commit_tree = (commit.get("tree") or {}).get("sha")
    parents = [row.get("sha") for row in commit.get("parents", []) if isinstance(row, dict)]
    if not isinstance(candidate, str) or not SHA40.fullmatch(candidate):
        fail("candidate identity is absent")
    if commit_tree != authority_tree or parents != [parent]:
        fail("candidate tree or sole-parent binding drift")
    return {
        "candidate_head": candidate,
        "authority_tree": authority_tree,
        "mirror_parent": parent,
        "authority_main": authority,
        "changed_file_count": len(changed_paths),
        "tree_equality": True,
        "sole_parent_bound": True,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main() -> int:
    if not MARKER.is_file():
        print("Mirror synchronization request is not present; constructor skipped.")
        return 0
    try:
        marker = json.loads(MARKER.read_text(encoding="utf-8"))
        result = construct(marker)
    except (CandidateError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"state": "BLOCK", "failure_class": "HISTORY_PRESERVING_MIRROR_CANDIDATE_CONSTRUCTION_FAILED", "reason": str(exc)}, sort_keys=True))
        return 2
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True)
    print(rendered)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with pathlib.Path(summary).open("a", encoding="utf-8", newline="\n") as handle:
            for key, value in result.items():
                handle.write(f"{key.upper()}={str(value).lower() if isinstance(value, bool) else value}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
