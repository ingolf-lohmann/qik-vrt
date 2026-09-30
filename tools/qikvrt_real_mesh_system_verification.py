#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Reflexive system verification for the QIK-VRT real multi-pair mesh.

This tool verifies an execution receipt produced by ``qikvrt_real_mesh.py``
against the declared contract in ``state/mesh/QIKVRT_REAL_MESH_V1.json``,
applies the REFLEXIVE_FINDING_WORKFLOW_STANDARD, and emits a structured
audit receipt.

Each declared contract field is checked precisely.  Any deviation is recorded
as a finding and causes the tool to exit with a non-zero status.

Usage::

    python3 -B tools/qikvrt_real_mesh_system_verification.py verify \\
        --receipt path/to/EXECUTION_RECEIPT.json

    python3 -B tools/qikvrt_real_mesh_system_verification.py run \\
        --source-head <sha1> --source-tree <sha1>
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import pathlib
import re
import sys
import tempfile
import subprocess
import time
import zipfile
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "state" / "mesh" / "QIKVRT_REAL_MESH_V1.json"
REFLEXIVE_STANDARD_PATH = ROOT / "REFLEXIVE_FINDING_WORKFLOW_STANDARD.json"

VERIFICATION_RECEIPT_SCHEMA = "qikvrt_real_mesh_system_verification_v1"
AUDIT_SCHEMA = "qikvrt_real_mesh_system_audit_v1"
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(ValueError):
    """A contract violation discovered during reflexive verification."""


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return a canonical SHA-256 identifier in ``sha256:<hex>`` format.

    This matches the format produced by ``qikvrt_real_mesh.canonical_sha256``
    and stored in execution receipts.
    """
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def load_contract() -> dict[str, Any]:
    """Load and lightly validate the declared mesh contract."""
    try:
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"cannot load contract {CONTRACT_PATH}: {exc}"
        ) from exc
    if raw.get("schema") != "qikvrt_real_mesh_contract_v1":
        raise VerificationError("contract schema mismatch")
    if raw.get("mesh_id") != "QIKVRT_REAL_MULTI_PAIR_MESH_V1":
        raise VerificationError("contract mesh_id mismatch")
    return raw


def load_reflexive_standard() -> dict[str, Any]:
    """Load the REFLEXIVE_FINDING_WORKFLOW_STANDARD."""
    try:
        return json.loads(REFLEXIVE_STANDARD_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(
            f"cannot load reflexive standard {REFLEXIVE_STANDARD_PATH}: {exc}"
        ) from exc


def verify_receipt(
    receipt: dict[str, Any],
    contract: dict[str, Any],
) -> list[str]:
    """Return a list of findings.  An empty list means the receipt is conformant."""
    findings: list[str] = []

    def _check(condition: bool, finding: str) -> None:
        if not condition:
            findings.append(finding)

    # --- schema and identity ---
    _check(
        receipt.get("schema") == "qikvrt_real_mesh_execution_receipt_v1",
        "receipt.schema must be qikvrt_real_mesh_execution_receipt_v1",
    )
    _check(
        receipt.get("mesh_id") == contract["mesh_id"],
        f"receipt.mesh_id must be {contract['mesh_id']}",
    )

    # --- minimum_topology ---
    topo = contract.get("minimum_topology", {})
    _check(
        isinstance(receipt.get("pair_count"), int)
        and receipt["pair_count"] >= topo.get("pair_count", 2),
        f"receipt.pair_count must be >= {topo.get('pair_count', 2)}",
    )
    _check(
        isinstance(receipt.get("node_process_count"), int)
        and receipt["node_process_count"] >= topo.get("node_process_count", 4),
        f"receipt.node_process_count must be >= {topo.get('node_process_count', 4)}",
    )
    _check(
        receipt.get("redundant_path_observed") is True,
        "receipt.redundant_path_observed must be true (contract requires redundant_routes_required)",
    )

    # --- transport ---
    transport = contract.get("transport", {})
    _check(
        receipt.get("network_scope") == transport.get("network_scope"),
        f"receipt.network_scope must be {transport.get('network_scope')}",
    )
    _check(
        receipt.get("event_model") == transport.get("event_model"),
        f"receipt.event_model must be {transport.get('event_model')}",
    )

    # --- restart replay ---
    replay = receipt.get("restart_replay", {})
    _check(
        replay.get("same_terminal_receipt") is True,
        "receipt.restart_replay.same_terminal_receipt must be true"
        " (contract: idempotent_exact_replay)",
    )
    _check(
        replay.get("ledger_record_count_unchanged") is True,
        "receipt.restart_replay.ledger_record_count_unchanged must be true"
        " (contract: append_only_hash_linked_ledger + restart_reconstruction)",
    )

    # --- completion_claims ---
    claims = receipt.get("completion_claims", {})
    required_true = {
        "real_multi_pair_mesh_runtime_executed",
        "independent_tcp_node_processes_observed",
        "multi_hop_delivery_reobserved",
        "acknowledgement_return_path_observed",
        "append_only_restart_persistence_observed",
        "bounded_loopback_effect_ack_done",
    }
    required_false = {
        "general_effect_ack_done",
        "general_internet_reachability",
        "production_deployment",
        "physical_hardware_execution",
        "authority_mirror_synchronization",
        "authority_mirror_equality_claimed",
        "merge",
        "PASS",
        "FINAL_PASS",
    }
    for field in required_true:
        _check(
            claims.get(field) is True,
            f"receipt.completion_claims.{field} must be true",
        )
    for field in required_false:
        _check(
            claims.get(field) is False,
            f"receipt.completion_claims.{field} must be false"
            " (effect boundary violation)",
        )

    # --- effect boundary ---
    eb = contract.get("effect_boundary", {})
    _check(
        receipt.get("external_effect") == "NONE",
        "receipt.external_effect must be NONE",
    )
    for eb_field in (
        "general_effect_ack_done",
        "general_internet_reachability",
        "production_deployment",
        "physical_hardware_execution",
        "authority_mirror_synchronization",
        "authority_mirror_equality_claimed",
        "merge",
        "PASS",
        "FINAL_PASS",
    ):
        declared = eb.get(eb_field)
        if declared is False:
            _check(
                claims.get(eb_field) is False,
                f"effect_boundary.{eb_field} is false in contract"
                f" but receipt claims it true",
            )

    # --- effect_ack ---
    eff = contract.get("effect_ack", {})
    _check(
        receipt.get("effect_ack_scope") == eff.get("completion_scope"),
        f"receipt.effect_ack_scope must be {eff.get('completion_scope')}",
    )
    # all hop ledgers must be reobserved
    routes = receipt.get("routes", [])
    _check(
        len(routes) >= 2,
        "receipt must contain at least two route observations",
    )
    for i, route in enumerate(routes):
        obs = route.get("observation", {})
        path = obs.get("path") or obs.get("hops") or []
        _check(
            isinstance(path, list) and len(path) >= 2,
            f"route[{i}].observation.path must contain at least two entries",
        )

    # --- receipt integrity ---
    stored_sha = receipt.get("receipt_sha256")
    if isinstance(stored_sha, str):
        receipt_without_sha = {k: v for k, v in receipt.items() if k != "receipt_sha256"}
        computed = canonical_sha256(receipt_without_sha)
        _check(
            stored_sha == computed,
            "receipt.receipt_sha256 does not match canonical hash of receipt body",
        )

    return findings


def build_audit_receipt(
    *,
    receipt_path: str | None,
    receipt: dict[str, Any],
    contract: dict[str, Any],
    findings: list[str],
    reflexive_standard: dict[str, Any],
) -> dict[str, Any]:
    """Build a structured audit receipt."""
    status = "PASS" if not findings else "BLOCK"
    audit: dict[str, Any] = {
        "schema": AUDIT_SCHEMA,
        "mesh_id": contract.get("mesh_id"),
        "verified_at": _utc_now(),
        "receipt_source": receipt_path or "in-memory",
        "source_head": receipt.get("source_head"),
        "source_tree": receipt.get("source_tree"),
        "contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "contract_schema": contract.get("schema"),
        "reflexive_standard_id": reflexive_standard.get("id"),
        "reflexive_standard_status": reflexive_standard.get("status"),
        "finding_count": len(findings),
        "findings": findings,
        "status": status,
        "effect_boundary_preserved": not any(
            "effect boundary" in f or "must be false" in f for f in findings
        ),
        "bounded_loopback_effect_ack_scope_confirmed": receipt.get("effect_ack_scope")
        == "BOUNDED_LOOPBACK_MULTI_PAIR_MESSAGE_DELIVERY_ONLY",
        "general_effect_ack_done": False,
        "external_effect": "NONE",
        "transport_ack_is_effect_ack": False,
    }
    audit["audit_sha256"] = canonical_sha256(audit)
    return audit


def run_and_verify(
    *,
    source_head: str,
    source_tree: str,
    workdir: pathlib.Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Execute the real mesh demo and verify the resulting receipt."""
    from tools import qikvrt_real_mesh as mesh  # noqa: PLC0415

    resolved_workdir = workdir or pathlib.Path(
        tempfile.mkdtemp(prefix="qikvrt-real-mesh-sysverify-")
    )
    receipt = mesh.run_demo(
        resolved_workdir,
        source_head=source_head,
        source_tree=source_tree,
    )
    contract = load_contract()
    findings = verify_receipt(receipt, contract)
    return receipt, contract, findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _verify_command(args: argparse.Namespace) -> int:
    try:
        raw = json.loads(pathlib.Path(args.receipt).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"BLOCK: cannot load receipt: {exc}", file=sys.stderr)
        return 2

    try:
        contract = load_contract()
        reflexive_standard = load_reflexive_standard()
    except VerificationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2

    findings = verify_receipt(raw, contract)
    audit = build_audit_receipt(
        receipt_path=args.receipt,
        receipt=raw,
        contract=contract,
        findings=findings,
        reflexive_standard=reflexive_standard,
    )

    encoded = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

    if findings:
        print(
            f"BLOCK: {len(findings)} finding(s) — reflexive correction required",
            file=sys.stderr,
        )
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] {f}", file=sys.stderr)
        return 2

    print("PASS: all declared contract fields verified", file=sys.stderr)
    return 0


