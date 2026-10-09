# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""No billable requests. Actual SQLite concurrency/HTTP routing + provider doubles."""
from __future__ import annotations

import copy
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.qikvrt_personal_budget import BudgetLedger, CapabilityBlock
from src import qikvrt_personal_assistant as p
from src import qikvrt_effect_ack_http_terminal as terminal

KEY = "test-claude-key-" + "k" * 32
TOKEN = "test-local-token-" + "t" * 32
MODEL = "explicit-test-model"
NOW = 1800000000


def snapshot(provider="openai", now=None):
    now = int(time.time()) if now is None else now
    return {"schema": "qikvrt_personal_budget_v1", "provider": provider,
            "organization_id": "org_test", "workspace_id": "workspace_test",
            "subscription": {"plan": "unknown", "status": "unknown", "linked_organization_id": "org_test"},
            "observation": {"id": "test-observation-1", "source_sha256": "a" * 64, "confirmed_at": now,
                            "valid_until": now + 86400, "ledger_revision": 0},
            "credits": [{"id": "promo-1", "kind": "subscription", "remaining_micro_usd": 1000000,
                         "expires_at": now + 3600, "cycle_id": "billing-cycle-1"},
                        {"id": "paid-1", "kind": "purchased", "remaining_micro_usd": 2000000,
                         "expires_at": now + 86400, "cycle_id": None}],
            "limits": [{"id": k, "period_start": now - 100, "period_end": now + 7200,
                        "remaining_micro_usd": 1000000} for k in ("local", "organization", "workspace")],
            "pricing": {"model": MODEL, "source_sha256": "b" * 64, "valid_until": now + 86400,
                        "input_token_ceiling": 1000, "max_output_tokens": 100,
                        "input_micro_usd_per_million": 1000000, "output_micro_usd_per_million": 2000000,
                        "max_request_micro_usd": 1200},
            "allow_purchased": False, "billing_mode": "prepaid", "auto_reload": False,
            "warning_remaining_percent": [20, 10], "expiry_warning_seconds": 300}


