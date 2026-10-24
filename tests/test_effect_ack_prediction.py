#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Precommit a C-model prediction, then compare the existing Python evaluator.

SOFTWARE CONTROL ONLY: no actuator, external randomness prediction, independent
institution, trusted external time service, or production effect is claimed.
"""
from __future__ import annotations

import collections
import concurrent.futures
import copy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from qikvrt_effect_ack import (  # noqa: E402
    ConnectionDecision, EffectAckEngine, EffectAckRequest, RiskLevel,
    canonical_json, sha256_identifier,
)
from qikvrt_temdd_event_ledger import Ledger, SCHEMA, utc  # noqa: E402
import qikvrt_effect_ack_http_terminal as terminal  # noqa: E402

CASE_COUNT = 10248
PROFILE = "qikvrt-effect-ack-c90-python-prediction-v1"
SOURCES = ("src/effect_ack_core.c", "include/qikvrt/effect_ack.h",
           "src/qikvrt_effect_ack.py", "src/qikvrt_temdd_event_ledger.py",
           "src/qikvrt_effect_ack_http_terminal.py",
           "tests/effect_ack_prediction_oracle.c", "tests/test_effect_ack_prediction.py",
           "tests/effect_ack_prediction_m68000.S",
           "formalization/prediction-control/QIKVRTEffectAck/PredictionProfile.lean",
           "runtime/toolchains/M68000_PROOF_POC_LOCK.json")
STATE_NAMES = ("EFFECT_NACK", "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE", "EFFECT_ACK_ISOLATE", "EFFECT_ACK_BLOCK")
CONDITIONS = {
    "profile": PROFILE,
    "case_count": CASE_COUNT,
    "observable": ["case_id", "state", "ordinary_release"],
    "binary_product": "256 masks * 5 decisions * 2 transport * 2 reception * 2 deadline",
    "mask_bits": ["origin_checked", "context_checked", "semantics_reconstructed",
                  "effect_anticipated", "risk_classified", "responsibility_assigned",
                  "policy_allows_release", "risk_known"],
    "one_fault_cases": ["owner_missing", "open_question", "next_check", "missing_evidence",
                        "wrong_hash", "oversized_payload", "missing_root", "malformed_hash"],
    "max_payload_bytes": 16,
    "clock": "CONTROLLED_CONSTANT_ZERO_NS; timeout_ms is 0 or 100",
    "predecessor": "NONE; protocol version 1",
    "created_utc": "2000-01-01T00:00:00Z; FIXTURE_METADATA_NOT_TIME_EVIDENCE",
    "scope": "STATE_AND_RELEASE_DECISION_IN_FINITE_SOFTWARE_PROFILE",
    "shared_host": True,
    "independent_organization": False,
    "external_timestamp_verified": False,
    "physical_effect_verified": False,
    "unknown_future_input_prediction": False,
    "native_build": "HOST_TARGET_FROM_CC_DUMPMACHINE; C90 O0 MODEL THEN C90 O2 EXECUTION",
    "optional_emulation": "M68000_LINUX_USER_AND_LEAN_4_19_KERNEL; ONLY_WHEN_EXPLICITLY_SELECTED",
}


def encoded(value):
    return canonical_json(value).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_rows(raw):
    """Reject missing, duplicated, reordered or incorrectly typed observations."""
    rows = []
    names = {"EFFECT_NACK", "EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE",
             "EFFECT_ACK_ISOLATE", "EFFECT_ACK_BLOCK"}
    for index, line in enumerate(raw.decode("ascii").splitlines()):
        parts = line.split(" ")
        if len(parts) != 3 or parts[0] != str(index) or parts[1] not in names or parts[2] not in ("0", "1"):
            raise ValueError("COMPLETE_ORDERED_PROFILE_REQUIRED")
        if (parts[2] == "1") != (parts[1] == "EFFECT_ACK_DONE"):
            raise ValueError("STATE_RELEASE_DISAGREEMENT")
        rows.append(parts)
    if len(rows) != CASE_COUNT:
        raise ValueError("COMPLETE_ORDERED_PROFILE_REQUIRED")
    return rows


def audit(expected, observed, commitment, trusted_sha256, before, after, *, native_observed, emulated_observed=None):
    """The caller supplies the earlier anchor, never a digest from the outcome."""
    if digest(encoded(commitment)) != trusted_sha256:
        raise ValueError("COMMITMENT_ANCHOR_MISMATCH")
    if (set(commitment) != {"conditions", "expected_sha256", "sources", "subject", "build"} or
            commitment.get("conditions") != CONDITIONS or
            commitment.get("expected_sha256") != digest(expected)):
        raise ValueError("PREDICTION_BINDING_MISMATCH")
    if before.get("kind") != "OBSERVE" or after.get("kind") != "EFFECT":
        raise ValueError("NATIVE_ORDER_EVIDENCE_REQUIRED")
    if (before.get("subject") != after.get("subject") or
            before.get("subject") != commitment["subject"] or
            before.get("payload") != commitment or
            after.get("payload", {}).get("commitment_sha256") != trusted_sha256 or
            after.get("payload", {}).get("observed_sha256") != digest(observed) or
            after.get("payload", {}).get("native_observed_sha256") != digest(native_observed)):
        raise ValueError("NATIVE_BINDING_MISMATCH")
    # Each event is independently rehashed, including the subject and payload.
    for event in (before, after):
        body = {k: v for k, v in event.items() if k not in ("id", "ledger_digest")}
        if (digest(terminal.canonical_json(body)) != event.get("ledger_digest") or
                digest(terminal.canonical_json(body["payload"])) != body.get("payload_digest")):
            raise ValueError("NATIVE_EVENT_DIGEST_MISMATCH")
    try:
        epoch_a, seq_a = before["id"].split(":")
        epoch_b, seq_b = after["id"].split(":")
        ordered = (epoch_a == epoch_b and re.fullmatch(r"[0-9a-f]{32}", epoch_a) is not None
                   and re.fullmatch(r"[1-9][0-9]*", seq_a) is not None
                   and re.fullmatch(r"[1-9][0-9]*", seq_b) is not None
                   and int(seq_a) < int(seq_b))
    except (KeyError, ValueError, TypeError):
        ordered = False
    if not ordered:
        raise ValueError("PREDICTION_MUST_PRECEDE_EXECUTION")
    expected_rows, observed_rows = read_rows(expected), read_rows(observed)
    if expected_rows != observed_rows or expected_rows != read_rows(native_observed):
        raise ValueError("PREDICTION_MISMATCH")
    if commitment["build"].get("m68000") is not None:
        if emulated_observed is None:
            raise ValueError("EMULATED_EXECUTION_REQUIRED")
        if after["payload"].get("m68000_observed_sha256") != digest(emulated_observed):
            raise ValueError("EMULATED_BINDING_MISMATCH")
        if emulated_observed != bytes(STATE_NAMES.index(row[1]) for row in expected_rows):
            raise ValueError("EMULATED_PREDICTION_MISMATCH")
    return {"status": "PASS_BOUNDED_DETERMINISTIC_PREDICTION",
            "case_count": CASE_COUNT, "matches": CASE_COUNT,
            "states": dict(collections.Counter(row[1] for row in observed_rows)),
            "commitment_sha256": trusted_sha256,
            "expected_sha256": digest(expected), "observed_sha256": digest(observed),
            "native_observed_sha256": digest(native_observed), "build": commitment["build"],
            "m68000_execution_verified": emulated_observed is not None,
            "conditions": CONDITIONS, "effect_ack_done": False,
            "proof_class": "CROSS_IMPLEMENTATION_SOFTWARE_TEST_NOT_FORMAL_PROOF"}


def cases():
    evidence = sha256_identifier(b"bounded-software-fixture-evidence")
    decisions = list(ConnectionDecision)
    for mask, decision, transport, reception, deadline in itertools.product(range(256), range(5), range(2), range(2), range(2)):
        value = {"protocol_root_id": "qikvrt:prediction:fixture", "input_id": "fixture-input",
                 "payload": b"prediction" if reception else None, "transport_ack": bool(transport),
                 "responsibility_owner": "FIXTURE_OWNER_NOT_IDENTITY_PROOF",
                 "connection_decision": decisions[decision], "risk_level": RiskLevel.LOW if mask & 128 else RiskLevel.UNKNOWN,
                 "evidence_refs": (evidence,), "required_evidence_refs": (evidence,)}
        for bit, key in enumerate(CONDITIONS["mask_bits"][:-1]):
            value[key] = bool(mask & (1 << bit))
        yield value, 0 if deadline else 100
    complete = {"protocol_root_id": "qikvrt:prediction:fixture", "input_id": "fixture-input",
                "payload": b"prediction", "transport_ack": True, "risk_level": RiskLevel.LOW,
                "responsibility_owner": "FIXTURE_OWNER_NOT_IDENTITY_PROOF",
                "connection_decision": ConnectionDecision.RELEASE,
                "evidence_refs": (evidence,), "required_evidence_refs": (evidence,)}
    complete.update({k: True for k in CONDITIONS["mask_bits"][:-1]})
    for change in ({"responsibility_owner": ""}, {"open_questions": ("unresolved",)},
                   {"next_required_checks": ("unperformed",)}, {"evidence_refs": ()},
                   {"declared_input_hash": "sha256:" + "0" * 64}, {"payload": b"x" * 17},
                   {"protocol_root_id": ""}, {"declared_input_hash": "invalid"}):
        yield {**complete, **change}, 100


def emulated_tools_from_environment():
    names = ("QIKVRT_M68000_CC", "QIKVRT_M68000_QEMU", "QIKVRT_PROOF_LEAN", "QIKVRT_PROOF_LAKE")
    if any(not os.environ.get(name) for name in names):
        raise ValueError("EXPLICIT_EMULATOR_AND_KERNEL_TOOL_BINDINGS_REQUIRED")
    tools = dict(zip(("compiler", "emulator", "lean", "lake"), (shlex.split(os.environ[name]) for name in names)))
    locked = json.loads((ROOT / "runtime/toolchains/M68000_PROOF_POC_LOCK.json").read_text())["executables"]
    for name, position, lock_name in (("compiler", 0, "compiler"), ("emulator", 0, "m68000_emulator"),
                                      ("lean", -1, "lean"), ("lake", -1, "lake")):
        path = shutil.which(tools[name][position])
        if path is None or digest(Path(path).read_bytes()) != locked[lock_name]["sha256"]:
            raise ValueError("PINNED_PROOF_TOOL_MISMATCH: " + name)
    for name in ("lean", "lake"):
        if len(tools[name]) > 1:
            runner = shutil.which(tools[name][0])
            if runner is None or digest(Path(runner).read_bytes()) != locked["lean_runner"]["sha256"]:
                raise ValueError("PINNED_LEAN_RUNNER_MISMATCH")
    return tools


def check_lean_observation(output, observed, tools):
    """Kernel-check the actual observed bytes against the existing Lean model."""
    project = ROOT / "formalization/QIKVRT_Formalization_v2.0"
    build = project / ".lake/build/lib/lean/QIKVRTEffectAck"
    build.mkdir(parents=True, exist_ok=True)
    logs = []
    def check(arguments, name):
        result = subprocess.run([*tools["lake"], "env", *tools["lean"], *arguments], cwd=project,
                                capture_output=True, timeout=300)
        raw = result.stdout + result.stderr
        (output / name).write_bytes(raw)
        logs.append({"name": name, "exit_code": result.returncode, "sha256": digest(raw)})
        if result.returncode:
            raise ValueError("LEAN_KERNEL_CHECK_FAILED: " + raw.decode(errors="replace")[-3000:])
        return raw
    check(["-o", str(build / "Model.olean"), "QIKVRTEffectAck/Model.lean"], "lean-model.log")
    extension = ROOT / "formalization/prediction-control"
    check(["--root=" + str(extension), "-o", str(build / "PredictionProfile.olean"),
           str(extension / "QIKVRTEffectAck/PredictionProfile.lean")], "lean-profile.log")
    def source(values, namespace, first_batch=0):
        batches = [values[start:start + 40] for start in range(0, len(values), 40)]
        return ("import QIKVRTEffectAck.PredictionProfile\n"
                "set_option maxRecDepth 100000\nset_option maxHeartbeats 0\n"
                f"namespace {namespace}\n"
                "open QIKVRT.EffectAck.V1.PredictionProfile\n"
                + "".join(f"def observed{index + first_batch} : List Nat := [" + ",".join(map(str, batch)) + "]\n"
                          + f"theorem agreesBatch{index + first_batch} : observed{index + first_batch} = expectedBatchCodes ⟨{index + first_batch}, by decide⟩ := by rfl\n"
                          + f"#print axioms agreesBatch{index + first_batch}\n" for index, batch in enumerate(batches))
                + f"end {namespace}\n")
    proofs = []
    for first in range(0, len(observed), 2560):
        proof = output / f"Observation-{first // 40:03d}.lean"
        proof.write_text(source(observed[first:first + 2560], f"QIKVRTPredictionObservation{first // 40}", first // 40))
        proofs.append(proof)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as workers:
        checked = list(workers.map(lambda proof: check([str(proof)], proof.stem + ".log"), proofs))
    raw = b"".join(checked)
    if raw.count(b"does not depend on any axioms") != 257:
        raise ValueError("LEAN_AXIOM_AUDIT_MISSING")
    changed = bytearray(observed[:40]); changed[0] = (changed[0] + 1) % 5
    negative = output / "RejectedObservation.lean"
    negative.write_text(source(changed, "QIKVRTPredictionNegative"))
    result = subprocess.run([*tools["lake"], "env", *tools["lean"], str(negative)], cwd=project,
                            capture_output=True, timeout=300)
    negative_log = result.stdout + result.stderr
    (output / "lean-negative.log").write_bytes(negative_log)
    if not result.returncode or not any(tactic in negative_log for tactic in (b"decide", b"rfl")):
        raise ValueError("LEAN_NEGATIVE_CONTROL_NOT_REJECTED_BY_PROOF")
    return {"status": "KERNEL_CHECKED_FINITE_OBSERVATION_EQUALITY", "axioms": [],
            "batch_theorem_count": 257,
            "lean_version": subprocess.check_output([*tools["lean"], "--version"], timeout=30).decode().strip(),
            "proof_sources": [{"path": proof.name, "sha256": digest(proof.read_bytes())} for proof in proofs],
            "observed_sha256": digest(observed),
            "negative_control_rejected": True, "negative_log_sha256": digest(negative_log), "logs": sorted(logs, key=lambda row: row["name"]),
            "compiler_correctness_proved": False, "emulator_correctness_proved": False}


def run_profile(output, *, exact_subject=None, emulated_tools=None):
    """Run the existing native APIs; the default subject is explicitly a fixture."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    subject = exact_subject or {"repository": "fixture/local", "pr": 1, "head": "0" * 40, "tree": "0" * 40}
    compiler = shlex.split(os.environ.get("CC", "cc"))
    flags = ["-std=c90", "-pedantic", "-Wall", "-Wextra", "-Werror"]
    binary, native_binary = output / "prediction-oracle", output / "prediction-native"
    for target, optimization in ((binary, "-O0"), (native_binary, "-O2")):
        subprocess.run([*compiler, *flags, optimization, "-I" + str(ROOT / "include"),
                        str(ROOT / "src/effect_ack_core.c"), str(ROOT / "tests/effect_ack_prediction_oracle.c"),
                        "-o", str(target)], check=True, timeout=60)
    version = subprocess.check_output([*compiler, "--version"], timeout=10).decode().splitlines()[0]
    target = subprocess.check_output([*compiler, "-dumpmachine"], timeout=10).decode().strip()
    build = {"compiler": compiler, "compiler_version": version, "target_triple": target,
             "model_flags": flags + ["-O0"], "native_flags": flags + ["-O2"],
             "model_binary_sha256": digest(binary.read_bytes()),
             "native_binary_sha256": digest(native_binary.read_bytes()),
             "abi": "NATIVE_COMPILER_ABI_NO_C_STRUCT_WIRE_SERIALIZATION",
             "m68000_execution_verified": False}
    if emulated_tools is not None:
        guest = output / "prediction-m68000.elf"
        guest_flags = flags + ["-O2", "-m68000", "-msoft-float", "-ffreestanding", "-fno-builtin",
                              "-fno-tree-loop-distribute-patterns", "-fno-stack-protector", "-fno-pie", "-nostdlib", "-static",
                              "-DQIKVRT_PREDICTION_FREESTANDING", "-Wl,--build-id=none", "-Wl,-e,_start", "-Wl,-Ttext=0x10000"]
        subprocess.run([*emulated_tools["compiler"], *guest_flags, "-I" + str(ROOT / "include"),
                        str(ROOT / "src/effect_ack_core.c"), str(ROOT / "tests/effect_ack_prediction_oracle.c"),
                        str(ROOT / "tests/effect_ack_prediction_m68000.S"), "-o", str(guest)], check=True, timeout=60)
        build["m68000"] = {"compiler": emulated_tools["compiler"], "flags": guest_flags,
                           "compiler_version": subprocess.check_output([*emulated_tools["compiler"], "--version"], timeout=30).decode().splitlines()[0],
                           "emulator": emulated_tools["emulator"], "cpu": "m68000", "binary_sha256": digest(guest.read_bytes()),
                           "emulator_version": subprocess.check_output([*emulated_tools["emulator"], "--version"], timeout=30).decode().splitlines()[0],
                           "lean": emulated_tools["lean"], "lake": emulated_tools["lake"]}
    expected = subprocess.check_output([str(binary)], timeout=30)
    read_rows(expected)
    with (output / "expected.txt").open("xb") as stream:
        stream.write(expected)
        stream.flush()
        os.fsync(stream.fileno())
    if (output / "expected.txt").read_bytes() != expected:
        raise ValueError("PREDICTION_FILE_READBACK_MISMATCH")
    commitment = {"conditions": CONDITIONS, "expected_sha256": digest(expected), "subject": subject, "build": build,
                  "sources": {p: digest((ROOT / p).read_bytes()) for p in SOURCES}}
    anchor = digest(encoded(commitment))
    (output / "commitment.json").write_bytes(encoded(commitment) + b"\n")
    ledger = Ledger(output / "native", subject)
    def record(kind, name, payload):
        event = {"schema": SCHEMA, "kind": kind, "subject": subject,
                 "provenance": {"source": "transputer", "native_event_id": "prediction:" + name},
                 "observed_at": utc(), "message": "Bounded software prediction control: " + name, "payload": payload}
        written = ledger.append(event)
        _, readback = terminal._durable_read(str(output / "native"), event)
        if readback != written:
            raise ValueError("INDEPENDENT_TERMINAL_READBACK_MISMATCH")
        return readback
    try:
        before = record("OBSERVE", "commit-before-execution", commitment)
        native_start_ns = time.monotonic_ns()
        native_observed = subprocess.check_output([str(native_binary)], timeout=30)
        native_elapsed_ns = time.monotonic_ns() - native_start_ns
        emulated_observed = None
        if emulated_tools is not None:
            emulated_observed = subprocess.check_output([*emulated_tools["emulator"], "-cpu", "m68000", str(guest)], timeout=60)
            (output / "m68000-observed.bin").write_bytes(emulated_observed)
        started_ns = time.monotonic_ns()
        engine = EffectAckEngine(max_payload_bytes=16, clock_ns=lambda: 0)
        lines = []
        for case_id, (value, timeout) in enumerate(cases()):
            result = engine.evaluate(EffectAckRequest(**value), timeout_ms=timeout, created_utc=CONDITIONS["created_utc"].split(";")[0])
            lines.append(f"{case_id} {result.state.value} {int(result.ordinary_release)}\n")
        observed = "".join(lines).encode("ascii")
        finished_ns = time.monotonic_ns()
        after = record("EFFECT", "observed-after-execution", {"commitment_sha256": anchor,
                       "observed_sha256": digest(observed), "native_observed_sha256": digest(native_observed),
                       "m68000_observed_sha256": digest(emulated_observed) if emulated_observed is not None else None})
        report = audit(expected, observed, commitment, anchor, before, after, native_observed=native_observed,
                       emulated_observed=emulated_observed)
        if emulated_observed is not None:
            report["kernel_receipt"] = check_lean_observation(output, emulated_observed, emulated_tools)
        report.update({"subject": subject, "subject_is_fixture": exact_subject is None,
                       "executor_elapsed_ns": finished_ns - started_ns,
                       "native_process_elapsed_ns": native_elapsed_ns,
                       "timing_scope": "DIFFERENT_ADAPTER_WORKLOADS_AND_PROCESS_OVERHEAD; NOT_A_KERNEL_SPEEDUP_BENCHMARK",
                       "commit_event_id": before["id"], "effect_event_id": after["id"],
                       "terminal_readback": "SEPARATE_READ_ONLY_SQLITE_CONNECTION_ON_SAME_HOST"})
        record("READBACK", "audit", {"report_sha256": digest(encoded(report)), "effect_ack_done": False})
        for name, value in (("observed.txt", observed), ("native-observed.txt", native_observed), ("before.json", encoded(before)), ("after.json", encoded(after)), ("report.json", encoded(report))):
            (output / name).write_bytes(value)
        return expected, observed, commitment, anchor, before, after, report, native_observed
    finally:
        ledger.close()


class DeterministicPredictionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="qikvrt-prediction-")
        cls.bundle = run_profile(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def check(self, **changes):
        args = dict(zip(("expected", "observed", "commitment", "trusted_sha256", "before", "after"), copy.deepcopy(self.bundle[:6])))
        args.update(changes)
        args.setdefault("native_observed", self.bundle[7])
        return audit(**args)

    def test_c_prediction_precedes_and_matches_all_python_cases(self):
        report = self.check()
        self.assertEqual(report["matches"], CASE_COUNT)
        self.assertEqual(len(report["states"]), 5)
        self.assertFalse(report["effect_ack_done"])

    def test_changed_prediction_fails_against_original_anchor(self):
        value = copy.deepcopy(self.bundle[2]); value["expected_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "COMMITMENT_ANCHOR_MISMATCH"):
            self.check(commitment=value)

    def test_missing_or_postselected_cases_are_rejected(self):
        expected = self.bundle[0]
        for changed in (b"", b"\n".join(expected.splitlines()[:-1]) + b"\n", expected + expected.splitlines()[0] + b"\n"):
            with self.subTest(size=len(changed)), self.assertRaises(ValueError):
                read_rows(changed)

    def test_changed_or_reordered_result_is_rejected(self):
        rows = self.bundle[1].splitlines(keepends=True)
        for value in (rows[1] + rows[0] + b"".join(rows[2:]), self.bundle[1].replace(b"EFFECT_NACK 0", b"EFFECT_ACK_DONE 0", 1)):
            with self.assertRaises(ValueError):
                self.check(observed=value)

    def test_validly_recorded_wrong_execution_is_still_a_prediction_mismatch(self):
        observed = self.bundle[1].replace(b"EFFECT_NACK 0", b"EFFECT_ACK_BLOCK 0", 1)
        after = copy.deepcopy(self.bundle[5])
        after["payload"]["observed_sha256"] = digest(observed)
        after["payload_digest"] = digest(terminal.canonical_json(after["payload"]))
        after["ledger_digest"] = digest(terminal.canonical_json({k: v for k, v in after.items() if k not in ("id", "ledger_digest")}))
        with self.assertRaisesRegex(ValueError, "PREDICTION_MISMATCH"):
            self.check(observed=observed, after=after)

    def test_foreign_native_subject_is_rejected(self):
        after = copy.deepcopy(self.bundle[5]); after["subject"]["head"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "NATIVE_BINDING_MISMATCH"):
            self.check(after=after)

    def test_late_commitment_fails_sequence_check(self):
        before = copy.deepcopy(self.bundle[4]); before["id"] = self.bundle[5]["id"]
        with self.assertRaisesRegex(ValueError, "PREDICTION_MUST_PRECEDE_EXECUTION"):
            self.check(before=before)

    def test_tampered_native_event_is_rejected(self):
        after = copy.deepcopy(self.bundle[5]); after["message"] = "changed"
        with self.assertRaisesRegex(ValueError, "NATIVE_EVENT_DIGEST_MISMATCH"):
            self.check(after=after)

    def test_changed_conditions_are_not_accepted_as_same_prediction(self):
        commitment = copy.deepcopy(self.bundle[2]); commitment["conditions"]["max_payload_bytes"] = 32
        with self.assertRaisesRegex(ValueError, "PREDICTION_BINDING_MISMATCH"):
            self.check(commitment=commitment, trusted_sha256=digest(encoded(commitment)))

    def test_optimized_native_mismatch_cannot_be_hidden_by_python_match(self):
        observed = self.bundle[7].replace(b"EFFECT_NACK 0", b"EFFECT_ACK_BLOCK 0", 1)
        after = copy.deepcopy(self.bundle[5])
        after["payload"]["native_observed_sha256"] = digest(observed)
        after["payload_digest"] = digest(terminal.canonical_json(after["payload"]))
        after["ledger_digest"] = digest(terminal.canonical_json({k: v for k, v in after.items() if k not in ("id", "ledger_digest")}))
        with self.assertRaisesRegex(ValueError, "PREDICTION_MISMATCH"):
            self.check(native_observed=observed, after=after)


@unittest.skipUnless(os.environ.get("QIKVRT_EMULATED_PROOF") == "1", "Explicit pinned M68000/QEMU/Lean tool profile is not selected")
class EmulatedPredictionTests(unittest.TestCase):
    def test_m68000_observation_and_lean_kernel_agree_with_precommitted_profile(self):
        with tempfile.TemporaryDirectory(prefix="qikvrt-m68000-proof-") as output:
            result = run_profile(output, emulated_tools=emulated_tools_from_environment())
            report = result[6]
            self.assertTrue(report["m68000_execution_verified"])
            self.assertEqual(report["matches"], CASE_COUNT)
            self.assertEqual(report["kernel_receipt"]["axioms"], [])
            self.assertTrue(report["kernel_receipt"]["negative_control_rejected"])


if __name__ == "__main__":
    unittest.main()
