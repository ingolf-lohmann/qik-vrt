# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Independent failure-oriented checks of the interruption measurement contract."""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from tools import qikvrt_browser_assistant_ab as ab


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
