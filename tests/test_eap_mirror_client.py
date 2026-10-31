#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: Claude (Anthropic).
"""Mirror EAP client against the original Runtime, OwnerREST and EAP handler over real local HTTP.

The principal guard is the same isolated fixture as tests/test_effect_ack_http_service.py;
production uses the original S1 OwnerHTTP guard and public monitor unchanged.
This is local acceptance of the client, not delivery to the VPS.
"""
import hmac
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
import qikvrt_effect_ack_http_service as service  # noqa: E402
import qikvrt_effect_ack_http_terminal as terminal  # noqa: E402
import qikvrt_temdd_event_ledger as native  # noqa: E402
from tools import qikvrt_eap_mirror_client as mirror  # noqa: E402
spec = importlib.util.spec_from_file_location("eap_self_host_mirror", ROOT / "tools/qikvrt_self_host.py")
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)


class MirrorClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"; self.root.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-q"); git("config", "user.name", "Local EAP fixture"); git("config", "user.email", "fixture@example.invalid")
        git("config", "commit.gpgsign", "false")
        (self.root / "SOURCE.txt").write_text("Isolated original Runtime test subject.\n")
        git("add", "SOURCE.txt"); git("commit", "-qm", "Local fixture")
        state = Path(self.temp.name) / "state"; state.mkdir(mode=0o700)
        self.runtime = native.Runtime(self.root, state, "ingolf-lohmann/qik-vrt", 658)
        self.addCleanup(lambda: self.runtime.ledger.close())
        rest = host.OwnerREST(self.runtime, terminal, state)
        grant = self.grant = {"principal": "claude:mirror", "token": "mirror-fixture-capability-" + "b" * 40,
                              "permissions": ["prepare", "commit", "readback"]}
        class Guarded(native.make_handler(self.runtime)):
            def owner_guard(handler, permission):
                if not hmac.compare_digest(handler.headers.get("Authorization", ""), "Bearer " + grant["token"]):
                    handler._hold("AUTHENTICATION_REQUIRED", 401); return None
                if handler.headers.get("QIKVRT-Owner") != grant["principal"] or permission not in grant["permissions"]:
                    handler._hold("PRINCIPAL_CAPABILITY_REQUIRED", 403); return None
                return grant
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), service.make_handler(Guarded, rest))
        thread = threading.Thread(target=self.server.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (self.server.shutdown(), self.server.server_close(), thread.join(2)))
        self.base = "http://127.0.0.1:" + str(self.server.server_port)
        self.direct = mirror.urllib.request.build_opener(mirror.urllib.request.ProxyHandler({}))

    def inputs(self):
        return [e for e in self.runtime.ledger.replay(0) if e.get("payload", {}).get("adapter") == "QIKVRT_OWNER_REST_TERMINAL_V1"]

    def test_delivers_one_observation_with_independent_readback(self):
        text = "Mirror finding: PR #658 head a56b0632 verify PASS; merge order sha256:8647139d"
        client = mirror.Client(self.base, self.grant["principal"], self.grant["token"], self.direct)
        result = client.deliver("mirror-pr658-finding-1", text)
        self.assertEqual(result["state"], "DELIVERED_TO_AUTHORITY_LEDGER")
        self.assertFalse(result["effect_ack_done"])
        self.assertEqual(result["subject"], self.runtime.subject)
        self.assertEqual([s["status"] for s in result["trace"]], [200] * 8)
        events = self.inputs()
        self.assertEqual(len(events), 1)
        self.assertNotIn(self.grant["token"], json.dumps(self.runtime.ledger.replay(0)))
        self.assertNotIn(self.grant["token"], json.dumps(result))
        again = mirror.Client(self.base, self.grant["principal"], self.grant["token"], self.direct).deliver("mirror-pr658-finding-1", text)
        self.assertEqual(again["durable_readback"], result["durable_readback"])
        self.assertEqual(len(self.inputs()), 1)

    def test_wrong_token_or_principal_holds_before_any_input(self):
        for principal, token in (("claude:mirror", "x" * 64), ("someone:else", self.grant["token"])):
            with self.subTest(principal=principal):
                with self.assertRaises(mirror.Hold) as held:
                    mirror.Client(self.base, principal, token, self.direct).deliver("mirror-denied", "denied")
                self.assertRegex(str(held.exception), r"HTTP_40[13] /api/eap/effect")
        self.assertEqual(self.inputs(), [])

    def test_tampered_context_is_refused_before_commit(self):
        client = mirror.Client(self.base, self.grant["principal"], self.grant["token"], self.direct)
        original = client.call
        def tamper(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path.endswith("/context"):
                value = json.loads(json.dumps(value)); value["latest_hash"] = "sha256:" + "0" * 64
            return value
        client.call = tamper
        with self.assertRaises(mirror.Hold) as held:
            client.deliver("mirror-tampered", "tampered")
        self.assertIn("LOCAL_RELEASE_VERIFICATION_FAILED", str(held.exception))
        self.assertEqual(self.inputs(), [])

    def test_plain_http_to_a_remote_host_is_refused(self):
        with self.assertRaises(mirror.Hold):
            mirror.Client("http://raumzeitterminal.de", "claude:mirror", "t" * 40)

    def test_redirect_never_forwards_the_mirror_credential(self):
        captured = []
        class Trap(BaseHTTPRequestHandler):
            def do_GET(handler):
                captured.append(handler.headers.get("Authorization"))
                handler.send_response(200); handler.end_headers(); handler.wfile.write(b"{}")
            do_POST = do_GET
            def log_message(self, *args):
                pass
        trap = ThreadingHTTPServer(("127.0.0.1", 0), Trap)
        thread = threading.Thread(target=trap.serve_forever, daemon=True); thread.start()
        self.addCleanup(lambda: (trap.shutdown(), trap.server_close(), thread.join(2)))
        original = self.server.RequestHandlerClass.do_POST
        def redirect(handler):
            handler.send_response(302)
            handler.send_header("Location", "http://127.0.0.1:" + str(trap.server_port) + "/trap")
            handler.end_headers()
        self.server.RequestHandlerClass.do_POST = redirect
        self.addCleanup(setattr, self.server.RequestHandlerClass, "do_POST", original)
        with self.assertRaises(mirror.Hold):
            mirror.Client(self.base, self.grant["principal"], self.grant["token"], self.direct).deliver("redirect", "test")
        self.assertEqual(captured, [], "A redirect must never receive the bearer credential")
        self.assertEqual(self.inputs(), [])

    def test_consistent_but_wrong_receipts_are_not_delivery(self):
        for field in ("principal", "request_id", "subject", "terminal_input", "payload_digest", "ledger_digest", "id"):
            with self.subTest(field=field):
                client = mirror.Client(self.base, self.grant["principal"], self.grant["token"], self.direct)
                original = client.call
                def tamper(path, *args, **kwargs):
                    value = original(path, *args, **kwargs)
                    if "native_receipt" in value or path.startswith("/api/eap/receipts/"):
                        value = json.loads(json.dumps(value))
                        receipt = value.get("native_receipt", value)
                        event = receipt["durable_readback"]
                        if field in ("principal", "request_id"):
                            receipt[field] = "wrong"
                        elif field == "subject":
                            event["subject"]["head"] = "0" * 40
                        elif field == "terminal_input":
                            event["payload"]["terminal_input"]["text"] = "wrong"
                        else:
                            event[field] = ("0" * 32 + ":1") if field == "id" else "0" * 64
                    return value
                client.call = tamper
                with self.assertRaises(mirror.Hold):
                    client.deliver("wrong-receipt-" + field, "bound observation")


if __name__ == "__main__":
    unittest.main()
