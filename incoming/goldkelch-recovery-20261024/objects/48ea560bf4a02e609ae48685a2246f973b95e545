<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# PR #443: fixed isolated I/O control

This carrier materializes the next contract of HEAD
`a1d35df440eada9bfae24df335f08da67dd5a875`, native run `37045385898`.
It is **PREPARED_NOT_EXECUTED**. No dedicated-host measurement, physical
backend attribution, co-tenant/hypervisor cause, portable scaling or release
is established by source tests or CI. Historical measurements retain their
original host/HEAD/TREE binding and are not transferred to this successor.

The existing `comparable_scale_benchmark` is the only workload engine. The
new `tools/qikvrt_linux_scale_isolation.py` provides admission, ordering,
telemetry checks and the bounded intervention. There is no replacement terminal
or writer. `benchmark_speedup`, the original atomic writer/syscalls, Firefox,
restart, network-loss and consolidation witnesses retain their behavior.

The machine authority is
`policy/QIKVRT_LINUX_SCALE_ISOLATION_V1.json`. External attestation structure is
`schemas/qikvrt-linux-scale-isolation-attestation-v1.schema.json`; runtime
validation is stronger than structural JSON Schema. Exact byte hashes, clean
checkout and HEAD/TREE checks govern execution. The schema is not a new runtime
dependency: the carrier uses locked Python and its standard library.

| Fixed element | Contract |
| --- | --- |
| Conditions | `isolated`, `io_interference` |
| Budget | Six repetitions per condition and each of 1/2/4 processes: 36 trials total |
| Order | Repetition, cyclic process order 1/2/4 → 2/4/1 → 4/1/2, then condition order alternating by repetition |
| Starts | One shared set of four closed templates; identical per-origin bytes across all 36 trials |
| Work | 64 requests, four clients, four preloaded effects per origin |
| Readback | 80 effects / 160 records; all input/seed/record hashes; unchanged consolidation/restart; 80 consumed-token and four concurrent replay refusals |
| Cache | Warm snapshot copy plus full admission readback; no cache drops, excluded warmup, tmpfs or durability substitution |
| CPU | Four fixed affinity slots with four distinct visible package/core identities; driver and servers share these slots; interferer pinned to the first slot |
| Quotas | Actual v2 membership and full visible ancestry; all non-root CPU limits must be `max`; cpuset/I/O limits are pinned; hidden/outside-namespace limits require external attestation |
| Storage | Attested dedicated ext4/xfs local block volume, actual mount/device/backing identity, at least 1 GiB free; queue/cache/governor policy pinned before and after every trial |
| Interpreter | Offline CPython 3.12.13 Linux x64, exact binary digest; no hosted fallback or installation |
| Interferer | 64 KiB pwrite + original fsync, 16 MiB bounded extent, 5 ms minimum cycle; at most 3,000 operations / 15 s per trial |
| Calibration | Exactly 32 independent write+fsync primitives on the same volume before the trial schedule; recorded separately, not benchmark repetitions |
| Intervention admission | At least two complete write+fsync operations strictly inside each interference execution interval |
| Stop | First missing admission, drift, malformed/unavailable required telemetry, cumulative-counter reset, child error/budget exhaustion or invariant failure stops the schedule |

No additional unmodified hosted trials are available. The old hosted CLI fails
closed, and the existing hosted workflow job runs contract controls only.
Small-workload HTTP tests and mocked admission are explicitly source tests;
their timing is not admitted performance evidence.

## Prepare the dedicated runner

Provision a dedicated runner with labels `self-hosted`, `linux`, `x64`,
`qikvrt-isolated-scale`; four fixed usable CPU slots; declared governor and
queue/write-cache policy; and the exact offline interpreter. The carrier does
not write host CPU quotas, affinities, governors, schedulers, mount options or
cache settings. Its child sets only its own declared affinity.

Place the new run directories on the dedicated volume under
`/var/lib/qikvrt-scale/runs`. Obtain the pinned inventory from the clean exact
reviewed checkout, with zero benchmark trials:

```sh
python3 -B tools/qikvrt_firefox_windows_witness.py --isolation-inventory \
  --output /var/lib/qikvrt-scale/runs/new-inventory
```

An external verifier must establish dedicated host/volume, no co-tenants,
no other I/O producers and no hidden CPU quota. A runner label or the runner's
own declaration does not establish these facts. Put the inventory object in
`pinned_environment` of `/etc/qikvrt/scale-isolation.json`, bind separately
verified `host_isolation` and `volume_isolation` reports by relative path,
byte count and SHA-256, identify verifier/method, and set a timezone-aware
`valid_until` no more than 24 hours ahead. Set each required claim true only
when that verifier's actual evidence supports it. The carrier never fills
these decisions or manufactures a physical proof. Symlinks, path escapes,
changed input bytes and expired/mismatched inventories fail closed.

