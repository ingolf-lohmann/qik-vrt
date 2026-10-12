#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded repository-native QIK-VRT self-healing controller."""
from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
DELEGATION = (
    ROOT
    / "state/authorization/delegations/"
    "OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
)
PROMOTION_CONDITIONS = (
    "CURRENT_BASE_REOBSERVED",
    "HEAD_UNCHANGED",
    "DIFF_ALLOWLISTED",
    "NO_EXTERNAL_EFFECT",
    "ALL_APPLICABLE_GATES_TERMINAL_GREEN",
    "NO_COMPETING_WRITER",
)


class SelfHealBlock(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


def run(command: Sequence[str], timeout: int = 900) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        tuple(command),
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )


def _load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SelfHealBlock(f"{label} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise SelfHealBlock(f"{label} must be a JSON object")
    return value


def _validate_promotion_policy(
    policy: Any,
    *,
    proposal_workflow_may_merge: bool | None,
    standing_delegation: bool | None,
) -> Mapping[str, Any]:
    if not isinstance(policy, Mapping):
        raise SelfHealBlock("promotion policy is absent")
    if policy.get("unconditional_automatic_merge") != "FORBIDDEN":
        raise SelfHealBlock("unconditional automatic merge must remain forbidden")
    if policy.get("expected_head_bound_promotion") != "ALLOWED_ONLY_IF":
        raise SelfHealBlock("expected-head-bound promotion policy differs")
    if policy.get("conditions") != list(PROMOTION_CONDITIONS):
        raise SelfHealBlock("expected-head-bound promotion conditions differ")
    if policy.get("requires_existing_repository_bound_promotion_contract") is not True:
        raise SelfHealBlock("repository-bound promotion contract is required")
    if policy.get("general_auto_merge_authorization") is not False:
        raise SelfHealBlock("general automatic-merge authorization is forbidden")
    if (
        proposal_workflow_may_merge is not None
        and policy.get("proposal_workflow_may_merge")
        is not proposal_workflow_may_merge
    ):
        raise SelfHealBlock("proposal workflow promotion boundary differs")
    if (
        standing_delegation is not None
        and policy.get("standing_delegation") is not standing_delegation
    ):
        raise SelfHealBlock("standing promotion delegation differs")
    return policy


def load_delegation() -> dict[str, Any]:
    value = _load_json(DELEGATION, "autonomous continuation delegation")
    if value.get("schema") != "qikvrt_owner_autonomous_repository_continuation_v2":
        raise SelfHealBlock("delegation schema mismatch")
    if value.get("authorization_scope", {}).get("state") != "ACTIVE":
        raise SelfHealBlock("autonomous continuation delegation is not active")
    _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=None,
        standing_delegation=True,
    )
    if "unconditional_automatic_merge_or_unbound_promotion" not in set(
        value.get("not_authorized", [])
    ):
        raise SelfHealBlock("delegation does not forbid unbound promotion")
    return value


def _validate_handlers(handlers: Any) -> list[dict[str, Any]]:
    if not isinstance(handlers, list) or not handlers:
        raise SelfHealBlock("allowlisted_handlers must be a non-empty list")
    result: list[dict[str, Any]] = []
    failure_classes: set[str] = set()
    for raw in handlers:
        if not isinstance(raw, dict):
            raise SelfHealBlock("each repair handler must be an object")
        failure_class = raw.get("failure_class")
        if not isinstance(failure_class, str) or not failure_class:
            raise SelfHealBlock("repair handler failure_class is missing")
        if failure_class in failure_classes:
            raise SelfHealBlock(f"duplicate repair handler: {failure_class}")
        failure_classes.add(failure_class)
        for key in ("probe", "repair", "mutable_paths"):
            value = raw.get(key)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item for item in value
            ):
                raise SelfHealBlock(f"{failure_class} has invalid {key}")
        signature = raw.get("failure_signature")
        if signature is not None and (
            not isinstance(signature, str) or not signature
        ):
            raise SelfHealBlock(f"{failure_class} has invalid failure_signature")
        result.append(raw)
    order = [handler["failure_class"] for handler in result]
    if (
        "PUBLICATION_OVERVIEW_DRIFT" in order
        and "REPOSITORY_NATIVE_INTEGRITY_STALE" in order
        and order.index("PUBLICATION_OVERVIEW_DRIFT")
        > order.index("REPOSITORY_NATIVE_INTEGRITY_STALE")
    ):
        raise SelfHealBlock("publication overview repair must precede integrity repair")
    return result


