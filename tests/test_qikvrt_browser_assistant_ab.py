# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent failure-oriented checks of the interruption measurement contract."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from unittest import mock
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools import qikvrt_browser_assistant_ab as ab


class PersonalCarrierTests(unittest.TestCase):
    """Actual loopback adapter routing with explicit model transport doubles."""
    def test_frozen_task_roundtrip_restart_and_no_oracle_or_product_promotion(self):
        from src import qikvrt_personal_assistant as personal
        from src import qikvrt_effect_ack_http_terminal as terminal
        from tests.test_qikvrt_personal_assistant import TransportDouble, TOKEN, KEY
        from http.server import ThreadingHTTPServer
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {"QIKVRT_PERSONAL_LOCAL_TOKEN": TOKEN}):
            root = Path(temp)
            run = root / "run"
            manifest = ab.make_plan(run)
            pair = manifest["pairs"][0]
            tid = pair["pair_id"] + "-baseline"
            transport = TransportDouble()
            runtime = personal.PersonalRuntime(root / "state", "explicit-test-model", KEY, TOKEN, transport=transport)
            server = ThreadingHTTPServer(("127.0.0.1", 0), personal.personal_handler(terminal.Handler, runtime))
            worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
            try:
                first = ab.personal_carrier(run, tid, server.server_port, root / "first")
                self.assertEqual(first["state"], "INTEGRATION_READBACK_ONLY")
                self.assertTrue(first["baseline_local_retention_readback"])
                self.assertFalse(first["authenticated_runtime_readback"])
                self.assertEqual(first["product_trials_executed"], 0)
                self.assertIsNone(first["product_metrics"])
                provider_input = json.loads(transport.requests[-1][1]["input"][0]["content"])
                self.assertEqual(set(provider_input), {"task", "sources", "source_hashes"})
                self.assertNotIn("oracle", provider_input)
                self.assertNotIn("checkpoint", provider_input)
                session = runtime.load(first["session_id"])
                self.assertIsNone(session["checkpoint"])
                server.shutdown(); server.server_close(); worker.join()
                runtime.close()
                runtime = personal.PersonalRuntime(root / "state", "explicit-test-model", KEY, TOKEN, transport=transport)
                server = ThreadingHTTPServer(("127.0.0.1", 0), personal.personal_handler(terminal.Handler, runtime))
                worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
                n = len(transport.requests)
                restored = ab.personal_carrier(run, tid, server.server_port, root / "restored", first["session_id"])
                self.assertEqual(restored["session_sha256"], first["session_sha256"])
                self.assertEqual(len(transport.requests), n)
                self.assertEqual(restored["assistant_create_attempts"], 0)
                self.assertFalse(restored["interruption_observed"])
                # A session from another task/arm cannot be relabelled.
                other = ab.personal_carrier(run, pair["pair_id"] + "-qikvrt", server.server_port, root / "wrong-arm", first["session_id"])
                self.assertEqual(other["state"], "BLOCK")
                self.assertEqual(len(transport.requests), n)
                # Reject a different running source before any paid model request.
                original_subject = runtime.subject
                runtime.subject = {**runtime.subject, "sources": {}}
                mismatch = ab.personal_carrier(run, tid, server.server_port, root / "wrong-source")
                self.assertEqual(mismatch["state"], "BLOCK")
                self.assertEqual(mismatch["assistant_create_attempts"], 0)
                self.assertEqual(len(transport.requests), n)
                runtime.subject = original_subject
                # Ambiguous provider result remains pending, and is not retried.
                transport.fail = True
                blocked = ab.personal_carrier(run, tid, server.server_port, root / "failed")
                self.assertEqual(blocked["state"], "BLOCK")
                self.assertEqual(blocked["assistant_create_attempts"], 1)
                self.assertEqual(len(transport.requests), n + 1)
                self.assertFalse(blocked["product_claim_allowed"])
                for path in root.rglob("response-*.json"):
                    self.assertNotIn(TOKEN.encode(), path.read_bytes())
                    self.assertNotIn(KEY.encode(), path.read_bytes())
            finally:
                server.shutdown(); server.server_close(); worker.join(); runtime.close()

    def test_missing_auth_rejects_before_network_or_output(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.dict(os.environ, {"QIKVRT_PERSONAL_LOCAL_TOKEN": ""}), mock.patch.object(ab.http.client, "HTTPConnection") as network:
            root = Path(temp); manifest = ab.make_plan(root / "run")
            with self.assertRaisesRegex(ab.InvalidRun, "AUTHENTICATION_UNAVAILABLE"):
                ab.personal_carrier(root / "run", manifest["pairs"][0]["trials"][0], 8771, root / "out")
            network.assert_not_called()
            self.assertFalse((root / "out").exists())


class ObservedPersonalTurnTests(unittest.TestCase):
    """Actual HTTP and observer journal; model responses remain explicit doubles."""
    def setUp(self):
        from http.server import ThreadingHTTPServer
        from src import qikvrt_personal_assistant as personal
        from src import qikvrt_effect_ack_http_terminal as terminal
        from tests.test_qikvrt_personal_assistant import TransportDouble, TOKEN, KEY
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.manifest = ab.make_plan(self.run, repeats=2)
        self.now = 10**9
        self.journal = ab.Journal(self.run, clock=lambda: self.now)
        self.pair = self.manifest["pairs"][0]
        self.transport = TransportDouble()
        self.runtime = personal.PersonalRuntime(self.root / "state", "explicit-test-model", KEY, TOKEN, transport=self.transport)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), personal.personal_handler(terminal.Handler, self.runtime))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.auth = mock.patch.dict(os.environ, {"QIKVRT_PERSONAL_LOCAL_TOKEN": TOKEN})
        self.auth.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.worker.join()
        self.runtime.close(); self.auth.stop(); self.temp.cleanup()

    def prepare(self, tid):
        first = ab.personal_carrier(self.run, tid, self.server.server_port, self.root / (tid + "-create"))
        self.assertEqual(first["state"], "INTEGRATION_READBACK_ONLY")
        for kind, payload in [("trial_start", {}), ("checkpoint_readback", self.pair["binding"]),
                              ("interruption_observed", {"class": self.pair["interruption"]})]:
            self.journal.append(tid, kind, payload)
        self.now += 60 * 10**9
        self.journal.append(tid, "resume_signal", {})
        return first

    def turn(self, tid, first, name="a", **overrides):
        gesture = dict(gesture_id=tid + name, kind="context_reentry", text="ä😊")
        gesture.update(overrides)
        return ab.personal_carrier(self.run, tid, self.server.server_port,
            self.run / "personal-observations" / (name * 32), first["session_id"],
            journal=self.journal, turn=gesture)

    def observation(self, receipt, name="a"):
        path = self.run / "personal-observations" / (name * 32) / "RECEIPT.json"
        return dict(receipt=str(path.relative_to(self.run)), receipt_sha256=ab.digest(path.read_bytes()),
            text_sha256=receipt["output_observation"]["text_sha256"],
            excerpt=receipt["output_observation"]["text"])

    def test_same_observer_counts_actual_unicode_gestures_and_product_context_both_arms(self):
        for index, tid in enumerate(self.pair["trials"]):
            first = self.prepare(tid)
            before = self.runtime.load(first["session_id"])
            n = len(self.transport.requests)
            receipt = self.turn(tid, first, name="a" if index == 0 else "b")
            self.assertEqual(receipt["state"], "OBSERVED_TURN_READBACK_ONLY")
            self.assertEqual(receipt["observer_epoch"], self.journal.epoch)
            self.assertEqual(receipt["assistant_create_attempts"], 0)
            self.assertEqual(receipt["assistant_turn_attempts"], 1)
            self.assertEqual(len(self.transport.requests), n + 1)
            self.assertEqual(self.runtime.load(first["session_id"])["history"][:-1], before["history"])
            self.assertEqual([x["method"] for x in receipt["operations"]], ["GET", "GET", "POST", "GET", "GET"])
            self.assertEqual(receipt["operations"][2]["path"], "/personal/resume")
            self.assertFalse(receipt["authenticated_runtime_readback"])
            self.assertEqual(receipt["product_trials_executed"], 0)
            self.assertIsNone(receipt["product_metrics"])
            self.assertNotIn("oracle", self.transport.requests[-1][1]["input"][0]["content"])
            self.journal.append(tid, "trial_end", {"reason": "abort"})
            task = self.journal.tasks[self.pair["task_id"]]
            row = ab.evaluate(ab.read_events(self.run, tid), task, self.journal.contract, self.pair)
            self.assertEqual(row["context_reentered_characters"], 2)
            self.assertEqual(row["context_reentered_utf8_bytes"], 6)
            self.assertEqual(row["human_interventions"], 1)
            self.assertEqual(row["false_completed_step_claims"], 0)
            self.assertIsNone(row["reliable_resume_ms"])
            self.assertEqual(row["automatic_context_utf8_bytes"] > 0, tid.endswith("-qikvrt"))
        self.assertFalse(ab.analyze(self.run)["product_claim_allowed"])

    def test_wrong_arm_or_expired_horizon_refuses_before_any_paid_turn(self):
        tid = self.pair["trials"][0]
        first = self.prepare(tid)
        self.runtime.db.execute("UPDATE sessions SET body=? WHERE id=?",
            (ab.canonical(dict(self.runtime.load(first["session_id"]), mode="qikvrt" if tid.endswith("baseline") else "baseline")).decode(), first["session_id"]))
        self.runtime.db.commit()
        n = len(self.transport.requests)
        receipt = self.turn(tid, first)
        self.assertEqual(receipt["state"], "BLOCK")
        self.assertEqual(receipt["assistant_turn_attempts"], 0)
        self.assertEqual(len(self.transport.requests), n)
        self.now += 181 * 10**9
        expired = self.turn(tid, first, name="b")
        self.assertEqual(expired["state"], "BLOCK")
        self.assertIn("horizon exceeded", expired["reason"])
        self.assertEqual(expired["operations"], [])
        self.assertEqual(len(self.transport.requests), n)

    def test_ambiguous_paid_result_preserves_gesture_and_pending_intent_without_retry(self):
        tid = self.pair["trials"][0]
        first = self.prepare(tid)
        self.transport.fail = True
        n = len(self.transport.requests)
        receipt = self.turn(tid, first)
        self.assertEqual(receipt["state"], "BLOCK")
        self.assertEqual(receipt["assistant_turn_attempts"], 1)
        self.assertEqual(len(self.transport.requests), n + 1)
        self.assertEqual(self.runtime.load(first["session_id"])["status"], "TURN_PENDING")
        self.assertEqual(ab.read_events(self.run, tid)[-1]["type"], "human_input")
        duplicate = self.turn(tid, first, name="b", gesture_id=tid + "a")
        self.assertEqual(duplicate["state"], "BLOCK")
        self.assertEqual(duplicate["operations"], [])
        self.assertEqual(len(self.transport.requests), n + 1)

    def test_secret_input_and_another_observer_are_rejected_without_persistence_or_network(self):
        from tests.test_qikvrt_personal_assistant import TOKEN
        tid = self.pair["trials"][0]
        first = self.prepare(tid)
        n = len(self.transport.requests)
        with self.assertRaisesRegex(ab.InvalidRun, "CONTAINS_RUNTIME_SECRET"):
            self.turn(tid, first, text=TOKEN)
        self.assertEqual(len(self.transport.requests), n)
        self.assertFalse((self.run / "personal-observations" / ("a" * 32)).exists())
        other = ab.Journal(self.run, clock=lambda: self.now)
        receipt = ab.personal_carrier(self.run, tid, self.server.server_port,
            self.run / "personal-observations" / ("b" * 32), first["session_id"],
            journal=other, turn={"gesture_id":"other-epoch","kind":"instruction","text":"continue"})
        self.assertEqual(receipt["state"], "BLOCK")
        self.assertEqual(receipt["operations"], [])
        self.assertEqual(len(self.transport.requests), n)

    def test_literal_output_annotations_bind_raw_get_and_detect_later_tampering(self):
        tid = self.pair["trials"][0]
        first = self.prepare(tid)
        original = self.transport.post
        def output(path, payload):
            value, receipt = original(path, payload)
            if path == "/responses":
                value["output"][0]["content"][0]["text"] = "Aufgabe erledigt."
            return value, receipt
        self.transport.post = output
        receipt = self.turn(tid, first)
        evidence = self.observation(receipt)
        with self.assertRaises(ab.InvalidRun):
            self.journal.append(tid, "task_claim", {}, dict(evidence, excerpt="nicht in der Antwort"))
        event = self.journal.append(tid, "task_claim", {}, evidence)
        self.assertEqual(event["observation"], evidence)
        self.journal.append(tid, "trial_end", {"reason": "abort"})
        row = next(r for r in ab.analyze(self.run)["trials"] if r["trial_id"] == tid)
        self.assertEqual(row["false_completed_step_claims"], 1)
        raw = self.run / evidence["receipt"]
        response = raw.parent / receipt["output_observation"]["response_file"]
        response.write_text("{}")
        row = next(r for r in ab.analyze(self.run)["trials"] if r["trial_id"] == tid)
        self.assertEqual(row["state"], "INVALID_OR_INCOMPLETE")
        response.unlink()
        self.assertEqual(next(r for r in ab.analyze(self.run)["trials"] if r["trial_id"] == tid)["state"], "INVALID_OR_INCOMPLETE")

    def test_existing_observer_http_endpoint_refuses_unconfirmed_or_unstarted_turn(self):
        with mock.patch.object(ab, "Journal", return_value=self.journal):
            observer = ab.build_server(self.run)
        worker = threading.Thread(target=observer.serve_forever, daemon=True); worker.start()
        body = dict(trial_id=self.pair["trials"][0], port=self.server.server_port,
            session_id="existing", gesture_id="human-1", kind="instruction", text="continue", confirmed=False)
        base = f"http://127.0.0.1:{observer.server_port}"
        n = len(self.transport.requests)
        try:
            for confirmed, code in [(False, 400), (True, 409)]:
                body["confirmed"] = confirmed
                with self.assertRaises(HTTPError) as exc:
                    urlopen(Request(base + "/api/personal-resume", data=ab.canonical(body),
                        headers={"Content-Type": "application/json"}), timeout=5)
                self.assertEqual(exc.exception.code, code)
            self.assertEqual(len(self.transport.requests), n)
            first = self.prepare(self.pair["trials"][0])
            n = len(self.transport.requests)
            body["session_id"] = first["session_id"]
            with urlopen(Request(base + "/api/personal-resume", data=ab.canonical(body),
                headers={"Content-Type": "application/json"}), timeout=5) as response:
                value = json.load(response)
            self.assertEqual(value["state"], "OBSERVED_TURN_READBACK_ONLY")
            self.assertEqual(len(self.transport.requests), n + 1)
            self.assertFalse(value["product_claim_allowed"])
            self.assertIn("personal-observations/", value["receipt"])
        finally:
            observer.shutdown(); observer.server_close(); worker.join()


