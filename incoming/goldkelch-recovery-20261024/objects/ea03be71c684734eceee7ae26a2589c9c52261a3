#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repository-native pull-request closure engine.

Reuses the decision core from PR #396, with a stricter reciprocal-closure
execution boundary. Both roles use native merges after enforced native gates;
the legacy FAST_FORWARD_CAS label never enables a ref write. A run attempts at
most one authenticated mutation, reobserves its effect and the full inventory,
and retains a CONTINUE protocol receipt. It never claims reciprocal completion.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from tools.qikvrt_expected_head_promotion import evaluate_closure
from src.qikvrt_effect_ack import (
    ConnectionDecision, EffectAckEngine, EffectAckRequest, RiskLevel,
    ResponsibilityProtocol, verify_protocol_chain,
)

AUTO_READY_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
TECHNICAL_REVIEW_CONTEXT = "QIKVRT requested review execution"


class ClosureBlock(ValueError):
    """Raised for invalid policy or repository observations."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
        raise ClosureBlock(f"{label} is not a lowercase Git SHA-1")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ClosureBlock(f"{label} must be a non-empty string")
    return value


def validate_policy(policy: Mapping[str, Any], repository: str) -> dict[str, Any]:
    if policy.get("schema") != "qikvrt_autonomous_pr_closure_policy_v1":
        raise ClosureBlock("closure policy schema mismatch")
    if policy.get("status") != "ACTIVE":
        raise ClosureBlock("closure policy is not active")
    repos = policy.get("repositories")
    if not isinstance(repos, Mapping) or repository not in repos:
        raise ClosureBlock("repository is not authorized by closure policy")
    repo_policy = repos[repository]
    if not isinstance(repo_policy, Mapping):
        raise ClosureBlock("repository policy must be an object")
    reviewer = _string(policy.get("required_independent_reviewer"), "required_independent_reviewer")
    max_scan = policy.get("max_scan_per_run")
    max_mutations = policy.get("max_mutations_per_run")
    if isinstance(max_scan, bool) or not isinstance(max_scan, int) or not 1 <= max_scan <= 32:
        raise ClosureBlock("max_scan_per_run must be in [1, 32]")
    if type(max_mutations) is not int or max_mutations != 1:
        raise ClosureBlock("max_mutations_per_run must be exactly 1")
    boundaries = policy.get("hard_boundaries", {})
    if any(boundaries.get(k) is not False for k in (
        "predecessor_evidence_transfer", "self_review_counts_as_independent",
        "force_push_main", "force_ref_update", "effect_ack_done_claim")):
        raise ClosureBlock("closure hard boundaries must be explicitly false")
    check = policy.get("required_check")
    if not isinstance(check, Mapping):
        raise ClosureBlock("required_check must be an object")
    _string(check.get("name"), "required_check.name")
    app_id = check.get("integration_id")
    if isinstance(app_id, bool) or not isinstance(app_id, int) or app_id < 1:
        raise ClosureBlock("required_check.integration_id must be positive")
    mode = repo_policy.get("promotion_mode")
    if mode not in {"NATIVE_PR_MERGE", "FAST_FORWARD_CAS"}:
        raise ClosureBlock("unsupported promotion_mode")
    if repo_policy.get("base_branch") != "main":
        raise ClosureBlock("only main-base closure is authorized")
    if repo_policy.get("role_local_head_required") is not True:
        raise ClosureBlock("role-local head requirement may not be disabled")
    return {
        "reviewer": reviewer,
        "max_scan": max_scan,
        "required_check": dict(check),
        "repo": dict(repo_policy),
    }


def exact_head_approval(reviews: Iterable[Mapping[str, Any]], reviewer: str, head_sha: str, author: str) -> bool:
    latest: Mapping[str, Any] | None = None
    for review in reviews:
        if not isinstance(review, Mapping):
            continue
        user = review.get("user")
        login = user.get("login") if isinstance(user, Mapping) else None
        if login != reviewer or login == author:
            continue
        if latest is None or (review.get("submitted_at") or "") > (latest.get("submitted_at") or ""):
            latest = review
    return bool(latest and latest.get("state") == "APPROVED" and latest.get("commit_id") == head_sha)


def required_check_green(check_runs: Iterable[Mapping[str, Any]], name: str, integration_id: int) -> bool:
    matches = []
    for run in check_runs:
        if not isinstance(run, Mapping) or run.get("name") != name:
            continue
        app = run.get("app")
        app_id = app.get("id") if isinstance(app, Mapping) else None
        if app_id == integration_id:
            matches.append(run)
    if not matches:
        return False
    latest = max(matches, key=lambda x: (x.get("completed_at") or x.get("started_at") or "", x.get("id") or 0))
    return latest.get("status") == "completed" and latest.get("conclusion") == "success"


def technical_review_green(statuses: Iterable[Mapping[str, Any]], context: str = TECHNICAL_REVIEW_CONTEXT) -> bool:
    matches = [s for s in statuses if isinstance(s, Mapping) and s.get("context") == context]
    if not matches:
        return False
    latest = max(matches, key=lambda x: (x.get("updated_at") or x.get("created_at") or "", x.get("id") or 0))
    return latest.get("state") == "success"


def classify_pr(pr: Mapping[str, Any], observed: Mapping[str, Any], config: Mapping[str, Any], repository: str) -> dict[str, Any]:
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number < 1:
        raise ClosureBlock("pull request number is invalid")
    if pr.get("state") != "open":
        return {"pr": number, "action": "SKIP_CLOSED"}
    base = pr.get("base")
    head = pr.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        raise ClosureBlock("pull request lacks Git bindings")
    if base.get("ref") != config["repo"]["base_branch"]:
        return {"pr": number, "action": "BLOCK_UNSUPPORTED_BASE"}
    head_repo = head.get("repo")
    if not isinstance(head_repo, Mapping) or head_repo.get("full_name") != repository:
        return {"pr": number, "action": "BLOCK_NON_ROLE_LOCAL_HEAD"}

    head_sha = _sha(head.get("sha"), "pull request head")
    current_main = _sha(observed.get("current_main_sha"), "current main")
    compare_status = observed.get("compare_status")
    changed_files = pr.get("changed_files")
    if changed_files == 0 or compare_status == "identical":
        return {"pr": number, "action": "CLOSE_ALREADY_CONTAINED", "head_sha": head_sha}

    if pr.get("draft") is True:
        author = ((pr.get("user") or {}).get("login") if isinstance(pr.get("user"), Mapping) else None)
        body = pr.get("body") or ""
        head_ref = head.get("ref") or ""
        if (
            author == "github-actions[bot]"
            and isinstance(body, str)
            and AUTO_READY_MARKER in body
            and isinstance(head_ref, str)
            and head_ref.startswith("automation/self-heal-")
        ):
            return {"pr": number, "action": "MARK_READY", "head_sha": head_sha, "node_id": pr.get("node_id")}
        return {"pr": number, "action": "BLOCK_DRAFT_REQUIRES_OWNER"}

    if compare_status != "ahead":
        mergeable_state = pr.get("mergeable_state")
        if pr.get("mergeable") is False or mergeable_state == "dirty":
            return {"pr": number, "action": "BLOCK_REPAIR_REQUIRED", "reason": "MERGE_CONFLICT"}
        return {"pr": number, "action": "UPDATE_BRANCH", "head_sha": head_sha}

    check = config["required_check"]
    if not required_check_green(observed.get("check_runs", []), check["name"], check["integration_id"]):
        return {"pr": number, "action": "WAIT_REQUIRED_CHECK", "head_sha": head_sha}

    author = ((pr.get("user") or {}).get("login") if isinstance(pr.get("user"), Mapping) else "") or ""
    reviewer = config["reviewer"]
    reviews = observed.get("reviews", [])
    approved = exact_head_approval(reviews, reviewer, head_sha, author)
    requested = set(observed.get("requested_reviewers", []))
    if not approved:
        if reviewer not in requested:
            return {"pr": number, "action": "REQUEST_REVIEW", "head_sha": head_sha, "reviewer": reviewer}
        return {"pr": number, "action": "WAIT_INDEPENDENT_REVIEW", "head_sha": head_sha}

    if not technical_review_green(observed.get("statuses", [])):
        return {"pr": number, "action": "WAIT_TECHNICAL_REVIEW", "head_sha": head_sha}

    if base.get("sha") != current_main:
        return {"pr": number, "action": "REOBSERVE_BASE_DRIFT", "head_sha": head_sha}

    return {
        "pr": number,
        "action": "MERGE",
        "head_sha": head_sha,
        "main_sha": current_main,
        "promotion_mode": config["repo"]["promotion_mode"],
    }


def scan_window(
    prs: Sequence[Mapping[str, Any]],
    max_scan: int,
    run_number: Any,
) -> tuple[list[Mapping[str, Any]], int]:
    """Return a deterministic bounded rotating window over the open PR queue."""
    if not prs:
        return [], 0
    try:
        serial = int(run_number or 1)
    except (TypeError, ValueError):
        serial = 1
    serial = max(serial, 1)
    offset = ((serial - 1) * max_scan) % len(prs)
    ordered = list(prs[offset:]) + list(prs[:offset])
    return ordered[:max_scan], offset



def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class GitHubAPI:
    """Authenticated transport capability; JSON snapshots never enable writes.

    A host connector can implement this interface with its own authenticated
    read/probe/mutate operations. Permission observations are ephemeral; neither
    credentials nor cached capability facts are repository authority.
    """
    repository: str
    token: str
    api_url: str = "https://api.github.com"
    mutation_attempted: bool = False

    def repo_path(self, suffix: str) -> str:
        return f"/repos/{self.repository}{suffix}"

    def request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> Any:
        if self.api_url != "https://api.github.com" or not self.token:
            raise ClosureBlock("AUTHENTICATED_TRANSPORT_UNAVAILABLE")
        if not path.startswith(self.repo_path("/")) and not (method == "GET" and path in {"/user", self.repo_path("")}):
            raise ClosureBlock("REPOSITORY_CAPABILITY_SCOPE_MISMATCH")
        req = urllib.request.Request(self.api_url + path, method=method,
                                     data=None if payload is None else canonical(payload))
        req.add_header("Authorization", "Bearer " + self.token)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise ClosureBlock(f"HTTP_{exc.code}:{method}:{path}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ClosureBlock(f"TRANSPORT_UNCERTAIN:{method}:{path}") from exc
        return json.loads(raw) if raw else None

    def probe(self) -> dict[str, Any]:
        principal = self.request("GET", "/user")
        repo = self.request("GET", self.repo_path(""))
        if repo.get("full_name") != self.repository or repo.get("archived") is not False:
            raise ClosureBlock("REPOSITORY_CAPABILITY_SCOPE_MISMATCH")
        return {"repository": self.repository, "principal": _string(principal.get("login"), "principal"),
                "can_write": repo.get("permissions", {}).get("push") is True,
                "operations": ["REQUEST_REVIEW", "UPDATE_BRANCH", "MERGE"],
                "observed_utc": utc_now()}

    def collection(self, suffix: str, member: str | None = None) -> list[dict[str, Any]]:
        rows = []
        for page in range(1, 101):
            value = self.request("GET", self.repo_path(suffix + f"&per_page=100&page={page}"))
            batch = value.get(member) if member and isinstance(value, Mapping) else value
            if not isinstance(batch, list) or not all(isinstance(v, Mapping) for v in batch):
                raise ClosureBlock("INVENTORY_PAGE_INVALID:" + suffix)
            rows.extend(batch)
            if len(batch) < 100:
                if member and value.get("total_count") != len(rows):
                    raise ClosureBlock("INVENTORY_TOTAL_MISMATCH:" + suffix)
                return rows
        raise ClosureBlock("INVENTORY_TRUNCATED:" + suffix)

    def inventory(self) -> dict[str, Any]:
        main = self.request("GET", self.repo_path("/branches/main"))
        head = _sha(main["commit"]["sha"], "main")
        commit = self.request("GET", self.repo_path("/git/commits/" + head))
        branches = self.collection("/branches?")
        prs = self.collection("/pulls?state=open")
        # Include every open PR, even foreign heads/unsupported bases: omitted
        # entries would make the repository-wide census unsound.
        branch_rows = sorted([{"name": b["name"], "sha": _sha(b["commit"]["sha"], "tip")}
                              for b in branches], key=lambda b: b["name"])
        pr_rows = sorted([{"number": p["number"], "head_sha": _sha(p["head"]["sha"], "PR head"),
                           "head_ref": p["head"]["ref"],
                           "head_repository": (p["head"].get("repo") or {}).get("full_name"),
                           "base_ref": p["base"]["ref"], "draft": p["draft"],
                           "created_at": p["created_at"], "updated_at": p["updated_at"]}
                          for p in prs], key=lambda p: (p["created_at"], p["number"]))
        if len({b["name"] for b in branch_rows}) != len(branch_rows):
            raise ClosureBlock("DUPLICATE_BRANCH")
        if len({p["number"] for p in pr_rows}) != len(pr_rows):
            raise ClosureBlock("DUPLICATE_PR")
        if {b["name"]: b["sha"] for b in branch_rows}.get("main") != head:
            raise ClosureBlock("INVENTORY_MAIN_DRIFT")
        if self.request("GET", self.repo_path("/branches/main"))["commit"]["sha"] != head:
            raise ClosureBlock("INVENTORY_MAIN_DRIFT")
        return {"repository": self.repository, "main_sha": head,
                "main_tree": _sha(commit["tree"]["sha"], "main tree"),
                "branches": branch_rows, "pull_requests": pr_rows}

    def stable_inventory(self) -> dict[str, Any]:
        first, second = self.inventory(), self.inventory()
        if first != second:
            raise ClosureBlock("INVENTORY_DRIFT")
        return second

    def inspect(self, number: int, main: str) -> tuple[dict[str, Any], dict[str, Any]]:
        pr = self.request("GET", self.repo_path(f"/pulls/{number}"))
        head = _sha(pr["head"]["sha"], "PR head")
        compare = self.request("GET", self.repo_path(f"/compare/{main}...{head}"))
        if (compare.get("status") != "ahead" or pr.get("draft") is True or
                pr.get("changed_files") == 0 or (pr["head"].get("repo") or {}).get("full_name") != self.repository):
            return pr, {"current_main_sha": main, "compare_status": compare.get("status"),
                        "check_runs": [], "statuses": [], "reviews": [],
                        "requested_reviewers": []}
        runs = self.collection(f"/commits/{head}/check-runs?", "check_runs")
        if any(r.get("head_sha") != head for r in runs):
            raise ClosureBlock("CHECK_HEAD_DRIFT")
        statuses = self.collection(f"/commits/{head}/statuses?")
        reviews = self.collection(f"/pulls/{number}/reviews?")
        return pr, {"current_main_sha": main, "compare_status": compare.get("status"),
                    "check_runs": runs, "statuses": statuses, "reviews": reviews,
                    "requested_reviewers": [r["login"] for r in pr.get("requested_reviewers", [])]}

    def ancestor(self, old: str, new: str) -> bool:
        result = self.request("GET", self.repo_path(f"/compare/{old}...{new}"))
        return result.get("status") in {"ahead", "identical"} and result.get("merge_base_commit", {}).get("sha") == old

    def reviewer_capability(self, reviewer: str) -> None:
        identity = urllib.parse.quote(reviewer, safe="")
        try:
            # Permission summaries alone can disagree with operation eligibility.
            # The membership endpoint must positively admit this exact handle.
            self.request("GET", self.repo_path(f"/collaborators/{identity}"))
            value = self.request("GET", self.repo_path(f"/collaborators/{identity}/permission"))
        except ClosureBlock as exc:
            raise ClosureBlock("REVIEWER_COLLABORATOR_CAPABILITY_UNVERIFIED:" + reviewer + ":" + str(exc)) from exc
        if (value.get("permission") not in {"read", "triage", "write", "maintain", "admin"} or
                value.get("user", {}).get("login") != reviewer):
            raise ClosureBlock("REVIEWER_NOT_REPOSITORY_COLLABORATOR:" + reviewer)

    def protection(self, config: Mapping[str, Any]) -> None:
        # Both roles use native merges. A repo metadata permission does not
        # establish enforced review/check protection or absence of bypasses.
        ruleset_id = config["repo"].get("ruleset_id")
        if type(ruleset_id) is not int:
            raise ClosureBlock("NATIVE_PROTECTION_NOT_BOUND")
        ruleset = self.request("GET", self.repo_path(f"/rulesets/{ruleset_id}"))
        cond = ruleset.get("conditions", {}).get("ref_name", {})
        if (ruleset.get("enforcement") != "active" or ruleset.get("bypass_actors") or
                "refs/heads/main" not in cond.get("include", []) or cond.get("exclude")):
            raise ClosureBlock("NATIVE_PROTECTION_NOT_ENFORCED")
        rules = {r["type"]: r.get("parameters", {}) for r in ruleset.get("rules", [])}
        pr_rule = rules.get("pull_request", {})
        checks = rules.get("required_status_checks", {})
        required = config["required_check"]
        if (pr_rule.get("required_approving_review_count", 0) < 1 or
                pr_rule.get("require_last_push_approval") is not True or
                pr_rule.get("require_code_owner_review") is not True or
                checks.get("strict_required_status_checks_policy") is not True or
                {"context": required["name"], "integration_id": required["integration_id"]}
                not in checks.get("required_status_checks", []) or "non_fast_forward" not in rules):
            raise ClosureBlock("NATIVE_PROTECTION_NOT_ENFORCED")

    def mutate(self, action: Mapping[str, Any]) -> Any:
        if self.mutation_attempted:
            raise ClosureBlock("ONE_EFFECT_BUDGET_EXHAUSTED")
        self.mutation_attempted = True  # before I/O, including ambiguous failure
        number, kind = action["pr"], action["action"]
        if kind == "REQUEST_REVIEW":
            return self.request("POST", self.repo_path(f"/pulls/{number}/requested_reviewers"),
                                {"reviewers": [action["reviewer"]]})
        if kind == "UPDATE_BRANCH":
            return self.request("PUT", self.repo_path(f"/pulls/{number}/update-branch"),
                                {"expected_head_sha": action["head_sha"]})
        if kind == "MERGE":
            return self.request("PUT", self.repo_path(f"/pulls/{number}/merge"),
                                {"sha": action["head_sha"], "merge_method": "merge"})
        raise ClosureBlock("UNSUPPORTED_EFFECT")


def select_step(api: GitHubAPI, inventory: Mapping[str, Any], config: Mapping[str, Any],
                capability: Mapping[str, Any]) -> dict[str, Any]:
    scanned = []
    for summary in inventory["pull_requests"]:
        pr, observed = api.inspect(summary["number"], inventory["main_sha"])
        if pr["head"]["sha"] != summary["head_sha"] or pr.get("state") != "open":
            raise ClosureBlock("INVENTORY_PR_DRIFT")
        decision = classify_pr(pr, observed, config, api.repository)
        kind = decision["action"]
        if kind in {"CLOSE_ALREADY_CONTAINED", "MARK_READY"}:
            # Closing an unmerged PR or a GraphQL mutation without a SHA fence
            # cannot fulfill this native-merge / lossless successor contract.
            decision = {**decision, "action": "BLOCK_NATIVE_MERGE_OR_SHA_FENCE_REQUIRED"}
        elif kind == "UPDATE_BRANCH" and pr.get("mergeable") is not True:
            decision = {**decision, "action": "BLOCK_MERGEABILITY_UNVERIFIED"}
        elif kind == "REQUEST_REVIEW" and config["reviewer"] == (pr.get("user") or {}).get("login"):
            decision = {**decision, "action": "BLOCK_SELF_REVIEW"}
        elif kind == "REQUEST_REVIEW":
            try:
                api.reviewer_capability(config["reviewer"])
            except ClosureBlock as exc:
                decision = {**decision, "action": "BLOCK_REVIEWER_CAPABILITY", "detail": str(exc)}
        elif kind == "MERGE":
            try:
                api.protection(config)
                # Every current exact-head check/status is applicable unless a
                # reviewed profile excludes it. There is no such exclusion here.
                latest_runs = {}
                for run in observed["check_runs"]:
                    key = (run["name"], run.get("app", {}).get("id"))
                    if key not in latest_runs or run["id"] > latest_runs[key]["id"]:
                        latest_runs[key] = run
                if (any(r.get("status") != "completed" or r.get("conclusion") != "success"
                        for r in latest_runs.values()) or
                        any(s.get("state") != "success" for s in latest_statuses(observed["statuses"]))):
                    raise ClosureBlock("APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN")
            except ClosureBlock as exc:
                decision = {**decision, "action": "BLOCK_MERGE_GATE", "detail": str(exc)}
        if decision["action"] in {"REQUEST_REVIEW", "UPDATE_BRANCH", "MERGE"}:
            if decision["action"] not in capability.get("operations", []):
                decision = {**decision, "action": "BLOCK_MUTATION_CAPABILITY", "required_operation": kind}
            else:
                decision.update(main_sha=inventory["main_sha"], promotion_mode="NATIVE_PR_MERGE")
                return {"selected_action": decision, "scanned": scanned + [decision],
                        "selected_observation_sha256": digest({"pr": pr, "observed": observed})}
        scanned.append(decision)
    return {"selected_action": None, "scanned": scanned,
            "first_blocker": scanned[0] if scanned else {"action": "NO_ADMITTED_PR_EFFECT"}}


def latest_statuses(statuses: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    latest = {}
    for row in statuses:
        context = row["context"]
        if context not in latest or (row.get("created_at", ""), row.get("id", 0)) > (latest[context].get("created_at", ""), latest[context].get("id", 0)):
            latest[context] = row
    return list(latest.values())


def verify_post_effect(api: GitHubAPI, before: Mapping[str, Any], after: Mapping[str, Any],
                       action: Mapping[str, Any]) -> dict[str, Any]:
    pr = api.request("GET", api.repo_path(f"/pulls/{action['pr']}"))
    kind = action["action"]
    if kind == "REQUEST_REVIEW":
        if (pr["head"]["sha"] != action["head_sha"] or pr["state"] != "open" or
                action["reviewer"] not in [r["login"] for r in pr.get("requested_reviewers", [])]):
            raise ClosureBlock("REVIEW_REQUEST_READBACK_MISMATCH")
    elif kind == "UPDATE_BRANCH":
        if pr["state"] != "open" or not api.ancestor(action["head_sha"], pr["head"]["sha"]) or not api.ancestor(before["main_sha"], pr["head"]["sha"]):
            raise ClosureBlock("BRANCH_UPDATE_READBACK_MISMATCH")
    elif kind == "MERGE":
        merge_sha = _sha(pr.get("merge_commit_sha"), "native merge")
        commit = api.request("GET", api.repo_path("/git/commits/" + merge_sha))
        parents = [p["sha"] for p in commit.get("parents", [])]
        if (pr.get("merged") is not True or pr["head"]["sha"] != action["head_sha"] or
                len(parents) != 2 or parents[1] != action["head_sha"] or
                not api.ancestor(before["main_sha"], parents[0]) or
                not api.ancestor(merge_sha, after["main_sha"])):
            raise ClosureBlock("NATIVE_MERGE_READBACK_MISMATCH")
    else:
        raise ClosureBlock("UNSUPPORTED_EFFECT")
    branches = {b["name"]: b["sha"] for b in after["branches"]}
    proofs = []
    for row in before["branches"]:
        target = branches.get(row["name"], after["main_sha"])
        if target != row["sha"]:
            if not api.ancestor(row["sha"], target):
                raise ClosureBlock("ORIGINAL_BRANCH_TIP_LOST:" + row["name"])
            proofs.append({"branch": row["name"], "original": row["sha"], "reachable_from": target})
    prs = {p["number"]: p["head_sha"] for p in after["pull_requests"]}
    for row in before["pull_requests"]:
        target = prs.get(row["number"], after["main_sha"])
        if target != row["head_sha"] and not api.ancestor(row["head_sha"], target):
            raise ClosureBlock("ORIGINAL_PR_HEAD_LOST:" + str(row["number"]))
    if kind != "MERGE" and before["main_sha"] != after["main_sha"]:
        raise ClosureBlock("POST_EFFECT_COMPETING_MAIN_WRITER")
    return {"pr": action["pr"], "head_sha": pr["head"]["sha"],
            "merge_commit_sha": pr.get("merge_commit_sha") if kind == "MERGE" else None,
            "original_pr_heads_preserved": len(before["pull_requests"]),
            "original_branch_tips_preserved": len(before["branches"]),
            "changed_ref_ancestry": proofs, "observed_utc": utc_now()}


def protocol(payload: Mapping[str, Any], principal: str, previous=None):
    ref = "sha256:" + digest(payload)
    result = EffectAckEngine().evaluate(EffectAckRequest(
        protocol_root_id="qikvrt:closure-step:" + payload["intent_id"],
        input_id=payload["intent_id"], payload=canonical(payload["intent"]), transport_ack=True,
        origin_checked=True, context_checked=True, semantics_reconstructed=True,
        effect_anticipated=True, risk_classified=True, risk_level=RiskLevel.LOW,
        responsibility_assigned=True, responsibility_owner=principal,
        connection_decision=ConnectionDecision.CONTINUE, policy_allows_release=False,
        evidence_refs=(ref,), required_evidence_refs=(ref,),
        open_questions=("reciprocal execution and public byte readbacks remain unproved",),
    ), previous_protocol=previous)
    if result.state.value != "EFFECT_ACK_CONTINUE":
        raise ClosureBlock("EFFECT_ACK_CHAIN_BLOCKED")
    return result.protocol


def execute(api: GitHubAPI, policy: Mapping[str, Any], *, apply: bool,
            journal_dir: pathlib.Path | None = None,
            closure_snapshot: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Exactly one attempted remote mutation, including uncertain responses.

    The create-only intent journal MUST be retained by the authenticated host.
    Existing intents only permit readback recovery, never a second mutation.
    This function never calls itself or starts another executor.
    """
    receipt: dict[str, Any] = {
        "schema": "qikvrt_reciprocal_closure_step_receipt_v1", "repository": api.repository,
        "started_utc": utc_now(), "state": "BLOCK", "first_blocker": None,
        "selected_action": None, "mutation_attempted": False, "post_effect_verified": False,
        "predecessor_evidence_transfer": False, "reciprocal_effect_verified": False,
        "completion_claims": {"TARGET_REACHED": False, "EFFECT_ACK_DONE": False,
                              "AUTHORITY_MIRROR_EQUALITY": False},
        # The acceptance evaluator has no role in granting this capability.
        "closure_evaluation": evaluate_closure(closure_snapshot or {
            "schema": "qikvrt_reciprocal_devops_closure_snapshot_v1",
            "nodes": [], "evaluated_utc": utc_now(), "max_observation_age_seconds": 300}),
    }
    clock = time.monotonic()
    try:
        config = validate_policy(policy, api.repository)
        capability = api.probe()
        receipt["capability"] = capability
        if capability.get("repository") != api.repository or capability.get("can_write") is not True:
            raise ClosureBlock("REPOSITORY_WRITE_CAPABILITY_UNAVAILABLE")
        before = api.stable_inventory()
        receipt["inventory_before"] = before
        plan = select_step(api, before, config, capability)
        receipt.update(plan)
        action = plan["selected_action"]
        if action is None:
            raise ClosureBlock("NO_ADMITTED_EFFECT:" + str(plan["first_blocker"]))
        receipt["state"] = "STEP_PREPARED"
        if not apply:
            return receipt
        if journal_dir is None:
            raise ClosureBlock("DURABLE_INTENT_JOURNAL_REQUIRED")
        # No snapshot/review/check is carried forward: recapture the complete
        # census and rederive the SAME deterministic action at the final fence.
        fenced_capability = api.probe()
        fenced = api.stable_inventory()
        if fenced != before or fenced_capability.get("principal") != capability["principal"] or fenced_capability.get("can_write") is not True:
            raise ClosureBlock("PRE_EFFECT_INVENTORY_OR_CAPABILITY_DRIFT")
        fresh = select_step(api, fenced, config, fenced_capability)
        if fresh.get("selected_action") != action or fresh.get("selected_observation_sha256") != plan["selected_observation_sha256"]:
            raise ClosureBlock("PRE_EFFECT_GATE_DRIFT")
        if time.monotonic() - clock > 300:
            raise ClosureBlock("PRE_EFFECT_FRESHNESS_BUDGET_EXPIRED")
        intent = {"repository": api.repository, "capability": {k: capability[k] for k in ("repository", "principal")},
                  "inventory_sha256": digest(before), "action": action,
                  "observation_sha256": plan["selected_observation_sha256"], "policy_sha256": digest(policy)}
        intent_id = digest(intent)
        receipt["intent_id"] = intent_id
        journal_dir.mkdir(parents=True, exist_ok=True)
        for pending in journal_dir.glob("*.intent.json"):
            completed = pending.with_name(pending.name.replace(".intent.json", ".receipt.json"))
            if not completed.exists():
                raise ClosureBlock("UNRESOLVED_INTENT_READBACK_ONLY:" + pending.stem)
            completion = json.loads(completed.read_text(encoding="utf-8"))
            if (completion.get("post_effect_verified") is not True or
                    completion.get("intent_id") != pending.name.removesuffix(".intent.json") or
                    completion.get("receipt_sha256") != digest({k: v for k, v in completion.items() if k != "receipt_sha256"})):
                raise ClosureBlock("UNVERIFIED_JOURNAL_COMPLETION:" + pending.stem)
        journal = journal_dir / (intent_id + ".intent.json")
        pre_payload = {"intent_id": intent_id, "phase": "pre-effect", "intent": intent}
        pre_protocol = protocol(pre_payload, capability["principal"])
        try:
            with journal.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps({"intent": intent, "inventory_before": before,
                                         "pre_payload": pre_payload, "pre_protocol": pre_protocol.to_dict(),
                                         "state": "PREPARED_DO_NOT_RETRY"}, sort_keys=True))
                stream.flush(); os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise ClosureBlock("INTENT_ALREADY_RECORDED_READBACK_ONLY:" + intent_id) from exc
        directory_fd = os.open(journal_dir, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        if (api.request("GET", api.repo_path("/branches/main"))["commit"]["sha"] != before["main_sha"] or
                api.request("GET", api.repo_path(f"/pulls/{action['pr']}"))["head"]["sha"] != action["head_sha"]):
            raise ClosureBlock("IMMEDIATE_PRE_EFFECT_HEAD_OR_MAIN_DRIFT")
        receipt["protocol_payloads"] = [pre_payload]
        receipt["effect_ack_chain"] = [pre_protocol.to_dict()]
        receipt["mutation_attempted"] = True
        try:
            receipt["transport_result"] = api.mutate(action)
        except (ClosureBlock, OSError) as exc:
            receipt["transport_uncertainty"] = str(exc)
        # Always observe after uncertain I/O. Never issue a blind retry.
        after = api.stable_inventory()
        receipt["inventory_after"] = after
        readback = verify_post_effect(api, before, after, action)
        receipt["post_effect_readback"] = readback
        post_payload = {"intent_id": intent_id, "phase": "post-effect",
                        "intent": intent,
                        "before_sha256": digest(before), "after_sha256": digest(after),
                        "action": action, "readback": readback}
        post_protocol = protocol(post_payload, capability["principal"], pre_protocol)
        verify_protocol_chain([pre_protocol, post_protocol])
        receipt["protocol_payloads"].append(post_payload)
        receipt["effect_ack_chain"].append(post_protocol.to_dict())
        receipt.update(state="STEP_EFFECT_VERIFIED_CONTINUE", post_effect_verified=True, first_blocker=None)
    except (ClosureBlock, OSError, KeyError, TypeError, ValueError) as exc:
        receipt.update(state="BLOCK", first_blocker=str(exc))
    receipt["finished_utc"] = utc_now()
    receipt["receipt_sha256"] = digest(receipt)
    if receipt["post_effect_verified"] and journal_dir is not None:
        with (journal_dir / (receipt["intent_id"] + ".receipt.json")).open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, sort_keys=True)); stream.flush(); os.fsync(stream.fileno())
    return receipt



