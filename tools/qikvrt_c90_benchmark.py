#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Reproduce a scalar CPU comparison of the same checked Q16.16 operations."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.qikvrt_fixed_q16 import add, mul

CFLAGS = ("-O2", "-std=c90", "-pedantic-errors", "-Wall", "-Wextra", "-Werror")
SOURCES = ("src/fixed_q16.c", "include/qikvrt/fixed_q16.h",
           "src/qikvrt_fixed_q16.py", "tools/qikvrt_c90_benchmark.c",
           "tools/qikvrt_c90_benchmark.py")


def compiler_command() -> list[str]:
    command = shlex.split(os.environ.get("CC", "cc"))
    if not command:
        raise ValueError("CC must name a compiler")
    return command


def build_native(path: Path) -> list[str]:
    command = [*compiler_command(), *CFLAGS, "-I", str(ROOT / "include"),
               str(ROOT / "src/fixed_q16.c"),
               str(ROOT / "tools/qikvrt_c90_benchmark.c"), "-o", str(path)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return command


def python_workload(count: int) -> tuple[int, int]:
    checksum = 0
    start = time.process_time_ns()
    for i in range(count):
        a = i & 65535
        b = (i * 251 + 17) & 65535
        c = ((i * 17) & 65535) - 32768
        checksum = (checksum + add(mul(a, b), c)) & 4294967295
    return checksum, time.process_time_ns() - start


def benchmark(iterations: int, repeats: int) -> dict:
    if not 1 <= iterations <= 100_000_000 or not 1 <= repeats <= 31:
        raise ValueError("iterations 1..100000000; repeats 1..31")
    python_seconds, c_seconds, checksums = [], [], []
    with tempfile.TemporaryDirectory(prefix="qikvrt-c90-") as folder:
        binary = Path(folder) / ("q16.exe" if os.name == "nt" else "q16")
        command = build_native(binary)
        binary_sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
        version = subprocess.run([*compiler_command(), "--version"],
                                 check=True, capture_output=True, text=True).stdout.splitlines()[0]
        # Alternate order; compile, process startup and reporting are not timed.
        for run in range(repeats):
            def native():
                value = json.loads(subprocess.run(
                    [str(binary), str(iterations)], check=True,
                    capture_output=True, text=True).stdout)
                if (value["iterations"] != iterations or value["clock_ticks"] <= 0
                        or value["clocks_per_second"] <= 0):
                    raise ValueError("native timer/input mismatch")
                c_seconds.append(value["clock_ticks"] / value["clocks_per_second"])
                return value["checksum"]
            if run % 2:
                c_sum = native()
                p_sum, elapsed = python_workload(iterations)
            else:
                p_sum, elapsed = python_workload(iterations)
                c_sum = native()
            if p_sum != c_sum:
                raise ValueError("Python/C90 workload results differ")
            checksums.append(p_sum)
            python_seconds.append(elapsed / 1_000_000_000)
    py_median, c_median = statistics.median(python_seconds), statistics.median(c_seconds)
    return {
        "schema": "qikvrt-c90-q16-cpu-benchmark/v1",
        "scope": "SCALAR_CPU_CHECKED_Q16_MULTIPLY_THEN_ADD",
        "iterations": iterations, "repeats": repeats, "checksums": checksums,
        "python_cpu_seconds": python_seconds, "c90_cpu_seconds": c_seconds,
        "python_median_seconds": py_median, "c90_median_seconds": c_median,
        "python_over_c90_ratio": py_median / c_median,
        "compiler": version, "compiler_command": compiler_command(),
        "flags": list(CFLAGS), "binary_sha256": binary_sha256,
        "python": sys.version,
        "platform": platform.platform(), "machine": platform.machine(),
        "timing": "process CPU time inside each workload; excludes compile/startup/I-O",
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "not_measured": ["energy", "Nvidia GPU", "codec throughput", "whole runtime",
                         "Meta-Transistor hardware", "physical causality"],
        "effect_ack_done": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1_000_000)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = benchmark(args.iterations, args.repeats)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"C90_BENCHMARK_FAILED: {exc}\n")
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
