#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline interruption A/B harness. This version cannot establish product benefit.

Only Python's standard library is required. The existing Firefox terminal is
reused for a separate HTTP smoke test, never impersonated as a research agent.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.util
import json
import os
import platform
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "benchmarks/browser-assistant-ab"
ZERO = "0" * 64
TRIAL_ID = re.compile(r"^p[0-9]{3}-(baseline|qikvrt)$")
EVENTS = {
    "trial_start", "checkpoint_readback", "interruption_observed", "resume_signal",
    "resume_probe", "step_output", "human_input", "automatic_context",
    "step_claim", "task_claim", "trial_end",
}
INPUT_KINDS = {"context_reentry", "instruction", "correction", "approval", "restart", "escalation"}
SOURCE_PATHS = [
    "tools/qikvrt_browser_assistant_ab.py",
    "benchmarks/browser-assistant-ab/console.html",
    "browser/firefox/qikvrt-terminal/manifest.json",
    "browser/firefox/qikvrt-terminal/background.js",
    "browser/firefox/qikvrt-terminal/content.js",
    "src/qikvrt_effect_ack_http_terminal.py",
    "policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json",
    "src/qikvrt_personal_assistant.py",
    "personal/ingolf-lohmann/firefox-assistant/CAPABILITIES.json",
    "personal/ingolf-lohmann/firefox-assistant/ui.html",
    "personal/ingolf-lohmann/firefox-assistant/ui.js",
    "personal/ingolf-lohmann/firefox-assistant/ui.css",
    "runtime/toolchains/TOOLCHAIN.lock.tsv",
    "runtime/toolchains/CACHE_REGISTRY.json",
    "runtime/toolchains/CACHE_COVERAGE.json",
]


class InvalidRun(ValueError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Any) -> None:
    with path.open("xb") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode("utf-8") + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL, timeout=10).strip()


def source_map(task: dict[str, Any]) -> dict[str, str]:
    return {s["id"]: digest(canonical(s)) for s in task["sources"]}


def validate_fixture(task: dict[str, Any]) -> None:
    if task.get("schema") != "qikvrt_browser_ab_fixture_v1" or task.get("synthetic") is not True:
        raise InvalidRun("Only explicitly synthetic, versioned fixtures are accepted")
    ids = [s["id"] for s in task["sources"]]
    if len(ids) != len(set(ids)):
        raise InvalidRun("Duplicate source")
    checkpoint = task["checkpoint"]
    complete, pending = checkpoint["completed_steps"], checkpoint["pending_steps"]
    if len(complete + pending) != len(set(complete + pending)) or set(complete + pending) != set(task["oracle"]):
        raise InvalidRun("Checkpoint must partition all steps")
    if checkpoint["next_step"] not in pending or set(checkpoint["loaded_sources"]) != set(ids):
        raise InvalidRun("Incomplete checkpoint source/next-step binding")
    for criterion in task["oracle"].values():
        required = [criterion["source_id"], *criterion.get("additional_sources", [])]
        if not set(required) <= set(ids):
            raise InvalidRun("Unresolvable oracle citation")


def fixture_binding(task: dict[str, Any]) -> dict[str, Any]:
    return {"task_sha256": digest(canonical(task)), "checkpoint_sha256": digest(canonical(task["checkpoint"])), "sources": source_map(task)}


