#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Construct one history-preserving Mirror candidate for accepted Authority PR240.

The executor is fail-closed. It reobserves both main leases, fetches the exact
Authority commit into the local Git object database, creates one commit whose
sole parent is the frozen Mirror main and whose tree is the exact Authority
tree, and attaches only that commit to the isolated target branch.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUEST_PATH = ROOT / "work-units/HISTORY_PRESERVING_MIRROR_SYNC_REQUEST_PR240.json"

AUTHORITY_REPOSITORY = "Goldkelch/qik-vrt"
AUTHORITY_URL = "https://github.com/Goldkelch/qik-vrt.git"
AUTHORITY_MAIN = "1f559a197e0770dc735bbd020d7cefbe9ed6acaf"
AUTHORITY_PR = 240
ACCEPTED_EXACT_HEAD = "166624c3ca75c6da3d1026628e5a2895e8437ae8"
MIRROR_REPOSITORY = "ingolf-lohmann/qik-vrt"
MIRROR_PARENT = "465b46fd69f9311ff02f80a31790691b59affe9e"
TARGET_BRANCH = "sync/projector-repair-authority-1f559a19-from-465b46fd-v1"
CANDIDATE_TIMESTAMP = "2026-07-30T07:05:00Z"


class ConstructionError(RuntimeError):
    """Fail-closed construction error."""


