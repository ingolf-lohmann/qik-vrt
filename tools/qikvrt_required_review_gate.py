#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate the live native Code Owner review prerequisite without mutation."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "qikvrt_required_code_owner_review_gate_v1"
DEFAULT_CODE_OWNER = "ingolf-lohmann"
SUCCESS = "success"
PENDING = "pending"
FAILURE = "failure"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
GOVERNANCE_STATUS_CONTEXT = "QIKVRT required code-owner review"
LEGACY_GOVERNANCE_STATUS_CONTEXT = "QIKVRT requested review execution"
REVIEW_DISPOSITION_STATUS_CONTEXT = "QIKVRT requested review disposition"


class ReviewGateInputError(ValueError):
    pass


def resolve_required_code_owner(repository: str, *, policy: Mapping[str, Any] | None = None, codeowners: str | None = None) -> str:
    """Bind the trusted repository's three roles without creating native approval.

    Unknown repositories or a policy/CODEOWNERS disagreement fail closed.
    Human authority, execution identity and durable storage are distinct roles.
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    if policy is None:
        policy = json.loads((root / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text(encoding="utf-8"))
    if not isinstance(policy, Mapping):
        raise ReviewGateInputError("Mesh Authority policy must be an object")
    authority = policy.get("mesh_authority")
    if not isinstance(authority, Mapping):
        raise ReviewGateInputError("current Mesh Authority binding is missing")
    human = authority.get("human")
    executor = authority.get("executor")
    memory = authority.get("repository")
    if not all(isinstance(role, Mapping) for role in (human, executor, memory)):
        raise ReviewGateInputError("Mesh Authority must retain human, executor and repository roles")
    if repository != memory.get("full_name") or repository != authority.get("authority_repository"):
        raise ReviewGateInputError("repository is outside the current Mesh Authority binding")
    owner = _login(human.get("github_login"), "Mesh Authority human login")
    if human.get("type") != "NATURAL_PERSON" or owner.casefold().endswith("[bot]"):
        raise ReviewGateInputError("native Code Owner must be a human principal")
    if executor.get("may_submit_native_approve") is not False or memory.get("may_submit_native_approve") is not False:
        raise ReviewGateInputError("executor and repository cannot supply native human approval")
    if authority.get("independent_native_code_owner_review_required") is not True:
        raise ReviewGateInputError("independent native Code Owner review must remain required")
    if codeowners is None:
        codeowners = (root / ".github/CODEOWNERS").read_text(encoding="utf-8")
    entries = [line.split("#", 1)[0].split() for line in codeowners.splitlines() if line.split("#", 1)[0].strip()]
    if not entries or entries[0] != ["*", "@" + owner] or any(entry[1:] != ["@" + owner] for entry in entries):
        raise ReviewGateInputError("CODEOWNERS disagrees with current Mesh Authority human")
    return owner


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewGateInputError(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise ReviewGateInputError(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _login(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewGateInputError(f"{label} is missing")
    return value.strip()


def _review_sort_key(review: Mapping[str, Any], timestamp_field: str = "submitted_at") -> tuple[str, int]:
    submitted_at = review.get(timestamp_field)
    if not isinstance(submitted_at, str):
        submitted_at = ""
    identifier = review.get("id", -1)
    if isinstance(identifier, bool) or not isinstance(identifier, int):
        identifier = -1
    return submitted_at, identifier


def _block(*, gate_state: str, blocker: str, detail: str, pr_number: Any, head_sha: str | None, required_code_owner: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "gate_state": gate_state,
        "first_blocker": blocker,
        "detail": detail,
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owner": required_code_owner,
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def native_code_owner_rule_is_enforced(rules: Sequence[Mapping[str, Any]]) -> bool:
    for rule in rules:
        if rule.get("type") != "pull_request":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, Mapping):
            continue
        count = parameters.get("required_approving_review_count")
        if isinstance(count, bool) or not isinstance(count, int):
            continue
        if (
            count >= 1
            and parameters.get("require_code_owner_review") is True
            and parameters.get("dismiss_stale_reviews_on_push") is True
            and parameters.get("require_last_push_approval") is True
        ):
            return True
    return False


def evaluate_required_review(pr: Mapping[str, Any], rules: Sequence[Mapping[str, Any]], reviews: Sequence[Mapping[str, Any]], *, required_code_owner: str = DEFAULT_CODE_OWNER) -> dict[str, Any]:
    if not isinstance(pr, Mapping):
        raise ReviewGateInputError("pull request observation must be an object")
    if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes)):
        raise ReviewGateInputError("rules observation must be a list")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise ReviewGateInputError("reviews observation must be a list")
    if not all(isinstance(rule, Mapping) for rule in rules):
        raise ReviewGateInputError("rules observation contains a non-object")
    if not all(isinstance(review, Mapping) for review in reviews):
        raise ReviewGateInputError("reviews observation contains a non-object")

    head = pr.get("head")
    author = pr.get("user")
    if not isinstance(head, Mapping) or not isinstance(author, Mapping):
        raise ReviewGateInputError("pull request must contain head and user objects")
    head_sha = _sha(head.get("sha"), "pull request head.sha")
    author_login = _login(author.get("login"), "pull request user.login")
    owner_login = _login(required_code_owner, "required code owner")
    pr_number = pr.get("number")

    if not native_code_owner_rule_is_enforced(rules):
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_RULE_NOT_ENFORCED",
            detail="main must require one approval, Code Owner review, stale-review dismissal, and last-push approval",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    owner_reviews = [
        review for review in reviews
        if isinstance(review.get("user"), Mapping)
        and isinstance(review["user"].get("login"), str)
        and review["user"]["login"].casefold() == owner_login.casefold()
    ]
    if not owner_reviews:
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_MISSING", detail=f"no review from @{owner_login} is present", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)

    exact_head_reviews = [review for review in owner_reviews if review.get("commit_id") == head_sha]
    if not exact_head_reviews:
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_STALE", detail=f"@{owner_login} has no review bound to current head {head_sha}", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)

    decisive = [
        review for review in exact_head_reviews
        if isinstance(review.get("state"), str) and review["state"].upper() in DECISIVE_REVIEW_STATES
    ]
    if not decisive:
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_NOT_APPROVED", detail=f"@{owner_login} has no decisive current-head review", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)

    latest = max(decisive, key=_review_sort_key)
    latest_state = latest["state"].upper()
    if latest_state == "CHANGES_REQUESTED":
        return _block(gate_state=FAILURE, blocker="CODE_OWNER_REVIEW_CHANGES_REQUESTED", detail=f"@{owner_login} requested changes on current head {head_sha}", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)
    if latest_state == "DISMISSED":
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_DISMISSED", detail=f"@{owner_login}'s current-head review was dismissed", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)
    if latest_state != "APPROVED":
        raise ReviewGateInputError(f"unsupported decisive review state: {latest_state}")
    if author_login.casefold() == owner_login.casefold():
        return _block(gate_state=FAILURE, blocker="CODE_OWNER_REVIEW_SELF_APPROVAL", detail="the pull-request author cannot satisfy the independent Code Owner review gate", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)
    if latest["user"].get("type") == "Bot" or owner_login.casefold().endswith("[bot]"):
        return _block(gate_state=FAILURE, blocker="CODE_OWNER_REVIEW_AUTOMATED_APPROVAL", detail="an automated reviewer cannot satisfy independent Code Owner approval", pr_number=pr_number, head_sha=head_sha, required_code_owner=owner_login)

    return {
        "schema": SCHEMA,
        "gate_state": SUCCESS,
        "first_blocker": None,
        "detail": f"@{owner_login} approved the current head",
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owner": owner_login,
        "review_id": latest.get("id"),
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def project_governance(pr: Mapping[str, Any], rules: Sequence[Mapping[str, Any]], reviews: Sequence[Mapping[str, Any]], statuses: Sequence[Mapping[str, Any]], *, required_code_owner: str = DEFAULT_CODE_OWNER) -> dict[str, Any]:
    """Project fresh native evidence; execution success is never an input vote.

    The dedicated status must agree with the fresh native decision. The old
    shared status is a compatibility alias, never a substitute for that status.
    A missing, conflicting or stale publication keeps acceptance closed.
    """
    decision = evaluate_required_review(pr, rules, reviews, required_code_owner=required_code_owner)
    if not isinstance(statuses, list) or not all(isinstance(item, Mapping) for item in statuses):
        raise ReviewGateInputError("statuses observation must be a list of objects")
    latest = {}
    for item in statuses:
        context = item.get("context")
        if context in {GOVERNANCE_STATUS_CONTEXT, LEGACY_GOVERNANCE_STATUS_CONTEXT}:
            previous = latest.get(context)
            if previous is None or _review_sort_key(item, "created_at") > _review_sort_key(previous, "created_at"):
                latest[context] = item
    state, blocker = decision["gate_state"], decision["first_blocker"]
    published = latest.get(GOVERNANCE_STATUS_CONTEXT)
    legacy = latest.get(LEGACY_GOVERNANCE_STATUS_CONTEXT)
    if state == SUCCESS:
        if published is None:
            state, blocker = PENDING, "NATIVE_GOVERNANCE_STATUS_MISSING"
        elif published.get("state") != SUCCESS:
            state, blocker = FAILURE, "NATIVE_GOVERNANCE_STATUS_NOT_SUCCESSFUL"
        elif legacy is not None and legacy.get("state") != SUCCESS:
            state, blocker = FAILURE, "GOVERNANCE_STATUS_DISAGREEMENT"
    return {
        "schema": "qikvrt_governance_projection_v1",
        "pr_number": decision["pr_number"],
        "head_sha": decision["head_sha"],
        "base_sha": (pr.get("base") or {}).get("sha"),
        "gate_state": state,
        "first_blocker": blocker,
        "native_review_gate": decision,
        "acceptance": "NATIVE_GOVERNANCE_SATISFIED" if state == SUCCESS else "BLOCKED",
        "status_context": GOVERNANCE_STATUS_CONTEXT,
        "status_id": published.get("id") if published else None,
        "legacy_status_context": LEGACY_GOVERNANCE_STATUS_CONTEXT,
        "legacy_status_id": legacy.get("id") if legacy else None,
        "execution_success_implies_enforcement": False,
        "execution_success_implies_independent_approval": False,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def _load_json(path: str) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluate", nargs="?", default="evaluate")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--required-code-owner", default=DEFAULT_CODE_OWNER)
    args = parser.parse_args(argv)
    try:
        result = evaluate_required_review(_load_json(args.pr), _load_json(args.rules), _load_json(args.reviews), required_code_owner=args.required_code_owner)
    except (OSError, ValueError, json.JSONDecodeError, ReviewGateInputError) as exc:
        result = _block(gate_state=FAILURE, blocker="INVALID_REVIEW_GATE_SNAPSHOT", detail=str(exc), pr_number=None, head_sha=None, required_code_owner=args.required_code_owner)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["gate_state"] == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
