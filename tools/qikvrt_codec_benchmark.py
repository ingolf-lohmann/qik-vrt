#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Comparable local codec trials; timings are evidence, never universal bounds."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import statistics
import subprocess
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import qikvrt_codec as codec


def benchmark(*, size=1024 * 1024, repeats=7):
    if size < 65536 or repeats < 3:
        raise ValueError("size >= 65536 and repeats >= 3 required")
    # Reuse the exact canonical review-candidate seed from PR #424.
    seed = codec.QIKVRT_SIGNATURE
    rng = random.Random(4102026)
    random_data = rng.randbytes(size)
    text = (ROOT / "README.md").read_bytes()
    text = (text * (size // len(text) + 1))[:size]
    mixed = (random_data[:32768] + b"\0" * 32768) * (size // 65536 + 1)
    # Deliberately expose the sampling heuristic's space tradeoff.
    trap = bytearray(b"\0" * size)
    for base in range(0, size, codec.DEFAULT_BLOCK_BYTES):
        length = min(codec.DEFAULT_BLOCK_BYTES, size - base)
        for offset in (0, length // 3, 2 * length // 3, max(0, length - 2048)):
            trap[base + offset:base + min(offset + 2048, length)] = rng.randbytes(min(2048, length - offset))
    workloads = {"repetitive": b"QIKVRT\0\xff" * (size // 8), "repository_text": text,
                 "random": random_data, "mixed": mixed[:size],
                 "precompressed": zlib.compress(random_data), "sampling_adversary": bytes(trap)}
    element_count = min(128, size // 8192)
    mesh_elements = [codec.Element((i + 1).to_bytes(32, "big"), text[:8192])
                     for i in range(element_count)]
    workloads["canonical_mesh_snapshot"] = codec.serialize(mesh_elements)
    variants = [("baseline_fast_full_trial", "fast", False),
                ("optimized_fast", "fast", True), ("balanced", "balanced", True),
                ("compact", "compact", True), ("raw", "raw", True)]
    rows = []
    for name, raw in workloads.items():
        cases = {}
        for label, profile, probe in variants:
            encoded = codec.encode(raw, signature=seed, profile=profile, probe=probe)
            if codec.decode(encoded, signature=seed) != raw:
                raise AssertionError("ROUNDTRIP_FAILED")
            cases[label] = (profile, probe, encoded, [], [])
        # Interleave and deterministically vary order to reduce order/warmup bias.
        order_rng = random.Random(19)
        for _ in range(repeats):
            order = list(cases)
            order_rng.shuffle(order)
            for label in order:
                profile, probe, expected, encode_times, decode_times = cases[label]
                start = time.perf_counter_ns()
                encoded = codec.encode(raw, signature=seed, profile=profile, probe=probe)
                encode_times.append(time.perf_counter_ns() - start)
                if encoded != expected:
                    raise AssertionError("NONDETERMINISTIC_ENCODING")
                start = time.perf_counter_ns()
                decoded = codec.decode(encoded, signature=seed)
                decode_times.append(time.perf_counter_ns() - start)
                if decoded != raw:
                    raise AssertionError("ROUNDTRIP_FAILED")
                if name == "canonical_mesh_snapshot" and codec.serialize(codec.deserialize(decoded)) != raw:
                    raise AssertionError("CANONICAL_SNAPSHOT_ROUNDTRIP_FAILED")
        for label, (profile, probe, encoded, encode_times, decode_times) in cases.items():
            enc, dec = statistics.median(encode_times), statistics.median(decode_times)
            rows.append({"workload": name, "variant": label, "input_bytes": len(raw),
                         "input_sha256": hashlib.sha256(raw).hexdigest(), "wire_bytes": len(encoded),
                         "wire_sha256": hashlib.sha256(encoded).hexdigest(),
                         "ratio": len(encoded) / len(raw), "profile": profile, "probe": probe,
                         "encode_ns": encode_times, "decode_ns": decode_times,
                         "encode_median_ns": enc, "decode_median_ns": dec,
                         "encode_mib_s": len(raw) / (1024**2) / (enc / 1e9),
                         "decode_mib_s": len(raw) / (1024**2) / (dec / 1e9),
                         "roundtrip_verified_each_trial": True})
            rows[-1]["canonical_snapshot_roundtrip_verified_each_trial"] = name == "canonical_mesh_snapshot"
    source = (ROOT / "src/qikvrt_codec.py").read_bytes()
    return {"schema": "qikvrt_codec_benchmark_v1", "observed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "repository": "ingolf-lohmann/qik-vrt",
            "base_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "candidate_source_sha256": hashlib.sha256(source).hexdigest(),
            "candidate_dependencies_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                for path in ("src/qikvrt_standpoint_codex.py", "src/qikvrt_effect_ack.py",
                             "canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin")},
            "benchmark_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "environment": {"python": platform.python_version(), "platform": platform.platform(),
                            "machine": platform.machine(), "zlib_build": zlib.ZLIB_VERSION,
                            "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION},
            "seed": {"status": "CANONICAL_V1_REVIEW_CANDIDATE_REUSED_FROM_PR424", "bytes": 400,
                     "sha256": hashlib.sha256(seed).hexdigest()},
            "conditions": {"size": size, "repeats": repeats, "block_bytes": codec.DEFAULT_BLOCK_BYTES,
                           "order": "INTERLEAVED_DETERMINISTIC_SHUFFLE", "timing": "perf_counter_ns_wall",
                           "warmup": "ONE_PER_VARIANT", "historical_executable_codec_baseline_exists": False},
            "rows": rows,
            "limits": ["Shared host wall-clock observations; no energy measurement",
                       "Baseline is the declared full-trial framed reference, not a historical QIKVRT implementation",
                       "Sampling can miss compressibility; sampling_adversary deliberately demonstrates this",
                       "Not a proof of fastest or smallest encoding, all hardware, or future performance"],
            "effect_ack_done": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=1024 * 1024)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = benchmark(size=args.size, repeats=args.repeats)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
