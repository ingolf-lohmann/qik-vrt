# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real HTTP ingress and negative controls; entirely synthetic private data."""
import base64
import copy
from datetime import datetime, timedelta, timezone
import http.client
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qikvrt_graph_webhook as webhook
from qikvrt_github_api_shim import QikvrtGitHubApiShim, QikvrtGitHubApiServer, _RATE_WINDOWS
from tools import qikvrt_graph_subscription as control
from tools.qikvrt_subprocess import run_bounded

SUB = "11111111-1111-1111-1111-111111111111"
TENANT = "22222222-2222-2222-2222-222222222222"
SECRET = "synthetic-only-" + "x" * 40


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        state = self.root / "state"
        state.mkdir(mode=0o700)
        self.binding = {"schema": "qikvrt_graph_mail_webhook_binding_v1",
                        "repository": "owner/repository", "responsibility_owner": "owner",
                        "state_root": str(state), "accepted_effect_scope": webhook.SCOPE,
                        "notification_url": "https://callback.example.test" + webhook.MAIL_PATH,
                        "lifecycle_url": "https://callback.example.test" + webhook.LIFECYCLE_PATH,
                        "subscriptions": [{"id": SUB, "tenant_id": TENANT,
                                           "resource_prefix": "users/synthetic-mailbox/messages/",
                                           "client_state": SECRET}]}
        self.file = self.root / "private-binding.json"
        self.save()
        self.env = patch.dict(os.environ, {
            "QIKVRT_GRAPH_WEBHOOK_BINDING": str(self.file),
            "QIKVRT_ALLOWED_REPOSITORY": "owner/repository", "QIKVRT_API_PRINCIPAL": "owner",
            "QIKVRT_API_TOKEN": "b64url:" + base64.urlsafe_b64encode(b"a" * 32).decode().rstrip("="),
            "QIKVRT_API_TOKEN_EXPIRES_UTC": "2030-01-01T00:00:00Z", "QIKVRT_API_LOG": "0",
        })
        self.env.start()
        _RATE_WINDOWS.clear()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), QikvrtGitHubApiShim)
        self.server.graph_mail_wakeup = threading.Event()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def save(self):
        self.file.write_text(json.dumps(self.binding))
        self.file.chmod(0o600)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.env.stop()
        self.temp.cleanup()

    def event(self):
        return {"value": [{"id": "synthetic-event", "subscriptionId": SUB,
                           "tenantId": TENANT, "clientState": SECRET, "changeType": "created",
                           "resource": "users/synthetic-mailbox/messages/message-1",
                           "resourceData": {"@odata.type": "#Microsoft.Graph.Message",
                                            "id": "message-1", "@odata.etag": "version-1"}}]}

    def call(self, body=None, path=webhook.MAIL_PATH, method="POST", raw=None):
        c = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        payload = raw if raw is not None else json.dumps(body).encode()
        c.request(method, path, payload, {"Content-Type": "application/json"})
        r = c.getresponse()
        data = r.read()
        result = r.status, r.getheader("Content-Type"), data
        c.close()
        return result

    def records(self):
        return list((Path(self.binding["state_root"]) / ".qikvrt/api/inbox").glob("*.bin"))

    def worker_receipts(self):
        return sorted((Path(self.binding["state_root"]) / ".qikvrt/api/out").glob("graph-*.reconciled.json"))

    def native_server(self):
        server = QikvrtGitHubApiServer(("127.0.0.1", 0), QikvrtGitHubApiShim)
        self.addCleanup(server.server_close)
        return server

    def test_wakeup_occurs_only_after_commit_and_independent_readback(self):
        observed = []

        class Wake:
            def set(inner):
                self.assertEqual(len(self.records()), 1)
                key = self.records()[0].stem
                transaction = Path(self.binding["state_root"]) / ".qikvrt/api/transactions" / (key + ".json")
                self.assertEqual(json.loads(transaction.read_bytes())["state"], "COMMITTED")
                self.assertEqual(hashlib.sha256(self.records()[0].read_bytes()).hexdigest(), key[6:])
                observed.append(key)

        webhook.receive(self.event(), self.binding, wakeup=Wake())
        self.assertEqual(len(observed), 1)

    def test_failed_ingest_does_not_wake_or_claim_receipt(self):
        with patch.object(webhook, "run_handler", return_value={"effect_state": "EFFECT_ACK_BLOCK"}):
            self.assertEqual(self.call(self.event())[0], 503)
        self.assertFalse(self.server.graph_mail_wakeup.is_set())
        self.assertEqual(self.worker_receipts(), [])

    def test_partial_durable_batch_wakes_even_if_later_storage_fails(self):
        body = self.event()
        second = copy.deepcopy(body["value"][0])
        second["resourceData"]["@odata.etag"] = "version-2"
        body["value"].append(second)
        original = webhook.run_handler
        calls = []

        def store(cfg):
            calls.append(cfg)
            return original(cfg) if len(calls) == 1 else {"effect_state": "EFFECT_ACK_BLOCK"}

        with patch.object(webhook, "run_handler", side_effect=store):
            self.assertEqual(self.call(body)[0], 503)
        self.assertEqual(len(self.records()), 1)
        self.assertTrue(self.server.graph_mail_wakeup.is_set())
        self.assertEqual(self.native_server().graph_mail_status["records"], 1)

    def test_native_loop_binds_event_and_reconciles_startup_pending_bytes(self):
        self.assertEqual(self.call(self.event())[0], 202)
        server = self.native_server()
        self.assertEqual(server.graph_mail_status["status"], "RECONCILED")
        self.assertEqual(server.graph_mail_status["records"], 1)
        self.assertFalse(server.graph_mail_wakeup.is_set())
        receipt = json.loads(self.worker_receipts()[0].read_bytes())
        self.assertEqual(receipt["effect_scope"], webhook.WORKER_SCOPE)
        for field in ("effect_ack_done", "document_received", "provider_readback_performed", "native_mail_consumer_bound"):
            self.assertFalse(receipt[field])
        self.assertEqual(len(self.records()), 1)  # retained for the separately bound mail consumer
        self.assertNotIn(SECRET.encode(), self.worker_receipts()[0].read_bytes())

    def test_native_loop_processes_wake_and_has_no_timer_or_idle_scan(self):
        server = self.native_server()
        webhook.receive(self.event(), self.binding, wakeup=server.graph_mail_wakeup)
        self.assertEqual(self.worker_receipts(), [])
        server.service_actions()
        self.assertEqual(server.graph_mail_status["records"], 1)
        self.assertFalse(server.graph_mail_wakeup.is_set())
        with patch.object(server.graph_mail_reconciler, "reconcile", side_effect=AssertionError("idle scan")):
            for _ in range(5):
                server.service_actions()

    def test_real_native_http_loop_reconciles_delivery_and_exposes_bounded_health(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.server = self.native_server()
        completed = threading.Event()
        original = self.server.service_actions

        def actions():
            original()
            if self.server.graph_mail_status.get("records") == 1:
                completed.set()

        self.server.service_actions = actions
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.assertEqual(self.call(self.event())[0], 202)
        self.assertTrue(completed.wait(5), "native loop never reconciled the delivery")
        status, _, raw = self.call(method="GET", path="/health")
        self.assertEqual(status, 200)
        observed = json.loads(raw)["graph_mail_reconciliation"]
        self.assertEqual(observed["records"], 1)
        self.assertFalse(observed["native_mail_consumer_bound"])
        self.assertFalse(observed["effect_ack_done"])

    def test_concurrent_wakeup_during_scan_is_preserved(self):
        server = self.native_server()
        server.graph_mail_wakeup.set()
        original = server.graph_mail_reconciler.reconcile

        def concurrent_delivery():
            result = original()
            webhook.receive(self.event(), self.binding, wakeup=server.graph_mail_wakeup)
            return result

        with patch.object(server.graph_mail_reconciler, "reconcile", side_effect=concurrent_delivery):
            server.service_actions()
        self.assertTrue(server.graph_mail_wakeup.is_set())
        self.assertEqual(self.worker_receipts(), [])
        server.service_actions()
        self.assertEqual(len(self.worker_receipts()), 1)
        self.assertFalse(server.graph_mail_wakeup.is_set())

    def test_worker_replay_and_restart_reuse_same_receipt_without_overwrite(self):
        server = self.native_server()
        webhook.receive(self.event(), self.binding, wakeup=server.graph_mail_wakeup)
        server.service_actions()
        receipt = self.worker_receipts()[0]
        before = receipt.stat(), receipt.read_bytes()
        webhook.receive(self.event(), self.binding, wakeup=server.graph_mail_wakeup)
        with patch.object(server.graph_mail_reconciler, "reconcile", wraps=server.graph_mail_reconciler.reconcile) as scan:
            server.service_actions()
            self.assertEqual(scan.call_count, 1)
        self.assertEqual(self.native_server().graph_mail_status["records"], 1)
        self.assertEqual((receipt.stat().st_ino, receipt.stat().st_mtime_ns),
                         (before[0].st_ino, before[0].st_mtime_ns))
        self.assertEqual(receipt.read_bytes(), before[1])
        self.assertEqual(len(self.records()), 1)

    def test_worker_restart_recovers_after_process_exits_before_reconciliation(self):
        fixture = self.root / "synthetic-event.json"
        fixture.write_text(json.dumps(self.event()))
        child = """
import http.client, json, os, sys, threading
from pathlib import Path
sys.path.insert(0, 'src')
from qikvrt_github_api_shim import QikvrtGitHubApiServer, QikvrtGitHubApiShim
server = QikvrtGitHubApiServer(('127.0.0.1', 0), QikvrtGitHubApiShim)
if sys.argv[1] == 'ingest':
    # Abrupt process loss after durable wake but before its native loop scan.
    server.graph_mail_reconciler.reconcile = lambda: os._exit(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    client = http.client.HTTPConnection(*server.server_address, timeout=5)
    client.request('POST', '/webhooks/microsoft-graph/mail',
                   Path(sys.argv[2]).read_bytes(), {'Content-Type': 'application/json'})
    response = client.getresponse()
    assert response.status == 202
    response.read()
    server.graph_mail_wakeup.wait(5)
    os._exit(0)
print(json.dumps(server.graph_mail_status), flush=True)
os._exit(0)  # also lose all process memory after the durable worker receipt
"""
        observed = []
        for action in ("ingest", "restart", "restart"):
            result = run_bounded([sys.executable, "-B", "-S", "-c", child, action, str(fixture)],
                                 cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(),
                                 timeout=15, max_output_bytes=4096)
            self.assertEqual(result.returncode, 0, result.stderr)
            if action == "ingest":
                self.assertEqual(len(self.records()), 1)
                self.assertEqual(self.worker_receipts(), [])
            else:
                observed.append(json.loads(result.stdout))
        self.assertEqual(observed[0], observed[1])
        self.assertEqual(observed[0]["records"], 1)
        self.assertFalse(observed[0]["native_mail_consumer_bound"])
        self.assertEqual(len(self.worker_receipts()), 1)

    def test_corrupt_pending_payload_sidecar_or_ingest_provenance_blocks_startup(self):
        self.assertEqual(self.call(self.event())[0], 202)
        key = self.records()[0].stem
        base = Path(self.binding["state_root"]) / ".qikvrt/api"
        paths = [self.records()[0], base / "inbox" / (key + ".bin.sha256"),
                 base / "replay" / (key + ".json"),
                 base / "transactions" / (key + ".json"),
                 base / "provenance" / (key + "." + key + ".json")]
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(b"corrupt")
                with self.assertRaises((OSError, RuntimeError, ValueError)):
                    self.native_server()
                self.assertEqual(self.worker_receipts(), [])
                path.write_bytes(original)

    def test_named_hash_without_ingest_provenance_is_not_pending_authority(self):
        payload = webhook.wire(webhook.normalize(self.event(), self.binding)[0])
        inbox = Path(self.binding["state_root"]) / ".qikvrt/api/inbox"
        inbox.mkdir(parents=True)
        target = inbox / ("graph-" + hashlib.sha256(payload).hexdigest() + ".bin")
        target.write_bytes(payload)
        target.chmod(0o600)
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.native_server()
        self.assertEqual(self.worker_receipts(), [])

    def test_symlink_pending_record_cannot_be_reconciled(self):
        self.assertEqual(self.call(self.event())[0], 202)
        target = self.records()[0]
        other = self.root / "outside.bin"
        other.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(other)
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.native_server()
        self.assertEqual(self.worker_receipts(), [])

    def test_worker_failure_retains_pending_and_requires_new_wake_or_restart(self):
        server = self.native_server()
        webhook.receive(self.event(), self.binding, wakeup=server.graph_mail_wakeup)
        with patch.object(webhook, "atomic_write_bytes", side_effect=OSError("synthetic fsync failure")):
            server.service_actions()
        self.assertEqual(server.graph_mail_status["status"], "BLOCK")
        self.assertEqual(self.worker_receipts(), [])
        self.assertEqual(len(self.records()), 1)
        with patch.object(server.graph_mail_reconciler, "reconcile", side_effect=AssertionError("timed retry")):
            server.service_actions()
        self.assertEqual(self.native_server().graph_mail_status["records"], 1)

    def test_conflicting_worker_receipt_is_not_overwritten_or_promoted(self):
        self.assertEqual(self.call(self.event())[0], 202)
        self.native_server()
        receipt = self.worker_receipts()[0]
        value = json.loads(receipt.read_bytes())
        value["document_received"] = True
        receipt.write_bytes(webhook.wire(value))
        before = receipt.read_bytes()
        with self.assertRaises((OSError, RuntimeError, ValueError)):
            self.native_server()
        self.assertEqual(receipt.read_bytes(), before)

    def test_lifecycle_startup_reconciliation_does_not_renew_or_read_graph(self):
        body = {"value": [{"subscriptionId": SUB, "tenantId": TENANT,
                           "clientState": SECRET, "lifecycleEvent": "missed"}]}
        self.assertEqual(self.call(body, path=webhook.LIFECYCLE_PATH)[0], 202)
        server = self.native_server()
        self.assertEqual(server.graph_mail_status["records"], 1)
        self.assertFalse(server.graph_mail_status["provider_readback_performed"])
        self.assertEqual(len(self.records()), 1)

    def test_validation_is_url_decoded_plain_text_without_bearer_or_effect(self):
        status, kind, raw = self.call(path=webhook.MAIL_PATH + "?validationToken=opaque%2Btoken%20value")
        self.assertEqual((status, kind, raw), (200, "text/plain; charset=utf-8", b"opaque+token value"))
        self.assertEqual(self.records(), [])
        self.assertFalse(self.server.graph_mail_wakeup.is_set())

    def test_private_ingest_replay_survives_new_request_and_wakes_again(self):
        status, _, raw = self.call(self.event())
        self.assertEqual(status, 202)
        receipt = json.loads(raw)
        self.assertFalse(receipt["effect_ack_done"])
        self.assertFalse(receipt["document_received"])
        self.assertEqual(len(self.records()), 1)
        payload = self.records()[0].read_bytes()
        self.assertNotIn(SECRET.encode(), payload)
        self.server.graph_mail_wakeup.clear()
        self.assertEqual(self.call(self.event())[0], 202)
        self.assertTrue(self.server.graph_mail_wakeup.is_set())
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.records()[0].read_bytes(), payload)
        # A new adapter invocation uses only persisted state, not in-memory delivery IDs.
        result = webhook.receive(self.event(), copy.deepcopy(self.binding))
        self.assertEqual(result["event_keys"], receipt["event_keys"])

    def test_http_replay_survives_fresh_server_processes(self):
        fixture = self.root / "synthetic-event.json"
        fixture.write_text(json.dumps(self.event()))
        fixture.chmod(0o600)
        # Each bounded child starts and stops the actual HTTP handler. Only the
        # same private disk state crosses this process boundary.
        child = """
import http.client, json, sys, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0, 'src')
from qikvrt_github_api_shim import QikvrtGitHubApiShim
server = ThreadingHTTPServer(('127.0.0.1', 0), QikvrtGitHubApiShim)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    client = http.client.HTTPConnection(*server.server_address, timeout=5)
    client.request('POST', '/webhooks/microsoft-graph/mail',
                   Path(sys.argv[1]).read_bytes(), {'Content-Type': 'application/json'})
    response = client.getresponse()
    print(json.dumps({'status': response.status, 'receipt': json.loads(response.read())}))
    client.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
"""
        receipts = []
        for _ in range(2):
            result = run_bounded([sys.executable, "-B", "-S", "-c", child, str(fixture)],
                                 cwd=Path(__file__).resolve().parents[1],
                                 env=os.environ.copy(), timeout=15, max_output_bytes=4096)
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(result.stdout)
            self.assertEqual(observed["status"], 202)
            self.assertFalse(observed["receipt"]["effect_ack_done"])
            receipts.append(observed["receipt"])
        self.assertEqual(receipts[0]["event_keys"], receipts[1]["event_keys"])
        self.assertEqual(len(self.records()), 1)

    def test_unbound_secret_subscription_tenant_or_mailbox_never_persist(self):
        variants = [("clientState", "wrong"), ("subscriptionId", TENANT),
                    ("tenantId", SUB), ("resource", "users/another/messages/message-1")]
        for field, value in variants:
            with self.subTest(field=field):
                body = self.event()
                body["value"][0][field] = value
                self.assertEqual(self.call(body)[0], 401)
                self.assertEqual(self.records(), [])

    def test_invalid_second_batch_member_cannot_partially_apply(self):
        body = self.event()
        other = copy.deepcopy(body["value"][0])
        other["clientState"] = "wrong"
        body["value"].append(other)
        self.assertEqual(self.call(body)[0], 401)
        self.assertEqual(self.records(), [])

    def test_lifecycle_events_are_durable_observations_only(self):
        for kind in ("missed", "reauthorizationRequired", "subscriptionRemoved"):
            body = {"value": [{"subscriptionId": SUB, "tenantId": TENANT,
                               "clientState": SECRET, "lifecycleEvent": kind}]}
            self.assertEqual(self.call(body, path=webhook.LIFECYCLE_PATH)[0], 202)
        self.assertEqual(len(self.records()), 3)
        self.assertTrue(all(json.loads(p.read_bytes())["kind"].startswith("lifecycle.") for p in self.records()))

    def test_missing_public_or_symlinked_binding_fails_closed(self):
        self.file.chmod(0o644)
        self.assertEqual(self.call(self.event())[0], 503)
        self.file.chmod(0o600)
        link = self.root / "binding-link.json"
        link.symlink_to(self.file)
        with patch.dict(os.environ, {"QIKVRT_GRAPH_WEBHOOK_BINDING": str(link)}):
            self.assertEqual(self.call(self.event())[0], 503)
        self.assertEqual(self.records(), [])

    def test_duplicate_keys_nonfinite_and_wrong_method_do_not_queue(self):
        for raw in (b'{"value": [], "value": []}', b'{"value": NaN}'):
            self.assertEqual(self.call(raw=raw)[0], 400)
        self.assertEqual(self.call(self.event(), method="GET")[0], 404)
        self.assertEqual(self.records(), [])

    def test_pending_registration_id_cannot_admit_a_notification(self):
        self.binding["subscriptions"][0]["id"] = control.PENDING
        self.save()
        body = self.event()
        body["value"][0]["subscriptionId"] = control.PENDING
        self.assertEqual(self.call(body)[0], 401)

    def test_changed_message_version_creates_new_private_record(self):
        self.assertEqual(self.call(self.event())[0], 202)
        body = self.event()
        body["value"][0]["resourceData"]["@odata.etag"] = "version-2"
        self.assertEqual(self.call(body)[0], 202)
        self.assertEqual(len(self.records()), 2)

    def test_corrupt_persisted_record_is_not_acknowledged(self):
        self.assertEqual(self.call(self.event())[0], 202)
        self.records()[0].write_bytes(b"corrupt")
        self.assertEqual(self.call(self.event())[0], 503)


