#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate explicit Principal review or independent native review without mutation."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from datetime import datetime
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
OWNER_RECORD = "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
PRINCIPAL_REVIEW_MARKER = "<!-- qikvrt-owner-principal-review-v1 -->"
PRINCIPAL_REVIEW_SCHEMA = "qikvrt_owner_principal_review_v1"


class ReviewGateInputError(ValueError):
    pass


def validate_review_acceptance_policy(policy: Mapping[str, Any], root: pathlib.Path) -> Mapping[str, Any] | None:
    """Validate the Owner's versioned decision; never infer an account approval.

    Historical independent-review policies remain readable. The alternative
    requires the explicit, exact-byte-bound Principal decision of 18 October.
    """
    authority = policy.get("mesh_authority") or {}
    configured = authority.get("principal_review")
    independent = authority.get("independent_native_code_owner_review_required")
    if configured is None:
        if independent is not True:
            raise ReviewGateInputError("review acceptance requires an explicit Owner decision")
        return None
    if independent is not False or not isinstance(configured, Mapping):
        raise ReviewGateInputError("Principal review and independent-review-only policy disagree")
    if configured.get("source") != OWNER_RECORD or policy.get("owner_delegation") != OWNER_RECORD:
        raise ReviewGateInputError("Principal review has an unbound Owner source")
    try:
        original = (root / OWNER_RECORD).read_bytes()
        record = json.loads(original)
    except (OSError, UnicodeError, ValueError) as exc:
        raise ReviewGateInputError("Principal review Owner source is unavailable or invalid") from exc
    if hashlib.sha256(original).hexdigest() != configured.get("source_sha256"):
        raise ReviewGateInputError("Principal review Owner source bytes do not match")
    if not isinstance(record, Mapping):
        raise ReviewGateInputError("Principal review Owner source must be an object")
    human = authority.get("human") or {}
    owner = record.get("owner") or {}
    if not isinstance(human, Mapping) or not isinstance(owner, Mapping):
        raise ReviewGateInputError("Principal review human Owner binding is invalid")
    recorded = record.get("principal_review_decision")
    if (record.get("state") != "ACTIVE" or authority.get("authority_repository") not in record.get("repositories", [])
            or human.get("type") != "NATURAL_PERSON" or owner.get("type") != "NATURAL_PERSON"
            or human.get("name") != owner.get("name") or not isinstance(recorded, Mapping)):
        raise ReviewGateInputError("Principal review does not retain an active human Owner decision")
    obligations = {
        "schema": "qikvrt_principal_review_policy_v1", "state": "ACTIVE",
        "principal_login": human.get("github_login"),
        "approval_is_review": True, "exact_current_head_required": True,
        "native_review_state": "COMMENTED", "independent_native_approval_required": False,
        "github_platform_protections_may_be_bypassed": False,
        "automated_disposition_can_substitute": False,
    }
    for field, expected in obligations.items():
        for item in (configured, recorded):
            matches = item.get(field) is expected if isinstance(expected, bool) else item.get(field) == expected
            if not matches:
                raise ReviewGateInputError(f"Principal review violates {field}")
    identifier = configured.get("principal_github_id")
    if (isinstance(identifier, bool) or not isinstance(identifier, int) or identifier <= 0
            or recorded.get("principal_github_id") != identifier
            or not isinstance(human.get("github_login"), str) or human["github_login"].casefold().endswith("[bot]")):
        raise ReviewGateInputError("Principal review requires the bound human account identity")
    instruction = recorded.get("instruction") or {}
    if not isinstance(instruction, Mapping):
        raise ReviewGateInputError("Principal review instruction must be an object")
    text = instruction.get("text")
    if (not isinstance(text, str) or not text
            or hashlib.sha256(text.encode("utf-8")).hexdigest() != configured.get("instruction_sha256")
            or instruction.get("sha256") != configured.get("instruction_sha256")
            or recorded.get("effective_at") != configured.get("effective_at")):
        raise ReviewGateInputError("Principal review instruction binding is invalid")
    try:
        effective = datetime.fromisoformat(configured["effective_at"].replace("Z", "+00:00"))
        if effective.tzinfo is None:
            raise ValueError("timezone required")
    except (KeyError, TypeError, ValueError) as exc:
        raise ReviewGateInputError("Principal review effective time is invalid") from exc
    return configured


