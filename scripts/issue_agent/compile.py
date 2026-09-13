#!/usr/bin/env python3
"""Compile an issue into a bounded disposition without external cognition."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_DISPOSITIONS = (
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
)


def compile_issue(issue_path: Path, context_path: Path, output_path: Path) -> None:
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
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
    args = parser.parse_args()
    compile_issue(Path(args.issue), Path(args.context), Path(args.output))


if __name__ == "__main__":
    main()
