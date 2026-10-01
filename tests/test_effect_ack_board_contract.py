# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Synthetic contract controls. TEST_ONLY identifiers are never a board profile."""
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import qikvrt_effect_ack_clock_readback as clock

NOW = dt.datetime(2026, 10, 1, 18, 0, tzinfo=dt.timezone.utc)
SUBJECT = dict(repository='ingolf-lohmann/qik-vrt', pr=430, head='1' * 40, tree='2' * 40)


def fixture():
    return dict(schema='qikvrt_effect_ack_board_profile_v1', subject=dict(SUBJECT),
                observed_at='2026-10-01T17:59:00Z',
                board=dict(id='TEST_ONLY_BOARD', revision='TEST_ONLY_REV', serial='TEST_ONLY_SERIAL', source_sha256='3' * 64),
                fpga=dict(vendor='AMD_XILINX', part='TEST_ONLY_PART', idcode='TEST_ONLY_IDCODE'),
                clock=dict(port='clk', period_ns=10, source_id='TEST_ONLY_CLOCK'),
                pins={p: dict(package_pin='TEST_PIN_' + str(i), io_standard='TEST_ONLY_IO')
                      for i, p in enumerate(clock.ports())},
                timing=dict(input_min_ns=0, input_max_ns=2, output_min_ns=0, output_max_ns=2, clock_uncertainty_ns=0.1),
                toolchain=dict(name='vivado', version='TEST_ONLY_VERSION', executable_sha256='4' * 64, provenance_sha256='5' * 64),
                interfaces=dict(input_domain='SYNCHRONOUS_TO_CLK', **{x: 'OPEN' for x in clock.OPEN_OBLIGATIONS}))


