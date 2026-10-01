#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check coherent carrier telemetry; V1 cannot attest an unbound physical board."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('rtl/effect_ack_clock_pkg.vhd', 'rtl/effect_ack_coverage_witness.vhd',
           'rtl/effect_ack_clock_carrier.vhd', 'rtl/effect_ack_board_top.vhd')
PORT_WIDTHS = dict.fromkeys(('clk', 'power_reset_n', 'frame_start', 'frame_shift',
                            'frame_latch', 'serial_in', 'response_shift',
                            'serial_out', 'response_valid', 'transport_fault'), 1)
INPUT_PORTS = frozenset(('clk', 'power_reset_n', 'frame_start', 'frame_shift',
                        'frame_latch', 'serial_in', 'response_shift'))
OPEN_OBLIGATIONS = ('authenticated_inputs', 'cdc', 'epoch_fault_retention',
                    'independent_physical_clock_witness', 'complete_effect_mediation')
TIMING_FIELDS = ('input_min_ns', 'input_max_ns', 'output_min_ns', 'output_max_ns',
                 'clock_uncertainty_ns')
ARTIFACT_NAMES = ('placement_route', 'sta', 'bitstream', 'configuration_image',
                  'programmer_log', 'configuration_readback')
MAX_AGE_SECONDS = 300
PROFILE_MAX_AGE_SECONDS = 86400
MAX_RUN_SECONDS = 21600
DOCUMENTARY_PROFILE = 'hardware/boards/lattice_ice40up5k_b_evn_rev_a.json'


def unique(pairs):
    result = {}
    for key, val in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = val
    return result


def load_json(path):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('JSON input must be a regular file without symlinks')
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('JSON input exceeds byte bound')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite JSON: ' + x)))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise ValueError(label + ': missing or unexpected fields')


def token(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:/+-]{1,160}', value):
        raise ValueError(label + ': explicit bounded identifier required')
    if value.upper() in ('OPEN', 'UNKNOWN', 'UNAVAILABLE', 'TBD', 'REQUIRED', 'NONE'):
        raise ValueError(label + ': unresolved identifier')


def sha(value, label, width=64):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(width) + '}', value):
        raise ValueError(label + ': canonical digest required')


def subject_binding(subject):
    exact(subject, ('repository', 'pr', 'head', 'tree'), 'subject')
    if subject['repository'] != 'ingolf-lohmann/qik-vrt' or type(subject['pr']) is not int or subject['pr'] != 430:
        raise ValueError('repository/PR binding mismatch')
    sha(subject['head'], 'head', 40); sha(subject['tree'], 'tree', 40)


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z', value):
        raise ValueError('canonical UTC timestamp required')
    try:
        return dt.datetime.fromisoformat(value[:-1] + '+00:00')
    except ValueError as exc:
        raise ValueError('invalid UTC timestamp') from exc


def fresh(value, now, max_age=MAX_AGE_SECONDS):
    observed = timestamp(value)
    if now.tzinfo is None or not 0 <= (now - observed).total_seconds() <= max_age:
        raise ValueError('stale or future board data')
    return observed


def number(value, label):
    if type(value) not in (int, float) or abs(value) > 1e9 or not math.isfinite(value):
        raise ValueError(label + ': finite bounded number required')


def ports():
    return {name if width == 1 else f'{name}[{bit}]': name
            for name, width in PORT_WIDTHS.items() for bit in range(width)}


def board_receipt(state, reason, subject, **fields):
    return dict(schema='qikvrt_effect_ack_board_receipt_v1', state=state, reason=reason,
                subject=subject, external_effect='NONE', ordinary_release=False,
                physical_clock_verified=False, bitstream_programmed=False,
                programmer_readback_observed=False, EFFECT_ACK_DONE=False,
                effect_ack_done=False, **fields)


