#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed QIK-VRT epistemic output contract.

Every conforming repository/Mesh node output carries a binding to the canonical
article plus explicit subject, scope, epistemic-status and effect boundaries.
The binding is additive: domain payload schemas remain intact.
"""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/QIKVRT_UNIVERSAL_PROOF_THOUGHT_SCHEMA_V1.json"
ARTICLE_PATH = ROOT / "docs/QIKVRT_UNIVERSAL_PROOF_AND_THOUGHT_SCHEMA_DE.md"

BINDING_KEY = "_qikvrt_epistemic_output"
BINDING_SCHEMA = "qikvrt_epistemic_output_binding_v1"
POLICY_ID = "QIKVRT-UNIVERSAL-PROOF-THOUGHT-SCHEMA-V1"
ARTICLE_SHA256 = "9ee3dd68c64e73ad03b31238d1a23aa73bda855044dd59c63ee12d50535404ea"
ARTICLE_BYTES = 22638
ORIGIN_PATH = ROOT / "docs/ONTOLOGICAL_ORIGIN_OF_DIFFERENCE_DE.md"
ORIGIN_SHA256 = "728dcd263786db9420afd8483e06d8c2d0307aa3d2b2257c13c7ae45ffa6bd1e"
ORIGIN_PROOFS = [
    "QIKVRT.UniversalOntology.determinateReality_requires_difference",
    "QIKVRT.UniversalOntology.noDifference_excludes_determinateReality",
    "QIKVRT.UniversalOntology.noDifference_excludes_information",
]
EXTENSION_POLICY = ROOT / "policy/QIKVRT_PROOF_BOUND_CHANGE_ADMISSION_V1.json"

CLAIM_KINDS = frozenset({
    "DEFINITION",
    "ASSUMPTION",
    "FORMAL_THEOREM",
    "CORRESPONDENCE_POSTULATE",
    "EMPIRICAL_CLAIM",
    "SOURCE_BOUND",
    "INTERPRETATION",
    "NORMATIVE_RULE",
    "OPEN",
    "OUT_OF_SCOPE",
})

EPISTEMIC_STATES = frozenset({
    "FORMAL",
    "EMPIRICAL",
    "SOURCE_BOUND",
    "INTERPRETIVE",
    "NORMATIVE",
    "OPEN",
    "OUT_OF_SCOPE",
    "RUNTIME_EVIDENCE",
})

EFFECT_STATES = frozenset({
    "NONE",
    "CONTINUE",
    "BLOCK",
    "ISOLATE",
    "DONE_WITHIN_DECLARED_SCOPE",
})


class OutputContractError(ValueError):
    """A fail-closed output-contract violation."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_article_identity() -> dict[str, Any]:
    raw = ARTICLE_PATH.read_bytes()
    observed = _sha256_bytes(raw)
    if len(raw) != ARTICLE_BYTES:
        raise OutputContractError(
            f"canonical article byte length mismatch: {len(raw)} != {ARTICLE_BYTES}"
        )
    if observed != ARTICLE_SHA256:
        raise OutputContractError(
            f"canonical article sha256 mismatch: {observed} != {ARTICLE_SHA256}"
        )
    return {
        "path": ARTICLE_PATH.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": observed,
    }


def canonical_origin_identity() -> dict[str, Any]:
    raw = ORIGIN_PATH.read_bytes()
    if _sha256_bytes(raw) != ORIGIN_SHA256:
        raise OutputContractError("ontological-origin source binding mismatch")
    return {"path": ORIGIN_PATH.relative_to(ROOT).as_posix(),
            "bytes": len(raw), "sha256": ORIGIN_SHA256,
            "proof_constants": list(ORIGIN_PROOFS)}


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "qikvrt_universal_proof_thought_schema_v1":
        raise OutputContractError("policy schema mismatch")
    if value.get("policy_id") != POLICY_ID:
        raise OutputContractError("policy id mismatch")
    article = value.get("canonical_article")
    if not isinstance(article, dict):
        raise OutputContractError("policy canonical article binding missing")
    identity = canonical_article_identity()
    for key in ("path", "bytes", "sha256"):
        if article.get(key) != identity[key]:
            raise OutputContractError(f"policy canonical article {key} mismatch")
    if article.get("git_blob_sha1") != hashlib.sha1(
        f"blob {identity['bytes']}\0".encode() + ARTICLE_PATH.read_bytes()
    ).hexdigest():
        raise OutputContractError("policy canonical article Git blob mismatch")
    origin = value.get("ontological_origin_proof", {})
    if origin.get("proof_constants") != ORIGIN_PROOFS:
        raise OutputContractError("policy ontological-origin theorem set mismatch")
    canonical_origin_identity()
    return value


