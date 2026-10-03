# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Source-scope controls, not isolation attestation or performance evidence."""
from __future__ import annotations

import copy
import contextlib
import datetime as dt
import errno
import hashlib
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tools import qikvrt_linux_scale_isolation as isolation
from tools import qikvrt_firefox_windows_witness as benchmark

ROOT = Path(__file__).resolve().parents[1]


def snapshot_fixture(condition='isolated'):
    def observation(value):
        return {'state': 'OBSERVED', 'value': value}
    pins = {'affinity_cpus': [0, 1, 2, 3], 'storage': {'device': '8:1'},
            'cgroup_policy': {'/cg': {'root': True, 'cpu.max': {'state': 'ROOT_NO_LIMIT_INTERFACE'},
                                     'io.max': {'state': 'ROOT_NO_LIMIT_INTERFACE'}, 'cpuset.cpus.effective': '0-3'}}}
    cpu = observation({'usage_usec': 10, 'user_usec': 5, 'system_usec': 5})
    pressure = observation({'some': {'total': 1, 'avg10': 0.0}, 'full': {'total': 1, 'avg10': 0.0}})
    io = observation({'rbytes': 1, 'wbytes': 1, 'rios': 1, 'wios': 1})
    group = {'cpu.stat': cpu, 'io.stat': observation({'8:0': io['value']}),
        'cpu.max': {'state': 'UNAVAILABLE', 'errno': errno.ENOENT},
        'io.max': {'state': 'UNAVAILABLE', 'errno': errno.ENOENT},
        'cpuset.cpus.effective': observation('0-3'),
        **{name + '.pressure': copy.deepcopy(pressure) for name in ('cpu', 'io', 'memory')}}
    process = {'role': 'DRIVER', 'affinity_cpus': observation([0, 1, 2, 3]),
        'cgroup_membership': observation('0::/'),
        'io': observation(dict(rchar=1, wchar=1, read_bytes=1, write_bytes=1, syscr=1, syscw=1)),
        'main_thread_context_switches': observation(dict(voluntary_ctxt_switches=1, nonvoluntary_ctxt_switches=1))}
    processes = {'100': process, '101': dict(copy.deepcopy(process), role='SERVER')}
    if condition == 'io_interference':
        processes['102'] = dict(copy.deepcopy(process), role='INTERFERER', affinity_cpus=observation([0]))
    snapshot = {'start_ns': 10, 'end_ns': 20, 'observer_cpu_seconds': .001, 'processes': processes,
        'cgroups': {'/cg': group}, 'host': {'cpu_jiffies': observation(dict(user=1, iowait=1, steal=0)),
            'diskstats': observation({'8:1': dict(writes_completed=1)}), 'vmstat': observation(dict(pgpgout=1)),
            'loadavg': observation('0 0 0'), 'meminfo': observation('MemFree: 1024 kB'),
            'pressure': {name: copy.deepcopy(pressure) for name in ('cpu', 'io', 'memory')}}}
    return snapshot, pins