class FakeGraph:
    def __init__(self):
        self.rows = []
        self.effects = []
        self.lose_response = False
        self.account = "synthetic-mailbox"
        self.pages_incomplete = False

    def request(self, method, suffix, payload=None):
        if suffix == "me?$select=id":
            return {"id": self.account}
        if method == "GET" and suffix == "subscriptions":
            return {"value": copy.deepcopy(self.rows), **({"@odata.nextLink": "next"} if self.pages_incomplete else {})}
        if method == "POST":
            self.effects.append("POST")
            self.rows.append({**copy.deepcopy(payload), "id": SUB})
            if self.lose_response:
                raise OSError("synthetic lost response")
            return copy.deepcopy(self.rows[-1])
        if method == "PATCH":
            self.effects.append("PATCH")
            self.rows[0].update(payload)
            if self.lose_response:
                raise OSError("synthetic lost response")
            return copy.deepcopy(self.rows[0])
        return copy.deepcopy(self.rows[0])


class SubscriptionTests(unittest.TestCase):
    def binding(self):
        return {"notification_url": "https://callback.example.test" + webhook.MAIL_PATH,
                "lifecycle_url": "https://callback.example.test" + webhook.LIFECYCLE_PATH,
                "subscriptions": [{"id": control.PENDING, "resource_prefix": "users/synthetic-mailbox/messages/",
                                   "client_state": SECRET}]}

    def test_create_readback_and_reuse_have_only_one_native_effect(self):
        api, binding = FakeGraph(), self.binding()
        first = control.execute(binding, api)
        second = control.execute(binding, api)
        self.assertEqual(api.effects, ["POST"])
        self.assertEqual(first["subscription_id"], second["subscription_id"])
        self.assertFalse(first["effect_ack_done"])

    def test_lost_create_response_is_resolved_without_second_create(self):
        api, binding = FakeGraph(), self.binding()
        api.lose_response = True
        self.assertEqual(control.execute(binding, api)["state"], "SUBSCRIPTION_READ_BACK")
        self.assertEqual(api.effects, ["POST"])

    def test_lost_renewal_response_is_resolved_by_fresh_readback(self):
        api, binding = FakeGraph(), self.binding()
        now = datetime.now(timezone.utc)
        control.execute(binding, api, now=now)
        api.lose_response = True
        control.execute(binding, api, renew=True, now=now + timedelta(hours=1))
        self.assertEqual(api.effects, ["POST", "PATCH"])

    def test_other_mailbox_duplicate_or_incomplete_inventory_has_no_create(self):
        for case in ("mailbox", "duplicate", "incomplete"):
            with self.subTest(case=case):
                api, binding = FakeGraph(), self.binding()
                if case == "mailbox":
                    api.account = "other"
                elif case == "incomplete":
                    api.pages_incomplete = True
                else:
                    row = control.request_body(binding, binding["subscriptions"][0],
                                               (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
                    api.rows = [{**row, "id": SUB}, {**row, "id": TENANT}]
                with self.assertRaises(control.SubscriptionError):
                    control.execute(binding, api)
                self.assertEqual(api.effects, [])

    def test_missing_bound_subscription_is_not_silently_recreated(self):
        api, binding = FakeGraph(), self.binding()
        binding["subscriptions"][0]["id"] = SUB
        with self.assertRaises(control.SubscriptionError):
            control.execute(binding, api)
        self.assertEqual(api.effects, [])

    def test_rich_subscription_is_not_accepted_as_basic_readback(self):
        binding = self.binding()
        row = control.request_body(binding, binding["subscriptions"][0],
                                   (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
        self.assertTrue(control.same_subscription(row, row))
        self.assertFalse(control.same_subscription({**row, "includeResourceData": True}, row))


if __name__ == "__main__":
    unittest.main()
