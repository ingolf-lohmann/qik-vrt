<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Comparable Linux ring measurements

The separate `--comparable-scale-benchmark` mode extends the existing native
witness driver. It does not change `lossless_scale_consolidation_controls`,
the Firefox witness, the restart witness, or the socket-loss witness. Those
correctness experiments retain their own acceptance and cannot prove speedup.

Run `make linux-ring-benchmark QIKVRT_LINUX_BENCHMARK_OUTPUT=<new-private-directory>`.
The equivalent explicit invocation is:

```sh
python3 -B tools/qikvrt_firefox_windows_witness.py \
  --comparable-scale-benchmark --repetitions 6 --workload 64 \
  --preload-per-origin 4 --output <new-private-directory>
```

The benchmark populates four distinct origins through actual prepare/commit
HTTP requests, then closes all template processes. Each origin starts with four
effects and eight referenced records. Every measured run copies exactly these
closed private snapshots into new roots. Token keys differ between origins;
each origin's initial bytes are identical across all process counts and repeats.
Cloning is confined to isolated benchmark stores with no external effects.

The same four origins are assigned to one process with four stores, two
processes with two stores each, or four processes with one store each. All
placements use the existing RingHandler, State, durable writer and CLI. Four
barrier-synchronized HTTP clients each serve one fixed origin and perform an
equal share of the same ordered canonical payload bytes. Fresh token randomness
and timestamps remain native protocol behavior. They are not fixed or mocked.

The timed interval includes client barrier release, prepare/commit HTTP work,
confirmed response parsing and completion collection. Startup, initial-state
copying, preload, verification, consolidation and replay controls are excluded.
Wall time uses `perf_counter_ns`; each actual server's process CPU time uses
`clock_getcpuclockid(PID)` and `clock_gettime_ns`; driver CPU uses
`process_time_ns` and includes its client threads. CPU deltas include the tiny
accounting boundaries around the measured interval. No CPU metric silently
substitutes wall time. An unavailable server CPU clock fails the experiment.

The successor measures every excluded phase as well: template setup/preload,
per-trial snapshot copy, actual launch/restore, admission readback, full effect
verification, drained process termination and single-process consolidation,
and replay controls. `phase_timing_seconds` keeps these costs separate from the
inclusive effect-execution wall. Each benchmark worker calls the unchanged
`State.persist` through a process-local timing hook; the ordinary terminal CLI
and Firefox/correctness paths keep their original runtime behavior.

Every fsynced persist supplies monotonic start/end timestamps and calling-thread
CPU. The receipt exports all intervals and requires exactly two writes per new
effect. Their wall **union** counts overlapping writes once; their wall sum is
also reported. The execution residual measures elapsed intervals with no persist
active. It is not a counterfactual run without persistence and must not be used
to claim such a speedup. The hooks add small observed-mode overhead.
Reaped git child CPU is reported separately and added to server CPU in
`server_process_tree_cpu_seconds`; observer/client CPU remains separate.

Six repetitions use balanced cyclic orders 1/2/4, 2/4/1 and 4/1/2 twice.
Every repetition is retained. There is no outlier removal or discarded warmup.
The result reports each wall time, server and driver CPU time, confirmed-effect
throughput, every transaction latency, sample standard deviation, coefficient
of variation, range and empirical linearly interpolated percentiles. Pooled
latencies describe requests; pairing units are complete repetitions.
Independence between repetitions on the same host is not established.
Host, interpreter, CPU affinity, quota and available CPU model are disclosed.
Ambient cache and host load are not isolated.
Host/machine identity and interpreter binary SHA-256 are included. The benchmark
receipt also observes the installed Firefox version and binary digest when
available. A missing browser is explicitly `UNOBSERVED`. Installed identity does
not prove browser execution or Firefox transport performance; those remain in
the separate fresh native Firefox witness.

After **every** run, fresh HTTP reads verify all event identities, prepared and
executed record hashes, exact input and seed bindings, retained records, and
effect/record cardinality. With defaults the final totals are 80 effects and
160 referenced records. All workers then stop. Their unchanged origin stores
are moved into one process and read back again. All 80 consumed tokens and
four concurrent retries must return HTTP 409 without any new effect or changed
record, event or private snapshot byte. Aggregate readback must be lossless.
Existing output roots are refused without resetting or overwriting state.

Each run has a public readback receipt under `measurements/`; `RECEIPT.json`
binds its bytes and SHA-256, exact HEAD/TREE, source digests and CI producer.
The separate Linux job checks out the exact PR head and uses the existing
declared CPython. It uploads only receipts. `private-rings/` contains private
keys and tokens and must never be uploaded. A local API source fixture lacking
a complete Git checkout is only source-byte evidence; null HEAD/TREE must not
be filled from predecessor CI or claimed as exact-head execution.

A bounded speedup claim needs at least six paired repetitions, a faster
candidate in every pair, and a lower bootstrap percentile interval bound above
one. Two comparisons to one process use approximate Bonferroni-adjusted 97.5%
intervals, 5,000 resamples and a fixed disclosed bootstrap seed. This is a
small-sample observation on this host and workload, not a theorem, independent
replication or a portable performance guarantee. Contradictory or inconclusive
measurements leave `speedup_supported=false`.

`unbounded_scalability_proved=false`, `predecessor_evidence_transfer=false`,
and `personal_release_effect_ack_done=false` remain explicit. Native Main
protection and independent Code-Owner review remain separate governance gates.
