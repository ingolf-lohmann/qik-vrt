#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Construct an unreferenced history-preserving Mirror candidate, fail closed."""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.request

AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
AUTHORITY_MAIN = "7d87a6003135a6e3efbca34b2d898967d7f66018"
MIRROR_PARENT = "afcd0255aab6bc5ad18275a2d91516688a41e302"
EXECUTION_BRANCH = "execution/history-preserving-mirror-sync-authority-7d87-from-afcd-v1"
TARGET_BRANCH = "sync/accepted-six-candidates-authority-7d87-from-afcd-v1"
RECEIPT_PATH = pathlib.Path(
    "evidence/runtime/HISTORY_PRESERVING_MIRROR_CANDIDATE_7D87_FROM_AFCD.json"
)


def git(*args: str, text: bool = True) -> str | bytes:
    return subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
    ).stdout


def api(method: str, path: str, payload=None):
    token = os.environ["GITHUB_TOKEN"]
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "qikvrt-history-preserving-mirror-constructor",
    }
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        "https://api.github.com" + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API {method} {path} failed: {exc.code} {body}"
        ) from exc
    return json.loads(raw.decode("utf-8")) if raw else None


def remote_sha(remote: str, ref: str) -> str:
    output = str(git("ls-remote", remote, ref))
    if "\t" not in output:
        raise SystemExit(f"BLOCK: remote ref absent: {remote} {ref}")
    return output.split("\t", 1)[0]


