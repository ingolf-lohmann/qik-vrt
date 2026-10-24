#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repeat exact-source -00 TXT/HTML renders with isolated offline caches."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NAME = 'draft-lohmann-qikvrt-epistemic-status-00'
XML = HERE / (NAME + '.xml')
REUSE = ROOT / 'tools/materialize_ietf_current_synthesis_candidate.py'
spec = importlib.util.spec_from_file_location('qikvrt_locked_ietf_pattern', REUSE)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
identity = legacy.digest
EXPECTED_WARNINGS = set()

def run(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=180,
                       env={**os.environ, 'PYTHONNOUSERSITE': '1', 'TZ': 'UTC'})
    if p.returncode:
        raise RuntimeError(' '.join(args) + '\n' + (p.stdout + p.stderr)[-6000:])
    return p.stdout + p.stderr

def render(tool, directory, mode):
    cache = directory / ('cache-' + mode)
    shutil.copytree(HERE / 'bibxml', cache)
    output = directory / (NAME + ('.txt' if mode == 'text' else '.html'))
    command = [str(tool), str(XML), '--v3', '--' + mode, '--no-network',
               '--skip-config-files', '--warn-bare-unicode', '--cache', str(cache),
               '--date', '2026-10-04', '--verbose', '--out', str(output)]
    diagnostics = run(command).replace(str(HERE), '<staging>').replace(str(directory), '<isolated-render>')
    warnings = re.findall(r'Warning: Unused reference: There seems to be no reference to \[(RFC\d+)\]', diagnostics)
    assert set(warnings) == EXPECTED_WARNINGS and len(warnings) == 0, diagnostics
    assert diagnostics.count('Warning:') == 0 and 'Error:' not in diagnostics, diagnostics
    raw = output.read_bytes()
    assert all(s.encode() in raw for s in ['FORMAL_PROVED', 'EMPIRICALLY_EVIDENCED', 'SOURCE_BOUND', 'INTERPRETATIVE', 'NORMATIVE', 'PREDICTED', 'OPEN'])
    return raw, diagnostics, warnings

