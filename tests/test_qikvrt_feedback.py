# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded local feedback acceptance; no productive provider-effect claim."""
import hashlib
import random
import unittest
from dataclasses import replace

from src.qikvrt_codec import (
    BitFrame, CodecError, FeedbackPolicy, QIKVRT_SIGNATURE, encode, decode,
    feedback_step, join_bit_lanes, local_refeed, split_bit_lanes,
)
from src.qikvrt_effect_ack import verify_protocol


class FeedbackTests(unittest.TestCase):
    def frame(self, data=b"abcd", direction="left-to-right"):
        return BitFrame(direction, 0, 17, data)

    def test_every_byte_and_random_order_roundtrip(self):
        rng = random.Random(604)
        for data in (b"", bytes(range(256)), b"\x00" * 4096, b"\xff" * 4096,
                     rng.randbytes(65536), b"\xaa\x55" * 2048):
            zeros, ones = split_bit_lanes(data)
            self.assertEqual(data, join_bit_lanes(zeros, ones))
            self.assertEqual(len(data), len(zeros))
            self.assertTrue(all(a ^ b == 255 for a, b in zip(zeros, ones)))
        # Same counts, different order: never collapse to counts.
        self.assertNotEqual(split_bit_lanes(b"\xaa"), split_bit_lanes(b"\x55"))

    def test_both_directions_and_all_four_boundary_ports(self):
        policy = FeedbackPolicy(routes=((0, 0, 1), (1, 1, 2), (2, 2, 3), (3, 3, -1)))
        for direction in ("left-to-right", "right-to-left"):
            step = feedback_step(self.frame(direction=direction), policy)
            self.assertEqual(b"abcd", b"".join(data for _, data in step.ports))
            for port in range(4):
                child = local_refeed(step, policy, port=port, sequence=1, tick=18)
                self.assertEqual(direction, child.direction)
                self.assertEqual(port, child.port)
                self.assertEqual(step.frame.sha256, child.parent_sha256)
                self.assertEqual(1, child.hop)
                self.assertEqual(b"abcd"[port:port + 1], child.payload)

    def test_full_partial_and_absent_feedback(self):
        for routes, expected in ((( (0, 0, -1),), ((0, b"abcd"),)),
                                 (((2, 1, 3),), ((2, b"bc"),)), ((), ())):
            with self.subTest(routes=routes):
                step = feedback_step(self.frame(), FeedbackPolicy(routes=routes))
                self.assertEqual(expected, step.ports)
                self.assertEqual(b"abcd", step.frame.payload)
        with self.assertRaisesRegex(CodecError, "NO_FEEDBACK"):
            local_refeed(feedback_step(self.frame(), FeedbackPolicy()),
                         FeedbackPolicy(), port=0, sequence=1, tick=18)

    def test_existing_archive_decodes_before_feedback(self):
        payload = bytes(range(256)) * 128
        wire = encode(payload)
        policy = FeedbackPolicy(operation="decode", routes=((0, 0, -1),))
        result = feedback_step(self.frame(wire), policy)
        self.assertEqual(payload, result.processed)
        self.assertEqual(((0, payload),), result.ports)
        self.assertEqual(wire, join_bit_lanes(result.zeros, result.ones))
        for broken in (wire[:-1], wire + b"x", wire[:-1] + bytes([wire[-1] ^ 1])):
            with self.assertRaises(CodecError):
                feedback_step(self.frame(broken), policy)

    def test_existing_encode_chain_and_size_bound(self):
        step = feedback_step(self.frame(b"abcd" * 1000),
                             FeedbackPolicy(operation="encode", routes=((1, 0, -1),)))
        self.assertEqual(b"abcd" * 1000, decode(step.ports[0][1]))
        with self.assertRaisesRegex(CodecError, "ENCODE_BOUND"):
            feedback_step(self.frame(b"a"), FeedbackPolicy(operation="encode", max_output_bytes=1))

    def test_local_feedback_has_finite_hops(self):
        policy = FeedbackPolicy(routes=((0, 0, -1),), max_hops=2)
        frame = self.frame()
        for hop in (1, 2):
            step = feedback_step(frame, policy)
            frame = local_refeed(step, policy, port=0, sequence=hop, tick=17 + hop)
            self.assertEqual(b"abcd", frame.payload)
        with self.assertRaisesRegex(CodecError, "HOP_LIMIT"):
            local_refeed(feedback_step(frame, policy), policy, port=0, sequence=3, tick=20)
        with self.assertRaisesRegex(CodecError, "HOP_LIMIT"):
            feedback_step(replace(frame, hop=3), policy)

    def test_nonadvancing_clock_or_sequence_denied(self):
        policy = FeedbackPolicy(routes=((0, 0, -1),))
        step = feedback_step(self.frame(), policy)
        for sequence, tick in ((0, 18), (1, 17), (1, 16)):
            with self.assertRaisesRegex(CodecError, "NONADVANCING"):
                local_refeed(step, policy, port=0, sequence=sequence, tick=tick)

    def test_frame_identity_binds_duplex_clock_port_and_lineage(self):
        base = self.frame()
        changes = (replace(base, direction="right-to-left"), replace(base, tick=18),
                   replace(base, sequence=1), replace(base, port=1),
                   replace(base, payload=b"abce"), replace(base, hop=1, parent_sha256="0" * 64))
        self.assertEqual(7, len({base.sha256, *(x.sha256 for x in changes)}))

    def test_policy_changed_and_forged_step_denied(self):
        policy = FeedbackPolicy(routes=((0, 0, -1),))
        step = feedback_step(self.frame(), policy)
        with self.assertRaisesRegex(CodecError, "POLICY_CHANGED"):
            local_refeed(step, replace(policy, max_hops=2), port=0, sequence=1, tick=18)
        with self.assertRaisesRegex(CodecError, "TAMPERED"):
            local_refeed(replace(step, ports=((0, b"forged"),)), policy,
                         port=0, sequence=1, tick=18)

    def test_limits_routes_and_closed_schema(self):
        for kwargs in ({"version": 2}, {"sequence": True}, {"port": 4},
                       {"direction": "unknown"}, {"hop": 1}, {"payload": bytearray(b"x")}):
            with self.assertRaises(CodecError):
                replace(self.frame(), **kwargs)
        for kwargs in ({"operation": "exec"}, {"max_hops": True},
                       {"routes": [(0, 0, 1)]}, {"routes": ((4, 0, -1),)},
                       {"routes": ((0, 0, 1), (0, 1, 2))}):
            with self.assertRaises(CodecError):
                FeedbackPolicy(**kwargs)
        for policy in (FeedbackPolicy(max_input_bytes=3), FeedbackPolicy(max_output_bytes=3),
                       FeedbackPolicy(routes=((0, 0, 5),)),
                       FeedbackPolicy(routes=((0, 0, 3), (1, 2, -1)))):
            with self.assertRaises(CodecError):
                feedback_step(self.frame(), policy)
        with self.assertRaises(CodecError):
            join_bit_lanes(b"\x00", b"\x00")

    def test_effect_protocol_is_verified_and_never_self_releases(self):
        result = feedback_step(self.frame(), FeedbackPolicy(routes=((0, 0, -1),)))
        verify_protocol(result.effect_ack.protocol)
        self.assertFalse(result.effect_ack.ordinary_release)
        self.assertFalse(result.effect_ack.protocol.policy_allows_release)
        self.assertNotEqual("EFFECT_ACK_DONE", result.effect_ack.state.value)
        self.assertEqual(400, len(QIKVRT_SIGNATURE))
        self.assertEqual("27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792",
                         hashlib.sha256(QIKVRT_SIGNATURE).hexdigest())


if __name__ == "__main__":
    unittest.main()
