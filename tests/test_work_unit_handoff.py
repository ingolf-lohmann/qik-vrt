#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Real-process Mesh adapter controls; no ChatGPT/iOS witness is inferred."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from qikvrt_api_handler import HandlerConfig, run_handler, validate_audit_chain, work_unit_fence_name
from tests import test_tcpip_e2e as tcpip_fixture


class WorkUnitHandoffTests(unittest.TestCase):
    request = tcpip_fixture.TcpIpEndToEndTests.request
    _wait_until_ready = tcpip_fixture.TcpIpEndToEndTests._wait_until_ready
    tearDown = tcpip_fixture.TcpIpEndToEndTests.tearDown
    unit = "CONTINUITY_CONTROL"

    def setUp(self) -> None:
        tcpip_fixture.TcpIpEndToEndTests.setUp(self)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Control fixture")
        self.git("config", "user.email", "control@example.invalid")
        (self.state / ".gitignore").write_text(".qikvrt/\n")
        (self.state / "src").mkdir()
        for name in ("qikvrt_api_handler.py", "qikvrt_github_api_shim.py", "qikvrt_effect_ack.py"):
            (self.state / "src" / name).write_bytes((ROOT / "src" / name).read_bytes())
        path = self.state / "state/work_units" / f"{self.unit}.json"
        path.parent.mkdir(parents=True)
        self.raw = (json.dumps({"work_unit_id": self.unit,
                               "purpose": "Retain this exact authorized work-unit snapshot"}) + "\n").encode()
        path.write_bytes(self.raw)
        self.git("add", ".gitignore", "state", "src")
        self.git("commit", "-qm", "bound control work unit")
        self.head = self.git("rev-parse", "HEAD")
        self.tree = self.git("rev-parse", "HEAD^{tree}")
        self.sequence = 0

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.state), *args],
                                       stderr=subprocess.DEVNULL, text=True).strip()

    def inputs(self, operation: str, *, payload: dict | None = None,
               request_id: str | None = None, unit: str | None = None) -> dict:
        self.sequence += 1
        return {"operation": operation, "artifact_id": unit or self.unit,
                "payload_b64": base64.b64encode(json.dumps(payload).encode()).decode() if payload else "",
                "expected_sha256": hashlib.sha256(self.raw).hexdigest(),
                "dry_run": operation == "work_unit_status",
                "effect_accepted": operation != "work_unit_status",
                "request_id": request_id or f"control-{self.sequence}"}

    def call(self, inputs: dict) -> tuple[int, dict]:
        return self.request("POST", "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches",
                            {"ref": "main", "inputs": inputs})

    def handoff(self) -> dict:
        return self.inputs("work_unit_handoff", request_id="same-handoff", payload={
            "schema": "qikvrt_work_unit_handoff_v1", "work_unit_id": self.unit,
            "subject": {"head": self.head, "tree": self.tree, "ref": "refs/heads/main"}})

    def status(self) -> dict:
        code, body = self.call(self.inputs("work_unit_status"))
        self.assertEqual(code, 202, body)
        return body["handler_result"]

    def wait_state(self, state: str) -> dict:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            result = self.status()
            if result["state"] == state:
                return result
            time.sleep(0.03)
        self.fail(f"expected {state}, last status: {result}")

    def event(self, kind: str, *, request_id: str | None = None, evidence: bytes = b"control evidence") -> dict:
        values = self.inputs("work_unit_event", request_id=request_id,
                             payload={"kind": kind, "evidence_sha256": hashlib.sha256(evidence).hexdigest()})
        code, body = self.call(values)
        self.assertEqual(code, 202, body)
        return body["handler_result"]

    def admit(self) -> tuple[dict, dict]:
        handoff = self.handoff()
        code, body = self.call(handoff)
        self.assertEqual(code, 202, body)
        admitted = self.wait_state("WAITING_CLIENT_EVENT")
        self.assertEqual(admitted["executor"]["pid"], self.server.pid)
        self.assertTrue(admitted["writer_fence_held"])
        self.assertFalse(admitted["ordinary_release"])
        return handoff, admitted

    def journal(self) -> list[dict]:
        path = self.state / ".qikvrt/api/audit/events.jsonl"
        validate_audit_chain(path)
        return [json.loads(line) for line in path.read_text().splitlines()]

    def test_question_real_client_kill_effect_and_replay(self) -> None:
        handoff, admitted = self.admit()
        # A separate interactive client asks and reads the actual status.
        client_code = '''import json, os, sys, urllib.request, time
req=urllib.request.Request(os.environ["CONTROL_URL"], data=os.environ["CONTROL_BODY"].encode(),
 headers={"Content-Type":"application/json","Authorization":"Bearer "+os.environ["QIKVRT_API_TOKEN"]})
with urllib.request.urlopen(req,timeout=5) as response: answer=json.loads(response.read())
print(json.dumps({"question":"Which exact work unit is admitted?","answer":answer,"pid":os.getpid()}),flush=True)
sys.stdin.read()
'''
        env = os.environ.copy()
        env.update(CONTROL_URL=f"http://127.0.0.1:{self.port}/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches",
                   CONTROL_BODY=json.dumps({"ref": "main", "inputs": self.inputs("work_unit_status")}),
                   QIKVRT_API_TOKEN=self.token)
        client = subprocess.Popen([sys.executable, "-c", client_code], env=env,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            trace = json.loads(client.stdout.readline())
            self.assertEqual(trace["answer"]["handler_result"]["executor"]["run_id"], admitted["executor"]["run_id"])
            self.event("QUESTION_ANSWERED", evidence=json.dumps(trace, sort_keys=True).encode())
            client.kill()
            self.assertEqual(client.wait(timeout=5), -9)
            self.assertIsNone(self.server.poll())
            self.event("CLIENT_DISCONNECT_REPORTED",
                       evidence=json.dumps({"client_pid": client.pid, "returncode": client.returncode}).encode())
        finally:
            if client.poll() is None:
                client.kill()
            client.communicate(timeout=5)
        result = self.wait_state("COMPLETED")
        self.assertTrue(result["effect_readback_verified"])
        self.assertEqual(result["executor"]["run_id"], admitted["executor"]["run_id"])
        target = self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin"
        self.assertEqual(target.read_bytes(), self.raw)
        before = target.stat()
        self.assertEqual(self.call(handoff)[0], 202)  # reconciled handoff replay
        after = target.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        writes = [x for x in self.journal() if x.get("event") == "request_result"
                  and x.get("operation") == "ingest" and x.get("write_status") == "WRITTEN"
                  and not x.get("replayed")]
        self.assertEqual(len(writes), 1)
        self.assertIsNone(result["owner_manual_restart_count"])
        self.assertIsNone(result["duplicate_effect_count"])
        self.assertFalse(result["productive_continuity_verified"])
        self.assertFalse(result["client_behavior_changed"])

    def test_explicit_cancel_prevents_effect(self) -> None:
        self.admit()
        self.event("QUESTION_ANSWERED")
        self.event("EXPLICIT_CANCEL", request_id="cancel-once")
        self.event("EXPLICIT_CANCEL", request_id="cancel-once")  # same event is reconciled
        self.assertEqual(self.status()["state"], "CANCELLED")
        self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").exists())
        code, _ = self.call(self.inputs("work_unit_event", payload={
            "kind": "CLIENT_DISCONNECT_REPORTED", "evidence_sha256": "a" * 64}))
        self.assertEqual(code, 409)

    def test_head_and_dirty_subject_drift_prevent_effect(self) -> None:
        self.admit()
        self.event("QUESTION_ANSWERED")
        self.git("commit", "--allow-empty", "-qm", "actual subject drift")
        self.event("CLIENT_DISCONNECT_REPORTED")
        blocked = self.wait_state("BLOCKED")
        self.assertIn("SUBJECT_DRIFT", blocked["blocking_reason"])
        self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").exists())

    def test_dirty_checkout_prevents_effect(self) -> None:
        self.admit()
        self.event("QUESTION_ANSWERED")
        path = self.state / "src/qikvrt_api_handler.py"
        path.write_bytes(path.read_bytes() + b"\n# actual tracked-byte drift\n")
        self.event("CLIENT_DISCONNECT_REPORTED")
        blocked = self.wait_state("BLOCKED")
        self.assertIn("SUBJECT_DRIFT", blocked["blocking_reason"])
        self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").exists())

    def test_competing_process_fence_prevents_admission(self) -> None:
        holder_code = '''import fcntl, os, sys
fd=os.open(sys.argv[1], os.O_CREAT|os.O_RDWR, 0o600)
fcntl.flock(fd,fcntl.LOCK_EX)
print("held",flush=True)
sys.stdin.read()
'''
        fence = self.state / ".qikvrt/api" / work_unit_fence_name(self.unit)
        holder = subprocess.Popen([sys.executable, "-c", holder_code, str(fence)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            self.assertEqual(self.call(self.handoff())[0], 202)
            blocked = self.wait_state("HOLD_COMPETING_WRITER")
            self.assertEqual(blocked["blocking_reason"], "WORK_UNIT_COMPETING_WRITER")
            self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").exists())
        finally:
            holder.communicate(timeout=5)

    def test_same_work_unit_different_handoff_and_event_conflicts_isolate(self) -> None:
        values, _ = self.admit()
        values["request_id"] = "different-handoff"
        self.assertEqual(self.call(values)[0], 423)
        self.event("QUESTION_ANSWERED", request_id="question-once")
        conflict = self.inputs("work_unit_event", request_id="question-once", payload={
            "kind": "EXPLICIT_CANCEL", "evidence_sha256": "a" * 64})
        self.assertEqual(self.call(conflict)[0], 423)
        self.event("EXPLICIT_CANCEL")

    def test_server_restart_rebinds_same_durable_unit(self) -> None:
        _, before = self.admit()
        self.event("QUESTION_ANSWERED")
        # Recover via the ordinary adapter startup; no second handoff is sent.
        self.server.kill()
        self.server.communicate(timeout=5)
        self.start_adapter()
        after = self.wait_state("WAITING_CLIENT_EVENT")
        self.assertNotEqual(before["executor"]["run_id"], after["executor"]["run_id"])
        self.assertNotEqual(before["executor"]["pid"], after["executor"]["pid"])
        self.assertEqual(before["handoff_sha256"], after["handoff_sha256"])
        self.event("CLIENT_DISCONNECT_REPORTED")
        self.wait_state("COMPLETED")
        self.assertEqual((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").read_bytes(), self.raw)

    def start_adapter(self) -> None:
        env = os.environ.copy()
        env.update(QIKVRT_API_HOST="127.0.0.1", QIKVRT_API_PORT=str(self.port),
                   QIKVRT_API_TOKEN=self.token, QIKVRT_API_TOKEN_EXPIRES_UTC="2099-01-01T00:00:00Z",
                   QIKVRT_ALLOWED_REPOSITORY="owner/repo", QIKVRT_API_PRINCIPAL="e2e-responsible-operator",
                   QIKVRT_REPO_ROOT=str(self.state), QIKVRT_RATE_LIMIT_PER_MINUTE="10000")
        self.server = subprocess.Popen([sys.executable, "-S", "src/qikvrt_github_api_shim.py"],
                                       cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._wait_until_ready()

    def test_lost_transport_ack_reconciled_before_handoff_replay(self) -> None:
        handoff = self.handoff()
        encoded = json.dumps({"ref": "main", "inputs": handoff}).encode()
        header = ("POST /repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches HTTP/1.1\r\n"
                  "Host: 127.0.0.1\r\nContent-Type: application/json\r\n"
                  f"Authorization: Bearer {self.token}\r\nContent-Length: {len(encoded)}\r\n\r\n").encode()
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as transport:
            transport.sendall(header + encoded)
            transport.shutdown(socket.SHUT_RDWR)  # no transport result is consumed
        admitted = self.wait_state("WAITING_CLIENT_EVENT")  # authoritative readback FIRST
        code, body = self.call(handoff)
        self.assertEqual(code, 202, body)
        self.assertEqual(body["handler_result"]["executor"]["run_id"], admitted["executor"]["run_id"])
        self.event("EXPLICIT_CANCEL")
        self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").exists())

    def test_effect_committed_before_checkpoint_loss_is_reconciled_on_restart(self) -> None:
        self.admit()
        self.event("QUESTION_ANSWERED")
        self.server.kill()
        self.server.communicate(timeout=5)
        values = self.inputs("work_unit_event", payload={
            "kind": "CLIENT_DISCONNECT_REPORTED", "evidence_sha256": "a" * 64})
        result = run_handler(HandlerConfig(root=self.state, operation=values["operation"],
                             artifact_id=self.unit, payload_b64=values["payload_b64"],
                             expected_sha256=values["expected_sha256"], dry_run=False,
                             repository="owner/repo", request_id=values["request_id"],
                             effect_accepted=True, responsibility_owner="e2e-responsible-operator",
                             origin_authenticated=True))
        self.assertEqual(result["state"], "WAITING_CLIENT_EVENT")
        crash_code = '''import os, sys
from pathlib import Path
sys.path.insert(0,sys.argv[1]+"/src")
import qikvrt_api_handler as api
save=api._save_work_unit
def crash_after_effect(root, record, event):
 if event=="work_unit_effect_readback": os._exit(88)
 return save(root,record,event)
api._save_work_unit=crash_after_effect
api.execute_work_unit(Path(sys.argv[2]),sys.argv[3],"owner/repo","e2e-responsible-operator",lambda:True)
'''
        crashed = subprocess.run([sys.executable, "-c", crash_code, str(ROOT), str(self.state), self.unit],
                                 timeout=10, check=False)
        self.assertEqual(crashed.returncode, 88)
        target = self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin"
        self.assertEqual(target.read_bytes(), self.raw)
        before = target.stat()
        self.start_adapter()
        final = self.wait_state("COMPLETED")
        after = target.stat()
        self.assertTrue(final["result"]["replayed"])
        self.assertTrue(final["effect_readback_verified"])
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assertEqual(len([x for x in self.journal() if x.get("event") == "request_result"
                             and x.get("operation") == "ingest" and not x.get("replayed")
                             and x.get("write_status") == "WRITTEN"]), 1)

    def test_blocked_unit_does_not_stop_independent_unit(self) -> None:
        other = "INDEPENDENT_CONTROL"
        other_raw = json.dumps({"work_unit_id": other, "purpose": "Independent authorized snapshot"}).encode()
        (self.state / "state/work_units" / f"{other}.json").write_bytes(other_raw)
        self.git("add", "state")
        self.git("commit", "-qm", "bind independent control")
        self.head, self.tree = self.git("rev-parse", "HEAD"), self.git("rev-parse", "HEAD^{tree}")
        from qikvrt_api_handler import process_lock
        with process_lock(self.state, name=work_unit_fence_name(self.unit)):
            self.assertEqual(self.call(self.handoff())[0], 202)
            self.wait_state("HOLD_COMPETING_WRITER")
            blocked_unit = self.unit
            self.unit, self.raw = other, other_raw
            self.admit()
            self.event("QUESTION_ANSWERED")
            self.event("CLIENT_DISCONNECT_REPORTED")
            self.wait_state("COMPLETED")
            self.assertEqual((self.state / ".qikvrt/api/inbox" / f"{other}.bin").read_bytes(), other_raw)
            self.assertFalse((self.state / ".qikvrt/api/inbox" / f"{blocked_unit}.bin").exists())

    def test_checkpoint_tamper_and_stale_effect_readback_isolate(self) -> None:
        self.admit()
        path = self.state / ".qikvrt/api/transactions" / f"work-unit.{self.unit}.json"
        original = path.read_bytes()
        forged = json.loads(original)
        forged["events"] = [{"kind": "CLIENT_DISCONNECT_REPORTED"}]
        path.write_text(json.dumps(forged))
        self.assertEqual(self.call(self.inputs("work_unit_status"))[0], 423)
        path.write_bytes(original)
        self.event("QUESTION_ANSWERED")
        self.event("CLIENT_DISCONNECT_REPORTED")
        self.wait_state("COMPLETED")
        (self.state / ".qikvrt/api/inbox" / f"{self.unit}.bin").write_bytes(b"real effect byte drift")
        self.assertEqual(self.call(self.inputs("work_unit_status"))[0], 423)


if __name__ == "__main__":
    unittest.main()
