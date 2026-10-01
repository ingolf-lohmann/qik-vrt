#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# See LICENSES/Apache-2.0.txt.
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1]

FILES_TO_PERSIST = [
    "acceptance/FINAL_DELIVERY_CLAIM_WITHOUT_CONFIRMED_ARTIFACT_GENERATION.md",
    "acceptance/REPOSITORY_AND_GITHUB_PERSISTENCE_OF_ACCEPTANCE_CHANGES_TEST.md",
    "tools/persist_acceptance_change_to_github.py",
]

REQUIRED_MARKERS = [
    "FINAL_DELIVERY_CLAIM_WITHOUT_CONFIRMED_ARTIFACT_GENERATION",
    "AUSLIEFERUNGSBEHAUPTUNG_OHNE_BESTAETIGTE_ARTEFAKTGENERIERUNG",
    "ACCEPTANCE_CHANGE_NOT_PERSISTED_TO_REPOSITORY_AND_GITHUB",
    "REPOSITORY_AND_GITHUB_PERSISTENCE_OF_ACCEPTANCE_CHANGES_TEST",
]

def run(cmd: list[str], cwd: pathlib.Path) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def copy_required_files(target_repo: pathlib.Path) -> None:
    for rel in FILES_TO_PERSIST:
        src = PACKAGE_ROOT / rel
        dst = target_repo / rel
        if not src.is_file():
            raise FileNotFoundError(f"package file missing: {rel}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def verify_target(target_repo: pathlib.Path) -> None:
    combined = ""
    for rel in FILES_TO_PERSIST:
        p = target_repo / rel
        if not p.is_file():
            raise RuntimeError(f"target file missing after copy: {rel}")
        combined += "\n" + p.read_text(encoding="utf-8")
    for marker in REQUIRED_MARKERS:
        if marker not in combined:
            raise RuntimeError(f"required marker missing after copy: {marker}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Persist final-delivery acceptance change into a GitHub repository.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="Existing local Git repository path.")
    group.add_argument("--remote", help="GitHub remote URL to clone into --workdir.")
    parser.add_argument("--workdir", default="QIKVRT_GITHUB_ACCEPTANCE_UPDATE_WORKDIR", help="Clone/work directory if --remote is used.")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--message", default="Persist QIKVRT final delivery acceptance rule")
    parser.add_argument("--no-push", action="store_true", help="Commit locally but do not push.")
    args = parser.parse_args()

    if args.repo:
        repo = pathlib.Path(args.repo).resolve()
        if not (repo / ".git").exists():
            print("FAIL target --repo is not a Git repository", file=sys.stderr)
            return 1
    else:
        repo = pathlib.Path(args.workdir).resolve()
        if repo.exists():
            shutil.rmtree(repo)
        run(["git", "clone", args.remote, str(repo)], pathlib.Path.cwd())

    run(["git", "checkout", args.branch], repo)
    copy_required_files(repo)
    verify_target(repo)

    # Run repository verifier if present; otherwise local marker verification is the gate.
    verifier_candidates = [
        repo / "tools" / "verify_update_script_package.py",
        repo / "tools" / "verify_repository.py",
        repo / "tools" / "verify_github_three_pdf_package.py",
    ]
    for verifier in verifier_candidates:
        if verifier.is_file():
            run([sys.executable, str(verifier.relative_to(repo))], repo)
            break

    run(["git", "add"] + FILES_TO_PERSIST, repo)

    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()
    if status:
        run(["git", "commit", "-m", args.message], repo)
    else:
        print("No changes to commit.")

    if args.no_push:
        print("PASS local GitHub acceptance-change persistence prepared; push skipped.")
        return 0

    run(["git", "push", "origin", args.branch], repo)
    print("PASS acceptance change persisted to GitHub remote")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
