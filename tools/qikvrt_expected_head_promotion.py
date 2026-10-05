#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for expected-head-bound QIK-VRT promotion.

This module intentionally does not mutate GitHub. It evaluates an exact live
snapshot and returns either PROMOTABLE or the first deterministic blocker.
The GitHub workflow is responsible for reobserving the same head/base again
immediately before changing draft state or merging.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any, Iterable, Mapping, Sequence

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}


class PromotionBlock(ValueError):
    """Raised when a snapshot is structurally invalid rather than merely blocked."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise PromotionBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise PromotionBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PromotionBlock("workflow run_number must be an integer")
    return value


def collapse_latest_runs(runs: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """Return the newest run per workflow name.

    Trusted exact-head proxy execution can legitimately supersede an older
    action_required/zero-job registration on the same commit. Promotion must
    therefore use the newest observed execution for each workflow name rather
    than treating historical registrations as permanently adverse.
    """
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            raise PromotionBlock("workflow run must be an object")
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise PromotionBlock("workflow run name is missing")
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _blocked(snapshot: Mapping[str, Any], failure_class: str, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "BLOCK",
        "first_blocker": failure_class,
        "detail": detail,
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": snapshot.get("expected_head_sha"),
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one promotion candidate against the live fail-closed contract."""
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")

    overlaps = snapshot.get("competing_writer_overlaps", [])
    if not isinstance(overlaps, list):
        raise PromotionBlock("competing_writer_overlaps must be a list")
    if overlaps:
        return _blocked(snapshot, "COMPETING_WRITER_OVERLAP", f"overlapping open writer(s): {overlaps}")

    required = snapshot.get("required_gates")
    if not isinstance(required, list) or not required or not all(
        isinstance(name, str) and name for name in required
    ):
        raise PromotionBlock("required_gates must be a non-empty list of names")
    runs = snapshot.get("workflow_runs")
    if not isinstance(runs, list):
        raise PromotionBlock("workflow_runs must be a list")
    latest = collapse_latest_runs(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_MISSING", f"required workflow is absent: {gate}")
        if run.get("status") != "completed":
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL", f"required workflow is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS_CONCLUSIONS:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN", f"required workflow is not successful: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")

    return {
        "schema": "qikvrt_expected_head_promotion_decision_v1",
        "state": "PROMOTABLE",
        "first_blocker": None,
        "detail": "all exact-head promotion conditions are satisfied",
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": expected_head,
        "current_main_sha": current_main,
        "latest_workflows": {
            name: {
                "run_number": _run_number(run),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
            }
            for name, run in sorted(latest.items())
        },
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
        },
    }


def _load_snapshot(path: str) -> Mapping[str, Any]:
    def unique_object(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise PromotionBlock("duplicate snapshot member: " + key)
            result[key] = item
        return result

    def reject_constant(raw):
        raise PromotionBlock("non-finite snapshot number: " + raw)

    if path == "-":
        value = json.load(sys.stdin, object_pairs_hook=unique_object, parse_constant=reject_constant)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"),
                           object_pairs_hook=unique_object, parse_constant=reject_constant)
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


