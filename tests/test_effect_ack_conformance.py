#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import time
import unicodedata
import unittest
from enum import Enum
from itertools import permutations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qikvrt_effect_ack import (  # noqa: E402
    CANONICAL_RECORD_PROFILE,
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectAckResult,
    EffectState,
    ProtocolIntegrityError,
    ResponsibilityProtocol,
    RiskLevel,
    canonical_json,
    canonical_json_bytes,
    compute_protocol_hash,
    compute_record_hash,
    ordinary_release,
    sha256_identifier,
    verify_protocol,
    verify_protocol_chain,
)


PAYLOAD = b"effect-checked information unit"
EVIDENCE_A = sha256_identifier(b"evidence-a")
EVIDENCE_B = sha256_identifier(b"evidence-b")
EVIDENCE_NEW = sha256_identifier(b"new-evidence")


def request(**changes: object) -> EffectAckRequest:
    values: dict[str, object] = {
        "protocol_root_id": "qikvrt:test:root",
        "input_id": "input-1",
        "payload": PAYLOAD,
        "declared_input_hash": sha256_identifier(PAYLOAD),
        "transport_ack": True,
        "origin_checked": True,
        "context_checked": True,
        "semantics_reconstructed": True,
        "effect_anticipated": True,
        "risk_classified": True,
        "risk_level": RiskLevel.LOW,
        "responsibility_assigned": True,
        "responsibility_owner": "responsible-owner",
        "connection_decision": ConnectionDecision.RELEASE,
        "policy_allows_release": True,
        "reasons": ("release policy evaluated",),
        "evidence_refs": (EVIDENCE_A,),
        "required_evidence_refs": (EVIDENCE_A,),
        "open_questions": (),
        "next_required_checks": (),
    }
    values.update(changes)
    return EffectAckRequest(**values)  # type: ignore[arg-type]


