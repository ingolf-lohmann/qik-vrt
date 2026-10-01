# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.qikvrt_effect_ack_clock_readback import verify_readback

ROOT = Path(__file__).resolve().parents[1]


class ClockCarrierTests(unittest.TestCase):
    def test_rtl_simulation_and_synthesis(self):
        cache = Path(os.environ.get('QIKVRT_TOOLCHAIN_CACHE', ROOT / '.qikvrt/toolchains'))
        ghdl = cache / 'ghdl/6.0.0/ubuntu24.04-x86_64/ghdl-mcode-6.0.0-ubuntu24.04-x86_64/bin/ghdl'
        self.assertTrue(ghdl.is_file(), 'BLOCK: provision locked GHDL using bootstrap-runtime --profile clock --install --accept-third-party')
        with tempfile.TemporaryDirectory(prefix='qikvrt-clock-') as directory:
            build = Path(directory)
            def run(command, **kwargs):
                return subprocess.run(command, cwd=build, check=True, timeout=180, **kwargs)
            # Final-path verification precedes use, on cold and warm runs alike.
            run(['sh', str(ROOT / 'tools/bootstrap-runtime.sh'), '--profile', 'clock', '--check-only'])
            run([os.environ.get('CC', 'cc'), '-std=c90', '-pedantic', '-Wall', '-Wextra', '-Werror',
                 '-I' + str(ROOT / 'include'), str(ROOT / 'src/effect_ack_core.c'),
                 str(ROOT / 'tests/test_effect_ack_clock_vectors.c'), '-o', str(build / 'vectors')])
            with (build / 'vectors.txt').open('w') as output:
                run([str(build / 'vectors')], stdout=output)
            sources = [ROOT / 'rtl' / name for name in (
                'effect_ack_clock_pkg.vhd', 'effect_ack_coverage_witness.vhd', 'effect_ack_clock_carrier.vhd',
                'effect_ack_board_top.vhd')]
            run([str(ghdl), '-a', '--std=08', *map(str, sources), str(ROOT / 'tests/effect_ack_clock_tb.vhd')])
            run([str(ghdl), '-e', '--std=08', 'effect_ack_clock_tb'])
            run([str(ghdl), '-r', '--std=08', 'effect_ack_clock_tb', '--assert-level=error'])
            result = verify_readback(json.loads((build / 'readback.json').read_text()),
                                     nonce=99, epoch=7, expected_count=2569)
            self.assertTrue(result['telemetry_consistent'])
            self.assertFalse(result['physical_clock_verified'])
            with (build / 'synthesized.vhd').open('w') as output:
                run([str(ghdl), '--synth', '--std=08', 'effect_ack_clock_carrier'], stdout=output)
            self.assertGreater((build / 'synthesized.vhd').stat().st_size, 1000)
            for bound in ('false', 'true'):
                with (build / ('board_top_' + bound + '.vhd')).open('w') as output:
                    run([str(ghdl), '--synth', '--std=08', '-gBOARD_BINDING_VALIDATED=' + bound,
                         'effect_ack_board_top'], stdout=output)
                self.assertGreater((build / ('board_top_' + bound + '.vhd')).stat().st_size, 1000)
            with (build / 'synthesized_small.vhd').open('w') as output:
                run([str(ghdl), '--synth', '--std=08', '-gCOUNTER_BITS=2',
                     'effect_ack_clock_carrier'], stdout=output)
            small = build / 'synthesized_small.vhd'
            small.write_text(small.read_text().replace('effect_ack_clock_carrier', 'effect_ack_clock_carrier_small'))
            netlist_tb = build / 'netlist_tb.vhd'
            netlist_tb.write_text((ROOT / 'tests/effect_ack_clock_tb.vhd').read_text().replace(
                'tiny : entity work.effect_ack_clock_carrier ',
                'tiny : entity work.effect_ack_clock_carrier_small '))
            # Reexecute the same edge/fault controls on the synthesized netlist.
            # Synthesis specializes generics, so use distinct 64/2-bit netlists.
            synth = build / 'netlist'; synth.mkdir()
            flags = ['--std=08', '--workdir=' + str(synth)]
            run([str(ghdl), '-a', *flags, str(sources[0]), str(sources[1]),
                 str(build / 'synthesized.vhd'), str(small), str(sources[3]), str(netlist_tb)])
            run([str(ghdl), '-e', *flags, 'effect_ack_clock_tb'])
            run([str(ghdl), '-r', *flags, 'effect_ack_clock_tb', '--assert-level=error'])

    def test_bootstrap_rejects_bad_archive_and_symlink_cache(self):
        with tempfile.TemporaryDirectory(prefix='qikvrt-ghdl-negative-') as directory:
            root = Path(directory); bad = root / 'bad.tar.gz'; bad.write_bytes(b'not locked GHDL')
            cache = root / 'cache'; cache.mkdir()
            command = ['sh', str(ROOT / 'tools/bootstrap-runtime.sh'), '--profile', 'clock',
                       '--install', '--accept-third-party', '--cache-dir', str(cache)]
            environment = dict(os.environ, QIKVRT_GHDL_ARCHIVE=str(bad))
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertIn('archive hash mismatch', result.stderr)
            self.assertFalse((cache / 'ghdl/6.0.0/ubuntu24.04-x86_64').exists())
            self.assertFalse(list(cache.glob('ghdl/6.0.0/.install-*')))
            link = root / 'linked'; link.symlink_to(cache, target_is_directory=True)
            command[-1] = str(link)
            result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 1)
            self.assertIn('symlink', result.stderr)

    def telemetry(self):
        return dict(schema='qikvrt_effect_ack_clock_readback_v1', nonce=99, epoch=7,
                    evaluated=12, witnessed=12, fault=0, witness_fault=0, reset_seen=0,
                    state=2, snapshot_epoch=7, snapshot_cycle=11)

    def verify(self, value):
        return verify_readback(value, nonce=99, epoch=7, expected_count=12)

    def test_coherent_done_telemetry_cannot_claim_physical_effect(self):
        result = self.verify(self.telemetry())
        self.assertTrue(result['telemetry_consistent'])
        for key in ('ordinary_release', 'physical_clock_verified', 'effect_ack_done'):
            self.assertFalse(result[key])

    def test_fail_closed_readback_controls(self):
        for key, val in [('nonce', 98), ('epoch', 8), ('evaluated', 11), ('witnessed', 11),
                         ('fault', 1), ('witness_fault', 1), ('reset_seen', 1), ('state', 5),
                         ('snapshot_cycle', 10), ('snapshot_epoch', 8), ('evaluated', True),
                         ('nonce', -1), ('witnessed', 2**64)]:
            with self.subTest(key=key, value=val):
                value = self.telemetry(); value[key] = val
                with self.assertRaises(ValueError): self.verify(value)
        for value in [None, {}, dict(self.telemetry(), board_verified=True)]:
            with self.assertRaises(ValueError): self.verify(value)

    def test_cli_duplicate_keys_and_physical_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'readback.json'
            command = ['python3', '-B', str(ROOT / 'tools/qikvrt_effect_ack_clock_readback.py'),
                       str(path), '--nonce', '99', '--epoch', '7', '--expected-count', '12']
            path.write_text(json.dumps(self.telemetry()))
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 20)
            path.write_text(json.dumps(self.telemetry())[:-1] + ', "nonce":99}')
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['state'], 'BLOCK')


if __name__ == '__main__':
    unittest.main()
