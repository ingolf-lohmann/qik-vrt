#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bounded orchestration of existing repository tests; no external write authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('--group', choices=('python', 'formal', 'native'), required=True)
p.add_argument('--repository', required=True)
p.add_argument('--head', required=True)
p.add_argument('--tree', required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--followup-only', action='store_true')
a = p.parse_args()
root = Path.cwd()
out = a.output.resolve()
out.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'ZENODO_TOKEN', 'ZENODO_ACCESS_TOKEN', 'QIKVRT_LAUNCHED_BY_QIKVRT'):
    env.pop(name, None)
env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONNOUSERSITE='1', QIKVRT_EXTERNAL_EFFECTS='disabled')
env['PYTHONPATH'] = str(root) + os.pathsep + str(root / 'tests')

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

assert git('rev-parse', 'HEAD') == a.head
assert git('rev-parse', 'HEAD^{tree}') == a.tree
assert not git('status', '--porcelain')
tracked = git('ls-files').splitlines()
checks = []
receipt = {
    'schema': 'qikvrt_repository_selftest_observation_v1',
    'subject': {'repository': a.repository, 'head': a.head, 'tree': a.tree},
    'executor': {k: os.environ.get(k) for k in ('GITHUB_REPOSITORY', 'GITHUB_SHA', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'RUNNER_OS', 'ImageVersion')},
    'group': a.group, 'checks': checks, 'ordinary_release': False,
    'predecessor_evidence_transfer': False,
    'external_write_authority': False,
}

def save():
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')