class BoardContractTests(unittest.TestCase):
    def prepare(self, profile):
        return clock.prepare_board(profile, subject=SUBJECT, nonce=99, now=NOW)

    def flags_false(self, value):
        for key in ('physical_clock_verified', 'bitstream_programmed', 'programmer_readback_observed',
                    'EFFECT_ACK_DONE', 'effect_ack_done', 'ordinary_release'):
            self.assertIs(value[key], False)
        self.assertEqual(value['external_effect'], 'NONE')

    def test_missing_board_profile_precise_blocker(self):
        result = self.prepare(None)
        self.assertEqual(result['state'], 'BOARD_BINDING_REQUIRED')
        self.assertNotIn('plan', result)
        self.flags_false(result)

    def test_complete_profile_emits_all_pins_and_bounded_build_interface(self):
        result = self.prepare(fixture())
        self.assertEqual(result['state'], 'BUILD_INPUTS_READY')
        self.flags_false(result)
        plan = result['plan']; xdc = plan['constraints']['board.xdc']
        self.assertEqual(xdc.count('set_property PACKAGE_PIN'), 804)
        self.assertEqual(xdc.count('set_property IOSTANDARD'), 804)
        self.assertIn('create_clock -name processor_clock -period 10 [get_ports {clk}]', xdc)
        self.assertIn('set_input_delay -min 0', xdc)
        self.assertIn('set_output_delay -max 2', xdc)
        self.assertNotIn('false_path', xdc)
        self.assertFalse(plan['programming_authorized'])
        self.assertFalse(plan['tool_execution_authorized'])
        self.assertEqual(plan['sources']['rtl/effect_ack_board_top.vhd'],
                         hashlib.sha256((clock.ROOT / 'rtl/effect_ack_board_top.vhd').read_bytes()).hexdigest())
        self.assertEqual(result, self.prepare(fixture()))

    def test_intel_constraints_preserve_part_pins_and_timing(self):
        profile = fixture(); profile['fpga']['vendor'] = 'INTEL'; profile['toolchain']['name'] = 'quartus'
        profile['pins']['clk']['io_standard'] = 'TEST_ONLY_IO WITH SPACE'
        constraints = self.prepare(profile)['plan']['constraints']
        self.assertIn('DEVICE TEST_ONLY_PART', constraints['board.qsf'])
        self.assertEqual(constraints['board.qsf'].count('set_location_assignment'), 804)
        self.assertIn('set_clock_uncertainty', constraints['board.sdc'])
        self.assertIn('IO_STANDARD {TEST_ONLY_IO WITH SPACE}', constraints['board.qsf'])

    def test_every_missing_binding_fails_closed(self):
        for key in fixture():
            with self.subTest(key=key):
                profile = fixture(); del profile[key]
                with self.assertRaises(ValueError): self.prepare(profile)
        for section in ('board', 'fpga', 'clock', 'timing', 'toolchain', 'interfaces'):
            for key in fixture()[section]:
                with self.subTest(section=section, key=key):
                    profile = fixture(); del profile[section][key]
                    with self.assertRaises(ValueError): self.prepare(profile)
        for profile in (None, {}, []):
            if profile is not None:
                with self.assertRaises(ValueError): self.prepare(profile)

    def test_stale_subject_time_and_forged_physical_flags(self):
        for key, value in [('head', 'a' * 40), ('tree', 'b' * 40), ('pr', 431), ('repository', 'Goldkelch/qik-vrt')]:
            profile = fixture(); profile['subject'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.prepare(profile)
        for value in ('2026-09-29T18:00:00Z', '2026-10-01T18:00:01Z', '2026-10-01T18:00:00', '2026-10-01Z'):
            profile = fixture(); profile['observed_at'] = value
            with self.subTest(value=value), self.assertRaises(ValueError): self.prepare(profile)
        profile = fixture(); profile['physical_clock_verified'] = True
        with self.assertRaises(ValueError): self.prepare(profile)
        for key in clock.OPEN_OBLIGATIONS:
            profile = fixture(); profile['interfaces'][key] = 'VERIFIED'
            with self.subTest(key=key), self.assertRaises(ValueError): self.prepare(profile)

    def test_contradictory_pin_clock_timing_and_tool_bindings(self):
        changes = [('fpga', 'part', 'OPEN'), ('fpga', 'vendor', 'INTEL'), ('clock', 'port', 'other_clk'),
                   ('clock', 'period_ns', 0), ('clock', 'period_ns', True), ('clock', 'period_ns', float('nan')),
                   ('clock', 'period_ns', 10**1000),
                   ('timing', 'input_min_ns', 3), ('timing', 'output_min_ns', 3),
                   ('timing', 'clock_uncertainty_ns', -1), ('toolchain', 'executable_sha256', 'bad'),
                   ('interfaces', 'input_domain', 'ASYNCHRONOUS')]
        for section, key, value in changes:
            profile = fixture(); profile[section][key] = value
            with self.subTest(section=section, key=key, value=value), self.assertRaises(ValueError): self.prepare(profile)
        for mutation in ('missing', 'extra', 'duplicate', 'injection', 'io_missing'):
            profile = fixture(); pins = profile['pins']
            if mutation == 'missing': del pins['clk']
            if mutation == 'extra': pins['unknown'] = dict(pins['clk'])
            if mutation == 'duplicate': pins['admit'] = dict(pins['clk'])
            if mutation == 'injection': pins['clk']['package_pin'] = 'P1;exec_bad'
            if mutation == 'io_missing': del pins['clk']['io_standard']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): self.prepare(profile)

    def run_fixture(self, root):
        profile = fixture(); prepared = self.prepare(profile)
        artifacts = {}
        for name in clock.ARTIFACT_NAMES:
            data = b'TEST_ONLY_CONFIGURATION' if name in ('configuration_image', 'configuration_readback') else ('TEST_ONLY_' + name).encode()
            (root / name).write_bytes(data)
            artifacts[name] = dict(path=name, sha256=hashlib.sha256(data).hexdigest())
        report = dict(schema='qikvrt_effect_ack_board_run_v1', subject=dict(SUBJECT),
                      profile_sha256=prepared['plan']['profile_sha256'], plan_sha256=prepared['plan_sha256'],
                      nonce=99, run_id='TEST_ONLY_RUN', started_at='2026-10-01T17:59:10Z', observed_at='2026-10-01T18:00:00Z',
                      board_serial=profile['board']['serial'], fpga_idcode=profile['fpga']['idcode'], artifacts=artifacts,
                      sta=dict(part=profile['fpga']['part'], clock_period_ns=10, placement_route_completed=True,
                               unconstrained_paths=0, setup_slack_ns=1, hold_slack_ns=1, recovery_slack_ns=1, removal_slack_ns=1),
                      programmer=dict(programmed=True, readback_observed=True, tool='TEST_ONLY_PROGRAMMER', version='TEST_ONLY_VERSION',
                                      executable_sha256='6' * 64, configuration_image_sha256=artifacts['configuration_image']['sha256'],
                                      readback_configuration_sha256=artifacts['configuration_readback']['sha256']),
                      clock_readback=dict(schema='qikvrt_effect_ack_clock_readback_v1', nonce=99, epoch=7,
                                          evaluated=12, witnessed=12, fault=0, witness_fault=0, reset_seen=0,
                                          state=2, snapshot_epoch=7, snapshot_cycle=11))
        return profile, report

    def verify(self, profile, report, root):
        return clock.verify_board_run(profile, report, subject=SUBJECT, nonce=99, epoch=7,
                                      expected_count=12, now=NOW, artifacts_root=root)

    def test_consistent_synthetic_report_never_attests_a_board(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); profile, report = self.run_fixture(root)
            result = self.verify(profile, report, root)
            self.assertEqual(result['state'], 'HOLD_AUTHENTICATED_BOARD_RUN_REQUIRED')
            self.assertTrue(result['evidence_contract_consistent'])
            self.flags_false(result)
            # Changing source bytes invalidates the build binding, even at the same subject.
            with tempfile.TemporaryDirectory() as source_dir:
                source_root = Path(source_dir)
                for path in clock.SOURCES:
                    target = source_root / path; target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((clock.ROOT / path).read_bytes() + b'\n-- changed\n')
                with self.assertRaisesRegex(ValueError, 'build binding'):
                    clock.verify_board_run(profile, report, subject=SUBJECT, nonce=99, epoch=7,
                                           expected_count=12, now=NOW, artifacts_root=root, root=source_root)

    def test_run_rejects_missing_stale_or_substituted_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); profile, base = self.run_fixture(root)
            changes = [('nonce', 98), ('nonce', True), ('profile_sha256', 'a' * 64), ('plan_sha256', 'a' * 64),
                       ('board_serial', 'WRONG_BOARD'), ('fpga_idcode', 'WRONG_PART'),
                       ('observed_at', '2026-10-01T17:54:59Z'), ('observed_at', '2026-10-01T18:00:01Z'),
                       ('started_at', '2026-10-01T17:58:59Z')]
            for key, value in changes:
                report = copy.deepcopy(base); report[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError): self.verify(profile, report, root)
            for key in base:
                report = copy.deepcopy(base); del report[key]
                with self.subTest(missing=key), self.assertRaises(ValueError): self.verify(profile, report, root)
            report = copy.deepcopy(base); report['physical_clock_verified'] = True
            with self.assertRaises(ValueError): self.verify(profile, report, root)

    def test_sta_programmer_and_clock_negative_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); profile, base = self.run_fixture(root)
            for section, key, value in [('sta', 'part', 'WRONG'), ('sta', 'clock_period_ns', 20),
                ('sta', 'clock_period_ns', True), ('sta', 'placement_route_completed', False),
                ('sta', 'unconstrained_paths', 1), ('sta', 'unconstrained_paths', False),
                *[('sta', x, -0.1) for x in ('setup_slack_ns', 'hold_slack_ns', 'recovery_slack_ns', 'removal_slack_ns')],
                ('programmer', 'programmed', False), ('programmer', 'readback_observed', False),
                ('programmer', 'configuration_image_sha256', 'a' * 64), ('programmer', 'readback_configuration_sha256', 'b' * 64),
                ('clock_readback', 'witnessed', 11), ('clock_readback', 'fault', 1), ('clock_readback', 'nonce', 98),
                ('clock_readback', 'epoch', 8), ('clock_readback', 'snapshot_cycle', 10)]:
                report = copy.deepcopy(base); report[section][key] = value
                with self.subTest(section=section, key=key), self.assertRaises(ValueError): self.verify(profile, report, root)

    def test_exact_artifacts_confinement_and_configuration_readback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); profile, base = self.run_fixture(root)
            for value in ('../escape', '/tmp/escape', 'sta/../escape'):
                report = copy.deepcopy(base); report['artifacts']['sta']['path'] = value
                with self.assertRaises(ValueError): self.verify(profile, report, root)
            for name in clock.ARTIFACT_NAMES:
                original = (root / name).read_bytes(); (root / name).write_bytes(b'TAMPERED')
                with self.subTest(name=name), self.assertRaises(ValueError): self.verify(profile, base, root)
                (root / name).write_bytes(original)
            (root / 'configuration_readback').write_bytes(b'DIFFERENT_READBACK')
            report = copy.deepcopy(base)
            new_sha = hashlib.sha256(b'DIFFERENT_READBACK').hexdigest()
            report['artifacts']['configuration_readback']['sha256'] = new_sha
            report['programmer']['readback_configuration_sha256'] = new_sha
            with self.assertRaisesRegex(ValueError, 'readback mismatch'): self.verify(profile, report, root)
            link = root / 'link'; link.symlink_to(root / 'sta')
            report = copy.deepcopy(base); report['artifacts']['sta']['path'] = 'link'
            with self.assertRaisesRegex(ValueError, 'symlinks'): self.verify(profile, report, root)
            report = copy.deepcopy(base); report['artifacts']['sta'] = dict(report['artifacts']['placement_route'])
            with self.assertRaisesRegex(ValueError, 'independent artifact paths'): self.verify(profile, report, root)

    def test_json_duplicate_nonfinite_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'profile.json'
            for data in ('{"schema":1,"schema":2}', '{"period":NaN}', '{"period":Infinity}'):
                path.write_text(data)
                with self.assertRaises(ValueError): clock.load_json(path)
            path.write_text(json.dumps(fixture()))
            link = root / 'link'; link.symlink_to(path)
            with self.assertRaises(ValueError): clock.load_json(link)

    def test_cli_rejects_checkout_subject_substitution(self):
        result = subprocess.run(['python3', '-B', str(clock.ROOT / 'tools/qikvrt_effect_ack_clock_readback.py'),
                                 'prepare-board', '--expect-head', 'f' * 40, '--expect-tree', 'e' * 40, '--nonce', '99'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout); self.flags_false(value)
        self.assertEqual(value['state'], 'BLOCK_BOARD_EVIDENCE')


if __name__ == '__main__':
    unittest.main()
