#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT repository runtime bootloader.

The bootloader reconstructs a new session from repository evidence. It is
standard-library only, performs no network access, and does not modify tracked
files. Runtime installation and task effects remain separate, explicit actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "policy/AI_BOOTSTRAP_KNOWLEDGE_CORPUS_V1.json"
ADAPTATION_POLICY_PATH = ROOT / "policy/HUMAN_MACHINE_INTERFACE_ADAPTATION_V1.json"
ADAPTATION_MATRIX_PATH = ROOT / "state/interface_adaptation/EVALUATION_MATRIX.json"


class BootBlock(RuntimeError):
    """A required repository-runtime gate failed."""


def run_gate(name: str, command: list[str], accepted: set[int] | None = None) -> dict[str, Any]:
    accepted = accepted or {0}
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BootBlock(f"{name}: execution failed: {exc}") from exc
    result = {
        "name": name,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "state": "PASS" if completed.returncode == 0 else "CONTINUE",
    }
    if completed.returncode not in accepted:
        result["state"] = "BLOCK"
        detail = completed.stderr.strip() or completed.stdout.strip() or "no diagnostic"
        raise BootBlock(f"{name}: exit {completed.returncode}: {detail}")
    return result


def git_value(*args: str) -> str:
    gate = run_gate("git " + " ".join(args), ["git", *args])
    return str(gate["stdout"])


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BootBlock(f"{label} is unreadable: {exc}") from exc
    if not isinstance(value, dict):
        raise BootBlock(f"{label} must contain an object")
    return value


def load_context() -> dict[str, Any]:
    return load_json_object(ROOT / "AI_CONTEXT.json", "AI_CONTEXT.json")