def run(label, command, cwd=root, timeout=600, informational=False, extra_env=None):
    log = out / (f'{len(checks):03d}-' + re.sub(r'[^a-zA-Z0-9_.-]+', '_', label) + '.log')
    start = time.monotonic()
    status = 'FAIL'
    code = None
    with log.open('w') as f:
        try:
            result = subprocess.run(command, cwd=cwd, env={**env, **(extra_env or {})}, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
            code = result.returncode
            status = 'PASS' if code == 0 else 'FAIL'
        except subprocess.TimeoutExpired:
            status = 'TIMEOUT'
            f.write('\nSELFTEST_TIMEOUT\n')
        except OSError as exc:
            status = 'UNAVAILABLE'
            f.write(str(exc) + '\n')
    text = log.read_text(errors='replace')
    entry = {'name': label, 'command': command, 'cwd': str(Path(cwd).relative_to(root)), 'exit_code': code,
             'status': status, 'seconds': round(time.monotonic() - start, 3), 'log': log.name,
             'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(), 'informational': informational}
    counts = [int(n) for n in re.findall(r'^Ran (\d+) tests? in ', text, re.M)]
    if counts:
        entry['unittest_executions'] = sum(counts)
    if label == 'bootstrap-all':
        try:
            entry['runtime_state'] = json.loads(text).get('state')
        except ValueError:
            entry['runtime_state'] = 'UNPARSED'
    checks.append(entry)
    save()
    print(f'SELFTEST {status} {label} exit={code} seconds={entry["seconds"]}', flush=True)
    if status != 'PASS':
        print(text[-6500:], flush=True)
    return code == 0

save()
if not run('tool-cache', [sys.executable, '-B', 'tools/qikvrt_tool_cache.py', 'verify']):
    receipt['state'] = 'BLOCKED_TOOL_CACHE'
    save()
    raise SystemExit(1)
run('integrity-before', [sys.executable, '-B', 'tools/qikvrt_integrity.py', 'verify'])

if a.group == 'python':
    run('locked-ietf-bootstrap', ['sh', 'tools/bootstrap-runtime.sh', '--install', '--accept-third-party', '--profile', 'ietf'], timeout=1200)
    run('historical-recovery-object', ['git', 'fetch', '--no-tags', 'https://github.com/Goldkelch/qik-vrt.git', '53e757ebce929b40250f90a02ed2a9ec62de6217'])
    renderers = sorted((root / '.qikvrt/toolchains/xml2rfc').glob('3.34.0/python-3.12.13/linux-amd64/venv/bin/xml2rfc'))
    renderer = renderers[0] if len(renderers) == 1 else root / 'UNAVAILABLE_XML2RFC'
    run('bootstrap-all', [sys.executable, '-B', 'tools/ai_runtime_bootloader.py', '--profile', 'all', '--json'], informational=True)
    if Path('tools/ai_collective_bootstrap_extension.py').exists():
        run('collective-bootstrap', [sys.executable, '-B', 'tools/ai_collective_bootstrap_extension.py', '--json'], informational=True)
    run('bind-master-test-authorization', [sys.executable, '-B', 'tools/qikvrt_initial_acceptance_gate.py', '--accept', '--accepted-by', 'OpenAI Codex executing Ingolf Lohmann repository self-test request', '--scope', 'Repository self-test only; no publication, merge, deployment or external write', '--operation', 'master-gate'])
    master_ok = run('canonical-master-gate', [sys.executable, '-B', 'tools/qikvrt_master_acceptance_gate.py', '--test-timeout', '180'], timeout=3600)
    modules = sorted(s for s in tracked if re.fullmatch(r'tests/test_[^/]+\.py', s))
    receipt['root_python_module_inventory'] = modules
    receipt['root_python_module_count'] = len(modules)
    receipt['root_execution_route'] = 'canonical-master-gate' if master_ok else 'individual-modules-after-master-failure'
    if not master_ok:
        for path in modules:
            if path in ('tests/test_ietf_offline_render.py', 'tests/test_ietf_revision_02.py', 'tests/test_ietf_revision_03.py'):
                command = [sys.executable, '-B', path, '--xml2rfc', str(renderer)]
            elif path == 'tests/test_pypdf_runtime_contract.py':
                command = [str(renderer.parent / 'python'), '-B', path]
            elif '__main__' in Path(path).read_text():
                command = [sys.executable, '-B', path]
            else:
                command = [sys.executable, '-B', '-m', 'unittest', '-v', path[:-3].replace('/', '.')]
            run(path, command, timeout=180)
    for path in sorted(s for s in tracked if re.fullmatch(r'(tests/[^/]+|docs/publications/[^/]+)/test_[^/]+\.py', s)):
        run(path, [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', str(Path(path).parent), '-p', Path(path).name, '-v'], timeout=180)
    for path in sorted(s for s in tracked if re.fullmatch(r'tests/test_[^/]+\.sh', s)):
        run(path, ['bash', path])
    if Path('tests/firefox_i18n_behavior.cjs').exists():
        run('firefox-i18n-behavior', ['node', 'tests/firefox_i18n_behavior.cjs'])
    run('integrity-after', [sys.executable, '-B', 'tools/qikvrt_integrity.py', 'verify'])

if a.group == 'formal' and a.followup_only:
    # Successful builds and audits remain evidenced by the first exact-subject
    # run. This follow-up resolves only its missing Poppler / native-role checks.
    run('native-role-ontology', [sys.executable, '-B', 'scripts/verify_universal_ontology.py'], cwd=root / 'formalization/QIKVRT_Formalization_v2.0')
    try:
        lean_bin = subprocess.check_output(['lake', 'env', 'which', 'lean'], cwd=root / 'formalization/QIKVRT_Formalization_v2.0', text=True, env=env).strip()
    except (OSError, subprocess.CalledProcessError):
        lean_bin = '/unavailable/lean'
    for name in ('h5', 'qce'):
        paths = [s for s in tracked if s.startswith('docs/publications/') and s.endswith('/verify_' + name + '_package.py')]
        for path in paths:
            command = [sys.executable, '-B', path, '--lean', lean_bin]
            if name == 'qce':
                command += ['--axiom-output', str(out / 'qce-axioms.txt')]
            run('package-' + name, command, timeout=600)
    a.group = 'formal-followup-completed'

if a.group == 'formal':
    v1 = root / 'formalization/QIKVRT_Formalization_v1.0'
    run('formal-python-dependencies', [sys.executable, '-m', 'pip', 'install', '-r', str(v1 / 'requirements-dev.txt')])
    projects = sorted({str(Path(s).parent) for s in tracked if s.endswith('/lean-toolchain') and not s.startswith(('release/', 'incoming/', 'payload/'))})
    receipt['lean_project_inventory'] = projects
    for project in projects:
        run('lake-build-' + project, ['lake', 'build'], cwd=root / project, timeout=1200)
    run('v1-pytest', [sys.executable, '-m', 'pytest', '-q'], cwd=v1)
    v2 = root / 'formalization/QIKVRT_Formalization_v2.0'
    run('v2-python-tests', [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=v2)
    for script, args in [
        ('verify_source_lock.py', []), ('materialize_completion.py', ['--check']),
        ('render_completion_proof_map.py', ['--check']), ('render_completion_verification_report.py', ['--check']),
        ('validate_completion_claim_graph.py', []), ('validate_effect_ack_claims.py', []),
        ('verify_universal_ontology.py', []), ('audit_lean_axioms.py', []),
        ('audit_completion_axioms.py', []), ('audit_proof_escapes.py', []),
        ('materialize_completion_proof_manifest.py', ['--check'])]:
        run('v2-' + script, [sys.executable, '-B', 'scripts/' + script, *args], cwd=v2)
    for f in ['QIKVRTUniversalOntology/AxiomAudit.lean', 'QIKVRTUniversalOntology/ExtendedAxiomAudit.lean']:
        run('v2-' + f, ['lake', 'env', 'lean', f], cwd=v2)
    for label, directory, commands in [
        ('v1-node', v1, [['npm', 'ci'], ['npm', 'run', 'validate'], ['npm', 'run', 'test:negative']]),
        ('audio-tooling', root / 'tools/offline-audio-transcription', [['npm', 'ci'], ['npm', 'test'], ['bash', '-n', 'bin/transcribe-audio', 'scripts/install-model.sh']])]:
        for i, command in enumerate(commands):
            run(label + '-' + str(i), command, cwd=directory)
    for label, command in [
        ('v1-build-monolith', [sys.executable, 'scripts/build_monolith.py']),
        ('v1-kernel-monolith', ['bash', '-c', 'lake env lean --json build/All.lean > build/lean.stdout.jsonl']),
        ('v1-kernel-receipt', [sys.executable, 'scripts/make_lean_receipt.py', '--checker', 'Lean 4 native kernel', '--version', '4.19.0', '--commit', '6caaee842e9495688c1567e78c0e68dbb96942aa']),
        ('v1-package-checksums', [sys.executable, 'scripts/generate_checksums.py']),
        ('v1-node-gate20', ['npm', 'run', 'gate20']),
        ('v1-python-gate20', [sys.executable, '-m', 'python.gate20'])]:
        run(label, command, cwd=v1)
    try:
        lean_bin = subprocess.check_output(['lake', 'env', 'which', 'lean'], cwd=v2, text=True, env=env).strip()
    except (OSError, subprocess.CalledProcessError):
        lean_bin = '/unavailable/lean'
    for name in ('h5', 'h6', 'qce'):
        pattern = 'verify_' + name + '_package.py'
        matching = [s for s in tracked if s.startswith('docs/publications/') and s.endswith('/' + pattern)]
        for path in matching:
            command = [sys.executable, '-B', path, '--lean', lean_bin]
            if name == 'qce':
                command += ['--axiom-output', str(out / 'qce-axioms.txt')]
            run('package-' + name, command, timeout=600)

if a.group == 'native' and a.followup_only:
    # The prior run executed roundtrip, Smalltalk, Pascal, real mesh and byte
    # audit successfully; retry the reference corpus with its declared root.
    run('full-core-reference', [sys.executable, '-B', 'test_full.py'], cwd=root / 'next/reference/full-core-draft03')
    a.group = 'native-followup-completed'

if a.group == 'native':
    if Path('next/tools/bootstrap.py').exists():
        prefix = out / 'target-tools'
        run('frozen-predecessor', ['git', 'fetch', '--no-tags', '--depth=1', 'https://github.com/Goldkelch/qik-vrt.git', '26bc470bf553f471abc02e65950acaffb3e5302a'])
        ready = run('locked-target-bootstrap', [sys.executable, '-B', 'next/tools/bootstrap.py', '--prefix', str(prefix), '--install'], timeout=1200)
        if ready:
            run('roundtrip', ['bash', '-c', '. "$1/target-env.sh"; python3 -B roundtrip.py --repository "$2" --output-dir "$3"', 'selftest', str(prefix), a.repository, str(out / 'roundtrip')], timeout=1200)
        if Path('next/reference/full-core-draft03/test_full.py').exists():
            run('full-core-reference', [sys.executable, '-B', 'test_full.py'], cwd=root / 'next/reference/full-core-draft03')
    if Path('tools/qikvrt_smalltalk.py').exists():
        run('locked-smalltalk-bootstrap', [sys.executable, '-B', 'tools/qikvrt_smalltalk.py', 'install'], timeout=1200)
        run('smalltalk-test', ['make', 'smalltalk-test'])
    if Path('tools/qikvrt_c89_pascal_bridge.py').exists():
        run('pascal-bridge', [sys.executable, '-B', 'tools/qikvrt_c89_pascal_bridge.py'])
    if Path('tools/qikvrt_real_mesh_system_verification.py').exists():
        run('real-mesh-system', [sys.executable, '-B', 'tools/qikvrt_real_mesh_system_verification.py', 'run', '--source-head', a.head, '--source-tree', a.tree, '--workdir', str(out / 'real-mesh'), '--output', str(out / 'real-mesh-receipt.json')])
    if Path('tools/qikvrt_bit_audit.py').exists():
        run('all-tracked-byte-audit', [sys.executable, '-B', 'tools/qikvrt_bit_audit.py', '--head', a.head, '--receipt', str(out / 'bit-audit.json'), '--inventory', str(out / 'bit-inventory.jsonl')])

receipt['observed_head_after'] = git('rev-parse', 'HEAD')
receipt['observed_tree_after'] = git('rev-parse', 'HEAD^{tree}')
receipt['worktree_after'] = git('status', '--porcelain').splitlines()
receipt['state'] = 'PASS' if all(c['status'] == 'PASS' for c in checks if not c['informational']) else 'FAIL'
if receipt['observed_head_after'] != a.head or receipt['observed_tree_after'] != a.tree:
    receipt['state'] = 'SUBJECT_CHANGED'
save()
print(json.dumps({'state': receipt['state'], 'checks': len(checks), 'failed': [c['name'] for c in checks if c['status'] != 'PASS']}, sort_keys=True), flush=True)
raise SystemExit(0 if receipt['state'] == 'PASS' else 1)
