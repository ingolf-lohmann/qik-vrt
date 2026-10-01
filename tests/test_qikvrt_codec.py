# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import io
import json
import random
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

from src import qikvrt_codec as codec
from src import qikvrt_standpoint_codex as codex

ROOT = Path(__file__).resolve().parents[1]
# Exact review-candidate seed reused from PR #424, not a historical recovered image.
SEED = codex.QIKVRT_SIGNATURE


class FragmentedReader(io.BytesIO):
    def read(self, size=-1):
        return super().read(min(size, 7))


class ShortWriter(io.BytesIO):
    def write(self, value):
        return super().write(value[:13])


class ByteCodecTests(unittest.TestCase):
    def test_roundtrip_all_profiles_and_arbitrary_bytes(self):
        rng = random.Random(4102026)
        inputs = [b"", b"\0", bytes(range(256)), b"\xff" * 8192,
                  b"QIKVRT\0\xff" * 40000, rng.randbytes(270000)]
        inputs.extend(rng.randbytes(rng.randrange(12000)) for _ in range(30))
        for profile in codec.PROFILES:
            for raw in inputs:
                with self.subTest(profile=profile, size=len(raw)):
                    encoded = codec.encode(raw, signature=SEED, profile=profile)
                    self.assertEqual(codec.decode(encoded, signature=SEED), raw)

    def test_independent_empty_wire_vector(self):
        header = b"QIKVRTC\0" + bytes.fromhex("010001a000040000") + SEED
        footer_prefix = b"\xff" + b"\0" * 16
        expected = header + footer_prefix + hashlib.sha256(header + footer_prefix).digest()
        self.assertEqual(codec.encode(b"", signature=SEED), expected)
        self.assertEqual(codec.decode(expected, signature=SEED), b"")

    def test_legacy_v1_byte_transport_remains_readable_after_standpoint_adoption(self):
        legacy_seed = bytes(range(200)) * 2
        header = b"QIKVRTC\0" + bytes.fromhex("010001a000040000") + legacy_seed
        prefix = b"\xff" + b"\0" * 16
        legacy_wire = header + prefix + hashlib.sha256(header + prefix).digest()
        self.assertEqual(codec.decode(legacy_wire, signature=legacy_seed), b"")

    def test_same_profile_is_deterministic_and_short_reads_do_not_change_wire(self):
        raw = bytes(range(256)) * 50
        a, b = io.BytesIO(), ShortWriter()
        info_a = codec.encode_stream(io.BytesIO(raw), a, signature=SEED, block_bytes=4096)
        info_b = codec.encode_stream(FragmentedReader(raw), b, signature=SEED, block_bytes=4096)
        self.assertEqual(a.getvalue(), b.getvalue())
        self.assertEqual(info_a, info_b)
        target = ShortWriter()
        info_c = codec.decode_stream(FragmentedReader(a.getvalue()), target, signature=SEED)
        self.assertEqual(info_a, info_c)
        self.assertEqual(target.getvalue(), raw)

    def test_raw_fallback_has_bounded_expansion(self):
        raw = random.Random(7).randbytes(100000)
        for profile in ("fast", "balanced", "compact", "raw"):
            encoded = codec.encode(raw, signature=SEED, profile=profile, block_bytes=65536)
            self.assertLessEqual(len(encoded), len(raw) + 465 + 2 * 41)
            self.assertEqual(codec.decode(encoded, signature=SEED), raw)

    def test_probe_and_full_trial_are_interoperable(self):
        raw = random.Random(8).randbytes(200000)
        a = codec.encode(raw, signature=SEED, profile="fast", probe=True)
        b = codec.encode(raw, signature=SEED, profile="fast", probe=False)
        self.assertEqual(codec.decode(a, signature=SEED), codec.decode(b, signature=SEED))

    def test_balanced_and_compact_do_not_skip_sampling_adversary(self):
        raw = bytearray(b"\0" * codec.DEFAULT_BLOCK_BYTES)
        rng = random.Random(8)
        for offset in (0, len(raw) // 3, 2 * len(raw) // 3, len(raw) - 2048):
            raw[offset:offset + 2048] = rng.randbytes(2048)
        raw = bytes(raw)
        self.assertTrue(codec._probably_incompressible(raw))
        for profile in ("balanced", "compact"):
            encoded = codec.encode(raw, signature=SEED, profile=profile)
            self.assertEqual(encoded, codec.encode(raw, signature=SEED, profile=profile, probe=False))
            self.assertLess(len(encoded), len(raw) // 10)
            self.assertEqual(codec.decode(encoded, signature=SEED), raw)

    def test_seed_length_type_and_mismatch_fail_closed(self):
        for seed in (b"", b"a" * 399, b"a" * 401, "a" * 400, bytearray(SEED)):
            with self.subTest(seed_type=type(seed)), self.assertRaises(codec.CodecError):
                codec.encode(b"x", signature=seed)
        encoded = codec.encode(b"x", signature=SEED)
        with self.assertRaisesRegex(codec.CodecError, "SIGNATURE_MISMATCH"):
            codec.decode(encoded, signature=b"a" * 400)

    def test_mutations_are_rejected_at_every_header_field_payload_and_footer(self):
        encoded = codec.encode(bytes(range(256)) * 20, signature=SEED, profile="raw")
        for offset in (0, 7, 8, 9, 10, 11, 12, 15, 16, 415, 416, 420,
                       424, 430, 457, 600, len(encoded) - 1, len(encoded) - 49):
            changed = bytearray(encoded)
            changed[offset] ^= 0x80
            with self.subTest(offset=offset), self.assertRaises(codec.CodecError):
                codec.decode(bytes(changed), signature=SEED)

    def test_truncation_and_trailing_input_rejected(self):
        encoded = codec.encode(b"abc" * 4000, signature=SEED, block_bytes=4096)
        for end in list(range(465)) + [len(encoded) - 1, len(encoded) - 49]:
            with self.subTest(end=end), self.assertRaises(codec.CodecError):
                codec.decode(encoded[:end], signature=SEED)
        for tail in (b"\0", encoded):
            with self.assertRaisesRegex(codec.CodecError, "TRAILING_INPUT"):
                codec.decode(encoded + tail, signature=SEED)

    def test_limits_checked_before_block_allocation_or_output(self):
        encoded = codec.encode(b"a" * 100000, signature=SEED)
        sink = io.BytesIO()
        with self.assertRaisesRegex(codec.CodecError, "OUTPUT_LIMIT_EXCEEDED"):
            codec.decode_stream(io.BytesIO(encoded), sink, signature=SEED, max_output_bytes=99999)
        self.assertEqual(sink.getvalue(), b"")
        with self.assertRaisesRegex(codec.CodecError, "BLOCK_LIMIT_EXCEEDED"):
            codec.decode_stream(io.BytesIO(encoded), sink, signature=SEED, max_block_bytes=4096)

    def test_bomb_concatenated_stream_dictionary_and_invalid_lengths_rejected(self):
        header = codec.HEADER.pack(codec.MAGIC, 1, 0, 416, 4096) + SEED
        compressed = zlib.compress(b"x" * 1000000)
        frame = codec.BLOCK.pack(codec.ZLIB, 4096, len(compressed), b"\0" * 32)
        with self.assertRaises(codec.CodecError):
            codec.decode(header + frame + compressed, signature=SEED)
        payload = zlib.compress(b"x" * 1000) + zlib.compress(b"y" * 1000)
        frame = codec.BLOCK.pack(codec.ZLIB, 2000, len(payload), b"\0" * 32)
        with self.assertRaises(codec.CodecError):
            codec.decode(header + frame + payload, signature=SEED)
        compressor = zlib.compressobj(zdict=b"qikvrt-dictionary")
        payload = compressor.compress(b"qikvrt-dictionary" * 100) + compressor.flush()
        frame = codec.BLOCK.pack(codec.ZLIB, 1700, len(payload), b"\0" * 32)
        with self.assertRaises(codec.CodecError):
            codec.decode(header + frame + payload, signature=SEED)
        for method, raw_size, stored_size in ((0, 0, 0), (0, 1, 2), (1, 100, 100),
                                                (1, 4097, 1), (7, 1, 1)):
            frame = codec.BLOCK.pack(method, raw_size, stored_size, b"\0" * 32)
            with self.subTest(method=method, size=raw_size), self.assertRaises(codec.CodecError):
                codec.decode(header + frame, signature=SEED)

    def test_short_nonterminal_block_is_noncanonical(self):
        header = codec.HEADER.pack(codec.MAGIC, 1, 0, 416, 4096) + SEED
        raw = b"a"
        frame = codec.BLOCK.pack(0, 1, 1, hashlib.sha256(raw).digest()) + raw
        with self.assertRaisesRegex(codec.CodecError, "NONCANONICAL_BLOCK_ORDER"):
            codec.decode(header + frame + frame, signature=SEED)

    def test_late_failure_does_not_claim_container_acceptance(self):
        encoded = codec.encode(b"abc", signature=SEED)
        sink = io.BytesIO()
        with self.assertRaisesRegex(codec.CodecError, "FOOTER_MISMATCH"):
            codec.decode_stream(io.BytesIO(encoded[:-1] + bytes([encoded[-1] ^ 1])),
                                sink, signature=SEED)
        self.assertEqual(sink.getvalue(), b"abc")

    def test_invalid_reader_writer_and_options_do_not_loop(self):
        class Nonblocking:
            def read(self, size):
                return None
            def write(self, value):
                return None
        with self.assertRaises(codec.CodecError):
            codec.encode_stream(Nonblocking(), io.BytesIO(), signature=SEED)
        with self.assertRaises(codec.CodecError):
            codec.encode_stream(io.BytesIO(b"x"), Nonblocking(), signature=SEED)
        for options in ({"block_bytes": True}, {"block_bytes": 4095},
                        {"block_bytes": 2**32}, {"profile": "future"}, {"probe": 1}):
            with self.assertRaises(codec.CodecError):
                codec.encode(b"x", signature=SEED, **options)

    def test_cli_roundtrip_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            seed, source, encoded, decoded = (root / n for n in ("seed", "input", "wire", "output"))
            seed.write_bytes(SEED)
            source.write_bytes(bytes(range(256)) * 100)
            cli = [sys.executable, "-B", "-m", "src.qikvrt_codec"]
            def run(operation, input_path, output_path):
                return subprocess.run(cli + [operation, str(input_path), str(output_path),
                                      "--signature-file", str(seed)], cwd=ROOT,
                                      capture_output=True, timeout=10)
            self.assertEqual(run("encode", source, encoded).returncode, 0)
            self.assertEqual(run("decode", encoded, decoded).returncode, 0)
            self.assertEqual(decoded.read_bytes(), source.read_bytes())
            before = decoded.read_bytes()
            encoded.write_bytes(encoded.read_bytes()[:-1])
            self.assertEqual(run("decode", encoded, decoded).returncode, 2)
            self.assertEqual(decoded.read_bytes(), before)
            self.assertFalse(list(root.glob(".qikvrt-codec-*")))
            self.assertEqual(run("encode", source, source).returncode, 2)
            self.assertEqual(run("encode", source, seed).returncode, 2)
            self.assertEqual(seed.read_bytes(), SEED)


class StandpointIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.a = codex.Element(b"\x01" * 32, b"a\0\xff")
        self.b = codex.Element(b"\x02" * 32, b"b")

    def test_canonical_snapshot_bytes_are_preserved_without_a_second_format(self):
        for elements in ([], [self.a], [self.b, self.a]):
            expected = codex.serialize(elements)
            for profile in codec.PROFILES:
                wire = codec.encode_snapshot(elements, profile=profile)
                self.assertEqual(codec.decode(wire, signature=SEED), expected)
                decoded = codec.decode_snapshot(wire)
                self.assertEqual(codex.serialize(decoded), expected)
                self.assertEqual(decoded, codex.deserialize(expected))

    def test_stable_labels_and_content_identities_survive_transport(self):
        changed = codex.Element(self.a.stable_id, b"changed")
        same_payload_other_element = codex.Element(self.b.stable_id, self.a.payload)
        self.assertEqual(changed.stable_id, self.a.stable_id)
        self.assertNotEqual(changed.identity, self.a.identity)
        self.assertNotEqual(same_payload_other_element.identity, self.a.identity)
        self.assertEqual(codec.decode_snapshot(codec.encode_snapshot([changed])), (changed,))

    def test_existing_duplicate_and_order_guards_are_reused(self):
        with self.assertRaises(codex.CodexError):
            codec.encode_snapshot([self.a, codex.Element(self.a.stable_id, b"other")])
        raw = codex.serialize([self.a, self.b])
        start = codex.MIN_SNAPSHOT_BYTES
        record_a = raw[start:start + codex.MIN_ELEMENT_BYTES + len(self.a.payload)]
        record_b = raw[start + len(record_a):]
        noncanonical = raw[:start] + record_b + record_a
        with self.assertRaises(codex.CodexError):
            codec.decode_snapshot(codec.encode(noncanonical, signature=SEED))

    def test_valid_transport_does_not_authorize_a_foreign_standpoint(self):
        raw = bytearray(codex.serialize([self.a]))
        raw[codex.MIN_SNAPSHOT_BYTES] ^= 1
        wire = codec.encode(bytes(raw), signature=SEED)
        self.assertEqual(codec.decode(wire, signature=SEED), bytes(raw))
        with self.assertRaises(codex.CodexError):
            codec.decode_snapshot(wire)
        with self.assertRaises(codec.CodecError):
            codec.decode_snapshot(codec.encode(codex.serialize([self.a]), signature=b"x" * 400))

    def test_resource_limits_apply_to_transport_and_snapshot(self):
        wire = codec.encode_snapshot([self.a])
        with self.assertRaises(codec.CodecError):
            codec.decode_snapshot(wire, limits=codex.Limits(max_snapshot_bytes=428))
        with self.assertRaises(codex.CodexError):
            codec.decode_snapshot(wire, limits=codex.Limits(max_payload_bytes=2))
        with self.assertRaises(codec.CodecError):
            codec.decode_snapshot(wire, limits={})

    def test_contract_binds_existing_codec_and_exact_signature_file(self):
        contract = json.loads((ROOT / "policy/QIKVRT_CODEC_CONTRACT_V1.json").read_text())
        self.assertEqual(contract["wire"]["header_bytes"], 416)
        self.assertEqual(contract["wire"]["block_header_bytes"], 41)
        self.assertEqual(contract["wire"]["footer_bytes"], 49)
        self.assertEqual(contract["seed"]["bytes"], len(SEED))
        self.assertEqual(contract["profiles"], codec.PROFILES)
        self.assertEqual(contract["snapshot"]["implementation"], "src/qikvrt_standpoint_codex.py")
        self.assertEqual(contract["seed"]["snapshot_signature_sha256"],
                         "27a84a7e19e1b46f50d3a855b87da65f5fe07b806575b0d15ca0587b7cab5792")
        self.assertEqual((ROOT / contract["seed"]["snapshot_signature_path"]).read_bytes(), SEED)
        self.assertFalse(contract["claims"]["universal_compression_or_global_optimality"])
        self.assertFalse(contract["claims"]["all_runtime_environments_verified"])
        self.assertFalse(contract["claims"]["physical_effect_ack_done"])


if __name__ == "__main__":
    unittest.main()
