#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-byte runner for the PR249 history-preserving Mirror constructor.

The underlying constructor's generic text command helper strips trailing
whitespace. That is correct for scalar Git output, but not for hashing the
manifest blob. This runner preserves the exact blob bytes for the manifest
and detached digest while leaving the reviewed transaction logic unchanged.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any

from tools import qikvrt_construct_history_preserving_mirror_candidate_pr249 as base


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
