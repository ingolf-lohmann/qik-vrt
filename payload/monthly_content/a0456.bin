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
    "acceptance/MONTHLY_CONTENT_CLAIMED_BUT_ONLY_UPDATE_SCRIPTS_DELIVERED.md",
    "audit/V3_MONTHLY_CONTENT_ACCEPTANCE_FAILURE_REPORT.json",
    "tools/verify_monthly_content_claim.py",
    "tools/persist_monthly_content_acceptance_failure_to_github.py",
]

REQUIRED_MARKERS = [
    "MONTHLY_CONTENT_CLAIMED_BUT_ONLY_UPDATE_SCRIPTS_DELIVERED",
    "MONATSINHALT_BEHAUPTET_ABER_NUR_UPDATE_SKRIPTE_GELIEFERT",
]

def run(cmd: list[str], cwd: pathlib.Path) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def copy_files(target_repo: pathlib.Path) -> None:
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
            raise RuntimeError(f"target file missing: {rel}")
        try:
            combined += "\n" + p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            pass
    for marker in REQUIRED_MARKERS:
        if marker not in combined:
            raise RuntimeError(f"required marker missing in target: {marker}")

def main() -> int:
    parser = argparse.ArgumentParser(description="Persist monthly-content acceptance failure into a GitHub repository.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="Existing local Git repository path")
    group.add_argument("--remote", help="GitHub remote URL to clone")
    parser.add_argument("--workdir", default="QIKVRT_MONTHLY_CONTENT_FAILURE_GITHUB_WORKDIR")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--message", default="Persist QIKVRT monthly content acceptance failure")
    parser.add_argument("--no-push", action="store_true")
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
    copy_files(repo)
    verify_target(repo)

    # Run verifier if present in target.
    verifier = repo / "tools" / "verify_monthly_content_claim.py"
    if verifier.is_file():
        run([sys.executable, str(verifier.relative_to(repo))], repo)

    run(["git", "add"] + FILES_TO_PERSIST, repo)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, text=True, capture_output=True, check=True).stdout.strip()
    if status:
        run(["git", "commit", "-m", args.message], repo)
    else:
        print("No changes to commit.")

    if args.no_push:
        print("PASS local GitHub monthly-content failure persistence prepared; push skipped.")
        return 0

    run(["git", "push", "origin", args.branch], repo)
    print("PASS monthly-content acceptance failure persisted to GitHub remote")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