class ClaudeDouble:
    def __init__(self):
        self.requests = []; self.fail = False; self.wrong_org = False; self.bad_usage = False

    def post(self, path, payload):
        self.requests.append((path, copy.deepcopy(payload)))
        receipt = {"evidence_class": "TECHNICAL_TEST_DOUBLE", "request_id": "fake-request",
                   "organization_id": "wrong-org" if self.wrong_org else "org_test", "workspace_id": "workspace_test"}
        if path == "/messages/count_tokens":
            return {"input_tokens": 30}, receipt
        if self.fail:
            raise TimeoutError("simulated response lost after effect")
        return {"id": "msg_test_" + str(len(self.requests)), "model": MODEL, "type": "message", "role": "assistant",
                "content": [{"type": "text", "text": "Unverified technical draft"}], "stop_reason": "end_turn",
                "usage": None if self.bad_usage else {"input_tokens": 30, "output_tokens": 20}}, receipt


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name) / "ledger.sqlite3"
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL"); self.db.execute("PRAGMA synchronous=FULL")
        self.now = NOW
        self.ledger = BudgetLedger(self.db, clock=lambda: self.now)
        self.s = snapshot("claude", NOW)

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def reserve(self, key="request-1", provider="claude"):
        return self.ledger.reserve(provider, MODEL, key, "request-fingerprint")

    def test_plan_name_never_creates_balance(self):
        self.s["subscription"]["plan"] = "Max20x"
        for c in self.s["credits"]: c["remaining_micro_usd"] = None
        self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"):
            self.reserve()
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM personal_requests").fetchone()[0], 0)

    def test_missing_zero_and_expired_balance_stop(self):
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"): self.reserve()
        for c in self.s["credits"]: c["remaining_micro_usd"] = 0
        self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "EXHAUSTED"): self.reserve()
        self.now += 3600
        with self.assertRaisesRegex(CapabilityBlock, "EXPIRED"): self.reserve()

    def test_purchased_balance_with_unknown_expiry_is_not_spendable(self):
        self.s["credits"] = [self.s["credits"][1]]
        self.s["credits"][0]["expires_at"] = None
        self.s["allow_purchased"] = True
        self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"): self.reserve()

    def test_purchased_credits_require_opt_in_and_promotional_credits_spend_first(self):
        self.s["credits"][0]["remaining_micro_usd"] = 100
        self.s["allow_purchased"] = True; self.ledger.install(self.s)
        op = self.reserve()
        self.assertEqual(op["allocations"], [{"id": "promo-1", "amount": 100}, {"id": "paid-1", "amount": 1100}])
        self.ledger.finish("claude", "request-1", {"input_tokens": 10, "output_tokens": 0}, {"ok": True})
        state = self.ledger.status("claude")
        self.assertEqual(state["credits"][0]["remaining_micro_usd"], 90)
        self.assertEqual(state["credits"][1]["remaining_micro_usd"], 2000000)

    def test_warn_thresholds_and_expiry(self):
        self.s["credits"][0]["remaining_micro_usd"] = 1500
        self.ledger.install(self.s); self.reserve(); self.now += 3400
        self.assertIn("CREDIT_REMAINING_AT_OR_BELOW_20_PERCENT", self.ledger.status("claude")["warnings"])
        self.assertIn("CREDIT_EXPIRY_APPROACHING", self.ledger.status("claude")["warnings"])

    def test_billing_cycle_does_not_reset_calendar_limits_or_create_new_credit(self):
        self.ledger.install(self.s); self.now += 3600
        with self.assertRaisesRegex(CapabilityBlock, "EXPIRED"): self.reserve()
        self.assertEqual(self.ledger.status("claude")["limits"][0]["remaining_micro_usd"], 1000000)

    def test_calendar_rollover_stops_even_with_live_purchased_credit(self):
        self.s["allow_purchased"] = True; self.ledger.install(self.s); self.now += 7200
        with self.assertRaisesRegex(CapabilityBlock, "PERIOD_CHANGED"): self.reserve()

    def test_boundary_during_request_is_refused(self):
        self.s["credits"][0]["expires_at"] = NOW + 90; self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "EXPIRY_TOO_CLOSE"): self.reserve()
        self.assertEqual(self.ledger.status("claude")["credits"][0]["remaining_micro_usd"], 1000000)

    def test_spend_limit_is_independent_of_balance(self):
        self.s["limits"][1]["remaining_micro_usd"] = 100; self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "EXCEEDS_LIMIT"): self.reserve()

    def test_stale_and_clock_rollback(self):
        self.ledger.install(self.s); self.now -= 1
        with self.assertRaisesRegex(CapabilityBlock, "CLOCK"): self.reserve()
        self.now = NOW + 86400
        with self.assertRaisesRegex(CapabilityBlock, "STALE"): self.reserve()

    def test_reimport_same_snapshot_never_refills(self):
        self.ledger.install(self.s); self.reserve(); self.ledger.install(self.s)
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 998800)

    def test_expired_snapshot_reimport_preserves_readback_without_enabling_calls(self):
        self.ledger.install(self.s); self.now += 90000; self.ledger.install(self.s)
        self.assertEqual(self.ledger.status("claude")["state"], "BLOCK")
        with self.assertRaisesRegex(CapabilityBlock, "STALE"): self.reserve()

    def test_new_snapshot_cannot_drop_unresolved_holds_after_expiry(self):
        self.ledger.install(self.s); self.reserve(); self.now += 4000
        updated = snapshot("claude", self.now); updated["observation"].update(id="new", ledger_revision=1)
        with self.assertRaisesRegex(CapabilityBlock, "UNRESOLVED"): self.ledger.install(updated)
        self.assertEqual(self.ledger.status("claude")["revision"], 1)

    def test_reconciled_cycle_change_requires_new_evidence_and_exact_revision(self):
        self.ledger.install(self.s); self.reserve()
        self.ledger.finish("claude", "request-1", {"input_tokens": 10, "output_tokens": 20}, {"ok": True})
        self.now += 8000; updated = snapshot("claude", self.now); updated["observation"]["id"] = "new-evidence"
        with self.assertRaisesRegex(CapabilityBlock, "REVISION"): self.ledger.install(updated)
        updated["observation"]["ledger_revision"] = 2; self.ledger.install(updated)
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 1000000)
        self.assertEqual(self.reserve()["state"], "COMPLETED")

    def test_completed_repeat_is_cached_and_conflicts_are_rejected(self):
        self.ledger.install(self.s); self.reserve()
        self.ledger.finish("claude", "request-1", {"input_tokens": 0, "output_tokens": 0}, {"ok": True})
        self.assertEqual(self.reserve()["result"], {"ok": True})
        with self.assertRaisesRegex(CapabilityBlock, "CONFLICT"):
            self.ledger.reserve("claude", MODEL, "request-1", "different")
        with self.assertRaisesRegex(CapabilityBlock, "PROVIDER_SWITCH"):
            self.reserve(provider="openai")

    def test_provider_budgets_are_separate(self):
        self.ledger.install(self.s); other = snapshot("openai", NOW); self.ledger.install(other); self.reserve()
        self.assertEqual(self.ledger.status("openai")["available_micro_usd"], 1000000)

    def test_reservation_survives_database_restart(self):
        self.ledger.install(self.s); self.reserve(); self.db.close()
        self.db = sqlite3.connect(self.path); self.ledger = BudgetLedger(self.db, clock=lambda: self.now)
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"): self.reserve()
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 998800)

    def test_parallel_connections_do_not_oversubscribe(self):
        self.s["credits"][0]["remaining_micro_usd"] = 1200; self.ledger.install(self.s)
        barrier = threading.Barrier(8)
        def worker(i):
            conn = sqlite3.connect(self.path, timeout=10); ledger = BudgetLedger(conn, clock=lambda: NOW)
            barrier.wait()
            try: return ledger.reserve("claude", MODEL, f"parallel-{i}", str(i))["state"]
            except CapabilityBlock: return "BLOCK"
            finally: conn.close()
        with ThreadPoolExecutor(max_workers=8) as pool: results = list(pool.map(worker, range(8)))
        self.assertEqual(results.count("RESERVED"), 1); self.assertEqual(results.count("BLOCK"), 7)
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 0)

    def test_unknown_or_over_bound_usage_freezes_without_refund(self):
        self.ledger.install(self.s); self.reserve()
        with self.assertRaisesRegex(CapabilityBlock, "RECONCILIATION"):
            self.ledger.finish("claude", "request-1", {"input_tokens": 2000, "output_tokens": 1}, {})
        self.assertEqual(self.ledger.status("claude")["available_micro_usd"], 998800)
        with self.assertRaisesRegex(CapabilityBlock, "FROZEN"): self.reserve("next")

    def test_floats_negative_unknown_limits_and_auto_reload_are_rejected(self):
        for change in [lambda s: s.update(auto_reload=True), lambda s: s.update(billing_mode="invoice"),
                       lambda s: s["credits"][0].update(remaining_micro_usd=0.1),
                       lambda s: s["credits"][0].update(remaining_micro_usd=-1)]:
            candidate = copy.deepcopy(self.s); change(candidate)
            with self.assertRaises(CapabilityBlock): self.ledger.install(candidate)
        self.s["limits"][0]["remaining_micro_usd"] = None; self.ledger.install(self.s)
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"): self.reserve()


class ClaudeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name) / "private"
        self.transport = ClaudeDouble()
        self.runtime = p.PersonalRuntime(self.root, MODEL, KEY, TOKEN, provider="claude", transport=self.transport,
                                         budget_snapshot=snapshot("claude", NOW), clock=lambda: NOW)

    def tearDown(self):
        if self.runtime: self.runtime.close()
        self.tmp.cleanup()

    def create(self, request_id="create-1", mode="qikvrt"):
        return self.runtime.create(mode, "Source-bound task", [{"id": "a", "revision": "1", "text": "evidence"}], request_id=request_id)

    def test_explicit_stateless_messages_retain_full_history_and_checkpoint(self):
        first = self.create(); sid = first["session"]["id"]
        result = self.runtime.turn(sid, "continue", resume=True, request_id="turn-1")
        path, payload = self.transport.requests[-1]
        self.assertEqual(path, "/messages"); self.assertEqual(len(payload["messages"]), 3)
        self.assertEqual(payload["messages"][1]["content"], first["session"]["history"][0]["text"])
        self.assertNotIn("conversation", payload); self.assertNotIn("tools", payload)
        self.assertIn("QIKVRT_OBSERVED_CHECKPOINT", payload["messages"][-1]["content"])
        self.assertEqual(len(result["session"]["history"]), 2)
        self.assertFalse(self.runtime.capabilities()["authenticated_runtime_readback"])

    def test_timeout_after_effect_keeps_reservation_and_prevents_duplicate_after_restart(self):
        self.transport.fail = True
        with self.assertRaises(TimeoutError): self.create()
        n = len(self.transport.requests); session = self.runtime.sessions()[0]
        self.assertEqual(session["status"], "TURN_PENDING")
        self.runtime.close()
        self.runtime = p.PersonalRuntime(self.root, MODEL, KEY, TOKEN, provider="claude", transport=self.transport, clock=lambda: NOW)
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"): self.create()
        self.assertEqual(len(self.transport.requests), n)
        self.assertEqual(self.runtime.budget.status("claude")["available_micro_usd"], 998800)

    def test_successful_repeats_are_cached_including_old_http_clients(self):
        first = self.create(); n = len(self.transport.requests)
        self.assertEqual(self.create(), first); self.assertEqual(len(self.transport.requests), n)
        self.runtime.turn(first["session"]["id"], "Repeat-safe turn")
        n = len(self.transport.requests)
        self.runtime.turn(first["session"]["id"], "Repeat-safe turn")
        self.assertEqual(len(self.transport.requests), n)

    def test_request_id_collision_or_cross_provider_switch_is_blocked(self):
        self.create()
        with self.assertRaisesRegex(CapabilityBlock, "CONFLICT"):
            self.runtime.create("baseline", "different", [], request_id="create-1")
        self.runtime.close(); self.runtime = None
        with self.assertRaisesRegex(CapabilityBlock, "MISMATCH"):
            p.PersonalRuntime(self.root, MODEL, KEY, TOKEN, provider="openai", transport=self.transport)

    def test_concurrent_duplicate_creates_make_one_provider_request(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: self.create(), range(6)))
        self.assertTrue(all(r == results[0] for r in results))
        self.assertEqual(len(self.transport.requests), 2)  # one free count + one paid message

    def test_new_id_cannot_reserve_again_for_an_ambiguous_session(self):
        self.transport.fail = True
        with self.assertRaises(TimeoutError): self.create()
        before = self.runtime.budget.status("claude")
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"):
            self.runtime.turn(self.runtime.sessions()[0]["id"], "continue", request_id="new-id")
        self.assertEqual(self.runtime.budget.status("claude"), before)

    def test_real_sigkill_after_dispatch_retains_budget_and_no_retry(self):
        if os.name != "posix": self.skipTest("POSIX process-loss witness")
        script = r'''
import sys,time
from src import qikvrt_personal_assistant as p
from tests.test_qikvrt_personal_budget import ClaudeDouble,KEY,TOKEN,MODEL,NOW,snapshot
class Interrupted(ClaudeDouble):
 def post(self,path,payload):
  if path == "/messages":
   print("EFFECT_SENT",flush=True);time.sleep(30)
  return super().post(path,payload)
r=p.PersonalRuntime(sys.argv[1],MODEL,KEY,TOKEN,provider="claude",transport=Interrupted(),budget_snapshot=snapshot("claude",NOW),clock=lambda:NOW)
r.create("baseline","kill",[],request_id="kill-request")
'''
        root = Path(self.tmp.name) / "killed"
        process = subprocess.Popen([sys.executable, "-B", "-c", script, str(root)], cwd=p.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(), "EFFECT_SENT")
            process.kill(); process.wait(timeout=5)
            transport = ClaudeDouble()
            restored = p.PersonalRuntime(root, MODEL, KEY, TOKEN, provider="claude", transport=transport, clock=lambda: NOW)
            try:
                self.assertEqual(restored.budget.status("claude")["available_micro_usd"], 998800)
                with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"):
                    restored.create("baseline", "kill", [], request_id="kill-request")
                self.assertEqual(transport.requests, [])
            finally: restored.close()
        finally:
            if process.poll() is None: process.kill(); process.wait(timeout=5)
            process.stdout.close(); process.stderr.close()

    def test_wrong_credential_organization_stops_before_paid_request(self):
        self.transport.wrong_org = True
        with self.assertRaisesRegex(CapabilityBlock, "ACCOUNT_BINDING"): self.create()
        self.assertEqual([p for p, _ in self.transport.requests], ["/messages/count_tokens"])

    def test_slow_preflight_crossing_expiry_stops_before_paid_request(self):
        moment = [NOW]
        self.runtime.budget.clock = lambda: moment[0]
        original = self.transport.post
        def slow_count(path, payload):
            result = original(path, payload)
            if path == "/messages/count_tokens": moment[0] = NOW + 3550
            return result
        self.transport.post = slow_count
        with self.assertRaisesRegex(CapabilityBlock, "BEFORE_DISPATCH"): self.create()
        self.assertEqual([path for path, _ in self.transport.requests], ["/messages/count_tokens"])

    def test_unknown_usage_does_not_refund_or_look_successful(self):
        self.transport.bad_usage = True
        with self.assertRaisesRegex(CapabilityBlock, "USAGE_UNKNOWN"): self.create()
        n = len(self.transport.requests)
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"): self.create()
        with self.assertRaisesRegex(CapabilityBlock, "FROZEN"): self.create("different")
        self.assertEqual(len(self.transport.requests), n)

    def test_secrets_do_not_enter_snapshot_session_or_budget_database(self):
        candidate = snapshot("claude", NOW); candidate["subscription"]["plan"] = KEY
        # Runtime import checks all fields before persistence.
        with self.assertRaisesRegex(CapabilityBlock, "SECRET"):
            p.PersonalRuntime(Path(self.tmp.name) / "other", MODEL, KEY, TOKEN, provider="claude", transport=self.transport, budget_snapshot=candidate)
        self.create()
        with self.assertRaisesRegex(CapabilityBlock, "SECRET"):
            self.runtime.turn(self.runtime.sessions()[0]["id"], KEY)
        for file in self.root.iterdir():
            self.assertNotIn(KEY.encode(), file.read_bytes()); self.assertNotIn(TOKEN.encode(), file.read_bytes())

    def test_missing_budget_preserves_existing_openai_session_bytes_but_stops_calls(self):
        from tests.test_qikvrt_personal_assistant import TransportDouble
        root = Path(self.tmp.name) / "legacy"; transport = TransportDouble()
        old = p.PersonalRuntime(root, MODEL, KEY, TOKEN, transport=transport, budget_snapshot=snapshot())
        result = old.create("baseline", "legacy", []); sid = result["session"]["id"]
        # Restore the exact v1 history shape: no budget fields existed there.
        legacy = old.load(sid)
        for turn in legacy["history"]: turn.pop("budget_usage", None)
        old.save(legacy)
        result = old.readback(legacy)
        body = old.db.execute("SELECT body FROM sessions WHERE id=?", (sid,)).fetchone()[0]
        # Equivalent to a v1 DB: sessions/config remain, new budget tables absent.
        with old.db:
            old.db.execute("DROP TABLE personal_requests"); old.db.execute("DROP TABLE personal_budgets")
        old.close()
        restored = p.PersonalRuntime(root, MODEL, KEY, TOKEN, transport=transport)
        try:
            self.assertEqual(restored.db.execute("SELECT body FROM sessions WHERE id=?", (sid,)).fetchone()[0], body)
            self.assertEqual(restored.readback(restored.load(sid))["session"], result["session"])
            n = len(transport.requests)
            with self.assertRaisesRegex(CapabilityBlock, "BUDGET_UNKNOWN"): restored.turn(sid, "next")
            self.assertEqual(len(transport.requests), n)
            restored.budget.install(snapshot())
            continued = restored.turn(sid, "next")
            self.assertEqual(continued["session"]["conversation_id"], result["session"]["conversation_id"])
            self.assertEqual(len(continued["session"]["history"]), 2)
        finally: restored.close()

    def test_http_create_retry_readback_and_authenticated_budget(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), p.personal_handler(terminal.Handler, self.runtime))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        def query(path, body=None, token=TOKEN):
            req = Request(base + path, data=p.canonical(body) if body else None,
                          headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with urlopen(req, timeout=3) as r: return json.load(r)
        try:
            with self.assertRaises(HTTPError): query("/personal/budget", token="wrong")
            body = {"mode": "baseline", "task": "http", "sources": [], "confirmed": True, "request_id": "http-1"}
            first = query("/personal/create", body); second = query("/personal/create", body)
            self.assertEqual(first, second); self.assertEqual(len(self.transport.requests), 2)
            readback = query("/personal/session/" + first["session"]["id"])
            self.assertEqual(first["session_sha256"], readback["session_sha256"])
            self.assertFalse(query("/personal/budget")["provider_live_balance_verified"])
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_transport_fixed_authority_headers_redaction_and_no_retry(self):
        transport = p.ClaudeTransport(KEY); transport.workspace_id = "workspace_test"
        for path in ("/conversations", "/billing", "/reload", "https://other.invalid"):
            with self.assertRaises(CapabilityBlock): transport.post(path, {})
        for failure in (TimeoutError(KEY), HTTPError("https://api.anthropic.com", 429, KEY, {}, None)):
            with patch.object(transport.opener, "open", side_effect=failure) as call:
                with self.assertRaises(CapabilityBlock) as raised: transport.post("/messages", {})
                self.assertNotIn(KEY, str(raised.exception)); self.assertEqual(call.call_count, 1)
                req = call.call_args.args[0]
                self.assertEqual(req.full_url, "https://api.anthropic.com/v1/messages")
                self.assertEqual(req.get_header("X-api-key"), KEY)
                self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")
                self.assertEqual(req.get_header("Anthropic-workspace-id"), "workspace_test")
                self.assertIsNone(req.get_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
