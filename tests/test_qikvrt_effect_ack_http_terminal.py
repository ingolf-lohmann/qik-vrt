from __future__ import annotations

import base64
import importlib.util
import json
import socket
import socketserver
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
_spec = importlib.util.spec_from_file_location("qikvrt_effect_ack_http_terminal", MODULE_PATH)
assert _spec and _spec.loader
terminal = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = terminal
_spec.loader.exec_module(terminal)


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def commit_field(token: str, digest: str) -> str:
    return f"v=1, mode=commit, token={sf_bytes(token.encode('ascii'))}, hash={sf_bytes(bytes.fromhex(digest))}"


class EffectAckHttpTerminalContractTests(unittest.TestCase):
    def test_repository_contract_files_parse(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "docs/terminal/QIKVRT_TERMINAL_FRAME_V1.schema.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml")
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("alarms", manifest["permissions"])
        self.assertIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
        self.assertEqual(policy["http"]["request_field"], "Effect-Ack-Request")
        self.assertEqual(policy["http"]["response_field"], "Effect-Ack")
        self.assertEqual(policy["http"]["link_relation"], "effect-ack")
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_terminal_frame_v1")

    def test_firefox_source_preserves_terminal_boundaries(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        content = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")
        manifest = (ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8")
        self.assertIn("browser.alarms", background)
        self.assertIn("WATCHDOG_PERIOD_MINUTES = 5", background)
        self.assertIn("validated DONE prepare result required", background)
        self.assertIn("record_validated", background)
        self.assertIn("compact/full record hash mismatch", background)
        self.assertIn("Effect-Ack-Request", background)
        self.assertNotIn("X-QIKVRT-Commit-Token", background)
        self.assertNotIn("X-QIKVRT-Record-Hash", background)
        self.assertIn("getUserMedia({audio: true", content)
        self.assertIn("getUserMedia({audio: false, video:", content)
        self.assertIn("preparedRequest", content)
        self.assertIn("Prepare ≠ effect", content)
        self.assertNotIn('"service_worker"', manifest)
        self.assertNotIn("8766", background + manifest)

    def test_http_draft_defines_backward_compatible_two_phase_profile(self) -> None:
        text = (ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml").read_text(encoding="utf-8")
        for value in (
            "Effect-Ack-Request",
            "Effect-Ack",
            "effect-ack",
            "mode=prepare",
            "mode=commit",
            "single-use",
            "Backward Compatibility",
            "HTML Integration",
        ):
            self.assertIn(value, text)
        self.assertIn("MUST NOT execute the protected effect", text)

    def test_structured_request_parser_is_closed_and_exact(self) -> None:
        parsed = terminal.parse_effect_ack_request("v=1, mode=prepare")
        self.assertEqual(parsed, {"v": 1, "mode": "prepare"})
        token = "abc_DEF-123"
        digest = "00" * 32
        parsed = terminal.parse_effect_ack_request(commit_field(token, digest))
        self.assertEqual(parsed["token"], token)
        self.assertEqual(parsed["hash"], digest)
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=prepare, token=:YQ==:")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=commit")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=2, mode=prepare")


class LoopbackTerminalE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        terminal.STATE = terminal.State()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
        data = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request_headers = dict(headers or {})
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.base + path, method=method, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(req, timeout=3)
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, response.headers, payload
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            return exc.code, exc.headers, payload

    def prepare(self, payload: dict):
        status, headers, body = self.request(
            "/terminal/prepare",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=prepare"},
        )
        self.assertEqual(status, 200)
        self.assertIn("state=done", headers["Effect-Ack"])
        self.assertIn("token=:", headers["Effect-Ack"])
        self.assertFalse(body["ordinary_release"])
        self.assertEqual(body["external_effect"], "NONE")
        return body

    def commit_headers(self, prepared: dict) -> dict[str, str]:
        return {"Effect-Ack-Request": commit_field(prepared["commit_token"], prepared["record_hash"])}

    def test_discovery_prepare_commit_reobserve_and_replay_block(self) -> None:
        status, headers, capability = self.request("/.well-known/effect-ack")
        self.assertEqual(status, 200)
        self.assertIn('rel="effect-ack"', headers["Link"])
        self.assertEqual(capability["external_effects"], "NONE")

        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "https://github.com/Goldkelch/qik-vrt/blob/main/AI",
            "text": "eins und nicht keins",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)

        status, record_headers, record = self.request(prepared["record_url"])
        self.assertEqual(status, 200)
        self.assertEqual(record["state"], "EFFECT_ACK_DONE")
        self.assertEqual(record["external_effect"], "NONE")
        self.assertIn("state=done", record_headers["Effect-Ack"])
        self.assertNotIn("token=:", record_headers["Effect-Ack"])

        wrong = dict(payload)
        wrong["text"] = "different"
        status, _, rejected = self.request(
            "/terminal/commit", method="POST", body=wrong, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("differs", rejected["reason"])

        status, _, committed = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 200)
        self.assertTrue(committed["ordinary_release"])
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertEqual(committed["post_effect"]["text"], "eins und nicht keins")

        status, _, replay = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("used", replay["reason"])

        status, _, observed = self.request("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(observed["events"], 1)
        self.assertEqual(observed["last_event"]["kind"], "TERMINAL_INPUT_ACCEPTED")

    def test_expired_token_fails_closed(self) -> None:
        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "AI",
            "text": "x",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)
        terminal.STATE.prepared[prepared["commit_token"]].expires_at = time.time() - 1
        status, _, body = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertFalse(body["ordinary_release"])

    def test_missing_or_malformed_effect_ack_request_fails_closed(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "x"}
        status, _, body = self.request("/terminal/prepare", method="POST", body=payload)
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])
        status, _, body = self.request(
            "/terminal/commit",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=commit"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])

    def test_durable_writer_is_not_exposed_over_http(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "owner-only"}
        for path in ("/terminal/durable-prepare", "/terminal/durable-commit", "/api/temdd/events"):
            status, _, _ = self.request(path, method="POST", body=payload,
                                        headers={"Effect-Ack-Request": "v=1, mode=prepare"})
            self.assertEqual(status, 404)
        self.assertEqual(terminal.STATE.events, [])


@unittest.skipUnless(hasattr(socket, "SO_PEERCRED"), "owner Unix peer credentials require Linux")
class DurableOwnerTerminalTests(unittest.TestCase):
    """Real Unix/SQLite contract fixture; not an execution of the deployed daemon.

    The carrier ledger is absent from this Mirror tree. This independent fixture
    follows the observed native-event/SQLite contract, including deduplication,
    commit-before-reply, denial of foreign subjects, and corrupt/ambiguous replies.
    """

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = str(Path(self.temp.name) / "state")
        self.directory = Path(self.state_dir) / "temdd"
        self.directory.mkdir(parents=True, mode=0o700)
        self.subject = {"repository": "ingolf-lohmann/qik-vrt", "pr": 454, "head": "a" * 40, "tree": "b" * 40}
        self.body = {"schema": "qikvrt_terminal_input_v1", "text": "Geprüfter Modellbeweis; Produktabschluss offen.", "audio": None, "video": None}
        self.reply_mode = "normal"
        self.calls = 0
        self.start_fixture()

    def start_fixture(self) -> None:
        self.db = sqlite3.connect(self.directory / "events.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            self.db.executemany("INSERT OR IGNORE INTO meta VALUES (?,?)", (("schema", "1"), ("epoch", "c" * 32)))
            self.db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, binding TEXT NOT NULL, source TEXT NOT NULL, native_id TEXT NOT NULL, native_digest TEXT NOT NULL, body TEXT NOT NULL, body_digest TEXT NOT NULL, UNIQUE(source,native_id))")
        fixture = self
        class Ingress(socketserver.StreamRequestHandler):
            def handle(self):
                fixture.calls += 1
                raw = self.rfile.readline(65538)
                if not raw:
                    return
                native = json.loads(raw)
                if native["subject"] != fixture.subject:
                    self.wfile.write(b'{"state":"HOLD","reason":"EXACT_SUBJECT_MISMATCH","dod":false}\n')
                    return
                body = dict(native, schema="qikvrt_temdd_event_v1", recorded_at="2026-10-04T07:30:00Z",
                            payload_digest=terminal.sha256(terminal.canonical_json(native["payload"])), evidence_transfer="DENY", dod=False)
                digest = terminal.sha256(terminal.canonical_json(body))
                provenance = native["provenance"]
                if fixture.reply_mode == "ack_without_persistence":
                    event = dict(body, id="c" * 32 + ":1", ledger_digest=digest)
                else:
                    with fixture.db:
                        old = fixture.db.execute("SELECT seq,native_digest FROM events WHERE source=? AND native_id=?", (provenance["source"], provenance["native_event_id"])).fetchone()
                        if old:
                            if old[1] != terminal.sha256(terminal.canonical_json(native)):
                                self.wfile.write(b'{"state":"HOLD","reason":"NATIVE_EVENT_ID_CONFLICT","dod":false}\n')
                                return
                            seq = old[0]
                        else:
                            seq = fixture.db.execute("INSERT INTO events(binding,source,native_id,native_digest,body,body_digest) VALUES (?,?,?,?,?,?)",
                                (terminal.sha256(terminal.canonical_json(native["subject"])), provenance["source"], provenance["native_event_id"],
                                 terminal.sha256(terminal.canonical_json(native)), terminal.canonical_json(body).decode(), digest)).lastrowid
                    event = dict(body, id="c" * 32 + ":" + str(seq), ledger_digest=digest)
                if fixture.reply_mode == "drop_after_persistence":
                    return
                if fixture.reply_mode == "wrong_reply":
                    event["ledger_digest"] = "0" * 64
                self.wfile.write(terminal.canonical_json({"state": "PERSISTED", "event": event, "authority_effect": False, "dod": False}) + b"\n")
        path = self.directory / "ingress.sock"
        if path.exists():
            path.unlink()
        self.server = socketserver.UnixStreamServer(str(path), Ingress)
        path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_fixture(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.db.close()

    def tearDown(self) -> None:
        self.stop_fixture()
        self.temp.cleanup()

    def prepare(self):
        return terminal.durable_prepare(self.body, self.subject, self.state_dir)

    def commit(self, prepared):
        return terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, self.subject, self.state_dir)

    def readback(self, prepared):
        return terminal.durable_readback(prepared, prepared["prepare_hash"], self.body, self.subject, self.state_dir)

    def count(self):
        return self.db.execute("SELECT count(*) FROM events").fetchone()[0]

    def test_prepare_has_no_ledger_write(self):
        prepared = self.prepare()
        self.assertFalse(prepared["EFFECT_ACK_DONE"])
        self.assertEqual((self.calls, self.count()), (0, 0))

    def test_commit_and_restart_have_fresh_durable_readback(self):
        prepared = self.prepare()
        receipt = self.commit(prepared)
        self.assertTrue(receipt["durable_persisted"])
        self.assertFalse(receipt["EFFECT_ACK_DONE"])
        self.assertFalse(receipt["public_readback_verified"])
        self.assertEqual(receipt["durable_readback"]["subject"], self.subject)
        self.stop_fixture()
        self.start_fixture()
        self.assertEqual(self.readback(prepared), receipt)

    def test_repeat_commit_is_readback_only_and_single_effect(self):
        prepared = self.prepare()
        receipt = self.commit(prepared)
        with self.assertRaisesRegex(terminal.DurableHold, "ALREADY_COMMITTED"):
            self.commit(prepared)
        self.assertEqual(self.readback(prepared), receipt)
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_concurrent_commits_share_one_native_effect(self):
        prepared = self.prepare()
        results = []
        def commit():
            try:
                results.append(self.commit(prepared))
            except terminal.DurableHold as exc:
                results.append(str(exc))
        threads = [threading.Thread(target=commit) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        self.assertTrue(any(isinstance(x, dict) and x["durable_persisted"] for x in results))
        self.assertEqual(self.count(), 1)
        self.assertLessEqual(self.calls, 2)

    def test_wrong_prepare_hash_cannot_write(self):
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "HASH_MISMATCH"):
            terminal.durable_commit(prepared, "sha256:" + "0" * 64, self.body, self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_changed_preparation_cannot_write(self):
        prepared = self.prepare()
        prepared["preparation"]["event"]["message"] += "tampered"
        with self.assertRaisesRegex(terminal.DurableHold, "HASH_MISMATCH"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_changed_payload_cannot_write(self):
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "INPUT_MISMATCH"):
            terminal.durable_commit(prepared, prepared["prepare_hash"], dict(self.body, text="changed"), self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_changed_head_or_tree_cannot_write(self):
        prepared = self.prepare()
        for key in ("head", "tree", "repository", "pr"):
            other = dict(self.subject)
            other[key] = 455 if key == "pr" else "f" * 40
            with self.assertRaisesRegex(terminal.DurableHold, "SUBJECT_OR_ROUTE_MISMATCH"):
                terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, other, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_expired_preparation_cannot_write(self):
        prepared = self.prepare()
        prepared["preparation"]["expires_at"] = int(time.time()) - 1
        prepared["prepare_hash"] = "sha256:" + terminal.sha256(terminal.canonical_json(prepared["preparation"]))
        with self.assertRaisesRegex(terminal.DurableHold, "EXPIRED"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_ledger_epoch_change_blocks_commit(self):
        prepared = self.prepare()
        with self.db:
            self.db.execute("UPDATE meta SET value=? WHERE key='epoch'", ("d" * 32,))
        with self.assertRaisesRegex(terminal.DurableHold, "LEDGER_CHANGED"):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_socket_permissions_never_widened(self):
        prepared = self.prepare()
        path = self.directory / "ingress.sock"
        path.chmod(0o666)
        with self.assertRaises(terminal.DurableHold):
            self.commit(prepared)
        self.assertEqual(path.stat().st_mode & 0o777, 0o666)
        self.assertEqual(self.calls, 0)

    def test_socket_symlink_rejected(self):
        prepared = self.prepare()
        path = self.directory / "ingress.sock"
        real = self.directory / "real.sock"
        path.rename(real)
        path.symlink_to(real)
        with self.assertRaises(terminal.DurableHold):
            self.commit(prepared)
        self.assertEqual(self.calls, 0)

    def test_parent_symlink_and_non_owner_directory_rejected(self):
        alias = Path(self.temp.name) / "alias"
        alias.symlink_to(self.state_dir)
        with self.assertRaises(terminal.DurableHold):
            terminal.durable_prepare(self.body, self.subject, str(alias))
        self.directory.chmod(0o755)
        with self.assertRaises(terminal.DurableHold):
            self.prepare()
        self.assertEqual(self.calls, 0)

    def test_media_and_unbounded_input_not_admitted(self):
        for body in (dict(self.body, audio="data"), dict(self.body, video="data"), dict(self.body, text="x" * 4097), dict(self.body, command="id")):
            with self.assertRaises(terminal.DurableHold):
                terminal.durable_prepare(body, self.subject, self.state_dir)
        self.assertEqual(self.calls, 0)

    def test_foreign_peer_uid_cannot_write(self):
        prepared = self.prepare()
        with mock.patch.object(terminal.struct, "unpack", return_value=(1, terminal.os.geteuid() + 1, 1)):
            with self.assertRaisesRegex(terminal.DurableHold, "PEER_OWNER_MISMATCH"):
                self.commit(prepared)
        self.assertEqual(self.count(), 0)

    def test_ingress_subject_mismatch_not_success(self):
        other = dict(self.subject, head="f" * 40)
        prepared = terminal.durable_prepare(self.body, other, self.state_dir)
        with self.assertRaises(terminal.DurableHold):
            terminal.durable_commit(prepared, prepared["prepare_hash"], self.body, other, self.state_dir)
        self.assertEqual(self.count(), 0)

    def test_ack_without_sqlite_effect_cannot_succeed(self):
        self.reply_mode = "ack_without_persistence"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "NOT_OBSERVED"):
            self.commit(prepared)
        self.assertEqual((self.calls, self.count()), (1, 0))

    def test_spoofed_ack_cannot_replace_exact_readback(self):
        self.reply_mode = "wrong_reply"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "REPLY_DIFFERS"):
            self.commit(prepared)
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_ambiguous_commit_recovers_by_readback_without_resubmission(self):
        self.reply_mode = "drop_after_persistence"
        prepared = self.prepare()
        with self.assertRaisesRegex(terminal.DurableHold, "DO_NOT_RESUBMIT"):
            self.commit(prepared)
        self.stop_fixture()
        self.start_fixture()
        self.assertTrue(self.readback(prepared)["durable_persisted"])
        self.assertEqual((self.calls, self.count()), (1, 1))

    def test_corrupt_ledger_readback_fails_closed(self):
        prepared = self.prepare()
        self.commit(prepared)
        with self.db:
            self.db.execute("UPDATE events SET body_digest=?", ("0" * 64,))
        with self.assertRaisesRegex(terminal.DurableHold, "READBACK_MISMATCH"):
            self.readback(prepared)

    def test_cli_roundtrip_and_dirty_checkout_rejection(self):
        root = Path(self.temp.name) / "checkout"
        root.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()
        git("init", "-q")
        git("remote", "add", "origin", "https://github.com/ingolf-lohmann/qik-vrt.git")
        (root / "source").write_text("fixture\n")
        git("add", "source")
        git("-c", "user.name=Contract Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        self.subject.update(head=git("rev-parse", "HEAD"), tree=git("rev-parse", "HEAD^{tree}"))
        input_file = Path(self.temp.name) / "input.json"
        input_file.write_bytes(terminal.canonical_json(self.body))
        args = ["--root", str(root), "--repository", self.subject["repository"], "--pr", "454", "--expected-head", self.subject["head"],
                "--expected-tree", self.subject["tree"], "--input", str(input_file), "--state-dir", self.state_dir]
        def cli(operation, *extra):
            p = subprocess.run([sys.executable, "-B", str(MODULE_PATH), operation, *args, *extra], capture_output=True, text=True, timeout=10)
            return p.returncode, json.loads(p.stdout)
        code, prepared = cli("durable-prepare")
        self.assertEqual(code, 0)
        prepared_file = Path(self.temp.name) / "prepared.json"
        prepared_file.write_bytes(terminal.canonical_json(prepared))
        extra = ("--prepared", str(prepared_file), "--prepare-hash", prepared["prepare_hash"])
        code, receipt = cli("durable-commit", *extra)
        self.assertEqual(code, 0)
        self.assertTrue(receipt["durable_persisted"])
        code, readback = cli("durable-readback", *extra)
        self.assertEqual((code, readback), (0, receipt))
        (root / "source").write_text("dirty\n")
        code, hold = cli("durable-prepare")
        self.assertEqual(code, 2)
        self.assertFalse(hold["EFFECT_ACK_DONE"])
        self.assertEqual((self.calls, self.count()), (1, 1))


if __name__ == "__main__":
    unittest.main()
