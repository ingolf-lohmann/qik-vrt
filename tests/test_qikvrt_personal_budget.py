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



if __name__ == '__main__':
    unittest.main()