def make_binding(
    *,
    node_id: str,
    repository: str,
    subject: Mapping[str, Any],
    claim_kind: str,
    statement: str,
    assumptions: list[str] | tuple[str, ...] = (),
    definitions: list[str] | tuple[str, ...] = (),
    dependencies: list[str] | tuple[str, ...] = (),
    exclusions: list[str] | tuple[str, ...] = (),
    evidence_refs: list[str] | tuple[str, ...] = (),
    formal_proofs: list[str] | tuple[str, ...] = (),
    empirical_evidence: list[str] | tuple[str, ...] = (),
    source_bindings: list[str] | tuple[str, ...] = (),
    execution_receipts: list[str] | tuple[str, ...] = (),
    readback: list[str] | tuple[str, ...] = (),
    epistemic_state: str = "RUNTIME_EVIDENCE",
    effect_state: str = "NONE",
    transport_ack: bool = False,
    effect_ack_done: bool = False,
    effect_ack: str | None = None,
    new_difference: str = "OUTPUT_MATERIALIZED",
) -> dict[str, Any]:
    load_policy()
    if claim_kind not in CLAIM_KINDS:
        raise OutputContractError(f"unknown claim kind: {claim_kind}")
    if epistemic_state not in EPISTEMIC_STATES:
        raise OutputContractError(f"unknown epistemic state: {epistemic_state}")
    if effect_state not in EFFECT_STATES:
        raise OutputContractError(f"unknown effect state: {effect_state}")
    if type(effect_ack_done) is not bool or type(transport_ack) is not bool:
        raise OutputContractError("effect and transport acknowledgements must be booleans")
    if effect_ack_done and effect_state != "DONE_WITHIN_DECLARED_SCOPE":
        raise OutputContractError("effect_ack_done requires scoped DONE state")
    if effect_state == "DONE_WITHIN_DECLARED_SCOPE" and not effect_ack_done:
        raise OutputContractError("scoped DONE requires effect_ack_done")
    if not isinstance(statement, str) or not statement:
        raise OutputContractError("statement must be non-empty")
    if not isinstance(node_id, str) or not node_id:
        raise OutputContractError("node_id must be non-empty")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise OutputContractError("repository must be owner/name")
    if not isinstance(subject, Mapping) or not subject:
        raise OutputContractError("subject binding must be non-empty")
    article = canonical_article_identity()
    return {
        "schema": BINDING_SCHEMA,
        "policy_id": POLICY_ID,
        "node": {
            "node_id": node_id,
            "repository": repository,
        },
        "subject": copy.deepcopy(dict(subject)),
        "claim": {
            "kind": claim_kind,
            "statement": statement,
        },
        "scope": {
            "assumptions": list(assumptions),
            "definitions": list(definitions),
            "dependencies": list(dependencies),
            "exclusions": list(exclusions),
            "predecessor_evidence_transfer": False,
        },
        "evidence": {
            "refs": list(evidence_refs),
            "formal_proofs": list(formal_proofs),
            "empirical_evidence": list(empirical_evidence),
            "source_bindings": list(source_bindings),
            "execution_receipts": list(execution_receipts),
            "readback": list(readback),
            "cached_output_is_proof_authority": False,
        },
        "epistemic_status": epistemic_state,
        "effect_status": {
            "state": effect_state,
            "transport_ack": bool(transport_ack),
            "effect_ack_done": bool(effect_ack_done),
            "effect_ack": effect_ack,
            "transport_ack_is_effect_ack": False,
        },
        "new_difference": new_difference,
        "article_binding": article,
        "ontological_origin_proof_binding": canonical_origin_identity(),
    }