def prepare_documentary_board(profile, *, subject, nonce, timing=None, root=ROOT):
    """Source-bound candidate inputs, never a lab identity or a vendor result.

    Documentary data cannot satisfy V1's physical serial/IDCODE requirements.
    The canonical reference is reviewed repository content; a caller cannot
    replace its pin, voltage, package, source or physical-status bindings.
    """
    reference = load_json(Path(root) / DOCUMENTARY_PROFILE)
    if profile != reference:
        raise ValueError('documentary profile differs from source-bound repository profile')
    if timing is None:
        return board_receipt('HOLD_INTERFACE_TIMING_BUDGET_REQUIRED',
                             'Documentary pin binding exists; explicit synchronous interface timing budget required.',
                             subject, nonce=nonce, physical_authentication=False,
                             source_archive_crosscheck_complete=False)
    exact(timing, TIMING_FIELDS, 'timing budget')
    for key in timing: number(timing[key], key)
    if (timing['input_min_ns'] > timing['input_max_ns'] or
        timing['output_min_ns'] > timing['output_max_ns'] or
        timing['clock_uncertainty_ns'] < 0 or
        max(timing.values()) >= profile['clock']['period_ns']):
        raise ValueError('contradictory or out-of-period timing budget')
    pins = profile['adapter']['ports']
    top = profile['adapter']['top']
    pdc = ['# Documentary Rev A voltage assignments; actual rails still unmeasured.']
    pdc.extend(f'ldc_set_vcc -bank {bank} {volts}'
               for bank, volts in sorted(profile['electrical']['vccio_volts'].items()))
    pdc.append(f'ldc_set_vcc -core {profile["electrical"]["vcc_volts"]}')
    for port, pin in sorted(pins.items()):
        pdc.extend((f'ldc_set_location -site {{{pin["package_pin"]}}} [get_ports {{{port}}}]',
                    f'ldc_set_port -iobuf {{IO_TYPE=LVCMOS33 PULLMODE=NONE}} [get_ports {{{port}}}]'))
    sdc = [f'create_clock -name processor_clock -period {profile["clock"]["period_ns"]} [get_ports {{clk}}]',
           f'set_clock_uncertainty {timing["clock_uncertainty_ns"]} [get_clocks {{processor_clock}}]']
    for direction in ('input', 'output'):
        names = sorted(p for p, b in pins.items() if b['direction'] == direction and p != 'clk')
        for bound in ('min', 'max'):
            sdc.append(f'set_{direction}_delay -{bound} {timing[direction + "_" + bound + "_ns"]} '
                       f'-clock processor_clock [get_ports {{{" ".join(names)}}}]')
    # Radiant 2026.1 Project-mode Tcl from FPGA-AN-02113 sections 4.1/4.4/4.10
    # and the TCL Scripting User Guide, "Running a Design Flow".
    # GHDL lowers VHDL-2008 first. The vendor consumes the derived Verilog,
    # avoiding an invented vendor HDL-language/generic command.
    build = [
        '# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0',
        '# Candidate only; separately provision/lock/verify Radiant 2026.1 before execution.',
        'if {![file exists up5k_synth.v]} {error {GHDL-derived netlist required}}',
        'prj_create -name effect_ack_up5k -impl impl_1 -dev iCE40UP5K-SG48I -synthesis synplify',
        'prj_add_source up5k_synth.v', 'prj_add_source board.pdc', 'prj_add_source board.sdc',
        'prj_set_top_module effect_ack_board_top',
        'if {![prj_run Synthesis -impl impl_1]} {error {Synthesis failed}}',
        'if {![prj_run Map -impl impl_1]} {error {Map failed}}',
        'if {![prj_run PAR -impl impl_1]} {error {PAR failed}}',
        'prj_save',
        'puts {HOLD: verify routed STA, all IO/reset recovery/removal paths and resource fit before bitstream generation}',
    ]
    constraints = {'board.pdc': '\n'.join(pdc) + '\n', 'board.sdc': '\n'.join(sdc) + '\n'}
    generated = dict(constraints, **{'build_radiant.tcl': '\n'.join(build) + '\n'})
    sources = {}
    for path in SOURCES:
        source = Path(root) / path
        if any(p.is_symlink() for p in (source, *source.parents)) or not source.is_file():
            raise ValueError('source must be a regular file without symlinks')
        sources[path] = hashlib.sha256(source.read_bytes()).hexdigest()
    plan = dict(schema='qikvrt_effect_ack_documentary_build_plan_v2', subject=subject,
                profile_sha256=digest(profile), nonce=nonce, top=top,
                part=profile['fpga']['selected_build_part'], sources=sources, interface=profile['adapter'],
                source_order=list(SOURCES), external_signal_bits=len(pins),
                timing_budget=timing, timing_budget_measured=False,
                constraints=constraints, generated_files=generated,
                generated_sha256={p: hashlib.sha256(v.encode()).hexdigest() for p, v in generated.items()},
                pre_synthesis=[['ghdl', '-a', '--std=08', *SOURCES],
                               ['ghdl', '--synth', '--std=08', '--out=verilog',
                                '-gBOARD_BINDING_VALIDATED=true', top]],
                pre_synthesis_output='up5k_synth.v',
                pre_synthesis_tool='LOCKED_GHDL_6.0.0; hash derived netlist before vendor build',
                vendor_tool=dict(name='radiant', version='2026.1', executable_sha256=None,
                                 installation_authenticated=False),
                vendor_invocation=['radiantc', 'build_radiant.tcl'], vendor_build_executed=False,
                programmer=profile['vendor_path'],
                programming_authorized=False, tool_execution_authorized=False,
                source_archive_crosscheck_complete=False,
                physical_authentication=False, physical_clock_verified=False,
                static_generic_is_physical_attestation=False,
                required_observations=['primary_archive_crosscheck', 'locked_vendor_installation',
                    'routed_resource_fit_and_STA', 'bitstream', 'board_revision_serial_and_marking',
                    'programmer_target_and_flash_byte_readback', 'active_image_correspondence',
                    'fresh_clock_nonce_epoch_count_readback', *OPEN_OBLIGATIONS])
    return board_receipt('HOLD_PRIMARY_ARCHIVE_CROSSCHECK_REQUIRED',
                         'Ten-pin documentary build candidate prepared; three primary ZIPs require Lattice authentication. '
                         'Vendor build, interface timing measurements and authenticated board run remain required.',
                         subject, nonce=nonce, plan=plan, plan_sha256=digest(plan),
                         physical_authentication=False, source_archive_crosscheck_complete=False)


