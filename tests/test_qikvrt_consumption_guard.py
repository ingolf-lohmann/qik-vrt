# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic grants, real durable SQLite/HTTP; no vendor account or paid calls."""
import copy
import contextlib
import hashlib
import json
import sqlite3
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

from src import qikvrt_personal_assistant as p
from src import qikvrt_effect_ack_http_terminal as terminal
from src import qikvrt_personal_auth as auth
from src.qikvrt_personal_budget import BudgetLedger, CapabilityBlock, ConsumptionGuard, check_entitlement, encoded
from tests.test_qikvrt_personal_budget import snapshot, NOW, MODEL
from tests.test_qikvrt_personal_assistant import TransportDouble, KEY, TOKEN


def configuration(provider="openai", now=NOW, *, units=False):
    budget = snapshot(provider, now)
    if units:
        budget.update(schema="qikvrt_personal_budget_v2", currency="USD")
        budget["billing_mode"] = "bounded_usage"
        budget["credits"] = [{"id": "explicit-test-spend-allowance", "kind": "authorized_usage",
                              "remaining_micro_usd": 1000000, "expires_at": now + 3600, "cycle_id": None}]
        budget["pricing"] = {"kind": "units", "model": MODEL, "source_sha256": "b" * 64,
            "valid_until": now + 86400, "unit": "copilot_credit", "max_units": 10,
            "unit_micro_usd": 100, "max_request_micro_usd": 1000}
    subject = {"provider": provider, "organization_id": "org_test", "workspace_id": "workspace_test",
        "principal_id": "test-principal", "product_id": "SYNTHETIC-TEST-PRODUCT", "sku_id": "SYNTHETIC-TEST-SKU",
        "service_id": MODEL, "region": "FR", "channel": "csp"}
    bound = hashlib.sha256(encoded(subject).encode()).hexdigest()
    def evidence(kind):
        return {"kind": kind, "subject_sha256": bound, "source_sha256": "c" * 64,
                "observed_at": now, "valid_until": now + 86400}
    grant = {"schema": "qikvrt_consumption_grant_v1", "subject": subject, "activation": "explicit",
        "offer": {"provider": provider, "product_id": subject["product_id"], "sku_id": subject["sku_id"],
            "services": [MODEL], "regions": ["FR", "US"], "channels": ["csp"],
            "effective_from": now, "effective_until": now + 86400,
            "requires_seat": True, "requires_base_subscription": False,
            "default_billing_regions": ["US"], "evidence": evidence("catalog")},
        "rights": {name: {"authorized": True, "evidence": evidence(name)} for name in ("provider", "seat", "service", "consumption")}}
    grant["rights"]["consumption"]["budget_sha256"] = hashlib.sha256(encoded(budget).encode()).hexdigest()
    return {"schema": "qikvrt_consumption_config_v1", "grant": grant, "budget": budget}


class EntitlementTests(unittest.TestCase):
    def check(self, config):
        return check_entitlement(config["grant"], provider="openai", organization_id="org_test", workspace_id="workspace_test",
            principal_id="test-principal", service_id=MODEL, now=NOW)

    def test_standalone_offer_has_no_global_base_subscription_requirement(self):
        result = self.check(configuration())
        self.assertEqual(result["state"], "AUTHORIZED_FROM_OPERATOR_RECORD")
        self.assertFalse(result["vendor_live_entitlement_verified"])

    def test_each_independent_right_is_required_even_with_valid_sso_identity(self):
        for name in ("provider", "seat", "service", "consumption"):
            with self.subTest(name=name):
                config = configuration(); del config["grant"]["rights"][name]
                with self.assertRaisesRegex(CapabilityBlock, "INDEPENDENT_RIGHTS"): self.check(config)
                config = configuration(); config["grant"]["rights"][name]["authorized"] = False
                with self.assertRaisesRegex(CapabilityBlock, "NOT_AUTHORIZED"): self.check(config)

    def test_sso_evidence_cannot_be_relabelled_as_entitlement(self):
        config = configuration(); config["grant"]["rights"]["service"]["evidence"]["kind"] = "sso"
        with self.assertRaisesRegex(CapabilityBlock, "EVIDENCE_UNBOUND"): self.check(config)

    def test_real_offer_base_requirement_is_preserved(self):
        config = configuration(); config["grant"]["offer"]["requires_base_subscription"] = True
        with self.assertRaisesRegex(CapabilityBlock, "INDEPENDENT_RIGHTS"): self.check(config)

    def test_display_names_cannot_replace_product_or_sku_ids(self):
        for key in ("provider", "product_id", "sku_id"):
            config = configuration(); config["grant"]["offer"][key] = "same-marketing-name"
            with self.assertRaisesRegex(CapabilityBlock, "CATALOG_MISMATCH"): self.check(config)

    def test_france_default_off_is_distinct_from_explicit_usage(self):
        config = configuration(); config["grant"]["activation"] = "provider_default"
        with self.assertRaisesRegex(CapabilityBlock, "DEFAULT_BILLING"): self.check(config)
        config["grant"]["activation"] = "explicit"
        self.assertEqual(self.check(config)["state"], "AUTHORIZED_FROM_OPERATOR_RECORD")

    def test_future_offer_expired_evidence_unknown_region_and_channel_fail_closed(self):
        changes = [lambda g: g["offer"].update(effective_from=NOW + 1),
            lambda g: g["offer"]["evidence"].update(valid_until=NOW),
            lambda g: g["subject"].update(region="UNKNOWN"),
            lambda g: g["subject"].update(channel="unlisted"),
            lambda g: g["rights"]["consumption"]["evidence"].update(source_sha256=""),
            lambda g: g["subject"].update(principal_id="another-principal"),
            lambda g: g["offer"].update(requires_seat=None)]
        for change in changes:
            config = configuration(); change(config["grant"])
            with self.subTest(change=change), self.assertRaises(CapabilityBlock): self.check(config)


class MeteredLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name) / "budget.sqlite3"
        self.db = sqlite3.connect(self.path, check_same_thread=False); self.now = NOW
        self.ledger = BudgetLedger(self.db, clock=lambda: self.now)
        self.config = configuration("microsoft_copilot", units=True)
        self.guard = ConsumptionGuard(self.ledger, self.config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def test_credit_unit_quote_is_explicit_usd_and_settles_actual_usage(self):
        op = self.guard.reserve("units-1", "operation")
        self.assertEqual(op["reserved_micro_usd"], 1000)
        self.guard.before_dispatch(op)
        self.ledger.finish("microsoft_copilot", "units-1", {"units": 3}, {"result": "SYNTHETIC"})
        self.assertEqual(self.ledger.status("microsoft_copilot")["available_micro_usd"], 999700)
        self.assertEqual(self.guard.reserve("units-1", "operation")["state"], "COMPLETED")
        state = self.ledger.status("microsoft_copilot")
        self.assertEqual(state["billing_mode"], "bounded_usage")
        self.assertEqual(state["balance_evidence"], "PRIVATE_OPERATOR_SPEND_ALLOWANCE_MINUS_LOCAL_RESERVATIONS")
        self.assertFalse(state["provider_live_balance_verified"])

    def test_unknown_usage_and_new_request_ids_do_not_release_hold(self):
        self.guard.reserve("units-1", "operation")
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"): self.ledger.finish("microsoft_copilot", "units-1", None, {})
        with self.assertRaisesRegex(CapabilityBlock, "FROZEN"): self.guard.reserve("new-id", "new-operation")
        self.db.close(); self.db = sqlite3.connect(self.path)
        self.ledger = BudgetLedger(self.db, clock=lambda: self.now)
        self.guard = ConsumptionGuard(self.ledger, self.config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"): self.guard.reserve("units-1", "operation")

    def test_expired_grant_is_readable_but_cannot_reserve(self):
        self.now += 86400
        self.assertEqual(self.guard.status()["state"], "BLOCK")
        with self.assertRaises(CapabilityBlock): self.guard.reserve("expired", "operation")

    def test_expiry_during_slow_preflight_blocks_dispatch(self):
        op = self.guard.reserve("units-1", "operation")
        self.config["grant"]["rights"]["service"]["evidence"]["valid_until"] = NOW + 200
        self.guard.config["grant"] = copy.deepcopy(self.config["grant"])
        self.now += 110
        with self.assertRaisesRegex(CapabilityBlock, "STALE"): self.guard.before_dispatch(op)

    def test_unknown_currency_provider_balance_or_limit_never_authorizes(self):
        for change in [lambda c: c["budget"].update(currency="EUR"),
                       lambda c: c["budget"]["limits"][0].update(remaining_micro_usd=None)]:
            with self.subTest(change=change):
                config = configuration("microsoft_copilot", units=True); change(config)
                db = sqlite3.connect(":memory:")
                try:
                    with self.assertRaises(CapabilityBlock):
                        guard = ConsumptionGuard(BudgetLedger(db, clock=lambda: NOW), config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)
                        guard.reserve("unknown", "operation")
                finally: db.close()

    def test_parallel_connections_share_one_cap(self):
        # New independent connections compete for the same original SQLite pool.
        self.db.execute("DELETE FROM personal_budgets"); self.db.commit()
        self.config["budget"]["credits"][0]["remaining_micro_usd"] = 1000
        self.config["grant"]["rights"]["consumption"]["budget_sha256"] = hashlib.sha256(encoded(self.config["budget"]).encode()).hexdigest()
        self.guard = ConsumptionGuard(self.ledger, self.config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)
        barrier = threading.Barrier(6)
        def worker(i):
            db = sqlite3.connect(self.path, timeout=10)
            try:
                guard = ConsumptionGuard(BudgetLedger(db, clock=lambda: NOW), self.config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)
                barrier.wait()
                try: return guard.reserve("parallel-" + str(i), "operation")["state"]
                except CapabilityBlock: return "BLOCK"
            finally: db.close()
        with ThreadPoolExecutor(max_workers=6) as pool: results = list(pool.map(worker, range(6)))
        self.assertEqual(results.count("RESERVED"), 1)
        self.assertEqual(results.count("BLOCK"), 5)

    def test_changed_cost_limit_requires_a_new_bound_operator_decision(self):
        config = configuration("microsoft_copilot", units=True)
        config["budget"]["limits"][0]["remaining_micro_usd"] += 1
        db = sqlite3.connect(":memory:")
        try:
            with self.assertRaisesRegex(CapabilityBlock, "COST_LIMIT_DECISION_UNBOUND"):
                ConsumptionGuard(BudgetLedger(db, clock=lambda: NOW), config, provider="microsoft_copilot", principal_id="test-principal", service_id=MODEL)
        finally: db.close()

    def test_malformed_usage_freezes_as_unknown_instead_of_releasing_hold(self):
        self.guard.reserve("units-1", "operation")
        with self.assertRaisesRegex(CapabilityBlock, "USAGE_UNKNOWN"):
            self.ledger.finish("microsoft_copilot", "units-1", {"units": -1}, {})
        self.assertEqual(self.guard.status()["state"], "BLOCK")


class UsageDouble(TransportDouble):
    unknown_usage = False
    input_count = 10
    def post(self, path, payload):
        if path == "/responses/input_tokens":
            self.requests.append((path, copy.deepcopy(payload)))
            return {"object": "response.input_tokens", "input_tokens": self.input_count}, {"evidence_class": "TECHNICAL_TEST_DOUBLE"}
        value, receipt = super().post(path, payload)
        if path == "/responses" and not self.unknown_usage:
            value["usage"] = {"input_tokens": 10, "output_tokens": 20}
        return value, receipt


class RuntimeConsumptionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name) / "private"
        self.transport = UsageDouble(); self.runtime = None

    def tearDown(self):
        if self.runtime: self.runtime.close()
        self.tmp.cleanup()

    def start(self, config=True):
        self.runtime = p.PersonalRuntime(self.root, MODEL, KEY, TOKEN, transport=self.transport,
            require_consumption=True, consumption_config=configuration() if config else None,
            principal_id="test-principal", clock=lambda: NOW)

    def test_missing_operator_grant_stops_before_every_provider_request(self):
        self.start(False)
        with self.assertRaisesRegex(CapabilityBlock, "CONFIG_REQUIRED"): self.runtime.create("baseline", "task", [])
        self.assertEqual(self.transport.requests, [])

    def test_real_http_admission_readback_and_repeat_do_not_double_spend(self):
        self.start()
        server = ThreadingHTTPServer(("127.0.0.1", 0), p.personal_handler(terminal.Handler, self.runtime))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        def request(path, body=None, token=TOKEN):
            headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
            with urlopen(Request(base + path, data=None if body is None else p.canonical(body), headers=headers), timeout=3) as response:
                return json.load(response)
        try:
            with self.assertRaises(HTTPError): request("/personal/consumption", token="wrong")
            data = {"confirmed": True, "mode": "baseline", "task": "task", "sources": [], "request_id": "http-once"}
            first = request("/personal/create", data); second = request("/personal/create", data)
            self.assertEqual(first, second); self.assertEqual(len(self.transport.requests), 3)
            self.assertEqual(self.transport.requests[-1][1]["max_output_tokens"], 100)
            self.assertEqual(first["session"]["history"][0]["intent"]["request_sha256"], p.digest(p.canonical(self.transport.requests[-1][1])))
            self.assertEqual(request("/personal/consumption")["budget"]["available_micro_usd"], 999950)
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_unknown_result_retains_reservation_across_runtime_restart(self):
        self.start(); self.transport.unknown_usage = True
        with self.assertRaisesRegex(CapabilityBlock, "UNKNOWN"): self.runtime.create("baseline", "task", [], request_id="lost")
        before = len(self.transport.requests); self.runtime.close(); self.runtime = None; self.start()
        with self.assertRaisesRegex(CapabilityBlock, "NO_RETRY"): self.runtime.create("baseline", "task", [], request_id="lost")
        self.assertEqual(len(self.transport.requests), before)

    def test_oversize_input_stops_before_generation_without_local_estimates(self):
        self.start(); self.transport.input_count = 1001
        with self.assertRaisesRegex(CapabilityBlock, "INPUT_COUNT"):
            self.runtime.create("baseline", "task", [], request_id="oversize")
        self.assertEqual([path for path, _ in self.transport.requests], ["/conversations", "/responses/input_tokens"])

    def test_slow_count_cannot_cross_budget_expiry_into_paid_generation(self):
        self.start(); moment = [NOW]; self.runtime.consumption.ledger.clock = lambda: moment[0]
        original = self.transport.post
        def slow(path, payload):
            result = original(path, payload)
            if path == "/responses/input_tokens": moment[0] = NOW + 3550
            return result
        self.transport.post = slow
        with self.assertRaisesRegex(CapabilityBlock, "BOUNDARY_BEFORE_DISPATCH"):
            self.runtime.create("baseline", "task", [])
        self.assertNotIn("/responses", [path for path, _ in self.transport.requests])

    def test_protected_store_change_blocks_before_network(self):
        self.start()
        def changed(): raise CapabilityBlock("PROTECTED_CONSUMPTION_CONFIG_CHANGED_RESTART_REQUIRED")
        self.runtime.consumption_binding_check = changed
        with self.assertRaisesRegex(CapabilityBlock, "CONFIG_CHANGED"): self.runtime.create("baseline", "task", [])
        self.assertEqual(self.transport.requests, [])

    def test_secure_factory_always_requires_consumption_without_grant(self):
        class Store:
            def __init__(self, *args): pass
            def read(self): return {"provider_keys": {"openai": KEY}}
        with patch("src.qikvrt_personal_auth.load_config", return_value={"subject": "test-principal"}), \
             patch("src.qikvrt_personal_auth.OSSecretStore", Store), \
             patch("src.qikvrt_personal_auth.PersonalAuth"):
            self.runtime = p.PersonalRuntime.from_secret_store(self.root, MODEL, "openai", "private-config", "http://127.0.0.1:8771")
        self.runtime.transport = self.transport
        with self.assertRaisesRegex(CapabilityBlock, "CONFIG_REQUIRED"): self.runtime.create("baseline", "task", [])
        self.assertEqual(self.transport.requests, [])


class ProtectedProvisionTests(unittest.TestCase):
    def test_provision_uses_existing_store_lock_and_readback_without_paid_request(self):
        class Store:
            def __init__(self, *args):
                self.value = {"provider_keys": {"openai": KEY}}
            def provision_lock(self, state_dir): return contextlib.nullcontext()
            def read(self): return copy.deepcopy(self.value)
            def write(self, value): self.value = copy.deepcopy(value)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "consumption.json"
            path.write_text(encoded(configuration(now=int(time.time())))); path.chmod(0o600)
            store = Store()
            with patch.object(auth, "load_config", return_value={"subject": "test-principal"}), patch.object(auth, "OSSecretStore", return_value=store):
                result = auth.provision_consumption(Path(tmp) / "state", "openai", MODEL, "oidc", "http://127.0.0.1:8771", path)
            self.assertEqual(result["state"], "PROTECTED_CONSUMPTION_CONFIG_READBACK_VERIFIED")
            self.assertEqual(result["paid_requests"], 0)
            self.assertFalse(result["vendor_live_entitlement_verified"])
            self.assertEqual(store.value["provider_keys"]["openai"], KEY)
            self.assertIn("consumption", store.value)

    def test_public_file_and_embedded_protected_key_are_rejected(self):
        class Store:
            def __init__(self, *args): pass
            def provision_lock(self, state_dir): return contextlib.nullcontext()
            def read(self): return {"provider_keys": {"openai": KEY}}
            def write(self, value): raise AssertionError("must not store rejected input")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "consumption.json"
            config = configuration(now=int(time.time())); path.write_text(encoded(config)); path.chmod(0o644)
            with patch.object(auth, "load_config", return_value={"subject": "test-principal"}), patch.object(auth, "OSSecretStore", Store):
                with self.assertRaisesRegex(auth.AuthBlock, "PRIVATE_REGULAR_FILE"):
                    auth.provision_consumption(tmp, "openai", MODEL, "oidc", "http://127.0.0.1:8771", path)
                config["budget"]["subscription"]["plan"] = KEY
                path.write_text(encoded(config)); path.chmod(0o600)
                with self.assertRaisesRegex(auth.AuthBlock, "PROTECTED_SECRET"):
                    auth.provision_consumption(tmp, "openai", MODEL, "oidc", "http://127.0.0.1:8771", path)


if __name__ == "__main__":
    unittest.main()