def _run_command(args: argparse.Namespace) -> int:
    if not SHA1_RE.fullmatch(args.source_head):
        print("BLOCK: --source-head must be a 40-char lowercase hex SHA-1", file=sys.stderr)
        return 2
    if not SHA1_RE.fullmatch(args.source_tree):
        print("BLOCK: --source-tree must be a 40-char lowercase hex SHA-1", file=sys.stderr)
        return 2

    workdir = pathlib.Path(args.workdir) if args.workdir else None

    try:
        contract = load_contract()
        reflexive_standard = load_reflexive_standard()
    except VerificationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2

    try:
        receipt, _contract, findings = run_and_verify(
            source_head=args.source_head,
            source_tree=args.source_tree,
            workdir=workdir,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCK: mesh execution failed: {exc}", file=sys.stderr)
        return 2

    audit = build_audit_receipt(
        receipt_path=None,
        receipt=receipt,
        contract=contract,
        findings=findings,
        reflexive_standard=reflexive_standard,
    )

    encoded = json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        out_path = pathlib.Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded, encoding="utf-8")
    print(encoded, end="")

    if findings:
        print(
            f"BLOCK: {len(findings)} finding(s) — reflexive correction required",
            file=sys.stderr,
        )
        for i, f in enumerate(findings, 1):
            print(f"  [{i}] {f}", file=sys.stderr)
        return 2

    print("PASS: real mesh executed and all contract fields verified", file=sys.stderr)
    return 0