def preflight() -> dict[str, Any]:
    policy = read_json(ROOT / "policy/QIKVRT_PERSONAL_FIREFOX_CAPABILITY_BOUNDARY_V1.json")
    candidate = policy["personal_release_acceptance"]["current_candidate"]
    firefox = shutil.which("firefox") or shutil.which("firefox-esr")
    browser = {"executable": firefox, "version": None, "executable_sha256": None}
    if firefox:
        result = subprocess.run([firefox, "--version"], capture_output=True, text=True, timeout=10, check=False)
        browser["version"] = result.stdout.strip() if result.returncode == 0 else None
        browser["executable_sha256"] = digest(Path(firefox).resolve().read_bytes())
    manifest_path = ROOT / candidate.get("personal_capability_manifest", "MISSING_CAPABILITIES")
    manifest = read_json(manifest_path) if manifest_path.is_file() else None
    adapter_materialized = bool(manifest and (ROOT / manifest.get("adapter", "MISSING_ADAPTER")).is_file())
    # Source presence and an environment variable are not authenticated execution.
    blockers = [] if adapter_materialized else ["EXECUTABLE_PERSONAL_RESEARCH_ASSISTANT_ADAPTER_NOT_IMPLEMENTED"]
    blockers += ["AUTHENTICATED_PERSONAL_RUNTIME_NOT_ESTABLISHED",
                 "BASELINE_RUNTIME_AND_NORMAL_RETENTION_READBACK_NOT_BOUND",
                 "EQUIVALENT_REAL_PRE_RUNS_NOT_OBSERVED",
                 "PRODUCT_INTERRUPTION_AND_ORACLE_ISOLATION_NOT_BOUND"]
    if not firefox:
        blockers.append("FIREFOX_EXECUTABLE_UNAVAILABLE")
    return {
        "schema": "qikvrt_browser_ab_preflight_v1",
        "observed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repository": "ingolf-lohmann/qik-vrt", "head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"),
        "worktree_dirty": bool(git("status", "--porcelain")),
        "source_files": {p: {"bytes": (ROOT / p).stat().st_size, "sha256": digest((ROOT / p).read_bytes())} for p in SOURCE_PATHS},
        "environment": {"python": platform.python_version(), "os": platform.platform(), "machine": platform.machine(), "firefox": browser},
        "personal_release_candidate": candidate,
        "personal_adapter_source_materialized": adapter_materialized,
        "personal_capability_manifest": manifest,
        "authenticated_runtime_readback": False,
        "baseline_implementation_materialized": bool(manifest and manifest.get("normal_baseline")),
        "baseline_runtime_readback": False,
        "status": "PRODUCT_EXECUTION_NOT_AVAILABLE", "blockers": blockers,
        "product_trials_executed": 0, "product_metrics": None, "product_claim_allowed": False,
        "terminal_boundary": "The optional Personal adapter shares the terminal server and implements source-bound model requests, normal conversation persistence and checkpoint resume. Real authenticated Firefox product execution is not established by this offline preflight.",
    }


