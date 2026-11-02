#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check the causal-distance extension using the existing Lean evidence helpers.

The historical temporal-memory plan has a frozen, single-module claim scope.
This successor reuses its safe paths, byte identities, command runner, lexical
escape filter and axiom-report parser, while keeping a separate three-module
plan. It does not promote historical claims or perform external effects.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys

try:
    from . import qikvrt_canonical_temporal_memory_kernel_evidence as original
except ImportError:
    import qikvrt_canonical_temporal_memory_kernel_evidence as original

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
PUBLICATION = "docs/publications/2026-10-24-causal-distance-temporal-memory"
PLAN = PUBLICATION + "/KERNEL_PROOF_PLAN.json"


def verify() -> dict:
    plan_path = original.safe_regular(ROOT, PLAN, "proof plan")
    plan = original.load_json(plan_path, "proof plan")
    original.require(plan["schema"] == "qikvrt_causal_distance_kernel_plan_v1", "wrong plan schema")
    expected = plan["expected_axioms_by_theorem"]
    original.require(len(expected) == 36, "wrong reviewed theorem inventory")
    original.require(all(set(a) <= original.ALLOWED_AXIOMS for a in expected.values()), "forbidden axiom policy")
    source_identities = []
    for raw, bound in plan["source_bindings"].items():
        path = original.safe_regular(ROOT, raw, "bound source")
        observed = original.identity(path, ROOT)
        original.require(observed == bound, "source identity differs: " + raw)
        code = original.strip_lean_comments_and_strings(path.read_text())
        original.require(not re.search(r"\b(?:sorry|admit|axiom|unsafe|constant)\b", code), "proof escape: " + raw)
        source_identities.append(observed)
    actual_declarations = []
    for module in plan["proof_modules"]:
        path = original.safe_regular(PROJECT, module.replace(".", "/") + ".lean", "proof module")
        text = path.read_text()
        namespace = re.search(r"^namespace (\S+)", text, re.M).group(1)
        actual_declarations += [namespace + "." + n for n in re.findall(r"^theorem (\w+)", text, re.M)]
    original.require(set(actual_declarations) == set(expected), "unaudited or missing theorem")
    entrypoint = original.strip_lean_comments_and_strings((PROJECT / "QIKVRTEffectAck.lean").read_text())
    imports = set(re.findall(r"^import\s+([A-Za-z][A-Za-z0-9_.]*)\s*$", entrypoint, re.M))
    original.require(set(plan["proof_modules"]) <= imports, "unconnected module")
    original.require((PROJECT / "lean-toolchain").read_text().strip() == "leanprover/lean4:v4.19.0", "toolchain changed")
    build, _ = original.run(["lake", "build", "QIKVRTEffectAck"], PROJECT)
    checks = []
    objects = []
    for module in plan["proof_modules"]:
        source = module.replace(".", "/") + ".lean"
        result, _ = original.run(["lake", "env", "lean", "-E", "hasSorry", source], PROJECT)
        checks.append(result)
        obj = original.safe_regular(PROJECT, ".lake/build/lib/lean/" + module.replace(".", "/") + ".olean", "proof object")
        objects.append(original.identity(obj, PROJECT))
    audit_run, audit_output = original.run(["lake", "env", "lean", "QIKVRTEffectAck/CausalDistanceAxiomAudit.lean"], PROJECT)
    observed = original.parse_axiom_reports(audit_output, list(expected))
    original.require(observed == {k: sorted(v) for k, v in expected.items()}, "axiom inventory differs")
    negative_results = []
    for name, identity in plan["negative_controls"].items():
        file = original.safe_regular(ROOT, PUBLICATION + "/negative/" + name, "negative control")
        original.require(original.identity(file, ROOT) == identity, "negative bytes differ")
        r = subprocess.run(["lake", "env", "lean", str(file)], cwd=PROJECT, capture_output=True, text=True)
        out = r.stdout + r.stderr
        original.require(r.returncode != 0 and "error:" in out, "false theorem was not rejected: " + name)
        original.require("unknown module" not in out and "failed to locate" not in out, "negative control did not reach compiler")
        negative_results.append({"name": name, "exit_code": r.returncode, "rejected": True, "diagnostics": out})
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, capture_output=True, text=True)
    _, version = original.run(["lake", "env", "lean", "--version"], PROJECT)
    return {
        "schema": "qikvrt_causal_distance_kernel_receipt_v1",
        "status": "KERNEL_VERIFIED",
        "plan": original.identity(plan_path, ROOT),
        "verifier": original.identity(Path(__file__).resolve(), ROOT),
        "reused_verifier_helpers": original.identity(Path(original.__file__).resolve(), ROOT),
        "source_bindings": source_identities,
        "compiled_objects": objects,
        "theorem_count": len(expected),
        "axioms_by_theorem": observed,
        "project_axioms": [],
        "build": build,
        "source_checks": checks,
        "axiom_audit": audit_run,
        "negative_controls": negative_results,
        "lean_version": version.strip(),
        "checkout_commit": git.stdout.strip() if git.returncode == 0 else None,
        "checkout_tree": tree.stdout.strip() if tree.returncode == 0 else None,
        "workflow_event": os.environ.get("GITHUB_EVENT_NAME"),
        "workflow_sha": os.environ.get("GITHUB_SHA"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "path_compatibility_preload_used": bool(os.environ.get("LD_PRELOAD")),
        "scope": plan["scope"],
        "nonclaims": plan["nonclaims"],
        "zenodo_published": False,
        "native_effect_ack_done": False,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))
    except (original.EvidenceError, KeyError, OSError, ValueError) as error:
        print("BLOCK: " + str(error), file=sys.stderr)
        raise SystemExit(1)