def evaluate_closure(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Check externally verified closure observations; no effect permission.

    The caller must authenticate and verify every supplied fact at its source.
    This pure core validates bindings and acceptance completeness, not the
    truth of an arbitrary JSON document. A positive result is review readiness.
    """
    result = {
        "schema": "qikvrt_reciprocal_devops_closure_decision_v1",
        "state": "BLOCK", "first_blocker": None, "external_effect": "NONE",
        "ordinary_release": False,
        "completion_claims": {"EFFECT_ACK_DONE": False, "TARGET_REACHED": False},
    }

    def require(condition: bool, failure: str) -> None:
        if not condition:
            raise PromotionBlock(failure)

    def timestamp(raw: Any) -> datetime.datetime:
        require(isinstance(raw, str) and raw.endswith("Z"), "INVALID_UTC_TIME")
        try:
            return datetime.datetime.fromisoformat(raw[:-1] + "+00:00")
        except ValueError as exc:
            raise PromotionBlock("INVALID_UTC_TIME") from exc

    def records(raw: Any, key: str) -> dict[Any, Mapping[str, Any]]:
        require(isinstance(raw, list), "INVENTORY_NOT_A_LIST")
        indexed = {}
        for item in raw:
            require(isinstance(item, Mapping), "INVALID_INVENTORY_RECORD")
            identity = item.get(key)
            require(isinstance(identity, (int, str)) and not isinstance(identity, bool)
                    and bool(identity), "INVALID_INVENTORY_ID")
            require(identity not in indexed, "DUPLICATE_INVENTORY_ID")
            indexed[identity] = item
        return indexed

    try:
        require(isinstance(snapshot, Mapping), "INVALID_CLOSURE_SNAPSHOT")
        require(snapshot.get("schema") == "qikvrt_reciprocal_devops_closure_snapshot_v1",
                "UNSUPPORTED_CLOSURE_VERSION")
        now = timestamp(snapshot.get("evaluated_utc"))
        age = snapshot.get("max_observation_age_seconds")
        require(type(age) is int and 0 < age <= 300, "INVALID_FRESHNESS_BUDGET")
        nodes = records(snapshot.get("nodes"), "repository")
        expected = {"Goldkelch/qik-vrt": "AUTHORITY", "ingolf-lohmann/qik-vrt": "MIRROR"}
        require(set(nodes) == set(expected), "BOTH_NODES_REQUIRED")
        for repository, role in expected.items():
            node = nodes[repository]
            require(node.get("role") == role, "REPOSITORY_ROLE_MISMATCH")
            require(node.get("accessible") is True, "NODE_ACCESS_NOT_ESTABLISHED")
            head = _sha(node.get("main_sha"), "main_sha")
            tree = _sha(node.get("main_tree"), "main_tree")
            require(0 <= (now - timestamp(node.get("observed_utc"))).total_seconds() <= age,
                    "STALE_OR_FUTURE_OBSERVATION")
            require(node.get("inventory_complete") is True, "INVENTORY_INCOMPLETE")
            require(node.get("inventory_stable") is True, "INVENTORY_DRIFT")
            require(node.get("origin_verified") is True, "ORIGIN_NOT_VERIFIED")
            initial = records(node.get("initial_branches"), "name")
            final = records(node.get("final_branches"), "name")
            require("main" in initial, "INITIAL_MAIN_BINDING_MISSING")
            require("main" in final and final["main"].get("sha") == head,
                    "MAIN_REF_BINDING_MISMATCH")
            for branch in list(initial.values()) + list(final.values()):
                _sha(branch.get("sha"), "branch tip")
                require(branch.get("reachable_from_main") is True and
                        branch.get("verified_against_main") == head and
                        branch.get("object_closure_verified") is True,
                        "BRANCH_HISTORY_NOT_RETAINED")
            for pr in records(node.get("initial_pull_requests"), "number").values():
                _sha(pr.get("head_sha"), "original PR head")
                _sha(pr.get("merge_commit_sha"), "PR merge commit")
                require(pr.get("merged") is True and pr.get("head_reachable_from_main") is True
                        and pr.get("merge_reachable_from_main") is True
                        and pr.get("verified_against_main") == head,
                        "PR_NOT_LOSSLESSLY_MERGED")
            require(node.get("final_open_pull_requests") == [], "OPEN_PULL_REQUESTS_REMAIN")
            quality = node.get("quality")
            require(isinstance(quality, Mapping), "QUALITY_PROFILE_MISSING")
            require(quality.get("head_sha") == head and quality.get("tree_sha") == tree,
                    "QUALITY_SUBJECT_DRIFT")
            require(isinstance(quality.get("profile_id"), str) and bool(quality["profile_id"])
                    and type(quality.get("profile_version")) is int and quality["profile_version"] > 0,
                    "QUALITY_PROFILE_UNVERSIONED")
            for check in ("all_applicable_gates_green", "native_code_owner_rule_enforced",
                          "independent_exact_head_approval", "provenance_rights_security_verified",
                          "no_unaccepted_known_defects", "fresh_main_readback"):
                require(quality.get(check) is True, "QUALITY_NOT_ESTABLISHED:" + check)
        witnesses = snapshot.get("reciprocal_witnesses")
        require(isinstance(witnesses, list) and len(witnesses) == 2, "BOTH_DIRECTIONS_REQUIRED")
        seen = set()
        for witness in witnesses:
            require(isinstance(witness, Mapping), "INVALID_DIRECTION_WITNESS")
            source, target = witness.get("source"), witness.get("target")
            require(source in nodes and target in nodes and source != target,
                    "INVALID_DIRECTION")
            require((source, target) not in seen, "DUPLICATE_DIRECTION")
            seen.add((source, target))
            require(witness.get("source_head") == nodes[source]["main_sha"] and
                    witness.get("target_after") == nodes[target]["main_sha"],
                    "DIRECTION_SUBJECT_DRIFT")
            _sha(witness.get("target_before"), "target_before")
            for check in ("authenticated_executor", "accepted_scoped_effect_ack_chain",
                          "post_effect_readback", "lossless_history_verified"):
                require(witness.get(check) is True, "DIRECTION_UNVERIFIED:" + check)
        public = records(snapshot.get("public_evidence"), "kind")
        require(set(public) == {"REPOSITORY", "IETF", "ZENODO"}, "PUBLIC_EVIDENCE_INCOMPLETE")
        for item in public.values():
            require(isinstance(item.get("url"), str) and item["url"].startswith("https://"),
                    "PUBLIC_URL_MISSING")
            digest = item.get("sha256")
            require(isinstance(digest, str) and len(digest) == 64 and
                    all(c in "0123456789abcdef" for c in digest), "PUBLIC_DIGEST_INVALID")
            require(item.get("public_byte_readback_verified") is True,
                    "PUBLIC_BYTE_READBACK_UNVERIFIED")
            if item["kind"] != "IETF":
                require(item.get("subject_heads") == {k: n["main_sha"] for k, n in nodes.items()},
                        "PUBLIC_EVIDENCE_SUBJECT_DRIFT")
            else:
                require(item.get("document") == "draft-lohmann-qikvrt-effect-ack-03",
                        "PROTOCOL_VERSION_MISMATCH")
        result.update(state="CLOSURE_READY_FOR_ACCEPTANCE", first_blocker=None)
    except (PromotionBlock, TypeError, KeyError) as exc:
        result["first_blocker"] = str(exc)
    result["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate", "evaluate-closure"))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        snapshot = _load_snapshot(args.input)
        result = evaluate_closure(snapshot) if args.command == "evaluate-closure" else evaluate_promotion(snapshot)
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": ("qikvrt_reciprocal_devops_closure_decision_v1" if args.command == "evaluate-closure"
                       else "qikvrt_expected_head_promotion_decision_v1"),
            "state": "BLOCK",
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"PROMOTABLE", "CLOSURE_READY_FOR_ACCEPTANCE"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