def load_contract() -> dict[str, Any]:
    value = _load_json(CONTRACT, "autonomous self-healing contract")
    if value.get("schema") != "qikvrt_autonomous_self_healing_contract_v1":
        raise SelfHealBlock("contract schema mismatch")
    execution_model = value.get("execution_model", {})
    if execution_model.get("promotion") != "expected_head_bound_only":
        raise SelfHealBlock("promotion must remain expected-head-bound")
    contract_policy = _validate_promotion_policy(
        value.get("promotion_policy"),
        proposal_workflow_may_merge=False,
        standing_delegation=None,
    )
    delegation = load_delegation()
    delegation_policy = delegation["promotion_policy"]
    if contract_policy["conditions"] != delegation_policy["conditions"]:
        raise SelfHealBlock("contract and delegation promotion conditions differ")
    if value.get("promotion_gate_order") != [
        "NEW_CURRENT_MAIN_DRAFT",
        "REPOSITORY_NATIVE_INTEGRITY_MATERIALIZATION",
        "EXACT_HEAD_GATES",
        "EXPECTED_HEAD_BOUND_PROMOTION",
    ]:
        raise SelfHealBlock("promotion gate order differs")
    forbidden = set(value.get("forbidden_effects", []))
    if not {
        "unconditional_automatic_merge",
        "unbound_or_stale_head_promotion",
        "force_push",
        "zenodo_mutation",
        "ietf_mutation",
        "deployment",
    }.issubset(forbidden):
        raise SelfHealBlock("forbidden-effect boundary differs")
    candidate = value.get("candidate_contract", {})
    if (
        candidate.get("pull_request_mode") != "draft"
        or candidate.get("deduplicate_by")
        != "base_revision_and_semantic_fingerprint"
        or candidate.get("proposal_workflow_may_merge") is not False
    ):
        raise SelfHealBlock("candidate review boundary differs")
    value["allowlisted_handlers"] = _validate_handlers(
        value.get("allowlisted_handlers")
    )
    return value