def consolidate_node_ledgers(paths: dict[str, pathlib.Path], archive: pathlib.Path) -> dict:
    """Preserve and independently read back every byte in the declared corpus.

    This archive is a projection, never a replacement for the original ledgers.
    Reconstructed node ledgers must retain accepted, completed and held records.
    """
    from tools import qikvrt_real_mesh as mesh
    inputs = {}
    for node_id, path in sorted(paths.items()):
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", node_id):
            raise VerificationError("unsafe consolidation node identifier")
        ledger = mesh.AppendOnlyNodeLedger(path, node_id)
        raw = path.read_bytes()
        inputs[node_id] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                           "records": ledger.sequence, "accepted": sorted(ledger.accepted),
                           "completed": sorted(ledger.completed)}
    # Create-only destination: an earlier corpus must never be overwritten.
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for node_id, path in sorted(paths.items()):
            output.writestr(node_id + ".jsonl", path.read_bytes())
    with tempfile.TemporaryDirectory(prefix="qikvrt-consolidation-readback-") as directory:
        with zipfile.ZipFile(archive) as readback:
            if sorted(readback.namelist()) != sorted(node + ".jsonl" for node in paths):
                raise VerificationError("consolidated corpus membership mismatch")
            if readback.testzip() is not None:
                raise VerificationError("consolidated corpus CRC failure")
            for node_id, path in sorted(paths.items()):
                raw = readback.read(node_id + ".jsonl")
                if raw != path.read_bytes() or hashlib.sha256(raw).hexdigest() != inputs[node_id]["sha256"]:
                    raise VerificationError("consolidation lost or changed node bytes")
                recovered = pathlib.Path(directory) / (node_id + ".jsonl")
                recovered.write_bytes(raw)
                ledger = mesh.AppendOnlyNodeLedger(recovered, node_id)
                if (ledger.sequence != inputs[node_id]["records"] or
                    sorted(ledger.accepted) != inputs[node_id]["accepted"] or
                    sorted(ledger.completed) != inputs[node_id]["completed"]):
                    raise VerificationError("consolidation reconstruction mismatch")
    return {"inputs": inputs, "archive": archive.name,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "zero_missing_or_changed_bytes": True, "restart_reconstruction": True,
            "scope": "EXACT_NODE_LEDGER_CORPUS_ONLY"}


