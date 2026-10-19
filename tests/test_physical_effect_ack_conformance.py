#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""SS-03 simulations through the unchanged core and native evidence readback.

Not a physical device adapter, hardware test or safety certification.
"""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from qikvrt_effect_ack import (
    ConnectionDecision, EffectAckRequest, EffectAckResult, EffectState,
    ResponsibilityProtocol, RiskLevel, canonical_json, effect_ack_sync,
    sha256_identifier, verify_protocol, verify_protocol_chain,
)
from tests.test_effect_ack_conformance import request


class _PhysicalEffectSimulation:
    """SS-03 test oracle ONLY; no device driver or production admission path.

    The real core evaluates the resulting request. Authentication, observation
    independence and elapsed milliseconds here are declared simulation inputs,
    not measured hardware facts. Keep this helper in the existing test module.
    """

    def __init__(self) -> None:
        self.command = {
            "effect_id": "simulated-effect-1", "actuator": "simulated-lock-1",
            "from_state": "unsecured", "to_state": "secured",
            "principal": "simulated-site-operator",
            "authorization": sha256_identifier(b"simulated-grant-1"),
            "policy": sha256_identifier(b"simulated-policy-1"),
            "configuration": sha256_identifier(b"simulated-configuration-1"),
            "firmware": sha256_identifier(b"simulated-firmware-1"),
            "issued_ms": 1000, "deadline_ms": 1200,
        }
        self.now_ms = 1030
        self.max_age_ms = 100
        self.clock_trusted = True
        self.authorized = True
        self.revoked = False
        self.grant_expires_ms = 1300
        self.information_received = True
        self.command_reply_received = False
        self.output_transitioned = False
        self.dispatches = 0
        self.high_water = {"simulated-contact": 40, "simulated-bolt": 80}
        self.observation: dict | None = None

    def command_bytes(self) -> bytes:
        return canonical_json(self.command).encode("utf-8")

    def execute(self, *, lost_reply: bool = False, stuck: bool = False,
                unresponsive: bool = False) -> None:
        """One simulated actuation; observation is read separately."""
        if self.dispatches:
            raise AssertionError("ambiguous physical command must not be resubmitted")
        self.dispatches += 1
        if unresponsive:
            return
        self.command_reply_received = not lost_reply
        self.output_transitioned = True
        self.observation = {
            **{key: self.command[key] for key in (
                "effect_id", "actuator", "from_state", "to_state", "principal",
                "authorization", "policy", "configuration", "firmware")},
            "request_hash": sha256_identifier(self.command_bytes()),
            "observed_ms": 1020,
            "sensors": [
                {"source": "simulated-contact", "sequence": 41, "secured": not stuck},
                {"source": "simulated-bolt", "sequence": 81, "secured": not stuck},
            ],
        }

    def request(self) -> EffectAckRequest:
        """Derive claims from the declared trace, never from command ACK alone."""
        payload = self.command_bytes()
        refs = [sha256_identifier(payload)]
        reasons = ["SIMULATED_SS03_TRACE_ONLY_NOT_HARDWARE_ACCEPTANCE"]
        decision = ConnectionDecision.RELEASE
        checks: list[str] = []
        if (self.command["from_state"], self.command["to_state"]) != ("unsecured", "secured"):
            decision = ConnectionDecision.BLOCK
            reasons.append("SS03_TRANSITION_OUTSIDE_SIMULATION_SCOPE")
        if (not self.authorized or self.revoked
                or self.now_ms > self.grant_expires_ms):
            decision = ConnectionDecision.BLOCK
            reasons.append("SS03_AUTHORIZATION_DENIED")
        elif not self.clock_trusted:
            checks.append("SS03_ESTABLISH_OBSERVATION_CLOCK_BOUND")
        elif self.now_ms > self.command["deadline_ms"]:
            decision = ConnectionDecision.BLOCK
            reasons.append("SS03_OBSERVATION_DEADLINE_EXCEEDED")
        if not self.output_transitioned:
            checks.append("SS03_OBSERVE_OUTPUT_TRANSITION")
        obs = self.observation
        if obs is None:
            checks.append("SS03_OBTAIN_INDEPENDENT_PHYSICAL_READBACK")
        else:
            refs.append(sha256_identifier(canonical_json(obs).encode("utf-8")))
            binding_keys = ("effect_id", "actuator", "from_state", "to_state",
                            "principal", "authorization", "policy", "configuration", "firmware")
            if (any(obs[key] != self.command[key] for key in binding_keys)
                    or obs["request_hash"] != sha256_identifier(payload)):
                decision = ConnectionDecision.BLOCK
                reasons.append("SS03_EXACT_BINDING_MISMATCH")
            if not (self.command["issued_ms"] <= obs["observed_ms"] <= self.now_ms
                    and self.now_ms - obs["observed_ms"] <= self.max_age_ms):
                decision = ConnectionDecision.BLOCK
                reasons.append("SS03_OBSERVATION_OUTSIDE_FRESHNESS_WINDOW")
            sensors = obs["sensors"]
            sources = [sensor["source"] for sensor in sensors]
            if len(set(sources)) != len(sources) or any(s not in self.high_water for s in sources):
                decision = ConnectionDecision.ISOLATE
                reasons.append("SS03_OBSERVER_IDENTITY_OR_INDEPENDENCE_UNVERIFIED")
            elif any(sensor["sequence"] <= self.high_water[sensor["source"]] for sensor in sensors):
                decision = ConnectionDecision.BLOCK
                reasons.append("SS03_REPLAYED_OBSERVATION")
            elif set(sources) != set(self.high_water):
                checks.append("SS03_OBTAIN_ALL_REQUIRED_SENSORS")
            elif len({sensor["secured"] for sensor in sensors}) != 1:
                decision = ConnectionDecision.ISOLATE
                reasons.append("SS03_CONTRADICTORY_PHYSICAL_FEEDBACK")
            elif not all(sensor["secured"] is True for sensor in sensors):
                decision = ConnectionDecision.BLOCK
                reasons.append("SS03_PHYSICAL_TARGET_NOT_OBSERVED")
        return EffectAckRequest(
            protocol_root_id="qikvrt:test:ss03:" + self.command["effect_id"],
            input_id=self.command["effect_id"],
            payload=payload if self.information_received else None,
            declared_input_hash=sha256_identifier(payload),
            transport_ack=self.information_received,
            origin_checked=self.authorized and not self.revoked,
            context_checked=not checks,
            semantics_reconstructed=True, effect_anticipated=True,
            risk_classified=True, risk_level=RiskLevel.HIGH,
            responsibility_assigned=True, responsibility_owner=self.command["principal"],
            connection_decision=decision, policy_allows_release=self.authorized and not self.revoked,
            reasons=tuple(reasons), evidence_refs=tuple(refs), required_evidence_refs=tuple(refs),
            next_required_checks=tuple(checks),
        )


class PhysicalEffectSimulationConformanceTests(unittest.TestCase):
    """Deterministic SS-03 controls; NOT a physical-adapter/hardware test.

    No production physical adapter exists in this subject. These tests exercise
    the original five-state core with a test-only evidence oracle. They cannot
    establish sensor authenticity, real independence or installation safety.
    """

    def setUp(self) -> None:
        self.trace = _PhysicalEffectSimulation()

    def evaluate(self, expected: EffectState, reason: str | None = None,
                 previous: ResponsibilityProtocol | None = None) -> EffectAckResult:
        result = effect_ack_sync(self.trace.request(), previous_protocol=previous)
        self.assertIs(result.state, expected)
        self.assertEqual(result.ordinary_release, expected is EffectState.EFFECT_ACK_DONE)
        verify_protocol(result.protocol)
        if reason:
            self.assertIn(reason, result.protocol.reasons + result.protocol.next_required_checks)
        return result

    def test_positive_simulated_physical_readback_binds_command_and_observation(self) -> None:
        self.trace.execute()
        result = self.evaluate(EffectState.EFFECT_ACK_DONE)
        self.assertEqual(result.protocol.input_hash, sha256_identifier(self.trace.command_bytes()))
        self.assertIn(sha256_identifier(canonical_json(self.trace.observation).encode()), result.protocol.evidence_refs)
        self.assertEqual(self.trace.dispatches, 1)

    def test_command_receipt_and_output_are_separate_from_physical_condition(self) -> None:
        first = self.evaluate(EffectState.EFFECT_ACK_CONTINUE)
        self.trace.execute()
        observation = self.trace.observation
        self.trace.observation = None
        second = self.evaluate(EffectState.EFFECT_ACK_CONTINUE,
                               "SS03_OBTAIN_INDEPENDENT_PHYSICAL_READBACK", first.protocol)
        self.trace.observation = observation
        third = self.evaluate(EffectState.EFFECT_ACK_DONE, previous=second.protocol)
        verify_protocol_chain([first.protocol, second.protocol, third.protocol])
        self.assertTrue(self.trace.command_reply_received)

    def test_lost_reply_requires_readback_and_never_reexecutes_command(self) -> None:
        self.trace.execute(lost_reply=True)
        readback = self.trace.observation
        self.trace.observation = None
        first = self.evaluate(EffectState.EFFECT_ACK_CONTINUE)
        self.trace.observation = readback
        second = self.evaluate(EffectState.EFFECT_ACK_DONE, previous=first.protocol)
        verify_protocol_chain([first.protocol, second.protocol])
        self.assertFalse(self.trace.command_reply_received)
        self.assertEqual(self.trace.dispatches, 1)
        with self.assertRaisesRegex(AssertionError, "must not be resubmitted"):
            self.trace.execute()

    def test_absent_information_reception_is_nack(self) -> None:
        self.trace.information_received = False
        self.evaluate(EffectState.EFFECT_NACK)

    def test_unresponsive_actuator_holds_then_blocks_at_declared_deadline(self) -> None:
        self.trace.execute(unresponsive=True)
        first = self.evaluate(EffectState.EFFECT_ACK_CONTINUE)
        self.trace.now_ms = self.trace.command["deadline_ms"] + 1
        second = self.evaluate(EffectState.EFFECT_ACK_BLOCK,
                               "SS03_OBSERVATION_DEADLINE_EXCEEDED", first.protocol)
        verify_protocol_chain([first.protocol, second.protocol])
        self.assertEqual(self.trace.dispatches, 1)
        self.assertFalse(self.trace.command_reply_received)
        self.assertFalse(self.trace.output_transitioned)

    def test_stuck_actuator_cannot_be_confirmed_by_output_transition(self) -> None:
        self.trace.execute(stuck=True)
        self.assertTrue(self.trace.output_transitioned)
        self.assertTrue(self.trace.command_reply_received)
        self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_PHYSICAL_TARGET_NOT_OBSERVED")

    def test_contradictory_physical_sensors_isolate_and_retain_both_signals(self) -> None:
        self.trace.execute()
        self.trace.observation["sensors"][1]["secured"] = False
        before = copy.deepcopy(self.trace.observation)
        result = self.evaluate(EffectState.EFFECT_ACK_ISOLATE, "SS03_CONTRADICTORY_PHYSICAL_FEEDBACK")
        self.assertEqual(self.trace.observation, before)
        self.assertIn(sha256_identifier(canonical_json(before).encode()), result.protocol.evidence_refs)

    def test_each_exact_physical_binding_rejects_an_unrelated_acknowledgement(self) -> None:
        for key in ("effect_id", "actuator", "from_state", "to_state", "principal",
                    "authorization", "policy", "configuration", "firmware", "request_hash"):
            with self.subTest(binding=key):
                self.trace = _PhysicalEffectSimulation()
                self.trace.execute()
                self.trace.observation[key] = "unrelated-" + self.trace.observation[key]
                self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_EXACT_BINDING_MISMATCH")

    def test_denied_revoked_and_expired_authorization_block_even_matching_feedback(self) -> None:
        for field, value in (("authorized", False), ("revoked", True), ("grant_expires_ms", 1029)):
            with self.subTest(field=field):
                self.trace = _PhysicalEffectSimulation()
                self.trace.execute()
                setattr(self.trace, field, value)
                self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_AUTHORIZATION_DENIED")

    def test_freshness_boundary_is_inclusive_and_one_ms_older_blocks(self) -> None:
        self.trace.execute()
        self.trace.now_ms = 1120
        self.evaluate(EffectState.EFFECT_ACK_DONE)
        self.trace.now_ms = 1121
        self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_OBSERVATION_OUTSIDE_FRESHNESS_WINDOW")

    def test_future_and_precommand_observations_block_despite_recent_delivery(self) -> None:
        self.trace.execute()
        for timestamp in (999, 1031):
            with self.subTest(observed_ms=timestamp):
                self.trace.observation["observed_ms"] = timestamp
                self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_OBSERVATION_OUTSIDE_FRESHNESS_WINDOW")

    def test_uncertain_clock_cannot_release_physical_effect(self) -> None:
        self.trace.execute()
        self.trace.clock_trusted = False
        self.evaluate(EffectState.EFFECT_ACK_CONTINUE, "SS03_ESTABLISH_OBSERVATION_CLOCK_BOUND")

    def test_old_or_consumed_sensor_sequence_blocks_replay(self) -> None:
        self.trace.execute()
        for sequence in (39, 40):
            with self.subTest(sequence=sequence):
                self.trace.observation["sensors"][0]["sequence"] = sequence
                self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_REPLAYED_OBSERVATION")

    def test_actuator_self_report_unknown_and_duplicate_observer_are_isolated(self) -> None:
        for source in ("simulated-lock-1", "unknown-observer", "simulated-bolt"):
            with self.subTest(source=source):
                self.trace = _PhysicalEffectSimulation()
                self.trace.execute()
                self.trace.observation["sensors"][0]["source"] = source
                self.evaluate(EffectState.EFFECT_ACK_ISOLATE,
                              "SS03_OBSERVER_IDENTITY_OR_INDEPENDENCE_UNVERIFIED")

    def test_missing_required_sensor_continues_without_strengthening_claim(self) -> None:
        self.trace.execute()
        self.trace.observation["sensors"].pop()
        self.evaluate(EffectState.EFFECT_ACK_CONTINUE, "SS03_OBTAIN_ALL_REQUIRED_SENSORS")

    def test_duplicate_readback_of_same_effect_is_idempotent_not_another_actuation(self) -> None:
        self.trace.execute()
        first = self.evaluate(EffectState.EFFECT_ACK_DONE)
        second = self.evaluate(EffectState.EFFECT_ACK_DONE, previous=first.protocol)
        self.assertIs(first.protocol, second.protocol)
        self.assertEqual(self.trace.dispatches, 1)

    def test_expired_done_readback_creates_protective_successor_without_erasing_original(self) -> None:
        self.trace.execute()
        first = self.evaluate(EffectState.EFFECT_ACK_DONE)
        original = first.protocol.to_json()
        self.trace.now_ms = 1121
        second = self.evaluate(EffectState.EFFECT_ACK_BLOCK, previous=first.protocol)
        verify_protocol_chain([first.protocol, second.protocol])
        self.assertEqual(first.protocol.to_json(), original)

    def test_changed_configuration_cannot_rebind_same_effect_to_old_done(self) -> None:
        self.trace.execute()
        first = self.evaluate(EffectState.EFFECT_ACK_DONE)
        self.trace = _PhysicalEffectSimulation()  # Separate candidate trace.
        self.trace.command["firmware"] = sha256_identifier(b"different-simulated-firmware")
        self.trace.execute()
        self.evaluate(EffectState.EFFECT_ACK_BLOCK, "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE", first.protocol)

    def test_prior_effect_done_cannot_complete_a_new_effect(self) -> None:
        self.trace.execute()
        first = self.evaluate(EffectState.EFFECT_ACK_DONE)
        self.trace = _PhysicalEffectSimulation()
        self.trace.command["effect_id"] = "simulated-effect-2"
        self.evaluate(EffectState.EFFECT_ACK_BLOCK, "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE", first.protocol)
        self.assertEqual(self.trace.dispatches, 0)

    def test_unsupported_transition_cannot_borrow_secured_sensor_semantics(self) -> None:
        self.trace.command["to_state"] = "unsecured"
        self.trace.execute()
        self.evaluate(EffectState.EFFECT_ACK_BLOCK, "SS03_TRANSITION_OUTSIDE_SIMULATION_SCOPE")

    def test_core_trust_boundary_boolean_assertions_alone_do_not_prove_hardware(self) -> None:
        # Deliberately bad adapter: the pure core cannot inspect physical truth.
        # This positive control prevents advertising the oracle as a live guard.
        self.assertIs(effect_ack_sync(request()).state, EffectState.EFFECT_ACK_DONE)
        self.evaluate(EffectState.EFFECT_ACK_CONTINUE)

    def test_original_native_ledger_and_terminal_read_back_simulation_scope_and_bytes(self) -> None:
        import qikvrt_temdd_event_ledger as native
        import qikvrt_effect_ack_http_terminal as terminal

        self.trace.execute()
        result = self.evaluate(EffectState.EFFECT_ACK_DONE)
        subject = {"repository": "ingolf-lohmann/qik-vrt", "pr": 539,
                   "head": "a" * 40, "tree": "b" * 40}  # Declared fixture subject only.
        event = {"schema": native.SCHEMA, "kind": "READBACK", "subject": subject,
                 "provenance": {"source": "transputer", "native_event_id": "test:ss03:readback"},
                 "observed_at": "2026-10-19T00:00:00Z", "message": "SS-03 simulation only",
                 "payload": {"command": self.trace.command, "observation": self.trace.observation,
                             "protocol": result.protocol.to_dict(), "hardware_test": False,
                             "physical_installation_accepted": False, "effect_ack_done": False}}
        with tempfile.TemporaryDirectory() as state:
            ledger = native.Ledger(state, subject)
            try:
                receipt = ledger.append(event)
                epoch, readback = terminal._durable_read(state, event)
                self.assertEqual(epoch, ledger.epoch)
                self.assertEqual(readback, receipt)
                self.assertEqual(ledger.append(event), receipt)
                self.assertEqual(len(ledger.replay(0)), 1)
                self.assertFalse(readback["dod"])
                self.assertFalse(readback["payload"]["effect_ack_done"])
                verify_protocol(ResponsibilityProtocol.from_dict(readback["payload"]["protocol"]))
            finally:
                ledger.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