def prepare_board(profile, *, subject, nonce, now, root=ROOT, timing=None):
    """Validate data and emit build inputs. Never run a vendor tool/programmer."""
    subject_binding(subject)
    if type(nonce) is not int or not 0 < nonce < 2**64:
        raise ValueError('fresh nonzero board-run challenge required')
    if profile is None:
        return board_receipt('BOARD_BINDING_REQUIRED', 'No evidenced board/FPGA/clock/pin profile supplied.', subject,
                             nonce=nonce, required_inputs=['board', 'fpga', 'clock', 'pins', 'timing', 'toolchain'])
    if isinstance(profile, dict) and profile.get('schema') == 'qikvrt_effect_ack_documentary_board_profile_v2':
        return prepare_documentary_board(profile, subject=subject, nonce=nonce, timing=timing, root=root)
    exact(profile, ('schema', 'subject', 'observed_at', 'board', 'fpga', 'clock',
                    'pins', 'timing', 'toolchain', 'interfaces'), 'board profile')
    if profile['schema'] != 'qikvrt_effect_ack_board_profile_v1' or profile['subject'] != subject:
        raise ValueError('stale board profile subject/schema')
    fresh(profile['observed_at'], now, PROFILE_MAX_AGE_SECONDS)
    board = profile['board']; fpga = profile['fpga']; clock = profile['clock']
    exact(board, ('id', 'revision', 'serial', 'source_sha256'), 'board')
    for key in ('id', 'revision', 'serial'): token(board[key], 'board.' + key)
    sha(board['source_sha256'], 'board source')
    exact(fpga, ('vendor', 'part', 'idcode'), 'FPGA')
    for key in fpga: token(fpga[key], 'FPGA.' + key)
    exact(clock, ('port', 'period_ns', 'source_id'), 'clock')
    if clock['port'] != 'clk': raise ValueError('clock must bind top-level clk')
    token(clock['source_id'], 'clock source'); number(clock['period_ns'], 'clock period')
    if clock['period_ns'] <= 0: raise ValueError('positive clock period required')
    pin_map = profile['pins']; exact(pin_map, ports(), 'pins: complete top-level bit binding')
    assigned = set()
    for port, binding in pin_map.items():
        exact(binding, ('package_pin', 'io_standard'), 'pin ' + port)
        pin = binding['package_pin']; io = binding['io_standard']
        if not isinstance(pin, str) or not re.fullmatch(r'[A-Za-z0-9_+-]{1,64}', pin):
            raise ValueError('unsafe or missing package-pin identifier')
        token(pin, 'pin.package_pin')
        if not isinstance(io, str) or not re.fullmatch(r'[A-Za-z0-9_. /+-]{1,64}', io) or io != io.strip() or io.upper() in ('OPEN', 'TBD', 'UNKNOWN', 'REQUIRED'):
            raise ValueError('unsafe or missing IO-standard identifier')
        package_pin = binding['package_pin'].upper()
        if package_pin in assigned: raise ValueError('contradictory duplicate package pin')
        assigned.add(package_pin)
    timing = profile['timing']; exact(timing, TIMING_FIELDS, 'timing')
    for key in timing: number(timing[key], key)
    if timing['input_min_ns'] > timing['input_max_ns'] or timing['output_min_ns'] > timing['output_max_ns'] or timing['clock_uncertainty_ns'] < 0:
        raise ValueError('contradictory timing bounds')
    tool = profile['toolchain']; exact(tool, ('name', 'version', 'executable_sha256', 'provenance_sha256'), 'toolchain')
    token(tool['version'], 'tool version')
    sha(tool['executable_sha256'], 'tool bytes'); sha(tool['provenance_sha256'], 'tool provenance')
    if (fpga['vendor'], tool['name']) not in (('AMD_XILINX', 'vivado'), ('INTEL', 'quartus')):
        raise ValueError('unsupported or contradictory vendor/toolchain binding')
    interfaces = profile['interfaces']; exact(interfaces, ('input_domain', *OPEN_OBLIGATIONS), 'interfaces')
    if interfaces['input_domain'] != 'SYNCHRONOUS_TO_CLK' or any(interfaces[x] != 'OPEN' for x in OPEN_OBLIGATIONS):
        raise ValueError('V1 requires synchronous inputs and preserves unresolved physical obligations')
    sdc = [f'create_clock -name processor_clock -period {clock["period_ns"]} [get_ports {{clk}}]',
           f'set_clock_uncertainty {timing["clock_uncertainty_ns"]} [get_clocks {{processor_clock}}]']
    for direction in ('input', 'output'):
        names = sorted(p for p, name in ports().items() if (name in INPUT_PORTS) == (direction == 'input') and name != 'clk')
        for bound in ('min', 'max'):
            sdc.append(f'set_{direction}_delay -{bound} {timing[direction + "_" + bound + "_ns"]} -clock processor_clock [get_ports {{{" ".join(names)}}}]')
    locations = []
    if tool['name'] == 'vivado':
        for port, pin in sorted(pin_map.items()):
            locations.extend((f'set_property PACKAGE_PIN {pin["package_pin"]} [get_ports {{{port}}}]',
                              f'set_property IOSTANDARD {pin["io_standard"]} [get_ports {{{port}}}]'))
        constraints = {'board.xdc': '\n'.join(locations + sdc) + '\n'}
    else:
        locations.extend((f'set_global_assignment -name DEVICE {fpga["part"]}',
                          'set_global_assignment -name TOP_LEVEL_ENTITY effect_ack_board_top',
                          'set_parameter -name BOARD_BINDING_VALIDATED true'))
        for port, pin in sorted(pin_map.items()):
            locations.extend((f'set_location_assignment PIN_{pin["package_pin"]} -to {{{port}}}',
                              f'set_instance_assignment -name IO_STANDARD {{{pin["io_standard"]}}} -to {{{port}}}'))
        constraints = {'board.qsf': '\n'.join(locations) + '\n', 'board.sdc': '\n'.join(sdc) + '\n'}
    sources = {}
    for path in SOURCES:
        source = Path(root) / path
        if any(p.is_symlink() for p in (source, *source.parents)):
            raise ValueError('source symlink forbidden')
        sources[path] = hashlib.sha256(source.read_bytes()).hexdigest()
    plan = dict(schema='qikvrt_effect_ack_board_build_plan_v1', subject=subject,
                profile_sha256=digest(profile), nonce=nonce, board=board, fpga=fpga,
                toolchain=tool, top='effect_ack_board_top', sources=sources,
                source_order=list(SOURCES),
                interface=dict(protocol='SYNCHRONOUS_FRAMED_SERIAL_V1',
                               physical_ports=list(PORT_WIDTHS), request_bits=317,
                               response_bits=485, carrier_paused_during_transfer=False),
                generics={'BOARD_BINDING_VALIDATED': True}, constraints=constraints,
                constraint_sha256={p: hashlib.sha256(v.encode()).hexdigest() for p, v in constraints.items()},
                phases=['synthesis', 'placement_route', 'STA', 'bitstream', 'separately_authorized_programming', 'fresh_programmer_readback'],
                programming_authorized=False, tool_execution_authorized=False,
                required_report_schema='qikvrt_effect_ack_board_run_v1')
    return board_receipt('BUILD_INPUTS_READY', 'Validated build inputs; vendor build and authenticated board execution remain required.',
                         subject, nonce=nonce, plan=plan, plan_sha256=digest(plan))


