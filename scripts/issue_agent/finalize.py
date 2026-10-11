#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_DISPOSITIONS = {
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
CLOSURE_DISPOSITIONS = {
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}


def section(markdown: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)",
        markdown,
    )
    return match.group(1).strip() if match else ""


def disposition_token(markdown: str) -> str | None:
    value = section(markdown, "Issue disposition")
    if not value:
        return None
    token = value.splitlines()[0].strip().strip("`")
    return token if token in ALLOWED_DISPOSITIONS else None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--directory", required=True)
    outcome = p.add_mutually_exclusive_group(required=True)
    outcome.add_argument("--processing-outcome", choices=("success", "failure", "cancelled", "skipped"))
    outcome.add_argument("--inference-outcome", help="Legacy outcome; fail closed without an admitted inference carrier")
    args = p.parse_args()

    directory = Path(args.directory)
    answer = directory / "ANSWER.md"
    compilation_succeeded = (
        args.processing_outcome == "success"
        and answer.exists()
        and bool(answer.read_text(encoding='utf-8').strip())
    )
    if not compilation_succeeded:
        reason = "MODEL_INFERENCE_UNAVAILABLE" if args.inference_outcome is not None else "DETERMINISTIC_COMPILER_FAILED"
        answer.write_text(
            "# Repository answer\n\n"
            "The deterministic compiler failed. No scientific or technical "
            "answer is asserted. The request and repository context were materialized for review.\n\n"
            "## Evidence used\n\nRepository request and materialized context only.\n\n"
            "## Formal status\n\nNOT_EVALUATED\n\n"
            "## Empirical status\n\nNOT_EVALUATED\n\n"
            "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
            f"## Disposition reason\n\n{reason}\n\n"
            "## Required next action\n\nRepair the repository-local compiler and replay this unchanged issue event.\n\n"
            "## Gate result\n\nBLOCK\n",
            encoding="utf-8",
        )

    markdown = answer.read_text(encoding="utf-8")
    disposition = disposition_token(markdown)
    reason = section(markdown, "Disposition reason")
    next_action = section(markdown, "Required next action")
    disposition_valid = (
        disposition is not None
        and bool(reason)
        and bool(next_action)
        and (
            disposition in CLOSURE_DISPOSITIONS
            or next_action.strip().upper() != "NONE"
        )
    )

    if not disposition_valid:
        disposition = "BLOCKED_WITH_NEXT_ACTION"
        reason = "ISSUE_DISPOSITION_MISSING_OR_INVALID"
        next_action = "Regenerate the repository-grounded answer with one allowed disposition, a reason, and one concrete next action."

    status_value = (
        "BLOCK"
        if disposition in {"CLARIFICATION_REQUIRED", "BLOCKED_WITH_NEXT_ACTION"}
        else "CONTINUE"
    )
    status = {
        "status": status_value,
        "issue_materialized": True,
        "deterministic_compilation_completed": compilation_succeeded,
        "external_model_used": False,
        "model_inference_completed": False,
        "processing_carrier": "repository-local-deterministic-compiler",
        "work_unit": {
            "schema": "qikvrt_issue_deterministic_work_unit_v1",
            "request_sha256": hashlib.sha256((directory / "REQUEST.json").read_bytes()).hexdigest(),
            "context_sha256": hashlib.sha256((directory / "CONTEXT.md").read_bytes()).hexdigest(),
            "answer_sha256": hashlib.sha256(answer.read_bytes()).hexdigest(),
            "effecting_handler": None,
            "capability_gap": "NO_REVIEWED_EFFECTING_HANDLER_OR_AUTHORIZED_INFERENCE_CARRIER",
        },
        "issue_disposition": disposition,
        "disposition_reason": reason,
        "next_action": next_action,
        "closure_recommended": disposition in CLOSURE_DISPOSITIONS,
        "automatic_issue_close": False,
        "automatic_merge": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "no_false_pass": True,
    }
    (directory / "STATUS.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