def save(name, data, write):
    if write:
        (HERE / name).write_bytes(data)
    else:
        assert (HERE / name).read_bytes() == data, 'fresh bytes differ: ' + name

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xml2rfc', type=Path, required=True)
    p.add_argument('--write', action='store_true')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    assert args.write != args.check
    tool = args.xml2rfc.resolve(strict=True)
    legacy.check_renderer(tool)
    provenance = json.loads((HERE / 'SOURCE_PROVENANCE.json').read_text())
    derivation = json.loads((HERE / 'DERIVATION_MAP.json').read_text())
    original = ROOT / derivation['source_repository_path']
    assert identity(original)['sha256'] == derivation['source']['sha256']
    transformed = original.read_text()
    for operation in derivation['operations']:
        transformed = transformed.replace(operation['from'], operation['to'], operation['count'])
    assert XML.read_text() == transformed
    assert identity(XML)['sha256'] == derivation['successor']['sha256']
    for item in provenance['inputs'] + provenance['protected_original_artifacts']:
        assert identity(ROOT / item['path'])['sha256'] == item['sha256']
    for item in provenance['bibliography_inputs']:
        assert identity(HERE / item['path'])['sha256'] == item['sha256']
    outputs, logs = {}, {}
    for mode in ['text', 'html']:
        with tempfile.TemporaryDirectory(prefix='qikvrt-ietf-render-a-') as a, tempfile.TemporaryDirectory(prefix='qikvrt-ietf-render-b-') as b:
            first, diagnostic, warnings = render(tool, Path(a), mode)
            second, _, _ = render(tool, Path(b), mode)
        assert first == second, 'independent offline renders differ: ' + mode
        ext = '.txt' if mode == 'text' else '.html'
        save(NAME + ext, first, args.write)
        if args.write:
            (HERE / ('XML2RFC_' + mode.upper() + '_LOG.txt')).write_text(diagnostic)
        outputs[mode] = {**identity(HERE / (NAME + ext)), 'repeat_render_byte_identical': True}
        logs[mode] = {'warnings': warnings, 'warning_count': 0, 'errors': 0}
    parser = legacy.TextExtractor()
    parser.feed((HERE / (NAME + '.html')).read_text())
    parser.close()
    text = ' '.join(parser.fragments)
    assert 'Security Considerations' in text and 'Non-Goals' in text
    assert 'phenomenal consciousness' in text and 'does not, by itself' in text
    max_line, pages = legacy.line_count((HERE / (NAME + '.txt')).read_bytes())
    assert max_line <= 72, max_line
    requirements = ROOT / 'runtime/toolchains/requirements-xml2rfc-3.34.0.txt'
    pins = dict(re.findall(r'^([a-zA-Z0-9-]+)==([^\s\\]+)', requirements.read_text(), re.M))
    python = tool.parent / 'python'
    package_probe = 'import importlib.metadata as m,json,platform; print(json.dumps({"python":platform.python_version(),"packages":{n:m.version(n) for n in ' + repr(list(pins)) + '}}))'
    installed = json.loads(run([str(python), '-I', '-c', package_probe]))
    assert installed['packages'] == pins, 'not the exact 19-package lock'
    validation = {
        'schema': 'qikvrt_ietf_render_validation_v1',
        'state': 'RENDER_VERIFIED_ZERO_WARNINGS_AUTHOR_REVIEW_REQUIRED',
        'observed_utc': datetime.now(timezone.utc).isoformat(),
        'source_date': '2026-10-04', 'renderer_date': '2026-10-04',
        'source_xml': identity(XML), 'source_xml_byte_identical': False, 'frozen_source_preserved': True, 'declared_derivation_verified': True,
        'toolchain': {'xml2rfc': '3.34.0', 'python_observed': installed['python'],
                      'python_historical_lock': '3.12.13',
                      'historical_python_patch_reproduced': installed['python'] == '3.12.13',
                      'python_patch_boundary': 'Local reproducibility is verified on the recorded interpreter. The frozen full-runtime patch pin is not promoted to reproduced when different.',
                      'packages': installed['packages'], 'requirements': identity(requirements),
                      'requirements_hash_locked_install': True, 'network_access_during_render': False,
                      'configuration_files_skipped': True, 'isolated_caches_per_run_and_mode': True},
        'bibliography_inputs': provenance['bibliography_inputs'],
        'validation': {'rfcxml_v3_schema_and_preptool': 'SUCCESS_BY_XML2RFC',
                       'txt': outputs['text'], 'html': outputs['html'],
                       'diagnostics': logs, 'expected_warning_ids': sorted(EXPECTED_WARNINGS),
                       'txt_max_line_width': max_line, 'txt_page_count': pages,
                       'html_parse': 'PASS', 'seven_statuses_present_in_both_outputs': True,
                       'prepped_xml_digest_claimed': False,
                       'semantic_profile_validation_or_interoperability_claimed': False},
        'warning_disposition': 'Explicit normative RFC xrefs remove both unused-reference causes. No diagnostics are suppressed; zero warnings and errors are required.',
        'submission_performed': False, 'upload_authorization_consumed': False,
        'reused_version_identity_parser_primitives': {'path': str(REUSE.relative_to(ROOT)), **{k:v for k,v in identity(REUSE).items() if k!='path'}}
    }
    if args.write:
        (HERE / 'RENDER_VALIDATION.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
        m = json.loads((HERE / 'SUBMISSION_MANIFEST.json').read_text())
        m['artifacts'] = {name: identity(HERE / name) for name in [NAME + '.xml', NAME + '.txt', NAME + '.html', 'RENDER_VALIDATION.json', 'SOURCE_PROVENANCE.json', 'DERIVATION_MAP.json', 'CHANGE_NOTICE.md', 'CONTENT_VALIDATION.json', 'STAGING_README.md', 'build.py', 'XML2RFC_TEXT_LOG.txt', 'XML2RFC_HTML_LOG.txt', 'bibxml/reference.RFC.2119.xml', 'bibxml/reference.RFC.8174.xml']}
        m['toolchain'] = validation['toolchain']
        m['render_status'] = validation['state']
        (HERE / 'SUBMISSION_MANIFEST.json').write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')
    else:
        m = json.loads((HERE / 'SUBMISSION_MANIFEST.json').read_text())
        assert m['datatracker_submission_performed'] is False
        for name, item in m['artifacts'].items():
            assert identity(HERE / name)['sha256'] == item['sha256'], name
    print(json.dumps({'txt': outputs['text'], 'html': outputs['html'], 'repeat_render_byte_identical': True, 'warning_count_per_mode': 0, 'submission': False}))

if __name__ == '__main__':
    main()