def artifact_bytes(root, item):
    exact(item, ('path', 'sha256'), 'artifact'); sha(item['sha256'], 'artifact digest')
    name = item['path']
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]{1,240}', name):
        raise ValueError('unsafe artifact path')
    path = Path(name)
    if path.is_absolute() or any(p in ('.', '..') for p in name.split('/')):
        raise ValueError('artifact traversal forbidden')
    full = Path(root) / path
    if any(p.is_symlink() for p in (full, *full.parents)) or not full.is_file():
        raise ValueError('artifact must be a regular file without symlinks')
    if not 0 < full.stat().st_size <= 64 * 1024 * 1024: raise ValueError('artifact byte bound')
    raw = full.read_bytes()
    if hashlib.sha256(raw).hexdigest() != item['sha256']: raise ValueError('artifact byte mismatch')
    return raw


def verify_board_run(profile, report, *, subject, nonce, epoch, expected_count, now, artifacts_root, root=ROOT):
    if isinstance(profile, dict) and profile.get('schema') == 'qikvrt_effect_ack_documentary_board_profile_v2':
        raise ValueError('documentary profile has no authenticated board identity or trusted programmer adapter')
    prepared = prepare_board(profile, subject=subject, nonce=nonce, now=now, root=root)
    if 'plan' not in prepared: return prepared
    exact(report, ('schema', 'subject', 'profile_sha256', 'plan_sha256', 'nonce', 'run_id',
                   'started_at', 'observed_at', 'board_serial', 'fpga_idcode', 'artifacts',
                   'sta', 'programmer', 'clock_readback'), 'board run')
    if report['schema'] != 'qikvrt_effect_ack_board_run_v1' or report['subject'] != subject:
        raise ValueError('stale board-run subject/schema')
    if type(report['nonce']) is not int or report['nonce'] != nonce or report['profile_sha256'] != digest(profile) or report['plan_sha256'] != prepared['plan_sha256']:
        raise ValueError('stale challenge/profile/build binding')
    token(report['run_id'], 'run ID')
    started = fresh(report['started_at'], now, MAX_RUN_SECONDS); observed = fresh(report['observed_at'], now)
    if not timestamp(profile['observed_at']) <= started <= observed: raise ValueError('contradictory board-run chronology')
    if report['board_serial'] != profile['board']['serial'] or report['fpga_idcode'] != profile['fpga']['idcode']:
        raise ValueError('programmer target identity mismatch')
    exact(report['artifacts'], ARTIFACT_NAMES, 'artifacts')
    if len({v['path'] for v in report['artifacts'].values() if isinstance(v, dict) and 'path' in v}) != len(ARTIFACT_NAMES):
        raise ValueError('independent artifact paths required')
    artifacts = {name: artifact_bytes(artifacts_root, report['artifacts'][name]) for name in ARTIFACT_NAMES}
    sta = report['sta']
    exact(sta, ('part', 'clock_period_ns', 'placement_route_completed', 'unconstrained_paths',
                'setup_slack_ns', 'hold_slack_ns', 'recovery_slack_ns', 'removal_slack_ns'), 'STA')
    number(sta['clock_period_ns'], 'STA clock period')
    if sta['part'] != profile['fpga']['part'] or sta['clock_period_ns'] != profile['clock']['period_ns'] or sta['placement_route_completed'] is not True or type(sta['unconstrained_paths']) is not int or sta['unconstrained_paths'] != 0:
        raise ValueError('STA target/clock/route/coverage mismatch')
    for key in ('setup_slack_ns', 'hold_slack_ns', 'recovery_slack_ns', 'removal_slack_ns'):
        number(sta[key], key)
        if sta[key] < 0: raise ValueError('STA violation: ' + key)
    programmer = report['programmer']
    exact(programmer, ('programmed', 'readback_observed', 'tool', 'version', 'executable_sha256',
                       'configuration_image_sha256', 'readback_configuration_sha256'), 'programmer')
    token(programmer['tool'], 'programmer tool'); token(programmer['version'], 'programmer version')
    sha(programmer['executable_sha256'], 'programmer bytes')
    if programmer['programmed'] is not True or programmer['readback_observed'] is not True:
        raise ValueError('programming/readback absent')
    config = hashlib.sha256(artifacts['configuration_image']).hexdigest()
    if programmer['configuration_image_sha256'] != config or programmer['readback_configuration_sha256'] != config or artifacts['configuration_image'] != artifacts['configuration_readback']:
        raise ValueError('programmer configuration readback mismatch')
    # Reuse the existing coherent telemetry verifier. External JSON plus hashes
    # cannot authenticate a lab run, a CDC adapter or an independent oscillator.
    verify_readback(report['clock_readback'], nonce=nonce, epoch=epoch, expected_count=expected_count)
    return board_receipt('HOLD_AUTHENTICATED_BOARD_RUN_REQUIRED',
                         'Evidence contract is consistent; trusted adapter/lab attestation and physical obligations remain OPEN.',
                         subject, nonce=nonce, plan_sha256=prepared['plan_sha256'],
                         evidence_contract_consistent=True, open_obligations=list(OPEN_OBLIGATIONS))


