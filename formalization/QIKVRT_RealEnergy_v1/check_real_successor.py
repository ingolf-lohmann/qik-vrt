#!/usr/bin/env python3
"""Check the separately locked real-energy consumer, preserving per-run logs.

SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
Extends the original 2026-11-03 checker; never imports a previous PASS receipt.
"""
from pathlib import Path
import argparse, datetime, hashlib, json, os, re, shutil, subprocess, sys, uuid

ROOT = Path(__file__).resolve().parent
NS = 'QIKVRT.V2.Physics.PlanckRealEnergy.'
NAMES = ['PRE_T01_planckMass_pos', 'PRE_T02_planckTime_pos',
         'PRE_T03_planckEnergy_pos', 'PRE_T04_planckTime_mul_planckEnergy',
         'PRE_T05_planckEnergy_eq_hbar_div_planckTime', 'REB_T01_real_bit_bound',
         'REB_T02_gap_normalized', 'REB_T03_planck_budget']
IDS = ['PRE_T01', 'PRE_T02', 'PRE_T03', 'PRE_T04', 'PRE_T05',
       'REB_T01', 'REB_T02', 'REB_T03']
ALLOWED = {'propext', 'Classical.choice', 'Quot.sound'}
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def check_sources(root):
    lock = json.loads((root / 'SOURCE_LOCK.json').read_text())
    for name, expected in lock['package_files'].items():
        p = root / name
        if not p.is_file() or p.stat().st_size != expected['bytes'] or digest(p) != expected['sha256']:
            raise ValueError('SOURCE_BINDING_MISMATCH: ' + name)
    source_manifest = root / 'MATHLIB_SOURCE_MANIFEST.json'
    if digest(source_manifest) != lock['mathlib']['source_manifest_sha256']:
        raise ValueError('MATHLIB_MANIFEST_BINDING_MISMATCH')
    for name, expected in json.loads(source_manifest.read_text()).items():
        p = root / 'vendor/mathlib' / name
        if not p.is_file() or p.stat().st_size != expected['bytes'] or digest(p) != expected['sha256']:
            raise ValueError('MATHLIB_SOURCE_BINDING_MISMATCH: ' + name)
    manifest = json.loads((root / 'lake-manifest.json').read_text())
    upstream = json.loads((root / 'vendor/mathlib/lake-manifest.json').read_text())
    expected = {p['name']: p['rev'] for p in upstream['packages']}
    actual = {p['name']: p['rev'] for p in manifest['packages'] if p['type'] == 'git'}
    if expected != actual: raise ValueError('TRANSITIVE_REVISION_MISMATCH')
    mathlib = [p for p in manifest['packages'] if p['name'] == 'mathlib']
    if len(mathlib) != 1 or mathlib[0].get('type') != 'path' or mathlib[0].get('dir') != './vendor/mathlib':
        raise ValueError('MATHLIB_SOURCE_PATH_MISMATCH')
    for name, rev in expected.items():
        directory = root / '.lake/packages' / name
        head = subprocess.run(['git', '-C', str(directory), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
        if head.returncode or head.stdout.strip() != rev:
            raise ValueError('DEPENDENCY_GIT_REVISION_MISMATCH: ' + name)
        clean = subprocess.run(['git', '-C', str(directory), 'diff', '--exit-code', 'HEAD', '--'], capture_output=True, timeout=10)
        if clean.returncode: raise ValueError('DEPENDENCY_TRACKED_SOURCE_CHANGED: ' + name)
    for name in lock['package_files']:
        if name.endswith('.lean'):
            text = (root / name).read_text()
            if re.search(r'\b(sorry|admit|sorryAx)\b|^\s*(axiom|unsafe)\b', text, re.M):
                raise ValueError('FORBIDDEN_PROOF_PLACEHOLDER: ' + name)
    return lock

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--lake', default=shutil.which('lake'))
    ap.add_argument('--lean', default=shutil.which('lean'))
    ap.add_argument('--preflight-only', action='store_true')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    outdir = args.output or root / 'verification' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8])
    outdir.mkdir(parents=True, exist_ok=False)
    report = {'schema':'qikvrt-locked-real-energy-verification/v2', 'started_at':now(),
              'status':'UNVERIFIED', 'cases':[], 'source_lock_sha256':None,
              'native_CI':'NOT_EXECUTED', 'seven_independent_checkers':'NOT_EXECUTED',
              'empirical_correspondence':'NOT_MEASURED', 'effect_ack_done':False}
    def finish(code, reason):
        report['finished_at'] = now(); report['reason'] = reason
        (outdir / 'RECEIPT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'status':report['status'],'reason':reason,'receipt':str(outdir / 'RECEIPT.json')}), flush=True)
        return code
    def run(name, command):
        log = outdir / (name + '.log'); start = now()
        with log.open('wb') as stream:
            p = subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        raw = log.read_text(errors='replace')
        record = {'name':name, 'started_at':start, 'finished_at':now(), 'exit':p.returncode,
                  'log':log.name, 'log_bytes':log.stat().st_size, 'log_sha256':digest(log)}
        report['cases'].append(record)
        print(name, 'EXIT', p.returncode, flush=True)
        return record, raw
    try:
        lock = check_sources(root); report['source_lock_sha256'] = digest(root / 'SOURCE_LOCK.json')
        if args.preflight_only:
            report['status'] = 'VERIFIED_SOURCE_BINDING'
            return finish(0, 'Exact sources and dependency revisions checked; no proof check claimed')
        for name, executable in [('lean', args.lean), ('lake', args.lake)]:
            if not executable or not Path(executable).is_file():
                return finish(2, name.upper() + '_EXECUTABLE_UNAVAILABLE')
        if digest(Path(args.lean)) != lock['lean_linux_x86_64_executable_sha256']:
            return finish(2, 'LEAN_EXECUTABLE_BINDING_MISMATCH')
        record, raw = run('lean_version', [args.lean, '--version'])
        if record['exit'] or 'version 4.19.0' not in raw or '6caaee842e94' not in raw:
            return finish(2, 'LEAN_VERSION_UNVERIFIED')
        report['lean_executable_sha256'] = digest(Path(args.lean))
        base = root / '.lake/build/lib/lean'; base.mkdir(parents=True, exist_ok=True)
        for name in ['PlanckRealEnergyDomain', 'RealErasureBudget', 'RealEnergyStatements',
                     'RealEnergyAxiomAudit', 'RealEnergyAcceptanceAudit']:
            record, raw = run(name, [args.lake, 'env', 'lean', '-E', 'hasSorry', '-o', str(base / (name + '.olean')), str(root / (name + '.lean'))])
            if record['exit']:
                report['status'] = 'FAILED' if re.search(r'\.lean:\d+:\d+: error:', raw) else 'UNVERIFIED'
                return finish(1 if report['status'] == 'FAILED' else 2, 'COMPILE_' + name)
            record['olean_sha256'] = digest(base / (name + '.olean'))
            if 'Audit' in name:
                matches = re.findall(r"'([^']+)' depends on axioms:\s*\[([^]]*)\]", raw, re.S)
                expected = {NS+n for n in (NAMES if name == 'RealEnergyAxiomAudit' else [i+'_checked' for i in IDS])}
                if len(matches) != 8 or {x for x,_ in matches} != expected:
                    return finish(2, 'AXIOM_INVENTORY_INCOMPLETE: ' + name)
                record['axiom_map'] = {key:[v.strip() for v in values.split(',') if v.strip()] for key,values in matches}
                if any(set(values)-ALLOWED for values in record['axiom_map'].values()):
                    report['status']='FAILED'; return finish(1, 'UNAPPROVED_AXIOM')
        for source in sorted((root / 'negative').glob('*.lean')):
            record, raw = run('negative_' + source.stem, [args.lake, 'env', 'lean', '-E', 'hasSorry', str(source)])
            semantic = re.search(r'\.lean:\d+:\d+: error:', raw) and re.search(r'unsolved goals|failed to prove|made no progress', raw)
            unavailable = re.search(r'unknown module|unknown tactic|unknown identifier|failed to locate|file not found|unexpected token', raw)
            if record['exit'] == 0:
                report['status']='FAILED'; return finish(1, 'FALSE_STATEMENT_ACCEPTED')
            if not semantic or unavailable: return finish(2, 'NEGATIVE_CHECKER_UNAVAILABLE')
            record['outcome']='VERIFIED_REJECTION'
        check_sources(root)
        report['core_theorems']=8; report['checked_bindings']=8; report['negative_controls']=4
        report['status']='VERIFIED_LOCAL_KERNEL'
        return finish(0, 'Eight original claims and eight statement bindings checked with exact sources; four false statements rejected')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return finish(2, type(exc).__name__ + ': ' + str(exc))

if __name__ == '__main__': sys.exit(main())
