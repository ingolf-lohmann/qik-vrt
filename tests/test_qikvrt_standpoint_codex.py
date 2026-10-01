# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from src import qikvrt_standpoint_codex as codex

ROOT = Path(__file__).resolve().parents[1]


def independent_identity(stable_id: bytes, payload: bytes) -> bytes:
    return hashlib.sha256(
        b"QIKVRT-ELEMENT-V1\0" + b"\x00\x01" + codex.QIKVRT_SIGNATURE
        + stable_id + struct.pack(">Q", len(payload)) + payload
    ).digest()


def record(stable_id: bytes, payload: bytes) -> bytes:
    return (
        codex.QIKVRT_SIGNATURE + stable_id
        + independent_identity(stable_id, payload)
        + struct.pack(">Q", len(payload)) + payload
    )


def snapshot(records: bytes, count: int) -> bytes:
    return struct.pack(">8sHHQQ", b"QIKVRTSS", 1, 400, count, len(records)) + codex.QIKVRT_SIGNATURE + records


class StandpointCodexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.elements = (
            codex.Element(bytes(range(32)), b"\x00\xffQIKVRT\x00"),
            codex.Element(bytes(range(32, 64)), b""),
        )
        self.dump = codex.serialize(self.elements)

    def test_machine_contract_binds_exact_signature_and_layout(self) -> None:
        policy = json.loads((ROOT / "policy/QIKVRT_STANDPOINT_CODEX_V1.json").read_text())
        signature = policy["signature"]
        self.assertEqual(policy["schema"], "qikvrt_standpoint_codex_v1")
        self.assertEqual(signature["bytes"], 400)
        self.assertEqual(bytes.fromhex(signature["hex"]), codex.QIKVRT_SIGNATURE)
        self.assertEqual((ROOT / signature["path"]).read_bytes(), codex.QIKVRT_SIGNATURE)
        self.assertEqual(signature["sha256"], codex.SIGNATURE_SHA256)
        self.assertEqual(signature["descriptor"], codex.SIGNATURE_DESCRIPTOR)
        fields = signature["fields"]
        self.assertEqual(sum(field["bytes"] for field in fields), 400)
        offset = 0
        for field in fields:
            self.assertEqual(field["offset"], offset)
            offset += field["bytes"]
        self.assertEqual(policy["snapshot"]["header_bytes"], 28)
        self.assertEqual(policy["snapshot"]["minimum_bytes"], 428)
        self.assertEqual(policy["element"]["minimum_record_bytes"], 472)
        self.assertEqual(
            [(f["offset"], f["bytes"]) for f in policy["element"]["fields"]],
            [(0, 400), (400, 32), (432, 32), (464, 8), (472, "payload_bytes")],
        )
        self.assertEqual(
            [(f["offset"], f["bytes"]) for f in policy["snapshot"]["fields"]],
            [(0, 8), (8, 2), (10, 2), (12, 8), (20, 8), (28, 400), (428, "body_bytes")],
        )
        self.assertTrue(all(policy["fail_closed"].values()))
        self.assertFalse(policy["normative_process"]["chatgpt_required"])
        self.assertFalse(policy["normative_process"]["external_model_required"])
        self.assertFalse(policy["semantic_source"]["recovered_historical_400_byte_image"])
        self.assertIn("policy/QIKVRT_STANDPOINT_CODEX_V1.json", json.loads((ROOT / "AI_CONTEXT.json").read_text())["required_read_order"])
        for key in ("specification", "implementation", "regression_tests"):
            self.assertTrue((ROOT / policy[key]).is_file())
        vector = policy["fixed_vector"]
        self.assertEqual([e.stable_id.hex() for e in self.elements], vector["stable_ids_hex"])
        self.assertEqual([e.payload.hex() for e in self.elements], vector["payloads_hex"])
        self.assertEqual([e.identity.hex() for e in self.elements], vector["identity_hex"])
        self.assertEqual(len(self.dump), vector["snapshot_bytes"])
        self.assertEqual(hashlib.sha256(self.dump).hexdigest(), vector["snapshot_sha256"])

    def test_fixed_signature_and_snapshot_vectors(self) -> None:
        self.assertEqual(len(codex.QIKVRT_SIGNATURE), 400)
        self.assertEqual(codex.SIGNATURE_SHA256, "27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792")
        self.assertEqual(len(self.dump), 1381)
        self.assertEqual(hashlib.sha256(self.dump).hexdigest(), "ef8b7d6bf629a8cdfd4e537de213917ae48a407d76179e2c8cb62dc865a680b5")
        self.assertEqual(self.elements[0].identity.hex(), "edd507903074e055f4033d4b44597cb4f574f1f34e11ce6e6629d1017a4f4468")
        self.assertEqual(self.elements[1].identity.hex(), "037c3220c2851a2c5491e3c03f5787de9756e3d3cc96218e21eeedc415cabb48")
        codex.validate_signature(codex.QIKVRT_SIGNATURE)

    def test_independently_packed_wire_and_identity(self) -> None:
        wire = snapshot(b"".join(record(e.stable_id, e.payload) for e in self.elements), 2)
        self.assertEqual(wire, self.dump)
        self.assertEqual(codex.deserialize(wire), self.elements)
        for element in self.elements:
            self.assertEqual(element.identity, independent_identity(element.stable_id, element.payload))

    def test_roundtrip_preserves_every_field_and_dump_byte(self) -> None:
        restored = codex.deserialize(self.dump)
        self.assertEqual(restored, self.elements)
        self.assertEqual(codex.serialize(restored), self.dump)
        for element in restored:
            self.assertEqual(element.signature, codex.QIKVRT_SIGNATURE)
            self.assertEqual(len(element.identity), 32)

    def test_empty_set_has_one_canonical_428_byte_snapshot(self) -> None:
        wire = snapshot(b"", 0)
        self.assertEqual(len(wire), 428)
        self.assertEqual(codex.serialize([]), wire)
        self.assertEqual(codex.deserialize(wire), ())
        self.assertEqual(codex.serialize(codex.deserialize(wire)), wire)

    def test_all_input_permutations_have_identical_bytes(self) -> None:
        elements = [codex.Element(bytes([n]) * 32, bytes([n])) for n in range(4)]
        expected = codex.serialize(elements)
        for permutation in itertools.permutations(elements):
            self.assertEqual(codex.serialize(iter(permutation)), expected)

    def test_opaque_bytes_are_not_normalized_or_text_decoded(self) -> None:
        payloads = (bytes(range(256)), b"\x00" * 4097, "é".encode(), "e\u0301".encode(), b"\xff\xfe")
        elements = tuple(codex.Element(bytes([n]) * 32, payload) for n, payload in enumerate(payloads))
        restored = codex.deserialize(codex.serialize(elements))
        self.assertEqual(restored, elements)
        self.assertNotEqual(restored[2].payload, restored[3].payload)

    def test_identical_payloads_are_distinct_when_stable_ids_differ(self) -> None:
        elements = [codex.Element(bytes([n]) * 32, b"same") for n in range(2)]
        self.assertNotEqual(elements[0].identity, elements[1].identity)
        self.assertEqual(codex.deserialize(codex.serialize(elements)), tuple(elements))

    def test_content_change_preserves_label_but_changes_identity(self) -> None:
        old = self.elements[0]
        successor = codex.Element(old.stable_id, old.payload + b"new")
        self.assertEqual(old.stable_id, successor.stable_id)
        self.assertNotEqual(old.identity, successor.identity)

    def test_file_dump_and_fresh_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.qikvrt"
            path.write_bytes(self.dump)
            readback = path.read_bytes()
            self.assertEqual(readback, self.dump)
            self.assertEqual(codex.deserialize(readback), self.elements)
            self.assertEqual(codex.serialize(codex.deserialize(readback)), readback)

    def test_codec_runs_with_network_and_external_execution_denied(self) -> None:
        with patch("socket.socket", side_effect=AssertionError("network forbidden")), patch("urllib.request.urlopen", side_effect=AssertionError("external service forbidden")), patch("subprocess.Popen", side_effect=AssertionError("external execution forbidden")):
            wire = codex.serialize(self.elements)
            self.assertEqual(codex.deserialize(wire), self.elements)
            self.assertEqual(wire, self.dump)

    def test_historical_charter_keeps_published_exact_bytes(self) -> None:
        charter = (ROOT / "docs/CHARTA_MASCHINENPRUEFBARE_WISSENSCHAFT.md").read_bytes()
        self.assertEqual(len(charter), 10127)
        self.assertEqual(hashlib.sha256(charter).hexdigest(), "7fb4e5c369b079e93ce409e9ca4f6830476a1b6dbd42543273d85164e111a631")

    def test_every_single_signature_bit_mutation_fails_closed(self) -> None:
        for position in range(400):
            for bit in range(8):
                mutated = bytearray(codex.QIKVRT_SIGNATURE)
                mutated[position] ^= 1 << bit
                with self.subTest(position=position, bit=bit):
                    with self.assertRaises(codex.CodexError):
                        codex.validate_signature(bytes(mutated))

    def test_signature_wrong_lengths_and_types_are_rejected(self) -> None:
        for signature in (b"", codex.QIKVRT_SIGNATURE[:-1], codex.QIKVRT_SIGNATURE + b"\0", bytearray(codex.QIKVRT_SIGNATURE), None, "400"):
            with self.subTest(signature_type=type(signature)):
                with self.assertRaises(codex.CodexError):
                    codex.Element(bytes(32), b"", signature)

    def test_rehashed_foreign_standpoint_is_not_authorized(self) -> None:
        signature = codex.QIKVRT_SIGNATURE
        length = struct.unpack_from(">H", signature, 12)[0]
        payload = signature[48:48 + length].replace(b'"QIKVRT"', b'"OTHER!"')
        self.assertNotEqual(payload, signature[48:48 + length])
        foreign = (signature[:16] + hashlib.sha256(b"QIKVRT-STANDPOINT-V1\0" + signature[:16] + payload).digest() + payload + bytes(352 - length))
        self.assertEqual(len(foreign), 400)
        with self.assertRaises(codex.CodexError):
            codex.validate_signature(foreign)
        wire = self.dump[:28] + foreign + self.dump[428:]
        with self.assertRaises(codex.CodexError):
            codex.deserialize(wire)

    def test_each_wire_signature_must_equal_bound_signature(self) -> None:
        for start in (28, 428, 428 + 472 + len(self.elements[0].payload)):
            wire = bytearray(self.dump)
            wire[start + 399] = 1
            with self.subTest(start=start):
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(bytes(wire))

    def test_payload_id_and_digest_tampering_is_rejected(self) -> None:
        for offset in (428 + 400, 428 + 432, 428 + 472):
            wire = bytearray(self.dump)
            wire[offset] ^= 1
            with self.subTest(offset=offset):
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(bytes(wire))

    def test_duplicate_identical_or_changed_members_are_rejected(self) -> None:
        original = self.elements[0]
        for duplicate in (original, codex.Element(original.stable_id, b"changed")):
            with self.subTest(duplicate=duplicate):
                with self.assertRaises(codex.CodexError):
                    codex.serialize([original, duplicate])
                wire = snapshot(record(original.stable_id, original.payload) + record(duplicate.stable_id, duplicate.payload), 2)
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(wire)

    def test_even_a_simulated_digest_collision_fails_closed(self) -> None:
        with patch.object(codex, "_identity", return_value=b"x" * 32):
            elements = [codex.Element(bytes([n]) * 32, b"same") for n in range(2)]
            with self.assertRaises(codex.CodexError):
                codex.serialize(elements)
            records = b"".join(e.signature + e.stable_id + e.identity + struct.pack(">Q", 4) + b"same" for e in elements)
            with self.assertRaises(codex.CodexError):
                codex.deserialize(snapshot(records, 2))

    def test_reordered_valid_records_are_noncanonical(self) -> None:
        records = b"".join(record(e.stable_id, e.payload) for e in reversed(self.elements))
        with self.assertRaises(codex.CodexError):
            codex.deserialize(snapshot(records, 2))

    def test_every_truncated_prefix_is_rejected(self) -> None:
        for length in range(len(self.dump)):
            with self.subTest(length=length):
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(self.dump[:length])

    def test_trailing_bytes_and_surplus_records_are_rejected(self) -> None:
        with self.assertRaises(codex.CodexError):
            codex.deserialize(self.dump + b"\0")
        records = b"".join(record(e.stable_id, e.payload) for e in self.elements)
        for count in (0, 1, 3, 2**64 - 1):
            with self.subTest(count=count):
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(snapshot(records, count))

    def test_inconsistent_or_overflowing_wire_lengths_are_rejected(self) -> None:
        for offset in (20, 428 + 464):
            for length in (0, 1, 2**64 - 1):
                wire = bytearray(self.dump)
                struct.pack_into(">Q", wire, offset, length)
                with self.subTest(offset=offset, length=length):
                    with self.assertRaises(codex.CodexError):
                        codex.deserialize(bytes(wire))

    def test_wrong_magic_versions_and_signature_lengths_are_rejected(self) -> None:
        for offset, value in ((0, b"OTHER!!!"), (8, b"\x00\x02"), (10, b"\x01\x8f")):
            wire = self.dump[:offset] + value + self.dump[offset + len(value):]
            with self.subTest(offset=offset):
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(wire)

    def test_wrong_element_and_snapshot_types_fail_closed(self) -> None:
        for stable_id in (bytes(31), bytes(33), "a" * 32, bytearray(32), None):
            with self.assertRaises(codex.CodexError):
                codex.Element(stable_id, b"")
        for payload in ("text", bytearray(b"bytes"), None, 3):
            with self.assertRaises(codex.CodexError):
                codex.Element(bytes(32), payload)
        for wire in (None, bytearray(self.dump), self.dump.hex()):
            with self.assertRaises(codex.CodexError):
                codex.deserialize(wire)
        for elements in (None, [object()], [dict(payload=b"")]):
            with self.assertRaises(codex.CodexError):
                codex.serialize(elements)

    def test_mutated_frozen_object_is_revalidated_before_serialization(self) -> None:
        element = codex.Element(bytes(32), b"payload")
        object.__setattr__(element, "identity", bytes(32))
        with self.assertRaises(codex.CodexError):
            codex.serialize([element])

    def test_resource_limits_have_exact_acceptance_boundaries(self) -> None:
        exact = codex.Limits(len(self.dump), 2, len(self.elements[0].payload))
        self.assertEqual(codex.serialize(self.elements, limits=exact), self.dump)
        self.assertEqual(codex.deserialize(self.dump, limits=exact), self.elements)
        for limits in (codex.Limits(len(self.dump) - 1, 2, 100), codex.Limits(10000, 1, 100), codex.Limits(10000, 2, len(self.elements[0].payload) - 1)):
            with self.subTest(limits=limits):
                with self.assertRaises(codex.CodexError):
                    codex.serialize(self.elements, limits=limits)
                with self.assertRaises(codex.CodexError):
                    codex.deserialize(self.dump, limits=limits)
        self.assertEqual(codex.serialize([], limits=codex.Limits(428, 0, 0)), snapshot(b"", 0))

    def test_invalid_or_boolean_limits_are_rejected(self) -> None:
        for name in ("max_snapshot_bytes", "max_elements", "max_payload_bytes"):
            for value in (-1, True, 1.0, "2", 2**64):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(codex.CodexError):
                        codex.Limits(**{name: value})
        for limits in (None, dict(max_elements=2)):
            with self.assertRaises(codex.CodexError):
                codex.serialize(self.elements, limits=limits)
            with self.assertRaises(codex.CodexError):
                codex.deserialize(self.dump, limits=limits)

    def test_bounded_iterable_stops_when_count_budget_is_exceeded(self) -> None:
        consumed = []
        def members():
            for n in range(100):
                consumed.append(n)
                yield codex.Element(bytes([n]) * 32, b"")
        with self.assertRaises(codex.CodexError):
            codex.serialize(members(), limits=codex.Limits(10000, 2, 0))
        self.assertEqual(consumed, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
