<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Comparable Linux ring measurements

The separate comparable engine extends the existing native witness driver.
Its historical hosted CLI budget is now closed. The executable successor is
`--isolated-scale-benchmark`, specified in
[the isolated-control carrier](QIKVRT_LINUX_ISOLATED_SCALE_CONTROL_V1.md).
It does not change `lossless_scale_consolidation_controls`,
the Firefox witness, the restart witness, or the socket-loss witness. Those
correctness experiments retain their own acceptance and cannot prove speedup.

An externally admitted dedicated runner executes this exact command:

```sh
python3 -B tools/qikvrt_firefox_windows_witness.py \
  --isolated-scale-benchmark --expected-head <exact-head> \
  --expected-tree <exact-tree> --isolation-attestation-sha256 <external-sha256> \
  --output <new-directory-on-the-dedicated-volume>
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
The historical hosted observations did not isolate ambient cache or host load.
The successor requires an external isolation attestation and exact local
policy/telemetry admission; code tests do not establish actual isolation.
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
The hosted Linux job now validates the contract only. The dedicated job is
dispatch-only, checks out its own reviewed exact ref and requires the declared
offline CPython. It uploads only receipts. `private-rings/` contains private
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

## Bounded variance diagnosis

Native run `37009544042`, job `110845708035`, artifact `11226239403` is historical
evidence for HEAD `e998f89cfcee647773acd2d91a7cf0d3a4f00a74`, TREE
`81c0931f2a98b057d6d422655c9871fc50a24395`. Its six paired repetitions fail both
speedup admission tests. Execution and persistence-union outliers coincide;
this supports an I/O-stall hypothesis but does not identify their cause.
The successor does not transfer those gates, observations or Owner acceptance.

The existing benchmark worker now observes the following for every trial:

| Observation | Binding and limitation |
| --- | --- |
| Entire persist | Monotonic interval, calling-thread CPU, native thread ID, context switches, faults and block-I/O counts. Elapsed minus CPU includes all waiting and clock-boundary error; it is not exclusive I/O-wait time. Signed residuals are retained. |
| Original atomic writer | Inclusive operation interval and serialized byte count. Payload, snapshots, tokens and keys are never exported. |
| File fsync, replace, directory fsync | Separate intervals and thread CPU around the original syscalls, including error outcomes. Failure still poisons the original State. |
| Persist/atomic residuals | Persist outside atomic includes serialization, seed/hash work and instrumentation. Atomic other includes creation, write, flush, opens, cleanup and instrumentation. It is not a pure write-latency estimate. |
| Storage | Actual snapshot device, filesystem/mount/options, visible block-device sysfs/slaves and available capacity. Overlay/virtual backing devices remain explicitly unresolved. Visible device identity does not attest physical isolation. |
| Process/CPU | Actual server/driver PIDs and affinity, per-process I/O counters, main-thread context switches; per-persist resource counters cover the actual calling threads. |
| cgroup/quotas | Resolve `/proc/PID/cgroup` against actual mount roots; observe visible leaf and ancestor CPU quota/stat, effective cpuset, I/O limits/stat and PSI. Shared ancestors are read once; never add parent and child counters. v1 configuration is preserved with its native units. Outside-namespace/hidden ancestors remain unobserved. |
| Host I/O/load | Before/after CPU jiffies including steal/iowait, diskstats, PSI totals for CPU/I/O/memory, vmstat, meminfo and load average. Host and shared-cgroup counters include other tasks. |

`worker_metrics_after.persist_intervals` preserves every raw storage interval.
Each successful persist must contain exactly one atomic write, file fsync,
replace and directory fsync. Outer atomic/persist intervals overlap their nested
operations; **do not sum them as independent costs**. Each operation reports its
wall distribution, sum and union; per-process summaries retain per-trial maxima.

`telemetry_targets`, `observability_before` and `observability_after` are in each
hashed trial receipt. Sequential before/after reads bracket the measured
execution, with their own monotonic boundaries and observer process CPU; they
are not simultaneous snapshots. They are outside the execution timer. The
operation hooks run inside execution and their overhead has not been separately
calibrated. All comparisons use the same observation mode. No host poller,
tracer, privileged collector, cache reset, quota write, filesystem substitution
or durability change is added.

Missing, inaccessible or malformed telemetry is `UNAVAILABLE` with source and
error identity. Counter decreases/resets retain before/after values and a null
delta. Missing fields never become zero throttling or zero I/O wait. PSI average
windows and queue-in-flight gauges are retained in the snapshots but are not
subtracted as cumulative counters. Diskstats and cgroup accounting do not
establish exclusive physical device ownership or causal attribution.

Correctness can be `PASS` while `variance_observability.state` and every trial's
`variance_diagnosis.state` are `HOLD_CAUSAL_ISOLATION_UNVERIFIED`.
`causal_runner_io_stall_proved=false` and
`runner_independent_scaling_proved=false` remain explicit. The existing
`benchmark_speedup` function and its six-pair/all-pairs-faster/interval-above-one
rule are unchanged; its outcome is scoped to this host and observation mode.
No claim is inferred from lower medians or a successful diagnostic job.

The historical native job completed its bounded six-repetition diagnostic.
No additional unmodified hosted diagnostic is prescribed or triggered. There
is no automatic retry, added warmup, outlier removal or sample-budget extension.
On an admission gap, the receipt materializes
`next_measurement_contract` with
`maximum_additional_unmodified_hosted_trials=0`.

The next contract requires a separately verified dedicated host and durable
block volume; fixed CPU/affinity and fully visible effective quotas; disclosed
filesystem, device/queue, governor and cache policy; exact source/interpreter,
seed, origin/workload and receipt digests; and collector overhead. It prescribes
one predeclared matched isolated comparison and one with a calibrated, bounded
I/O interferer on the same volume, while preserving the original workload,
clients, snapshot bytes, durability, effects/records and replay controls. The
interferer is not executed by this hosted diagnostic. Each condition has six
cyclic interleaved repetitions and retains every sample. Missing admission
evidence stops repetitions and preserves HOLD; it is not filled from runner
labels or declarations. The full machine contract is generated by
`benchmark_next_measurement_contract()` and persisted in the work unit. Its
executable materialization is `policy/QIKVRT_LINUX_SCALE_ISOLATION_V1.json`;
the prepared carrier is not evidence that the isolated experiment ran.

Counter semantics follow the primary Linux documentation:
[cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html),
[PSI](https://docs.kernel.org/accounting/psi.html),
[proc I/O accounting](https://docs.kernel.org/filesystems/proc.html), and
[diskstats](https://docs.kernel.org/admin-guide/iostats.html).