def board_main(argv):
    parser = argparse.ArgumentParser(description='Fail-closed board build/readback interface; no vendor-tool or programmer effects')
    parser.add_argument('action', choices=('prepare-board', 'verify-board'))
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--timing', type=Path, help='Explicit synchronous interface timing budget for documentary V2 candidate')
    parser.add_argument('--expect-head', required=True); parser.add_argument('--expect-tree', required=True)
    parser.add_argument('--nonce', type=int, required=True)
    parser.add_argument('--report', type=Path); parser.add_argument('--artifacts-root', type=Path)
    parser.add_argument('--epoch', type=int); parser.add_argument('--expected-count', type=int)
    args = parser.parse_args(argv)
    subject = dict(repository='ingolf-lohmann/qik-vrt', pr=430, head=args.expect_head, tree=args.expect_tree)
    try:
        subject_binding(subject)
        for query, expected in [('HEAD', args.expect_head), ('HEAD^{tree}', args.expect_tree)]:
            actual = subprocess.run(['git', 'rev-parse', '--verify', query], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10).stdout.strip()
            if actual != expected: raise ValueError('current checkout subject mismatch')
        dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, capture_output=True, text=True, check=True, timeout=10).stdout
        if dirty: raise ValueError('clean exact-subject checkout required')
        now = dt.datetime.now(dt.timezone.utc)
        profile = load_json(args.profile) if args.profile else None
        if args.action == 'prepare-board':
            result = prepare_board(profile, subject=subject, nonce=args.nonce, now=now,
                                   timing=load_json(args.timing) if args.timing else None)
        else:
            if any(x is None for x in (args.report, args.artifacts_root, args.epoch, args.expected_count)):
                raise ValueError('report/artifacts/epoch/count caller bindings required')
            result = verify_board_run(profile, load_json(args.report), subject=subject, nonce=args.nonce,
                                      epoch=args.epoch, expected_count=args.expected_count, now=now, artifacts_root=args.artifacts_root)
        code = 20
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        result = board_receipt('BLOCK_BOARD_EVIDENCE', str(exc), subject); code = 1
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return code