def run_multitasking(workdir: pathlib.Path, *, repository: str, source_head: str,
                     source_tree: str, counterpart_head: str, counterpart_tree: str,
                     node_counts: tuple[int, ...] = (4, 8, 16), repetitions: int = 3) -> dict:
    """Real processes, overlapping TCP routes, exact replay and lossless readback.

    All nodes execute THIS checkout. Counterpart HEAD/TREE is a reference binding,
    not a remote executor receipt. The other repository needs its own execution.
    """
    from tools import qikvrt_real_mesh as mesh
    if repository not in ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"):
        raise VerificationError("unknown implementation repository")
    if any(not isinstance(sha, str) or not SHA1_RE.fullmatch(sha) for sha in
           (source_head, source_tree, counterpart_head, counterpart_tree)):
        raise VerificationError("unbound multitasking implementation or counterpart")
    if (not node_counts or len(set(node_counts)) != len(node_counts) or
        any(type(n) is not int or n not in (4, 8, 16) for n in node_counts) or
        type(repetitions) is not int or not 1 <= repetitions <= 3):
        raise VerificationError("bounded 4/8/16-node, 1..3-trial workload required")
    workdir.mkdir(parents=True, exist_ok=False)
    authority_tree, mirror_tree = ((source_tree, counterpart_tree) if repository == "Goldkelch/qik-vrt"
                                   else (counterpart_tree, source_tree))
    runs = []
    for count in node_counts:
        for trial in range(1, repetitions + 1):
            directory = workdir / f"nodes-{count}-trial-{trial}"
            started = time.monotonic()
            with mesh.MeshHarness(directory, authority_tree, node_count=count, mirror_tree=mirror_tree) as harness:
                startup_seconds = time.monotonic() - started
                ids = list(harness.nodes)
                if count == 4:
                    ids = [ids[0], ids[1], ids[3], ids[2]]
                messages = []
                for index in range(count):
                    route = ids[index:] + ids[:index]
                    messages.append(mesh.build_message(harness.topology, route,
                        message_id=f"multitask-{count}-{trial}-{index}", nonce=f"nonce-{count}-{trial}-{index}",
                        source_head=source_head, source_tree=source_tree))

                async def burst():
                    async def deliver(message):
                        first = mesh.node_by_id(message["topology"], message["route"][0])
                        begin = time.monotonic()
                        terminal = await mesh.send_message_async(first["host"], first["port"], message)
                        return terminal, (time.monotonic() - begin) * 1000
                    return await asyncio.gather(*(deliver(message) for message in messages))

                results = asyncio.run(burst())
                observations = []
                for message, (terminal, latency) in zip(messages, results):
                    observation = mesh.reobserve_route(harness, message, terminal)
                    ack = mesh.finalize_effect_ack(message, observation)
                    if ack["state"] != "EFFECT_ACK_DONE":
                        raise VerificationError("message effect lacks fresh readback")
                    observations.append({"message": message, "terminal": terminal,
                                         "readback": observation, "bounded_effect_ack": ack,
                                         "route_latency_ms": latency})
                peaks = {}
                for node_id, node in harness.nodes.items():
                    active, peak = set(), 0
                    for raw in node.ledger_path.read_text().splitlines():
                        record = json.loads(raw)
                        if record["event"] == "ACCEPTED":
                            active.add(record["message_id"])
                            peak = max(peak, len(active))
                        elif record["event"] in ("COMPLETED", "HELD"):
                            active.discard(record["message_id"])
                    if active or peak < 2:
                        raise VerificationError("node lacks observed overlapping completed tasks: " + node_id)
                    peaks[node_id] = peak
                # Restart every process on its previous endpoint so the exact
                # original topology/message bytes remain usable for replay.
                original = {node_id: node.ledger_path.read_bytes() for node_id, node in harness.nodes.items()}
                for node in harness.nodes.values():
                    port = node.port
                    stderr = node.stop()
                    if stderr:
                        raise VerificationError("node restart diagnostics: " + stderr)
                    node.start(port=port)
                replay = asyncio.run(burst())
                if [r[0] for r in replay] != [r[0] for r in results]:
                    raise VerificationError("exact replay changed terminal receipts")
                if any(node.ledger_path.read_bytes() != original[node_id] for node_id, node in harness.nodes.items()):
                    raise VerificationError("restart replay duplicated or changed ledger effect")
                consolidation = consolidate_node_ledgers(
                    {node_id: node.ledger_path for node_id, node in harness.nodes.items()},
                    directory / "CONSOLIDATED_LEDGERS.zip")
                record_count = sum(item["records"] for item in consolidation["inputs"].values())
                if record_count != 2 * count * count:
                    raise VerificationError("lost or duplicated accepted/completed records")
                runs.append({"node_count": count, "trial": trial, "startup_seconds": startup_seconds,
                             "messages_attempted": count, "messages_completed": len(results),
                             "effect_ack_done_count": len(observations), "ledger_records": record_count,
                             "peak_inflight_by_node": peaks, "restart_recovery_success": True,
                             "process_failures": 0, "integrity_failures": 0,
                             "routes": observations, "consolidation": consolidation,
                             "elapsed_seconds": time.monotonic() - started})
    inputs = ("tools/qikvrt_real_mesh.py", "tools/qikvrt_real_mesh_system_verification.py",
              "src/qikvrt_effect_ack.py", "tests/test_qikvrt_real_mesh.py",
              "tests/test_qikvrt_real_mesh_system_verification.py", "state/mesh/QIKVRT_REAL_MESH_V1.json")
    report = {"schema": "qikvrt_repository_multitasking_v1", "status": "SCOPED_WORKLOAD_CHECKED",
              "implementation_subject": {"repository": repository, "head": source_head, "tree": source_tree},
              "counterpart_reference": {"repository": "ingolf-lohmann/qik-vrt" if repository == "Goldkelch/qik-vrt" else "Goldkelch/qik-vrt",
                                        "head": counterpart_head, "tree": counterpart_tree, "execution_verified_by_this_run": False},
              "input_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
              "runtime": {"python": sys.version, "executable": sys.executable},
              "node_counts": list(node_counts), "repetitions": repetitions, "runs": runs,
              "source_binding_verified": False,
              "scope": "THIS_CHECKOUT_LOOPBACK_AUTHORITY_MIRROR_ROLE_PROCESSES_AND_DECLARED_LEDGER_CORPUS",
              "completion_claims": {"tested_scope_multitasking": True, "unbounded_scalability": False,
                                    "remote_counterpart_executed": False, "whole_repository_completion": False,
                                    "all_temdd_layers_conformant": False, "main_activation": False,
                                    "authority_mirror_equality": False, "general_effect_ack_done": False}}
    report["receipt_sha256"] = canonical_sha256(report)
    return report


