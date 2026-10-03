#!/usr/bin/env python3
import argparse
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
    p.add_argument("--inference-outcome", required=True)
    args = p.parse_args()

    directory = Path(args.directory)
    answer = directory / "ANSWER.md"
    inference_succeeded = (
        args.inference_outcome == "success"
        and answer.exists()
        and answer.stat().st_size > 0
    )
    if not inference_succeeded:
        optional_adapter_disabled = args.inference_outcome == "skipped"
        explanation = (
            "The optional external model adapter is disabled. The deterministic request and "
            "repository context were materialized for a repository-native work unit. "
            "No scientific or technical answer is asserted.\n\n"
            if optional_adapter_disabled
            else "The autonomous model step was not available or failed. No scientific or technical "
            "answer is asserted. The request and repository context were materialized for review.\n\n"
        )
        reason = "OPTIONAL_MODEL_ADAPTER_DISABLED" if optional_adapter_disabled else "MODEL_INFERENCE_UNAVAILABLE"
        next_action = (
            "Execute the supported deterministic repository-native work unit with its exact-subject gates; "
            "an external model adapter is optional and requires explicit authorization."
            if optional_adapter_disabled
            else "Resume the bounded issue transaction when a trusted inference or deterministic work-unit path is available."
        )
        answer.write_text(
            "# Repository answer\n\n"
            + explanation +
            "## Evidence used\n\nRepository request and materialized context only.\n\n"
            "## Formal status\n\nNOT_EVALUATED\n\n"
            "## Empirical status\n\nNOT_EVALUATED\n\n"
            "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
            f"## Disposition reason\n\n{reason}\n\n"
            f"## Required next action\n\n{next_action}\n\n"
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
        "model_inference_completed": inference_succeeded,
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