def allowed_paths(contract: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for handler in contract["allowlisted_handlers"]:
        result.update(handler["mutable_paths"])
    return result


def changed_paths() -> list[str]:
    result = run(("git", "diff", "--name-only", "--"), timeout=60)
    if result.returncode:
        raise SelfHealBlock(result.stderr.strip() or "git diff failed")
    return sorted(line for line in result.stdout.splitlines() if line)


def semantic_fingerprint(paths: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        payload = (ROOT / path).read_bytes()
        digest.update(path.encode("utf-8") + b"\0")
        digest.update(hashlib.sha256(payload).digest())
    return digest.hexdigest()


def candidate_identity(base_revision: str, fingerprint: str) -> str:
    if (
        len(base_revision) != 40
        or any(character not in "0123456789abcdef" for character in base_revision)
    ):
        raise SelfHealBlock("base revision is not a Git SHA-1")
    if (
        len(fingerprint) != 64
        or any(character not in "0123456789abcdef" for character in fingerprint)
    ):
        raise SelfHealBlock("semantic fingerprint is not a SHA-256")
    payload = (
        base_revision.encode("ascii")
        + b"\0"
        + fingerprint.encode("ascii")
    )
    return hashlib.sha256(payload).hexdigest()


def observed_base_revision() -> str:
    result = run(("git", "rev-parse", "--verify", "HEAD^{commit}"), timeout=60)
    value = result.stdout.strip()
    if result.returncode or len(value) != 40:
        raise SelfHealBlock(result.stderr.strip() or "cannot bind current HEAD")
    return value


def repair_handler(handler: dict[str, Any]) -> dict[str, Any]:
    probe = run(tuple(handler["probe"]))
    if probe.returncode == 0:
        return {"failure_class": handler["failure_class"], "state": "NOOP"}
    combined = probe.stdout + "\n" + probe.stderr
    signature = handler.get("failure_signature")
    if signature and signature not in combined:
        raise SelfHealBlock(
            f"{handler['failure_class']} probe did not emit its exact failure signature"
        )
    if (
        handler["failure_class"] == "ANTICIPATION_PROJECTION_DRIFT"
        and "projection drift:" not in combined
    ):
        raise SelfHealBlock(
            "anticipation failure is not an allowlisted projection drift"
        )
    repair = run(tuple(handler["repair"]))
    if repair.returncode:
        raise SelfHealBlock(
            f"repair failed for {handler['failure_class']}: "
            f"{repair.stderr.strip() or repair.stdout.strip()}"
        )
    return {"failure_class": handler["failure_class"], "state": "REPAIRED"}


def execute(apply: bool) -> dict[str, Any]:
    contract = load_contract()
    initial = run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        timeout=60,
    )
    if initial.returncode or initial.stdout.strip():
        raise SelfHealBlock("controller requires a clean repository")
    base_revision = observed_base_revision()
    boot = run(
        (
            "python3",
            "-B",
            "tools/ai_runtime_bootloader.py",
            "--profile",
            "all",
            "--json",
        )
    )
    if boot.returncode not in (0, 2):
        raise SelfHealBlock("AI runtime bootloader returned an unrecognized state")
    actions: list[dict[str, Any]] = []
    if apply:
        for handler in contract["allowlisted_handlers"]:
            actions.append(repair_handler(handler))
    paths = changed_paths()
    unexpected = sorted(set(paths) - allowed_paths(contract))
    if unexpected:
        raise SelfHealBlock(f"non-allowlisted mutation: {unexpected}")
    fingerprint = semantic_fingerprint(paths) if paths else None
    candidate_id = (
        candidate_identity(base_revision, fingerprint)
        if fingerprint is not None
        else None
    )
    state = "CANDIDATE_READY" if paths else "NOOP"
    return {
        "schema": "qikvrt_autonomous_self_heal_result_v1",
        "state": state,
        "observed_base_revision": base_revision,
        "semantic_fingerprint": fingerprint,
        "candidate_identity": candidate_id,
        "changed_paths": paths,
        "actions": actions,
        "external_effect": "NONE",
        "promotion_policy": {
            "unconditional_automatic_merge": "FORBIDDEN",
            "expected_head_bound_promotion": "ALLOWED_ONLY_IF",
            "conditions": list(PROMOTION_CONDITIONS),
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "FULL_SYNC": False,
            "SYMMETRIC_CANONICALITY": False,
        },
    }


PR_MARKER = "<!-- qikvrt-autonomous-self-heal:enabled -->"
CONTINUATION_MARKER = "<!-- qikvrt-autonomous-pr-continuation -->"
CONTINUATION_REFS = "refs/qikvrt/pr-continuation/"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
ATTEMPT_PATTERN = re.compile(
    re.escape(CONTINUATION_REFS)
    + r"attempts/([1-9][0-9]*)-([1-9][0-9]*)-([0-9a-f]{40})-([0-9a-f]{40})-([1-9][0-9]*)\Z"
)


class GitHubREST:
    """Use only gh api; never gh pr, Git network transport or GraphQL."""

    def __init__(self, repository: str):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise SelfHealBlock("invalid repository identity")
        self.repository = repository
        self.prefix = f"repos/{repository}/"

    def call(self, method: str, path: str, payload: Any = None) -> Any:
        command = ["gh", "api", "--method", method, self.prefix + path]
        if payload is not None:
            command += ["--input", "-"]
        result = subprocess.run(command, input=None if payload is None else json.dumps(payload),
                                text=True, capture_output=True, timeout=120, check=False)
        if result.returncode:
            match = re.search(r"HTTP ([0-9]{3})", result.stderr)
            code = match.group(1) if match else "AMBIGUOUS_TRANSPORT"
            raise SelfHealBlock(f"REST {method} {path}: {code}; no automatic retry")
        return json.loads(result.stdout) if result.stdout.strip() else None

    def pages(self, path: str) -> list[Any]:
        result = subprocess.run(["gh", "api", "--method", "GET", "--paginate", "--slurp",
                                 self.prefix + path], text=True, capture_output=True,
                                timeout=120, check=False)
        if result.returncode:
            raise SelfHealBlock(f"complete REST inventory unavailable: {path}")
        pages = json.loads(result.stdout)
        if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
            raise SelfHealBlock(f"invalid REST page inventory: {path}")
        return [item for page in pages for item in page]

    def ref(self, ref: str) -> Any:
        try:
            return self.call("GET", "git/ref/" + ref.removeprefix("refs/"))
        except SelfHealBlock as exc:
            if ": 404;" in str(exc):
                return None
            raise

    def create_once(self, ref: str, sha: str) -> bool:
        """A rejected/ambiguous acquisition never grants permission to act."""
        existing = self.ref(ref)
        if existing is not None:
            if existing.get("ref") != ref or existing.get("object", {}).get("sha") != sha:
                raise SelfHealBlock("conflicting immutable continuation receipt: " + ref)
            return False
        try:
            self.call("POST", "git/refs", {"ref": ref, "sha": sha})
        except SelfHealBlock:
            # Independent observation is safe. Even a matching ref cannot prove
            # ownership after a timeout or a race; only a confirmed create can.
            self.ref(ref)
            raise
        observed = self.ref(ref)
        if observed is None or observed.get("ref") != ref or observed.get("object", {}).get("sha") != sha:
            raise SelfHealBlock("immutable continuation receipt readback mismatch")
        return True


def eligible_pr(pr: Mapping[str, Any], repository: str) -> bool:
    head, base = pr.get("head") or {}, pr.get("base") or {}
    return (pr.get("state") == "open" and pr.get("draft") is True
            and (head.get("repo") or {}).get("full_name") == repository
            and (base.get("repo") or {}).get("full_name") == repository
            and base.get("ref") == "main" and head.get("ref") != "main"
            and PR_MARKER in (pr.get("body") or "")
            and SHA_PATTERN.fullmatch(head.get("sha") or "") is not None)


def rank_prs(prs: Sequence[Mapping[str, Any]], repository: str,
             attempts: Sequence[Mapping[str, Any]],
             comments: Mapping[int, Sequence[Mapping[str, Any]]]) -> list[dict[str, Any]]:
    """Least recently attempted, then PR number. Heads never reset service age.

    Native workflow concurrency serializes distinct runs. The run claim below
    excludes duplicate attempts of the same run; per-effect claims additionally
    fence duplicate successors and handoffs. Failed and NOOP attempts count.
    """
    last: dict[int, int] = {}
    for ref in attempts:
        match = ATTEMPT_PATTERN.fullmatch(ref.get("ref") or "")
        if match is None or ref.get("object", {}).get("sha") != match.group(3):
            raise SelfHealBlock("malformed immutable attempt inventory")
        turn, number = int(match.group(1)), int(match.group(2))
        last[number] = max(last.get(number, 0), turn)
    result = []
    for pr in prs:
        if not eligible_pr(pr, repository):
            continue
        number = int(pr["number"])
        legacy = [str(comment.get("created_at") or "")
                  for comment in comments.get(number, [])
                  if (comment.get("user") or {}).get("login") == "github-actions[bot]"
                  and (comment.get("body") or "").startswith(CONTINUATION_MARKER + "\n")]
        # Old native comments bootstrap the rotation without changing old PRs.
        rank = (2, last[number], "") if number in last else ((1, 0, max(legacy)) if legacy else (0, 0, ""))
        result.append({"pull_request": number, "head_ref": pr["head"]["ref"],
                       "head_sha": pr["head"]["sha"], "base_ref": "main", "rank": list(rank)})
    return sorted(result, key=lambda item: (tuple(item["rank"]), item["pull_request"]))


def observe_pr_plan(api: GitHubREST) -> dict[str, Any]:
    prs = api.pages("pulls?state=open&per_page=100")
    candidates = [pr for pr in prs if eligible_pr(pr, api.repository)]
    comments = {int(pr["number"]): api.pages(f"issues/{pr['number']}/comments?per_page=100")
                for pr in candidates}
    attempts = api.pages("git/matching-refs/qikvrt/pr-continuation/attempts/")
    turns = api.pages("git/matching-refs/qikvrt/pr-continuation/turns/")
    turn_numbers = []
    for ref in turns:
        match = re.fullmatch(re.escape(CONTINUATION_REFS) + r"turns/([1-9][0-9]*)", ref.get("ref") or "")
        if match is None or SHA_PATTERN.fullmatch(ref.get("object", {}).get("sha") or "") is None:
            raise SelfHealBlock("malformed continuation turn inventory")
        turn_numbers.append(int(match.group(1)))
    main_sha = api.ref("refs/heads/main")["object"]["sha"]
    ranked = rank_prs(prs, api.repository, attempts, comments)
    return {"schema": "qikvrt_pr_continuation_selection_v1", "repository": api.repository,
            "base_sha": main_sha, "strategy": "LEAST_RECENTLY_ATTEMPTED_THEN_PR_NUMBER",
            "ranked": ranked, "selected": ranked[0] if ranked else None,
            "turn_number": max(turn_numbers, default=0) + 1,
            "state": "READ_ONLY_PLAN", "main_activation": False}


def reobserve_selection(api: GitHubREST, plan: Mapping[str, Any], head: str) -> dict[str, Any]:
    selected = plan["selected"]
    pr = api.call("GET", f"pulls/{selected['pull_request']}")
    if (not eligible_pr(pr, api.repository) or pr["head"]["sha"] != head
            or pr["head"]["ref"] != selected["head_ref"]
            or api.ref("refs/heads/main")["object"]["sha"] != plan["base_sha"]):
        raise SelfHealBlock("opt-in, exact head, branch or current main changed")
    return pr


def claim_pr_plan(api: GitHubREST, plan: dict[str, Any], run_id: int) -> dict[str, Any]:
    if run_id < 1:
        raise SelfHealBlock("native run identity is required")
    if plan["selected"] is None:
        return dict(plan, state="NO_ELIGIBLE_PR")
    selected = plan["selected"]
    reobserve_selection(api, plan, selected["head_sha"])
    run_ref = CONTINUATION_REFS + f"runs/{run_id}"
    if not api.create_once(run_ref, plan["base_sha"]):
        return dict(plan, state="DUPLICATE_RUN_NOOP", selected=None)
    if not api.create_once(CONTINUATION_REFS + f"turns/{plan['turn_number']}", selected["head_sha"]):
        return dict(plan, state="CONTENDED_TURN_NOOP", selected=None)
    receipt = (CONTINUATION_REFS + f"attempts/{plan['turn_number']}-{selected['pull_request']}-"
               f"{selected['head_sha']}-{plan['base_sha']}-{run_id}")
    if not api.create_once(receipt, selected["head_sha"]):
        raise SelfHealBlock("attempt receipt already consumed")
    successors = api.pages(f"git/matching-refs/qikvrt/pr-continuation/effects/{selected['pull_request']}/")
    resume = []
    for ref in successors:
        match = re.fullmatch(re.escape(CONTINUATION_REFS) + rf"effects/{selected['pull_request']}/([0-9a-f]{{40}})-([0-9a-f]{{40}})/successor", ref.get("ref") or "")
        if match and match.group(2) == plan["base_sha"] and ref.get("object", {}).get("sha") == selected["head_sha"]:
            resume.append(match.group(1))
    if len(resume) > 1:
        raise SelfHealBlock("ambiguous predecessor handoff binding")
    if resume:
        selected = dict(selected, source_head_sha=resume[0], resume_handoff=True)
    return dict(plan, selected=selected, state="SELECTION_CLAIMED", run_id=run_id, attempt_ref=receipt)


def handoff_pr(api: GitHubREST, plan: Mapping[str, Any], candidate: str) -> dict[str, Any]:
    selected = plan["selected"]
    reobserve_selection(api, plan, candidate)
    number = selected["pull_request"]
    source = selected.get("source_head_sha", selected["head_sha"])
    key = CONTINUATION_REFS + f"effects/{number}/{source}-{plan['base_sha']}/"
    target_url = f"https://github.com/{api.repository}/actions/runs/{plan['run_id']}"
    context = "QIKVRT autonomous exact-head verification"
    statuses = api.pages(f"commits/{candidate}/statuses?per_page=100")
    if not any(status.get("context") == context for status in statuses):
        if not api.create_once(key + "status", candidate):
            raise SelfHealBlock("STATUS_OUTCOME_UNESTABLISHED; no duplicate POST")
        api.call("POST", f"statuses/{candidate}", {"state": "pending", "context": context,
                 "description": "Exact repaired head awaits separate verification", "target_url": target_url})
        if not any(s.get("context") == context for s in api.pages(f"commits/{candidate}/statuses?per_page=100")):
            raise SelfHealBlock("status readback missing")
    accepted = api.ref(key + "dispatch-accepted")
    if accepted is not None and accepted.get("object", {}).get("sha") != candidate:
        raise SelfHealBlock("dispatch acceptance binding differs")
    if accepted is None:
        if not api.create_once(key + "dispatch", candidate):
            raise SelfHealBlock("DISPATCH_OUTCOME_UNESTABLISHED; native readback required, no duplicate POST")
        api.call("POST", "dispatches", {"event_type": "qikvrt_autonomous_exact_head_verify", "client_payload": {
            "repository": api.repository, "pull_request": number, "head_ref": selected["head_ref"],
            "head_sha": candidate, "source_head_sha": source, "base_sha": plan["base_sha"]}})
        api.create_once(key + "dispatch-accepted", candidate)
    marker = f"<!-- qikvrt-pr-continuation-effect:{source}:{candidate} -->"
    comments = api.pages(f"issues/{number}/comments?per_page=100")
    if not any(marker in (c.get("body") or "") for c in comments):
        if not api.create_once(key + "comment", candidate):
            raise SelfHealBlock("COMMENT_OUTCOME_UNESTABLISHED; no duplicate POST")
        body = (CONTINUATION_MARKER + "\n" + marker + "\n"
                "History-preserving successor; independent exact-head verification requested.\n\n"
                f"- previous exact head: `{source}`\n- candidate head: `{candidate}`\n"
                f"- bound main: `{plan['base_sha']}`\n- selection receipt: `{plan['attempt_ref']}`\n\n"
                "Dispatch acceptance is not workflow admission, Code-Owner approval, Main activation, "
                "PASS, FINAL_PASS or EFFECT_ACK_DONE. No publication or deployment is claimed.")
        comment = api.call("POST", f"issues/{number}/comments", {"body": body})
        if api.call("GET", f"issues/comments/{comment['id']}").get("body") != body:
            raise SelfHealBlock("comment exact readback mismatch")
    return {"state": "HANDOFF_SUBMITTED", "candidate_head": candidate,
            "workflow_admission": "UNESTABLISHED", "code_owner_approval": False, "main_activation": False}


def local_git(root: pathlib.Path, *args: str, payload: bytes | None = None) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, input=payload,
                            capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise SelfHealBlock("local Git operation failed: " + " ".join(args[:2]))
    return result.stdout


def import_rest_commit(api: GitHubREST, root: pathlib.Path, sha: str) -> dict[str, Any]:
    value = api.call("GET", f"git/commits/{sha}")
    verification = value.get("verification") or {}
    candidates = []
    if verification.get("payload") and verification.get("signature"):
        headers, message = verification["payload"].split("\n\n", 1)
        for tail in ("", "\n"):
            signature = "\n ".join((verification["signature"].rstrip("\n") + tail).split("\n"))
            candidates.append((headers + "\ngpgsig " + signature + "\n\n" + message).encode())
    prefix = ["tree " + value["tree"]["sha"], *["parent " + p["sha"] for p in value["parents"]]]
    identities = {}
    for role in ("author", "committer"):
        identity = value[role]
        stamp = int(datetime.datetime.fromisoformat(identity["date"].replace("Z", "+00:00")).timestamp())
        identities[role] = f"{role} {identity['name']} <{identity['email']}> {stamp} "
    zones = ["+0000"] + [f"{'+' if offset >= 0 else '-'}{abs(offset)//60:02d}{abs(offset)%60:02d}"
                          for offset in range(-12 * 60, 14 * 60 + 1, 15) if offset]
    messages = [value["message"], value["message"] + "\n"]
    def reconstruct(author_zone: str, committer_zone: str, message: str) -> bytes:
        lines = prefix + [identities['author'] + author_zone, identities['committer'] + committer_zone]
        return ("\n".join(lines) + "\n\n" + message).encode()
    def matches(raw: bytes) -> bool:
        return hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == sha
    raw = next((raw for raw in candidates if matches(raw)), None)
    if raw is None:
        raw = next((raw for zone in zones for message in messages
                    if matches(raw := reconstruct(zone, zone, message))), None)
    if raw is None:
        raw = next((raw for author_zone in zones for committer_zone in zones for message in messages
                    if matches(raw := reconstruct(author_zone, committer_zone, message))), None)
    if raw is None:
        raise SelfHealBlock("raw REST commit cannot be reconstructed exactly; no substitute commit")
    actual = local_git(root, "hash-object", "-w", "-t", "commit", "--stdin", payload=raw).decode().strip()
    if actual != sha:
        raise SelfHealBlock("REST commit object mismatch")
    shallow = root / ".git/shallow"
    entries = set(shallow.read_text().splitlines()) if shallow.exists() else set()
    shallow.write_text("\n".join(sorted(entries | {sha})) + "\n")
    return value


def import_rest_snapshot(api: GitHubREST, root: pathlib.Path, sha: str, checkout: bool = False) -> None:
    """Import exact bytes via REST archive + Git data, with no Git network I/O.

    Archives may apply .gitattributes line-end conversions. Repair any differing
    blob from the raw REST blob endpoint and recompute the entire Git tree.
    This is explicitly a shallow snapshot, never a complete-history backup.
    """
    if SHA_PATTERN.fullmatch(sha) is None:
        raise SelfHealBlock("snapshot SHA is malformed")
    root.mkdir(parents=True, exist_ok=True)
    if not (root / ".git").exists():
        local_git(root, "init", "-b", "main")
    metadata = api.call("GET", f"git/commits/{sha}")
    tree = api.call("GET", f"git/trees/{metadata['tree']['sha']}?recursive=1")
    if tree.get("truncated"):
        raise SelfHealBlock("REST snapshot tree inventory is incomplete")
    with tempfile.TemporaryDirectory(prefix="qikvrt-rest-") as directory:
        stage = pathlib.Path(directory)
        archive = stage / "source.tar.gz"
        with archive.open("wb") as output:
            result = subprocess.run(["gh", "api", "--method", "GET", api.prefix + f"tarball/{sha}"],
                                    stdout=output, stderr=subprocess.PIPE, timeout=900, check=False)
        if result.returncode:
            raise SelfHealBlock("REST archive download failed")
        extracted = stage / "source"
        extracted.mkdir()
        with tarfile.open(archive) as bundle:
            bundle.extractall(extracted, filter="data")
        roots = list(extracted.iterdir())
        if len(roots) != 1 or not roots[0].is_dir():
            raise SelfHealBlock("REST archive root is malformed")
        objects = {}
        for item in tree["tree"]:
            if item["type"] == "tree":
                continue
            if item["type"] != "blob":
                raise SelfHealBlock("non-blob snapshot transport is outside this scope")
            path = roots[0] / item["path"]
            if pathlib.PurePosixPath(item["path"]).is_absolute() or ".." in pathlib.PurePosixPath(item["path"]).parts:
                raise SelfHealBlock("unsafe REST tree path")
            raw = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            identity = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            if identity != item["sha"]:
                cached = subprocess.run(["git", "cat-file", "blob", item["sha"]], cwd=root,
                                        capture_output=True, timeout=120, check=False)
                if cached.returncode == 0:
                    raw = cached.stdout
                else:
                    blob = api.call("GET", "git/blobs/" + item["sha"])
                    raw = base64.b64decode(blob["content"])
            actual = local_git(root, "hash-object", "-w", "--no-filters", "--stdin", payload=raw).decode().strip()
            if actual != item["sha"]:
                raise SelfHealBlock("REST snapshot blob mismatch: " + item["path"])
            objects[item["path"]] = item
        # Build trees without touching the live index or trusting archive modes.
        directories = {""}
        for path in objects:
            parent = pathlib.PurePosixPath(path).parent
            while str(parent) != ".":
                directories.add(str(parent)); parent = parent.parent
        written = {}
        for directory in sorted(directories, key=lambda p: (p.count("/"), len(p)), reverse=True):
            entries = []
            for path, item in objects.items():
                parent = str(pathlib.PurePosixPath(path).parent)
                if ("" if parent == "." else parent) == directory:
                    entries.append((pathlib.PurePosixPath(path).name, item["mode"], "blob", item["sha"]))
            for path, identity in written.items():
                parent = str(pathlib.PurePosixPath(path).parent)
                if ("" if parent == "." else parent) == directory:
                    entries.append((pathlib.PurePosixPath(path).name, "040000", "tree", identity))
            payload = b"".join(f"{mode} {kind} {identity}\t{name}".encode() + b"\0"
                               for name, mode, kind, identity in entries)
            written[directory] = local_git(root, "mktree", "-z", payload=payload).decode().strip()
        if written[""] != metadata["tree"]["sha"]:
            raise SelfHealBlock("REST snapshot full tree mismatch")
    import_rest_commit(api, root, sha)
    if checkout:
        local_git(root, "update-ref", "refs/heads/main", sha)
        local_git(root, "reset", "--hard", sha)


def export_rest_successor(api: GitHubREST, root: pathlib.Path, plan: Mapping[str, Any], candidate: str) -> None:
    source = plan["selected"]["head_sha"]
    if candidate == source:
        raise SelfHealBlock("NOOP cannot create an external successor")
    commits = local_git(root, "rev-list", "--reverse", candidate, "^" + source, "^" + plan["base_sha"]).decode().splitlines()
    if not commits or len(commits) > 2:
        raise SelfHealBlock("successor must contain only the bounded merge and repair commits")
    for sha in commits:
        raw = local_git(root, "cat-file", "commit", sha).decode()
        headers, message = raw.split("\n\n", 1)
        parents, identities = [], {}
        for line in headers.splitlines():
            if line.startswith("parent "): parents.append(line.split()[1])
            elif line.startswith(("author ", "committer ")):
                match = re.fullmatch(r"(author|committer) (.*) <([^<>]*)> ([0-9]+) ([+-][0-9]{4})", line)
                if match is None: raise SelfHealBlock("local successor identity is malformed")
                role, name, email, stamp, zone = match.groups()
                offset = (int(zone[1:3]) * 60 + int(zone[3:])) * (1 if zone[0] == "+" else -1)
                date = datetime.datetime.fromtimestamp(int(stamp), datetime.timezone(datetime.timedelta(minutes=offset)))
                identities[role] = {"name": name, "email": email, "date": date.isoformat()}
        parent_tree = local_git(root, "rev-parse", parents[0] + "^{tree}").decode().strip()
        paths = local_git(root, "diff", "--name-only", "-z", parents[0], sha).split(b"\0")
        entries = []
        for path_bytes in paths:
            if not path_bytes: continue
            path = path_bytes.decode()
            item = local_git(root, "ls-tree", "-z", sha, "--", path).rstrip(b"\0")
            if not item:
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None}); continue
            mode, kind, identity = item.split(b"\t", 1)[0].decode().split()
            blob = local_git(root, "cat-file", "blob", identity)
            remote = api.call("POST", "git/blobs", {"content": base64.b64encode(blob).decode(), "encoding": "base64"})
            if remote.get("sha") != identity: raise SelfHealBlock("outgoing blob readback mismatch")
            entries.append({"path": path, "mode": mode, "type": kind, "sha": identity})
        tree = api.call("POST", "git/trees", {"base_tree": parent_tree, "tree": entries})
        expected_tree = local_git(root, "rev-parse", sha + "^{tree}").decode().strip()
        if tree.get("sha") != expected_tree: raise SelfHealBlock("outgoing tree mismatch")
        created = api.call("POST", "git/commits", {"tree": expected_tree, "parents": parents,
                           "message": message.rstrip("\n"), **identities})
        if created.get("sha") != sha: raise SelfHealBlock("outgoing commit mismatch")
        if api.call("GET", f"git/commits/{sha}").get("tree", {}).get("sha") != expected_tree:
            raise SelfHealBlock("outgoing commit independent readback mismatch")
    reobserve_selection(api, plan, source)
    selected = plan["selected"]
    key = CONTINUATION_REFS + f"effects/{selected['pull_request']}/{source}-{plan['base_sha']}/successor"
    if not api.create_once(key, candidate):
        raise SelfHealBlock("successor already claimed; observe current branch before recovery")
    try:
        api.call("PATCH", "git/refs/heads/" + selected["head_ref"], {"sha": candidate, "force": False})
    except SelfHealBlock:
        # A timeout may follow a successful ref write. Never repeat the PATCH.
        reobserve_selection(api, plan, candidate)
    reobserve_selection(api, plan, candidate)


