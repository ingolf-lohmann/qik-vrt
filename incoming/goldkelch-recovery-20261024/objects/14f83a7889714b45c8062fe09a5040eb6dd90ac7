# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic private HTTP scenarios for PR453 on the literal PR429 carrier.

Processes really stop/restart. Delivery is independently read from an isolated
HTTP channel fixture, never from the client-supplied transport acknowledgement.
These tests do not attest the Owner's private runtime or human understanding.
"""
from __future__ import annotations

import copy
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tests import test_tcpip_e2e as tcpip
from src import qikvrt_digital_twin_personal as personal
from src import qikvrt_digital_twin_schedule_events as native
from src.qikvrt_digital_twin_scheduling import canonical, digest

SOURCE = {"repository": "owner/repo", "role": "MIRROR", "head": "1" * 40, "tree": "2" * 40}
PRINCIPAL = "e2e-responsible-operator"
CHANNELS = {"fixture-terminal": {"principal": PRINCIPAL, "languages": ["de"], "modalities": ["text"]}}
GOAL = digest("synthetic-goal")

# Every requirement scenario has a concrete independently executable HTTP test.
SCENARIO_TESTS = {
    "MAIN-PRIMARY-01": "test_main_primary_01_four_strands_and_urgent_priority",
    "REQ-UNDEFINED-01": "test_req_undefined_01_refinement_before_owner_question",
    "REQ-DEFINED-01": "test_req_defined_01_ready_is_not_effect",
    "REQ-REVISION-01": "test_req_revision_01_invalidates_prior_action",
    "TWIN-CAS-01": "test_twin_cas_01_concurrent_duplicate_and_competing_clients",
    "FEEDBACK-RESTART-01": "test_feedback_restart_01_exact_private_decision_and_replay",
    "FEEDBACK-DELIVERY-01": "test_feedback_delivery_01_transport_and_independent_channel_readback",
    "FEEDBACK-NOOP-01": "test_feedback_noop_01_no_new_ledger_or_notification",
    "HUMAN-CORRECTION-01": "test_human_correction_01_supersession_and_cancellation",
    "HUMAN-CONTEXT-01": "test_human_context_01_actual_authorized_alternative",
    "ROLE-COVERAGE-01": "test_role_coverage_01_no_authority_or_head_transfer",
    "EFFECT-CLOSURE-01": "test_effect_closure_01_scoped_human_feedback_not_global_done",
}


def requirement(goal=GOAL):
    value = {key: "Explicit synthetic fixture scope" for key in personal.REQUIREMENT_FIELDS}
    value.update(requirement_id=goal,
                 origin_reference_and_epistemic_type={"reference": "synthetic://fixture/requirement", "epistemic_type": "HUMAN_DIRECTIVE"},
                 repository_role_and_exact_source=SOURCE,
                 current_revision_and_supersedes={"revision": 1, "supersedes": None},
                 purpose_and_beneficiary="Resolve the synthetic private fixture requirement",
                 acceptance_predicates=["The synthetic persisted value is identical after service restart"],
                 owner_choices_and_their_resolution=[], current_quality_procedure_fingerprint="a" * 64)
    return value


def context(channel="fixture-terminal", language="de", modality="text"):
    return {"channel_id": channel, "language": language, "modality": modality}


def priority(main=True, deadline=None, impact=2):
    return {"main_goal": main, "continuing_goal": main, "deadline_utc": deadline, "impact": impact,
            "reason": "Explicit synthetic priority declaration"}


def command(transition="input", version=0, *, key="input", goal=GOAL, data=None):
    if data is None:
        data = {"strand_id": digest("synthetic-strand"), "requirement": requirement(goal),
                "priority": priority(), "context": context(), "input": {"text": "Synthetic private input"}}
    return {"schema": personal.INPUT_SCHEMA, "input_id": digest(key), "requirement_id": goal,
            "expected_version": version, "transition": transition, "data": data}


def observation(blocker="Synthetic missing permission", procedure="a" * 64, ctx=None):
    return {"blocker": blocker, "retry_condition": "A materially changed admission observation",
            "procedure_sha256": procedure, "context": ctx or context()}


def stamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class PersonalHttpTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"QIKVRT_SCHEDULE_ROLE": SOURCE["role"], "QIKVRT_SCHEDULE_HEAD": SOURCE["head"],
                                           "QIKVRT_SCHEDULE_TREE": SOURCE["tree"], "QIKVRT_PERSONAL_CHANNELS_JSON": canonical(CHANNELS)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = tcpip.TcpIpEndToEndTests()
        self.client.setUp()
        self.addCleanup(self.client.tearDown)

    def post(self, raw, code=200):
        actual, result = self.client.request("POST", personal.BASE + "/inputs", raw)
        self.assertEqual(actual, code, result)
        self.assertFalse(result["effect_ack_done"])
        return result

    def goal(self, goal=GOAL):
        code, result = self.client.request("GET", personal.BASE + "/" + goal)
        self.assertEqual(code, 200, result)
        self.assertEqual(len(result["goals"]), 1)
        return result["goals"][0]

    def native_store(self, principal=PRINCIPAL, source=None):
        return native.ScheduleEventStore(self.client.state, source or SOURCE, principal)

    def restart(self, *, principal=PRINCIPAL, source=None, channel_url=None):
        self.client.server.terminate()
        self.client.server.communicate(timeout=5)
        source = source or SOURCE
        environment = os.environ.copy()
        environment.update(QIKVRT_API_HOST="127.0.0.1", QIKVRT_API_PORT=str(self.client.port),
                           QIKVRT_API_TOKEN=self.client.token, QIKVRT_API_TOKEN_EXPIRES_UTC="2099-01-01T00:00:00Z",
                           QIKVRT_ALLOWED_REPOSITORY=source["repository"], QIKVRT_API_PRINCIPAL=principal,
                           QIKVRT_REPO_ROOT=str(self.client.state), QIKVRT_RATE_LIMIT_PER_MINUTE="10000",
                           QIKVRT_SCHEDULE_ROLE=source["role"], QIKVRT_SCHEDULE_HEAD=source["head"], QIKVRT_SCHEDULE_TREE=source["tree"])
        if channel_url:
            environment["QIKVRT_TEST_CHANNEL_URL"] = channel_url
            script = (
                "import json,os,urllib.request; "
                "from urllib.parse import urlencode; "
                "from http.server import ThreadingHTTPServer; "
                "from src.qikvrt_github_api_shim import QikvrtGitHubApiShim; "
                "server=ThreadingHTTPServer(('127.0.0.1',int(os.environ['QIKVRT_API_PORT'])),QikvrtGitHubApiShim); "
                "server.qikvrt_personal_channel_readback=lambda binding: json.loads(urllib.request.urlopen("
                "os.environ['QIKVRT_TEST_CHANNEL_URL']+'?'+urlencode(binding),timeout=3).read()); "
                "server.serve_forever()"
            )
            args = [sys.executable, "-S", "-c", script]
        else:
            args = [sys.executable, "-S", "src/qikvrt_github_api_shim.py"]
        self.client.server = subprocess.Popen(args, cwd=tcpip.REPOSITORY_ROOT, env=environment,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.client._wait_until_ready()

    def test_main_primary_01_four_strands_and_urgent_priority(self):
        now = stamp()
        for index in range(4):
            goal = digest("strand-goal-" + str(index))
            data = command(goal=goal)["data"]
            data.update(strand_id=digest("strand-" + str(index)), priority=priority(index == 3, now if index == 1 else None))
            self.post(command(goal=goal, key="create-" + str(index), data=data))
        code, result = self.client.request("POST", personal.BASE + "/prioritize", {"at_utc": now})
        self.assertEqual(code, 200, result)
        self.assertEqual(result["entries"][0]["requirement_id"], digest("strand-goal-1"))
        self.assertTrue(result["entries"][0]["urgent"])
        self.assertEqual(result["entries"][1]["requirement_id"], digest("strand-goal-3"))
        self.assertEqual(len({e["strand_id"] for e in result["entries"]}), 4)
        self.assertFalse(result["dispatch_performed"])
        self.restart()
        self.assertEqual(len(self.client.request("GET", personal.BASE)[1]["goals"]), 4)

    def test_req_undefined_01_refinement_before_owner_question(self):
        raw = command()
        raw["data"]["requirement"]["acceptance_predicates"] = None
        self.post(raw)
        ready = self.goal()["readiness"]
        self.assertEqual(ready["state"], "OPEN")
        self.assertIn("acceptance_predicates", ready["missing_fields"])
        self.assertEqual(ready["necessary_owner_choices"], [])
        self.assertIsNone(self.goal()["event"]["value"]["payload"]["feedback"])
        self.assertTrue(ready["routine_refinement_first"])

    def test_req_defined_01_ready_is_not_effect(self):
        result = self.post(command())
        self.assertTrue(result["local_post_effect_readback_verified"])
        self.assertEqual(self.goal()["readiness"]["state"], "READY_FOR_IMPLEMENTATION")
        self.assertFalse(self.goal()["readiness"]["readiness_is_authorization"])
        self.assertFalse(self.goal()["global_goal_done"])
        self.assertFalse(self.goal()["prepared_action_current"])

    def test_req_revision_01_invalidates_prior_action(self):
        self.post(command())
        self.post(command("prepare_action", 1, key="prepare", data={"action_id": digest("action")}))
        self.assertTrue(self.goal()["prepared_action_current"])
        self.post(command("observe", 2, key="criteria", data=observation(None, "b" * 64)))
        self.assertEqual(self.goal()["readiness"]["state"], "OPEN_REVALIDATION_REQUIRED")
        self.assertFalse(self.goal()["prepared_action_current"])
        self.assertEqual(self.goal()["event"]["value"]["payload"]["prepared_action"]["state"], "INVALIDATED")
        history = self.native_store().export()
        self.assertEqual(len(native.validate_snapshot(history)["operations"]), 3)

    def test_twin_cas_01_concurrent_duplicate_and_competing_clients(self):
        raw = command()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.client.request("POST", personal.BASE + "/inputs", raw), range(2)))
        self.assertEqual([code for code, _ in results], [200, 200], results)
        self.assertEqual(len(native.validate_snapshot(self.native_store().export())["operations"]), 1)
        self.assertEqual(self.goal()["event"]["version"], 1)
        changed = copy.deepcopy(raw)
        changed["data"]["input"] = "Different content under the same input identity"
        self.post(changed, 409)
        with ThreadPoolExecutor(max_workers=2) as pool:
            inputs = [command("observe", 1, key="writer-" + str(i), data=observation("blocker-" + str(i))) for i in range(2)]
            results = list(pool.map(lambda body: self.client.request("POST", personal.BASE + "/inputs", body), inputs))
        self.assertEqual(sorted(code for code, _ in results), [200, 409], results)
        self.assertEqual(self.goal()["event"]["version"], 2)
        self.assertEqual(len(native.validate_snapshot(self.native_store().export())["operations"]), 2)

    def test_feedback_restart_01_exact_private_decision_and_replay(self):
        raw = command()
        choice = {"decision_id": digest("decision"), "question": "Choose a synthetic fixture alternative",
                  "necessary": True, "resolution": None}
        raw["data"]["requirement"]["owner_choices_and_their_resolution"] = [choice]
        self.post(raw)
        before = self.native_store().export()
        db = self.native_store().path
        self.assertEqual(stat.S_IMODE(db.stat().st_mode), 0o600)
        self.assertEqual(len(list(db.parent.glob("*.sqlite3"))), 1)
        self.restart()
        self.assertEqual(self.native_store().export(), before)
        self.assertEqual(self.goal()["readiness"]["necessary_owner_choices"], [choice])
        replay = self.post(raw)
        self.assertTrue(replay["replay"])
        self.assertFalse(replay["local_post_effect_readback_verified"])
        self.restart(principal="another-synthetic-principal")
        self.assertEqual(self.client.request("GET", personal.BASE)[1]["goals"], [])
        self.assertEqual(self.client.request("GET", personal.BASE + "/" + GOAL)[0], 404)
        self.restart()
        self.assertEqual(self.native_store().export(), before)

    def queue_feedback(self):
        self.post(command())
        self.post(command("observe", 1, key="blocked", data=observation()))
        return self.goal()["event"]["value"]["payload"]["feedback"]

    def test_feedback_delivery_01_transport_and_independent_channel_readback(self):
        feedback = self.queue_feedback()
        data = {"feedback_id": feedback["feedback_id"], "attempt_id": digest("delivery-attempt"),
                "channel_id": "fixture-terminal", "transport_ack": True}
        self.post(command("feedback_attempt", 2, key="attempt", data=data))
        read = {"feedback_id": data["feedback_id"], "attempt_id": data["attempt_id"]}
        pending = self.post(command("feedback_readback", 3, key="unconfigured", data=read))
        self.assertEqual(pending["state"], "NOOP_UNCHANGED")
        self.assertEqual(self.goal()["delivery_state"], "DELIVERY_PENDING")
        self.post(command("feedback_readback", 3, key="fabricated", data=dict(read, delivered=True)), 400)
        state = {"delivered": False, "received": None, "reads": 0}
        class Channel(BaseHTTPRequestHandler):
            def do_POST(self):
                received = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if digest(received["message"]) != received["message_sha256"]:
                    self.send_error(400)
                    return
                state["received"] = received
                self.send_response(202)
                self.end_headers()
            def do_GET(self):
                state["reads"] += 1
                received = state["received"]
                body = {k: received[k] for k in ("principal", "channel_id", "attempt_id", "message_sha256")}
                body.update(delivered=state["delivered"], observed_at_utc=stamp(), receipt_id="synthetic-channel-readback-1")
                raw = canonical(body).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def log_message(self, *args):
                pass
        channel = ThreadingHTTPServer(("127.0.0.1", 0), Channel)
        thread = threading.Thread(target=channel.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(channel.server_close)
        self.addCleanup(lambda: thread.join(timeout=3))
        self.addCleanup(channel.shutdown)
        url = "http://127.0.0.1:" + str(channel.server_port)
        outgoing = {"principal": PRINCIPAL, "channel_id": data["channel_id"], "attempt_id": data["attempt_id"],
                    "message_sha256": feedback["message_sha256"], "message": feedback["message"]}
        with urllib.request.urlopen(urllib.request.Request(url, data=canonical(outgoing).encode(), method="POST"), timeout=3) as response:
            self.assertEqual(response.status, 202)
        self.restart(channel_url=url)
        self.post(command("feedback_readback", 3, key="channel-pending", data=read))
        self.assertEqual(self.goal()["delivery_state"], "DELIVERY_PENDING")
        state["delivered"] = True
        result = self.post(command("feedback_readback", 3, key="channel-delivered", data=read))
        self.assertTrue(result["local_post_effect_readback_verified"])
        self.assertEqual(self.goal()["delivery_state"], "DELIVERED_CHANNEL_READBACK")
        self.assertFalse(self.goal()["human_understanding_inferred"])
        self.assertEqual(state["reads"], 2)
        replay = self.post(command("feedback_readback", 3, key="channel-delivered", data=read))
        self.assertTrue(replay["historical_only"])
        self.assertEqual(state["reads"], 2)
        self.restart(channel_url=url)
        self.assertEqual(self.goal()["delivery_state"], "DELIVERED_CHANNEL_READBACK")

    def test_feedback_noop_01_no_new_ledger_or_notification(self):
        feedback = self.queue_feedback()
        snapshot = self.native_store().export()
        self.restart()
        for i in range(3):
            result = self.post(command("observe", 2, key="same-blocker-" + str(i), data=observation()))
            self.assertEqual(result["state"], "NOOP_UNCHANGED")
            self.assertFalse(result["notification_created"])
        self.assertEqual(self.native_store().export(), snapshot)
        self.assertEqual(self.goal()["event"]["value"]["payload"]["feedback"], feedback)

    def test_human_correction_01_supersession_and_cancellation(self):
        self.post(command())
        self.post(command("prepare_action", 1, key="prepare", data={"action_id": digest("action")}))
        req = requirement()
        req.update(purpose_and_beneficiary="Corrected synthetic requirement",
                   current_revision_and_supersedes={"revision": 2, "supersedes": digest(requirement())})
        data = {"requirement": req, "priority": priority(), "context": context(), "input": "Explicit synthetic correction"}
        self.post(command("correct", 2, key="correct", data=data))
        self.assertFalse(self.goal()["prepared_action_current"])
        self.assertEqual(self.goal()["event"]["value"]["payload"]["requirement"], req)
        self.post(command("prepare_action", 3, key="reprepare", data={"action_id": digest("new-action")}))
        self.post(command("cancel", 4, key="stop", data={"reason": "Explicit synthetic stop"}))
        self.assertEqual(self.goal()["readiness"]["state"], "CANCELLED")
        self.assertFalse(self.goal()["event"]["value"]["enabled"])
        self.assertFalse(self.goal()["prepared_action_current"])
        self.post(command("observe", 5, key="after-stop", data=observation()), 409)
        self.restart()
        self.assertEqual(self.goal()["readiness"]["state"], "CANCELLED")
        history = native.validate_snapshot(self.native_store().export())
        self.assertEqual(len(history["operations"]), 5)
        self.assertEqual(history["operations"][0]["event"]["value"]["payload"]["requirement"], requirement())

    def test_human_context_01_actual_authorized_alternative(self):
        raw = command()
        raw["data"]["context"] = context(channel="unconfigured-mobile")
        self.post(raw)
        self.assertEqual(self.goal()["readiness"]["state"], "HOLD_UNSUPPORTED_HUMAN_CONTEXT")
        self.assertEqual(self.goal()["context_coverage"]["authorized_alternative_channel"], "fixture-terminal")
        self.post(command("observe", 1, key="voice-only", data=observation(ctx=context(modality="voice"))))
        self.assertIsNone(self.goal()["context_coverage"]["authorized_alternative_channel"])
        self.assertFalse(self.goal()["context_coverage"]["supported"])

    def test_role_coverage_01_no_authority_or_head_transfer(self):
        raw = command()
        raw["data"]["requirement"]["repository_role_and_exact_source"] = dict(SOURCE, repository="authority/repo", role="AUTHORITY")
        self.post(raw)
        self.assertEqual(self.goal()["readiness"]["state"], "HOLD_EXACT_SOURCE_OR_ROLE_UNVERIFIED")
        self.restart(source=dict(SOURCE, role="AUTHORITY"))
        self.assertEqual(self.client.request("GET", personal.BASE)[1]["goals"], [])
        self.restart(source=dict(SOURCE, head="3" * 40, tree="4" * 40))
        self.assertEqual(self.goal()["delivery_state"], "INVALIDATED_EXACT_SUBJECT_CHANGED")
        self.assertFalse(self.goal()["prepared_action_current"])
        self.assertEqual(self.post(raw)["state"], "REPLAY_HISTORICAL_ONLY")

    def test_effect_closure_01_scoped_human_feedback_not_global_done(self):
        feedback = self.queue_feedback()
        result = self.post(command("human_feedback", 2, key="human", data={"feedback_id": feedback["feedback_id"],
                        "response": "Accept only the synthetic fixture scope", "scope_acceptance": "ACCEPTED"}))
        goal = result["personal_readback"]
        self.assertEqual(goal["event"]["value"]["payload"]["human_feedback"][0]["scope_acceptance"], "ACCEPTED")
        self.assertTrue(goal["event"]["value"]["payload"]["priority"]["continuing_goal"])
        self.assertFalse(goal["global_goal_done"])
        self.assertFalse(result["external_effect_verified"])
        self.assertEqual(goal["delivery_state"], "RECEIPT_PENDING")

    def test_authentication_closed_schema_and_strict_cas_types(self):
        self.assertEqual(self.client.request("GET", personal.BASE, token=False)[0], 401)
        self.assertEqual(self.client.request("POST", personal.BASE + "/inputs", command(), token=False)[0], 401)
        self.assertEqual(self.client.request("GET", personal.BASE + "?principal=someone-else")[0], 404)
        self.post(dict(command(), principal="someone-else"), 400)
        self.post(dict(command(), expected_version=True), 400)
        self.post(dict(command(), data=dict(command()["data"], extra=True)), 400)
        raw = command()
        raw["data"]["requirement"]["origin_reference_and_epistemic_type"]["epistemic_type"] = "PROPOSAL"
        self.post(raw)
        self.assertEqual(self.goal()["readiness"]["state"], "OPEN")

    def test_generic_native_writer_and_replay_cannot_bypass_personal_semantics(self):
        self.post(command())
        event = self.goal()["event"]
        raw = {"schema": native.OPERATION_SCHEMA, "event_id": GOAL, "operation_id": digest("bypass"),
               "kind": "delete", "expected_version": 1, "value": None}
        code, result = self.client.request("POST", native.BASE + "/operations", raw)
        self.assertEqual(code, 403, result)
        snapshot = self.native_store().export().decode()
        code, result = self.client.request("POST", native.BASE + "/replay", {"snapshot": snapshot})
        self.assertEqual(code, 403, result)
        self.assertEqual(self.goal()["event"], event)

    def test_delivery_binding_contradiction_and_cancelled_attempt_are_rejected(self):
        feedback = self.queue_feedback()
        attempt = {"feedback_id": feedback["feedback_id"], "attempt_id": digest("attempt"), "channel_id": "fixture-terminal", "transport_ack": True}
        self.post(command("feedback_attempt", 2, key="attempt", data=attempt))
        self.post(command("feedback_attempt", 3, key="another-attempt", data=dict(attempt, attempt_id=digest("second"))), 409)
        adapter = personal.PersonalAdapter(self.native_store(), channels=CHANNELS,
                                          channel_readback=lambda binding: dict(binding, principal="wrong-principal", delivered=True,
                                                                                observed_at_utc=stamp(), receipt_id="wrong"))
        before = self.native_store().export()
        read = {"feedback_id": attempt["feedback_id"], "attempt_id": attempt["attempt_id"]}
        with self.assertRaisesRegex(ValueError, "BINDING_MISMATCH"):
            adapter.apply(command("feedback_readback", 3, key="wrong-channel", data=read))
        self.assertEqual(self.native_store().export(), before)
        self.post(command("cancel", 3, key="cancel", data={"reason": "Synthetic stop during delivery"}))
        self.post(command("feedback_readback", 4, key="after-stop", data=read), 409)

    def test_independent_post_commit_competitor_is_observed(self):
        store = self.native_store()
        adapter = personal.PersonalAdapter(store, channels=CHANNELS)
        original = store.read
        competitor = personal.PersonalAdapter(self.native_store(), channels=CHANNELS)
        def raced(goal=None):
            if goal == GOAL:
                store.read = original
                competitor.apply(command("observe", 1, key="competing-successor", data=observation()))
            return original(goal)
        store.read = raced
        with self.assertRaisesRegex(ValueError, "POST_EFFECT_READBACK_CHANGED"):
            adapter.apply(command())
        self.assertEqual(self.goal()["event"]["version"], 2)

    def test_scenario_mapping_matches_literal_pr453_requirements(self):
        proposal = json.loads((tcpip.REPOSITORY_ROOT / "state/interface_adaptation/HOTPATH_AND_CURRENT_CRITERIA_REACTIVATION_PROPOSAL_V1.json").read_text())
        scenarios = proposal["main_development_thread"]["human_context_coverage"]["scenarios"]
        self.assertEqual(set(SCENARIO_TESTS), {case["id"] for case in scenarios})
        for name in SCENARIO_TESTS.values():
            self.assertTrue(callable(getattr(self, name, None)))

    def test_offline_replay_is_principal_bound_and_never_a_new_effect(self):
        self.post(command())
        snapshot = self.native_store().export()
        with tempfile.TemporaryDirectory() as root:
            target = native.ScheduleEventStore(root, SOURCE, "other-principal")
            with self.assertRaisesRegex(ValueError, "PERSONAL_SNAPSHOT_PRINCIPAL"):
                target.restore(snapshot)
            self.assertEqual(target.read()["events"], [])
            own = native.ScheduleEventStore(root, SOURCE, PRINCIPAL)
            restored = own.restore(snapshot)
            self.assertFalse(restored["replay_establishes_external_effect"])
            replay = personal.PersonalAdapter(own, channels=CHANNELS).apply(command())
            self.assertTrue(replay["historical_only"])
            self.assertFalse(replay["local_post_effect_readback_verified"])
            self.assertFalse(replay["effect_ack_done"])

    def test_changed_blocker_correction_and_clear_invalidate_old_feedback(self):
        old = self.queue_feedback()
        self.post(command("observe", 2, key="changed-blocker", data=observation("New synthetic blocker")))
        current = self.goal()["event"]["value"]["payload"]["feedback"]
        self.assertNotEqual(old["feedback_id"], current["feedback_id"])
        self.post(command("feedback_attempt", 3, key="old-attempt", data={"feedback_id": old["feedback_id"],
                        "attempt_id": digest("old-attempt"), "channel_id": "fixture-terminal", "transport_ack": True}), 409)
        self.post(command("observe", 3, key="clear-blocker", data=observation(None)))
        self.assertIsNone(self.goal()["event"]["value"]["payload"]["feedback"])
        self.assertEqual(self.goal()["readiness"]["state"], "READY_FOR_IMPLEMENTATION")

    def test_stale_future_and_wrong_message_delivery_observations_do_not_commit(self):
        feedback = self.queue_feedback()
        attempt = {"feedback_id": feedback["feedback_id"], "attempt_id": digest("freshness-attempt"),
                   "channel_id": "fixture-terminal", "transport_ack": True}
        self.post(command("feedback_attempt", 2, key="freshness-attempt", data=attempt))
        read = {"feedback_id": attempt["feedback_id"], "attempt_id": attempt["attempt_id"]}
        before = self.native_store().export()
        for number, change in enumerate(({"observed_at_utc": "2000-01-01T00:00:00Z"},
                                         {"observed_at_utc": "2099-01-01T00:00:00Z"},
                                         {"message_sha256": "f" * 64})):
            def provider(binding, change=change):
                result = dict(binding, delivered=True, observed_at_utc=stamp(), receipt_id="synthetic-receipt")
                result.update(change)
                return result
            adapter = personal.PersonalAdapter(self.native_store(), channels=CHANNELS, channel_readback=provider)
            with self.assertRaises(ValueError):
                adapter.apply(command("feedback_readback", 3, key="bad-readback-" + str(number), data=read))
            self.assertEqual(self.native_store().export(), before)

    def test_cancellation_during_channel_readback_wins_cas_without_delivery_receipt(self):
        feedback = self.queue_feedback()
        attempt = {"feedback_id": feedback["feedback_id"], "attempt_id": digest("racing-attempt"),
                   "channel_id": "fixture-terminal", "transport_ack": True}
        self.post(command("feedback_attempt", 2, key="racing-attempt", data=attempt))
        competitor = personal.PersonalAdapter(self.native_store(), channels=CHANNELS)
        def provider(binding):
            competitor.apply(command("cancel", 3, key="cancel-during-readback", data={"reason": "Synthetic concurrent stop"}))
            return dict(binding, delivered=True, observed_at_utc=stamp(), receipt_id="late-synthetic-receipt")
        adapter = personal.PersonalAdapter(self.native_store(), channels=CHANNELS, channel_readback=provider)
        with self.assertRaisesRegex(ValueError, "STALE_.*VERSION"):
            adapter.apply(command("feedback_readback", 3, key="raced-delivery", data={"feedback_id": attempt["feedback_id"], "attempt_id": attempt["attempt_id"]}))
        self.assertEqual(self.goal()["readiness"]["state"], "CANCELLED")
        self.assertEqual(self.goal()["delivery_state"], "INVALIDATED_CANCELLED")
        self.assertIsNone(self.goal()["event"]["value"]["payload"]["feedback"]["observation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