def load_bootstrap_corpus() -> dict[str, Any]:
    corpus = load_json_object(CORPUS_PATH, str(CORPUS_PATH.relative_to(ROOT)))
    if corpus.get("schema") != "qikvrt_ai_bootstrap_knowledge_corpus_v1":
        raise BootBlock("bootstrap knowledge corpus schema drift")
    if corpus.get("canonical_entrypoint") != "AI":
        raise BootBlock("bootstrap knowledge corpus must bind canonical /AI")
    artifacts = corpus.get("source_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise BootBlock("bootstrap knowledge corpus lacks source artifacts")
    seen: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise BootBlock("bootstrap knowledge corpus artifact is malformed")
        name = artifact.get("name")
        digest = artifact.get("sha256")
        status = artifact.get("content_status")
        if not isinstance(name, str) or not name or name in seen:
            raise BootBlock("bootstrap knowledge corpus artifact name is invalid or duplicated")
        seen.add(name)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BootBlock(f"bootstrap knowledge corpus SHA-256 is invalid: {name}")
        if status not in {"PARSED", "VISUALLY_INTERPRETED", "UNTRANSCRIBED", "USER_DECLARED_QR_TARGET"}:
            raise BootBlock(f"bootstrap knowledge corpus status is invalid: {name}")
    required_invariants = {
        "REPOSITORY_EVIDENCE_OVERRIDES_CHAT_AND_MODEL_MEMORY",
        "FORMAL_PROOF_IS_NOT_EMPIRICAL_CONFIRMATION",
        "ARTIFICIAL_COGNITION_IS_NOT_AN_AUTOMATIC_TRUTH_MACHINE",
        "HUMAN_AND_AI_CONTRIBUTIONS_REMAIN_SEPARATELY_ATTRIBUTABLE",
    }
    invariants = corpus.get("core_invariants")
    if not isinstance(invariants, list) or not required_invariants.issubset(set(invariants)):
        raise BootBlock("bootstrap knowledge corpus is missing mandatory epistemic invariants")
    audio_policy = corpus.get("audio_policy")
    if not isinstance(audio_policy, dict) or audio_policy.get("untranscribed_audio_may_supply_semantic_claims") is not False:
        raise BootBlock("bootstrap knowledge corpus must fail closed on untranscribed audio")
    return corpus


def load_interface_adaptation() -> tuple[dict[str, Any], dict[str, Any]]:
    policy = load_json_object(
        ADAPTATION_POLICY_PATH, str(ADAPTATION_POLICY_PATH.relative_to(ROOT))
    )
    matrix = load_json_object(
        ADAPTATION_MATRIX_PATH, str(ADAPTATION_MATRIX_PATH.relative_to(ROOT))
    )
    if policy.get("schema") != "qikvrt_human_machine_interface_adaptation_v1":
        raise BootBlock("human-machine interface adaptation policy schema drift")
    if policy.get("reuse_before_create") is not True:
        raise BootBlock("human-machine interface adaptation must enforce REUSE_BEFORE_CREATE")
    if policy.get("adaptation_mode") != "MEASURE_CACHE_RANK_PROPOSE_REVIEW":
        raise BootBlock("human-machine interface adaptation mode drift")
    never_optimize_by = policy.get("never_optimize_by")
    mandatory_prohibitions = {
        "skipping mandatory gates",
        "weakening exact-head binding",
        "dropping provenance",
        "persisting secrets",
        "treating cached output as proof authority",
        "performing external effects without authorization",
    }
    if not isinstance(never_optimize_by, list) or not mandatory_prohibitions.issubset(set(never_optimize_by)):
        raise BootBlock("adaptive optimization is missing mandatory safety prohibitions")
    cache_layers = policy.get("cache_layers")
    if not isinstance(cache_layers, list) or len(cache_layers) < 4:
        raise BootBlock("adaptive optimization cache hierarchy is incomplete")
    cache_ids = {item.get("id") for item in cache_layers if isinstance(item, dict)}
    if cache_ids != {"L0_SESSION", "L1_PERSONAL_WORKING_MEMORY", "L2_RUNTIME_TOOLCHAIN", "L3_DERIVED_KNOWLEDGE"}:
        raise BootBlock("adaptive optimization cache hierarchy drift")
    matrix_contract = policy.get("evaluation_matrix")
    if not isinstance(matrix_contract, dict):
        raise BootBlock("adaptive optimization lacks evaluation matrix contract")
    if matrix_contract.get("path") != str(ADAPTATION_MATRIX_PATH.relative_to(ROOT)):
        raise BootBlock("adaptive optimization evaluation matrix path drift")
    if matrix.get("schema") != "qikvrt_human_machine_interface_evaluation_matrix_v1":
        raise BootBlock("human-machine interface evaluation matrix schema drift")
    selection = matrix.get("selection")
    if not isinstance(selection, dict) or selection.get("quality_regression_allowed") is not False:
        raise BootBlock("evaluation matrix must fail closed on quality regression")
    if selection.get("mandatory_gate_reduction_allowed") is not False:
        raise BootBlock("evaluation matrix must not optimize by reducing mandatory gates")
    return policy, matrix


def load_requested_review_authority(context: dict[str, Any], repository: str) -> dict[str, Any]:
    """Resolve scoped standing authority; neither contact nor approve a reviewer."""
    binding = context.get("human_machine_interface_adaptation", {}).get("requested_review_authority", {})
    delegation_path = "state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
    policy_path = "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
    if (binding.get("delegation"), binding.get("policy")) != (delegation_path, policy_path):
        raise BootBlock("requested-review authority binding missing or changed")
    if not {delegation_path, policy_path}.issubset(context.get("required_read_order", [])):
        raise BootBlock("requested-review authority absent from required read order")
    delegation = load_json_object(ROOT / delegation_path, delegation_path)
    policy = load_json_object(ROOT / policy_path, policy_path)
    if (delegation.get("schema") != "qikvrt_owner_requested_review_and_issue_lifecycle_v1"
            or policy.get("schema") != "qikvrt_requested_review_and_issue_lifecycle_policy_v1"
            or policy.get("owner_delegation") != delegation_path
            or delegation.get("policy") != policy_path):
        raise BootBlock("requested-review delegation/policy binding drift")
    owner = delegation.get("owner", {})
    scopes = delegation.get("authorization_scope", {})
    if not isinstance(owner, dict) or not isinstance(scopes, dict):
        raise BootBlock("requested-review owner/scope malformed")
    established = (delegation.get("state") == "ACTIVE" and policy.get("status") == "ACTIVE"
                   and owner.get("role") == "Product Owner" and owner.get("type") == "NATURAL_PERSON"
                   and repository in delegation.get("repositories", [])
                   and repository in policy.get("repositories", [])
                   and scopes.get("perform_requested_substantive_reviews_without_reinteraction") is True
                   and policy.get("standing_internal_authority", {}).get("substantive_review_execution") is True)
    return {"repository": repository, "delegation_id": delegation.get("delegation_id"),
            "delegation_path": delegation_path, "policy_path": policy_path,
            "delegation_sha256": hashlib.sha256((ROOT / delegation_path).read_bytes()).hexdigest(),
            "policy_sha256": hashlib.sha256((ROOT / policy_path).read_bytes()).hexdigest(),
            "authorization_established": established,
            "scope": "REQUESTED_SUBSTANTIVE_REVIEW_ONLY",
            "independent_account_approval": False, "merge_authorized": False,
            "route": classify_review_route(established)}


def classify_review_route(authorized: bool, admission: str = "UNVERIFIED",
                          permission: str = "UNVERIFIED") -> dict[str, Any]:
    """Classify supplied observations, without inferring an executed effect.

    A task executor must independently bind fresh observations to its exact
    repository/head/principal. This read-only classifier does not attest them.
    """
    if (type(authorized) is not bool or admission not in {"UNVERIFIED", "REJECTED", "RECORDED"}
            or permission not in {"UNVERIFIED", "WRITE", "NONE"}):
        raise BootBlock("invalid requested-review route observation")
    if not authorized:
        state, action = "AUTHORIZATION_NOT_ESTABLISHED", "RESOLVE_SCOPED_OWNER_AUTHORITY"
    elif admission == "REJECTED":
        state = "CONFLICTING_PLATFORM_EVIDENCE" if permission == "WRITE" else "PLATFORM_ADMISSION_REJECTED"
        action = "VERIFY_PRINCIPAL_TARGET_AND_ADMISSION_ROUTE_PRESERVE_OWNER_AUTHORITY"
    elif admission == "RECORDED":
        state, action = "REQUEST_RECORDED_REVIEW_NOT_ESTABLISHED", "VERIFY_EXACT_HEAD_REVIEW_AND_REQUIRED_GATES"
    else:
        state, action = "CAPABILITY_AND_ADMISSION_UNVERIFIED", "VERIFY_CALLABLE_ROUTE_WITHOUT_REASKING_ESTABLISHED_AUTHORITY"
    return {"state": state, "next_action": action, "authorization_established": authorized,
            "admission_observation": admission, "permission_observation": permission,
            "review_accepted": False, "effect_ack_done": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit one JSON document")
    parser.add_argument(
        "--profile",
        default="all",
        choices=("core", "ietf", "formal", "audio", "publication", "all"),
        help="runtime profile checked without installation",
    )
    parser.add_argument("--task", default="", help="task label recorded in the boot report")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "schema": "qikvrt-ai-runtime-boot/1.2",
        "repository_root": str(ROOT),
        "task": args.task,
        "state": "RUNNING",
        "gates": [],
        "lifecycle": [
            "read AI and AI_CONTEXT.json",
            "load personal-origin and contribution-attribution contract",
            "load supplied bootstrap knowledge corpus with epistemic boundaries",
            "load adaptive human-machine interface cache and evaluation contracts",
            "verify repository identity and Git ref",
            "verify handoff and required repository evidence",
            "verify integrity authorities",
            "verify declared tool/cache contracts",
            "check runtime profile without hidden installation",
            "hand control to the authorized task executor using fastest verified reusable path",
            "measure reusable interaction and runtime evidence",
            "persist reviewed improvements through repository changes",
        ],
    }

    try:
        context = load_context()
        corpus = load_bootstrap_corpus()
        adaptation_policy, adaptation_matrix = load_interface_adaptation()
        artifacts = corpus["source_artifacts"]
        untranscribed = [item for item in artifacts if item.get("content_status") == "UNTRANSCRIBED"]
        report["context_id"] = context.get("context_id", "unknown")
        report["knowledge_corpus"] = {
            "corpus_id": corpus.get("corpus_id"),
            "artifact_count": len(artifacts),
            "untranscribed_audio_count": len(untranscribed),
            "untranscribed_audio_semantic_claims_allowed": False,
            "round_trip": corpus.get("round_trip", []),
            "epistemic_partition": corpus.get("epistemic_partition", []),
            "scientific_boundaries": corpus.get("scientific_boundaries", {}),
        }
        report["interface_adaptation"] = {
            "mode": adaptation_policy.get("adaptation_mode"),
            "default_state": adaptation_policy.get("default_state"),
            "cache_layers": [item.get("id") for item in adaptation_policy.get("cache_layers", [])],
            "routing": adaptation_policy.get("adaptive_routing", {}).get("strategy"),
            "matrix_state": adaptation_matrix.get("state"),
            "matrix_rows": len(adaptation_matrix.get("rows", [])),
            "minimum_observations_before_preference": adaptation_policy.get("evaluation_matrix", {}).get("minimum_observations_before_preference"),
        }
        report["repository"] = git_value("config", "--get", "remote.origin.url")
        origin = report["repository"]
        match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?", origin)
        repository = match.group(1) if match else "UNRESOLVED"
        report["requested_review_authority"] = load_requested_review_authority(context, repository)
        report["git_ref"] = git_value("rev-parse", "--abbrev-ref", "HEAD")
        report["git_commit"] = git_value("rev-parse", "HEAD")

        report["gates"].append(
            {
                "name": "bootstrap knowledge corpus",
                "command": ["internal", str(CORPUS_PATH.relative_to(ROOT))],
                "exit_code": 0,
                "stdout": f"artifacts={len(artifacts)} untranscribed_audio={len(untranscribed)}",
                "stderr": "",
                "state": "PASS",
            }
        )
        report["gates"].append(
            {
                "name": "human machine interface adaptation",
                "command": ["internal", str(ADAPTATION_POLICY_PATH.relative_to(ROOT))],
                "exit_code": 0,
                "stdout": f"mode={adaptation_policy.get('adaptation_mode')} matrix_rows={len(adaptation_matrix.get('rows', []))}",
                "stderr": "",
                "state": "PASS",
            }
        )
        report["gates"].append(
            run_gate("AI handoff", [sys.executable, "-B", "tools/ai_handoff.py"])
        )
        report["gates"].append(
            run_gate(
                "repository integrity",
                [sys.executable, "-B", "tools/qikvrt_integrity.py", "verify"],
            )
        )

        cache_verifier = ROOT / "tools/qikvrt_tool_cache.py"
        if cache_verifier.is_file():
            report["gates"].append(
                run_gate(
                    "tool cache coverage",
                    [sys.executable, "-B", str(cache_verifier.relative_to(ROOT)), "verify"],
                )
            )
        else:
            raise BootBlock("tools/qikvrt_tool_cache.py is missing")

        bootstrap = ROOT / "tools/bootstrap-runtime.sh"
        if bootstrap.is_file():
            report["gates"].append(
                run_gate(
                    "runtime profile",
                    ["sh", str(bootstrap.relative_to(ROOT)), "--check-only", "--profile", args.profile],
                    accepted={0, 20},
                )
            )
        else:
            raise BootBlock("tools/bootstrap-runtime.sh is missing")

        has_continue = any(gate["state"] == "CONTINUE" for gate in report["gates"])
        report["state"] = "CONTINUE" if has_continue else "PASS"
        report["next_action"] = (
            "Install explicitly accepted missing runtime components, then rerun the bootloader."
            if has_continue
            else "Execute the authorized task using the fastest previously verified path; record comparable performance evidence and persist only reviewed improvements."
        )
    except BootBlock as exc:
        report["state"] = "BLOCK"
        report["blocker"] = str(exc)
        report["next_action"] = "Repair the named repository gate and rerun the bootloader."

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"AI_RUNTIME_BOOT_STATE={report['state']}")
        print(f"REPOSITORY={report.get('repository', 'unavailable')}")
        print(f"GIT_REF={report.get('git_ref', 'unavailable')}")
        print(f"GIT_COMMIT={report.get('git_commit', 'unavailable')}")
        corpus_report = report.get("knowledge_corpus", {})
        if corpus_report:
            print(f"KNOWLEDGE_CORPUS_ARTIFACTS={corpus_report.get('artifact_count', 0)}")
            print(f"KNOWLEDGE_CORPUS_UNTRANSCRIBED_AUDIO={corpus_report.get('untranscribed_audio_count', 0)}")
        adaptation_report = report.get("interface_adaptation", {})
        if adaptation_report:
            print(f"INTERFACE_ADAPTATION_MODE={adaptation_report.get('mode', 'unavailable')}")
            print(f"INTERFACE_ADAPTATION_MATRIX_ROWS={adaptation_report.get('matrix_rows', 0)}")
            print(f"INTERFACE_ADAPTATION_ROUTING={adaptation_report.get('routing', 'unavailable')}")
        authority = report.get("requested_review_authority", {})
        if authority:
            print(f"REQUESTED_REVIEW_AUTHORIZATION={authority['authorization_established']}")
            print(f"REQUESTED_REVIEW_ROUTE={authority['route']['state']}")
        for gate in report["gates"]:
            print(f"GATE_{gate['name'].upper().replace(' ', '_')}={gate['state']}")
        if "blocker" in report:
            print(f"BLOCKER={report['blocker']}")
        print(f"NEXT_ACTION={report['next_action']}")

    return 0 if report["state"] in {"PASS", "CONTINUE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())