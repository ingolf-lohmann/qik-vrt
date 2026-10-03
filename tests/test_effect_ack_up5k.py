# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Documentary profile negatives and source/netlist transport controls."""
import copy
import datetime as dt
import hashlib
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools import qikvrt_effect_ack_clock_readback as clock

SUBJECT = dict(repository='ingolf-lohmann/qik-vrt', pr=430, head='1'*40, tree='2'*40)
# Synthetic interface contract budget, not measured PCB/controller timing.
BUDGET = dict(input_min_ns=0, input_max_ns=4, output_min_ns=0,
              output_max_ns=4, clock_uncertainty_ns=0.25)


class Up5kTests(unittest.TestCase):
    def profile(self):
        return clock.load_json(clock.ROOT / clock.DOCUMENTARY_PROFILE)

    def prepare(self, profile=None, timing=BUDGET):
        return clock.prepare_board(self.profile() if profile is None else profile, subject=SUBJECT, nonce=99,
            now=dt.datetime.now(dt.timezone.utc), timing=timing)

    def test_documentary_constraints_bind_ten_real_pins_and_preserve_holds(self):
        profile = self.profile(); result = self.prepare(); plan = result['plan']
        self.assertEqual(result['state'], 'HOLD_PRIMARY_ARCHIVE_CROSSCHECK_REQUIRED')
        for key in ('physical_authentication', 'physical_clock_verified', 'bitstream_programmed',
                    'programmer_readback_observed', 'EFFECT_ACK_DONE', 'ordinary_release'):
            self.assertIs(result[key], False)
        self.assertEqual(result['external_effect'], 'NONE')
        self.assertEqual(plan['external_signal_bits'], 10)
        self.assertEqual(plan['part'], 'iCE40UP5K-SG48I')
        pdc = plan['constraints']['board.pdc']; sdc = plan['constraints']['board.sdc']
        self.assertEqual(pdc.count('ldc_set_location'), 10)
        self.assertEqual(pdc.count('IO_TYPE=LVCMOS33'), 10)
        self.assertIn('-site {35} [get_ports {clk}]', pdc)
        for bank in ('0','1','2'): self.assertIn('ldc_set_vcc -bank '+bank+' 3.3', pdc)
        self.assertIn('ldc_set_vcc -core 1.2', pdc)
        self.assertIn('83.33333333333333 [get_ports {clk}]', sdc)
        self.assertIn('set_input_delay -min', sdc); self.assertIn('set_output_delay -max', sdc)
        self.assertNotIn('false_path', sdc); self.assertNotIn('multicycle', sdc)
        self.assertEqual(profile['fpga']['package'], 'SG48')
        self.assertEqual(len(profile['package_pins']), 48)
        self.assertEqual(len({x['package_pin'] for x in profile['package_pins']}), 48)
        self.assertEqual(sum(p['role']=='GPIO_HEADER_PAD' for p in profile['package_pins']), 31)
        self.assertFalse(plan['timing_budget_measured'])
        self.assertFalse(plan['programming_authorized']); self.assertFalse(plan['tool_execution_authorized'])
        self.assertFalse(plan['vendor_build_executed'])
        self.assertFalse(plan['static_generic_is_physical_attestation'])
        script = plan['generated_files']['build_radiant.tcl']
        self.assertIn('prj_set_top_module effect_ack_board_top', script)
        self.assertIn('prj_run PAR -impl impl_1', script)
        self.assertIn('error {PAR failed}', script)
        self.assertNotIn('prj_run export', script.lower())
        self.assertNotIn('program ', script.lower())
        for path, content in plan['generated_files'].items():
            self.assertEqual(plan['generated_sha256'][path], hashlib.sha256(content.encode()).hexdigest())
        self.assertEqual(plan['sources']['rtl/effect_ack_board_top.vhd'],
                         hashlib.sha256((clock.ROOT/'rtl/effect_ack_board_top.vhd').read_bytes()).hexdigest())
        for port, binding in profile['adapter']['ports'].items():
            pin = next(p for p in profile['package_pins'] if p['package_pin']==binding['package_pin'])
            self.assertEqual(pin['io_standard'], binding['io_standard'])
            self.assertEqual(pin['role'], 'OSCILLATOR_INPUT_ONLY' if port=='clk' else 'GPIO_HEADER_PAD')
            self.assertFalse(pin['shared_with_switch'])

    def test_source_or_pin_substitution_and_forged_authentication_rejected(self):
        base = self.profile()
        mutations = [
            ('board','documented_revision','B'), ('fpga','package','UWG30'),
            ('fpga','selected_build_part','iCE40UP3K-SG48I'), ('clock','frequency_hz',48000000),
            ('electrical','selected_io_standard','LVCMOS18'),
            ('vendor_path','configuration','NVCM'), ('sources','guide',{}),
        ]
        for section, key, val in mutations:
            value = copy.deepcopy(base); value[section][key] = val
            with self.subTest(section=section, key=key), self.assertRaises(ValueError): self.prepare(value)
        # Clock, configuration, RGB and supply pins cannot be silently repurposed.
        for pin in ('35','14','15','16','17','7','8','39','40','41','5','33'):
            value = copy.deepcopy(base); value['adapter']['ports']['serial_out']['package_pin'] = pin
            with self.subTest(pin=pin), self.assertRaises(ValueError): self.prepare(value)
        for flag in ('physical_authentication','physical_clock_verified','EFFECT_ACK_DONE',
                     'source_archive_crosscheck_complete','programmer_readback_observed'):
            value = copy.deepcopy(base); value[flag] = True
            with self.subTest(flag=flag), self.assertRaises(ValueError): self.prepare(value)
        value = copy.deepcopy(base); value['adapter']['ports']['clk']['package_pin'] = '35;exec_bad'
        with self.assertRaises(ValueError): self.prepare(value)

    def test_unmeasured_or_invalid_timing_never_becomes_physical_evidence(self):
        result = self.prepare(timing=None)
        self.assertEqual(result['state'], 'HOLD_INTERFACE_TIMING_BUDGET_REQUIRED')
        self.assertNotIn('plan', result)
        for key, value in [('input_min_ns',5), ('output_min_ns',5), ('clock_uncertainty_ns',-1),
                           ('input_max_ns',84), ('input_max_ns',True), ('input_max_ns',float('nan'))]:
            timing = dict(BUDGET); timing[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.prepare(timing=timing)
        with self.assertRaisesRegex(ValueError, 'authenticated board identity'):
            clock.verify_board_run(self.profile(), {}, subject=SUBJECT, nonce=99, epoch=7,
                expected_count=1, now=dt.datetime.now(dt.timezone.utc), artifacts_root=clock.ROOT)

    def test_vendor_verilog_lowering_has_exact_documented_scalar_ports(self):
        cache = Path(os.environ.get('QIKVRT_TOOLCHAIN_CACHE', clock.ROOT/'.qikvrt/toolchains'))
        ghdl = cache/'ghdl/6.0.0/ubuntu24.04-x86_64/ghdl-mcode-6.0.0-ubuntu24.04-x86_64/bin/ghdl'
        self.assertTrue(ghdl.is_file(), 'provision locked GHDL first')
        with tempfile.TemporaryDirectory(prefix='qikvrt-up5k-') as directory:
            build = Path(directory)
            def run(command, **kwargs):
                return subprocess.run(command, cwd=build, check=True, timeout=180, **kwargs)
            run(['sh', str(clock.ROOT/'tools/bootstrap-runtime.sh'), '--profile', 'clock', '--check-only'])
            sources = [str(clock.ROOT/p) for p in clock.SOURCES]
            run([str(ghdl), '-a', '--std=08', *sources])
            for binding in ('false', 'true'):
                with (build/'up5k_synth.v').open('w') as output:
                    run([str(ghdl),'--synth','--std=08','--out=verilog',
                         '-gBOARD_BINDING_VALIDATED='+binding,'effect_ack_board_top'], stdout=output)
                vendor_netlist = (build/'up5k_synth.v').read_text()
                top = re.search(r'\bmodule effect_ack_board_top\b(.*?)\bendmodule', vendor_netlist, re.S)
                self.assertIsNotNone(top)
                declarations = top.group(1).split(');',1)[0]
                actual_ports = dict((name, direction) for direction, name in
                                    re.findall(r'\b(input|output)\s+(\w+)', declarations))
                self.assertEqual(actual_ports, {p:b['direction'] for p,b in self.profile()['adapter']['ports'].items()})
                self.assertEqual(set(actual_ports), set(clock.ports()))
                self.assertNotIn('current_input_bits', declarations)
                self.assertNotIn('readback_bits', declarations)


if __name__ == '__main__': unittest.main()