def pr_cli(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Existing autonomous PR continuation, REST-only")
    parser.add_argument("command", choices=("pr-plan", "pr-select", "pr-checkout", "pr-import", "pr-fixtures", "pr-publish", "pr-resume"))
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--sha")
    parser.add_argument("--selection", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    api = GitHubREST(args.repository or "")
    if args.command == "pr-checkout":
        sha = api.ref("refs/heads/main")["object"]["sha"]
        if args.sha != sha:
            raise SelfHealBlock("trusted controller main binding changed before checkout")
        import_rest_snapshot(api, args.root, sha, checkout=True)
        result = {"state": "EXACT_SHALLOW_REST_CHECKOUT", "head_sha": sha}
    elif args.command == "pr-import":
        import_rest_snapshot(api, args.root, args.sha)
        result = {"state": "EXACT_SHALLOW_REST_IMPORT", "head_sha": args.sha}
    elif args.command == "pr-fixtures":
        # Existing make-test fixture: its manifest chooses this historical
        # source commit for an isolated local worktree. Import the declared
        # source without altering the fixture, its tests or the current index.
        manifest = args.root / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2/publish-request.json"
        if manifest.exists():
            fixture = json.loads(manifest.read_text())["source_head"]
            import_rest_snapshot(api, args.root, fixture)
            result = {"state": "EXACT_HISTORICAL_TEST_FIXTURE_IMPORT", "head_sha": fixture}
        else:
            result = {"state": "NO_HISTORICAL_FIXTURE_REQUIRED"}
    elif args.command in ("pr-plan", "pr-select"):
        result = observe_pr_plan(api)
        if args.command == "pr-select":
            checked = local_git(args.root, "rev-parse", "HEAD").decode().strip()
            if result["base_sha"] != checked: raise SelfHealBlock("checked main is stale")
            result = claim_pr_plan(api, result, int(os.environ["GITHUB_RUN_ID"]))
        if args.output: args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
        if args.command == "pr-select":
            selected = result["selected"]
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                print("found=" + ("true" if selected else "false"), file=output)
                if selected:
                    for key in ("head_ref", "head_sha", "base_ref"):
                        print(key + "=" + str(selected[key]), file=output)
                    print("pr_number=" + str(selected["pull_request"]), file=output)
                    print("base_sha=" + result["base_sha"], file=output)
                    print("resume_handoff=" + ("true" if selected.get("resume_handoff") else "false"), file=output)
    else:
        plan = json.loads(args.selection.read_text())
        if args.command == "pr-publish":
            export_rest_successor(api, args.root, plan, args.sha)
        elif not plan["selected"].get("resume_handoff") or args.sha != plan["selected"]["head_sha"]:
            raise SelfHealBlock("resume requires an existing exact successor binding")
        result = handoff_pr(api, plan, args.sha)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "apply"))
    try:
        if argv and argv[0].startswith("pr-"):
            return pr_cli(argv)
        args = parser.parse_args(argv)
        result = execute(args.command == "apply")
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
        SelfHealBlock,
    ) as exc:
        print(
            json.dumps(
                {
                    "state": "BLOCK",
                    "failure_class": "AUTONOMOUS_SELF_HEAL_BLOCKED",
                    "detail": str(exc),
                },
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