The external SHA-256 of the attestation is a separate execution input. Every
boundary rechecks it and the report bindings, exact subject, source/interpreter
digests and static environment. An unchanged preparation inventory does not
waive these fresh checks.

The existing Personal Firefox workflow exposes `run_isolated_control=false`
by default. Only an explicit `workflow_dispatch` with that input true can
reach the dedicated job. Dispatch the reviewed workflow ref and provide its
`expected_head`, `expected_tree`, and `isolation_attestation_sha256`. Checkout
uses the dispatch's own SHA, not an arbitrary input branch or a PR head.
No workflow dispatch or dedicated execution is claimed by this implementation.

The equivalent offline command is:

```sh
python3 -B tools/qikvrt_firefox_windows_witness.py --isolated-scale-benchmark \
  --expected-head <reviewed-head> --expected-tree <reviewed-tree> \
  --isolation-attestation-sha256 <externally-verified-sha256> \
  --output /var/lib/qikvrt-scale/runs/new-exact-subject-run
```

`make linux-ring-benchmark` exposes the same carrier through
`QIKVRT_EXPECTED_HEAD`, `QIKVRT_EXPECTED_TREE`, `QIKVRT_ATTESTATION_SHA256` and
`QIKVRT_LINUX_BENCHMARK_OUTPUT`. No other workload or repetition count is
accepted by the isolated CLI.

After admission, a durable create-only lease below the output parent's
`.qikvrt-scale-budgets` binds HEAD/TREE and contract digest. It is never removed
or replenished after a failure. Another output name or attestation does not
grant another budget for that subject/contract. Failed/partial runs require
a separately reviewed successor measurement contract, not an automatic rerun.
This lease coordinates carriers sharing that volume; it is not a repository-
wide or cross-host locking claim.

## Telemetry and interpretation

Every trial retains actual process affinities, membership and I/O/switch
counters, resolved shared cgroup ancestry and CPU/I/O/PSI, host diskstats,
CPU jiffies including steal/iowait, PSI CPU/I/O/memory totals, vmstat, meminfo
and load. Governor/driver/min/max frequency, current frequency, block scheduler,
queue size/read-ahead, block geometry and write-cache policy are explicit.
Namespace identities and external hidden-quota assumptions remain visible.

Required telemetry is checked at both execution boundaries. Cgroup-root
`cpu.max`/`io.max` absence is accepted only as exact ENOENT at the visible
cgroup2 root; it is never converted to an observed quota value. Other missing
required values fail closed. CPU PSI `full` is not interpreted as system CPU
stall time. VM stock gauges may decrease normally: all raw values remain,
while cumulative VM deltas use the declared pgpgin/pgpgout/pswpin/pswpout,
pgfault/pgmajfault/oom_kill/nr_dirtied/nr_written subset. True cumulative
decreases or field loss terminate the admitted schedule.

Original persist/atomic/file-fsync/replace/directory-fsync intervals and
calling-thread CPU/resource data remain complete. Host/ancestor counters are
shared accounting, not exclusive costs, and nested operation wall times are
not added as independent costs. Boundary and admission read overhead is
reported outside the execution timer; hook overhead remains included and
uncalibrated. Observer output is buffered before execution, and receipt
writes are drained with file/directory fsync outside execution. Failed trials
retain partial raw boundaries/worker operations instead of disappearing.

Interferer readiness, file device, every write/fsync interval, bytes,
calling-thread CPU and whole-child CPU/I/O/fault/switch deltas are retained.
Only complete in-window operations contribute to its declared execution
cost; setup, stop, boundary reads and receipt output are separate. Its CPU is
not added to server/driver costs. Calibration and per-trial control receipts
are hashed alongside all benchmark readbacks.

Each condition is analyzed separately with the unchanged six-pair, all-pairs-
faster, approximate 97.5% lower-bound-above-one admission. The two comparisons
form a family within each condition; no pooled four-comparison confidence or
cross-host estimate is claimed. Historical EPYC/Xeon runs are not pooled.
Even a complete control run leaves physical attribution for evidence review:
`causal_runner_io_stall_proved=false`, `runner_independent_scaling_proved=false`,
`unbounded_scalability_proved=false`, and no release `EFFECT_ACK_DONE`.

Upload only `RECEIPT.json`, `ISOLATION_ADMISSION.json`, `measurements/*.json`
and `controls/*.json`. Never export `private-rings`, token/key-bearing stores
or interferer data payloads. External isolation reports are retained at their
bound external locations; automatic publication of those reports is not
authorized by this carrier.

Primary counter semantics:
[cgroup v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html),
[PSI](https://www.kernel.org/doc/html/latest/accounting/psi.html),
[proc accounting](https://docs.kernel.org/filesystems/proc.html),
[diskstats](https://docs.kernel.org/admin-guide/iostats.html).
