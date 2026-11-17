# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Independent reference, negative, native executable and ZIP acceptance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile
import zlib

from src import qikvrt_codec as reference
from tools import qikvrt_native_archive as archive


class NativeArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.root = Path(cls.work.name)
        cls.binary = cls.root / "qikvrt-archive"
        cls.sanitized = cls.root / "qikvrt-archive-ubsan"
        archive.compile_native(cls.binary)
        archive.compile_native(cls.sanitized, sanitize=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.root)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def run_native(self, *args, sanitized=False):
        return subprocess.run([str(self.sanitized if sanitized else self.binary), *map(str, args)],
                              capture_output=True, timeout=30)

    def test_sha256_known_vectors_and_padding_boundaries(self):
        for count in (0, 1, 3, 55, 56, 63, 64, 65, 127, 128, 1000000):
            data = b"a" * count
            source = self.path / "input"
            source.write_bytes(data)
            for sanitized in (False, True):
                with self.subTest(count=count, sanitized=sanitized):
                    p = self.run_native("sha256", source, sanitized=sanitized)
                    self.assertEqual(p.returncode, 0, p.stderr)
                    self.assertEqual(p.stdout.strip().decode(), hashlib.sha256(data).hexdigest())

    def test_cross_decode_all_bytes_boundaries_random_and_native_c90_ubsan(self):
        rng = random.Random(20261030)
        cases = [b"", b"\0", bytes(range(256)), b"a" * 4096, b"b" * 4097,
                 bytes(range(256)) * 4096, rng.randbytes(700003)]
        for raw in cases:
            source, wire, restored = (self.path / p for p in ("input", "wire", "restored"))
            source.write_bytes(raw)
            for profile in ("raw", "balanced"):
                with self.subTest(size=len(raw), profile=profile):
                    p = self.run_native("encode", profile, source, wire, 4096)
                    self.assertEqual(p.returncode, 0, p.stderr)
                    self.assertEqual(reference.decode(wire.read_bytes()), raw)
                    if profile == "raw":
                        self.assertEqual(wire.read_bytes(), reference.encode(raw, profile=profile, block_bytes=4096))
                    wire.write_bytes(reference.encode(raw, profile=profile, block_bytes=4096))
                    p = self.run_native("decode", wire, restored, sanitized=True)
                    self.assertEqual(p.returncode, 0, p.stderr)
                    self.assertEqual(restored.read_bytes(), raw)

    def assert_rejected(self, wire, limit=None):
        source, target = self.path / "bad-wire", self.path / "destination"
        source.write_bytes(wire)
        target.write_bytes(b"retained original destination")
        args = ["decode", source, target] + ([] if limit is None else [str(limit)])
        result = self.run_native(*args, sanitized=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(target.read_bytes(), b"retained original destination")
        self.assertFalse(list(self.path.glob("*.qikvrt-*")))

    def test_corruption_truncation_foreign_seed_budgets_and_footer_counters(self):
        wire = reference.encode(b"x" * 9000, block_bytes=4096)
        variants = [wire[:n] for n in (0, 1, 415, 416, 417, len(wire) - 1)]
        variants += [wire + b"trailing", wire + wire]
        for offset in (0, 8, 9, 10, 12, 16, 415, 416, 420, 430, len(wire) - 1, len(wire) - 48):
            bad = bytearray(wire)
            bad[offset] ^= 255
            variants.append(bytes(bad))
        for bad in variants:
            with self.subTest(size=len(bad), sha=hashlib.sha256(bad).hexdigest()):
                self.assert_rejected(bad)
        self.assert_rejected(wire, limit=8999)
        empty = reference.encode(b"")
        self.assertEqual(self.run_native("--version").returncode, 0)
        source, output = self.path / "empty-wire", self.path / "empty-output"
        source.write_bytes(empty)
        self.assertEqual(self.run_native("decode", source, output, 0).returncode, 0)
        self.assertEqual(output.read_bytes(), b"")

    def test_rehashed_trailing_concatenated_incomplete_and_excess_zlib_output(self):
        original = reference.encode(b"a" * 4096, block_bytes=4096)
        header, frame = original[:416], original[416:457]
        size = struct.unpack(">I", frame[5:9])[0]
        compressed = original[457:457 + size]
        for payload in (compressed + b"trailing", compressed + compressed,
                        compressed[:-1], zlib.compress(b"a" * 4097)):
            new_frame = frame[:5] + struct.pack(">I", len(payload)) + frame[9:]
            wire = header + new_frame + payload + struct.pack(">BQQ", 255, 4096, 1)
            self.assert_rejected(wire + hashlib.sha256(wire).digest())

    def test_noncanonical_lengths_block_order_and_numeric_arguments(self):
        header = reference.encode(b"")[:416]
        for raw_size, stored_size, method in ((0, 0, 0), (4097, 1, 1), (1, 2, 1),
                                              (1, 1, 1), (2**32 - 1, 1, 1)):
            frame = struct.pack(">BII32s", method, raw_size, stored_size, b"\0" * 32)
            self.assert_rejected(header + frame + b"x")
        source, out = self.path / "source", self.path / "target"
        source.write_bytes(b"x")
        out.write_bytes(b"retained")
        for value in ("-1", "18446744073709551616000", "1x", "2147483648"):
            self.assertEqual(self.run_native("decode", source, out, value).returncode, 2)
            self.assertEqual(out.read_bytes(), b"retained")
        self.assertEqual(self.run_native("encode", "balanced", source, out, 4095).returncode, 2)

    def test_special_or_link_destinations_and_failed_hash_output_are_rejected(self):
        source, sentinel = self.path / "wire", self.path / "sentinel"
        source.write_bytes(reference.encode(b"accepted bytes"))
        sentinel.write_bytes(b"retained")
        link, fifo = self.path / "link", self.path / "fifo"
        link.symlink_to(sentinel)
        os.mkfifo(fifo)
        for destination in (link, fifo, self.path):
            p = self.run_native("decode", source, destination, sanitized=True)
            self.assertEqual(p.returncode, 2, p.stderr)
        self.assertTrue(link.is_symlink())
        self.assertEqual(sentinel.read_bytes(), b"retained")
        with open("/dev/full", "wb", buffering=0) as failed_output:
            p = subprocess.run([str(self.binary), "sha256", str(source)],
                               stdout=failed_output, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(p.returncode, 2)

    def fixture_repository(self):
        root = self.path / "git-source"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "data.bin").write_bytes(bytes(range(256)) * 300)
        (root / "program.py").write_text("print('must not execute during packaging')\n")
        (root / "executable").write_bytes(b"#!/bin/sh\nexit 0\n")
        (root / "executable").chmod(0o755)
        (root / "link").symlink_to("data.bin")
        (root / "\u00c4hnlich.txt").write_text("UTF-8\n")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.name=Archive Test",
                        "-c", "user.email=archive@example.invalid", "-c", "commit.gpgsign=false",
                        "commit", "-qm", "frozen archive fixture"], check=True)
        return root

    def test_complete_git_inventory_zip_and_real_native_self_extraction(self):
        root = self.fixture_repository()
        original = self.path / "source.zip"
        manifest = archive.snapshot_zip(root, "HEAD", original)
        self.assertEqual(archive.verify_snapshot(original, manifest), 5)
        second = self.path / "second.zip"
        self.assertEqual(archive.snapshot_zip(root, "HEAD", second), manifest)
        self.assertEqual(original.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(original) as z:
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in z.infolist()))
        sfx, restored = self.path / "archive.run", self.path / "restored.zip"
        archive.self_extractor(self.binary, original, sfx)
        second_sfx = self.path / "second.run"
        os.utime(original, (1900000000, 1900000000))
        archive.self_extractor(self.binary, original, second_sfx)
        self.assertEqual(sfx.read_bytes(), second_sfx.read_bytes())
        for path in (original, sfx):
            result = subprocess.run(["unzip", "-t", str(path)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([str(sfx), "extract", str(restored)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(restored.read_bytes(), original.read_bytes())
        self.assertEqual(archive.verify_snapshot(restored, manifest), 5)
        # The executable remains the same native codec runtime with its ZIP appended.
        self.assertEqual(subprocess.run([str(sfx), "--version"], capture_output=True).returncode, 0)

    def test_sfx_modified_payload_or_locator_cannot_clobber_destination(self):
        root = self.fixture_repository()
        original, sfx, restored = (self.path / n for n in ("source.zip", "archive.run", "restored.zip"))
        archive.snapshot_zip(root, "HEAD", original)
        info = archive.self_extractor(self.binary, original, sfx)
        baseline = sfx.read_bytes()
        for offset in (info["payload_offset"] + 100, len(baseline) - 1, len(baseline) - 48):
            bad = bytearray(baseline)
            bad[offset] ^= 255
            sfx.write_bytes(bad)
            restored.write_bytes(b"retained")
            result = subprocess.run([str(sfx), "extract", str(restored)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(restored.read_bytes(), b"retained")
        self.assertFalse(list(self.path.glob("*.qikvrt-*")))

    @staticmethod
    def machine_program(table):
        return (b"QIKTM01\0" + struct.pack(">H", len(table))
                + b"".join(struct.pack(">HBB", *t) for row in table for t in row))

    @staticmethod
    def reference_machine(table, bits, max_steps, max_cells):
        # Independent sparse integer-indexed tape; native uses linked cells.
        tape = dict(enumerate(map(int, bits))) or {0: 0}
        state, head, steps = 0, 0, 0
        while state != 65535:
            if steps >= max_steps:
                return None
            state, tape[head], move = table[state][tape[head]]
            head += move - 1
            if head not in tape:
                if len(tape) >= max_cells:
                    return None
                tape[head] = 0
            steps += 1
        return {"schema": "qikvrt-binary-machine-result/v1", "state": state, "head": head,
                "steps": steps, "cells": len(tape),
                "tape": "".join(str(tape[n]) for n in range(min(tape), max(tape) + 1))}

    def test_binary_machine_reference_differential_and_resource_negative_cases(self):
        rng = random.Random(41030)
        tables = [[[(65535, 1, 1), (0, 1, 2)]],
                  [[(1, 1, 0), (1, 1, 0)], [(65535, 1, 1), (65535, 1, 1)]],
                  [[(0, 0, 2), (0, 1, 2)]]]
        for _ in range(100):
            states = rng.randrange(1, 8)
            tables.append([[(rng.choice([*range(states), 65535]), rng.randrange(2), rng.randrange(3))
                            for _ in range(2)] for _ in range(states)])
        program = self.path / "machine.tm"
        for table in tables:
            bits = "".join(rng.choice("01") for _ in range(rng.randrange(1, 20)))
            program.write_bytes(self.machine_program(table))
            expected = self.reference_machine(table, bits, 100, 40)
            p = self.run_native("machine", program, bits, 100, 40, sanitized=True)
            if expected is None:
                self.assertEqual(p.returncode, 2, p.stderr)
                self.assertEqual(p.stdout, b"")
            else:
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(p.stdout), expected)

    def test_binary_machine_rejects_bad_program_and_does_not_execute_host_code(self):
        program = self.path / "machine.tm"
        valid = archive.binary_increment_program()
        for data in (b"", valid[:-1], valid + b"extra", b"#!/bin/sh\necho unsafe\n",
                     self.machine_program([[ (65535, 2, 1), (0, 1, 2) ]]),
                     self.machine_program([[ (4, 0, 1), (0, 1, 2) ]])):
            program.write_bytes(data)
            p = self.run_native("machine", program, "1110", 100, 100, sanitized=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(p.stdout, b"")
        program.write_bytes(valid)
        for bits, steps, cells in (("2", 100, 100), ("1110", 0, 100),
                                  ("1110", 100, 1), ("0", 10000001, 100)):
            p = self.run_native("machine", program, bits, steps, cells, sanitized=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(p.stdout, b"")

    def test_native_result_original_authenticated_terminal_readback_and_replay(self):
        program = self.path / "machine.tm"
        program.write_bytes(archive.binary_increment_program())
        p = self.run_native("machine", program, "1110", 100, 100, sanitized=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result["tape"], "1111")
        observed = archive.terminal_readback(archive.file_digest(program), result)
        self.assertEqual(observed["replay_status"], 409)
        self.assertFalse(observed["productive_native_mesh_admission"])


if __name__ == "__main__":
    unittest.main()
