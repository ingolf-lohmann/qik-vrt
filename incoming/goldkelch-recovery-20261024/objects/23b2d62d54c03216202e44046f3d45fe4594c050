#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-byte runner for the current PR249 history-preserving Mirror transaction.

The generic constructor strips trailing whitespace from scalar Git output.
That is correct for object identities but not for hashing a blob. This runner
preserves the exact Authority manifest bytes and binds the candidate's sole
parent to the post-infrastructure Mirror main. The exact Authority tree thereby
removes the temporary constructor paths while their commits remain in history.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools import qikvrt_construct_history_preserving_mirror_candidate_pr249 as base


base.MIRROR_PARENT = "c2a6e75eb24721029865a9dd5fd94fa55590a955"
base.TARGET_BRANCH = "sync/six-corrected-candidates-authority-7d87a600-from-c2a6e75e-v1"
base.CANDIDATE_TIMESTAMP = "2026-07-30T08:10:00Z"

ConstructionError = base.ConstructionError
REQUEST_PATH = base.REQUEST_PATH
AUTHORITY_MAIN = base.AUTHORITY_MAIN
AUTHORITY_PR = base.AUTHORITY_PR
ACCEPTED_EXACT_HEAD = base.ACCEPTED_EXACT_HEAD
MIRROR_PARENT = base.MIRROR_PARENT
TARGET_BRANCH = base.TARGET_BRANCH
CANDIDATE_TIMESTAMP = base.CANDIDATE_TIMESTAMP
load_and_validate_request = base.load_and_validate_request
construct = base.construct


def _git_blob_bytes(spec: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", spec],
        cwd=base.ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise base.ConstructionError(
            f"command failed ({completed.returncode}): git show {spec}\n"
            f"{completed.stderr.decode('utf-8', errors='replace').strip()}"
        )
    return completed.stdout


def verify_authority_manifest_exact_bytes() -> dict[str, Any]:
    manifest_blob = base._run(
        ["git", "rev-parse", f"{base.AUTHORITY_MAIN}:REPOSITORY_FILE_MANIFEST.json"]
    )
    if manifest_blob != base.AUTHORITY_MANIFEST_BLOB:
        raise base.ConstructionError(f"Authority manifest blob drift: {manifest_blob}")

    raw = _git_blob_bytes(f"{base.AUTHORITY_MAIN}:REPOSITORY_FILE_MANIFEST.json")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != base.AUTHORITY_MANIFEST_SHA256:
        raise base.ConstructionError(f"Authority manifest SHA-256 drift: {digest}")

    manifest = json.loads(raw.decode("utf-8"))
    if manifest.get("file_count") != base.AUTHORITY_FILE_COUNT:
        raise base.ConstructionError("Authority file count drift")
    if manifest.get("immutable_file_count") != base.AUTHORITY_IMMUTABLE_FILE_COUNT:
        raise base.ConstructionError("Authority immutable file count drift")
    if manifest.get("repository_content_tree_sha256") != base.AUTHORITY_CONTENT_TREE_SHA256:
        raise base.ConstructionError("Authority content-tree digest drift")

    detached_raw = _git_blob_bytes(
        f"{base.AUTHORITY_MAIN}:REPOSITORY_FILE_MANIFEST.json.sha256"
    )
    detached = detached_raw.decode("utf-8").split()
    if not detached or detached[0] != base.AUTHORITY_MANIFEST_SHA256:
        raise base.ConstructionError("Authority detached manifest digest drift")

    return {
        "repository_manifest_git_blob_sha1": manifest_blob,
        "repository_manifest_sha256": digest,
        "repository_content_tree_sha256": manifest["repository_content_tree_sha256"],
        "file_count": manifest["file_count"],
        "immutable_file_count": manifest["immutable_file_count"],
    }


base.verify_authority_manifest = verify_authority_manifest_exact_bytes


if __name__ == "__main__":
    raise SystemExit(base.main())
