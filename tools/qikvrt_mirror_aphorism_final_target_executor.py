#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Persist the exact Mirror aphorism-corpus candidate, fail-closed."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from collections.abc import Iterable, Sequence


class Block(RuntimeError):
    """Deterministic repository-contract failure."""


def run(
    argv: Sequence[str],
    *,
    cwd: pathlib.Path,
    capture: bool = False,
) -> str:
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if completed.returncode != 0:
        detail = ""
        if capture:
            detail = f"\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        raise Block(
            f"command failed ({completed.returncode}): {' '.join(argv)}{detail}"
        )
    return completed.stdout.strip() if capture else ""


def env_exact(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise Block(f"required environment variable is absent: {name}")
    return value


def git(cwd: pathlib.Path, *args: str, capture: bool = True) -> str:
    return run(("git", *args), cwd=cwd, capture=capture)


def require_equal(label: str, observed: object, expected: object) -> None:
    if observed != expected:
        raise Block(f"{label} differs: observed={observed!r}; expected={expected!r}")


def read_status_paths(cwd: pathlib.Path) -> list[tuple[str, str]]:
    raw = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=cwd,
    )
    entries = [entry for entry in raw.split(b"\0") if entry]
    result: list[tuple[str, str]] = []
    for entry in entries:
        if len(entry) < 4 or entry[2:3] != b" ":
            raise Block(f"malformed porcelain entry: {entry!r}")
        status = entry[:2].decode("ascii")
        path = entry[3:].decode("utf-8")
        result.append((status, path))
    return result


def ensure_files(root: pathlib.Path, paths: Iterable[str]) -> None:
    for relative in paths:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise Block(f"required regular file is absent or symlinked: {relative}")


