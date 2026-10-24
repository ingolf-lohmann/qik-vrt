#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Candidate-local deterministic archive and independent XeLaTeX rebuilds.

No network, submission, authorization consumption or protected-source writes.
Extends the frozen repository's archive/extract/build pattern for seven inputs.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MEMBERS = ('main.tex', 'orientation.tex', 'theory.tex', 'measurements.tex',
           'delivery.tex', 'appendix.tex', 'claim-scope.tex')
EPOCH = int(datetime(2026, 10, 3, tzinfo=timezone.utc).timestamp())
REUSE = ROOT / 'tools/materialize_arxiv_current_synthesis_v2.py'
spec = importlib.util.spec_from_file_location('qikvrt_arxiv_archive_pattern', REUSE)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)
identity = legacy.identity

def run(args, cwd=None, env=None):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=180)
    if p.returncode:
        raise RuntimeError(' '.join(args) + '\n' + (p.stdout + p.stderr)[-6000:])
    return p.stdout + p.stderr

def archive_bytes():
    buf = io.BytesIO()
    with gzip.GzipFile(filename='', mode='wb', fileobj=buf, mtime=EPOCH) as gz:
        with tarfile.open(fileobj=gz, mode='w', format=tarfile.USTAR_FORMAT) as a:
            for name in MEMBERS:
                b = (HERE / name).read_bytes()
                t = tarfile.TarInfo(name)
                t.size, t.mode, t.mtime = len(b), 0o644, EPOCH
                t.uid = t.gid = 0
                t.uname = t.gname = ''
                a.addfile(t, io.BytesIO(b))
    return buf.getvalue()

def extract(raw, directory):
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as a:
        members = a.getmembers()
        assert [m.name for m in members] == list(MEMBERS), 'unexpected archive members'
        for m in members:
            assert m.isfile() and '/' not in m.name and '\\' not in m.name, 'unsafe archive member'
            assert not m.issym() and not m.islnk()
            b = a.extractfile(m).read()
            assert b == (HERE / m.name).read_bytes(), 'archive/source mismatch'
            (directory / m.name).write_bytes(b)

