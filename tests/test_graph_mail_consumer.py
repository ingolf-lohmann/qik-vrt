# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Native-loop, provider replay/recovery and fail-closed synthetic controls."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import qikvrt_graph_mail_consumer as consumer
import qikvrt_graph_webhook as webhook
from qikvrt_github_api_shim import QikvrtGitHubApiServer, QikvrtGitHubApiShim
from tools.qikvrt_graph_subscription import Graph, SubscriptionError
from tools.qikvrt_subprocess import run_bounded
from tests.test_graph_mail_webhook import SUB, TENANT, SECRET


def message(version="version-1", subject="Synthetic private subject", folder="folder-inbox"):
    return {"id": "message-1", "parentFolderId": folder, "changeKey": version,
            "lastModifiedDateTime": "2026-10-06T20:00:00Z",
            "receivedDateTime": "2026-10-06T19:00:00Z", "subject": subject,
            "from": {"emailAddress": {"name": "Synthetic sender", "address": "sender@example.test"}},
            "hasAttachments": True, "isRead": False, "importance": "normal",
            "bodyPreview": "Synthetic private preview", "internetMessageId": "<synthetic@example.test>"}


class SyntheticGraph:
    source = "SYNTHETIC_TEST_PROVIDER"

    def __init__(self, token_file=None):
        self.account = "synthetic-mailbox"
        self.messages = {"message-1": message()}
        self.folder_ids = {"inbox": "folder-inbox"}
        self.cursor = "https://graph.microsoft.com" + consumer.delta_path("inbox") + "?$deltatoken=one"
        self.pages = {}
        self.calls = []
        self.on_read = None

    def request(self, method, suffix, payload=None):
        if method != "GET" or suffix != "me?$select=id" or payload is not None:
            raise AssertionError("consumer attempted a provider write/control-plane effect")
        self.calls.append((method, consumer.ORIGIN + suffix))
        return {"id": self.account}

    def mail_get(self, url):
        self.calls.append(("GET", url))
        if self.on_read:
            self.on_read(url)
        if url in self.pages:
            value = self.pages[url]
            if isinstance(value, Exception):
                raise value
            return copy.deepcopy(value)
        path = unquote(urlsplit(url).path)
        if path.endswith("/messages/delta"):
            return {"value": [{"id": k} for k in self.messages], "@odata.deltaLink": self.cursor}
        if path.startswith("/v1.0/me/mailFolders/"):
            return {"id": self.folder_ids[path.rsplit("/", 1)[1]]}
        key = path.rsplit("/", 1)[1]
        if key not in self.messages:
            raise HTTPError(url, 404, "synthetic missing message", {}, None)
        return copy.deepcopy(self.messages[key])


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "private-state"
        self.state.mkdir(mode=0o700)
        self.webhook = {"schema": "qikvrt_graph_mail_webhook_binding_v1",
                        "repository": "owner/repository", "responsibility_owner": "owner",
                        "state_root": str(self.state), "accepted_effect_scope": webhook.SCOPE,
                        "notification_url": "https://callback.example.test" + webhook.MAIL_PATH,
                        "lifecycle_url": "https://callback.example.test" + webhook.LIFECYCLE_PATH,
                        "subscriptions": [{"id": SUB, "tenant_id": TENANT,
                                           "resource_prefix": "users/synthetic-mailbox/messages/",
                                           "client_state": SECRET}]}
        self.webhook_file = self.root / "webhook.json"
        self.private(self.webhook_file, self.webhook)
        self.token_file = self.root / "token"
        self.token_file.write_text("synthetic-oauth-bearer")
        self.token_file.chmod(0o600)
        self.binding = {"schema": "qikvrt_graph_mail_consumer_binding_v1",
                        "repository": "owner/repository", "responsibility_owner": "owner",
                        "state_root": str(self.state), "accepted_effect_scope": consumer.SCOPE,
                        "tenant_id": TENANT, "mailbox_id": "synthetic-mailbox",
                        "folder_ids": ["inbox"], "token_file": str(self.token_file)}
        self.file = self.root / "consumer.json"
        self.private(self.file, self.binding)
        self.api = SyntheticGraph()
        self.consumer = consumer.GraphMailConsumer(self.file, api_factory=lambda _: self.api)
        env = patch.dict(os.environ, {
            "QIKVRT_GRAPH_WEBHOOK_BINDING": str(self.webhook_file),
            "QIKVRT_GRAPH_MAIL_CONSUMER_BINDING": str(self.file),
            "QIKVRT_ALLOWED_REPOSITORY": "owner/repository", "QIKVRT_API_PRINCIPAL": "owner"})
        env.start()
        self.addCleanup(env.stop)

    def private(self, file, value):
        file.write_bytes(webhook.wire(value))
        file.chmod(0o600)

    def native_server(self):
        with patch("qikvrt_github_api_shim.GraphMailConsumer", return_value=self.consumer):
            server = QikvrtGitHubApiServer(("127.0.0.1", 0), QikvrtGitHubApiShim)
        self.addCleanup(server.server_close)
        return server

    def event(self, *, lifecycle=None):
        row = {"subscriptionId": SUB, "tenantId": TENANT, "clientState": SECRET}
        if lifecycle:
            row["lifecycleEvent"] = lifecycle
        else:
            row.update(changeType="updated", resource="users/synthetic-mailbox/messages/message-1",
                       resourceData={"@odata.type": "#Microsoft.Graph.Message", "id": "message-1"})
        return {"value": [row]}  # deliberately no event ID and no ETag

    def pointer(self):
        return self.state / ".qikvrt/api/out/graph-mail-current.json"

    def current(self):
        p = json.loads(self.pointer().read_bytes())
        return self.consumer._packet(self.binding, p["observation_key"])

    def observe(self):
        return self.consumer.observe(self.webhook)

    def delta_initial(self):
        return "https://graph.microsoft.com" + consumer.delta_path("inbox") + consumer.SELECT

    def assert_not_advanced(self, before):
        self.assertEqual(self.pointer().read_bytes() if self.pointer().exists() else None, before)

    def test_startup_without_notifications_reads_provider_and_private_current_messages(self):
        server = self.native_server()
        self.assertEqual(server.graph_mail_status["mail_observation"]["changes"], 1)
        self.assertTrue(server.graph_mail_status["native_mail_consumer_bound"])
        packet = self.current()
        observation = packet["observation"]
        self.assertEqual(observation["trigger"], "START_RECOVERY")
        self.assertEqual(observation["provider_source"], "SYNTHETIC_TEST_PROVIDER")
        self.assertEqual(observation["changes"][0]["message"], message())
        self.assertTrue(observation["provider_readback_performed"])
        self.assertFalse(observation["document_received"])
        self.assertFalse(observation["effect_ack_done"])
        self.assertTrue(any("/me/messages/message-1" in u for _, u in self.api.calls))
        public = json.dumps(server.graph_mail_status)
        for secret in ("Synthetic private subject", "sender@example.test", "synthetic-mailbox", "deltatoken", SECRET):
            self.assertNotIn(secret, public)

    def test_replayed_idless_etagless_notification_reads_new_version_and_deduplicates(self):
        server = self.native_server()
        first = webhook.receive(self.event(), self.webhook, wakeup=server.graph_mail_wakeup)
        server.service_actions()
        self.assertEqual(self.current()["observation"]["changes"], [])
        self.api.messages["message-1"] = message("version-2")
        self.api.cursor = self.api.cursor.replace("one", "two")
        replay = webhook.receive(self.event(), self.webhook, wakeup=server.graph_mail_wakeup)
        self.assertEqual(first["event_keys"], replay["event_keys"])
        before_calls = len(self.api.calls)
        server.service_actions()
        self.assertGreater(len(self.api.calls), before_calls)
        self.assertEqual(self.current()["observation"]["changes"][0]["message"]["changeKey"], "version-2")
        webhook.receive(self.event(), self.webhook, wakeup=server.graph_mail_wakeup)
        server.service_actions()
        self.assertEqual(self.current()["observation"]["changes"], [])

    def test_same_version_changed_selected_content_and_versionless_content_are_observed(self):
        self.observe()
        self.api.messages["message-1"]["subject"] = "Synthetic changed subject"
        self.assertEqual(self.observe()["changes"], 1)
        self.api.messages["message-1"].pop("changeKey")
        self.assertEqual(self.observe()["changes"], 1)
        self.assertEqual(self.observe()["changes"], 0)
        self.api.messages["message-1"]["isRead"] = True
        self.assertEqual(self.observe()["changes"], 1)

    def test_restart_uses_committed_delta_cursor_and_does_not_reemit_same_messages(self):
        self.observe()
        cursor = self.current()["folders"]["inbox"]["delta_link"]
        self.api.calls.clear()
        second = consumer.GraphMailConsumer(self.file, api_factory=lambda _: self.api)
        self.assertEqual(second.observe(self.webhook)["changes"], 0)
        self.assertIn(("GET", cursor), self.api.calls)
        self.assertNotIn(("GET", self.delta_initial()), self.api.calls)

    def test_delete_and_move_are_current_folder_observations_and_not_document_acceptance(self):
        for move in (False, True):
            with self.subTest(move=move):
                self.api.messages = {"message-1": message()}
                self.observe()
                if move:
                    self.api.messages["message-1"]["parentFolderId"] = "another-folder"
                else:
                    self.api.messages.clear()
                self.api.pages[self.api.cursor] = {"value": [{"id": "message-1", "@removed": {"reason": "deleted"}}],
                                                   "@odata.deltaLink": self.api.cursor}
                self.observe()
                packet = self.current()
                self.assertEqual(packet["folders"]["inbox"]["messages"], {})
                self.assertEqual(packet["observation"]["changes"][0]["kind"], "REMOVED_FROM_FOLDER")
                self.assertFalse(packet["observation"]["document_received"])
                self.api.pages.clear()

    def test_lifecycle_notifications_reconcile_without_subscription_or_oauth_writes(self):
        server = self.native_server()
        for kind in ("missed", "subscriptionRemoved", "reauthorizationRequired"):
            webhook.receive(self.event(lifecycle=kind), self.webhook,
                            lifecycle=True, wakeup=server.graph_mail_wakeup)
            before = len(self.api.calls)
            server.service_actions()
            self.assertGreater(len(self.api.calls), before)
            self.assertIn("lifecycle." + kind, self.current()["observation"]["lifecycle_signals"])
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))

    def test_empty_intermediate_page_is_followed_to_complete_round(self):
        next_link = self.api.cursor.replace("deltatoken=one", "skiptoken=next")
        self.api.pages[self.delta_initial()] = {"value": [], "@odata.nextLink": next_link}
        self.api.pages[next_link] = {"value": [{"id": "message-1"}], "@odata.deltaLink": self.api.cursor}
        self.assertEqual(self.observe()["changes"], 1)
        self.assertIn(("GET", next_link), self.api.calls)

    def test_partial_round_failure_retains_original_cursor_until_real_recovery_wake(self):
        server = self.native_server()
        before = self.pointer().read_bytes()
        next_link = self.api.cursor.replace("deltatoken=one", "skiptoken=next")
        self.api.pages[self.api.cursor] = {"value": [{"id": "message-1"}], "@odata.nextLink": next_link}
        self.api.pages[next_link] = HTTPError(next_link, 503, "synthetic private failure", {}, None)
        server.graph_mail_wakeup.set()
        server.service_actions()
        self.assertEqual(server.graph_mail_status["status"], "BLOCK")
        self.assertFalse(server.graph_mail_status["provider_readback_performed"])
        self.assert_not_advanced(before)
        calls = len(self.api.calls)
        for _ in range(20):
            server.service_actions()
        self.assertEqual(len(self.api.calls), calls)  # no timed retry
        self.api.pages.clear()
        server.graph_mail_wakeup.set()
        server.service_actions()
        self.assertEqual(self.current()["observation"]["trigger"], "RECOVERY")
        self.assertEqual(server.graph_mail_status["mail_observation"]["changes"], 0)

    def test_expired_delta_cursor_resets_once_and_reconciles_absent_messages(self):
        self.observe()
        stale = self.api.cursor
        self.api.pages[stale] = HTTPError(stale, 410, "expired cursor", {}, None)
        self.api.messages.clear()
        self.api.cursor = stale.replace("one", "reset")
        self.assertEqual(self.observe()["changes"], 1)
        self.assertEqual(self.current()["observation"]["resynced_folders"], ["inbox"])
        self.assertEqual(self.current()["folders"]["inbox"]["messages"], {})

    def test_expired_initial_cursor_has_no_blind_retry(self):
        url = self.delta_initial()
        self.api.pages[url] = HTTPError(url, 410, "expired initial", {}, None)
        with self.assertRaises(HTTPError):
            self.observe()
        self.assertEqual(self.api.calls.count(("GET", url)), 1)
        self.assertFalse(self.pointer().exists())

    def test_foreign_cursor_pagination_cycle_and_incomplete_pages_never_advance(self):
        self.observe()
        before = self.pointer().read_bytes()
        bad_pages = [
            {"value": [], "@odata.nextLink": "https://evil.example.test/steal"},
            {"value": [], "@odata.deltaLink": self.api.cursor.replace("inbox", "other-folder")},
            {"value": [], "@odata.deltaLink": self.api.cursor.replace("/me/", "/users/other/")},
            {"value": [], "@odata.nextLink": self.api.cursor},
            {"value": []}, {"value": {}, "@odata.deltaLink": self.api.cursor},
            {"value": [], "@odata.deltaLink": self.api.cursor, "@odata.nextLink": self.api.cursor},
            {"value": [{"id": ""}], "@odata.deltaLink": self.api.cursor}]
        for page in bad_pages:
            with self.subTest(page=page):
                self.api.pages[self.api.cursor] = page
                with self.assertRaises(consumer.ConsumerError):
                    self.observe()
                self.assert_not_advanced(before)
        self.assertTrue(all(url.startswith(consumer.ORIGIN) for _, url in self.api.calls))

    def test_wrong_mailbox_folder_alias_or_changed_folder_identity_fail_closed(self):
        self.observe()
        before = self.pointer().read_bytes()
        self.api.account = "other-mailbox"
        with self.assertRaises(consumer.ConsumerError):
            self.observe()
        self.assert_not_advanced(before)
        self.api.account = "synthetic-mailbox"
        self.api.folder_ids["inbox"] = "replaced-folder"
        with self.assertRaises(consumer.ConsumerError):
            self.observe()
        self.assert_not_advanced(before)

    def test_duplicate_folder_aliases_and_private_scope_changes_are_not_silently_accepted(self):
        self.binding["folder_ids"] = ["inbox", "alias"]
        self.private(self.file, self.binding)
        self.api.folder_ids["alias"] = self.api.folder_ids["inbox"]
        with self.assertRaises(consumer.ConsumerError):
            self.observe()
        self.assertFalse(self.pointer().exists())

    def test_missing_current_message_fields_or_wrong_id_fail_without_cursor_advance(self):
        self.observe()
        before = self.pointer().read_bytes()
        for bad in ({"id": "wrong-id", "parentFolderId": "folder-inbox", "changeKey": "v"},
                    {"id": "message-1", "parentFolderId": "folder-inbox"},
                    {**message(), "isRead": "false"}, {**message(), "from": "untyped"}):
            self.api.messages["message-1"] = bad
            with self.assertRaises(consumer.ConsumerError):
                self.observe()
            self.assert_not_advanced(before)

    def test_binding_token_privacy_and_symlinks_rejected_before_provider_reads(self):
        for file in (self.file, self.token_file):
            file.chmod(0o644)
            with self.assertRaises(webhook.BindingError):
                self.observe()
            file.chmod(0o600)
        content = self.token_file.read_bytes()
        self.token_file.unlink()
        other = self.root / "other-token"
        other.write_bytes(content)
        other.chmod(0o600)
        self.token_file.symlink_to(other)
        with self.assertRaises(webhook.BindingError):
            self.observe()
        self.assertEqual(self.api.calls, [])

    def test_checkpoint_symlink_tamper_and_missing_native_provenance_block_before_provider(self):
        self.observe()
        pointer = self.pointer()
        raw = pointer.read_bytes()
        key = json.loads(raw)["observation_key"]
        payload = self.state / ".qikvrt/api/inbox" / (key + ".bin")
        original = payload.read_bytes()
        payload.write_bytes(original + b" ")
        self.api.calls.clear()
        with self.assertRaises(consumer.ConsumerError):
            self.observe()
        self.assertEqual(self.api.calls, [])
        payload.write_bytes(original)
        metadata = self.state / ".qikvrt/api/provenance" / (key + "." + key + ".json")
        metadata.rename(metadata.with_suffix(".missing"))
        with self.assertRaises(OSError):
            self.observe()
        pointer.unlink()
        redirect = self.root / "redirect"
        redirect.write_bytes(raw)
        redirect.chmod(0o600)
        pointer.symlink_to(redirect)
        with self.assertRaises(RuntimeError):
            self.observe()
        self.assertEqual(self.api.calls, [])

    def test_failed_native_storage_or_pointer_commit_retains_old_cursor(self):
        self.observe()
        before = self.pointer().read_bytes()
        self.api.messages["message-1"] = message("version-2")
        with patch.object(consumer, "run_handler", return_value={"effect_state": "EFFECT_ACK_BLOCK"}):
            with self.assertRaises(consumer.ConsumerError):
                self.observe()
        self.assert_not_advanced(before)
        with patch.object(consumer, "atomic_write_bytes", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                self.observe()
        self.assert_not_advanced(before)
        self.assertEqual(self.observe()["changes"], 1)
        self.assertEqual(self.observe()["changes"], 0)

    def test_changed_consumer_or_ingress_binding_during_read_has_no_cursor_effect(self):
        self.observe()
        before = self.pointer().read_bytes()
        original = copy.deepcopy(self.binding)
        def change(url):
            altered = copy.deepcopy(original)
            altered["folder_ids"] = ["archive"]
            self.private(self.file, altered)
        self.api.on_read = change
        with self.assertRaises(webhook.BindingError):
            self.observe()
        self.assert_not_advanced(before)
        self.private(self.file, original)
        self.api.on_read = None
        with self.assertRaises(webhook.BindingError):
            self.consumer.observe(self.webhook, binding_guard=lambda: {})
        self.assert_not_advanced(before)

    def test_concurrent_provider_round_cannot_overwrite_a_newer_native_checkpoint(self):
        self.observe()
        barrier = threading.Barrier(2)
        original = consumer.run_handler
        outcomes = []
        def ingest(cfg):
            value = original(cfg)
            barrier.wait(5)
            return value
        def run():
            try:
                outcomes.append(self.observe()["status"])
            except consumer.ConsumerError:
                outcomes.append("CONCURRENT_CURSOR_BLOCK")
        with patch.object(consumer, "run_handler", side_effect=ingest):
            threads = [threading.Thread(target=run) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(10)
                self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(outcomes), ["CONCURRENT_CURSOR_BLOCK", "OBSERVED"])
        self.assertEqual(self.current()["observation"]["changes"], [])

    def test_native_idle_never_queries_provider_and_concurrent_wake_survives_read(self):
        server = self.native_server()
        calls = len(self.api.calls)
        for _ in range(20):
            server.service_actions()
        self.assertEqual(len(self.api.calls), calls)
        self.api.on_read = lambda _: server.graph_mail_wakeup.set()
        server.graph_mail_wakeup.set()
        server.service_actions()
        self.assertTrue(server.graph_mail_wakeup.is_set())
        self.api.on_read = None
        server.service_actions()
        self.assertFalse(server.graph_mail_wakeup.is_set())

    def test_real_native_http_wakeup_produces_private_observation_and_sanitized_health(self):
        server = self.native_server()
        observed = threading.Event()
        original = server.service_actions
        def actions():
            original()
            if (server.graph_mail_status.get("records") == 1
                    and server.graph_mail_status.get("mail_observation", {}).get("changes") == 1):
                observed.set()
        server.service_actions = actions
        self.api.messages["message-1"] = message("version-2")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = http.client.HTTPConnection(*server.server_address, timeout=5)
            client.request("POST", webhook.MAIL_PATH, webhook.wire(self.event()),
                           {"Content-Type": "application/json"})
            response = client.getresponse()
            self.assertEqual(response.status, 202)
            response.read()
            client.close()
            self.assertTrue(observed.wait(5))
            client = http.client.HTTPConnection(*server.server_address, timeout=5)
            client.request("GET", "/health")
            response = client.getresponse()
            status = json.loads(response.read())["graph_mail_reconciliation"]
            client.close()
            self.assertTrue(status["provider_readback_performed"])
            self.assertEqual(status["mail_observation"]["changes"], 1)
            self.assertEqual(self.current()["observation"]["trigger"], "DURABLE_WAKE")
        finally:
            server.shutdown()
            thread.join(5)

    def test_provider_round_bounds_fail_closed_with_no_partial_observation(self):
        for bound in ("MAX_MESSAGES", "MAX_READS"):
            with patch.object(consumer, bound, 0):
                with self.assertRaises(consumer.ConsumerError):
                    self.observe()
            self.assertFalse(self.pointer().exists())
        next_link = self.api.cursor.replace("deltatoken=one", "skiptoken=next")
        self.api.pages[self.delta_initial()] = {"value": [], "@odata.nextLink": next_link}
        with patch.object(consumer, "MAX_PAGES", 1):
            with self.assertRaises(consumer.ConsumerError):
                self.observe()
        self.assertFalse(self.pointer().exists())

    def test_private_inbox_readback_deduplicates_committed_changes_and_ignores_orphans(self):
        self.observe()
        first = json.loads(self.pointer().read_bytes())["observation_key"]
        self.assertEqual(len(self.consumer.read_observations(self.webhook)), 1)
        self.api.messages["message-1"] = message("version-2")
        with patch.object(consumer, "atomic_write_bytes", side_effect=OSError("synthetic lost checkpoint")):
            with self.assertRaises(OSError):
                self.observe()
        self.assertEqual(self.consumer.read_observations(self.webhook, after_key=first), [])
        self.observe()
        self.observe()
        pending = self.consumer.read_observations(self.webhook, after_key=first)
        self.assertEqual([len(p["observation"]["changes"]) for p in pending], [1, 0])
        last = pending[-1]["observation_key"]
        self.assertEqual(self.consumer.read_observations(self.webhook, after_key=last), [])
        with self.assertRaises(consumer.ConsumerError):
            self.consumer.read_observations(self.webhook, after_key="mail-observation-" + "0" * 64)
        with self.assertRaises(consumer.ConsumerError):
            self.consumer.read_observations(self.webhook, limit=1)

    def test_unbound_or_invalid_oauth_consumer_does_not_become_an_active_worker(self):
        with patch.dict(os.environ, {"QIKVRT_GRAPH_WEBHOOK_BINDING": ""}):
            with self.assertRaises(ValueError):
                self.native_server()
        self.token_file.unlink()
        with self.assertRaises(OSError):
            self.native_server()
        self.assertEqual(self.api.calls, [])

    def test_native_runtime_imports_with_no_site_packages_from_another_cwd(self):
        source = Path(__file__).resolve().parents[1] / "src"
        code = "import sys; sys.path.insert(0, sys.argv[1]); import qikvrt_github_api_shim; print('NATIVE_IMPORT_OK')"
        run = run_bounded([sys.executable, "-B", "-S", "-c", code, str(source)],
                          cwd=self.root, env=os.environ.copy(), timeout=10, max_output_bytes=4096)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), "NATIVE_IMPORT_OK")

    def test_fresh_process_crash_before_pointer_then_restart_preserves_one_message_effect(self):
        self.observe()
        before = self.pointer().read_bytes()
        fixture = self.root / "synthetic-provider.json"
        self.private(fixture, {"message-1": message("version-2")})
        child = '''
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'src')
import qikvrt_graph_mail_consumer as native
from tests.test_graph_mail_consumer import SyntheticGraph
from qikvrt_github_api_shim import QikvrtGitHubApiServer, QikvrtGitHubApiShim
provider = SyntheticGraph()
provider.messages = json.loads(Path(sys.argv[2]).read_bytes())
native.GraphMailConsumer.__init__.__kwdefaults__['api_factory'] = lambda _: provider
if sys.argv[1] == 'crash':
    native.atomic_write_bytes = lambda *args, **kwargs: os._exit(0)
server = QikvrtGitHubApiServer(('127.0.0.1', 0), QikvrtGitHubApiShim)
print(json.dumps(server.graph_mail_status), flush=True)
os._exit(0)
'''
        results = []
        for phase in ("crash", "restart", "restart"):
            run = run_bounded([sys.executable, "-B", "-S", "-c", child, phase, str(fixture)],
                              cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(),
                              timeout=15, max_output_bytes=4096)
            self.assertEqual(run.returncode, 0, run.stderr)
            if phase == "crash":
                self.assert_not_advanced(before)
            else:
                results.append(json.loads(run.stdout)["mail_observation"]["changes"])
        self.assertEqual(results, [1, 0])