def verify_multitasking_report(report: dict, workdir: pathlib.Path, *, repository: str,
                              source_head: str, source_tree: str) -> dict:
    """Qualify only the exact bounded implementation and original ledger corpus.

    Callers must supply freshly observed subjects, never subjects copied from
    the receipt being checked. This is neither hosted-run authentication nor
    remote execution, lifetime stability or an unbounded scalability proof.
    """
    from tools import qikvrt_real_mesh as mesh
    def require(condition, reason):
        if not condition:
            raise VerificationError(reason)
    require(repository in ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt") and
            all(isinstance(value, str) and SHA1_RE.fullmatch(value) for value in (source_head, source_tree)),
            "unbound expected implementation subject")
    require(isinstance(report, dict), "multitasking evidence must be an object")
    require(report.get("schema") == "qikvrt_repository_multitasking_v1", "unknown multitasking evidence")
    require(report.get("implementation_subject") == {"repository": repository, "head": source_head,
                                                     "tree": source_tree}, "stale or substituted implementation subject")
    require(report.get("source_binding_verified") is True, "unverified implementation source")
    require(report.get("status") == "SCOPED_WORKLOAD_CHECKED", "workload was not completed")
    projection = dict(report)
    digest = projection.pop("receipt_sha256", None)
    require(digest == canonical_sha256(projection), "multitasking receipt digest mismatch")
    inputs = ("tools/qikvrt_real_mesh.py", "tools/qikvrt_real_mesh_system_verification.py",
              "src/qikvrt_effect_ack.py", "tests/test_qikvrt_real_mesh.py",
              "tests/test_qikvrt_real_mesh_system_verification.py", "state/mesh/QIKVRT_REAL_MESH_V1.json")
    require(report.get("input_sha256") == {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in inputs
    }, "implementation or contract version changed; reverify required")
    require(report.get("runtime") == {"python": sys.version, "executable": sys.executable},
            "execution runtime changed; reverify required")
    claims = report.get("completion_claims", {})
    require(isinstance(claims, dict), "invalid completion claims")
    require(claims.get("tested_scope_multitasking") is True and all(claims.get(name) is False for name in
        ("unbounded_scalability", "remote_counterpart_executed", "whole_repository_completion",
         "all_temdd_layers_conformant", "main_activation", "authority_mirror_equality", "general_effect_ack_done")),
        "unsupported completion claim")
    require(report.get("scope") == "THIS_CHECKOUT_LOOPBACK_AUTHORITY_MIRROR_ROLE_PROCESSES_AND_DECLARED_LEDGER_CORPUS",
            "unsupported qualification scope")
    reference = report.get("counterpart_reference", {})
    require(isinstance(reference, dict), "invalid counterpart reference")
    require(reference.get("execution_verified_by_this_run") is False, "reference promoted to remote execution")
    require(reference.get("repository") == ("ingolf-lohmann/qik-vrt" if repository == "Goldkelch/qik-vrt"
                                            else "Goldkelch/qik-vrt"), "counterpart substitution")
    require(all(isinstance(reference.get(name), str) and SHA1_RE.fullmatch(reference[name])
                for name in ("head", "tree")), "unbound counterpart reference")
    require(report.get("node_counts") == [4, 8, 16] and type(report.get("repetitions")) is int
            and report["repetitions"] == 3, "incomplete scale or repetition coverage")
    runs = report.get("runs", [])
    expected = {(count, trial) for count in (4, 8, 16) for trial in (1, 2, 3)}
    require(isinstance(runs, list) and len(runs) == 9, "missing execution trials")
    seen = set()
    for run in runs:
        require(isinstance(run, dict), "invalid execution trial")
        count, trial = run.get("node_count"), run.get("trial")
        require(type(count) is int and type(trial) is int and (count, trial) in expected
                and (count, trial) not in seen, "unknown or duplicate execution trial")
        seen.add((count, trial))
        for name, value in (("messages_attempted", count), ("messages_completed", count),
                            ("effect_ack_done_count", count), ("ledger_records", 2 * count * count),
                            ("process_failures", 0), ("integrity_failures", 0)):
            require(type(run.get(name)) is int and run[name] == value, "invalid execution counter: " + name)
        require(run.get("restart_recovery_success") is True, "restart replay not verified")
        nodes = {f"pair-{chr(97 + pair)}-{role}" for pair in range(count // 2)
                 for role in ("authority", "mirror")}
        consolidation = run.get("consolidation", {})
        require(isinstance(consolidation, dict) and isinstance(consolidation.get("inputs"), dict)
                and isinstance(run.get("peak_inflight_by_node"), dict), "invalid node corpus inventory")
        require(consolidation.get("zero_missing_or_changed_bytes") is True and
                consolidation.get("restart_reconstruction") is True, "lossless readback missing")
        require(set(consolidation.get("inputs", {})) == nodes and set(run.get("peak_inflight_by_node", {})) == nodes,
                "missing or substituted node")
        require(consolidation.get("archive") == "CONSOLIDATED_LEDGERS.zip", "unsafe corpus archive path")
        directory = workdir / f"nodes-{count}-trial-{trial}"
        require(not directory.is_symlink() and not (directory / "ledgers").is_symlink()
                and not (directory / "CONSOLIDATED_LEDGERS.zip").is_symlink(), "redirected corpus path")
        require({path.name for path in (directory / "ledgers").iterdir()} == {node + ".jsonl" for node in nodes},
                "undeclared original ledger")
        raw_archive = (directory / "CONSOLIDATED_LEDGERS.zip").read_bytes()
        require(hashlib.sha256(raw_archive).hexdigest() == consolidation.get("archive_sha256"), "archive changed")
        with zipfile.ZipFile(io.BytesIO(raw_archive)) as archive:
            require(sorted(archive.namelist()) == sorted(node + ".jsonl" for node in nodes), "corpus membership changed")
            for node in nodes:
                path = directory / "ledgers" / (node + ".jsonl")
                require(path.is_file() and not path.is_symlink(), "original ledger missing or redirected")
                raw = path.read_bytes()
                require(archive.read(node + ".jsonl") == raw, "original and consolidated ledger bytes differ")
                ledger = mesh.AppendOnlyNodeLedger(path, node)
                item = consolidation["inputs"][node]
                require(item == {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                                  "records": ledger.sequence, "accepted": sorted(ledger.accepted),
                                  "completed": sorted(ledger.completed)}, "ledger reconstruction differs")
                messages = {f"multitask-{count}-{trial}-{index}" for index in range(count)}
                require(set(ledger.accepted) == set(ledger.completed) == messages and ledger.sequence == 2 * count,
                        "missing or duplicated message effect")
                active, peak = set(), 0
                for line in raw.splitlines():
                    record = json.loads(line)
                    if record["event"] == "ACCEPTED":
                        active.add(record["message_id"])
                        peak = max(peak, len(active))
                    elif record["event"] in ("COMPLETED", "HELD"):
                        active.discard(record["message_id"])
                require(not active and peak >= 2 and run["peak_inflight_by_node"][node] == peak,
                        "node overlap is not supported by original ledger")
    receipt = {"schema": "qikvrt_multitasking_qualification_v1", "status": "QUALIFIED_FOR_EXACT_BOUNDED_SCOPE",
               "implementation_subject": report["implementation_subject"], "report_sha256": digest,
               "input_sha256": report["input_sha256"], "scope": report["scope"],
               "runtime": report["runtime"],
               "mutation_rule": "ANY_SUBJECT_INPUT_OR_RUNTIME_VERSION_CHANGE_INVALIDATES_QUALIFICATION",
               "remote_counterpart_execution": False, "continuous_operation_proven": False,
               "unbounded_scalability_proven": False, "general_effect_ack_done": False}
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def _multitasking_source(args: argparse.Namespace):
    remote = subprocess.check_output(["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"], text=True).strip()
    if remote not in (f"https://github.com/{args.repository}.git", f"https://github.com/{args.repository}",
                      f"git@github.com:{args.repository}.git"):
        raise VerificationError("implementation repository does not match the configured origin")
    values = [subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", ref], text=True).strip()
              for ref in ("HEAD", "HEAD^{tree}")]
    dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain"], text=True)
    if values != [args.source_head, args.source_tree] or dirty:
        raise VerificationError("multitasking requires the exact clean committed implementation")
    return values

def _multitasking_command(args: argparse.Namespace) -> int:
    try:
        before = _multitasking_source(args)
        report = run_multitasking(pathlib.Path(args.workdir), repository=args.repository,
            source_head=args.source_head, source_tree=args.source_tree,
            counterpart_head=args.counterpart_head, counterpart_tree=args.counterpart_tree)
        if _multitasking_source(args) != before:
            raise VerificationError("implementation mutated during execution")
        report["source_binding_verified"] = True
        report.pop("receipt_sha256")
        report["receipt_sha256"] = canonical_sha256(report)
        verify_multitasking_report(report, pathlib.Path(args.workdir), repository=args.repository,
                                  source_head=args.source_head, source_tree=args.source_tree)
        if _multitasking_source(args) != before:
            raise VerificationError("implementation mutated during qualification")
        pathlib.Path(args.output).write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
        print(json.dumps({"status": report["status"], "runs": len(report["runs"]),
                          "subject": report["implementation_subject"], "receipt_sha256": report["receipt_sha256"]}))
    except (VerificationError, OSError, ValueError, RuntimeError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2
    return 0


def _qualification_command(args: argparse.Namespace) -> int:
    try:
        before = _multitasking_source(args)
        report = json.loads(pathlib.Path(args.report).read_text())
        receipt = verify_multitasking_report(report, pathlib.Path(args.workdir), repository=args.repository,
                                            source_head=args.source_head, source_tree=args.source_tree)
        if _multitasking_source(args) != before:
            raise VerificationError("implementation mutated during qualification")
        encoded = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
        if args.output:
            pathlib.Path(args.output).write_text(encoded)
        print(encoded, end="")
        return 0
    except (VerificationError, OSError, ValueError, RuntimeError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print("BLOCK: " + str(exc), file=sys.stderr)
        return 2


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify", help="verify an existing execution receipt")
    verify.add_argument("--receipt", required=True, help="path to execution receipt JSON")
    verify.add_argument("--output", help="path to write audit receipt JSON")
    verify.set_defaults(func=_verify_command)

    run = sub.add_parser("run", help="execute real mesh and verify the receipt")
    run.add_argument("--source-head", required=True)
    run.add_argument("--source-tree", required=True)
    run.add_argument("--workdir")
    run.add_argument("--output", help="path to write audit receipt JSON")
    run.set_defaults(func=_run_command)

    multitasking = sub.add_parser("multitasking", help="measure the bounded 4/8/16-node parallel/restart/consolidation corpus")
    for name in ("repository", "source-head", "source-tree", "counterpart-head", "counterpart-tree", "workdir", "output"):
        multitasking.add_argument("--" + name, required=True)
    multitasking.set_defaults(func=_multitasking_command)

    qualification = sub.add_parser("verify-multitasking", help="qualify exact implementation and original bounded corpus")
    for name in ("repository", "source-head", "source-tree", "report", "workdir"):
        qualification.add_argument("--" + name, required=True)
    qualification.add_argument("--output")
    qualification.set_defaults(func=_qualification_command)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