def _run(args: list[str], *, input_text: str | None = None, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise ConstructionError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def _ls_remote(remote: str, ref: str) -> str | None:
    output = _run(["git", "ls-remote", remote, ref])
    if not output:
        return None
    rows = [line.split() for line in output.splitlines() if line.strip()]
    if len(rows) != 1 or len(rows[0]) != 2 or rows[0][1] != ref:
        raise ConstructionError(f"ambiguous remote ref: {remote} {ref}")
    return rows[0][0]


def load_and_validate_request(path: pathlib.Path = REQUEST_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "qikvrt_history_preserving_mirror_sync_request_v1",
        "operation": "CONSTRUCT_HISTORY_PRESERVING_MIRROR_CANDIDATE",
        "state": "AUTHORIZED",
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ConstructionError(f"request {key} drift")
    authority = value.get("authority", {})
    mirror = value.get("mirror", {})
    decision = value.get("owner_decision", {})
    contract = value.get("candidate_contract", {})
    boundary = value.get("truth_boundary", {})
    checks = {
        "authority repository": authority.get("repository") == AUTHORITY_REPOSITORY,
        "authority main": authority.get("main") == AUTHORITY_MAIN,
        "authority PR": authority.get("source_pr") == AUTHORITY_PR,
        "accepted exact head": authority.get("accepted_exact_head") == ACCEPTED_EXACT_HEAD,
        "mirror repository": mirror.get("repository") == MIRROR_REPOSITORY,
        "mirror parent": mirror.get("parent_main") == MIRROR_PARENT,
        "target branch": mirror.get("target_branch") == TARGET_BRANCH,
        "owner": decision.get("actor") == "Ingolf Lohmann",
        "owner type": decision.get("actor_type") == "NATURAL_PERSON",
        "owner decision": decision.get("decision") == "ACCEPT",
        "sole parent": contract.get("sole_parent_required") is True,
        "tree equality": contract.get("authority_tree_equality_required") is True,
        "authority lease": contract.get("current_authority_main_lease_required") is True,
        "mirror lease": contract.get("current_mirror_main_lease_required") is True,
        "timestamp": contract.get("candidate_timestamp") == CANDIDATE_TIMESTAMP,
    }
    failed = sorted(name for name, ok in checks.items() if not ok)
    if failed:
        raise ConstructionError("request binding drift: " + ", ".join(failed))
    for key in (
        "mirror_promoted",
        "reciprocal_equality_receipt_materialized",
        "zenodo_mutation_authorized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        if boundary.get(key) is not False:
            raise ConstructionError(f"truth boundary inflation: {key}")
    return value


def construct(*, origin: str = "origin") -> dict[str, Any]:
    load_and_validate_request()
    observed_mirror = _ls_remote(origin, "refs/heads/main")
    if observed_mirror != MIRROR_PARENT:
        raise ConstructionError(
            f"Mirror main lease drift: expected {MIRROR_PARENT}, observed {observed_mirror}"
        )
    observed_authority = _ls_remote(AUTHORITY_URL, "refs/heads/main")
    if observed_authority != AUTHORITY_MAIN:
        raise ConstructionError(
            f"Authority main lease drift: expected {AUTHORITY_MAIN}, observed {observed_authority}"
        )

    _run(["git", "fetch", "--no-tags", AUTHORITY_URL, AUTHORITY_MAIN])
    fetched = _run(["git", "rev-parse", "FETCH_HEAD"])
    if fetched != AUTHORITY_MAIN:
        raise ConstructionError(f"Authority fetch drift: {fetched}")
    authority_tree = _run(["git", "rev-parse", f"{AUTHORITY_MAIN}^{{tree}}"])
    _run(["git", "cat-file", "-e", f"{MIRROR_PARENT}^{{commit}}"])

    existing = _ls_remote(origin, f"refs/heads/{TARGET_BRANCH}")
    if existing:
        _run(["git", "fetch", "--no-tags", origin, f"refs/heads/{TARGET_BRANCH}"])
        existing_tree = _run(["git", "rev-parse", f"{existing}^{{tree}}"])
        parents = _run(["git", "show", "-s", "--format=%P", existing]).split()
        if existing_tree != authority_tree or parents != [MIRROR_PARENT]:
            raise ConstructionError("existing target branch violates exact candidate contract")
        candidate = existing
        state = "EXACT_CANDIDATE_ALREADY_ATTACHED"
    else:
        message = (
            "Synchronize accepted Authority PR240 projector-precedence repair\n\n"
            f"Authority main: {AUTHORITY_MAIN}\n"
            f"Authority exact accepted head: {ACCEPTED_EXACT_HEAD}\n"
            f"Authority PR: {AUTHORITY_PR}\n"
            f"Frozen Mirror parent: {MIRROR_PARENT}\n"
            "Truth boundary: no reciprocal receipt, Zenodo mutation, PASS, FINAL_PASS, or EFFECT_ACK_DONE.\n"
        )
        env = os.environ.copy()
        env.update(
            {
                "GIT_AUTHOR_NAME": "qik-vrt mirror synchronizer",
                "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                "GIT_AUTHOR_DATE": CANDIDATE_TIMESTAMP,
                "GIT_COMMITTER_NAME": "qik-vrt mirror synchronizer",
                "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                "GIT_COMMITTER_DATE": CANDIDATE_TIMESTAMP,
            }
        )
        candidate = _run(
            ["git", "commit-tree", authority_tree, "-p", MIRROR_PARENT],
            input_text=message,
            env=env,
        )
        # Reobserve both leases immediately before the only ref mutation.
        if _ls_remote(origin, "refs/heads/main") != MIRROR_PARENT:
            raise ConstructionError("Mirror main moved before target attachment")
        if _ls_remote(AUTHORITY_URL, "refs/heads/main") != AUTHORITY_MAIN:
            raise ConstructionError("Authority main moved before target attachment")
        if _ls_remote(origin, f"refs/heads/{TARGET_BRANCH}") is not None:
            raise ConstructionError("target branch appeared concurrently")
        _run(["git", "push", origin, f"{candidate}:refs/heads/{TARGET_BRANCH}"])
        state = "EXACT_HISTORY_PRESERVING_CANDIDATE_ATTACHED"

    final_tree = _run(["git", "rev-parse", f"{candidate}^{{tree}}"])
    final_parents = _run(["git", "show", "-s", "--format=%P", candidate]).split()
    if final_tree != authority_tree or final_parents != [MIRROR_PARENT]:
        raise ConstructionError("post-construction candidate verification failed")
    return {
        "schema": "qikvrt_history_preserving_mirror_candidate_result_v1",
        "state": state,
        "authority_main": AUTHORITY_MAIN,
        "authority_pr": AUTHORITY_PR,
        "accepted_exact_head": ACCEPTED_EXACT_HEAD,
        "mirror_parent": MIRROR_PARENT,
        "candidate": candidate,
        "shared_git_tree": authority_tree,
        "target_branch": TARGET_BRANCH,
        "sole_parent_verified": True,
        "authority_tree_equality_verified": True,
        "mirror_promoted": False,
        "reciprocal_equality_receipt_materialized": False,
        "zenodo_mutation_authorized": False,
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="origin")
    parser.add_argument("--check-request", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check_request:
            load_and_validate_request()
            result: dict[str, Any] = {
                "state": "REQUEST_VALID",
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            }
        else:
            result = construct(origin=args.origin)
    except (ConstructionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "state": "BLOCK",
                    "failure_class": "HISTORY_PRESERVING_MIRROR_CANDIDATE_CONSTRUCTION_INVALID",
                    "reason": str(exc),
                    "pass": False,
                    "final_pass": False,
                    "effect_ack_done": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