def main() -> int:
    workspace = pathlib.Path(env_exact("GITHUB_WORKSPACE")).resolve()
    target = (workspace / "target").resolve()
    if target.parent != workspace or not (target / ".git").exists():
        raise Block(f"target checkout is absent or outside workspace: {target}")

    target_ref = env_exact("TARGET_REF")
    expected_target_head = env_exact("EXPECTED_TARGET_HEAD")
    mirror_parent = env_exact("MIRROR_PARENT")
    authority_base = env_exact("AUTHORITY_BASE")
    authority_head = env_exact("AUTHORITY_HEAD")
    carrier_path = env_exact("CARRIER_PATH")
    expected_carrier_blob = env_exact("EXPECTED_CARRIER_BLOB")
    mirror_makefile_blob = env_exact("MIRROR_MAKEFILE_BLOB")

    source_head = git(target, "rev-parse", "--verify", "HEAD^{commit}")
    require_equal("target source head", source_head, expected_target_head)
    run(("git", "merge-base", "--is-ancestor", mirror_parent, "HEAD"), cwd=target)
    require_equal(
        "target carrier blob",
        git(target, "hash-object", carrier_path),
        expected_carrier_blob,
    )
    require_equal(
        "Mirror parent Makefile blob",
        git(target, "rev-parse", f"{mirror_parent}:Makefile"),
        mirror_makefile_blob,
    )

    pre_paths = set(
        git(
            target,
            "diff",
            "--name-only",
            "--no-renames",
            mirror_parent,
            "HEAD",
            "--",
        ).splitlines()
    )
    require_equal(
        "bounded target pre-port paths",
        pre_paths,
        {
            carrier_path,
            "REPOSITORY_FILE_MANIFEST.json",
            "REPOSITORY_FILE_MANIFEST.json.sha256",
            "SHA256SUMS.txt",
        },
    )

    git(target, "remote", "add", "authority", "https://github.com/Goldkelch/qik-vrt.git", capture=False)
    git(
        target,
        "fetch",
        "--no-tags",
        "authority",
        authority_base,
        authority_head,
        capture=False,
    )
    require_equal(
        "Authority base object",
        git(target, "rev-parse", "--verify", f"{authority_base}^{{commit}}"),
        authority_base,
    )
    require_equal(
        "Authority head object",
        git(target, "rev-parse", "--verify", f"{authority_head}^{{commit}}"),
        authority_head,
    )
    run(
        ("git", "merge-base", "--is-ancestor", authority_base, authority_head),
        cwd=target,
    )

    raw_delta = git(
        target,
        "diff",
        "--name-status",
        "--no-renames",
        authority_base,
        authority_head,
        "--",
    ).splitlines()
    authority_delta: list[tuple[str, str]] = []
    for line in raw_delta:
        fields = line.split("\t", 1)
        if len(fields) != 2:
            raise Block(f"malformed Authority delta line: {line!r}")
        authority_delta.append((fields[0], fields[1]))
    require_equal("Authority changed-path count", len(authority_delta), 76)

    adapted = {
        "Makefile",
        "REPOSITORY_FILE_MANIFEST.json",
        "REPOSITORY_FILE_MANIFEST.json.sha256",
        "SHA256SUMS.txt",
    }
    portable: list[str] = []
    for status, path in authority_delta:
        if path in adapted:
            continue
        if status not in {"A", "M"}:
            raise Block(f"unsupported Authority status {status!r} for {path}")
        portable.append(path)
        git(target, "checkout", authority_head, "--", path, capture=False)
        require_equal(
            f"portable blob {path}",
            git(target, "hash-object", path),
            git(target, "rev-parse", f"{authority_head}:{path}"),
        )
    require_equal("portable path count", len(portable), 72)
    require_equal("portable path uniqueness", len(set(portable)), 72)

    makefile = target / "Makefile"
    require_equal("pre-adaptation Makefile blob", git(target, "hash-object", "Makefile"), mirror_makefile_blob)
    text = makefile.read_text(encoding="utf-8")
    replacements = (
        (
            "tests/test_virtual_past_reception.py tests/test_quantum_classical_runtime_article.py",
            "tests/test_virtual_past_reception.py tests/test_aphorism_corpus_v2.py tests/test_quantum_classical_runtime_article.py",
        ),
        (
            "tests.test_virtual_past_reception tests.test_quantum_classical_runtime_article",
            "tests.test_virtual_past_reception tests.test_aphorism_corpus_v2 tests.test_quantum_classical_runtime_article",
        ),
    )
    for old, new in replacements:
        require_equal(f"Mirror Makefile anchor count for {old}", text.count(old), 1)
        text = text.replace(old, new, 1)
    makefile.write_text(text, encoding="utf-8", newline="\n")
    if git(target, "hash-object", "Makefile") == mirror_makefile_blob:
        raise Block("Mirror Makefile adaptation produced no byte change")

    run(
        (sys.executable, "-B", "tools/qikvrt_aphorism_corpus_v2.py", "--materialize", "--json"),
        cwd=target,
    )
    run(
        (sys.executable, "-B", "tools/qikvrt_aphorism_corpus_v2.py", "--check", "--json"),
        cwd=target,
    )
    run(
        (sys.executable, "-B", "-m", "unittest", "-v", "tests.test_aphorism_corpus_v2"),
        cwd=target,
    )
    for path in portable:
        require_equal(
            f"post-materialization portable blob {path}",
            git(target, "hash-object", path),
            git(target, "rev-parse", f"{authority_head}:{path}"),
        )

    carrier = target / carrier_path
    if not carrier.is_file() or carrier.is_symlink():
        raise Block("target carrier is absent or symlinked before removal")
    carrier.unlink()
    run((sys.executable, "-B", "tools/qikvrt_integrity.py", "generate"), cwd=target)
    run((sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"), cwd=target)
    run(("make", "test"), cwd=target)
    run((sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"), cwd=target)
    run(("git", "diff", "--check"), cwd=target)

    allowed = set(portable) | adapted
    final_paths = set(
        git(
            target,
            "diff",
            "--name-only",
            "--no-renames",
            mirror_parent,
            "--",
        ).splitlines()
    )
    require_equal("final changed-path set", final_paths, allowed)
    require_equal("final changed-path count", len(final_paths), 76)
    require_equal(
        "exact carrier deletion delta",
        git(
            target,
            "diff",
            "--name-status",
            "--no-renames",
            "HEAD",
            "--",
            carrier_path,
        ).splitlines(),
        [f"D\t{carrier_path}"],
    )

    statuses = read_status_paths(target)
    if not statuses:
        raise Block("Mirror candidate has no materialized working-tree delta")
    seen_carrier = False
    for status, path in statuses:
        if status.startswith(("R", "C")):
            raise Block(f"rename/copy status is outside contract: {status!r} {path}")
        if path == carrier_path:
            if status not in {" D", "D "}:
                raise Block(f"carrier deletion status differs: {status!r}")
            seen_carrier = True
            continue
        if path not in allowed:
            raise Block(f"unexpected status path: {status!r} {path}")
    if not seen_carrier:
        raise Block("exact carrier deletion is absent from status")

    required = (
        "docs/publications/2026-08-04-aphorism-corpus-scientific-assessment/QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.pdf",
        "docs/publications/2026-08-04-aphorism-corpus-scientific-assessment/QIK-VRT_Aphorism_Corpus_Scientific_Assessment_2026-08-04.tex",
        "tests/test_ietf_revision_02.py",
        "tests/test_aphorism_corpus_v2.py",
    )
    ensure_files(target, required)
    if carrier.exists() or carrier.is_symlink():
        raise Block("carrier still exists after removal")

    remote_head = git(
        target,
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{target_ref}",
    ).split()
    if not remote_head:
        raise Block("target remote ref is absent")
    require_equal("target remote head before commit", remote_head[0], source_head)

    git(target, "config", "user.name", "github-actions[bot]", capture=False)
    git(
        target,
        "config",
        "user.email",
        "41898282+github-actions[bot]@users.noreply.github.com",
        capture=False,
    )
    git(target, "add", "-A", capture=False)
    staged = set(
        git(
            target,
            "diff",
            "--cached",
            "--name-only",
            "--no-renames",
            mirror_parent,
            "--",
        ).splitlines()
    )
    require_equal("staged final path set", staged, allowed)
    git(
        target,
        "commit",
        "-m",
        "science: materialize Mirror aphorism corpus assessment",
        capture=False,
    )
    final_commit = git(target, "rev-parse", "--verify", "HEAD^{commit}")
    final_tree = git(target, "rev-parse", "--verify", "HEAD^{tree}")
    remote_after_commit = git(
        target,
        "ls-remote",
        "--heads",
        "origin",
        f"refs/heads/{target_ref}",
    ).split()
    require_equal("target remote head before push", remote_after_commit[0], source_head)
    git(target, "push", "origin", f"HEAD:{target_ref}", capture=False)

    print(f"FINAL_COMMIT={final_commit}")
    print(f"FINAL_TREE={final_tree}")
    print(f"PORTABLE_PATH_COUNT={len(portable)}")
    print(f"FINAL_CHANGED_PATH_COUNT={len(allowed)}")
    print("PASS=NOT_CLAIMED")
    print("FINAL_PASS=NOT_CLAIMED")
    print("EFFECT_ACK_DONE=NOT_CLAIMED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Block as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