class CanonicalizationTests(unittest.TestCase):
    """VERIFY_CANONICALIZATION: fixed octets, hashes and rejection cases."""

    def test_unicode_nfc_normalization(self) -> None:
        expected = b'{"msg":"\xc3\xa4"}'
        for text in ("ä", "a\u0308"):
            with self.subTest(text=text):
                self.assertEqual(canonical_json_bytes({"msg": text}), expected)
                self.assertEqual(
                    compute_record_hash({"msg": text}),
                    "sha256:3e2c233238a32ee1e5a6de4b4cae8d1447652be6f03f416fc585c43a835df2db",
                )

    def test_nested_object_determinism(self) -> None:
        left = {"outer": {"b": 1, "a": 2}}
        right = {"outer": {"a": 2, "b": 1}}
        for record in (left, right):
            self.assertEqual(canonical_json_bytes(record), b'{"outer":{"a":2,"b":1}}')
            self.assertEqual(
                compute_record_hash(record),
                "sha256:77209164d05abc063fac37648106ce8110313b172578e17dcc7264859e55f307",
            )

    def test_key_order_independence(self) -> None:
        entries = [("z", 0), ("ä", 1), ("A", 2), ("a", 3)]
        expected = '{"A":2,"a":3,"z":0,"ä":1}'.encode("utf-8")
        for order in permutations(entries):
            self.assertEqual(canonical_json_bytes(dict(order)), expected)

    def test_array_order_preservation(self) -> None:
        forward = {"items": [1, 2, 3]}
        reverse = {"items": [3, 2, 1]}
        self.assertEqual(canonical_json_bytes(forward), b'{"items":[1,2,3]}')
        self.assertNotEqual(compute_record_hash(forward), compute_record_hash(reverse))

    def test_reproducible_hash_derivation(self) -> None:
        record = {"items": [1, 2, 3]}
        expected = "sha256:7aff5dcbe562761bfd9d8569cdd3226d3944acad6539db5d62ad3f67d9a45d0a"
        self.assertEqual(compute_record_hash(record), expected)
        self.assertEqual(compute_record_hash(record), expected)
        restored = json.loads(canonical_json_bytes(record))
        self.assertEqual(compute_record_hash(restored), expected)

    def test_recursive_key_and_value_nfc(self) -> None:
        record = {"outer": [{"a\u0308": ["e\u0301", {"o\u0308": "u\u0308"}]}]}
        expected = '{"outer":[{"ä":["é",{"ö":"ü"}]}]}'.encode("utf-8")
        self.assertEqual(canonical_json_bytes(record), expected)

    def test_nfc_key_collision_fails_closed(self) -> None:
        for record in ({"ä": 1, "a\u0308": 2}, {"x": [{"ä": 1, "a\u0308": 1}]}):
            with self.subTest(record=record), self.assertRaisesRegex(ValueError, "duplicate key"):
                compute_record_hash(record)

    def test_non_string_keys_fail_closed(self) -> None:
        for key in (1, True, None, ("x",)):
            with self.subTest(key=key), self.assertRaisesRegex(TypeError, "string object keys"):
                compute_record_hash({"nested": {key: "value"}})

    def test_floating_point_values_fail_closed(self) -> None:
        for value in (1.0, -0.0, float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaisesRegex(TypeError, "floating-point"):
                compute_record_hash({"nested": [value]})

    def test_lone_surrogates_fail_closed(self) -> None:
        for record in ({"msg": "\ud800"}, {"msg": "\udfff"}, {"\ud800": "x"}):
            with self.subTest(record=record), self.assertRaises(UnicodeEncodeError):
                canonical_json(record)

    def test_enum_values_use_the_same_recursive_rules(self) -> None:
        class Text(Enum):
            DECOMPOSED = "a\u0308"
        class Invalid(Enum):
            FLOAT = 1.5
        self.assertEqual(canonical_json_bytes({"msg": Text.DECOMPOSED}), b'{"msg":"\xc3\xa4"}')
        with self.assertRaisesRegex(TypeError, "floating-point"):
            compute_record_hash({"value": Invalid.FLOAT})

    def test_unicode_code_point_key_order(self) -> None:
        # Unicode code-point order differs from UTF-16 code-unit order here.
        record = {"\U00010000": 2, "\ue000": 1}
        self.assertEqual(canonical_json_bytes(record), '{"\ue000":1,"\U00010000":2}'.encode("utf-8"))

    def test_compact_utf8_and_json_scalar_types(self) -> None:
        record = {"z": "\"\\\n", "a": [None, True, False, -2, 0]}
        self.assertEqual(canonical_json_bytes(record), b'{"a":[null,true,false,-2,0],"z":"\\"\\\\\\n"}')
        self.assertNotEqual(compute_record_hash({"x": True}), compute_record_hash({"x": 1}))

    def test_hash_covers_every_supplied_field(self) -> None:
        record = {"msg": "ä", "record_hash": "kept", "signature": "kept"}
        raw = b'{"msg":"\xc3\xa4","record_hash":"kept","signature":"kept"}'
        self.assertEqual(compute_record_hash(record), "sha256:" + hashlib.sha256(raw).hexdigest())
        self.assertNotEqual(compute_record_hash(record), compute_record_hash({"msg": "ä"}))

    def test_record_root_must_be_an_object(self) -> None:
        for record in (None, "x", 1, [1, 2]):
            with self.subTest(record=record), self.assertRaisesRegex(TypeError, "must be an object"):
                compute_record_hash(record)

    def test_input_is_not_mutated(self) -> None:
        record = {"a\u0308": [{"b": "e\u0301"}]}
        before = json.dumps(record, ensure_ascii=True)
        compute_record_hash(record)
        self.assertEqual(json.dumps(record, ensure_ascii=True), before)

    def test_existing_protocol_hash_vector_is_preserved(self) -> None:
        protocol = EffectAckEngine().evaluate(
            request(), created_utc="2026-10-22T00:00:00Z"
        ).protocol
        self.assertEqual(
            protocol.protocol_hash,
            "sha256:d992e84ba02def2e29fa67752edefe31b5d6bd219a207fd13f40510188e3baa4",
        )
        verify_protocol(protocol)

    def test_required_evidence_gate_binding(self) -> None:
        root = Path(__file__).resolve().parents[1]
        policy = json.loads((root / "policy/QIKVRT_CANONICAL_RECORD_V1.json").read_bytes())
        self.assertEqual(policy["profile"], CANONICAL_RECORD_PROFILE)
        gate = policy["VERIFY_CANONICALIZATION"]
        self.assertIs(gate["required"], True)
        self.assertEqual(gate["command"], ["make", "canonicalization-test"])
        self.assertIn("test: canonicalization-test", (root / "Makefile").read_text())
        self.assertEqual(set(gate["assertions"]), {
            "unicode_nfc_normalization", "nested_object_determinism", "key_order_independence",
            "array_order_preservation", "reproducible_hash_derivation",
        })
        for assertion in gate["assertions"]:
            self.assertTrue(callable(getattr(self, "test_" + assertion)))


class FakeClock:
    def __init__(self, values: list[int]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> int:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


class EffectAckStateConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EffectAckEngine()

    def test_exactly_five_normative_states_exist(self) -> None:
        self.assertEqual(
            [state.value for state in EffectState],
            [
                "EFFECT_NACK",
                "EFFECT_ACK_CONTINUE",
                "EFFECT_ACK_DONE",
                "EFFECT_ACK_ISOLATE",
                "EFFECT_ACK_BLOCK",
            ],
        )

    def test_wire_states_match_repository_protocol_summary(self) -> None:
        summary_path = (
            Path(__file__).resolve().parents[1]
            / "external"
            / "ietf"
            / "EFFECT_ACK_PROTOCOL_SUMMARY.json"
        )
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["states"], [state.value for state in EffectState])
        self.assertTrue(summary["responsibility_protocol_required"])
        self.assertTrue(summary["canonical_json_required"])

    def test_effect_nack_when_no_effect_checkable_reception_exists(self) -> None:
        result = self.engine.evaluate(
            request(payload=None, transport_ack=False, declared_input_hash=None)
        )
        self.assertIs(result.state, EffectState.EFFECT_NACK)
        self.assertIn("NO_EFFECT_CHECKABLE_RECEPTION", result.protocol.reasons)

    def test_continue_means_checking_may_continue_but_effect_is_unreleased(self) -> None:
        result = self.engine.evaluate(
            request(
                origin_checked=False,
                connection_decision=ConnectionDecision.CONTINUE,
            )
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_CONTINUE)
        self.assertIn("ORIGIN_UNCHECKED", result.protocol.reasons)
        self.assertFalse(result.ordinary_release)

    def test_done_is_reached_when_every_release_gate_is_satisfied(self) -> None:
        result = self.engine.evaluate(request())
        self.assertIs(result.state, EffectState.EFFECT_ACK_DONE)
        self.assertTrue(result.ordinary_release)
        self.assertTrue(ordinary_release(result))
        verify_protocol(result.protocol)

    def test_every_result_contains_all_draft_minimal_protocol_fields(self) -> None:
        required = {
            "protocol_root_id",
            "protocol_version",
            "protocol_id",
            "previous_protocol_id",
            "previous_protocol_hash",
            "protocol_hash",
            "input_id",
            "input_hash",
            "state",
            "transport_ack",
            "origin_checked",
            "context_checked",
            "semantics_reconstructed",
            "effect_anticipated",
            "risk_classified",
            "risk_level",
            "responsibility_assigned",
            "responsibility_owner",
            "connection_decided",
            "reasons",
            "evidence_refs",
            "open_questions",
            "next_required_checks",
            "created_utc",
        }
        for item in (
            request(payload=None, transport_ack=False, declared_input_hash=None),
            request(connection_decision=ConnectionDecision.CONTINUE),
            request(),
            request(connection_decision=ConnectionDecision.ISOLATE),
            request(connection_decision=ConnectionDecision.BLOCK),
        ):
            protocol_fields = self.engine.evaluate(item).protocol.to_dict()
            self.assertTrue(required.issubset(protocol_fields))

    def test_isolate_separates_effect_from_ordinary_flow(self) -> None:
        result = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.ISOLATE)
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_ISOLATE)
        self.assertIn("EXAMINE_EFFECT_IN_CONTAINMENT", result.protocol.next_required_checks)

    def test_block_stops_effect_and_exposes_a_responsible_continue_path(self) -> None:
        result = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.BLOCK)
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn(
            "FOLLOW_DOCUMENTED_REPAIR_OR_REVIEW_PATH",
            result.protocol.next_required_checks,
        )

    def test_done_is_the_only_ordinary_release_state(self) -> None:
        cases = {
            EffectState.EFFECT_NACK: request(
                payload=None, transport_ack=False, declared_input_hash=None
            ),
            EffectState.EFFECT_ACK_CONTINUE: request(
                connection_decision=ConnectionDecision.CONTINUE
            ),
            EffectState.EFFECT_ACK_DONE: request(),
            EffectState.EFFECT_ACK_ISOLATE: request(
                connection_decision=ConnectionDecision.ISOLATE
            ),
            EffectState.EFFECT_ACK_BLOCK: request(
                connection_decision=ConnectionDecision.BLOCK
            ),
        }
        for expected_state, item in cases.items():
            with self.subTest(state=expected_state.value):
                result = self.engine.evaluate(item)
                self.assertIs(result.state, expected_state)
                self.assertEqual(
                    result.ordinary_release,
                    expected_state is EffectState.EFFECT_ACK_DONE,
                )

    def test_transport_ack_alone_is_never_release_permission(self) -> None:
        result = self.engine.evaluate(
            request(
                origin_checked=False,
                context_checked=False,
                semantics_reconstructed=False,
                effect_anticipated=False,
                risk_classified=False,
                risk_level=RiskLevel.UNKNOWN,
                responsibility_assigned=False,
                responsibility_owner="",
                connection_decision=ConnectionDecision.UNDECIDED,
                policy_allows_release=False,
                evidence_refs=(),
            )
        )
        self.assertTrue(result.protocol.transport_ack)
        self.assertIs(result.state, EffectState.EFFECT_ACK_CONTINUE)
        self.assertFalse(result.ordinary_release)

    def test_json_facing_enum_values_are_normalized_at_request_boundary(self) -> None:
        item = request(risk_level="LOW", connection_decision="RELEASE")
        self.assertIs(item.risk_level, RiskLevel.LOW)
        self.assertIs(item.connection_decision, ConnectionDecision.RELEASE)
        self.assertIs(self.engine.evaluate(item).state, EffectState.EFFECT_ACK_DONE)

    def test_non_boolean_gate_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(TypeError, "origin_checked must be bool"):
            request(origin_checked=1)

    def test_synchronous_metadata_is_bounded(self) -> None:
        with self.assertRaisesRegex(ValueError, "reasons exceeds 128 items"):
            request(reasons=tuple(f"reason-{index}" for index in range(129)))
        with self.assertRaisesRegex(ValueError, "evidence_refs must contain"):
            request(evidence_refs=("not-a-content-hash",))
        with self.assertRaisesRegex(TypeError, "reasons must contain strings"):
            request(reasons=(1,))

    def test_each_required_done_condition_individually_prevents_done(self) -> None:
        mutations: dict[str, dict[str, object]] = {
            "origin": {"origin_checked": False},
            "context": {"context_checked": False},
            "semantics": {"semantics_reconstructed": False},
            "effect": {"effect_anticipated": False},
            "risk classification": {"risk_classified": False},
            "risk level": {"risk_level": RiskLevel.UNKNOWN},
            "responsibility": {"responsibility_assigned": False},
            "owner": {"responsibility_owner": ""},
            "connection": {
                "connection_decision": ConnectionDecision.UNDECIDED
            },
            "release decision": {
                "connection_decision": ConnectionDecision.CONTINUE
            },
            "policy": {"policy_allows_release": False},
            "open question": {"open_questions": ("unresolved",)},
            "next check": {"next_required_checks": ("check-x",)},
            "evidence": {"evidence_refs": ()},
        }
        for gate, changes in mutations.items():
            with self.subTest(gate=gate):
                result = self.engine.evaluate(request(**changes))
                self.assertIsNot(result.state, EffectState.EFFECT_ACK_DONE)
                self.assertFalse(result.ordinary_release)


class HashAndCanonicalizationConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EffectAckEngine()

    def test_payload_is_bound_to_protocol_by_sha256(self) -> None:
        result = self.engine.evaluate(request())
        self.assertEqual(result.protocol.input_hash, sha256_identifier(PAYLOAD))

    def test_declared_hash_mismatch_fails_closed(self) -> None:
        result = self.engine.evaluate(
            request(declared_input_hash="sha256:" + "0" * 64)
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn("INPUT_HASH_MISMATCH", result.protocol.reasons)
        self.assertFalse(result.ordinary_release)

    def test_malformed_declared_hash_fails_closed(self) -> None:
        result = self.engine.evaluate(request(declared_input_hash="not-a-hash"))
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn("DECLARED_INPUT_HASH_MALFORMED", result.protocol.reasons)

    def test_oversized_payload_fails_closed_without_hashing_it(self) -> None:
        engine = EffectAckEngine(max_payload_bytes=3)
        result = engine.evaluate(request())
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn("PAYLOAD_EXCEEDS_SYNCHRONOUS_LIMIT", result.protocol.reasons)

    def test_protocol_hash_excludes_volatile_timestamp(self) -> None:
        first = EffectAckEngine().evaluate(
            request(), created_utc="2026-07-20T00:00:00Z"
        ).protocol
        second = EffectAckEngine().evaluate(
            request(), created_utc="2099-01-01T12:34:56Z"
        ).protocol
        self.assertNotEqual(first.created_utc, second.created_utc)
        self.assertEqual(first.protocol_hash, second.protocol_hash)

    def test_canonical_json_normalizes_unicode_and_key_order(self) -> None:
        composed = "é"
        decomposed = unicodedata.normalize("NFD", composed)
        left = canonical_json({"z": decomposed, "a": ["x", 1]})
        right = canonical_json({"a": ["x", 1], "z": composed})
        self.assertEqual(left, right)
        self.assertEqual(left, '{"a":["x",1],"z":"é"}')

    def test_protocol_round_trip_verifies(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        decoded = json.loads(protocol.to_json())
        restored = ResponsibilityProtocol.from_dict(decoded)
        self.assertEqual(restored, protocol)

    def test_result_cannot_disagree_with_its_protocol(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        with self.assertRaisesRegex(ProtocolIntegrityError, "state and protocol"):
            EffectAckResult(EffectState.EFFECT_ACK_BLOCK, protocol)

    def test_created_timestamp_must_be_valid_utc(self) -> None:
        with self.assertRaisesRegex(ValueError, "RFC 3339 UTC"):
            self.engine.evaluate(request(), created_utc="not-a-timestamp")

    def test_protocol_tampering_is_detected(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        tampered = dataclasses.replace(protocol, responsibility_owner="attacker")
        with self.assertRaisesRegex(ProtocolIntegrityError, "protocol_hash mismatch"):
            verify_protocol(tampered)

    def test_false_done_record_is_rejected_even_with_recomputed_hash(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        malformed = dataclasses.replace(protocol, origin_checked=False, protocol_hash="")
        malformed = dataclasses.replace(
            malformed, protocol_hash=compute_protocol_hash(malformed)
        )
        with self.assertRaisesRegex(ProtocolIntegrityError, "false EFFECT_ACK_DONE"):
            verify_protocol(malformed)

    def test_deserialized_non_boolean_cannot_satisfy_a_gate(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        raw = protocol.to_dict()
        raw["origin_checked"] = 1
        # Recompute to prove type validation is independent of hash mismatch.
        candidate = ResponsibilityProtocol.from_dict(
            {**raw, "origin_checked": True}
        )
        malformed = dataclasses.replace(candidate, origin_checked=1, protocol_hash="")
        malformed = dataclasses.replace(
            malformed, protocol_hash=compute_protocol_hash(malformed)
        )
        with self.assertRaisesRegex(ProtocolIntegrityError, "origin_checked must be bool"):
            verify_protocol(malformed)

    def test_input_hash_requires_exact_sha256_shape(self) -> None:
        protocol = self.engine.evaluate(request()).protocol
        malformed = dataclasses.replace(protocol, input_hash="sha256:abc", protocol_hash="")
        malformed = dataclasses.replace(
            malformed, protocol_hash=compute_protocol_hash(malformed)
        )
        with self.assertRaisesRegex(ProtocolIntegrityError, "input_hash must be canonical"):
            verify_protocol(malformed)


class VersioningAndChainConformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = EffectAckEngine()

    def test_identical_reevaluation_is_idempotent(self) -> None:
        first = self.engine.evaluate(request()).protocol
        repeated = self.engine.evaluate(request(), previous_protocol=first).protocol
        self.assertIs(repeated, first)
        self.assertEqual(repeated.protocol_version, 1)

    def test_new_evidence_creates_new_hash_linked_version(self) -> None:
        first = self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_A,),
            )
        ).protocol
        second = self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_A, EVIDENCE_B),
            ),
            previous_protocol=first,
        ).protocol
        self.assertEqual(second.protocol_version, 2)
        self.assertEqual(second.previous_protocol_id, first.protocol_id)
        self.assertEqual(second.previous_protocol_hash, first.protocol_hash)
        self.assertNotEqual(second.protocol_hash, first.protocol_hash)
        verify_protocol_chain([first, second])

    def test_changed_evidence_cannot_silently_mutate_old_version(self) -> None:
        first = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.CONTINUE)
        ).protocol
        before = first.to_json()
        self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_NEW,),
            ),
            previous_protocol=first,
        )
        self.assertEqual(first.to_json(), before)

    def test_chain_link_tampering_is_detected(self) -> None:
        first = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.CONTINUE)
        ).protocol
        second = self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_A, EVIDENCE_B),
            ),
            previous_protocol=first,
        ).protocol
        broken = dataclasses.replace(second, previous_protocol_hash="sha256:" + "0" * 64)
        broken = dataclasses.replace(broken, protocol_hash=compute_protocol_hash(broken))
        with self.assertRaisesRegex(ProtocolIntegrityError, "link mismatch"):
            verify_protocol_chain([first, broken])

    def test_protocol_chain_cannot_switch_input_identity(self) -> None:
        first = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.CONTINUE)
        ).protocol
        second = self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_B,),
            ),
            previous_protocol=first,
        ).protocol
        switched = dataclasses.replace(second, input_id="different-input", protocol_hash="")
        switched = dataclasses.replace(
            switched, protocol_hash=compute_protocol_hash(switched)
        )
        with self.assertRaisesRegex(ProtocolIntegrityError, "input_id changed"):
            verify_protocol_chain([first, switched])

    def test_reevaluation_against_different_protocol_root_fails_closed(self) -> None:
        first = self.engine.evaluate(request()).protocol
        result = self.engine.evaluate(
            request(protocol_root_id="qikvrt:different-root"),
            previous_protocol=first,
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn(
            "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE", result.protocol.reasons
        )

    def test_reevaluation_cannot_rebind_same_input_id_to_new_payload(self) -> None:
        first = self.engine.evaluate(request()).protocol
        changed = b"different payload"
        result = self.engine.evaluate(
            request(
                payload=changed,
                declared_input_hash=sha256_identifier(changed),
            ),
            previous_protocol=first,
        )
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn(
            "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE", result.protocol.reasons
        )

    def test_corrupt_predecessor_fails_closed(self) -> None:
        first = self.engine.evaluate(request()).protocol
        corrupt = dataclasses.replace(first, protocol_hash="sha256:" + "0" * 64)
        result = self.engine.evaluate(request(), previous_protocol=corrupt)
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn(
            "PREVIOUS_PROTOCOL_INTEGRITY_FAILURE", result.protocol.reasons
        )
        self.assertFalse(result.ordinary_release)
        self.assertNotEqual(result.protocol.protocol_id, corrupt.protocol_id)
        self.assertTrue(
            result.protocol.protocol_root_id.startswith("qikvrt:incident:")
        )
        self.assertEqual(result.protocol.protocol_version, 1)
        self.assertEqual(len(result.protocol.evidence_refs), 2)

    def test_external_trusted_hash_anchor_detects_full_chain_rewrite(self) -> None:
        first = self.engine.evaluate(
            request(connection_decision=ConnectionDecision.CONTINUE)
        ).protocol
        second = self.engine.evaluate(
            request(
                connection_decision=ConnectionDecision.CONTINUE,
                evidence_refs=(EVIDENCE_A, EVIDENCE_B),
            ),
            previous_protocol=first,
        ).protocol
        trusted = {first.protocol_id: first.protocol_hash}
        verify_protocol_chain([first, second], trusted_protocol_hashes=trusted)

        rewritten_first = dataclasses.replace(
            first,
            reasons=tuple(sorted((*first.reasons, "rewritten"))),
            protocol_hash="",
        )
        rewritten_first = dataclasses.replace(
            rewritten_first,
            protocol_hash=compute_protocol_hash(rewritten_first),
        )
        rewritten_second = dataclasses.replace(
            second,
            previous_protocol_hash=rewritten_first.protocol_hash,
            protocol_hash="",
        )
        rewritten_second = dataclasses.replace(
            rewritten_second,
            protocol_hash=compute_protocol_hash(rewritten_second),
        )
        # A fully recomputed self-contained chain is internally consistent.
        verify_protocol_chain([rewritten_first, rewritten_second])
        # The externally retained hash exposes the rewrite.
        with self.assertRaisesRegex(ProtocolIntegrityError, "trusted protocol hash"):
            verify_protocol_chain(
                [rewritten_first, rewritten_second],
                trusted_protocol_hashes=trusted,
            )


class DeadlineAndDeterminismConformanceTests(unittest.TestCase):
    def test_nonpositive_deadline_fails_closed(self) -> None:
        result = EffectAckEngine().evaluate(request(), timeout_ms=0)
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertIn("SYNCHRONOUS_DEADLINE_EXCEEDED", result.protocol.reasons)
        self.assertIn(
            "CONTINUE_EVIDENCE_CHECK_ASYNCHRONOUSLY",
            result.protocol.next_required_checks,
        )

    def test_deadline_exhausted_during_check_prevents_done(self) -> None:
        clock = FakeClock([0, 2_000_000, 2_000_000])
        result = EffectAckEngine(clock_ns=clock).evaluate(request(), timeout_ms=1)
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertFalse(result.ordinary_release)

    def test_deadline_exhausted_during_finalization_prevents_done(self) -> None:
        clock = FakeClock([0, 500_000, 2_000_000, 2_000_000])
        result = EffectAckEngine(clock_ns=clock).evaluate(request(), timeout_ms=1)
        self.assertIs(result.state, EffectState.EFFECT_ACK_BLOCK)
        self.assertFalse(result.ordinary_release)

    def test_synchronous_haltpoint_returns_without_unbounded_waiting(self) -> None:
        start = time.monotonic()
        result = EffectAckEngine().evaluate(request(), timeout_ms=100)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 0.5)
        self.assertIs(result.state, EffectState.EFFECT_ACK_DONE)

    def test_same_deterministic_content_produces_same_state_and_hash(self) -> None:
        first = EffectAckEngine().evaluate(
            request(
                evidence_refs=(EVIDENCE_B, EVIDENCE_A),
                required_evidence_refs=(EVIDENCE_A,),
            ),
            created_utc="2026-01-01T00:00:00Z",
        )
        second = EffectAckEngine().evaluate(
            request(
                evidence_refs=(EVIDENCE_A, EVIDENCE_B, EVIDENCE_A),
                required_evidence_refs=(EVIDENCE_A,),
            ),
            created_utc="2027-01-01T00:00:00Z",
        )
        self.assertIs(first.state, second.state)
        self.assertEqual(first.protocol.protocol_hash, second.protocol.protocol_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