def resolve_required_code_owner(repository: str, *, policy: Mapping[str, Any] | None = None, codeowners: str | None = None, pr_author: str | None = None) -> str:
    """Bind the trusted repository's three roles without creating native approval.

    Unknown repositories or a policy/CODEOWNERS disagreement fail closed.
    Human authority, execution identity and durable storage are distinct roles.
    A delegated reviewer is selected only for a principal-authored PR and only
    from an active, exact-byte-bound Owner record. No native approval is inferred.
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
    try:
        try:
            from tools.qikvrt_workflow_executor import load_repository_roles, ExecutorBlock
        except ModuleNotFoundError:
            from qikvrt_workflow_executor import load_repository_roles, ExecutorBlock
        if repository != load_repository_roles(root)["AUTHORITY"]:
            raise ReviewGateInputError("governance and canonical Authority policies disagree")
    except ExecutorBlock as exc:
        raise ReviewGateInputError(str(exc)) from exc
    owner = _login(human.get("github_login"), "Mesh Authority human login")
    if human.get("type") != "NATURAL_PERSON" or owner.casefold().endswith("[bot]"):
        raise ReviewGateInputError("native Code Owner must be a human principal")
    if executor.get("may_submit_native_approve") is not False or memory.get("may_submit_native_approve") is not False:
        raise ReviewGateInputError("executor and repository cannot supply native human approval")
    validate_review_acceptance_policy(policy, root)
    delegate = None
    configured = authority.get("code_owner_review_delegation")
    if configured is not None:
        if not isinstance(configured, Mapping):
            raise ReviewGateInputError("Code Owner review delegation must be an object")
        source = "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
        if configured.get("source") != source or policy.get("owner_delegation") != source:
            raise ReviewGateInputError("Code Owner review delegation has an unbound source")
        try:
            original = (root / source).read_bytes()
            record = json.loads(original)
        except (OSError, UnicodeError, ValueError) as exc:
            raise ReviewGateInputError("Code Owner review delegation source is unavailable or invalid") from exc
        if hashlib.sha256(original).hexdigest() != configured.get("source_sha256"):
            raise ReviewGateInputError("Code Owner review delegation source bytes do not match")
        if not isinstance(record, Mapping) or record.get("state") != "ACTIVE" or not isinstance(record.get("repositories"), list) or repository not in record["repositories"]:
            raise ReviewGateInputError("Code Owner review delegation is not active for this repository")
        record_owner = record.get("owner")
        if not isinstance(record_owner, Mapping) or record_owner.get("name") != human.get("name") or record_owner.get("type") != "NATURAL_PERSON":
            raise ReviewGateInputError("Code Owner review delegation does not retain the human principal")
        recorded = record.get("code_owner_review_delegation")
        if not isinstance(recorded, Mapping):
            raise ReviewGateInputError("Code Owner review delegation is not recorded by the Owner")
        obligations = {
            "principal_login": owner,
            "scope": "REPOSITORY_CODE_REVIEW_ONLY",
            "state": "ACTIVE",
            "native_approval_required": True,
            "owner_final_authority_retained": True,
            "self_approval_allowed": False,
            "automated_approval_can_substitute": False,
        }
        for field, expected in obligations.items():
            configured_matches = configured.get(field) is expected if isinstance(expected, bool) else configured.get(field) == expected
            recorded_matches = recorded.get(field) is expected if isinstance(expected, bool) else recorded.get(field) == expected
            if not configured_matches or not recorded_matches:
                raise ReviewGateInputError(f"Code Owner review delegation violates {field}")
        delegate = _login(configured.get("delegate_login"), "delegated Code Owner reviewer")
        if recorded.get("delegate_login") != delegate or delegate.casefold() == owner.casefold() or delegate.casefold().endswith("[bot]"):
            raise ReviewGateInputError("delegated Code Owner reviewer must be a distinct non-bot identity")
    if codeowners is None:
        codeowners = (root / ".github/CODEOWNERS").read_text(encoding="utf-8")
    entries = [line.split("#", 1)[0].split() for line in codeowners.splitlines() if line.split("#", 1)[0].strip()]
    accounts = ["@" + owner] + (["@" + delegate] if delegate else [])
    if not entries or entries[0] != ["*", *accounts] or any(entry[1:] != accounts for entry in entries):
        raise ReviewGateInputError("CODEOWNERS disagrees with current Mesh Authority human")
    if pr_author is not None and _login(pr_author, "pull request author").casefold() == owner.casefold() and delegate:
        return delegate
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


def _block(*, gate_state: str, blocker: str | None, detail: str, pr_number: Any, head_sha: str | None, required_code_owner: str) -> dict[str, Any]:
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


def code_owner_review_policy_is_enforced(rules: Sequence[Mapping[str, Any]]) -> bool:
    """Observe either native independent review or the trusted Principal gate.

    This checks actual rules, not a green run or the mere policy declaration.
    The Principal path requires the dedicated status from GitHub Actions and
    strict freshness; it does not require an additional independent approval.
    """
    if (not isinstance(rules, Sequence) or isinstance(rules, (str, bytes))
            or not all(isinstance(rule, Mapping) for rule in rules)):
        return False
    if native_code_owner_rule_is_enforced(rules):
        return True
    root = pathlib.Path(__file__).resolve().parents[1]
    policy = json.loads((root / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text(encoding="utf-8"))
    if validate_review_acceptance_policy(policy, root) is None:
        return False
    for rule in rules:
        parameters = rule.get("parameters")
        if rule.get("type") != "required_status_checks" or not isinstance(parameters, Mapping):
            continue
        checks = parameters.get("required_status_checks")
        if parameters.get("strict_required_status_checks_policy") is not True or not isinstance(checks, list):
            continue
        if any(isinstance(check, Mapping) and check.get("context") == GOVERNANCE_STATUS_CONTEXT
               and type(check.get("integration_id")) is int and check["integration_id"] == 15368 for check in checks):
            return True
    return False


def _evaluate_principal_review(pr: Mapping[str, Any], reviews: Sequence[Mapping[str, Any]], configured: Mapping[str, Any], *, native_enforcement: bool) -> dict[str, Any]:
    """Read an actual Owner-account COMMENTED review, never a bot disposition.

    The explicit human decision authorizes its recording through the connected
    account. That account event is not biometric proof or an independent review.
    A commit SHA binds the immutable Git tree; no tree lookup is inferred here.
    """
    head_sha, number = pr["head"]["sha"], pr["number"]
    owner = configured["principal_login"]
    owner_reviews = [item for item in reviews if isinstance(item.get("user"), Mapping)
                     and str(item["user"].get("login", "")).casefold() == owner.casefold()]
    marked = lambda item: isinstance(item.get("body"), str) and item["body"].startswith(PRINCIPAL_REVIEW_MARKER)
    exact = [item for item in owner_reviews if item.get("commit_id") == head_sha
             and (marked(item) or item.get("state") in {"CHANGES_REQUESTED", "DISMISSED"})]

    def result(state: str, blocker: str | None, detail: str, review: Mapping[str, Any] | None = None) -> dict[str, Any]:
        value = _block(gate_state=state, blocker=blocker, detail=detail, pr_number=number,
                       head_sha=head_sha, required_code_owner=owner)
        value.update(review_basis="OWNER_PRINCIPAL_REVIEW", independent_native_approval=False,
                     native_code_owner_rule_enforced=native_enforcement,
                     platform_review_state=review.get("state") if review else None,
                     review_id=review.get("id") if review else None)
        return value

    if not exact:
        stale = any(marked(item) and item.get("commit_id") != head_sha for item in owner_reviews)
        return result(PENDING, "OWNER_PRINCIPAL_REVIEW_STALE" if stale else "OWNER_PRINCIPAL_REVIEW_MISSING",
                      "record the already authorized Principal review on the current PR head; no renewed human permission is required")
    latest = max(exact, key=_review_sort_key)
    actor = latest["user"]
    if (actor.get("type") != "User" or isinstance(actor.get("id"), bool)
            or actor.get("id") != configured["principal_github_id"]):
        return result(FAILURE, "OWNER_PRINCIPAL_REVIEW_IDENTITY_MISMATCH", "review is not from the bound Principal account", latest)
    if latest.get("state") == "CHANGES_REQUESTED":
        return result(FAILURE, "OWNER_PRINCIPAL_REVIEW_CHANGES_REQUESTED", "the Principal requested changes on this head", latest)
    if latest.get("state") == "DISMISSED":
        return result(PENDING, "OWNER_PRINCIPAL_REVIEW_DISMISSED", "the Principal review was dismissed", latest)
    if latest.get("state") != configured["native_review_state"]:
        return result(FAILURE, "OWNER_PRINCIPAL_REVIEW_STATE_INVALID", "Principal review must retain the actual COMMENTED platform state", latest)
    try:
        match = re.fullmatch(re.escape(PRINCIPAL_REVIEW_MARKER) + r"\s*```json\s*(\{.*\})\s*```\s*", latest["body"], re.DOTALL)
        if match is None:
            raise ValueError("structured Principal decision missing")
        def unique_object(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("duplicate Principal decision field")
                value[key] = item
            return value
        payload = json.loads(match.group(1), object_pairs_hook=unique_object)
        base = pr.get("base") or {}
        repository = (base.get("repo") or {}).get("full_name")
        expected = {"schema": PRINCIPAL_REVIEW_SCHEMA, "repository": repository,
                    "pull_request": number, "head_sha": head_sha,
                    "base_sha": _sha(base.get("sha"), "Principal review base.sha"),
                    "owner_record_sha256": configured["source_sha256"],
                    "instruction_sha256": configured["instruction_sha256"]}
        if not repository or isinstance(number, bool) or not isinstance(number, int) or number <= 0:
            raise ValueError("Principal review subject missing")
        if any(type(payload.get(field)) is not type(expected_value) or payload[field] != expected_value
               for field, expected_value in expected.items()):
            raise ValueError("Principal decision does not match its current subject or Owner instruction")
        submitted = datetime.fromisoformat(latest["submitted_at"].replace("Z", "+00:00"))
        effective = datetime.fromisoformat(configured["effective_at"].replace("Z", "+00:00"))
        if (submitted.tzinfo is None or submitted < effective or isinstance(latest.get("id"), bool)
                or not isinstance(latest.get("id"), int) or latest["id"] <= 0):
            raise ValueError("Principal review submission is not bound to the effective decision")
        if payload.get("decision") not in {"APPROVE", "REVOKE"}:
            raise ValueError("Principal decision must explicitly approve or revoke")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        return result(FAILURE, "OWNER_PRINCIPAL_REVIEW_INVALID", str(exc), latest)
    if payload["decision"] == "REVOKE":
        return result(FAILURE, "OWNER_PRINCIPAL_REVIEW_REVOKED", "the Principal revoked the current-head review", latest)
    return result(SUCCESS, None, "the Principal's explicit approval is the current-head review; GitHub state remains COMMENTED", latest)


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

    repository = ((pr.get("base") or {}).get("repo") or {}).get("full_name")
    principal = None
    if repository is not None:
        resolve_required_code_owner(repository)
        root = pathlib.Path(__file__).resolve().parents[1]
        policy = json.loads((root / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json").read_text(encoding="utf-8"))
        configured = validate_review_acceptance_policy(policy, root)
        if configured is not None:
            principal = _evaluate_principal_review(pr, reviews, configured, native_enforcement=native_code_owner_rule_is_enforced(rules))
            if principal["first_blocker"] not in {"OWNER_PRINCIPAL_REVIEW_MISSING", "OWNER_PRINCIPAL_REVIEW_STALE"}:
                return principal
    if not native_code_owner_rule_is_enforced(rules):
        if principal is not None:
            return principal
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
        "review_basis": "INDEPENDENT_NATIVE_APPROVAL",
        "independent_native_approval": True,
        "native_code_owner_rule_enforced": True,
        "platform_review_state": latest_state,
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
        "acceptance": ("OWNER_PRINCIPAL_REVIEW_SATISFIED" if decision.get("review_basis") == "OWNER_PRINCIPAL_REVIEW" else "NATIVE_GOVERNANCE_SATISFIED") if state == SUCCESS else "BLOCKED",
        "review_basis": decision.get("review_basis"),
        "independent_native_approval": decision.get("independent_native_approval", False),
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