def request_message(text="Bitte senden Sie mir das Formular", *, sender="sender@example.test", urgent=False):
    value = message(subject="DRINGEND: Synthetic private request" if urgent else "Synthetic private request")
    value["from"]["emailAddress"]["address"] = sender
    value.update(toRecipients=[{"emailAddress": {"address": "owner@example.test"}}],
                 ccRecipients=[], isDraft=False, uniqueBody={"contentType": "text", "content": text},
                 internetMessageHeaders=[])
    return value


class MailTaskTests(unittest.TestCase):
    private = ConsumerTests.private
    native_server = ConsumerTests.native_server
    event = ConsumerTests.event
    observe = ConsumerTests.observe

    def setUp(self):
        ConsumerTests.setUp(self)
        self.task_file = self.root / "tasks.json"
        self.task_binding = {"schema": "qikvrt_graph_mail_task_binding_v1",
            "repository": "owner/repository", "responsibility_owner": "owner",
            "state_root": str(self.state), "accepted_effect_scope": consumer.MAIL_TASK_SCOPE,
            "owner_addresses": ["owner@example.test"], "human_senders": ["sender@example.test"],
            "timezone": "Europe/Paris"}
        self.private(self.task_file, self.task_binding)
        self.consumer = consumer.GraphMailConsumer(self.file, api_factory=lambda _: self.api,
                                                   task_binding_path=self.task_file)
        self.tasks = self.consumer.task_consumer
        self.api.messages = {"message-1": request_message()}
        env = patch.dict(os.environ, {"QIKVRT_GRAPH_MAIL_TASK_BINDING": str(self.task_file)})
        env.start()
        self.addCleanup(env.stop)

    def task_pointer(self):
        return self.state / ".qikvrt/api/out/graph-mail-tasks-current.json"

    def current_tasks(self):
        return self.tasks.read_private_state(self.webhook)

    def consume(self):
        return self.tasks.consume(self.webhook)

    def test_native_startup_derives_one_private_task_and_uses_existing_day_plan(self):
        original = copy.deepcopy(self.api.messages)
        server = self.native_server()
        status = server.graph_mail_status["private_mail_tasks"]
        self.assertEqual(status["tasks"], 1)
        packet = self.current_tasks()
        task = packet["day_plan"]["tasks"][0]
        self.assertEqual(task["request_excerpt"], "Bitte senden Sie mir das Formular")
        self.assertEqual(task["due"], None)
        self.assertEqual(task["state"], "OPEN")
        self.assertEqual(packet["mail"]["message-1"]["classification"]["category"], "DIRECT_HUMAN_REQUEST")
        self.assertEqual(packet["day_plan"]["effect_scope"], consumer.MAIL_TASK_SCOPE)
        self.assertFalse(packet["day_plan"]["notification_sent"])
        self.assertEqual(self.api.messages, original)
        for marker in ("Formular", "sender@example.test", "owner@example.test", "mail-request-", "mail-observation-", SECRET):
            self.assertNotIn(marker, json.dumps(server.graph_mail_status))

    def test_actual_native_http_delivery_runs_task_lane(self):
        server = self.native_server()
        before = self.current_tasks()["day_plan"]["tasks"][0]["id"]
        self.api.messages["message-1"] = request_message("Please review the updated form", urgent=True)
        event = threading.Event()
        original = server.service_actions
        def actions():
            original()
            if self.current_tasks()["day_plan"]["tasks"][0]["request_excerpt"] == "Please review the updated form":
                event.set()
        server.service_actions = actions
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = http.client.HTTPConnection(*server.server_address, timeout=5)
            client.request("POST", webhook.MAIL_PATH, webhook.wire(self.event()), {"Content-Type": "application/json"})
            response = client.getresponse()
            self.assertEqual(response.status, 202)
            self.assertNotIn("updated form", response.read().decode())
            client.close()
            self.assertTrue(event.wait(5))
            self.assertEqual(self.current_tasks()["day_plan"]["tasks"][0]["id"], before)
        finally:
            server.shutdown()
            thread.join(5)

    def test_replay_version_read_and_restart_keep_one_task_with_stable_identity(self):
        server = self.native_server()
        first = self.current_tasks()["day_plan"]["tasks"][0]["id"]
        for i in range(3):
            self.api.messages["message-1"]["changeKey"] = "version-" + str(i)
            self.api.messages["message-1"]["isRead"] = bool(i % 2)
            webhook.receive(self.event(), self.webhook, wakeup=server.graph_mail_wakeup)
            server.service_actions()
            self.assertEqual([t["id"] for t in self.current_tasks()["day_plan"]["tasks"]], [first])
        before = self.task_pointer().read_bytes()
        self.assertEqual(self.consume()["status"], "NOOP")
        self.assertEqual(self.task_pointer().read_bytes(), before)
        restarted = self.native_server()
        self.assertEqual(restarted.graph_mail_status["private_mail_tasks"]["tasks"], 1)
        self.assertEqual(self.current_tasks()["day_plan"]["tasks"][0]["id"], first)

    def test_updated_request_updates_source_but_does_not_duplicate_task(self):
        self.observe(); self.consume()
        first = self.current_tasks()["day_plan"]["tasks"][0]
        self.api.messages["message-1"] = request_message("Could you sign the form", urgent=True)
        self.observe(); self.consume()
        tasks = self.current_tasks()["day_plan"]["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], first["id"])
        self.assertNotEqual(tasks[0]["source_sha256"], first["source_sha256"])
        self.assertTrue(tasks[0]["urgent"])

    def test_important_urgent_information_creates_attention_without_invented_task(self):
        self.api.messages["message-1"] = request_message("FYI: an update is available", urgent=True)
        self.api.messages["message-1"]["importance"] = "high"
        self.observe(); self.consume()
        plan = self.current_tasks()["day_plan"]
        self.assertEqual(plan["tasks"], [])
        self.assertEqual(len(plan["attention"]), 1)
        self.assertTrue(plan["attention"][0]["urgent"])
        self.assertFalse(plan["due_times_inferred"])

    def test_unknown_sender_request_is_review_attention_without_human_claim_or_task(self):
        self.api.messages["message-1"] = request_message(sender="unknown@example.test")
        self.observe(); self.consume()
        plan = self.current_tasks()["day_plan"]
        self.assertEqual(plan["tasks"], [])
        self.assertEqual(plan["attention"][0]["category"], "DIRECT_REQUEST_SENDER_UNVERIFIED")

    def test_bulk_auto_no_reply_cc_quote_draft_self_and_negation_cannot_derive_task(self):
        fixtures = []
        bulk = request_message(); bulk["internetMessageHeaders"] = [{"name": "List-Id", "value": "synthetic list"}]; fixtures.append(bulk)
        auto = request_message(); auto["internetMessageHeaders"] = [{"name": "Auto-Submitted", "value": "auto-generated"}]; fixtures.append(auto)
        fixtures.append(request_message(sender="no-reply@example.test"))
        cc = request_message(); cc["ccRecipients"] = cc["toRecipients"]; cc["toRecipients"] = []; fixtures.append(cc)
        fixtures.append(request_message("> Please send the form"))
        fixtures.append(request_message("FYI\nFrom: someone@example.test\nPlease send the form"))
        draft = request_message(); draft["isDraft"] = True; fixtures.append(draft)
        fixtures.append(request_message(sender="owner@example.test"))
        fixtures.append(request_message("Bitte senden Sie das Formular nicht"))
        html = request_message(); html["uniqueBody"]["contentType"] = "html"; fixtures.append(html)
        for value in fixtures:
            result = consumer.classify_private_mail(value, owner_addresses=self.task_binding["owner_addresses"],
                                                   human_senders=self.task_binding["human_senders"])
            self.assertFalse(result["task_derivable"], value)

    def test_truncated_preview_cannot_invent_action_when_current_unique_body_is_missing(self):
        value = request_message()
        value.pop("uniqueBody")
        value["bodyPreview"] = "Please send the form"
        self.api.messages["message-1"] = value
        self.observe(); self.consume()
        self.assertEqual(self.current_tasks()["day_plan"]["tasks"], [])
        self.assertEqual(self.current_tasks()["mail"]["message-1"]["classification"]["category"], "INSUFFICIENT_PROJECTION")

    def test_german_english_french_requests_are_source_bound_without_inferred_deadline(self):
        for text in ("Bitte prüfen Sie die Unterlagen heute", "Please send the form tomorrow", "Merci de confirmer le rendez-vous"):
            result = consumer.classify_private_mail(request_message(text), owner_addresses=self.task_binding["owner_addresses"],
                                                   human_senders=self.task_binding["human_senders"])
            self.assertTrue(result["task_derivable"], text)
            self.assertEqual(result["request_excerpt"], text)

    def test_delete_or_move_out_does_not_mark_task_completed(self):
        self.observe(); self.consume()
        self.api.messages.clear()
        self.api.pages[self.api.cursor] = {"value": [{"id": "message-1", "@removed": {"reason": "deleted"}}],
                                          "@odata.deltaLink": self.api.cursor}
        self.observe(); self.consume()
        plan = self.current_tasks()["day_plan"]
        self.assertEqual(plan["tasks"][0]["state"], "SOURCE_UNAVAILABLE_REVIEW_REQUIRED")
        self.assertEqual(plan["attention"], [])
        self.assertFalse(plan["task_completion_proven"])

    def test_move_between_selected_folders_retains_single_task_and_membership(self):
        self.binding["folder_ids"] = ["inbox", "archive"]
        self.private(self.file, self.binding)
        self.api.folder_ids["archive"] = "folder-archive"
        archive_cursor = "https://graph.microsoft.com" + consumer.delta_path("archive") + "?$deltatoken=archive"
        self.api.pages["https://graph.microsoft.com" + consumer.delta_path("archive") + consumer.SELECT] = {"value": [], "@odata.deltaLink": archive_cursor}
        self.observe(); self.consume()
        first = self.current_tasks()["day_plan"]["tasks"][0]["id"]
        self.api.messages["message-1"]["parentFolderId"] = "folder-archive"
        self.api.pages[self.api.cursor] = {"value": [{"id": "message-1"}], "@odata.deltaLink": self.api.cursor}
        self.api.pages[archive_cursor] = {"value": [{"id": "message-1"}], "@odata.deltaLink": archive_cursor}
        self.observe(); self.consume()
        packet = self.current_tasks()
        self.assertEqual(packet["mail"]["message-1"]["folders"], ["archive"])
        self.assertEqual([t["id"] for t in packet["day_plan"]["tasks"]], [first])
        self.assertEqual(packet["day_plan"]["tasks"][0]["state"], "OPEN")

    def test_changed_message_without_request_requires_owner_review_without_false_completion(self):
        self.observe(); self.consume()
        self.api.messages["message-1"] = request_message("FYI only")
        self.observe(); self.consume()
        self.assertEqual(self.current_tasks()["day_plan"]["tasks"][0]["state"], "SOURCE_CHANGED_REVIEW_REQUIRED")

    def test_storage_loss_leaves_no_accepted_key_then_recovers_same_single_task(self):
        self.observe()
        with patch.object(consumer, "atomic_write_bytes", side_effect=OSError("synthetic task pointer failure")):
            with self.assertRaises(OSError): self.consume()
        self.assertFalse(self.task_pointer().exists())
        self.assertIsNone(self.current_tasks())
        self.consume()
        first = self.task_pointer().read_bytes()
        self.assertEqual(self.consume()["tasks"], 1)
        self.assertEqual(self.task_pointer().read_bytes(), first)

    def test_corrupt_native_provenance_blocks_without_accepted_task_state(self):
        self.observe()
        provider_pointer = self.state / ".qikvrt/api/out/graph-mail-current.json"
        key = json.loads(provider_pointer.read_bytes())["observation_key"]
        provenance = self.state / ".qikvrt/api/provenance" / (key + "." + key + ".json")
        provenance.unlink()
        with self.assertRaises((OSError, RuntimeError, ValueError)): self.consume()
        self.assertFalse(self.task_pointer().exists())

    def test_corrupt_task_pointer_and_capsule_never_duplicate_or_accept(self):
        self.observe(); self.consume()
        original = self.task_pointer().read_bytes()
        key = json.loads(original)["task_checkpoint_key"]
        capsule = consumer.dirs(self.state)["inbox"] / (key + ".bin")
        raw = capsule.read_bytes()
        capsule.write_bytes(raw + b" ")
        with self.assertRaises((OSError, RuntimeError, ValueError)): self.consume()
        self.assertEqual(self.task_pointer().read_bytes(), original)

    def test_changed_private_task_binding_cannot_reuse_previous_tasks(self):
        self.observe(); self.consume()
        before = self.task_pointer().read_bytes()
        self.task_binding["human_senders"] = []
        self.private(self.task_file, self.task_binding)
        with self.assertRaises(consumer.ConsumerError): self.consume()
        self.assertEqual(self.task_pointer().read_bytes(), before)

    def test_concurrent_task_writer_is_rejected_instead_of_losing_update(self):
        self.observe()
        original = self.consumer.read_observations
        def race(*args, **kwargs):
            rows = original(*args, **kwargs)
            with patch.object(self.consumer, "read_observations", side_effect=original): self.consume()
            return rows
        with patch.object(self.consumer, "read_observations", side_effect=race):
            with self.assertRaises(consumer.ConsumerError): self.consume()
        self.assertEqual(len(self.current_tasks()["day_plan"]["tasks"]), 1)

    def test_no_idle_poll_or_timed_retry_and_runtime_errors_do_not_publish_content(self):
        server = self.native_server()
        calls = list(self.api.calls)
        before = self.task_pointer().read_bytes()
        for _ in range(5): server.service_actions()
        self.assertEqual(self.api.calls, calls)
        self.assertEqual(self.task_pointer().read_bytes(), before)
        with patch.object(self.tasks, "consume", side_effect=consumer.ConsumerError("PRIVATE_MAIL_SECRET")):
            server.graph_mail_wakeup.set(); server.service_actions()
        self.assertEqual(server.graph_mail_status["status"], "BLOCK")
        self.assertNotIn("PRIVATE_MAIL_SECRET", json.dumps(server.graph_mail_status))
        calls = list(self.api.calls)
        for _ in range(5): server.service_actions()
        self.assertEqual(self.api.calls, calls)

    def test_lifecycle_is_private_state_without_control_plane_tasks_or_effect(self):
        server = self.native_server()
        for kind in ("missed", "subscriptionRemoved", "reauthorizationRequired"):
            webhook.receive(self.event(lifecycle=kind), self.webhook, lifecycle=True, wakeup=server.graph_mail_wakeup)
            server.service_actions()
        plan = self.current_tasks()["day_plan"]
        self.assertEqual(len(plan["tasks"]), 1)
        self.assertEqual(len(plan["lifecycle_signals"]), 3)
        self.assertFalse(plan["effect_ack_done"])
        self.assertTrue(all(method == "GET" for method, _ in self.api.calls))

    def test_invalid_binding_missing_provider_symlink_and_address_bounds_block_startup(self):
        self.task_file.chmod(0o644)
        with self.assertRaises((OSError, RuntimeError, ValueError)): self.native_server()
        self.task_file.chmod(0o600)
        self.task_binding["owner_addresses"] = []
        self.private(self.task_file, self.task_binding)
        with self.assertRaises(consumer.BindingError): self.native_server()
        with patch.dict(os.environ, {"QIKVRT_GRAPH_MAIL_CONSUMER_BINDING": ""}):
            with self.assertRaises(ValueError): self.native_server()

    def test_pending_committed_tasks_recover_before_an_unavailable_provider_read(self):
        self.observe()
        with patch.object(self.api, "request", side_effect=HTTPError("https://graph.microsoft.com", 401, "synthetic OAuth gate", {}, None)):
            with self.assertRaises(HTTPError): self.native_server()
        self.assertEqual(len(self.current_tasks()["day_plan"]["tasks"]), 1)

    def test_fabricated_task_excerpt_with_native_storage_provenance_is_rejected(self):
        self.observe(); self.consume()
        packet = copy.deepcopy(self.current_tasks())
        key = next(iter(packet["tasks"]))
        packet["tasks"][key]["request_excerpt"] = "Please transfer invented money"
        packet["day_plan"] = consumer.project_private_mail_plan(packet["mail"], packet["tasks"], packet["lifecycle_signals"],
            owner="owner", timezone="Europe/Paris", observed_at=packet["observed_at_utc"])
        raw = webhook.wire(packet)
        candidate = "mail-tasks-" + hashlib.sha256(raw).hexdigest()
        consumer.run_handler(self.consumer._cfg(self.binding, candidate, "ingest", raw))
        with self.assertRaises(consumer.ConsumerError):
            self.tasks._packet(self.binding, self.task_binding, candidate)

    def test_orphan_provider_observation_is_never_accepted_as_a_task_source(self):
        self.observe(); self.consume()
        packet = copy.deepcopy(self.current_tasks())
        self.api.messages["message-1"] = request_message("Please sign an orphan form")
        with patch.object(consumer, "atomic_write_bytes", side_effect=OSError("synthetic uncommitted provider pointer")):
            with self.assertRaises(OSError): self.observe()
        current = packet["accepted_observation_key"]
        orphan = next(p.stem for p in consumer.dirs(self.state)["inbox"].glob("mail-observation-*.bin") if p.stem != current)
        packet["accepted_observation_key"] = orphan
        raw = webhook.wire(packet)
        candidate = "mail-tasks-" + hashlib.sha256(raw).hexdigest()
        consumer.run_handler(self.consumer._cfg(self.binding, candidate, "ingest", raw))
        with self.assertRaises(consumer.ConsumerError):
            self.tasks._packet(self.binding, self.task_binding, candidate)

    def test_urgent_tasks_sort_first_and_plan_date_uses_owner_timezone(self):
        second = request_message("Please review the urgent form", urgent=True)
        second["id"] = "message-2"
        self.api.messages["message-2"] = second
        self.observe(); self.consume()
        plan = self.current_tasks()["day_plan"]
        self.assertEqual(len(plan["tasks"]), 2)
        self.assertEqual(plan["tasks"][0]["source_message_id"], "message-2")
        dated = consumer.project_private_mail_plan({}, {}, [], owner="owner", timezone="Europe/Paris",
                                                 observed_at="2026-10-06T23:30:00Z")
        self.assertEqual(dated["local_date"], "2026-10-07")

    def test_bad_current_task_fields_fail_closed_without_any_task_pointer(self):
        for field, value in (("toRecipients", [{"emailAddress": {"address": "invalid"}}]),
                             ("internetMessageHeaders", [{"name": "List-Id", "value": 9}]),
                             ("uniqueBody", {"contentType": "text", "content": "x" * 65537})):
            candidate = request_message(); candidate[field] = value
            self.api.messages["message-1"] = candidate
            with self.assertRaises((ValueError, RuntimeError)): self.observe()
            self.assertFalse(self.task_pointer().exists())

    def test_private_task_binding_and_checkpoint_symlinks_are_rejected(self):
        backing = self.root / "task-backing.json"
        self.task_file.rename(backing)
        self.task_file.symlink_to(backing)
        with self.assertRaises((ValueError, RuntimeError, OSError)): self.consume()
        self.task_file.unlink(); backing.rename(self.task_file)
        self.observe(); self.consume()
        pointer = self.task_pointer()
        backing = pointer.with_name("task-pointer-backing.json")
        pointer.rename(backing); pointer.symlink_to(backing)
        with self.assertRaises((ValueError, RuntimeError, OSError)): self.consume()

    def test_fresh_process_loss_before_task_pointer_recovers_exactly_one_task(self):
        self.observe()
        child = r"""
import json, os, sys
from pathlib import Path
sys.path.insert(0, 'src')
import qikvrt_graph_mail_consumer as native
from tests.test_graph_mail_consumer import SyntheticGraph
webhook = json.loads(Path(os.environ['QIKVRT_GRAPH_WEBHOOK_BINDING']).read_bytes())
c = native.GraphMailConsumer(os.environ['QIKVRT_GRAPH_MAIL_CONSUMER_BINDING'],
    api_factory=lambda _: SyntheticGraph(), task_binding_path=os.environ['QIKVRT_GRAPH_MAIL_TASK_BINDING'])
if sys.argv[1] == 'crash':
    native.atomic_write_bytes = lambda *args, **kwargs: os._exit(73)
result = c.task_consumer.consume(webhook)
print(json.dumps(result), flush=True)
os._exit(0)
"""
        for phase in ("crash", "restart", "restart"):
            run = run_bounded([sys.executable, "-B", "-S", "-c", child, phase],
                              cwd=Path(__file__).resolve().parents[1], env=os.environ.copy(),
                              timeout=15, max_output_bytes=4096)
            self.assertEqual(run.returncode, 73 if phase == "crash" else 0, run.stderr)
            if phase == "crash": self.assertFalse(self.task_pointer().exists())
            else:
                status = json.loads(run.stdout)
                self.assertEqual(status["tasks"], 1)
                self.assertNotIn("Formular", run.stdout)



class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.token = Path(self.temp.name) / "token"
        self.token.write_text("synthetic-only-bearer")
        self.token.chmod(0o600)
        self.api = Graph(self.token)

    def test_fixed_read_only_origin_and_path_prevent_token_redirect(self):
        for url in ("http://graph.microsoft.com/v1.0/me/messages/id", "https://evil.example.test/v1.0/me/messages/id",
                    "https://graph.microsoft.com:443/v1.0/me/messages/id", "https://graph.microsoft.com/v1.0/users/other/messages/id",
                    "https://graph.microsoft.com/v1.0/me/messages/id#fragment", "https://graph.microsoft.com/v1.0/me/messages/id\n"):
            with self.assertRaises(SubscriptionError):
                self.api.mail_get(url)
        self.assertTrue(any(type(h).__name__ == "_NoRedirect" for h in self.api.opener.handlers))

    def test_transport_is_get_only_has_immutable_ids_and_captures_exact_private_readback(self):
        raw = b'{"id":"message-1"}'
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return raw
        seen = []
        def open_request(request, timeout):
            seen.append(request)
            return Response()
        url = consumer.ORIGIN + "me/messages/message-1" + consumer.SELECT
        with patch.object(self.api.opener, "open", side_effect=open_request):
            self.assertEqual(self.api.mail_get(url), {"id": "message-1"})
        self.assertEqual(seen[0].get_method(), "GET")
        self.assertEqual(seen[0].get_header("Prefer"), 'IdType="ImmutableId", outlook.body-content-type="text"')
        self.assertEqual(self.api.last_readback["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("synthetic-only-bearer", json.dumps(self.api.last_readback))

    def test_duplicate_nonfinite_and_oversized_provider_json_fail_closed(self):
        for raw in (b'{"id":1,"id":2}', b'{"value":NaN}', b" " * 1048577):
            class Response:
                def __enter__(self): return self
                def __exit__(self, *args): return False
                def read(self, limit): return raw
            with patch.object(self.api.opener, "open", return_value=Response()):
                with self.assertRaises((ValueError, SubscriptionError)):
                    self.api.mail_get(consumer.ORIGIN + "me/messages/message-1")


if __name__ == "__main__":
    unittest.main()