def main() -> int:
    mirror_repository = os.environ["GITHUB_REPOSITORY"]
    authority_url = f"https://github.com/{AUTHORITY_REPOSITORY}.git"

    if remote_sha("origin", "refs/heads/main") != MIRROR_PARENT:
        raise SystemExit("BLOCK: Mirror main lease moved before construction")
    if remote_sha(authority_url, "refs/heads/main") != AUTHORITY_MAIN:
        raise SystemExit("BLOCK: Authority main lease moved before construction")

    git("fetch", "--no-tags", "--force", authority_url, AUTHORITY_MAIN)
    if str(git("rev-parse", "FETCH_HEAD")).strip() != AUTHORITY_MAIN:
        raise SystemExit("BLOCK: exact Authority fetch drift")

    authority_tree = str(git("show", "-s", "--format=%T", AUTHORITY_MAIN)).strip()
    mirror_parent_tree = str(git("show", "-s", "--format=%T", MIRROR_PARENT)).strip()

    raw_names = bytes(
        git(
            "diff",
            "--name-status",
            "--no-renames",
            "-z",
            MIRROR_PARENT,
            AUTHORITY_MAIN,
            text=False,
        )
    )
    tokens = raw_names.split(b"\0")
    changes: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens) and tokens[index]:
        status = tokens[index].decode("ascii")
        path = tokens[index + 1].decode("utf-8", errors="strict")
        changes.append((status, path))
        index += 2

    entries = []
    bindings = []
    imported_blobs = 0
    deleted_paths = 0
    for status, path in changes:
        if status == "D":
            entries.append({"path": path, "sha": None})
            deleted_paths += 1
            continue
        if status not in {"A", "M", "T"}:
            raise SystemExit(f"BLOCK: unsupported status {status!r} for {path!r}")
        row = str(git("ls-tree", AUTHORITY_MAIN, "--", path)).rstrip("\n")
        if not row:
            raise SystemExit(f"BLOCK: Authority path absent: {path}")
        metadata, observed_path = row.split("\t", 1)
        mode, object_type, source_sha = metadata.split(" ", 2)
        if observed_path != path:
            raise SystemExit(f"BLOCK: path decoding drift: {path!r}")
        if object_type == "blob":
            raw = bytes(git("cat-file", "blob", source_sha, text=False))
            created = api(
                "POST",
                f"/repos/{mirror_repository}/git/blobs",
                {
                    "content": base64.b64encode(raw).decode("ascii"),
                    "encoding": "base64",
                },
            )
            if created["sha"] != source_sha:
                raise SystemExit(f"BLOCK: blob mismatch for {path}")
            imported_blobs += 1
            target_type = "blob"
        elif object_type == "commit" and mode == "160000":
            target_type = "commit"
        else:
            raise SystemExit(
                f"BLOCK: unsupported Authority object {object_type}/{mode}: {path}"
            )
        entry = {
            "path": path,
            "mode": mode,
            "type": target_type,
            "sha": source_sha,
        }
        entries.append(entry)
        bindings.append(entry)

    tree = api(
        "POST",
        f"/repos/{mirror_repository}/git/trees",
        {"base_tree": mirror_parent_tree, "tree": entries},
    )
    if tree["sha"] != authority_tree:
        raise SystemExit(
            f"BLOCK: tree mismatch {tree['sha']} != Authority {authority_tree}"
        )

    commit = api(
        "POST",
        f"/repos/{mirror_repository}/git/commits",
        {
            "message": (
                "Synchronize owner-accepted six corrected corpus candidates from Authority\n\n"
                f"Authority main: {AUTHORITY_MAIN}\n"
                f"Mirror parent: {MIRROR_PARENT}\n"
                f"Authority tree: {authority_tree}\n\n"
                "History-preserving candidate only. No Mirror promotion, reciprocal equality, "
                "Zenodo mutation, repository-wide PASS, FINAL_PASS, or EFFECT_ACK_DONE is claimed."
            ),
            "tree": authority_tree,
            "parents": [MIRROR_PARENT],
        },
    )
    candidate_sha = commit["sha"]
    observed = api("GET", f"/repos/{mirror_repository}/git/commits/{candidate_sha}")
    parents = [item["sha"] for item in observed["parents"]]
    if parents != [MIRROR_PARENT]:
        raise SystemExit(f"BLOCK: candidate parents drift: {parents!r}")
    if observed["tree"]["sha"] != authority_tree:
        raise SystemExit("BLOCK: candidate tree drift after creation")

    if remote_sha("origin", "refs/heads/main") != MIRROR_PARENT:
        raise SystemExit("BLOCK: Mirror main moved during construction")
    if remote_sha(authority_url, "refs/heads/main") != AUTHORITY_MAIN:
        raise SystemExit("BLOCK: Authority main moved during construction")

    receipt = {
        "schema": "qikvrt_history_preserving_mirror_candidate_receipt_v1",
        "repository": mirror_repository,
        "authority_repository": AUTHORITY_REPOSITORY,
        "authority_main": AUTHORITY_MAIN,
        "authority_tree": authority_tree,
        "mirror_parent": MIRROR_PARENT,
        "mirror_parent_tree": mirror_parent_tree,
        "candidate_sha": candidate_sha,
        "candidate_tree": authority_tree,
        "candidate_parents": parents,
        "target_branch": TARGET_BRANCH,
        "changed_path_count": len(changes),
        "imported_blob_count": imported_blobs,
        "deleted_path_count": deleted_paths,
        "authority_tree_equality": True,
        "sole_parent_verified": True,
        "authority_main_lease_unchanged": True,
        "mirror_main_lease_unchanged": True,
        "branch_attached": False,
        "mirror_promoted": False,
        "reciprocal_equality_receipt_complete": False,
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
        "constructed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_blob_bindings": bindings,
    }
    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"AUTHORITY_TREE={authority_tree}")
    print(f"MIRROR_PARENT_TREE={mirror_parent_tree}")
    print(f"CANDIDATE_SHA={candidate_sha}")
    print(f"CHANGED_PATH_COUNT={len(changes)}")
    print(f"IMPORTED_BLOB_COUNT={imported_blobs}")
    print("AUTHORITY_TREE_EQUALITY=true")
    print("SOLE_PARENT_VERIFIED=true")
    print("BRANCH_ATTACHED=false")
    print("MIRROR_PROMOTED=false")
    print("PASS=false")
    print("FINAL_PASS=false")
    print("EFFECT_ACK_DONE=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
