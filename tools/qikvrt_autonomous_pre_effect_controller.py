#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed wrapper for autonomous repository work before external effects."""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from collections.abc import Sequence
from typing import Any

from tools import qikvrt_autonomous_self_heal as self_heal

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "state/autonomy/AUTONOMOUS_PRE_EFFECT_POLICY_V1.json"
PERSONAL_ORIGIN_POLICY = (
    ROOT / "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json"
)
CANONICAL_UPSTREAM_POLICY = ROOT / "policy/CANONICAL_UPSTREAM_REMOTE_V1.json"
EXPECTED_PRECONDITIONS = [
    "CURRENT_MAIN_REOBSERVED",
    "EXACT_HEAD_BOUND",
    "NO_COMPETING_WRITER",
    "DETERMINISTIC_STATE",
    "REPOSITORY_NATIVE_EVIDENCE",
]
IRREVERSIBLE_EFFECTS = {
    "ZENODO_PUBLICATION",
    "IETF_SUBMISSION",
    "DOI_CREATION",
    "PUBLIC_RELEASE",
    "EXTERNAL_CREDENTIAL_CONSUMPTION",
    "OTHER_NON_REVERSIBLE_EXTERNAL_STATE_CHANGE",
}
PROHIBITED_CLAIMS = {
    "SCIENTIFIC_CONFIRMATION",
    "PHYSICAL_CORRESPONDENCE",
    "PASS",
    "FINAL_PASS",
    "EFFECT_ACK_DONE",
}
REQUIRED_EVIDENCE_PATHS = (
    "AI",
    "AI_CONTEXT.json",
    "policy/AI_PERSONAL_WORKING_MEMORY_ORIGIN_AND_ATTRIBUTION_V1.json",
    "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json",
    "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json",
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
SHA1 = re.compile(r"^[0-9a-f]{40}$")


class PreEffectBlock(RuntimeError):
    pass


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_autonomous_pre_effect_policy_v1":
        raise PreEffectBlock("pre-effect policy schema mismatch")
    if value.get("mission") != "AUTONOMOUS_UNTIL_FIRST_IRREVERSIBLE_EXTERNAL_EFFECT":
        raise PreEffectBlock("pre-effect mission mismatch")
    if value.get("preconditions") != EXPECTED_PRECONDITIONS:
        raise PreEffectBlock("pre-effect preconditions differ")
    if value.get("fail_closed") != {
        "when": "ANY_PRECONDITION_MISSING",
        "state": "HOLD",
        "repair_forbidden": True,
    }:
        raise PreEffectBlock("fail-closed policy differs")
    if set(value.get("first_irreversible_external_effect", [])) != IRREVERSIBLE_EFFECTS:
        raise PreEffectBlock("irreversible-effect boundary differs")
    prohibited = set(value.get("prohibited_autonomous_effects", []))
    if not PROHIBITED_CLAIMS.issubset(prohibited):
        raise PreEffectBlock("epistemic or completion boundary weakened")
    owner = value.get("owner_authorization", {})
    if owner.get("state") != "ACTIVE" or owner.get("role") != "Product Owner":
        raise PreEffectBlock("Product Owner implementation authorization absent")
    self_heal.load_contract()
    self_heal.load_delegation()
    return value


def _canonical_source_remote() -> str:
    try:
        policy = json.loads(PERSONAL_ORIGIN_POLICY.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PreEffectBlock("personal-origin policy cannot be loaded") from exc
    if policy.get("schema") != "qikvrt_ai_personal_working_memory_origin_and_attribution_v1":
        raise PreEffectBlock("personal-origin policy schema mismatch")
    canonical = policy.get("personal_working_memory", {}).get("canonical_source_remote", {})
    expected_name = canonical.get("name")
    expected_url = canonical.get("url")
    if expected_name != "upstream" or not isinstance(expected_url, str):
        raise PreEffectBlock("canonical source remote contract mismatch")

    remotes_result = self_heal.run(("git", "remote"), timeout=60)
    if remotes_result.returncode:
        raise PreEffectBlock("cannot enumerate Git remotes")
    remotes = set(remotes_result.stdout.split())

    candidate = expected_name if expected_name in remotes else "origin"
    if candidate not in remotes:
        raise PreEffectBlock("canonical source remote is absent")
    url_result = self_heal.run(("git", "remote", "get-url", candidate), timeout=60)
    if url_result.returncode or url_result.stdout.strip() != expected_url:
        raise PreEffectBlock("canonical source remote URL mismatch")
    return candidate


def _normalized_repository_url(value: str) -> str:
    value = value.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value


def _role_local_remote_contract() -> dict[str, str]:
    try:
        policy = json.loads(CANONICAL_UPSTREAM_POLICY.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise PreEffectBlock("canonical upstream policy cannot be loaded") from exc
    if (
        policy.get("schema") != "qikvrt_canonical_upstream_remote_v1"
        or policy.get("status") != "NORMATIVE"
    ):
        raise PreEffectBlock("canonical upstream policy contract mismatch")

    candidates: list[dict[str, Any]] = []
    for key, expected_role in (("canonical_upstream", "AUTHORITY"), ("mirror", "MIRROR")):
        value = policy.get(key, {})
        if (
            isinstance(value, dict)
            and value.get("role") == expected_role
            and isinstance(value.get("repository"), str)
            and isinstance(value.get("canonical_https_url"), str)
            and isinstance(value.get("default_branch"), str)
        ):
            candidates.append(value)
    if len(candidates) != 2:
        raise PreEffectBlock("role-local repository contracts are incomplete")

    origin = self_heal.run(("git", "remote", "get-url", "origin"), timeout=60)
    if origin.returncode:
        raise PreEffectBlock("role-local origin remote is absent")
    origin_url = _normalized_repository_url(origin.stdout)

    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    matching = [
        value
        for value in candidates
        if (
            (not repository or value["repository"] == repository)
            and _normalized_repository_url(value["canonical_https_url"]) == origin_url
        )
    ]
    if len(matching) != 1:
        raise PreEffectBlock("role-local origin identity mismatch")
    selected = matching[0]
    return {
        "repository": selected["repository"],
        "remote_name": "origin",
        "remote_url": selected["canonical_https_url"],
        "default_branch": selected["default_branch"],
        "role": selected["role"],
    }


def _role_local_main_revision() -> str | None:
    contract = _role_local_remote_contract()
    ref = f"refs/heads/{contract['default_branch']}"
    result = self_heal.run((
        "git", "ls-remote", "--heads", contract["remote_name"], ref,
    ), timeout=60)
    if result.returncode:
        return None
    fields = result.stdout.split()
    if len(fields) != 2 or not SHA1.fullmatch(fields[0]) or fields[1] != ref:
        return None
    return fields[0]


def _remote_main_revision() -> str | None:
    remote = _canonical_source_remote()
    result = self_heal.run((
        "git", "ls-remote", "--heads", remote, "refs/heads/main",
    ), timeout=60)
    if result.returncode:
        return None
    fields = result.stdout.split()
    if len(fields) != 2 or not SHA1.fullmatch(fields[0]):
        return None
    return fields[0]


def observe_preconditions() -> dict[str, bool]:
    head = self_heal.observed_base_revision()
    remote_main = _role_local_main_revision()
    evidence_present = all((ROOT / path).is_file() for path in REQUIRED_EVIDENCE_PATHS)
    deterministic_state = True
    try:
        load_policy()
    except (OSError, ValueError, json.JSONDecodeError, self_heal.SelfHealBlock, PreEffectBlock):
        deterministic_state = False
    return {
        "CURRENT_MAIN_REOBSERVED": remote_main is not None and remote_main == head,
        "EXACT_HEAD_BOUND": SHA1.fullmatch(head) is not None,
        "NO_COMPETING_WRITER": remote_main is not None and remote_main == head,
        "DETERMINISTIC_STATE": deterministic_state,
        "REPOSITORY_NATIVE_EVIDENCE": evidence_present,
    }


def classify(preconditions: dict[str, bool], requested_effect: str | None) -> str:
    if requested_effect is not None:
        if requested_effect not in IRREVERSIBLE_EFFECTS:
            raise PreEffectBlock("unknown external effect")
        return "REQUIRE_EXACT_PRODUCT_OWNER_AUTHORIZATION"
    if set(preconditions) != set(EXPECTED_PRECONDITIONS):
        raise PreEffectBlock("precondition set differs")
    if not all(preconditions[name] is True for name in EXPECTED_PRECONDITIONS):
        return "HOLD"
    return "AUTONOMOUS_EXECUTION_ALLOWED"


def execute(command: str, requested_effect: str | None = None) -> dict[str, Any]:
    load_policy()
    preconditions = observe_preconditions()
    decision = classify(preconditions, requested_effect)
    if decision != "AUTONOMOUS_EXECUTION_ALLOWED":
        return {
            "schema": "qikvrt_autonomous_pre_effect_result_v1",
            "state": decision,
            "preconditions": preconditions,
            "external_effect": requested_effect or "NONE",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }
    result = self_heal.execute(command == "apply")
    result["schema"] = "qikvrt_autonomous_pre_effect_result_v1"
    result["pre_effect_policy"] = "AUTONOMOUS-PRE-EFFECT-POLICY-V1"
    result["preconditions"] = preconditions
    result["decision"] = decision
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "apply"))
    parser.add_argument("--requested-effect", choices=sorted(IRREVERSIBLE_EFFECTS))
    args = parser.parse_args(argv)
    try:
        result = execute(args.command, args.requested_effect)
    except (OSError, ValueError, json.JSONDecodeError, self_heal.SelfHealBlock, PreEffectBlock) as exc:
        print(json.dumps({
            "state": "HOLD",
            "failure_class": "AUTONOMOUS_PRE_EFFECT_BLOCKED",
            "detail": str(exc),
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