FIELDS = {'schema', 'nonce', 'epoch', 'evaluated', 'witnessed', 'fault',
          'witness_fault', 'reset_seen', 'state', 'snapshot_epoch', 'snapshot_cycle'}


def verify_readback(value, *, nonce, epoch, expected_count):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('missing or unexpected readback fields')
    if value['schema'] != 'qikvrt_effect_ack_clock_readback_v1':
        raise ValueError('readback schema mismatch')
    for key in FIELDS - {'schema'}:
        if type(value[key]) is not int or not 0 <= value[key] < 2**64:
            raise ValueError('noncanonical unsigned field: ' + key)
    if any(type(x) is not int or not 0 < x < 2**64 for x in (nonce, epoch, expected_count)):
        raise ValueError('fresh caller binding required')
    if (value['nonce'], value['epoch'], value['evaluated']) != (nonce, epoch, expected_count):
        raise ValueError('stale challenge, epoch or observation window')
    if value['evaluated'] != value['witnessed']:
        raise ValueError('coverage disagreement')
    if any(value[x] != 0 for x in ('fault', 'witness_fault', 'reset_seen')):
        raise ValueError('latched clock/reset fault')
    if value['snapshot_epoch'] != epoch or value['snapshot_cycle'] != expected_count - 1:
        raise ValueError('snapshot/coverage binding mismatch')
    if value['state'] > 4:
        raise ValueError('invalid state')
    return {'schema': 'qikvrt_effect_ack_clock_readback_disposition_v1',
            'telemetry_consistent': True, 'physical_clock_verified': False,
            'ordinary_release': False, 'effect_ack_done': False,
            'state': 'HOLD_PHYSICAL_BINDING_OPEN',
            'reason': 'No authenticated board adapter, pin/timing/programmer or independent oscillator witness is bound in V1.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readback', type=Path)
    parser.add_argument('--nonce', type=int, required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--expected-count', type=int, required=True)
    args = parser.parse_args()
    try:
        result = verify_readback(load_json(args.readback),
                                 nonce=args.nonce, epoch=args.epoch, expected_count=args.expected_count)
        code = 20
    except (OSError, ValueError) as exc:
        result = {'state': 'BLOCK', 'reason': str(exc), 'ordinary_release': False,
                  'physical_clock_verified': False, 'effect_ack_done': False}
        code = 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(board_main(sys.argv[1:]) if len(sys.argv) > 1 and sys.argv[1] in ('prepare-board', 'verify-board') else main())
