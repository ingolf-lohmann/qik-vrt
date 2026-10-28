# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Cross-language arithmetic checks against Python's unbounded integer oracle."""
import itertools
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.qikvrt_fixed_q16 import MIN_RAW, MAX_RAW, SCALE, add, mul
from tools.qikvrt_c90_benchmark import CFLAGS, build_native, compiler_command


class FixedQ16Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix="qikvrt-q16-test-")
        cls.addClassCleanup(cls.folder.cleanup)
        cls.binary = Path(cls.folder.name) / ("vectors.exe" if os.name == "nt" else "vectors")
        build_native(cls.binary)

    def test_c90_boundaries_and_null_output(self):
        binary = Path(self.folder.name) / ("bounds.exe" if os.name == "nt" else "bounds")
        subprocess.run([*compiler_command(), *CFLAGS, "-I", str(ROOT / "include"),
                        str(ROOT / "src/fixed_q16.c"), str(ROOT / "tests/test_fixed_q16.c"),
                        "-o", str(binary)], check=True, capture_output=True, text=True)
        subprocess.run([str(binary)], check=True)

    def test_cross_language_edges_and_random_values(self):
        edges = [MIN_RAW, MIN_RAW + 1, -SCALE - 1, -SCALE, -32768, -1,
                 0, 1, 32768, SCALE, SCALE + 1, MAX_RAW - 1, MAX_RAW]
        pairs = list(itertools.product(edges, repeat=2))
        rng = random.Random(20261028)
        pairs += [(rng.randint(-(1 << 23), 1 << 23),
                   rng.randint(-(1 << 23), 1 << 23)) for _ in range(4096)]
        pairs += [(rng.randint(MIN_RAW, MAX_RAW),
                   rng.randint(MIN_RAW, MAX_RAW)) for _ in range(1024)]
        vectors = [(op, a, b) for a, b in pairs for op in "AM"]
        proc = subprocess.run([str(self.binary), "--vectors"],
                              input="".join(f"{op} {a} {b}\n" for op, a, b in vectors),
                              capture_output=True, text=True, check=True)
        rows = proc.stdout.splitlines()
        self.assertEqual(len(rows), len(vectors))
        for (op, a, b), row in zip(vectors, rows):
            status, actual = map(int, row.split())
            try:
                expected = (add if op == "A" else mul)(a, b)
            except OverflowError:
                self.assertEqual((status, actual), (2, 12345), (op, a, b))
            else:
                self.assertEqual((status, actual), (0, expected), (op, a, b))

    def test_truncation_and_range_contract(self):
        self.assertEqual(mul(-1, 1), 0)
        self.assertEqual(mul(98304, -32768), -49152)
        for operation in (add, mul):
            for invalid in (True, 1.0, "1", None):
                with self.assertRaises(TypeError):
                    operation(invalid, 0)
            with self.assertRaises(OverflowError):
                operation(MAX_RAW + 1, 0)
        with self.assertRaises(OverflowError):
            mul(MIN_RAW, -SCALE)

    def test_driver_rejects_invalid_input(self):
        for raw in ("M 1 2 extra\n", "X 1 2\n", "M 1\n", "M 1 2",
                    "M 99999999999999999999999999999999999999 1\n"):
            proc = subprocess.run([str(self.binary), "--vectors"], input=raw,
                                  capture_output=True, text=True)
            self.assertNotEqual(proc.returncode, 0, raw)


if __name__ == "__main__":
    unittest.main()