def recover(api: GitHubAPI, journal: pathlib.Path) -> dict[str, Any]:
    """Readback-only recovery of an uncertain, exact-bound intent."""
    saved = json.loads(journal.read_text(encoding="utf-8"))
    intent = saved["intent"]
    intent_id = digest(intent)
    if journal.name != intent_id + ".intent.json" or intent["repository"] != api.repository:
        raise ClosureBlock("RECOVERY_INTENT_BINDING_MISMATCH")
    capability = api.probe()
    if capability["principal"] != intent["capability"]["principal"]:
        raise ClosureBlock("RECOVERY_PRINCIPAL_MISMATCH")
    pre = ResponsibilityProtocol.from_dict(saved["pre_protocol"])
    if (pre.input_hash != "sha256:" + digest(intent) or
            saved["pre_payload"] != {"intent_id": intent_id, "phase": "pre-effect", "intent": intent} or
            digest(saved["inventory_before"]) != intent["inventory_sha256"]):
        raise ClosureBlock("RECOVERY_EVIDENCE_BINDING_MISMATCH")
    after = api.stable_inventory()
    readback = verify_post_effect(api, saved["inventory_before"], after, intent["action"])
    payload = {"intent_id": intent_id, "phase": "post-effect",
               "intent": intent,
               "before_sha256": intent["inventory_sha256"], "after_sha256": digest(after),
               "action": intent["action"], "readback": readback}
    post = protocol(payload, capability["principal"], pre)
    verify_protocol_chain([pre, post])
    receipt = {"schema": "qikvrt_reciprocal_closure_step_receipt_v1", "repository": api.repository,
               "state": "STEP_EFFECT_VERIFIED_CONTINUE", "intent_id": intent_id,
               "recovery_readback_only": True, "mutation_attempted": False,
               "post_effect_verified": True, "inventory_before": saved["inventory_before"],
               "inventory_after": after, "selected_action": intent["action"],
               "protocol_payloads": [saved["pre_payload"], payload],
               "effect_ack_chain": [pre.to_dict(), post.to_dict()],
               "completion_claims": {"TARGET_REACHED": False, "EFFECT_ACK_DONE": False},
               "predecessor_evidence_transfer": False, "reciprocal_effect_verified": False}
    receipt["receipt_sha256"] = digest(receipt)
    target = journal.with_name(journal.name.replace(".intent.json", ".receipt.json"))
    if not target.exists():
        with target.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(receipt, sort_keys=True)); stream.flush(); os.fsync(stream.fileno())
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate-policy", "run", "recover"))
    parser.add_argument("--policy", default="state/autonomy/AUTONOMOUS_PR_CLOSURE_POLICY_V1.json")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--journal-dir", default=".qikvrt/evidence/pr-closure-intents")
    parser.add_argument("--closure-input")
    parser.add_argument("--intent")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        policy = json.loads(pathlib.Path(args.policy).read_text(encoding="utf-8"))
        if args.command == "validate-policy":
            for repository in ([args.repository] if args.repository else policy["repositories"]):
                validate_policy(policy, repository)
            result = {"state": "VALID"}
        elif args.command == "recover":
            result = recover(GitHubAPI(_string(args.repository, "repository"), os.environ.get("GH_TOKEN", "")),
                             pathlib.Path(_string(args.intent, "intent path")))
        else:
            snapshot = None if not args.closure_input else json.loads(pathlib.Path(args.closure_input).read_text(encoding="utf-8"))
            result = execute(GitHubAPI(_string(args.repository, "repository"), os.environ.get("GH_TOKEN", "")),
                             policy, apply=args.apply, journal_dir=pathlib.Path(args.journal_dir),
                             closure_snapshot=snapshot)
    except (OSError, ValueError, KeyError) as exc:
        result = {"state": "BLOCK", "first_blocker": str(exc), "mutation_attempted": False,
                  "completion_claims": {"TARGET_REACHED": False, "EFFECT_ACK_DONE": False}}
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(rendered, end="")
    if args.output:
        pathlib.Path(args.output).write_text(rendered, encoding="utf-8")
    return 2 if result["state"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