def bind_output(value: Mapping[str, Any], **binding_kwargs: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    result = copy.deepcopy(dict(value))
    if BINDING_KEY in result:
        # A returning Mesh response is transport of the already bound origin
        # output, not a new semantic claim. Validate and preserve it bytewise.
        validate_output(result)
        if "subject" in binding_kwargs and result[BINDING_KEY]["subject"] != binding_kwargs["subject"]:
            raise OutputContractError("successor subject requires a new output binding")
        return result
    result[BINDING_KEY] = make_binding(**binding_kwargs)
    validate_output(result)
    return result


def strip_output_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return the domain payload without its additive epistemic binding."""
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    result = copy.deepcopy(dict(value))
    result.pop(BINDING_KEY, None)
    return result


def validate_output(value: Mapping[str, Any]) -> dict[str, Any]:
    load_policy()
    if not isinstance(value, Mapping):
        raise OutputContractError("node output must be an object")
    binding = value.get(BINDING_KEY)
    if not isinstance(binding, Mapping):
        raise OutputContractError("mandatory epistemic output binding missing")
    if binding.get("schema") != BINDING_SCHEMA:
        raise OutputContractError("output binding schema mismatch")
    if binding.get("policy_id") != POLICY_ID:
        raise OutputContractError("output policy binding mismatch")
    article = binding.get("article_binding")
    if article != canonical_article_identity():
        raise OutputContractError("output canonical article binding mismatch")
    if binding.get("ontological_origin_proof_binding") != canonical_origin_identity():
        raise OutputContractError("output ontological-origin proof binding mismatch")
    node = binding.get("node")
    if (not isinstance(node, Mapping) or not isinstance(node.get("node_id"), str)
            or not node["node_id"] or not isinstance(node.get("repository"), str)
            or node["repository"].count("/") != 1):
        raise OutputContractError("output node identity missing or invalid")
    if not isinstance(binding.get("subject"), Mapping) or not binding["subject"]:
        raise OutputContractError("output exact subject missing")
    claim = binding.get("claim")
    if (not isinstance(claim, Mapping) or claim.get("kind") not in CLAIM_KINDS
            or not isinstance(claim.get("statement"), str) or not claim["statement"]):
        raise OutputContractError("output claim kind missing or invalid")
    scope = binding.get("scope")
    if not isinstance(scope, Mapping):
        raise OutputContractError("output scope missing")
    if scope.get("predecessor_evidence_transfer") is not False:
        raise OutputContractError("predecessor evidence transfer must be false")
    for key in ("assumptions", "definitions", "dependencies", "exclusions"):
        if not isinstance(scope.get(key), list):
            raise OutputContractError(f"scope.{key} must be a list")
    epistemic_state = binding.get("epistemic_status")
    if epistemic_state not in EPISTEMIC_STATES:
        raise OutputContractError("invalid epistemic status")
    if claim["kind"] == "FORMAL_THEOREM" and epistemic_state != "FORMAL":
        raise OutputContractError("formal theorem cannot be promoted to another evidence class")
    if claim["kind"] == "EMPIRICAL_CLAIM" and epistemic_state != "EMPIRICAL":
        raise OutputContractError("empirical claim requires empirical evidence status")
    evidence = binding.get("evidence")
    if not isinstance(evidence, Mapping) or evidence.get("cached_output_is_proof_authority") is not False:
        raise OutputContractError("output evidence binding missing or promoted")
    for key in ("refs", "formal_proofs", "empirical_evidence", "source_bindings", "execution_receipts", "readback"):
        if not isinstance(evidence.get(key), list) or any(not isinstance(x, str) or not x for x in evidence[key]):
            raise OutputContractError("invalid evidence field: " + key)
    if claim["kind"] == "FORMAL_THEOREM" and not evidence["formal_proofs"]:
        raise OutputContractError("formal theorem requires named proof evidence")
    if claim["kind"] == "EMPIRICAL_CLAIM" and not evidence["empirical_evidence"]:
        raise OutputContractError("empirical claim requires separate empirical evidence")
    effect = binding.get("effect_status")
    if not isinstance(effect, Mapping) or effect.get("state") not in EFFECT_STATES:
        raise OutputContractError("invalid effect status")
    if effect.get("transport_ack_is_effect_ack") is not False:
        raise OutputContractError("TRANSPORT_ACK must remain distinct from EFFECT_ACK")
    done = effect.get("effect_ack_done")
    if type(done) is not bool or type(effect.get("transport_ack")) is not bool:
        raise OutputContractError("invalid acknowledgement type")
    if effect.get("effect_ack") not in (None, "EFFECT_NACK", "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE", "EFFECT_ACK_ISOLATE", "EFFECT_ACK_BLOCK"):
        raise OutputContractError("unknown effect acknowledgement state")
    if done is True and effect.get("state") != "DONE_WITHIN_DECLARED_SCOPE":
        raise OutputContractError("unscoped effect_ack_done is forbidden")
    if effect.get("state") == "DONE_WITHIN_DECLARED_SCOPE" and done is not True:
        raise OutputContractError("DONE_WITHIN_DECLARED_SCOPE requires effect_ack_done")
    if done and (effect.get("effect_ack") != "EFFECT_ACK_DONE"
                 or not evidence["execution_receipts"] or not evidence["readback"]):
        raise OutputContractError("scoped DONE requires bound effect receipt and readback")
    if not isinstance(binding.get("new_difference"), str) or not binding["new_difference"]:
        raise OutputContractError("new_difference must be explicit")
    return copy.deepcopy(dict(value))


def validate_change_extension(
    extension: Mapping[str, Any], *, expected_subject: Mapping[str, Any],
    predecessor_root: str, expected_changed_paths: list[str],
    independently_read_proof: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Check a separately obtained verifier result, never a producer's PASS.

    The caller must obtain ``independently_read_proof`` through its admitted
    authenticated read path. This pure validator does not authenticate a
    caller, check Lean itself, admit a writer, deploy or append a native event.
    A generic kernel build is deliberately insufficient: the separately
    qualified implementation-refinement witness must cover every changed path.
    """
    policy = json.loads(EXTENSION_POLICY.read_text(encoding="utf-8"))
    if policy.get("schema") != "qikvrt_proof_bound_change_admission_v1":
        raise OutputContractError("change policy unavailable or invalid")
    if not isinstance(extension, Mapping) or extension.get("schema") != "qikvrt_proof_extension_v1":
        raise OutputContractError("proof extension missing")
    if extension.get("subject") != dict(expected_subject):
        raise OutputContractError("proof extension subject mismatch")
    required_subject = {"repository", "head", "tree", "node", "epoch"}
    if set(expected_subject) != required_subject or any(
        not isinstance(expected_subject.get(k), str) or not expected_subject[k]
        for k in ("repository", "head", "tree", "node")
    ) or type(expected_subject.get("epoch")) is not int or expected_subject["epoch"] < 0:
        raise OutputContractError("expected admission subject invalid")
    if any(re.fullmatch(r"[0-9a-f]{40}", expected_subject[k]) is None for k in ("head", "tree")):
        raise OutputContractError("expected Git identity invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", predecessor_root):
        raise OutputContractError("trusted predecessor root invalid")
    if extension.get("parent_root_sha256") != predecessor_root:
        raise OutputContractError("proof predecessor root mismatch")
    paths = extension.get("changed_paths")
    if (not isinstance(paths, list) or not paths
            or any(not isinstance(p, str) or not p or p.startswith("/")
                   or ".." in pathlib.PurePosixPath(p).parts for p in paths)
            or len(paths) != len(set(paths)) or paths != expected_changed_paths):
        raise OutputContractError("complete changed-path inventory required")
    claims = extension.get("added_claims")
    if not isinstance(claims, list) or not claims or any(not isinstance(x, str) or not x for x in claims):
        raise OutputContractError("proof delta must add named checked claims")
    raw = json.dumps(dict(extension), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    digest = _sha256_bytes(raw)
    if not isinstance(independently_read_proof, Mapping):
        raise OutputContractError("UNVERIFIED: independent proof readback unavailable")
    receipt = independently_read_proof
    if (receipt.get("schema") != "qikvrt_qualified_change_proof_readback_v1"
            or receipt.get("state") != "KERNEL_VERIFIED_IMPLEMENTATION_REFINEMENT"
            or receipt.get("subject") != dict(expected_subject)
            or receipt.get("extension_sha256") != digest
            or receipt.get("parent_root_sha256") != predecessor_root
            or receipt.get("covered_paths") != paths
            or receipt.get("added_claims") != claims):
        raise OutputContractError("UNVERIFIED: exact implementation-refinement witness required")
    for field in ("preserves_predecessor_meaning", "conservative_extension", "fresh_kernel_check",
                  "qualified_implementation_bridge", "trusted_base_checker", "authenticated_readback"):
        if receipt.get(field) is not True:
            raise OutputContractError("UNVERIFIED: missing proof obligation " + field)
    for field in ("kernel_receipt_sha256", "compiled_witness_sha256", "new_root_sha256"):
        if not isinstance(receipt.get(field), str) or re.fullmatch(r"[0-9a-f]{64}", receipt[field]) is None:
            raise OutputContractError("UNVERIFIED: proof object identity missing")
    # This establishes only declared, separately sourced admission metadata.
    # Actual EAP authorization, writer fencing, append and effect readback follow.
    return {"schema": "qikvrt_proof_extension_structure_check_v1",
            "state": "BOUND_IMPLEMENTATION_PROOF_READBACK_CHECKED",
            "subject": dict(expected_subject), "extension_sha256": digest,
            "new_root_sha256": receipt["new_root_sha256"],
            "native_append_executed": False, "activation_authorized": False,
            "effect_ack_done": False}


def validate_json_file(path: pathlib.Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_output(value)


def proof_core_source_check() -> dict[str, Any]:
    """Check the declared core extension without promoting it to activation."""
    policy = json.loads(EXTENSION_POLICY.read_text(encoding="utf-8"))
    if (policy.get("schema") != "qikvrt_proof_bound_change_admission_v1"
            or policy.get("status") != "MANDATORY_NO_UNPROVED_ACTIVATION"
            or policy.get("bootstrap_bypass") is not False
            or policy.get("allowed_new_axioms") != []):
        raise OutputContractError("proof-admission policy weakened or invalid")
    source_instruction = policy.get("source_instruction", {})
    if _sha256_bytes(source_instruction.get("text", "").encode()) != source_instruction.get("sha256"):
        raise OutputContractError("Owner instruction source binding invalid")
    baseline = json.loads((ROOT / policy["source_inventory"]).read_text())
    if (baseline.get("head") != policy["predecessor"]["head"]
            or baseline.get("tree") != policy["predecessor"]["tree"]):
        raise OutputContractError("proof baseline subject mismatch")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.qikvrt_canonical_temporal_memory_kernel_evidence import safe_regular, strip_lean_comments_and_strings
    entrypoints = set(baseline["entrypoint_imports_may_only_be_extended"])
    preserved = []
    for item in baseline["files"]:
        path = safe_regular(ROOT, item["path"], "proof baseline path")
        raw = path.read_bytes()
        if _sha256_bytes(raw) != item["sha256"]:
            if item["path"] not in entrypoints:
                raise OutputContractError("predecessor proof source modified: " + item["path"])
            # Only add imports to the two library aggregators. No declaration,
            # statement, comment or existing import may disappear or change.
            old = subprocess.check_output(["git", "show", baseline["head"] + ":" + item["path"]], cwd=ROOT)
            old_imports = {line for line in old.splitlines(keepends=True) if line.startswith(b"import ")}
            retained = b"".join(line for line in raw.splitlines(keepends=True)
                                if not line.startswith(b"import ") or line in old_imports)
            if retained != old:
                raise OutputContractError("predecessor entrypoint changed beyond additive imports")
        preserved.append(item["path"])
    for key in ("core_source", "axiom_audit"):
        path = safe_regular(ROOT, policy[key], key)
        code = strip_lean_comments_and_strings(path.read_text())
        if re.search(r"\b(sorry|admit|axiom|unsafe)\b", code):
            raise OutputContractError("proof escape in " + key)
    git_context = {"repository": policy["authority_repository"],
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip(),
        "tracked_worktree_matches_commit": subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=ROOT).returncode == 0}
    return {"schema": "qikvrt_proof_core_extension_check_v1",
            "state": "SOURCE_INPUTS_VERIFIED", "predecessor": policy["predecessor"],
            "observed_git_context": git_context,
            "preserved_source_count": len(preserved), "formal_theorems": policy["formal_theorems"],
            "policy_sha256": _sha256_bytes(EXTENSION_POLICY.read_bytes()),
            "core_source_sha256": _sha256_bytes((ROOT / policy["core_source"]).read_bytes()),
            "checker_source_sha256": _sha256_bytes(pathlib.Path(__file__).read_bytes()),
            "activation_authorized": False, "effect_ack_done": False,
            "remaining": ["qualified exact-candidate implementation refinement",
                          "trusted external admission and node-specific native append/readback"]}


def proof_core_kernel_check() -> dict[str, Any]:
    result = proof_core_source_check()
    policy = json.loads(EXTENSION_POLICY.read_text())
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.qikvrt_canonical_temporal_memory_kernel_evidence import parse_axiom_reports
    project = ROOT / "formalization/QIKVRT_Formalization_v2.0"
    logs = ROOT / ".qikvrt/runtime/proof-admission/commands"
    logs.mkdir(parents=True, exist_ok=True)
    def checked_process(argv: list[str], label: str) -> subprocess.CompletedProcess:
        try:
            run = subprocess.run(argv, cwd=project, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            for suffix, output in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                (logs / (label + "." + suffix)).write_bytes(
                    output if isinstance(output, bytes) else (output or "").encode())
            (logs / (label + ".json")).write_text(json.dumps(
                {"argv": argv, "state": "VERIFICATION_UNAVAILABLE", "reason": "CHECKER_TIMEOUT"}) + "\n")
            raise OutputContractError("UNVERIFIED: kernel checker timed out: " + label) from exc
        (logs / (label + ".stdout")).write_text(run.stdout)
        (logs / (label + ".stderr")).write_text(run.stderr)
        (logs / (label + ".json")).write_text(json.dumps({"argv": argv, "exit_code": run.returncode,
            "stdout_sha256": _sha256_bytes(run.stdout.encode()),
            "stderr_sha256": _sha256_bytes(run.stderr.encode())}) + "\n")
        return run
    version_run = checked_process(["lake", "env", "lean", "--version"], "000-version")
    if version_run.returncode:
        raise OutputContractError("UNVERIFIED: compiler unavailable")
    version = version_run.stdout
    if "version 4.19.0," not in version:
        raise OutputContractError("locked Lean compiler version mismatch")
    commands = []
    baseline = json.loads((ROOT / policy["source_inventory"]).read_text())
    sources = [str(pathlib.PurePosixPath(p["path"]).relative_to("formalization/QIKVRT_Formalization_v2.0"))
               for p in baseline["files"] if p["path"].endswith(".lean")]
    sources += ["QIKVRTEffectAck/ProofExtension.lean", "QIKVRTUniversalOntology/Origin.lean",
                "QIKVRTEffectAck/ProofExtensionAxiomAudit.lean"]
    targets = [str(pathlib.PurePosixPath(source).with_suffix("")).replace("/", ".") for source in sources]
    build = checked_process(["lake", "build", *targets], "001-all-baseline-targets")
    build_output = build.stdout + build.stderr
    if build.returncode:
        raise OutputContractError("complete baseline module build failed\n" + build_output)
    for index, source in enumerate(sources):
        run = checked_process(["lake", "env", "lean", source], f"source-{index:03d}")
        output = run.stdout + run.stderr
        if run.returncode:
            raise OutputContractError("fresh Lean check failed: " + source + "\n" + output)
        commands.append({"source": source, "exit_code": run.returncode,
                         "output_sha256": _sha256_bytes(output.encode())})
        if source.endswith("AxiomAudit.lean"):
            axioms = parse_axiom_reports(output, policy["formal_theorems"] + ORIGIN_PROOFS)
    expected = set(policy["formal_theorems"] + ORIGIN_PROOFS)
    if set(axioms) != expected or any(axioms.values()):
        raise OutputContractError("fresh theorem axiom audit incomplete or nonempty")
    obj = project / ".lake/build/lib/lean/QIKVRTEffectAck/ProofExtension.olean"
    if not obj.is_file():
        raise OutputContractError("fresh project build required before object binding")
    negative = []
    for name in ("FalseUnavailableAdmits", "FalseDeletionIsAppend",
                 "FalseRetainedListPreservesState", "FalseTransportActivates"):
        path = ROOT / "docs/development/proof-bound-change-negative" / (name + ".lean")
        run = checked_process(["lake", "env", "lean", str(path)], name)
        output = run.stdout + run.stderr
        # A missing import, unavailable checker or setup failure is not a
        # successful negative control. The checked false theorem must fail.
        if (run.returncode == 0 or not any(marker in output for marker in
                ("tactic 'decide' proved that the proposition", "tactic 'rfl' failed"))
                or any(marker in output for marker in ("unknown module", "object file", "failed to locate application"))):
            raise OutputContractError("negative control verification unavailable or falsely accepted: " + name)
        negative.append({"name": name, "exit_code": run.returncode, "false_claim_rejected": True,
                         "source_sha256": _sha256_bytes(path.read_bytes()),
                         "output_sha256": _sha256_bytes(output.encode())})
    result.update({"state": "DECLARED_MODEL_KERNEL_VERIFIED", "compiler_version": version.strip(),
                   "compiled_model_sha256": _sha256_bytes(obj.read_bytes()),
                   "axioms_by_theorem": axioms, "fresh_commands": commands,
                   "negative_controls": negative,
                   "complete_baseline_build": {"target_count": len(targets), "exit_code": build.returncode,
                                               "output_sha256": _sha256_bytes(build_output.encode())},
                   "arbitrary_changed_software_formally_verified": False})
    again = proof_core_source_check()
    for key in ("core_source_sha256", "checker_source_sha256", "policy_sha256", "observed_git_context"):
        if again[key] != result[key]:
            raise OutputContractError("UNVERIFIED: source or subject changed during kernel verification")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--proof-core-static", action="store_true")
    mode.add_argument("--proof-core-kernel", action="store_true")
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args()
    load_policy()
    canonical_article_identity()
    if args.proof_core_static or args.proof_core_kernel:
        result = proof_core_kernel_check() if args.proof_core_kernel else proof_core_source_check()
        result = bind_output(result, node_id="proof-core-checker", repository="ingolf-lohmann/qik-vrt",
            subject={"predecessor": result["predecessor"], "core_source_sha256": result["core_source_sha256"],
                     "checker_source_sha256": result["checker_source_sha256"], "policy_sha256": result["policy_sha256"]},
            claim_kind="SOURCE_BOUND", statement="Check of the declared source-bound conditional proof core.",
            evidence_refs=[result["core_source_sha256"], result["policy_sha256"]],
            exclusions=["arbitrary implementation refinement", "native activation", "all-node adoption", "general EFFECT_ACK_DONE"])
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(result, sort_keys=True, ensure_ascii=False))
        return 0
    print(
        json.dumps(
            {
                "schema": "qikvrt_output_contract_selfcheck_v1",
                "policy_id": POLICY_ID,
                "article": canonical_article_identity(),
                "status": "PASS",
                "effect_ack_done": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