def build(raw):
    with tempfile.TemporaryDirectory(prefix='qikvrt-arxiv-extraction-') as d:
        directory = Path(d)
        extract(raw, directory)
        env = os.environ.copy()
        env.update(SOURCE_DATE_EPOCH=str(EPOCH), FORCE_SOURCE_DATE='1', TZ='UTC', LC_ALL='C.UTF-8')
        for _ in range(3):
            run(['xelatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                 '-output-driver=xdvipdfmx -z0', 'main.tex'], cwd=directory, env=env)
        log = (directory / 'main.log').read_text(errors='replace').replace(str(directory), '<isolated-build>')
        forbidden = ('Missing character:', 'Undefined control sequence', 'Emergency stop', 'Fatal error occurred', 'There were undefined references', 'Rerun to get', 'Label(s) may have changed')
        assert not any(s in log for s in forbidden), 'unresolved build diagnostic'
        return (directory / 'main.pdf').read_bytes(), log

def check_scope_inputs():
    provenance = json.loads((HERE / 'SOURCE_PROVENANCE.json').read_text())
    for item in provenance['inputs'] + provenance['protected_original_artifacts']:
        assert identity(ROOT / item['path'])['sha256'] == item['sha256'], item['path']
    for name in MEMBERS[1:-1]:
        source = next(x for x in provenance['inputs'] if x['path'].endswith('/' + name))
        assert identity(HERE / name)['sha256'] == source['sha256'], name
    for name in ['CLAIM_MATRIX.json', 'METHOD_CLAIM_BOUNDARIES.md']:
        source = next(x for x in provenance['inputs'] if x['path'].endswith('/' + name))
        assert identity(HERE / name)['sha256'] == source['sha256'], name
    matrix = json.loads((HERE / 'CLAIM_MATRIX.json').read_text())
    assert len(matrix['claims']) == 30
    assert not any(x['classification'] == 'FORMAL_PROVED' for x in matrix['claims'])
    main = (HERE / 'main.tex').read_text()
    original_main = next(x for x in provenance['inputs'] if x['path'].endswith('/main.tex'))
    derived = (ROOT / original_main['path']).read_text()
    for change in provenance['transformations']:
        assert derived.count(change['from']) == 1
        derived = derived.replace(change['from'], change['to'])
    assert main == derived, 'main.tex differs from declared mechanical derivation'
    declared = re.findall(r'\\input\{([^}]+)\}', main)
    assert declared == list(MEMBERS[1:]), declared
    assert '/usr/' not in main and 'write18' not in main
    assert 'Noto Serif' not in main and '\\setmainfont{lmroman10-regular.otf}' in main
    for name in MEMBERS:
        text = (HERE / name).read_text()
        assert not re.search(r'\\(?:includegraphics|include|bibliography)\s*\{', text), name

def save(name, data, write):
    path = HERE / name
    if write:
        path.write_bytes(data)
    else:
        assert path.read_bytes() == data, 'fresh bytes differ: ' + name

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    assert args.write != args.check, 'choose exactly one of --write or --check'
    check_scope_inputs()
    raw = archive_bytes()
    assert raw == archive_bytes(), 'non-deterministic archive'
    save('arxiv-source.tar.gz', raw, args.write)
    first, log = build(raw)
    second, _ = build(raw)
    assert first == second, 'independent extracted builds differ'
    save('main.pdf', first, args.write)
    if args.write:
        (HERE / 'XELATEX_BUILD_LOG.txt').write_text(log)
    with tempfile.TemporaryDirectory(prefix='qikvrt-arxiv-pdf-check-') as d:
        tmp = Path(d)
        info = run(['pdfinfo', str(HERE / 'main.pdf')])
        fonts = run(['pdffonts', str(HERE / 'main.pdf')])
        run(['pdftotext', '-layout', str(HERE / 'main.pdf'), str(tmp / 'text.txt')])
        text = (tmp / 'text.txt').read_text()
        assert all('C' + str(n).zfill(2) in text for n in range(1, 31)), 'claim appendix not rendered'
        assert 'NICHT EINGEREICHT' in text and 'STAGING / GELTUNG' in text
        pages = int(re.search(r'^Pages:\s+(\d+)', info, re.M).group(1))
        assert re.search(r'^JavaScript:\s+no', info, re.M), 'unexpected PDF JavaScript'
        run(['pdftoppm', '-r', '90', '-png', str(HERE / 'main.pdf'), str(tmp / 'page')])
        rendered = sorted(tmp.glob('page-*.png'))
        assert len(rendered) == pages
        images = [identity(p) for p in rendered]
    warnings = [line.strip() for line in log.splitlines() if 'Warning' in line or 'Overfull' in line]
    validation = {
        'schema': 'qikvrt_arxiv_local_compatibility_validation_v1',
        'status': 'LOCAL_BUILD_VERIFIED_SERVER_BUILD_NOT_OBSERVED',
        'observed_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'deterministic archive, source closure, repeat extraction/build and local PDF; not scientific replication or destination acceptance',
        'source_archive': {**identity(HERE / 'arxiv-source.tar.gz'), 'members': list(MEMBERS), 'gzip_mtime': EPOCH, 'tar_format': 'USTAR', 'deterministic_repeat': True},
        'build': {'engine': 'XeLaTeX', 'version': run(['xelatex', '--version']).splitlines()[0], 'command': f'SOURCE_DATE_EPOCH={EPOCH} FORCE_SOURCE_DATE=1 TZ=UTC LC_ALL=C.UTF-8 xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-driver="xdvipdfmx -z0" main.tex', 'passes': 3, 'independent_builds': 2, 'pdf_byte_identical': True, 'warnings_after_final_pass': warnings, 'network_access': False, 'shell_escape': False},
        'output_pdf': {**identity(HERE / 'main.pdf'), 'page_count': pages},
        'bibliography': {'embedded_source': 'appendix.tex', 'reused_unchanged': True},
        'font_policy': {'filename_lookup': True, 'font_binaries_in_archive': False, 'absolute_font_paths': False, 'fonts': ['Latin Modern Roman', 'Latin Modern Sans', 'Latin Modern Mono', 'Latin Modern Math']},
        'poppler_pdfinfo': info, 'poppler_fonts': fonts,
        'visual_render': {'renderer': 'Poppler pdftoppm', 'dpi': 90, 'pages_rendered': pages, 'temporary_page_identities': images, 'human_or_ai_visual_review': 'RECORDED_SEPARATELY_IN_PDF_RENDER_VALIDATION.json'},
        'claim_boundaries_embedded': True, 'formal_proved_claim_count': 0,
        'arxiv_server_build_verified': False, 'submission_performed': False, 'authorization_consumed': False,
        'reused_identity_primitive': {'path': str(REUSE.relative_to(ROOT)), **{k:v for k,v in identity(REUSE).items() if k!='path'}}
    }
    if args.write:
        (HERE / 'BUILD_VALIDATION.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2) + '\n')
        m = json.loads((HERE / 'arxiv_submission_manifest.json').read_text())
        m['artifact_bindings'] = {name: identity(HERE / name) for name in [*MEMBERS, 'main.pdf', 'arxiv-source.tar.gz', 'CLAIM_MATRIX.json', 'METHOD_CLAIM_BOUNDARIES.md', 'CHANGE_NOTICE.md', 'SOURCE_PROVENANCE.json', 'STAGING_README.md', 'build.py', 'XELATEX_BUILD_LOG.txt', 'BUILD_VALIDATION.json']}
        m['build'] = {**validation['build'], 'result': 'SUCCESS_LOCAL', 'page_count': pages}
        (HERE / 'arxiv_submission_manifest.json').write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n')
    else:
        m = json.loads((HERE / 'arxiv_submission_manifest.json').read_text())
        assert m['effects']['arxiv_submission'] is False
        for name, item in m['artifact_bindings'].items():
            assert identity(HERE / name)['sha256'] == item['sha256'], name
    print(json.dumps({'archive_sha256': identity(HERE / 'arxiv-source.tar.gz')['sha256'], 'pdf_sha256': identity(HERE / 'main.pdf')['sha256'], 'pages': pages, 'repeat_build_byte_identical': True, 'warnings': warnings, 'submission': False}))

if __name__ == '__main__':
    main()
