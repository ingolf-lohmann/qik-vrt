#!/usr/bin/env python3
"""Compile an issue into a bounded disposition without external cognition."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.qikvrt_subprocess import run_bounded

ROOT = Path(__file__).resolve().parents[2]
PROCESSOR_PATHS = (
    '.github/workflows/issue-autonomous-processing.yml',
    '.github/workflows/issue-agent-backlog-resume.yml',
    'scripts/issue_agent/materialize.py', 'scripts/issue_agent/compile.py',
    'scripts/issue_agent/finalize.py', 'scripts/issue_agent/promote.py',
    'scripts/issue_agent/validate.py', 'scripts/issue_agent/handoff.py',
    'tools/qikvrt_subprocess.py', 'tools/qikvrt_integrity.py',
    'policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json',
)
ARTIFACTS = ('REQUEST.json', 'REQUEST.sha256', 'CONTEXT.md', 'ANSWER.md', 'STATUS.json')


def load_issue(path: Path) -> dict:
    try:
        issue = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError, OSError):
        raise SystemExit('INVALID_ISSUE_JSON') from None
    if not isinstance(issue, dict):
        raise SystemExit('INVALID_ISSUE_JSON')
    number = issue.get('number')
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise SystemExit('INVALID_ISSUE_NUMBER')
    if any(not isinstance(issue.get(k) or '', str) for k in ('title', 'body')):
        raise SystemExit('INVALID_ISSUE_TEXT')
    return issue


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def admission(*, issue_path: Path, context_path: Path, repository: str,
              previous_ref: str | None, root: Path, processor_root: Path = ROOT) -> dict:
    """Read-only causal admission. HEAD, timestamps and run IDs are not causes."""
    issue = load_issue(issue_path)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise SystemExit('INVALID_REPOSITORY')
    semantic_request = {'repository': repository, 'issue_number': issue['number'],
                        'title': issue.get('title') or '', 'body': issue.get('body') or ''}
    inputs = {
        'request_sha256': digest(json.dumps(semantic_request, ensure_ascii=False,
                                           sort_keys=True, separators=(',', ':')).encode()),
        'context_sha256': digest(context_path.read_bytes()),
        'processor_blobs': {p: digest((processor_root / p).read_bytes()) for p in PROCESSOR_PATHS},
    }
    fingerprint = digest(json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode())
    receipt = {'schema': 'qikvrt_issue_causal_attempt_v1', 'repository': repository,
               'issue_number': issue['number'], 'fingerprint': fingerprint, 'inputs': inputs,
               'execute': True, 'reason': 'NEW_CAUSAL_INPUT', 'previous_branch_head': None,
               'automatic_merge': False, 'automatic_issue_close': False, 'EFFECT_ACK_DONE': False}
    if previous_ref is None:
        return receipt
    expected_ref = f'refs/remotes/origin/issue-agent/{issue["number"]}'
    if previous_ref != expected_ref:
        raise SystemExit('INVALID_PREVIOUS_REF')
    def git(*args: str):
        return run_bounded(['git', *args], cwd=root, timeout=60, max_output_bytes=1_048_576)
    result = git('rev-parse', '--verify', previous_ref + '^{commit}')
    if result.returncode or result.timed_out or result.output_limit_exceeded:
        raise SystemExit('PREVIOUS_BRANCH_READBACK_UNAVAILABLE')
    head = result.stdout.strip()
    receipt['previous_branch_head'] = head
    prefix = f'evidence/issues/{issue["number"]}/'
    listing = git('ls-tree', '--name-only', head, prefix + 'ATTEMPT.json')
    if listing.returncode or listing.timed_out or listing.output_limit_exceeded:
        raise SystemExit('PREVIOUS_ATTEMPT_READBACK_UNAVAILABLE')
    if not listing.stdout.strip():
        receipt['reason'] = 'LEGACY_PROCESSOR_MIGRATION'
        return receipt
    previous = git('show', head + ':' + prefix + 'ATTEMPT.json')
    if previous.returncode or previous.timed_out or previous.output_limit_exceeded:
        raise SystemExit('PREVIOUS_ATTEMPT_READBACK_UNAVAILABLE')
    try:
        old = json.loads(previous.stdout)
        if (old['schema'] != receipt['schema'] or old['repository'] != repository
            or old['issue_number'] != issue['number'] or old.get('recorded') is not True
            or digest(json.dumps(old['inputs'], sort_keys=True, separators=(',', ':')).encode()) != old['fingerprint']):
            raise ValueError()
        for name in ARTIFACTS:
            artifact = git('show', head + ':' + prefix + name)
            if (artifact.returncode or artifact.timed_out or artifact.output_limit_exceeded
                or digest(artifact.stdout.encode('utf-8', errors='surrogateescape')) != old['artifacts'][name]):
                raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise SystemExit('PREVIOUS_ATTEMPT_INVALID') from None
    if old['fingerprint'] == fingerprint:
        receipt.update(execute=False, reason='NOOP_UNCHANGED_CAUSAL_INPUT')
    return receipt


def record_attempt(directory: Path, receipt_path: Path) -> None:
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('execute') is not True:
        raise SystemExit('UNADMITTED_ATTEMPT')
    request = json.loads((directory / 'REQUEST.json').read_text())
    if (request.get('repository') != receipt.get('repository')
        or request.get('issue_number') != receipt.get('issue_number')):
        raise SystemExit('ATTEMPT_SUBJECT_MISMATCH')
    semantic = {k: request.get(k) for k in ('repository', 'issue_number', 'title', 'body')}
    if (digest(json.dumps(semantic, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':')).encode()) != receipt['inputs']['request_sha256']
        or digest((directory / 'CONTEXT.md').read_bytes()) != receipt['inputs']['context_sha256']):
        raise SystemExit('ATTEMPT_INPUT_MISMATCH')
    receipt['recorded'] = True
    receipt['artifacts'] = {name: digest((directory / name).read_bytes()) for name in ARTIFACTS}
    receipt['processing_status'] = json.loads((directory / 'STATUS.json').read_text())['status']
    (directory / 'ATTEMPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')


def preserve_previous(directory: Path) -> None:
    """Retain existing evidence by content identity before materialization."""
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise SystemExit('UNSAFE_EVIDENCE_DIRECTORY')
    if any((directory / name).is_symlink() for name in (*ARTIFACTS, 'ATTEMPT.json')):
        raise SystemExit('UNSAFE_EVIDENCE_ARTIFACT')
    names = [name for name in (*ARTIFACTS, 'ATTEMPT.json') if (directory / name).is_file()]
    if not names:
        return
    identity = digest(json.dumps({n: digest((directory / n).read_bytes()) for n in names},
                                 sort_keys=True, separators=(',', ':')).encode())
    archive = directory / 'history' / identity
    if archive.is_symlink() or archive.parent.is_symlink():
        raise SystemExit('UNSAFE_EVIDENCE_HISTORY')
    archive.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = archive / name
        if target.is_symlink():
            raise SystemExit('UNSAFE_EVIDENCE_HISTORY')
        if target.exists() and target.read_bytes() != (directory / name).read_bytes():
            raise SystemExit('HISTORICAL_EVIDENCE_COLLISION')
        shutil.copyfile(directory / name, target)

ALLOWED_DISPOSITIONS = (
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
)


def compile_issue(issue_path: Path, context_path: Path, output_path: Path) -> None:
    issue = load_issue(issue_path)
    context_path.read_text(encoding="utf-8")
    number = issue.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise SystemExit("INVALID_ISSUE_NUMBER")

    # Only named, repository-reviewed handlers may ever turn an untrusted issue
    # into an executable work unit. The initial compiler intentionally has no
    # effecting handler; unsupported inputs remain visible instead of invoking a
    # model or manufacturing completion.
    answer = (
        "# Repository answer\n\n"
        f"Issue #{number} was materialized and classified by the repository-local "
        "deterministic compiler. No allowlisted executable handler matches this "
        "request on the current tree.\n\n"
        "## Evidence used\n\nExact issue JSON and bounded repository context.\n\n"
        "## Formal status\n\nNOT_EVALUATED\n\n"
        "## Empirical status\n\nNOT_EVALUATED\n\n"
        "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
        "## Disposition reason\n\nUNSUPPORTED_DETERMINISTIC_WORK_UNIT\n\n"
        "## Required next action\n\nAdd and review one schema-validated, "
        "effect-bounded handler for this work-unit class, then replay the unchanged issue event.\n\n"
        "## Gate result\n\nBLOCK\n"
    )
    output_path.write_text(answer, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument('--check-admission', action='store_true')
    parser.add_argument('--repository')
    parser.add_argument('--previous-ref')
    args = parser.parse_args()
    if args.check_admission:
        failure = None
        try:
            receipt = admission(issue_path=Path(args.issue), context_path=Path(args.context),
                                repository=args.repository or '', previous_ref=args.previous_ref,
                                root=Path.cwd())
        except (SystemExit, ValueError, KeyError, TypeError, OSError) as exc:
            failure = str(exc) if isinstance(exc, SystemExit) else 'CAUSAL_ADMISSION_UNAVAILABLE'
            receipt = {'schema': 'qikvrt_issue_causal_attempt_v1', 'execute': False,
                       'reason': failure, 'repository': args.repository,
                       'automatic_merge': False, 'automatic_issue_close': False, 'EFFECT_ACK_DONE': False}
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        print(receipt['reason'])
        if failure:
            raise SystemExit(2)
        return
    compile_issue(Path(args.issue), Path(args.context), Path(args.output))


if __name__ == "__main__":
    main()
