#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Bounded local reader comparison, separate from PR443's isolated protocol.

This measures Python allocations and warm file hashing only. It establishes
neither dedicated-host throughput, distributed scaling nor domain delivery.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_integrity as candidate

BASELINE_BLOB = "15b5eb5089b0753ee52ee6bf3a27020b449ca2cd"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.baseline_source.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != BASELINE_BLOB:
        parser.error("baseline must be the exact preserved PR514 generator blob")
    if args.output.exists():
        parser.error("create-only output; preserve previous observations")
    spec = importlib.util.spec_from_file_location("integrity_baseline", args.baseline_source)
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    rows = []
    with tempfile.TemporaryDirectory(prefix="qikvrt-reader-fixture-") as directory:
        root = Path(directory)
        block = bytes(range(256)) * 4096
        expected = hashlib.sha256()
        with (root / "payload").open("wb") as stream:
            for _ in range(64):
                stream.write(block)
                expected.update(block)
            stream.flush()
            os.fsync(stream.fileno())
        expected_digest = expected.hexdigest()
        for repeat in range(6):
            order = ("baseline", "streaming") if repeat % 2 == 0 else ("streaming", "baseline")
            for arm in order:
                tracemalloc.start()
                start = time.perf_counter_ns()
                if arm == "baseline":
                    data = baseline._regular_file_bytes(root, "payload")
                    size, digest = len(data), hashlib.sha256(data).hexdigest()
                    del data
                else:
                    size, digest = candidate._regular_file_digest(root, "payload")
                elapsed = time.perf_counter_ns() - start
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                if (size, digest) != (64 * 1024 * 1024, expected_digest):
                    raise RuntimeError("READER_BYTE_OR_DIGEST_MISMATCH")
                rows.append(dict(repeat=repeat, arm=arm, elapsed_ns=elapsed,
                                 peak_python_allocation_bytes=peak, bytes=size, sha256=digest))
    summaries = {}
    for arm in ("baseline", "streaming"):
        selected = [row for row in rows if row["arm"] == arm]
        summaries[arm] = dict(median_elapsed_ns=statistics.median(row["elapsed_ns"] for row in selected),
                             maximum_peak_python_allocation_bytes=max(row["peak_python_allocation_bytes"] for row in selected))
    result = dict(schema="qikvrt_integrity_reader_local_comparison_v1",
                  artifact_class="OPERATIONAL_DIAGNOSTIC_NOT_SCIENTIFIC_PUBLICATION",
                  observed_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  baseline_git_blob=blob, baseline_sha256=hashlib.sha256(raw).hexdigest(),
                  candidate_source_sha256=hashlib.sha256(Path(candidate.__file__).read_bytes()).hexdigest(),
                  python=platform.python_version(), platform=platform.platform(),
                  fixture_bytes=64 * 1024 * 1024, repetitions_per_arm=6,
                  order="alternating matched pairs", cache_policy="warm sequential file reads; no cache drops",
                  measure="tracemalloc Python allocation peak; wall time includes tracing overhead",
                  all_sizes_and_sha256_equal=True, trials=rows, summary=summaries,
                  limitations=["Selected source closure, not a full repository benchmark",
                               "Python allocations, not RSS or physical storage latency",
                               "Local host; no isolation or portable throughput claim",
                               "Separate from the fixed PR443 36-trial protocol; no PR443 budget consumed"],
                  effect_ack_done=False, domain_delivery=False)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