class IsolationContractTests(unittest.TestCase):
    def test_exact_budget_nested_pairs_and_balanced_order(self):
        contract = isolation.load_contract()
        plan = isolation.trial_plan()
        self.assertEqual(contract['maximum_additional_unmodified_hosted_trials'], 0)
        self.assertEqual(len(plan), 36)
        for condition in isolation.CONDITIONS:
            for processes in (1, 2, 4):
                self.assertEqual([r + 1 for r, _, n, c in plan if n == processes and c == condition], list(range(1, 7)))
        for i in range(0, 36, 2):
            self.assertEqual(plan[i][:3], plan[i + 1][:3])
            self.assertNotEqual(plan[i][3], plan[i + 1][3])
        self.assertEqual([plan[r * 6][1] for r in range(6)], [(1, 2, 4), (2, 4, 1), (4, 1, 2)] * 2)
        self.assertEqual([plan[r * 6][3] for r in range(6)], ['isolated', 'io_interference'] * 3)

    def test_budget_or_workload_changes_fail_closed(self):
        control = isolation.IsolatedScaleControl.__new__(isolation.IsolatedScaleControl)
        for values in ((9, 64, 4, 4), (6, 4, 4, 4), (6, 64, 1, 4), (6, 64, 4, 2)):
            with self.subTest(values=values), self.assertRaisesRegex(RuntimeError, 'WORKLOAD_OR_BUDGET_CHANGED'):
                control.plan(*values)
        self.assertEqual(len(control.plan(6, 64, 4, 4)), 36)

    def test_closed_json_rejects_duplicates_and_nan(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(RuntimeError):
                isolation.strict_json(raw)

    def test_attestation_exact_digests_external_evidence_and_expiry(self):
        contract = isolation.load_contract()
        now = dt.datetime(2026, 10, 3, tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            evidence = []
            for kind in ('host_isolation', 'volume_isolation'):
                raw = ('EXTERNAL VERIFICATION FIXTURE ONLY:' + kind).encode()
                (parent / kind).write_bytes(raw)
                evidence.append(dict(kind=kind, path=kind, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            a = dict(schema=contract['attestation_schema'], issuer=dict(verifier='test-external-verifier',
                verification_method='FIXTURE_NOT_PHYSICAL_EVIDENCE', runner_self_report=False),
                valid_until=(now + dt.timedelta(hours=1)).isoformat(), evidence=evidence,
                claims={key: True for key in contract['required_external_claims']}, pinned_environment={'fixture': True})
            path = parent / 'attestation.json'
            def check(value, pinned=None):
                raw = json.dumps(value).encode(); path.write_bytes(raw)
                return isolation.attestation_inputs(path, hashlib.sha256(raw).hexdigest(),
                    pinned or {'fixture': True}, contract, now)
            self.assertEqual(len(check(a)[1]), 2)
            for change in ('self_report', 'claim_false', 'evidence_tamper', 'expired', 'overlong', 'escape', 'unknown_field', 'missing_kind', 'pinned_drift'):
                candidate = copy.deepcopy(a)
                if change == 'self_report': candidate['issuer']['runner_self_report'] = True
                if change == 'claim_false': candidate['claims']['dedicated_host'] = False
                if change == 'evidence_tamper': candidate['evidence'][0]['sha256'] = '0' * 64
                if change == 'expired': candidate['valid_until'] = now.isoformat()
                if change == 'overlong': candidate['valid_until'] = (now + dt.timedelta(days=2)).isoformat()
                if change == 'escape': candidate['evidence'][0]['path'] = '../escape'
                if change == 'unknown_field': candidate['authorization'] = True
                if change == 'missing_kind': candidate['evidence'][0]['kind'] = 'other'
                if change == 'pinned_drift': candidate['pinned_environment'] = {'fixture': False}
                with self.subTest(change=change), self.assertRaises(RuntimeError): check(candidate)
            check(a)
            with self.assertRaisesRegex(RuntimeError, 'DIGEST_MISMATCH'):
                isolation.attestation_inputs(path, '0' * 64, {'fixture': True}, contract, now)

    def test_control_inputs_reject_symlinks_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); file = parent / 'input'; file.write_bytes(b'1234')
            with self.assertRaisesRegex(RuntimeError, 'BOUNDED_REGULAR'):
                isolation.regular_bytes(file, 3)
            try:
                (parent / 'link').symlink_to(file)
            except OSError:
                self.skipTest('native symlink privilege unavailable; other controls still run')
            with self.assertRaisesRegex(RuntimeError, 'SYMLINKED'):
                isolation.regular_bytes(parent / 'link')

    def test_full_boundary_accepts_only_fixed_condition_and_complete_telemetry(self):
        for condition in isolation.CONDITIONS:
            snapshot, pins = snapshot_fixture(condition)
            isolation.validate_snapshot(snapshot, pins, condition)
        modifications = [
            lambda s: s['host']['diskstats'].update(state='UNAVAILABLE'),
            lambda s: s['host']['diskstats']['value'].clear(),
            lambda s: s['host']['pressure']['io']['value'].pop('full'),
            lambda s: s['host']['pressure']['io']['value']['some'].update(avg10=float('nan')),
            lambda s: s['processes']['101']['io'].update(state='UNAVAILABLE'),
            lambda s: s['processes']['101']['io']['value'].pop('write_bytes'),
            lambda s: s['processes']['101']['affinity_cpus'].update(value=[0, 1]),
            lambda s: s['cgroups']['/cg']['cpu.max'].update(errno=errno.EACCES),
            lambda s: s['cgroups']['/cg']['cpu.stat']['value'].pop('usage_usec'),
            lambda s: s['cgroups']['/cg']['io.stat']['value'].clear(),
            lambda s: s['cgroups']['/cg']['io.pressure'].update(state='UNAVAILABLE'),
            lambda s: s['cgroups'].clear(),
        ]
        for i, change in enumerate(modifications):
            snapshot, pins = snapshot_fixture()
            change(snapshot)
            with self.subTest(control=i), self.assertRaises(RuntimeError):
                isolation.validate_snapshot(snapshot, pins, 'isolated')
        snapshot, pins = snapshot_fixture('io_interference')
        with self.assertRaisesRegex(RuntimeError, 'CONDITION_INTERFERER'):
            isolation.validate_snapshot(snapshot, pins, 'isolated')

    def test_missing_or_reset_counters_stop_instead_of_becoming_zero(self):
        before = {'host': {'counter': 10}}
        for after in ({'host': {'counter': 1}}, {'host': {}}):
            with self.assertRaisesRegex(RuntimeError, 'COUNTER_RESET_OR_FIELD_LOSS'):
                isolation.check_counter_continuity(benchmark, before, after)
        self.assertEqual(isolation.check_counter_continuity(benchmark, before, {'host': {'counter': 12}})
                         ['host']['counter']['delta'], 2)
        left = {'host': {'vmstat': {'state': 'OBSERVED', 'value': {'nr_free_pages': 20, 'pgpgout': 10}}}}
        right = {'host': {'vmstat': {'state': 'OBSERVED', 'value': {'nr_free_pages': 5, 'pgpgout': 12}}}}
        self.assertEqual(isolation.check_counter_continuity(benchmark, left, right)['host']['vmstat']['pgpgout']['delta'], 2)

    @unittest.skipUnless(sys.platform == 'linux', 'Dedicated Linux admission implementation')
    def test_static_admission_refuses_affinity_governor_queue_and_quota_gaps(self):
        contract = isolation.load_contract()
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); block = parent / 'block'; (block / 'queue').mkdir(parents=True)
            storage = {'state': 'OBSERVED', 'device': '8:1', 'mount': {'filesystem': 'ext4'},
                'block_device_sysfs': str(block), 'visible_backing_slaves': [],
                'backing_device_attribution': 'VISIBLE_BLOCK_DEVICE', 'block_size': 4096,
                'fragment_size': 4096, 'available_bytes': 2**31}
            targets = {'1': {'membership': {'state': 'OBSERVED'}, 'groups': [{'state': 'OBSERVED', 'version': 'v2',
                'mount': {'root': '/', 'mount_point': '/cg'}, 'visible_ancestors': ['/cg/job', '/cg']}]}}
            defect = [None]
            def observe(path, *args):
                path = str(path)
                if (defect[0] and path.endswith(defect[0])) or path in ('/cg/cpu.max', '/cg/io.max'):
                    return {'source': path, 'state': 'UNAVAILABLE', 'errno': errno.ENOENT}
                value = 'fixture'
                if path.endswith(('scaling_min_freq', 'scaling_max_freq')): value = '1000000'
                if path.endswith(('nr_requests', 'logical_block_size', 'physical_block_size')): value = '4096'
                if path.endswith(('read_ahead_kb', 'rotational')): value = '0'
                if path.endswith('write_cache'): value = 'write back'
                if path.endswith('cpu.max'): value = '200000 100000' if defect[0] == 'finite-quota' else 'max 100000'
                if path.endswith('core_id'): value = path.split('/cpu')[-1].split('/')[0]
                if path.endswith('physical_package_id'): value = '0'
                if path == '/proc/cpuinfo': value = 'model name: fixture CPU'
                return {'state': 'OBSERVED', 'source': path, 'value': value}
            with patch.object(os, 'sched_getaffinity', return_value={0, 1, 2, 3}) as affinity, \
                 patch.object(os, 'readlink', return_value='cgroup:[fixture]'), \
                 patch.object(benchmark, 'benchmark_observation', side_effect=observe), \
                 patch.object(benchmark, 'benchmark_storage_identity', return_value=storage), \
                 patch.object(benchmark, 'benchmark_telemetry_targets', return_value=targets), \
                 patch.object(benchmark, 'terminal_subject', return_value={'head': '1' * 40, 'tree': '2' * 40}):
                isolation.collect_static(benchmark, parent, contract)
                for value in ('scaling_governor', 'write_cache', 'finite-quota'):
                    defect[0] = value
                    with self.subTest(gap=value), self.assertRaises(RuntimeError):
                        isolation.collect_static(benchmark, parent, contract)
                defect[0] = None
                affinity.return_value = {0, 1, 2}
                with self.assertRaisesRegex(RuntimeError, 'FOUR_FIXED_CPU_SLOTS'):
                    isolation.collect_static(benchmark, parent, contract)

    def test_zero_trials_on_failed_isolation_admission_and_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'result'
            args = SimpleNamespace(output=output, isolation_attestation=Path(directory) / 'missing',
                isolation_attestation_sha256='0' * 64, expected_head='1' * 40, expected_tree='2' * 40)
            with patch.object(isolation, 'IsolatedScaleControl', side_effect=RuntimeError('DEDICATED_CARRIER_UNVERIFIED')), \
                 patch.object(benchmark, 'comparable_scale_benchmark') as engine, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(isolation.run_isolated(benchmark, None, args), 2)
                engine.assert_not_called()
            result = json.loads((output / 'RECEIPT.json').read_text())
            self.assertEqual(result['retained_trial_receipts'], [])
            self.assertFalse(result['runner_independent_scaling_proved'])
            frozen = (output / 'RECEIPT.json').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'NO_RESET_OR_OVERWRITE'):
                isolation.run_isolated(benchmark, None, args)
            self.assertEqual((output / 'RECEIPT.json').read_bytes(), frozen)

    @unittest.skipUnless(sys.platform == 'linux', 'Linux-only fsync lease control')
    def test_create_only_measurement_lease_survives_partial_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            control = isolation.IsolatedScaleControl.__new__(isolation.IsolatedScaleControl)
            control.output = Path(directory) / 'first'
            control.expected_subject = {'head': '1' * 40, 'tree': '2' * 40}
            control.acquire_budget()
            lease = Path(control.budget_lease['path'])
            raw = lease.read_bytes()
            control.output = Path(directory) / 'second'
            with self.assertRaisesRegex(RuntimeError, 'BUDGET_ALREADY_ACQUIRED'):
                control.acquire_budget()
            self.assertEqual(lease.read_bytes(), raw)

    @unittest.skipUnless(sys.platform == 'linux', 'Native Linux I/O primitive control')
    def test_native_fixed_calibration_and_interferer_error_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory); data = parent / 'data'; receipt = parent / 'receipt.json'
            cpu = min(os.sched_getaffinity(0))
            command = [sys.executable, '-B', str(ROOT / 'tools/qikvrt_firefox_windows_witness.py'),
                       '--isolated-io-child', str(data), str(receipt), str(cpu), 'calibration']
            child = subprocess.run(command, capture_output=True, timeout=20)
            self.assertEqual(child.returncode, 0, child.stderr)
            result = json.loads(receipt.read_text())
            self.assertEqual(result['state'], 'PASS')
            self.assertEqual(len(result['operations']), 32)
            self.assertEqual(sum(row['bytes'] for row in result['operations']), 32 * 65536)
            self.assertTrue(all(row['start_ns'] <= row['file_fsync_start_ns'] < row['end_ns'] for row in result['operations']))
            self.assertTrue(all(row['thread_cpu_seconds'] >= 0 for row in result['operations']))
            self.assertEqual(result['affinity_cpus'], [cpu])
            # The interferer never opens/reuses another file, including on failure.
            frozen = data.read_bytes()
            command[5] = str(parent / 'failed-receipt.json')
            child = subprocess.run(command, capture_output=True, timeout=20)
            self.assertEqual(child.returncode, 2)
            self.assertEqual(json.loads((parent / 'failed-receipt.json').read_text())['state'], 'HOLD')
            self.assertEqual(data.read_bytes(), frozen)

    def test_failed_trial_keeps_raw_boundary_and_worker_operations(self):
        with tempfile.TemporaryDirectory() as directory:
            control = isolation.IsolatedScaleControl.__new__(isolation.IsolatedScaleControl)
            control.output = Path(directory)
            (control.output / 'measurements').mkdir()
            control.active_raw = {'run_id': 'failed', 'state': 'INCOMPLETE'}
            control.record('BEFORE_EXECUTION', observability_before={'fixture': 'raw'})
            control.record('AFTER_EXECUTION', worker_metrics_after=[{'persist_intervals': [1]}])
            raw = json.loads((control.output / 'measurements/failed.json').read_text())
            self.assertEqual(raw['observability_before'], {'fixture': 'raw'})
            self.assertEqual(raw['worker_metrics_after'][0]['persist_intervals'], [1])
            self.assertEqual(raw['state'], 'INCOMPLETE')

    def test_receipt_failure_still_terminates_interferer(self):
        control = isolation.IsolatedScaleControl.__new__(isolation.IsolatedScaleControl)
        child = Mock()
        child.poll.return_value = None
        control.child = child
        control.flush_partial = Mock(side_effect=OSError('controlled receipt failure'))
        with self.assertRaises(OSError): control.close()
        child.kill.assert_called_once()
        child.communicate.assert_called_once_with(timeout=8)
        self.assertIsNone(control.child)

    @unittest.skipUnless(sys.platform == 'linux', 'Native bounded child lifecycle')
    def test_real_interferer_ready_stop_window_accounting_and_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory); (output / 'controls').mkdir()
            storage = benchmark.benchmark_storage_identity(output)
            cpu = min(os.sched_getaffinity(0))
            control = isolation.IsolatedScaleControl.__new__(isolation.IsolatedScaleControl)
            control.b, control.output, control.contract = benchmark, output, isolation.load_contract()
            control.pins = {'affinity_cpus': [cpu], 'storage': storage, 'cgroup_policy': {'fixture': True}}
            control.child = None
            control.active = {'run_id': 'child-lifecycle-fixture', 'condition': 'io_interference'}
            try:
                with patch.object(isolation, 'cgroup_pins', return_value={'fixture': True}):
                    targets = control.before_execution(benchmark.benchmark_telemetry_targets([]), [storage])
                self.assertEqual(targets[str(control.child.pid)]['role'], 'INTERFERER')
                before = benchmark.benchmark_host_snapshot(targets)
                start = time.perf_counter_ns()
                time.sleep(.06)  # Child accounting fixture; no benchmark requests or performance claim.
                end = time.perf_counter_ns()
                after = benchmark.benchmark_host_snapshot(targets)
                result = control.after_execution(before, after, start, end)
                self.assertGreaterEqual(result['interferer']['complete_operations_in_execution'], 2)
                self.assertGreater(result['interferer']['bytes_in_execution'], 0)
                self.assertTrue((output / result['interferer']['path']).is_file())
                self.assertIsNone(control.child)
                self.assertFalse(control.data.exists())
            finally:
                control.close()

    def test_hosted_workflow_has_no_performance_command_and_dedicated_job_is_dispatch_only(self):
        workflow = (ROOT / '.github/workflows/qikvrt_personal_firefox_capability_boundary.yml').read_text()
        hosted = workflow.split('  linux-comparable-scale:', 1)[1].split('  linux-isolated-control:', 1)[0]
        self.assertNotIn('--comparable-scale-benchmark', workflow)
        self.assertNotIn('--isolated-scale-benchmark', hosted)
        dedicated = workflow.split('  linux-isolated-control:', 1)[1].split('  windows-witness:', 1)[0]
        self.assertIn("github.event_name == 'workflow_dispatch'", dedicated)
        self.assertIn('runs-on: [self-hosted, linux, x64, qikvrt-isolated-scale]', dedicated)
        self.assertIn('--expected-tree', dedicated)
        self.assertNotIn('actions/setup-python', dedicated)
        self.assertNotIn('private-rings', dedicated)

    @unittest.skipUnless(sys.platform == 'linux', 'Actual HTTP process engine is Linux-only')
    def test_existing_engine_reuses_one_template_for_both_conditions(self):
        sys.path.insert(0, str(ROOT / 'src'))
        import qikvrt_effect_ack_http_terminal as terminal
        class FixtureControl:
            """Lifecycle plumbing only: explicitly NO isolation or interferer."""
            def plan(self, *args): return isolation.trial_plan()
            def before_trial(self, run_id, condition): self.condition = condition
            def before_execution(self, targets, stores): return targets
            def record(self, *args, **values): pass
            def write_receipt(self, path, value): isolation.durable_json(path, value)
            def boundary(self, snapshot): return {'state': 'MOCK_ADMISSION_FIXTURE_ONLY'}
            def after_execution(self, *args): return {'state': 'FIXTURE_NO_PHYSICAL_CONTROL'}
            def close(self): pass
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            result = benchmark.comparable_scale_benchmark(terminal, Path(directory) / 'rings',
                ROOT / 'canonical/QIKVRT_STANDPOINT_SIGNATURE_V1.bin', repetitions=6, workload=4,
                preload_per_origin=1, control=FixtureControl())
            self.assertEqual(len(result['measurements']), 36)
            self.assertEqual(set(result['comparisons_to_one_process']), set(isolation.CONDITIONS))
            self.assertEqual(len({tuple(row['initial_snapshot_sha256']) for row in result['measurements']}), 1)
            for row in result['measurements']:
                self.assertEqual((row['effects'], row['referenced_records']), (8, 16))
                self.assertEqual(row['invariants']['replay_refusals'], 8)
                self.assertEqual(row['invariants']['concurrent_replay_statuses'], [409] * 4)
            self.assertFalse(result['variance_observability']['runner_independent_scaling_proved'])


if __name__ == '__main__':
    unittest.main()
