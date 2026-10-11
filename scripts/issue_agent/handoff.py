#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Read back a published proposal and report review admission independently.

This refactors the existing gh PR/issue commands. It never pushes, approves,
merges, closes an issue, changes policy, or retries an ambiguous write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.issue_agent.validate import REQUIRED, validate
from tools.qikvrt_subprocess import run_bounded


class HandoffError(RuntimeError):
    pass


def command(arguments: list[str], root: Path):
    return run_bounded(arguments, cwd=root, timeout=60, max_output_bytes=1_048_576)


def checked(arguments: list[str], root: Path, failure: str) -> str:
    result = command(arguments, root)
    if result.returncode or result.timed_out or result.output_limit_exceeded:
        raise HandoffError(failure)
    return result.stdout.strip()


def write_receipt(output: Path, receipt: dict) -> None:
    (output / "HANDOFF.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def freeze_subject(root: Path, receipt: dict) -> None:
    """Bind committed bytes, then independently fetch the exact remote branch."""
    head, branch = receipt["commit"], receipt["branch"]
    actual = checked(["git", "rev-parse", "HEAD^{commit}"], root, "LOCAL_HEAD_UNAVAILABLE")
    tree = checked(["git", "rev-parse", f"{head}^{{tree}}"], root, "LOCAL_TREE_UNAVAILABLE")
    if actual != head or tree != receipt["tree"]:
        raise HandoffError("LOCAL_SUBJECT_MISMATCH")
    if checked(["git", "symbolic-ref", "--short", "HEAD"], root, "LOCAL_BRANCH_UNAVAILABLE") != branch:
        raise HandoffError("LOCAL_BRANCH_MISMATCH")
    receipt["source_tree"] = checked(
        ["git", "rev-parse", receipt["source_commit"] + "^{tree}"], root, "SOURCE_TREE_UNAVAILABLE"
    )
    directory = root / "evidence" / "issues" / str(receipt["issue_number"])
    validate(directory)
    request = json.loads((directory / "REQUEST.json").read_text(encoding="utf-8"))
    if request.get("repository") != receipt["repository"] or request.get("issue_number") != receipt["issue_number"]:
        raise HandoffError("REQUEST_SUBJECT_MISMATCH")
    for name in (*REQUIRED, *(('ATTEMPT.json',) if (directory / 'ATTEMPT.json').exists() else ())):
        path = (directory / name).relative_to(root).as_posix()
        raw = checked(["git", "rev-parse", f"{head}:{path}"], root, "ARTIFACT_BLOB_UNAVAILABLE")
        result = command(["git", "show", f"{head}:{path}"], root)
        if result.returncode or result.timed_out or result.output_limit_exceeded:
            raise HandoffError("ARTIFACT_BYTES_UNAVAILABLE")
        data = result.stdout.encode("utf-8", errors="surrogateescape")
        if data != (root / path).read_bytes():
            raise HandoffError("ARTIFACT_WORKTREE_MISMATCH")
        receipt["artifacts"].append({
            "path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "git_blob_sha1": raw,
        })
    status = json.loads((directory / "STATUS.json").read_text(encoding="utf-8"))
    receipt["processing_status"] = status["status"]
    receipt["issue_disposition"] = status["issue_disposition"]
    receipt["processing_carrier"] = status.get("processing_carrier", "repository-local-deterministic-compiler")
    receipt["processing_reason"] = status["disposition_reason"]
    remote = checked(
        ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"], root,
        "WORK_BRANCH_READBACK_UNAVAILABLE",
    )
    if remote.split() != [head, f"refs/heads/{branch}"]:
        raise HandoffError("WORK_BRANCH_HEAD_MISMATCH")
    checked(["git", "fetch", "--no-tags", "origin", f"refs/heads/{branch}"], root, "WORK_BRANCH_FETCH_FAILED")
    fetched = checked(["git", "rev-parse", "FETCH_HEAD^{commit}"], root, "WORK_BRANCH_COMMIT_UNAVAILABLE")
    fetched_tree = checked(["git", "rev-parse", "FETCH_HEAD^{tree}"], root, "WORK_BRANCH_TREE_UNAVAILABLE")
    if fetched != head or fetched_tree != receipt["tree"]:
        raise HandoffError("WORK_BRANCH_SUBJECT_MISMATCH")
    receipt["branch_readback_verified"] = True


def read_pr(root: Path, receipt: dict) -> dict | None:
    repo = receipt["repository"]
    head = quote(repo.split("/")[0] + ":" + receipt["branch"], safe="")
    data = json.loads(checked(
        ["gh", "api", f"repos/{repo}/pulls?state=open&head={head}&base=main&per_page=100"],
        root, "PR_LOOKUP_UNAVAILABLE",
    ))
    if not isinstance(data, list) or len(data) > 1:
        raise HandoffError("PR_LOOKUP_AMBIGUOUS")
    if not data:
        return None
    pr = data[0]
    if not isinstance(pr, dict):
        raise HandoffError("PR_RESPONSE_INVALID")
    for part in ("head", "base"):
        if not isinstance(pr.get(part), dict) or not isinstance(pr[part].get("repo"), dict):
            raise HandoffError("PR_SUBJECT_MISMATCH")
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise HandoffError("PR_IDENTITY_INVALID")
    if (pr.get("state") != "open" or pr.get("html_url") != f"https://github.com/{repo}/pull/{number}"
        or pr.get("base", {}).get("ref") != "main"
        or pr.get("base", {}).get("repo", {}).get("full_name") != repo
        or pr.get("head", {}).get("ref") != receipt["branch"]
        or pr.get("head", {}).get("repo", {}).get("full_name") != repo
        or pr.get("head", {}).get("sha") != receipt["commit"]):
        raise HandoffError("PR_SUBJECT_MISMATCH")
    return {"number": number, "url": pr["html_url"], "head": pr["head"]["sha"], "draft": pr.get("draft")}


def review_handoff(root: Path, output: Path, receipt: dict) -> None:
    pr = read_pr(root, receipt)
    if pr is None:
        if receipt['pr_create_attempts']:
            raise HandoffError('PR_CREATE_RETRY_REQUIRES_NEW_CAPABILITY_EVIDENCE')
        body = output / "PR_BODY.md"
        body.write_text(
            f"Repository-local processing proposal for #{receipt['issue_number']}.\n\n"
            f"Branch: `{receipt['branch']}`\nHEAD: `{receipt['commit']}`\nTREE: `{receipt['tree']}`\n\n"
            "automatic_merge=false; automatic_issue_close=false.\n"
            "Current-head repository checks, independent review and effect verification remain required.\n"
            "The proposal does not authorize synchronization, tagging or completion.\n",
            encoding="utf-8",
        )
        receipt["pr_create_attempts"] = 1
        write_receipt(output, receipt)  # retain the attempt before the external write
        request_path = output / 'PR_REQUEST.json'
        request_path.write_text(json.dumps({
            'base': 'main', 'head': receipt['branch'], 'draft': True,
            'title': f"Issue agent: process #{receipt['issue_number']}",
            'body': body.read_text(encoding='utf-8'),
        }))
        result = command([
            'gh', 'api', '--method', 'POST', f"repos/{receipt['repository']}/pulls",
            '--input', str(request_path),
        ], root)
        if result.returncode or result.timed_out or result.output_limit_exceeded:
            # Persist a bounded cause, never arbitrary provider text or tokens.
            denied = any(s in result.stderr.lower() for s in (
                'not permitted to create or approve pull requests', 'resource not accessible by integration', 'http 403'))
            receipt["pr_create_error"] = "PR_CREATION_NOT_PERMITTED" if denied else "PR_CREATE_FAILED_OR_AMBIGUOUS"
            receipt["pr_create_exit_code"] = result.returncode
        # One authoritative read after success OR an ambiguous/denied response;
        # never another create attempt in this transaction.
        pr = read_pr(root, receipt)
        if pr is None:
            raise HandoffError(receipt.get("pr_create_error", "PR_CREATION_NOT_OBSERVED"))
    # A matching PR cannot repair a branch that advanced during admission.
    remote = checked(["git", "ls-remote", "--heads", "origin", f"refs/heads/{receipt['branch']}"],
                     root, "WORK_BRANCH_READBACK_UNAVAILABLE")
    if remote.split() != [receipt["commit"], f"refs/heads/{receipt['branch']}"]:
        raise HandoffError("WORK_BRANCH_ADVANCED_DURING_HANDOFF")
    receipt["pull_request"] = pr
    receipt["handoff_status"] = "REVIEW_HANDOFF_READY"
    receipt["next_action"] = "Review this exact proposal under the existing current-head governance gates."


def comment_body(receipt: dict) -> str:
    repo, issue, head = receipt["repository"], receipt["issue_number"], receipt["commit"]
    lines = [
        f"<!-- qikvrt-issue-handoff:{issue}:{head} -->",
        f"Repository processing status: **{receipt['processing_status']}**",
        f"Review handoff status: **{receipt['handoff_status']}**", "",
        f"Branch: `{receipt['branch']}`", f"Commit: `{head}`", f"Root tree: `{receipt['tree']}`",
        f"Processor source: `{receipt['source_commit']}`", "",
        f"Committed evidence: https://github.com/{repo}/tree/{head}/evidence/issues/{issue}",
        f"Exact comparison: https://github.com/{repo}/compare/{receipt['source_commit']}...{head}",
        f"Run / HANDOFF.json artifact: {receipt['run_url']} ({receipt['artifact_name']})", "",
    ]
    if receipt.get("pull_request"):
        lines.append(f"Review PR: {receipt['pull_request']['url']}")
    else:
        lines.append(f"No matching review PR was verified. Capability: {receipt.get('failure_class', 'UNVERIFIED')}.")
    lines.extend(["", "| Committed artifact | Bytes | SHA-256 | Git blob |", "| --- | ---: | --- | --- |"])
    for artifact in receipt["artifacts"]:
        lines.append(f"| `{artifact['path']}` | {artifact['bytes']} | `{artifact['sha256']}` | `{artifact['git_blob_sha1']}` |")
    lines.extend([
        "", f"Next action: {receipt['next_action']}", "",
        "automatic_merge=false; automatic_issue_close=false; EFFECT_ACK_DONE=false.",
        "Branch persistence, review admission and processing completion are separate evidence states.", "",
    ])
    return "\n".join(lines)


def notify_issue(root: Path, output: Path, receipt: dict) -> None:
    body = comment_body(receipt)
    body_path = output / "ISSUE_COMMENT.md"
    body_path.write_text(body, encoding="utf-8")
    receipt["issue_comment_sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    marker = body.splitlines()[0]
    def existing_comment():
        matches = []
        for page in range(1, 101):
            rows = json.loads(checked([
                'gh', 'api', f"repos/{receipt['repository']}/issues/{receipt['issue_number']}/comments?per_page=100&page={page}",
            ], root, 'ISSUE_NOTIFICATION_LOOKUP_UNAVAILABLE'))
            if not isinstance(rows, list):
                raise HandoffError('ISSUE_NOTIFICATION_RESPONSE_INVALID')
            matches.extend(row for row in rows if isinstance(row, dict) and marker in (row.get('body') or ''))
            if len(rows) < 100:
                break
        else:
            raise HandoffError('ISSUE_NOTIFICATION_INVENTORY_INCOMPLETE')
        if len(matches) > 1:
            raise HandoffError('ISSUE_NOTIFICATION_AMBIGUOUS')
        if matches and matches[0].get('body') != body:
            raise HandoffError('ISSUE_NOTIFICATION_EXISTING_BODY_MISMATCH')
        return matches[0]['html_url'] if matches else None
    url = existing_comment()
    if url is None:
        if receipt['issue_comment_attempts']:
            raise HandoffError('ISSUE_NOTIFICATION_RETRY_REQUIRES_NEW_CAPABILITY_EVIDENCE')
        receipt['issue_comment_attempts'] = 1
        receipt['notification_status'] = 'ATTEMPTED'
        write_receipt(output, receipt)
        request_path = output / 'COMMENT_REQUEST.json'
        request_path.write_text(json.dumps({'body': body}))
        result = command([
            'gh', 'api', '--method', 'POST',
            f"repos/{receipt['repository']}/issues/{receipt['issue_number']}/comments",
            '--input', str(request_path),
        ], root)
        # Even a connection loss can follow a successful write; observe first.
        url = existing_comment()
        if url is None:
            raise HandoffError('ISSUE_NOTIFICATION_FAILED_OR_AMBIGUOUS')
    match = re.fullmatch(
        rf"https://github\.com/{re.escape(receipt['repository'])}/issues/{receipt['issue_number']}#issuecomment-([0-9]+)", url
    )
    if not match:
        raise HandoffError("ISSUE_NOTIFICATION_READBACK_UNAVAILABLE")
    remote = json.loads(checked(
        ["gh", "api", f"repos/{receipt['repository']}/issues/comments/{match.group(1)}"],
        root, "ISSUE_NOTIFICATION_READBACK_UNAVAILABLE",
    ))
    if (remote.get("body") != body or remote.get("html_url") != url
        or remote.get("issue_url") != f"https://api.github.com/repos/{receipt['repository']}/issues/{receipt['issue_number']}"):
        raise HandoffError("ISSUE_NOTIFICATION_READBACK_MISMATCH")
    receipt["notification_status"] = "ISSUE_COMMENT_READBACK_VERIFIED"
    receipt["issue_comment_url"] = url


def handoff(*, root: Path, output: Path, repository: str, issue_number: int,
            commit: str, tree: str, source_commit: str, run_id: str, run_attempt: str) -> dict:
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
        or isinstance(issue_number, bool) or issue_number <= 0
        or any(not re.fullmatch(r"[0-9a-f]{40}", value) for value in (commit, tree, source_commit))
        or any(not re.fullmatch(r"[1-9][0-9]*", value) for value in (run_id, run_attempt))):
        raise HandoffError("INVALID_HANDOFF_SUBJECT")
    output.mkdir(parents=True, exist_ok=True)
    previous_path = output / 'HANDOFF.json'
    try:
        previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
        if not isinstance(previous, dict):
            raise ValueError()
    except (ValueError, OSError):
        raise HandoffError('RESUME_RECEIPT_INVALID') from None
    if previous and any(previous.get(key) != value for key, value in (
        ('repository', repository), ('issue_number', issue_number), ('commit', commit),
        ('tree', tree), ('source_commit', source_commit))):
        raise HandoffError('RESUME_SUBJECT_MISMATCH')
    receipt = {
        "schema": "qikvrt_issue_review_handoff_v1", "repository": repository,
        "issue_number": issue_number, "branch": f"issue-agent/{issue_number}",
        "commit": commit, "tree": tree, "source_commit": source_commit,
        "run_id": run_id, "run_attempt": run_attempt,
        "run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
        "artifact_name": f"issue-agent-handoff-{issue_number}-{run_id}-{run_attempt}",
        "artifacts": [], "branch_readback_verified": False,
        "processing_status": "UNVERIFIED", "handoff_status": "REVIEW_HANDOFF_BLOCKED",
        "notification_status": "NOT_ATTEMPTED", "pr_create_attempts": 0, "issue_comment_attempts": 0,
        "automatic_merge": False, "automatic_issue_close": False, "EFFECT_ACK_DONE": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for key in ('pr_create_attempts', 'issue_comment_attempts'):
        if previous:
            receipt[key] = previous[key]
    write_receipt(output, receipt)
    try:
        freeze_subject(root, receipt)
        review_handoff(root, output, receipt)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, AttributeError, SystemExit) as exc:
        receipt["failure_class"] = str(exc) if isinstance(exc, HandoffError) else "HANDOFF_VALIDATION_FAILED"
        receipt["next_action"] = (
            "Use an authorized PR-creation carrier for the bound branch/commit, then verify the PR head."
            if receipt["failure_class"] in {"PR_CREATION_NOT_PERMITTED", "PR_CREATE_FAILED_OR_AMBIGUOUS", "PR_CREATION_NOT_OBSERVED"}
            else "Repair the named readback or subject mismatch, then reobserve the bound branch/commit before any write."
        )
    write_receipt(output, receipt)
    try:
        notify_issue(root, output, receipt)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        receipt["notification_status"] = "ISSUE_NOTIFICATION_BLOCKED"
        receipt["notification_failure"] = str(exc) if isinstance(exc, HandoffError) else "ISSUE_NOTIFICATION_UNAVAILABLE"
    write_receipt(output, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue-number", required=True, type=int)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--output-directory", required=True, type=Path)
    args = parser.parse_args()
    receipt = handoff(root=Path.cwd(), output=args.output_directory, repository=args.repository,
                      issue_number=args.issue_number, commit=args.commit, tree=args.tree,
                      source_commit=args.source_commit, run_id=args.run_id, run_attempt=args.run_attempt)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as stream:
            stream.write((args.output_directory / "ISSUE_COMMENT.md").read_text(encoding="utf-8"))
            stream.write(f"\nNotification: **{receipt['notification_status']}**\n")
    print(receipt["handoff_status"], receipt["notification_status"])
    if receipt["handoff_status"] != "REVIEW_HANDOFF_READY" or receipt["notification_status"] != "ISSUE_COMMENT_READBACK_VERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