def make_plan(output: Path, repeats: int = 6, seed: int = 20261005, evidence_class: str = "HARNESS_PREPARATION") -> dict[str, Any]:
    if repeats < 2 or repeats > 100 or repeats % 2:
        raise InvalidRun("Pairs per task must be even, 2..100, for balanced arm order")
    if evidence_class not in {"HARNESS_PREPARATION", "HARNESS_SELF_TEST"}:
        raise InvalidRun("Product execution is unavailable; evidence class cannot be promoted")
    output = output.resolve()
    if output == ROOT or (ROOT in output.parents and not (ROOT / ".qikvrt/runtime") in output.parents):
        raise InvalidRun("Raw run data must be outside the tracked tree or under .qikvrt/runtime")
    if output.exists():
        raise InvalidRun("Run directory must be new; never overwrite an earlier run")
    contract = read_json(SUITE / "contract.json")
    tasks = {t: read_json(SUITE / "fixtures" / f"{t}.json") for t in contract["fixture_ids"]}
    for task in tasks.values():
        validate_fixture(task)
    rng = random.Random(seed)
    pairs, number = [], 0
    for task_id in contract["fixture_ids"]:
        orders = ["AB", "BA"] * (repeats // 2)
        rng.shuffle(orders)
        for index, order in enumerate(orders):
            number += 1
            pid = f"p{number:03}"
            arms = ["baseline", "qikvrt"] if order == "AB" else ["qikvrt", "baseline"]
            pairs.append({"pair_id": pid, "task_id": task_id, "order": order,
                          "interruption": contract["interruption_classes"][index % 2],
                          "trials": [f"{pid}-{arm}" for arm in arms], "binding": fixture_binding(tasks[task_id])})
    rng.shuffle(pairs)
    output.mkdir(parents=True, mode=0o700)
    (output / "fixtures").mkdir(mode=0o700)
    (output / "events").mkdir(mode=0o700)
    write_json(output / "contract.json", contract)
    for task_id, task in tasks.items():
        write_json(output / "fixtures" / f"{task_id}.json", task)
    manifest = {
        "schema": "qikvrt_browser_ab_run_v1", "evidence_class": evidence_class,
        "product_claim_allowed": False, "seed": seed, "pairs_per_task": repeats,
        "contract_sha256": digest((output / "contract.json").read_bytes()),
        "fixture_files": {t: digest((output / "fixtures" / f"{t}.json").read_bytes()) for t in tasks},
        "preflight": preflight(), "pairs": pairs,
        "execution": "NOT_EXECUTED" if evidence_class == "HARNESS_PREPARATION" else "SYNTHETIC_CLOCK_AND_SCRIPTED_OUTPUTS",
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def load_run(run: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = read_json(run / "manifest.json")
    if manifest.get("schema") != "qikvrt_browser_ab_run_v1" or manifest.get("product_claim_allowed") is not False:
        raise InvalidRun("Unsupported run or product claim")
    if manifest["evidence_class"] not in {"HARNESS_PREPARATION", "HARNESS_SELF_TEST"}:
        raise InvalidRun("Unsupported product evidence class")
    if digest((run / "contract.json").read_bytes()) != manifest["contract_sha256"]:
        raise InvalidRun("Contract digest mismatch")
    contract = read_json(run / "contract.json")
    if contract.get("product_claim_allowed") is not False:
        raise InvalidRun("Contract promoted into product evidence")
    tasks = {}
    for task_id, expected in manifest["fixture_files"].items():
        if task_id not in {"research-costs", "document-recovery"}:
            raise InvalidRun("Unknown fixture")
        path = run / "fixtures" / f"{task_id}.json"
        if digest(path.read_bytes()) != expected:
            raise InvalidRun("Fixture digest mismatch")
        tasks[task_id] = read_json(path)
        validate_fixture(tasks[task_id])
    if set(manifest["preflight"]["source_files"]) != set(SOURCE_PATHS):
        raise InvalidRun("Incomplete harness/runtime source binding")
    for path, expected in manifest["preflight"]["source_files"].items():
        if path not in SOURCE_PATHS or digest((ROOT / path).read_bytes()) != expected["sha256"]:
            raise InvalidRun("Harness/runtime source version mismatch; use the bound checkout")
    ids = set()
    for pair in manifest["pairs"]:
        if pair["binding"] != fixture_binding(tasks[pair["task_id"]]):
            raise InvalidRun("Pair task/checkpoint binding mismatch")
        wanted = [f"{pair['pair_id']}-{a}" for a in (["baseline", "qikvrt"] if pair["order"] == "AB" else ["qikvrt", "baseline"])]
        if pair["order"] not in {"AB", "BA"} or pair["trials"] != wanted or pair["interruption"] not in contract["interruption_classes"]:
            raise InvalidRun("Pair arm/order/interruption mismatch")
        for tid in pair["trials"]:
            if not TRIAL_ID.fullmatch(tid) or tid in ids:
                raise InvalidRun("Invalid/duplicate trial")
            ids.add(tid)
    expected_count = manifest["pairs_per_task"]
    for task_id in tasks:
        subset = [p for p in manifest["pairs"] if p["task_id"] == task_id]
        if len(subset) != expected_count or sum(p["order"] == "AB" for p in subset) * 2 != expected_count:
            raise InvalidRun("Missing or unbalanced planned pairs")
    return manifest, contract, tasks


def pair_for(manifest: dict[str, Any], trial_id: str) -> dict[str, Any]:
    for pair in manifest["pairs"]:
        if trial_id in pair["trials"]:
            return pair
    raise InvalidRun("Unknown trial")


def valid_step(task: dict[str, Any], payload: dict[str, Any]) -> bool:
    criterion = task["oracle"].get(payload.get("step_id"))
    if not criterion or canonical(payload.get("facts")) != canonical(criterion["facts"]):
        return False
    required = [criterion["source_id"], *criterion.get("additional_sources", [])]
    return payload.get("citations") == {s: source_map(task)[s] for s in required}


def correct_probe(task: dict[str, Any]) -> dict[str, Any]:
    binding = fixture_binding(task)
    cp = task["checkpoint"]
    return {**binding, "completed_steps": cp["completed_steps"], "pending_steps": cp["pending_steps"], "next_step": cp["next_step"]}


def evaluate(events: list[dict[str, Any]], task: dict[str, Any], contract: dict[str, Any], pair: dict[str, Any], terminal: bool = True) -> dict[str, Any]:
    phase, resume_at, interrupt_at, resumed_at, completion_at = "NEW", None, None, None, None
    verified = set(task["checkpoint"]["completed_steps"])
    pending = set(task["checkpoint"]["pending_steps"])
    all_steps = set(task["oracle"])
    probe_ok, ended = False, False
    gestures, false_ids = set(), set()
    context_chars = context_bytes = context_messages = false_claims = automatic_bytes = protocol_actions = 0
    for event in events:
        kind, payload, now = event["type"], event["payload"], event["monotonic_ns"]
        if kind not in EVENTS or not isinstance(payload, dict) or ended:
            raise InvalidRun("Unknown event, malformed payload or event after trial_end")
        if kind == "trial_start":
            if phase != "NEW":
                raise InvalidRun("Duplicate/out-of-order trial_start")
            phase = "STARTED"
        elif kind == "checkpoint_readback":
            if phase != "STARTED" or payload != pair["binding"]:
                raise InvalidRun("Checkpoint readback differs from the identical paired fixture")
            phase = "CHECKPOINT"
        elif kind == "interruption_observed":
            if phase != "CHECKPOINT" or payload != {"class": pair["interruption"]}:
                raise InvalidRun("Wrong/unobserved interruption")
            phase, interrupt_at = "INTERRUPTED", now
        elif kind == "resume_signal":
            if phase != "INTERRUPTED" or now - interrupt_at < contract["design"]["interruption_seconds"] * 10**9:
                raise InvalidRun("Resume before matched interruption interval")
            phase, resume_at = "RESUMING", now
        elif kind == "trial_end":
            if phase != "RESUMING" or payload.get("reason") not in {"completed", "timeout", "abort"}:
                raise InvalidRun("Incomplete protocol or unknown end reason")
            elapsed = now - resume_at
            if payload["reason"] == "timeout" and elapsed < contract["design"]["resume_horizon_seconds"] * 10**9:
                raise InvalidRun("Early timeout")
            ended = True
        else:
            if phase != "RESUMING":
                raise InvalidRun("Task/input event outside the observed resume phase")
            within = now - resume_at <= contract["design"]["resume_horizon_seconds"] * 10**9
            if not within:
                raise InvalidRun("Resume horizon exceeded; record trial_end with reason timeout")
            if kind == "resume_probe":
                probe_ok = canonical(payload) == canonical(correct_probe(task))
            elif kind == "step_output":
                step = payload.get("step_id")
                if step not in all_steps:
                    raise InvalidRun("Unknown step output")
                correct = valid_step(task, payload)
                verified.discard(step)
                if correct:
                    verified.add(step)
                if within and correct and step in pending and probe_ok and resumed_at is None:
                    resumed_at = now
                if within and verified == all_steps and completion_at is None:
                    completion_at = now
            elif kind == "step_claim":
                step = payload.get("step_id")
                if step not in all_steps:
                    raise InvalidRun("Unknown step claim")
                if step not in verified:
                    false_claims += 1
                    false_ids.add(step)
            elif kind == "task_claim":
                if verified != all_steps:
                    false_claims += 1
                    false_ids.update(all_steps - verified)
            elif kind == "human_input":
                gesture, text = payload.get("gesture_id"), payload.get("text", "")
                if not isinstance(gesture, str) or not gesture or gesture in gestures or payload.get("kind") not in INPUT_KINDS or not isinstance(text, str):
                    raise InvalidRun("Human gestures must be unique, typed and carry observed text")
                gestures.add(gesture)
                if payload["kind"] == "context_reentry":
                    context_chars += len(text)
                    context_bytes += len(text.encode("utf-8"))
                    context_messages += 1
            elif kind == "automatic_context":
                text = payload.get("text")
                if not isinstance(text, str) or not isinstance(payload.get("origin_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", payload["origin_sha256"]):
                    raise InvalidRun("Automatic context needs separately bound origin and text")
                automatic_bytes += len(text.encode("utf-8"))
        if kind in {"trial_start", "checkpoint_readback", "interruption_observed", "resume_signal", "trial_end"}:
            protocol_actions += 1
    if terminal and not ended:
        raise InvalidRun("No terminal trial_end; incomplete trials are never successful observations")
    elapsed_ns = events[-1]["monotonic_ns"] - resume_at if ended else None
    horizon_ns = contract["design"]["resume_horizon_seconds"] * 10**9
    return {
        "state": "RECORDED_HARNESS_EXERCISE" if ended else "INCOMPLETE",
        "product_claim_allowed": False,
        "reliable_resume_ms": None if resumed_at is None else (resumed_at - resume_at) / 10**6,
        "resume_right_censored": ended and resumed_at is None and elapsed_ns >= horizon_ns,
        "resume_observation_status": "RESUMED" if resumed_at is not None else ("CENSORED_AT_HORIZON" if ended and elapsed_ns >= horizon_ns else "STOPPED_OR_INCOMPLETE_WITHOUT_RESUME"),
        "observation_ms": None if elapsed_ns is None else min(elapsed_ns, horizon_ns) / 10**6,
        "time_to_valid_completion_ms": None if completion_at is None else (completion_at - resume_at) / 10**6,
        "context_reentered_characters": context_chars, "context_reentered_utf8_bytes": context_bytes,
        "context_reentered_messages": context_messages, "automatic_context_utf8_bytes": automatic_bytes,
        "false_completed_step_claims": false_claims, "distinct_false_completed_steps": len(false_ids),
        "human_interventions": len(gestures), "protocol_actions": protocol_actions,
        "task_success": ended and verified == all_steps and completion_at is not None,
        "end_reason": events[-1]["payload"].get("reason") if ended else None,
        "verified_steps_at_end": sorted(verified),
    }


def read_events(run: Path, trial_id: str) -> list[dict[str, Any]]:
    if not TRIAL_ID.fullmatch(trial_id):
        raise InvalidRun("Unsafe trial ID")
    path = run / "events" / f"{trial_id}.jsonl"
    if not path.exists():
        return []
    result, previous, prior_ns, epoch = [], ZERO, -1, None
    manifest_hash = digest((run / "manifest.json").read_bytes())
    evidence_class = read_json(run / "manifest.json")["evidence_class"]
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        frame = json.loads(line)
        claimed = frame.pop("sha256")
        if frame.get("schema") != "qikvrt_browser_ab_event_v1" or claimed != digest(canonical(frame)) or frame["previous_sha256"] != previous or frame["seq"] != index:
            raise InvalidRun("Raw event chain/digest/sequence mismatch")
        if frame["manifest_sha256"] != manifest_hash or frame["trial_id"] != trial_id:
            raise InvalidRun("Event belongs to another manifest or trial")
        if type(frame["monotonic_ns"]) is not int or frame["monotonic_ns"] < prior_ns:
            raise InvalidRun("Invalid/regressed observer clock")
        if epoch is not None and frame["observer_epoch"] != epoch:
            raise InvalidRun("Observer restarted; timing cannot be compared")
        if frame["evidence_class"] != evidence_class:
            raise InvalidRun("Product event class unsupported")
        previous, prior_ns, epoch = claimed, frame["monotonic_ns"], frame["observer_epoch"]
        result.append({**frame, "sha256": claimed})
    return result


class Journal:
    """An independent observer; keep it alive while browser/assistant are interrupted."""
    def __init__(self, run: Path, clock: Callable[[], int] = time.monotonic_ns):
        self.run, self.clock = run, clock
        self.manifest, self.contract, self.tasks = load_run(run)
        self.epoch, self.lock = str(uuid.uuid4()), threading.Lock()
        self.manifest_hash = digest((run / "manifest.json").read_bytes())

    def append(self, trial_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        pair = pair_for(self.manifest, trial_id)
        with self.lock:
            events = read_events(self.run, trial_id)
            if kind == "trial_start":
                ordered = [tid for p in self.manifest["pairs"] for tid in p["trials"]]
                for prior in ordered[:ordered.index(trial_id)]:
                    previous_trial = read_events(self.run, prior)
                    if not previous_trial or previous_trial[-1]["type"] != "trial_end":
                        raise InvalidRun("Preregistered trial order must be preserved, including failed trials")
            if events and events[0]["observer_epoch"] != self.epoch:
                raise InvalidRun("Observer epoch changed; preserve this trial as invalid and create a new run")
            event = {"schema": "qikvrt_browser_ab_event_v1", "seq": len(events) + 1, "trial_id": trial_id, "type": kind, "payload": payload,
                     "monotonic_ns": self.clock(), "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "observer_epoch": self.epoch, "manifest_sha256": self.manifest_hash,
                     "evidence_class": self.manifest["evidence_class"],
                     "previous_sha256": events[-1]["sha256"] if events else ZERO}
            # Validate before appending, including clock monotonicity and protocol.
            if events and event["monotonic_ns"] < events[-1]["monotonic_ns"]:
                raise InvalidRun("Observer clock regressed")
            evaluate(events + [event], self.tasks[pair["task_id"]], self.contract, pair, terminal=False)
            event["sha256"] = digest(canonical(event))
            path = self.run / "events" / f"{trial_id}.jsonl"
            with path.open("ab") as stream:
                stream.write(canonical(event) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            path.chmod(0o600)
            return event


def analyze(run: Path) -> dict[str, Any]:
    manifest, contract, tasks = load_run(run)
    trials, contrasts = [], []
    for pair in manifest["pairs"]:
        pair_rows = {}
        for trial_id in pair["trials"]:
            row = {"trial_id": trial_id, "pair_id": pair["pair_id"], "task_id": pair["task_id"], "arm": trial_id.rsplit("-", 1)[1], "order": pair["order"], "interruption": pair["interruption"]}
            try:
                events = read_events(run, trial_id)
                if not events:
                    row.update(state="NOT_EXECUTED", product_claim_allowed=False)
                else:
                    row.update(evaluate(events, tasks[pair["task_id"]], contract, pair))
                    row["raw_log_sha256"] = digest((run / "events" / f"{trial_id}.jsonl").read_bytes())
                    row["event_chain_tip"] = events[-1]["sha256"]
            except (InvalidRun, KeyError, ValueError, TypeError) as exc:
                row.update(state="INVALID_OR_INCOMPLETE", reason=str(exc), product_claim_allowed=False)
            trials.append(row)
            pair_rows[row["arm"]] = row
        a, b = pair_rows["baseline"], pair_rows["qikvrt"]
        contrast = {"pair_id": pair["pair_id"], "task_id": pair["task_id"], "order": pair["order"], "interruption": pair["interruption"], "sign": "qikvrt_minus_baseline", "product_claim_allowed": False}
        complete = a["state"] == b["state"] == "RECORDED_HARNESS_EXERCISE"
        contrast["state"] = "HARNESS_PAIR_RECORDED" if complete else "NO_VALID_COMPLETE_PAIR"
        for metric in ["reliable_resume_ms", "context_reentered_characters", "false_completed_step_claims", "human_interventions"]:
            contrast[metric] = b.get(metric) - a.get(metric) if complete and a.get(metric) is not None and b.get(metric) is not None else None
        contrast["task_success_baseline"] = a.get("task_success")
        contrast["task_success_qikvrt"] = b.get("task_success")
        contrasts.append(contrast)
    return {
        "schema": "qikvrt_browser_ab_analysis_v1", "evidence_class": manifest["evidence_class"],
        "status": "HARNESS_DATA_ONLY" if any(t["state"] == "RECORDED_HARNESS_EXERCISE" for t in trials) else "PRODUCT_EXECUTION_NOT_PERFORMED",
        "manifest_sha256": digest((run / "manifest.json").read_bytes()),
        "planned_trials": len(trials), "product_trials_executed": 0, "product_claim_allowed": False,
        "product_metrics": None, "trials": trials, "paired_deltas": contrasts,
        "limitations": ["Adapter source does not establish an actual authenticated Firefox product run; this evaluator accepts harness data only.", "No benefit estimate, speedup, significance or causal claim is produced from harness exercises.", "Null latency is not zero; censored failures and invalid/incomplete/missing trials are retained.", "Hash chaining detects accidental/tampered bytes against retained bindings; it is not independent identity attestation or proof that an operator reported honestly."],
    }


def export_analysis(run: Path, output: Path) -> dict[str, Any]:
    result = analyze(run)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    write_json(output / "analysis.json", result)
    keys = sorted({key for row in result["trials"] for key in row})
    with (output / "trials.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for row in result["trials"]:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    (output / "trials.csv").chmod(0o600)
    write_json(output / "paired-deltas.json", result["paired_deltas"])
    return result


def build_server(run: Path, port: int = 0) -> ThreadingHTTPServer:
    journal = Journal(run)
    class Handler(BaseHTTPRequestHandler):
        def respond(self, status: int, data: bytes, mime: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/":
                self.respond(200, (SUITE / "console.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/plan":
                self.respond(200, canonical({"pairs": journal.manifest["pairs"], "evidence_class": journal.manifest["evidence_class"], "product_claim_allowed": False}))
            elif self.path.startswith("/api/task/"):
                try:
                    pair = pair_for(journal.manifest, self.path.removeprefix("/api/task/"))
                    task = journal.tasks[pair["task_id"]]
                    # Never expose the oracle through the participant interface.
                    self.respond(200, canonical({k: v for k, v in task.items() if k != "oracle"}))
                except InvalidRun as exc:
                    self.respond(404, canonical({"error": str(exc)}))
            else:
                self.respond(404, canonical({"error": "Unknown path"}))

        def do_POST(self) -> None:
            try:
                expected_host = f"127.0.0.1:{self.server.server_port}"
                if self.headers.get("Host") != expected_host or self.headers.get("Origin") not in {None, f"http://{expected_host}"}:
                    raise InvalidRun("Only this loopback origin is allowed")
                if self.path != "/api/event" or self.headers.get("Content-Type", "").split(";")[0] != "application/json" or self.headers.get("Transfer-Encoding"):
                    raise InvalidRun("Bounded JSON event endpoint required")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise InvalidRun("Event outside size bound")
                request = json.loads(self.rfile.read(length))
                event = journal.append(request["trial_id"], request["type"], request["payload"])
                self.respond(200, canonical({"recorded": True, "seq": event["seq"], "sha256": event["sha256"], "product_claim_allowed": False}))
            except (InvalidRun, ValueError, KeyError, TypeError) as exc:
                self.respond(400, canonical({"error": str(exc)}))

        def log_message(self, *_: Any) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def terminal_smoke() -> dict[str, Any]:
    """Actual existing HTTP path, no Firefox, no product measurements, no live service."""
    spec = importlib.util.spec_from_file_location("qikvrt_ab_terminal_smoke", ROOT / "src/qikvrt_effect_ack_http_terminal.py")
    assert spec and spec.loader
    terminal = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = terminal
    spec.loader.exec_module(terminal)
    server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    trace = []
    def request(path: str, body: Any = None, field: str | None = None) -> Any:
        headers = {} if body is None else {"Content-Type": "application/json", "Effect-Ack-Request": field}
        req = Request(base + path, data=None if body is None else canonical(body), headers=headers)
        try:
            with urlopen(req, timeout=5) as response:
                status, data = response.status, response.read()
        except HTTPError as exc:
            status, data = exc.code, exc.read()
        trace.append({"path": path, "status": status, "response_sha256": digest(data)})
        return status, json.loads(data)
    try:
        status, capability = request("/.well-known/effect-ack")
        if status != 200 or capability["external_effects"] != "NONE":
            raise InvalidRun("Terminal discovery failed")
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "Synthetic browser A/B harness smoke only", "audio": None, "video": None}
        status, prepared = request("/terminal/prepare", payload, "v=1, mode=prepare")
        if status != 200 or prepared["ordinary_release"] is not False:
            raise InvalidRun("Terminal prepare boundary failed")
        status, record = request(prepared["record_url"])
        record_hash = record.pop("record_hash")
        if status != 200 or record_hash != "sha256:" + prepared["record_hash"] or digest(canonical(record)) != prepared["record_hash"]:
            raise InvalidRun("Terminal full-record readback failed")
        token = ":" + base64.b64encode(prepared["commit_token"].encode("ascii")).decode("ascii") + ":"
        record_bytes = ":" + base64.b64encode(bytes.fromhex(prepared["record_hash"])).decode("ascii") + ":"
        field = f"v=1, mode=commit, token={token}, hash={record_bytes}"
        status, committed = request("/terminal/commit", payload, field)
        if status != 200 or committed["post_effect"]["input_hash"] != digest(canonical(payload)):
            raise InvalidRun("Terminal commit failed")
        status, observed = request("/terminal/state")
        if status != 200 or observed["events"] != 1 or observed["last_event"]["text"] != payload["text"]:
            raise InvalidRun("Terminal fresh readback failed")
        status, _ = request("/terminal/commit", payload, field)
        if status != 409:
            raise InvalidRun("Terminal replay refusal failed")
        return {"schema": "qikvrt_browser_ab_terminal_smoke_v1", "evidence_class": "HTTP_REFERENCE_PATH_TEST",
                "status": "PASS", "source_sha256": digest((ROOT / "src/qikvrt_effect_ack_http_terminal.py").read_bytes()),
                "head": git("rev-parse", "HEAD"), "tree": git("rev-parse", "HEAD^{tree}"), "trace": trace,
                "firefox_executed": False, "research_assistant_executed": False, "product_claim_allowed": False,
                "effect_scope": "One isolated in-memory loopback terminal input, no live service or repository mutation"}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def self_check(output: Path) -> dict[str, Any]:
    """Synthetic clocks and oracle outputs exercise the harness, not the product."""
    make_plan(output, repeats=2, evidence_class="HARNESS_SELF_TEST")
    now = [10**9]
    journal = Journal(output, clock=lambda: now[0])
    for pair in journal.manifest["pairs"]:
        task = journal.tasks[pair["task_id"]]
        for tid in pair["trials"]:
            journal.append(tid, "trial_start", {})
            journal.append(tid, "checkpoint_readback", pair["binding"])
            journal.append(tid, "interruption_observed", {"class": pair["interruption"]})
            now[0] += 60 * 10**9
            journal.append(tid, "resume_signal", {})
            now[0] += 10**9
            journal.append(tid, "human_input", {"gesture_id": tid, "kind": "context_reentry", "text": "synthetisch ä"})
            journal.append(tid, "step_claim", {"step_id": task["checkpoint"]["next_step"]})
            journal.append(tid, "resume_probe", correct_probe(task))
            for step in task["checkpoint"]["pending_steps"]:
                oracle = task["oracle"][step]
                required = [oracle["source_id"], *oracle.get("additional_sources", [])]
                now[0] += 10**9
                journal.append(tid, "step_output", {"step_id": step, "facts": oracle["facts"], "citations": {s: source_map(task)[s] for s in required}})
            journal.append(tid, "task_claim", {})
            journal.append(tid, "trial_end", {"reason": "completed"})
    return analyze(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preflight")
    plan = sub.add_parser("plan")
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--pairs-per-task", type=int, default=6)
    plan.add_argument("--seed", type=int, default=20261005)
    serve = sub.add_parser("serve")
    serve.add_argument("--run", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8782)
    analysis = sub.add_parser("analyze")
    analysis.add_argument("--run", type=Path, required=True)
    analysis.add_argument("--output", type=Path)
    check = sub.add_parser("self-check")
    check.add_argument("--output", type=Path, required=True)
    sub.add_parser("terminal-smoke")
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            result = preflight()
        elif args.command == "plan":
            result = make_plan(args.output, args.pairs_per_task, args.seed)
        elif args.command == "analyze":
            result = export_analysis(args.run, args.output) if args.output else analyze(args.run)
        elif args.command == "self-check":
            result = self_check(args.output)
        elif args.command == "terminal-smoke":
            result = terminal_smoke()
        else:
            server = build_server(args.run, args.port)
            print(json.dumps({"url": f"http://127.0.0.1:{server.server_port}", "status": "HARNESS_CONSOLE_ONLY", "product_claim_allowed": False}), flush=True)
            try:
                server.serve_forever()
            finally:
                server.server_close()
            return 0
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (InvalidRun, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCK", "reason": str(exc), "product_claim_allowed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
