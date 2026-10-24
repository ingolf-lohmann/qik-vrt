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


def load_personal_optimum(context: dict[str, Any]) -> dict[str, Any]:
    """Bind the Owner's longstanding goal without inventing its inception date."""
    binding = context.get("owner_personal_optimum", {})
    policy_name = "policy/OWNER_PERSONAL_OPTIMUM_V1.json"
    human_name = "docs/OWNER_PERSONAL_OPTIMUM.md"
    if binding.get("policy") != policy_name or binding.get("human_contract") != human_name:
        raise BootBlock("personal optimum context binding missing or changed")
    required = context.get("required_read_order", [])
    if not {policy_name, human_name, "policy/PERFECT_OPTIMUM_V1.json"} <= set(required):
        raise BootBlock("personal optimum is disconnected from /AI read order")
    policy = load_json_object(ROOT / policy_name, policy_name)
    if (policy.get("schema") != "qikvrt_owner_personal_optimum_v1"
            or policy.get("owner") != "Ingolf Lohmann"
            or policy.get("epistemic_class") != "PERSONAL_NORMATIVE_GOAL"):
        raise BootBlock("personal optimum owner or evidence class changed")
    statement = policy.get("original_statement", {})
    text = statement.get("text")
    if not isinstance(text, str) or not text:
        raise BootBlock("personal optimum original statement missing")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != statement.get("utf8_sha256") or digest != binding.get("original_statement_sha256"):
        raise BootBlock("personal optimum original statement identity changed")
    chronology = policy.get("chronology", {})
    if (chronology.get("longstanding_personal_optimum") is not True
            or chronology.get("recording_date_is_inception_date") is not False
            or chronology.get("inception_date") is not None):
        raise BootBlock("personal optimum recording date must not invent its origin")
    if policy.get("connection", {}).get("canonical_entrypoint") != "AI":
        raise BootBlock("personal optimum must bind canonical /AI")
    human = ROOT / human_name
    if not human.is_file() or text not in human.read_text(encoding="utf-8"):
        raise BootBlock("personal optimum human original statement missing")
    claims = policy.get("completion_claims", {})
    if any(claims.get(k) is not False for k in (
            "ALL_CLIENTS_ADOPTED", "PERSONAL_OPTIMUM_ACHIEVED", "EFFECT_ACK_DONE")):
        raise BootBlock("personal optimum source must not claim unobserved effects")
    return policy


def load_recovered_sources(context: dict[str, Any]) -> dict[str, Any]:
    """Verify an inactive source catalog without executing any archived source."""
    name = "incoming/goldkelch-recovery-20261024/INDEX.json"
    binding = context.get("recovered_goldkelch_sources", {})
    if binding.get("index") != name or name not in context.get("required_read_order", []):
        raise BootBlock("recovered source catalog disconnected from /AI")
    root = ROOT / Path(name).parent
    index = load_json_object(root / "INDEX.json", name)
    if index.get("schema") != "qikvrt_recovered_source_catalog_v1":
        raise BootBlock("recovered source catalog schema changed")
    if index.get("source", {}).get("archive_sha256") != binding.get("source_archive_sha256"):
        raise BootBlock("recovered source archive identity changed")
    activation = index.get("activation_contract", {})
    if (activation.get("catalog_is_not_execution_authority") is not True
            or any(activation.get(k) is not False for k in (
                "run_archived_source_automatically", "activate_historical_workflows",
                "overwrite_current_authority_files", "claim_live_mesh_from_source_presence"))):
        raise BootBlock("recovered source cannot grant historical execution authority")
    if any(index.get("completion_claims", {}).get(k) is not False for k in (
            "ALL_GOLDKELCH_LIVE_DATA_RECOVERED", "ALL_ARCHIVED_FEATURES_ACTIVE", "EFFECT_ACK_DONE")):
        raise BootBlock("recovered source cannot claim unobserved completeness or effects")
    objects: dict[str, int] = {}
    versions = 0
    for page in index.get("file_pages", []):
        if not isinstance(page, str) or not re.fullmatch(r"files-[0-9]{3}\.json", page):
            raise BootBlock("unsafe recovered source page")
        entries = load_json_object(root / page, page).get("entries", [])
        if not isinstance(entries, list):
            raise BootBlock("malformed recovered source page")
        versions += len(entries)
        for item in entries:
            if item.get("disposition") != "PRESERVED_INACTIVE_SOURCE_NOT_EXECUTED":
                continue
            blob = item.get("source_blob", "")
            if (not re.fullmatch(r"[0-9a-f]{40}", blob)
                    or item.get("object_path") != "objects/" + blob):
                raise BootBlock("unsafe recovered source object binding")
            path = root / "objects" / blob
            if path.is_symlink() or not path.is_file():
                raise BootBlock("recovered source object missing or symlinked")
            data = path.read_bytes()
            observed = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if (observed != blob or hashlib.sha256(data).hexdigest() != item.get("sha256")
                    or len(data) != item.get("bytes")):
                raise BootBlock("recovered source original bytes changed")
            objects[blob] = len(data)
    comparison = index.get("comparison", {})
    if (versions != comparison.get("absent_path_versions")
            or len(objects) != comparison.get("inactive_original_blobs_preserved")
            or sum(objects.values()) != comparison.get("inactive_original_bytes")):
        raise BootBlock("recovered source coverage changed")
    refs = {}
    for page in index.get("ref_pages", []):
        if not isinstance(page, str) or not re.fullmatch(r"refs-[0-9]{3}\.json", page):
            raise BootBlock("unsafe recovered ref page")
        for item in load_json_object(root / page, page).get("refs", []):
            ref, oid = item.get("ref", ""), item.get("object", "")
            if not ref.startswith("refs/") or not re.fullmatch(r"[0-9a-f]{40}", oid) or ref in refs:
                raise BootBlock("malformed or duplicate recovered ref binding")
            refs[ref] = oid
    if len(refs) != index.get("source", {}).get("refs"):
        raise BootBlock("recovered ref coverage changed")
    return {"index": name, "inactive_objects_byte_verified": len(objects),
            "inactive_bytes_verified": sum(objects.values()), "historical_refs_bound": len(refs),
            "archived_source_executed": False, "live_completeness_inferred": False}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit one JSON document")
    parser.add_argument(
        "--profile",
        default="all",
        choices=("core", "ietf", "formal", "audio", "publication", "all", "self-host", "self-host-firefox", "self-host-systemd"),
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
        personal_optimum = load_personal_optimum(context)
        recovered_sources = load_recovered_sources(context)
        corpus = load_bootstrap_corpus()
        adaptation_policy, adaptation_matrix = load_interface_adaptation()
        artifacts = corpus["source_artifacts"]
        untranscribed = [item for item in artifacts if item.get("content_status") == "UNTRANSCRIBED"]
        report["context_id"] = context.get("context_id", "unknown")
        report["recovered_sources"] = recovered_sources
        report["owner_personal_optimum"] = {
            "owner": personal_optimum["owner"],
            "original_statement": personal_optimum["original_statement"],
            "chronology": personal_optimum["chronology"],
            "epistemic_class": personal_optimum["epistemic_class"],
            "source_binding_verified": True,
            "peer_adoption_inferred": False,
        }
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
        for gate in report["gates"]:
            print(f"GATE_{gate['name'].upper().replace(' ', '_')}={gate['state']}")
        if "blocker" in report:
            print(f"BLOCKER={report['blocker']}")
        print(f"NEXT_ACTION={report['next_action']}")

    return 0 if report["state"] in {"PASS", "CONTINUE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
