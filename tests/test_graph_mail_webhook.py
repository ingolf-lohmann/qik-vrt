# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Real HTTP ingress and negative controls; entirely synthetic private data."""
import base64
import copy
from datetime import datetime, timedelta, timezone
import http.client
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
from qikvrt_github_api_shim import QikvrtGitHubApiShim, _RATE_WINDOWS
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
