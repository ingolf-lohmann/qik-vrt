#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Admission, fixed interventions and fail-closed telemetry for the existing benchmark.

There is one workload engine: comparable_scale_benchmark. This module supplies
its controlled plan/lifecycle, never a parallel implementation or an auto-rerun.
"""
from __future__ import annotations

import datetime as dt
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
try:
    import resource
except ImportError:  # Portable contract checks; measurement itself is Linux-only.
    resource = None
import select
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / 'policy/QIKVRT_LINUX_SCALE_ISOLATION_V1.json'
CONDITIONS = ('isolated', 'io_interference')
SOURCE_PATHS = ('tools/qikvrt_linux_scale_isolation.py',
                'tools/qikvrt_firefox_windows_witness.py',
                'policy/QIKVRT_LINUX_SCALE_ISOLATION_V1.json',
                'src/qikvrt_effect_ack_http_terminal.py', 'src/qikvrt_api_handler.py',
                'src/qikvrt_effect_ack.py', 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin')


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def durable_json(path, value):
    """Observer output is drained outside timing, never left as queued I/O."""
    path = Path(path)
    raw = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw); stream.flush(); os.fsync(fd)
    finally:
        os.close(fd)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY:' + key)
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, 'NONFINITE_JSON:' + value))


def load_contract():
    p = strict_json(CONTRACT.read_bytes())
    require(p['schema'] == 'qikvrt_linux_scale_isolation_contract_v1'
            and p['repetitions_per_condition_and_process_count'] == 6
            and p['process_counts'] == [1, 2, 4] and p['conditions'] == list(CONDITIONS)
            and p['total_trials'] == 36 and p['maximum_additional_unmodified_hosted_trials'] == 0
            and p['workload'] == dict(requests=64, clients=4, origins=4, preload_per_origin=4,
                                     effects=80, records=160, replay_refusals=80, concurrent_replay_refusals=4)
            and p['python_version'] == '3.12.13' and p['maximum_trial_seconds'] == 15
            and p['interferer'] == dict(chunk_bytes=65536, extent_chunks=256, period_ns=5000000,
                max_operations=3000, calibration_operations=32, minimum_complete_in_window_operations=2,
                placement='FIRST_OF_THE_SAME_FOUR_CPU_SLOTS', fsync_after_every_write=True),
            'MEASUREMENT_CONTRACT_CHANGED_REQUIRES_NEW_PROTOCOL')
    require(all(value is False for value in p['claim_boundary'].values()), 'CONTRACT_CLAIM_BOUNDARY')
    require(p['protocol_id'] == 'PR443-ISOLATED-IO-CONTROL-V1'
            and p['order'] == 'REPETITION_THEN_CYCLIC_PROCESS_COUNT_THEN_ALTERNATING_CONDITION'
            and p['cache_policy'] == 'WARM_SNAPSHOT_COPY_AND_FULL_ADMISSION_READBACK_NO_DROPS_NO_EXCLUDED_WARMUP'
            and p['durability_policy'] == 'ORIGINAL_ATOMIC_WRITER_FILE_FSYNC_REPLACE_DIRECTORY_FSYNC'
            and p['minimum_available_bytes'] == 1073741824
            and p['maximum_attestation_validity_seconds'] == 86400
            and p['required_external_claims'] == ['dedicated_host', 'dedicated_local_volume', 'no_cotenants', 'no_other_io_producers', 'no_hidden_cpu_quota']
            and p['required_evidence_kinds'] == ['host_isolation', 'volume_isolation']
            and p['required_queue_fields'] == ['scheduler', 'nr_requests', 'read_ahead_kb', 'rotational', 'write_cache', 'logical_block_size', 'physical_block_size']
            and p['required_cpu_policy_fields'] == ['scaling_governor', 'scaling_driver', 'scaling_min_freq', 'scaling_max_freq'],
            'MEASUREMENT_ADMISSION_OR_POLICY_CHANGED_REQUIRES_NEW_PROTOCOL')
    return p


def trial_plan():
    plan = []
    for repeat in range(6):
        order = (1, 2, 4)[repeat % 3:] + (1, 2, 4)[:repeat % 3]
        conditions = CONDITIONS if repeat % 2 == 0 else CONDITIONS[::-1]
        for workers in order:
            for condition in conditions:
                plan.append((repeat, order, workers, condition))
    return plan


def regular_bytes(path, limit=16 * 1024 * 1024):
    path = Path(path)
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'SYMLINKED_CONTROL_INPUT:' + str(part))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= limit, 'CONTROL_INPUT_NOT_BOUNDED_REGULAR_FILE')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                and len(raw) == before.st_size, 'CONTROL_INPUT_CHANGED_WHILE_READING')
        return raw
    finally:
        os.close(fd)


def attestation_inputs(path, expected_digest, pinned, contract, now=None):
    path = Path(path).absolute()
    require(not path.is_relative_to(ROOT), 'ATTESTATION_MUST_BE_EXTERNAL_TO_CHECKOUT')
    require(re.fullmatch('[0-9a-f]{64}', expected_digest or '') is not None, 'ATTESTATION_SHA256_REQUIRED')
    raw = regular_bytes(path, 1024 * 1024)
    require(hashlib.sha256(raw).hexdigest() == expected_digest, 'ATTESTATION_DIGEST_MISMATCH')
    a = strict_json(raw)
    require(set(a) == {'schema', 'issuer', 'valid_until', 'claims', 'evidence', 'pinned_environment'},
            'ATTESTATION_FIELDS_NOT_CLOSED')
    require(a['schema'] == contract['attestation_schema'], 'ATTESTATION_SCHEMA')
    require(set(a['issuer']) == {'verifier', 'verification_method', 'runner_self_report'}
            and a['issuer']['runner_self_report'] is False
            and all(isinstance(a['issuer'][key], str) and a['issuer'][key].strip()
                    for key in ('verifier', 'verification_method')), 'EXTERNAL_VERIFIER_REQUIRED')
    require(set(a['claims']) == set(contract['required_external_claims'])
            and all(value is True for value in a['claims'].values()), 'EXTERNAL_ISOLATION_NOT_ATTESTED')
    now = now or dt.datetime.now(dt.timezone.utc)
    expiry = dt.datetime.fromisoformat(a['valid_until'])
    require(expiry.tzinfo is not None and 0 < (expiry - now).total_seconds() <=
            contract['maximum_attestation_validity_seconds'], 'ATTESTATION_EXPIRED_OR_OVERLONG')
    require(a['pinned_environment'] == pinned, 'PINNED_ENVIRONMENT_MISMATCH')
    bindings = []
    require(isinstance(a['evidence'], list) and 2 <= len(a['evidence']) <= 16, 'EXTERNAL_EVIDENCE_REQUIRED')
    for e in a['evidence']:
        require(set(e) == {'kind', 'path', 'bytes', 'sha256'}, 'EVIDENCE_FIELDS_NOT_CLOSED')
        relative = Path(e['path'])
        require(not relative.is_absolute() and relative.parts and '..' not in relative.parts,
                'EVIDENCE_PATH_ESCAPE')
        source = path.parent / relative
        content = regular_bytes(source)
        require(type(e['bytes']) is int and e['bytes'] > 0 and len(content) == e['bytes']
                and hashlib.sha256(content).hexdigest() == e['sha256'], 'EXTERNAL_EVIDENCE_BINDING_MISMATCH')
        bindings.append({'source': str(source), **e})
    require(set(contract['required_evidence_kinds']) <= {e['kind'] for e in bindings}, 'ISOLATION_EVIDENCE_KIND_MISSING')
    return a, bindings


def observed(observation, reason):
    require(isinstance(observation, dict) and observation.get('state') == 'OBSERVED', reason)
    return observation['value']


def cgroup_pins(b, targets):
    pins = {}
    for target in targets.values():
        require(target['membership']['state'] == 'OBSERVED' and len(target['groups']) == 1,
                'CGROUP_V2_MEMBERSHIP_NOT_FULLY_OBSERVED')
        group = target['groups'][0]
        require(group['state'] == 'OBSERVED' and group['version'] == 'v2'
                and group['mount']['root'] == '/' and group['visible_ancestors'][-1] == group['mount']['mount_point'],
                'FULL_VISIBLE_CGROUP_ROOT_ANCESTRY_REQUIRED')
        for path in group['visible_ancestors']:
            if path in pins:
                continue
            root = path == group['mount']['mount_point']
            values = {}
            for name in ('cpu.max', 'io.max', 'cpuset.cpus.effective'):
                item = b.benchmark_observation(Path(path) / name)
                if (root and name in ('cpu.max', 'io.max') and item['state'] == 'UNAVAILABLE'
                        and item.get('errno') == errno.ENOENT):
                    values[name] = {'state': 'ROOT_NO_LIMIT_INTERFACE', 'source': item['source']}
                else:
                    values[name] = observed(item, 'CGROUP_POLICY_UNAVAILABLE:' + path + '/' + name)
                if name == 'cpu.max' and isinstance(values[name], str):
                    fields = values[name].split()
                    require(len(fields) == 2 and fields[0] == 'max' and int(fields[1]) > 0,
                            'FINITE_OR_MALFORMED_CPU_QUOTA:' + path)
            values['root'] = root
            pins[path] = values
    require(bool(pins), 'CGROUP_ANCESTRY_EMPTY')
    return pins


def collect_static(b, output_parent, contract):
    require(sys.platform == 'linux' and platform.machine() == 'x86_64', 'NATIVE_LINUX_X64_REQUIRED')
    require(Path(output_parent).is_dir() and not Path(output_parent).is_symlink(), 'REAL_OUTPUT_PARENT_REQUIRED')
    cpus = sorted(os.sched_getaffinity(0))
    require(len(cpus) == 4, 'EXACTLY_FOUR_FIXED_CPU_SLOTS_REQUIRED')
    cpu_policy = {}
    cores = []
    for cpu in cpus:
        base = Path('/sys/devices/system/cpu') / ('cpu' + str(cpu))
        cpu_policy[str(cpu)] = {name: observed(b.benchmark_observation(base / 'cpufreq' / name),
            'CPU_POLICY_UNAVAILABLE:' + str(cpu) + '/' + name) for name in contract['required_cpu_policy_fields']}
        require(0 < int(cpu_policy[str(cpu)]['scaling_min_freq']) <= int(cpu_policy[str(cpu)]['scaling_max_freq'])
                and cpu_policy[str(cpu)]['scaling_governor'] and cpu_policy[str(cpu)]['scaling_driver'], 'CPU_POLICY_MALFORMED')
        core = [observed(b.benchmark_observation(base / 'topology' / name), 'CPU_TOPOLOGY_UNAVAILABLE')
                for name in ('physical_package_id', 'core_id')]
        cpu_policy[str(cpu)]['core_identity'] = core
        cores.append(tuple(core))
    require(len(set(cores)) == 4, 'FOUR_DISTINCT_PHYSICAL_CORE_IDENTITIES_REQUIRED')
    storage = b.benchmark_storage_identity(output_parent)
    require(storage['state'] == 'OBSERVED' and storage['mount'] and storage['mount']['filesystem'] in ('ext4', 'xfs')
            and storage['block_device_sysfs'] and storage['backing_device_attribution'] == 'VISIBLE_BLOCK_DEVICE',
            'DURABLE_LOCAL_BLOCK_FILESYSTEM_REQUIRED')
    require(storage['available_bytes'] >= contract['minimum_available_bytes'], 'DEDICATED_VOLUME_CAPACITY_TOO_LOW')
    block = Path(storage['block_device_sysfs'])
    queue = block / 'queue' if (block / 'queue').is_dir() else block.parent / 'queue'
    require(queue.is_dir(), 'BLOCK_QUEUE_UNAVAILABLE')
    queue_values = {name: observed(b.benchmark_observation(queue / name), 'QUEUE_POLICY_UNAVAILABLE:' + name)
                    for name in contract['required_queue_fields']}
    require(int(queue_values['nr_requests']) > 0 and int(queue_values['read_ahead_kb']) >= 0
            and int(queue_values['rotational']) in (0, 1)
            and int(queue_values['logical_block_size']) > 0 and int(queue_values['physical_block_size']) > 0
            and queue_values['scheduler'] and queue_values['write_cache'] in ('write back', 'write through'), 'QUEUE_POLICY_MALFORMED')
    cpuinfo = observed(b.benchmark_observation('/proc/cpuinfo'), 'CPU_IDENTITY_UNAVAILABLE')
    models = sorted({line.split(':', 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('model name')})
    require(bool(models), 'CPU_MODEL_UNAVAILABLE')
    targets = b.benchmark_telemetry_targets([])
    return {'host': {'machine_id': observed(b.benchmark_observation('/etc/machine-id'), 'HOST_ID_UNAVAILABLE'),
                     'boot_id': observed(b.benchmark_observation('/proc/sys/kernel/random/boot_id'), 'BOOT_ID_UNAVAILABLE'),
                     'kernel_release': platform.release(), 'cpu_models': models},
            'python': {'version': platform.python_version(), 'binary_sha256': sha256(sys.executable)},
            'subject': {'head': b.terminal_subject()['head'], 'tree': b.terminal_subject()['tree']},
            'source_sha256': {p: sha256(ROOT / p) for p in SOURCE_PATHS},
            'affinity_cpus': cpus, 'cpu_policy': cpu_policy,
            'cgroup_namespace_identity': {'self': os.readlink('/proc/self/ns/cgroup'), 'pid1': os.readlink('/proc/1/ns/cgroup'),
                'outside_namespace_limits_basis': 'EXTERNAL_NO_HIDDEN_CPU_QUOTA_ATTESTATION_REQUIRED'},
            'storage': {key: storage[key] for key in ('device', 'mount', 'block_device_sysfs', 'visible_backing_slaves',
                'backing_device_attribution', 'block_size', 'fragment_size')},
            'queue_path': str(queue), 'queue_policy': queue_values,
            'cgroup_policy': cgroup_pins(b, targets),
            'cache_policy': contract['cache_policy'], 'durability_policy': contract['durability_policy']}


def validate_snapshot(snapshot, pins, condition):
    def finite(value):
        if isinstance(value, dict):
            for item in value.values():
                finite(item)
        elif isinstance(value, list):
            for item in value:
                finite(item)
        elif isinstance(value, float):
            require(math.isfinite(value), 'NONFINITE_KERNEL_TELEMETRY')
    finite(snapshot)
    require(snapshot['end_ns'] > snapshot['start_ns'] and snapshot['observer_cpu_seconds'] >= 0,
            'COLLECTOR_OVERHEAD_NOT_OBSERVED')
    host = snapshot['host']
    for name in ('cpu_jiffies', 'diskstats', 'vmstat', 'loadavg', 'meminfo'):
        observed(host[name], 'HOST_TELEMETRY_MISSING:' + name)
    require(pins['storage']['device'] in host['diskstats']['value'], 'SNAPSHOT_DEVICE_DISKSTATS_MISSING')
    for name in ('cpu', 'io', 'memory'):
        pressure = observed(host['pressure'][name], 'HOST_PSI_MISSING:' + name)
        require('some' in pressure and type(pressure['some'].get('total')) is int, 'HOST_PSI_TOTAL_MISSING')
        if name != 'cpu':
            require('full' in pressure and type(pressure['full'].get('total')) is int, 'HOST_PSI_FULL_MISSING')
    roles = []
    for p in snapshot['processes'].values():
        roles.append(p['role'])
        expected_affinity = pins['affinity_cpus'][:1] if p['role'] == 'INTERFERER' else pins['affinity_cpus']
        require(observed(p['affinity_cpus'], 'PROCESS_AFFINITY_MISSING') == expected_affinity, 'PROCESS_AFFINITY_DRIFT')
        observed(p['cgroup_membership'], 'PROCESS_CGROUP_MEMBERSHIP_MISSING')
        io = observed(p['io'], 'PROCESS_IO_MISSING')
        require({'rchar', 'wchar', 'read_bytes', 'write_bytes', 'syscr', 'syscw'} <= io.keys(), 'PROCESS_IO_FIELDS_MISSING')
        switches = observed(p['main_thread_context_switches'], 'PROCESS_SWITCHES_MISSING')
        require({'voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches'} <= switches.keys(), 'PROCESS_SWITCH_FIELDS_MISSING')
    require(roles.count('DRIVER') == 1 and roles.count('INTERFERER') == int(condition == 'io_interference'),
            'CONDITION_INTERFERER_MEMBERSHIP_MISMATCH')
    require(set(snapshot['cgroups']) == set(pins['cgroup_policy']), 'CGROUP_ANCESTRY_DRIFT')
    for path, group in snapshot['cgroups'].items():
        policy = pins['cgroup_policy'][path]
        for name in ('cpu.max', 'io.max', 'cpuset.cpus.effective'):
            expected = policy[name]
            item = group.get(name, {})
            if isinstance(expected, dict) and expected.get('state') == 'ROOT_NO_LIMIT_INTERFACE':
                require(item.get('state') == 'UNAVAILABLE' and item.get('errno') == errno.ENOENT, 'CGROUP_ROOT_INTERFACE_DRIFT')
            else:
                require(observed(item, 'CGROUP_POLICY_MISSING') == expected, 'CGROUP_POLICY_DRIFT')
        cpu = observed(group['cpu.stat'], 'CGROUP_CPU_STAT_MISSING')
        require({'usage_usec', 'user_usec', 'system_usec'} <= cpu.keys(), 'CGROUP_CPU_FIELDS_MISSING')
        if not policy['root']:
            require({'nr_throttled', 'throttled_usec'} <= cpu.keys(), 'CGROUP_THROTTLE_FIELDS_MISSING')
        io = observed(group['io.stat'], 'CGROUP_IO_STAT_MISSING')
        require(bool(io) and all({'rbytes', 'wbytes', 'rios', 'wios'} <= row.keys() for row in io.values()), 'CGROUP_IO_FIELDS_MISSING')
        for name in ('cpu.pressure', 'io.pressure', 'memory.pressure'):
            pressure = observed(group[name], 'CGROUP_PSI_MISSING')
            require('some' in pressure and type(pressure['some'].get('total')) is int, 'CGROUP_PSI_TOTAL_MISSING')


def check_counter_continuity(b, before, after):
    # Most nr_* VM entries (and workingset_nodes) are stock gauges. Their
    # normal decreases are not counter resets. Preserve all raw values and
    # subtract only these declared cumulative VM counters.
    cumulative_vm = {'pgpgin', 'pgpgout', 'pswpin', 'pswpout', 'pgfault', 'pgmajfault', 'oom_kill', 'nr_dirtied', 'nr_written'}
    def counter_scope(snapshot):
        selected = dict(snapshot)
        if 'host' in snapshot and 'vmstat' in snapshot['host']:
            selected['host'] = dict(snapshot['host'])
            vm = dict(snapshot['host']['vmstat'])
            if vm.get('state') == 'OBSERVED':
                vm['value'] = {k: v for k, v in vm['value'].items() if k in cumulative_vm}
            selected['host']['vmstat'] = vm
        return selected
    delta = b.benchmark_counter_delta(counter_scope(before), counter_scope(after))
    def walk(value, path=''):
        if isinstance(value, dict):
            require(value.get('state') not in ('COUNTER_RESET_OR_DECREASE', 'UNAVAILABLE_FIELD'), 'COUNTER_RESET_OR_FIELD_LOSS:' + path)
            for key, v in value.items():
                walk(v, path + '/' + key)
    walk(delta)
    return delta


def io_child(path, output, cpu, calibration=False):
    """Fixed pwrite+fsync intervention. Limits are independent of parent liveness."""
    require(sys.platform == 'linux' and resource is not None, 'INTERFERER_REQUIRES_NATIVE_LINUX')
    require(not Path(output).exists(), 'NEW_INTERFERER_RECEIPT_REQUIRED_NO_OVERWRITE')
    contract = load_contract()
    p = contract['interferer']
    os.sched_setaffinity(0, {cpu})
    rows, error = [], None
    fd = None
    started = time.perf_counter_ns()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    data = (b'QIKVRT-fixed-io-control\n' * (p['chunk_bytes'] // 24 + 2))[:p['chunk_bytes']]
    require(len(data) == p['chunk_bytes'], 'INTERFERER_PAYLOAD_LENGTH')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.ftruncate(fd, p['chunk_bytes'] * p['extent_chunks'])
        maximum = p['calibration_operations'] if calibration else p['max_operations']
        for index in range(maximum):
            if time.perf_counter_ns() - started >= contract['maximum_trial_seconds'] * 10**9:
                error = 'INTERFERER_WALL_BUDGET_EXHAUSTED'
                break
            if not calibration and index and select.select([sys.stdin], [], [], 0)[0]:
                require(sys.stdin.readline().strip() == 'STOP', 'PARENT_PIPE_LOST_OR_INVALID_STOP')
                break
            left, thread = time.perf_counter_ns(), time.thread_time_ns()
            count = os.pwrite(fd, data, (index % p['extent_chunks']) * p['chunk_bytes'])
            require(count == p['chunk_bytes'], 'INTERFERER_SHORT_WRITE')
            fsync_start = time.perf_counter_ns()
            os.fsync(fd)
            right = time.perf_counter_ns()
            rows.append({'start_ns': left, 'file_fsync_start_ns': fsync_start, 'end_ns': right,
                         'bytes': count, 'thread_cpu_seconds': (time.thread_time_ns() - thread) / 1e9})
            if index == 0 and not calibration:
                print(json.dumps({'state': 'READY', 'pid': os.getpid()}), flush=True)
            if not calibration:
                time.sleep(max(0, (p['period_ns'] - (time.perf_counter_ns() - left)) / 1e9))
        else:
            if not calibration:
                error = 'INTERFERER_OPERATION_BUDGET_EXHAUSTED'
    except Exception as exc:
        error = type(exc).__name__ + ':' + str(exc)
    finally:
        if fd is not None:
            os.close(fd)
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    result = {'schema': 'qikvrt_fixed_io_interferer_receipt_v1', 'state': 'HOLD' if error else 'PASS', 'error': error,
              'pid': os.getpid(), 'affinity_cpus': sorted(os.sched_getaffinity(0)), 'calibration': calibration,
              'file_device': str(os.major(os.stat(path).st_dev)) + ':' + str(os.minor(os.stat(path).st_dev)) if Path(path).exists() else None,
              'started_ns': started, 'ended_ns': time.perf_counter_ns(), 'operations': rows,
              'payload_sha256': hashlib.sha256(data).hexdigest(), 'parameters': p,
              'resource_delta': {name: getattr(usage_after, name) - getattr(usage_before, name)
                 for name in ('ru_utime', 'ru_stime', 'ru_inblock', 'ru_oublock', 'ru_nvcsw', 'ru_nivcsw', 'ru_minflt', 'ru_majflt')}}
    durable_json(output, result)
    return 0 if error is None else 2


class IsolatedScaleControl:
    def __init__(self, b, output, attestation, attestation_sha256, expected_head, expected_tree):
        self.b, self.output = b, Path(output).absolute()
        self.contract = load_contract()
        self.child = None
        self.active = None
        self.calibration = None
        self.attestation_path, self.attestation_sha256 = Path(attestation).absolute(), attestation_sha256
        self.expected_subject = {'head': expected_head, 'tree': expected_tree}
        require(all(re.fullmatch('[0-9a-f]{40}', v or '') for v in self.expected_subject.values()), 'EXACT_HEAD_TREE_REQUIRED')
        require(not self.output.exists(), 'NEW_ISOLATED_OUTPUT_REQUIRED_NO_RESET_OR_OVERWRITE')
        require(not self.output.is_relative_to(ROOT), 'ISOLATED_OUTPUT_MUST_BE_OUTSIDE_CHECKOUT')
        self.pins = collect_static(b, self.output.parent, self.contract)
        require(self.pins['subject'] == self.expected_subject, 'ISOLATED_EXACT_SUBJECT_MISMATCH')
        require(self.pins['python']['version'] == self.contract['python_version'], 'ISOLATED_EXACT_INTERPRETER_REQUIRED')
        self.attestation, self.evidence = attestation_inputs(self.attestation_path, attestation_sha256, self.pins, self.contract)
        self.verify_source()
        snapshot = b.benchmark_host_snapshot(b.benchmark_telemetry_targets([]))
        validate_snapshot(snapshot, self.pins, 'isolated')
        self.preflight = snapshot

    def verify_source(self):
        require(self.b.terminal_subject() == self.expected_subject, 'ISOLATED_HEAD_TREE_DRIFT')
        status = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, timeout=15)
        require(not status, 'ISOLATED_CHECKOUT_MUST_BE_CLEAN')
        for path, expected in self.pins['source_sha256'].items():
            raw = subprocess.check_output(['git', 'show', 'HEAD:' + path], cwd=ROOT, timeout=15)
            require(hashlib.sha256(raw).hexdigest() == expected == sha256(ROOT / path), 'ISOLATED_SOURCE_NOT_EXACT_HEAD:' + path)

    def reobserve(self):
        started, cpu = time.perf_counter_ns(), time.process_time_ns()
        require(collect_static(self.b, self.output.parent, self.contract) == self.pins, 'STATIC_ENVIRONMENT_DRIFT')
        attestation_inputs(self.attestation_path, self.attestation_sha256, self.pins, self.contract)
        self.verify_source()
        return {'start_ns': started, 'end_ns': time.perf_counter_ns(),
                'observer_cpu_seconds': (time.process_time_ns() - cpu) / 1e9}

    def acquire_budget(self):
        """Durable create-only lease; failed/partial runs never replenish trials."""
        parent = self.output.parent / '.qikvrt-scale-budgets'
        parent.mkdir(mode=0o700, exist_ok=True)
        require(not parent.is_symlink() and parent.is_dir(), 'BUDGET_LEDGER_NOT_REAL_DIRECTORY')
        material = {'subject': self.expected_subject, 'contract_sha256': sha256(CONTRACT)}
        key = hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()
        path = parent / (key + '.json')
        payload = material | {'output': str(self.output), 'total_trials': 36,
                              'state': 'ACQUIRED_NO_RETRY_NO_BUDGET_REPLENISHMENT'}
        raw = (json.dumps(payload, sort_keys=True, indent=2) + '\n').encode()
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            raise RuntimeError('EXACT_SUBJECT_MEASUREMENT_BUDGET_ALREADY_ACQUIRED') from None
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.budget_lease = {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def plan(self, repetitions, workload, preload, clients):
        require((repetitions, workload, preload, clients) == (6, 64, 4, 4), 'ISOLATED_WORKLOAD_OR_BUDGET_CHANGED')
        return trial_plan()

    def before_trial(self, run_id, condition):
        require(self.child is None and condition in CONDITIONS, 'INTERFERER_LEAK_OR_UNKNOWN_CONDITION')
        self.active_raw = {'schema': 'qikvrt_isolated_trial_partial_v1', 'state': 'INCOMPLETE',
            'run_id': run_id, 'condition': condition, 'subject': self.expected_subject}
        self.record('TRIAL_ADMISSION')
        validation = self.reobserve()
        directory = self.output / 'controls'
        directory.mkdir(mode=0o700, exist_ok=True)
        if self.calibration is None:
            data, receipt = directory / 'calibration.data', directory / 'calibration.json'
            command = [sys.executable, '-B', str(ROOT / 'tools/qikvrt_firefox_windows_witness.py'),
                       '--isolated-io-child', str(data), str(receipt), str(self.pins['affinity_cpus'][0]), 'calibration']
            result = subprocess.run(command, timeout=20, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            require(result.returncode == 0 and receipt.is_file(), 'INTERFERER_CALIBRATION_FAILED')
            calibration = strict_json(receipt.read_bytes())
            require(calibration['state'] == 'PASS' and calibration['calibration'] is True
                    and calibration['file_device'] == self.pins['storage']['device']
                    and len(calibration['operations']) == self.contract['interferer']['calibration_operations'], 'CALIBRATION_NOT_EXACT')
            data.unlink()
            self.calibration = {'path': receipt.relative_to(self.output).as_posix(), 'bytes': receipt.stat().st_size, 'sha256': sha256(receipt)}
        self.active = {'run_id': run_id, 'condition': condition, 'static_before_trial': validation}

    def record(self, stage, **values):
        self.active_raw.update(stage=stage, **values)
        self.partial_pending = True
        # No observer-output write immediately before the execution interval.
        # On failure close() drains the in-memory partial receipt instead.
        if stage == 'AFTER_EXECUTION':
            self.flush_partial()

    def flush_partial(self):
        if not getattr(self, 'partial_pending', False):
            return
        path = self.output / 'measurements' / (self.active_raw['run_id'] + '.json')
        durable_json(path, self.active_raw)
        self.partial_pending = False

    def write_receipt(self, path, value):
        durable_json(path, value)

    def before_execution(self, targets, stores):
        require(all(s['state'] == 'OBSERVED' and all(s[key] == self.pins['storage'][key]
                for key in ('device', 'mount', 'block_device_sysfs')) for s in stores), 'TRIAL_STORAGE_NOT_DEDICATED_VOLUME')
        if self.active['condition'] == 'io_interference':
            directory = self.output / 'controls'
            name = self.active['run_id']
            self.data, self.child_receipt = directory / (name + '.data'), directory / (name + '.json')
            self.child = subprocess.Popen([sys.executable, '-B', str(ROOT / 'tools/qikvrt_firefox_windows_witness.py'),
                '--isolated-io-child', str(self.data), str(self.child_receipt), str(self.pins['affinity_cpus'][0]), 'interference'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            require(bool(select.select([self.child.stdout], [], [], 8)[0]), 'INTERFERER_READINESS_TIMEOUT')
            ready = strict_json(self.child.stdout.readline())
            require(ready == {'state': 'READY', 'pid': self.child.pid}, 'INTERFERER_NOT_READY')
            targets = self.b.benchmark_telemetry_targets([int(pid) for pid, item in targets.items() if item['role'] == 'SERVER'] + [self.child.pid])
            targets[str(self.child.pid)]['role'] = 'INTERFERER'
        require(cgroup_pins(self.b, targets) == self.pins['cgroup_policy'], 'PROCESS_CGROUP_POLICY_DRIFT')
        return targets

    def boundary(self, snapshot):
        validation = self.reobserve()
        validate_snapshot(snapshot, self.pins, self.active['condition'])
        frequency = {str(cpu): self.b.benchmark_observation(Path('/sys/devices/system/cpu') / ('cpu' + str(cpu))
                     / 'cpufreq/scaling_cur_freq') for cpu in self.pins['affinity_cpus']}
        require(all(value['state'] == 'OBSERVED' for value in frequency.values()), 'CURRENT_CPU_FREQUENCY_UNAVAILABLE')
        return {'validation_overhead': validation, 'cpu_frequency_khz': frequency}

    def after_execution(self, before, after, start, end):
        result = dict(self.active)
        result['counter_deltas'] = check_counter_continuity(self.b, before, after)
        require(0 < end - start < self.contract['maximum_trial_seconds'] * 10**9, 'TRIAL_EXECUTION_BUDGET_EXHAUSTED')
        require(all(p['cgroup_membership'] == after['processes'][pid]['cgroup_membership'] for pid, p in before['processes'].items()),
                'PROCESS_MEMBERSHIP_DRIFT_DURING_EXECUTION')
        if self.child:
            require(self.child.poll() is None, 'INTERFERER_EXITED_BEFORE_TRIAL_END')
            _, stderr = self.child.communicate('STOP\n', timeout=8)
            require(self.child.returncode == 0 and not stderr, 'INTERFERER_FAILED')
            raw = strict_json(self.child_receipt.read_bytes())
            require(raw['state'] == 'PASS' and raw['calibration'] is False
                    and raw['pid'] == self.child.pid and raw['parameters'] == self.contract['interferer']
                    and raw['file_device'] == self.pins['storage']['device'], 'INTERFERER_READBACK_NOT_EXACT')
            inside = [row for row in raw['operations'] if start <= row['start_ns'] < row['end_ns'] <= end]
            require(len(inside) >= self.contract['interferer']['minimum_complete_in_window_operations'], 'INTERFERENCE_NOT_OBSERVED_IN_EXECUTION_WINDOW')
            result['interferer'] = {'path': self.child_receipt.relative_to(self.output).as_posix(),
                'bytes': self.child_receipt.stat().st_size, 'sha256': sha256(self.child_receipt),
                'complete_operations_in_execution': len(inside), 'bytes_in_execution': sum(row['bytes'] for row in inside),
                'thread_cpu_seconds_in_execution': sum(row['thread_cpu_seconds'] for row in inside),
                'file_fsync_wall_seconds_in_execution': sum((row['end_ns'] - row['file_fsync_start_ns']) / 1e9 for row in inside),
                'accounting': 'Separate interferer costs; never included as exclusive server/driver costs.'}
            self.child = None
            self.data.unlink()
        else:
            result['interferer'] = {'state': 'ABSENT', 'complete_operations_in_execution': 0}
        self.active = None
        return result

    def finalize(self, result):
        self.reobserve()
        require(len(result['measurements']) == 36, 'ISOLATED_SAMPLE_BUDGET_NOT_COMPLETE')
        expected_plan = [(repeat + 1, workers, condition) for repeat, _, workers, condition in trial_plan()]
        require([(row['repetition'], row['processes'], row['condition']) for row in result['measurements']] == expected_plan,
                'ISOLATED_ORDER_OR_CONDITION_CHANGED')
        for row in result['measurements']:
            require((row['effects'], row['referenced_records'], row['requests'], row['parallel_clients']) == (80, 160, 64, 4)
                    and row['invariants']['replay_refusals'] == 80
                    and row['invariants']['concurrent_replay_statuses'] == [409] * 4,
                    'ISOLATED_WORKLOAD_OR_EFFECT_INVARIANT_CHANGED')
        require(len({tuple(row['initial_snapshot_sha256']) for row in result['measurements']}) == 1
                and len({row['workload_sha256'] for row in result['measurements']}) == 1, 'CROSS_CONDITION_START_OR_WORKLOAD_DRIFT')
        evidence = self.output / 'ISOLATION_ADMISSION.json'
        durable_json(evidence, {'attestation': self.attestation, 'attestation_sha256': self.attestation_sha256,
            'external_evidence_bindings': self.evidence, 'pinned_environment': self.pins,
            'preflight': self.preflight, 'calibration': self.calibration,
            'external_attestation_is_not_independent_automatic_physical_verification': True})
        result['isolated_control'] = {'state': 'OBSERVED_CONTRACT_BOUND_HOST_ONLY',
            'contract_sha256': sha256(CONTRACT), 'admission': {'path': evidence.name, 'bytes': evidence.stat().st_size, 'sha256': sha256(evidence)},
            'calibration': self.calibration, 'conditions': list(CONDITIONS), 'total_trials': 36, 'budget_lease': self.budget_lease,
            'isolation_basis': 'EXTERNAL_ATTESTATION_AND_EXACT_LOCAL_READBACK',
            'causal_runner_io_stall_proved': False, 'runner_independent_scaling_proved': False}
        result['variance_observability']['state'] = 'CONTROL_OBSERVED_CAUSAL_ATTRIBUTION_REVIEW_REQUIRED'
        return result

    def close(self):
        try:
            self.flush_partial()
        finally:
            if self.child is not None:
                if self.child.poll() is None:
                    self.child.kill()
                self.child.communicate(timeout=8)
                self.child = None


def run_isolated(b, terminal, args):
    output = args.output.absolute()
    require(not output.exists(), 'NEW_ISOLATED_OUTPUT_REQUIRED_NO_RESET_OR_OVERWRITE')
    require(not output.is_relative_to(ROOT), 'ISOLATED_OUTPUT_MUST_BE_OUTSIDE_CHECKOUT')
    for part in (output.parent, *output.parent.parents):
        require(not part.is_symlink(), 'SYMLINKED_OUTPUT_PARENT')
    control = None
    try:
        control = IsolatedScaleControl(b, output, args.isolation_attestation, args.isolation_attestation_sha256,
                                       args.expected_head, args.expected_tree)
        control.acquire_budget()
        result = b.comparable_scale_benchmark(terminal, output, ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin', control=control)
        result = control.finalize(result)
    except Exception as exc:
        result = {'schema': 'qikvrt_linux_isolated_scale_control_receipt_v1', 'state': 'HOLD',
                  'reason': type(exc).__name__ + ':' + str(exc), **b.terminal_subject(),
                  'observed_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'requested_subject': {'head': args.expected_head, 'tree': args.expected_tree},
                  'retained_trial_receipts': [p.name for p in sorted((output / 'measurements').glob('*.json'))],
                  'predecessor_evidence_transfer': False, 'causal_runner_io_stall_proved': False,
                  'runner_independent_scaling_proved': False, 'comparative_speedup_proved': False,
                  'unbounded_scalability_proved': False, 'personal_release_effect_ack_done': False}
        output.mkdir(mode=0o700, parents=True, exist_ok=True)
    finally:
        if control:
            try:
                control.close()
            except (OSError, subprocess.SubprocessError) as error:
                result.update(state='HOLD', cleanup_error=str(error), comparative_speedup_proved=False)
            result['budget_lease'] = getattr(control, 'budget_lease', None)
    result['ci_provenance'] = {key: os.environ.get(key) for key in ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')}
    result['contract_sha256'] = sha256(CONTRACT)
    durable_json(output / 'RECEIPT.json', result)
    print(json.dumps({key: value for key, value in result.items() if key not in ('measurements', 'summary')}, sort_keys=True))
    return 0 if result['state'] == 'PASS' else 2