class NativeCarrierBoundaryTests(unittest.TestCase):
    def test_other_checkout_cannot_supply_native_source_or_launch_a_process(self):
        with tempfile.TemporaryDirectory() as temp, mock.patch.object(ab, "preflight") as product_observation:
            output = Path(temp) / "untouched"
            with self.assertRaisesRegex(ab.InvalidRun, "EXACT_TEMDD_SOURCE"):
                ab.temdd_carrier(ab.ROOT, output, "a" * 40, 462)
            self.assertFalse(output.exists())
            product_observation.assert_not_called()

    def test_native_source_dirty_or_substituted_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(ab.subprocess, "check_output", side_effect=[ab.TEMDD_SOURCE_HEAD, ab.TEMDD_SOURCE_TREE, " M src/native.py"]):
                with self.assertRaisesRegex(ab.InvalidRun, "EXACT_TEMDD_SOURCE"):
                    ab.temdd_source_binding(root)
            for path in ab.TEMDD_SOURCE_FILES:
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text("substituted implementation\n", encoding="utf-8")
            with mock.patch.object(ab.subprocess, "check_output", side_effect=[ab.TEMDD_SOURCE_HEAD, ab.TEMDD_SOURCE_TREE, ""]):
                with self.assertRaisesRegex(ab.InvalidRun, "EXACT_TEMDD_SOURCE_BYTES_CHANGED"):
                    ab.temdd_source_binding(root)

    def test_denied_unix_host_saves_a_failed_receipt_and_never_launches_native_cli(self):
        head = "a" * 40
        observed = {"head": head, "tree": "b" * 40, "repository": "ingolf-lohmann/qik-vrt",
                    "worktree_dirty": False, "observed_utc": "2026-10-06T00:00:00Z",
                    "environment": {}, "blockers": ["AUTHENTICATED_PERSONAL_RUNTIME_NOT_ESTABLISHED"]}
        checked = ab.subprocess.CompletedProcess([], 0, b"PASS\n", b"")
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(ab, "temdd_source_binding", return_value={"head": ab.TEMDD_SOURCE_HEAD}), \
                mock.patch.object(ab, "preflight", return_value=observed), \
                mock.patch.object(ab.subprocess, "run", return_value=checked), \
                mock.patch.object(ab.subprocess, "Popen") as launch, \
                mock.patch.object(ab.platform, "system", return_value="Linux"), \
                mock.patch.object(ab.socket, "socket", side_effect=PermissionError(1, "Operation not permitted")):
            output = Path(temp) / "blocked"
            receipt = ab.temdd_carrier(Path(temp), output, head, 462)
            self.assertEqual(receipt, ab.read_json(output / "RECEIPT.json"))
            self.assertEqual(receipt["reason"], "HOST_NATIVE_UNIX_INGRESS_UNAVAILABLE")
            self.assertEqual(receipt["host_transport_error"]["errno"], 1)
            self.assertFalse(receipt["native_transport_execution_complete"])
            self.assertEqual(receipt["controls"], {})
            self.assertEqual(receipt["native_transport_status"], "BLOCK")
            self.assertEqual(receipt["state"], "HOLD")
            self.assertEqual(receipt["product_trials_executed"], 0)
            self.assertIsNone(receipt["product_metrics"])
            self.assertFalse(receipt["product_claim_allowed"])
            self.assertFalse(receipt["effect_ack_done"])
            launch.assert_not_called()
            with self.assertRaises(FileExistsError):
                ab.temdd_carrier(Path(temp), output, head, 462)


class BrowserABTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = Path(self.tmp.name) / "run"
        self.manifest = ab.make_plan(self.run, repeats=2)
        self.now = 10**9
        self.journal = ab.Journal(self.run, clock=lambda: self.now)
        self.pair = self.manifest["pairs"][0]
        self.tid = self.pair["trials"][0]
        self.task = self.journal.tasks[self.pair["task_id"]]

    def tearDown(self):
        self.tmp.cleanup()

    def event(self, kind, payload=None, seconds=0):
        self.now += int(seconds * 10**9)
        return self.journal.append(self.tid, kind, payload or {})

    def resume(self):
        self.event("trial_start")
        self.event("checkpoint_readback", self.pair["binding"])
        self.event("interruption_observed", {"class": self.pair["interruption"]})
        self.event("resume_signal", seconds=60)

    def result(self, step):
        oracle = self.task["oracle"][step]
        sources = [oracle["source_id"], *oracle.get("additional_sources", [])]
        return {"step_id": step, "facts": oracle["facts"], "citations": {s: ab.source_map(self.task)[s] for s in sources}}

    def metrics(self):
        return ab.evaluate(ab.read_events(self.run, self.tid), self.task, self.journal.contract, self.pair)

    def test_plan_paired_tasks_balanced_order_and_all_missing_trials_retained(self):
        result = ab.analyze(self.run)
        self.assertEqual(len(result["trials"]), 8)
        self.assertTrue(all(t["state"] == "NOT_EXECUTED" for t in result["trials"]))
        self.assertIsNone(result["product_metrics"])
        self.assertFalse(result["product_claim_allowed"])
        for task_id in self.journal.tasks:
            pairs = [p for p in self.manifest["pairs"] if p["task_id"] == task_id]
            self.assertEqual({p["order"] for p in pairs}, {"AB", "BA"})
            for pair in pairs:
                self.assertEqual(pair["binding"], ab.fixture_binding(self.journal.tasks[task_id]))

    def test_probe_or_previously_done_step_alone_is_not_reliable_resume(self):
        self.resume()
        self.event("resume_probe", ab.correct_probe(self.task), seconds=1)
        self.event("step_output", self.result(self.task["checkpoint"]["completed_steps"][0]), seconds=1)
        self.event("trial_end", {"reason": "timeout"}, seconds=178)
        result = self.metrics()
        self.assertIsNone(result["reliable_resume_ms"])
        self.assertTrue(result["resume_right_censored"])
        self.assertFalse(result["task_success"])

    def test_real_resume_requires_correct_probe_then_source_validated_pending_step(self):
        self.resume()
        next_step = self.task["checkpoint"]["next_step"]
        self.event("step_output", self.result(next_step), seconds=1)
        self.event("resume_probe", ab.correct_probe(self.task), seconds=1)
        wrong = self.result(next_step)
        wrong["citations"] = {s: "f" * 64 for s in wrong["citations"]}
        self.event("step_output", wrong, seconds=1)
        self.event("step_output", self.result(next_step), seconds=1)
        self.event("trial_end", {"reason": "abort"})
        self.assertEqual(self.metrics()["reliable_resume_ms"], 4000)

    def test_false_done_counted_at_claim_time_and_never_retroactively_erased(self):
        self.resume()
        step = self.task["checkpoint"]["next_step"]
        self.event("step_claim", {"step_id": step})
        self.event("step_claim", {"step_id": step})
        self.event("task_claim")
        self.event("resume_probe", ab.correct_probe(self.task))
        for step in self.task["checkpoint"]["pending_steps"]:
            self.event("step_output", self.result(step), seconds=1)
        self.event("task_claim")
        self.event("trial_end", {"reason": "completed"})
        self.assertEqual(self.metrics()["false_completed_step_claims"], 3)
        self.assertEqual(self.metrics()["distinct_false_completed_steps"], 3)
        self.assertTrue(self.metrics()["task_success"])

    def test_unicode_paste_and_automatic_context_are_distinct_and_gestures_counted(self):
        self.resume()
        self.event("human_input", {"gesture_id": "paste-1", "kind": "context_reentry", "text": "ä😊"})
        self.event("human_input", {"gesture_id": "approve-1", "kind": "approval", "text": ""})
        self.event("automatic_context", {"origin_sha256": "a" * 64, "text": "automatic"})
        with self.assertRaises(ab.InvalidRun):
            self.event("human_input", {"gesture_id": "paste-1", "kind": "correction", "text": "x"})
        self.event("trial_end", {"reason": "abort"})
        result = self.metrics()
        self.assertEqual(result["context_reentered_characters"], 2)
        self.assertEqual(result["context_reentered_utf8_bytes"], 6)
        self.assertEqual(result["context_reentered_messages"], 1)
        self.assertEqual(result["automatic_context_utf8_bytes"], 9)
        self.assertEqual(result["human_interventions"], 2)
        self.assertEqual(result["protocol_actions"], 5)

    def test_interruption_early_timeout_and_post_end_events_fail_closed(self):
        with self.assertRaises(ab.InvalidRun):
            self.event("resume_signal")
        self.resume()
        with self.assertRaises(ab.InvalidRun):
            self.event("trial_end", {"reason": "timeout"}, seconds=1)
        self.event("trial_end", {"reason": "abort"})
        with self.assertRaises(ab.InvalidRun):
            self.event("task_claim")

    def test_late_output_and_out_of_order_trial_cannot_improve_metrics(self):
        with self.assertRaisesRegex(ab.InvalidRun, "Preregistered trial order"):
            self.journal.append(self.pair["trials"][1], "trial_start", {})
        self.resume()
        with self.assertRaisesRegex(ab.InvalidRun, "horizon exceeded"):
            self.event("step_output", self.result(self.task["checkpoint"]["next_step"]), seconds=181)
        self.event("trial_end", {"reason": "timeout"})
        self.assertIsNone(self.metrics()["reliable_resume_ms"])
        self.assertTrue(self.metrics()["resume_right_censored"])

    def test_fixture_cost_oracle_agrees_with_current_price_arithmetic(self):
        fixture = self.journal.tasks["research-costs"]
        costs = fixture["oracle"]["costs"]["facts"]
        self.assertEqual(costs["atlas_total_eur"], 12 * 24 * 10 + 120)
        self.assertEqual(costs["beacon_total_eur"], 12 * 24 * 12)
        self.assertEqual(costs["atlas_saving_eur"], costs["beacon_total_eur"] - costs["atlas_total_eur"])

    def test_export_csv_preserves_git_portable_line_bytes(self):
        output = Path(self.tmp.name) / "analysis"
        result = ab.export_analysis(self.run, output)
        raw = (output / "trials.csv").read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertEqual(result, ab.read_json(output / "analysis.json"))

    def test_changed_fixture_and_wrong_checkpoint_are_rejected(self):
        self.event("trial_start")
        wrong = dict(self.pair["binding"], checkpoint_sha256="a" * 64)
        with self.assertRaises(ab.InvalidRun):
            self.event("checkpoint_readback", wrong)
        path = self.run / "fixtures" / f"{self.pair['task_id']}.json"
        path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ab.InvalidRun, "Fixture digest"):
            ab.analyze(self.run)

    def test_log_tampering_and_observer_restart_are_not_accepted(self):
        self.resume()
        with self.assertRaisesRegex(ab.InvalidRun, "Observer epoch"):
            ab.Journal(self.run).append(self.tid, "task_claim", {})
        path = self.run / "events" / f"{self.tid}.jsonl"
        lines = path.read_text().splitlines()
        frame = json.loads(lines[0])
        frame["monotonic_ns"] += 1
        lines[0] = json.dumps(frame)
        path.write_text("\n".join(lines) + "\n")
        result = ab.analyze(self.run)
        row = next(t for t in result["trials"] if t["trial_id"] == self.tid)
        self.assertEqual(row["state"], "INVALID_OR_INCOMPLETE")
        self.assertFalse(result["product_claim_allowed"])

    def test_boolean_is_not_numeric_and_stale_source_is_not_evidence(self):
        task = self.journal.tasks["document-recovery"]
        result = {"step_id": "acceptance", "facts": {"overall_done": 0, "old_done_claim_supported": 0}, "citations": {"live-status": ab.source_map(task)["live-status"]}}
        self.assertFalse(ab.valid_step(task, result))
        result["facts"] = task["oracle"]["acceptance"]["facts"]
        result["citations"] = {"old-note": ab.source_map(task)["old-note"]}
        self.assertFalse(ab.valid_step(task, result))

    def test_no_product_promotion_or_run_overwrite(self):
        with self.assertRaises(ab.InvalidRun):
            ab.make_plan(Path(self.tmp.name) / "other", evidence_class="PRODUCT_E2E")
        with self.assertRaises(ab.InvalidRun):
            ab.make_plan(self.run)
        self.manifest["product_claim_allowed"] = True
        (self.run / "manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(ab.InvalidRun):
            ab.analyze(self.run)

    def test_http_fixture_is_usable_but_oracle_and_foreign_origin_are_closed(self):
        server = ab.build_server(self.run)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/", timeout=3) as response:
                self.assertIn("Harness, keine Produktmessung".encode(), response.read())
            with urlopen(base + f"/api/task/{self.tid}", timeout=3) as response:
                task = json.load(response)
                self.assertNotIn("oracle", task)
                self.assertTrue(task["synthetic"])
            request = Request(base + "/api/event", data=ab.canonical({"trial_id": self.tid, "type": "trial_start", "payload": {}}), headers={"Content-Type": "application/json", "Origin": "https://example.invalid"})
            with self.assertRaises(HTTPError) as exc:
                urlopen(request, timeout=3)
            self.assertEqual(exc.exception.code, 400)
            request = Request(base + "/api/event", data=ab.canonical({"trial_id": self.tid, "type": "trial_start", "payload": {}}), headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=3) as response:
                self.assertTrue(json.load(response)["recorded"])
            self.assertEqual(ab.read_events(self.run, self.tid)[0]["type"], "trial_start")
            with self.assertRaises(HTTPError):
                urlopen(base + "/fixtures/document-recovery.json", timeout=3)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def test_synthetic_self_check_and_real_terminal_smoke_never_become_product_metrics(self):
        result = ab.self_check(Path(self.tmp.name) / "self-check")
        self.assertEqual(result["evidence_class"], "HARNESS_SELF_TEST")
        self.assertEqual(result["product_trials_executed"], 0)
        self.assertIsNone(result["product_metrics"])
        self.assertTrue(all(t["task_success"] for t in result["trials"]))
        smoke = ab.terminal_smoke()
        self.assertEqual(smoke["status"], "PASS")
        self.assertFalse(smoke["firefox_executed"])
        self.assertFalse(smoke["product_claim_allowed"])
        self.assertEqual(smoke["trace"][-1]["status"], 409)


if __name__ == "__main__":
    unittest.main()
