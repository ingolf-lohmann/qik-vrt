#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the bounded main successor offline, without importing the old stack."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_integrity as integrity

V3 = 'publication-staging/ietf-epistemic-status-00-reconciled-20261005-v3'
POST = 'external/ietf/epistemic-status-00-post-effect-169906-20261006-v1'
DEST = 'external/ietf/epistemic-status-00-main-successor-20261006-v1'
BASE = '71f8c15319bf79456ac177d80941b4f59d372996'
SOURCE = 'c3de0a29d27702dfe7a39279017fea59ae905346'
SOURCE_TREE = '743c0fc49cdb1536f84271acb6167f0f1931c191'
NAME = 'draft-lohmann-qikvrt-epistemic-status-00'
EXTRA = {
    DEST+'/SOURCE_GIT_CAPSULE.json', DEST+'/SUCCESSOR_PROVENANCE.json',
    DEST+'/README.md', DEST+'/verify_successor.py',
    'state/work_units/PR452_IETF169906_MAIN_SUCCESSOR_20261006_V1.json',
    'Makefile', 'REPOSITORY_FILE_MANIFEST.json',
    'REPOSITORY_FILE_MANIFEST.json.sha256', 'SHA256SUMS.txt',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(*args):
    return integrity._git(ROOT, *args).decode().strip()


def check_identity(data, item):
    observed = {
        'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
        'git_blob_sha1': hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
    }
    require(all(observed[k] == item[k] for k in observed), 'artifact identity drift')


def check_paths(imported, changed):
    require(len(imported) == 35 and len(set(imported)) == 35, 'import count or duplicate drift')
    require(sum(p.startswith(V3+'/') for p in imported) == 26, 'v3 scope drift')
    require(sum(p.startswith(POST+'/') for p in imported) == 9, 'post-effect scope drift')
    require(set(changed) <= set(imported) | EXTRA, 'off-scope path imported')


def check_projection(checkout, subject, parents, base, checkout_tree, subject_tree):
    require(parents == [base, subject], 'unbound PR merge projection parents')
    require(checkout != subject and checkout_tree == subject_tree,
            'PR merge projection differs from the exact candidate tree')


def checksums(directory):
    listed = set()
    for line in (directory/'SHA256SUMS').read_text().splitlines():
        expected, path = line.split('  ', 1)
        pp = Path(path)
        require(not pp.is_absolute() and '..' not in pp.parts, 'unsafe checksum path')
        require(path not in listed, 'duplicate checksum path')
        listed.add(path)
        require(hashlib.sha256((directory/pp).read_bytes()).hexdigest() == expected,
                'checksum drift: '+path)
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts}
    require(listed == actual - {'SHA256SUMS'}, 'checksum coverage drift')


def verify(candidate_worktree=False, negative_controls=False):
    provenance = json.loads((HERE/'SUCCESSOR_PROVENANCE.json').read_text())
    require(provenance['base']['head'] == BASE, 'base binding drift')
    require(provenance['source']['commit_sha1'] == SOURCE and
            provenance['source']['root_tree_sha1'] == SOURCE_TREE, 'source binding drift')
    require(provenance['evidence_semantics']['predecessor_evidence_transfer'] is False,
            'predecessor evidence transfer')
    checkout = git('rev-parse', 'HEAD^{commit}')
    tree = git('rev-parse', 'HEAD^{tree}')
    head = checkout
    projection = False
    # Some existing workflows check out GitHub's temporary refs/pull/N/merge.
    # This service projection is not candidate ancestry. Bind its real event
    # parents and require exact candidate-tree identity before using its files.
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request' and event_path:
        event = json.loads(Path(event_path).read_text())
        pr = event['pull_request']
        require(pr['base']['ref'] == 'main', 'PR event is not based on main')
        event_head = pr['head']['sha']
        if checkout != event_head:
            subject_tree = git('rev-parse', event_head+'^{tree}')
            check_projection(checkout, event_head, git('show','-s','--format=%P',checkout).split(),
                             pr['base']['sha'], tree, subject_tree)
            head = event_head
            projection = True
    if not candidate_worktree:
        require(head != BASE, 'successor commit is not yet created')
        require(not git('diff', '--name-only', 'HEAD'), 'subject worktree differs from HEAD')
    git('merge-base', '--is-ancestor', BASE, head)
    ancestry = git('rev-list', '--parents', BASE+'..'+head).splitlines()
    require(all(len(row.split()) == 2 for row in ancestry), 'nonlinear old-stack ancestry imported')
    changed = git('diff', '--name-only', BASE).splitlines() if candidate_worktree else git(
        'diff', '--name-only', BASE, head).splitlines()
    imported = [x['path'] for x in provenance['imports']]
    check_paths(imported, changed)
    require(set(provenance['allowed_changed_paths']) == set(imported) | EXTRA,
            'allowlist definition drift')
    capsule = integrity.load_portable_git_source_capsule(
        ROOT, DEST+'/SOURCE_GIT_CAPSULE.json',
        expected_binding=provenance['import_source_capsule'])
    require(capsule.commit_sha1 == SOURCE and capsule.root_tree_sha1 == SOURCE_TREE,
            'source closure binding drift')
    integrity.cross_check_portable_git_source_capsule(ROOT, capsule)
    require(set(capsule.files) == set(imported), 'import closure scope drift')
    for item in provenance['imports']:
        data = (ROOT/item['path']).read_bytes()
        check_identity(data, item)
        require(data == capsule.files[item['path']], 'source/import byte difference')
        if not candidate_worktree:
            require(git('ls-tree', 'HEAD', '--', item['path']).split()[0] == item['mode'],
                    'source/import mode difference')
    checksums(ROOT/V3)
    checksums(ROOT/POST)

    # Reuse the frozen validator's semantic and derivation checks. Its original
    # full main() also requires off-scope Collective PDFs/ZIPs. Their historical
    # bindings are retained unchanged, and are not current successor evidence.
    spec = importlib.util.spec_from_file_location('frozen_ietf_v3', ROOT/V3/'verify_staging.py')
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)
    manifest = json.loads((ROOT/V3/'SUBMISSION_MANIFEST.json').read_text())
    validation.boundaries(manifest)
    original = integrity.load_portable_git_source_capsule(ROOT, V3+'/SOURCE_GIT_CAPSULE.json')
    integrity.cross_check_portable_git_source_capsule(ROOT, original)
    with tempfile.TemporaryDirectory() as temp:
        validation.ROOT = Path(temp)
        source_path = 'external/ietf/'+NAME+'.xml'
        derivation = json.loads((ROOT/V3/'DERIVATION_MAP.json').read_text())
        path = validation.ROOT/derivation['source_repository_path']
        path.parent.mkdir(parents=True)
        path.write_bytes(original.files[source_path])
        semantic = validation.content_checks(manifest)
    post = json.loads((ROOT/POST/'POST_EFFECT_RECEIPT.json').read_text())
    status = json.loads((ROOT/POST/'public/submission-status.json').read_text())
    require(str(status['id']) == '169906' and status['state'] == 'posted', 'archived status drift')
    for kind, artifact in post['artifacts'].items():
        check_identity((ROOT/artifact['local']['path']).read_bytes(), artifact['local'])
        check_identity((ROOT/artifact['public']['path']).read_bytes(), artifact['public'])
    for kind in ['xml','txt']:
        require((ROOT/V3/(NAME+'.'+kind)).read_bytes() ==
                (ROOT/POST/'public'/(NAME+'.'+kind)).read_bytes(), 'published contribution drift')
    local_html = (ROOT/V3/(NAME+'.html')).read_bytes()
    public_html = (ROOT/POST/'public'/(NAME+'.html')).read_bytes()
    require(local_html != public_html, 'server derivation boundary erased')
    body = lambda data: re.search(rb'<body\b[^>]*>.*?</body>', data, re.S).group(0)
    require(body(local_html) == body(public_html), 'server body differs')
    require(hashlib.sha256(body(local_html)).hexdigest() ==
            '5a2cb214e9d282d1b227065f059e7159658bc02d69612d522572680379e13191', 'body identity drift')

    controls = []
    if negative_controls:
        def denied(label, fn):
            try:
                fn()
            except (ValueError, AssertionError):
                controls.append(label)
            else:
                raise ValueError('negative control accepted: '+label)
        denied('off-scope-collective-import-rejected', lambda: check_paths(
            imported, changed+['docs/publications/2026-10-03-qik-vrt-collective-functional-consciousness/README.md']))
        item = provenance['imports'][0]
        denied('mutated-import-rejected', lambda: check_identity((ROOT/item['path']).read_bytes()+b'x', item))
        altered = copy.deepcopy(manifest)
        altered['published'] = True
        denied('historical-pending-publication-flag-rejected', lambda: validation.boundaries(altered))
        check_projection('projection', 'subject', ['base','subject'], 'base', 'tree','tree')
        denied('merge-projection-tree-drift-rejected', lambda: check_projection(
            'projection','subject',['base','subject'],'base','other-tree','tree'))
        denied('merge-projection-extra-parent-rejected', lambda: check_projection(
            'projection','subject',['base','old-stack','subject'],'base','tree','tree'))
        with tempfile.TemporaryDirectory() as temp:
            temporary_root = Path(temp)
            value = json.loads((HERE/'SOURCE_GIT_CAPSULE.json').read_text())
            variants = []
            changed_capsule = copy.deepcopy(value)
            changed_capsule['authority_source']['commit_sha1'] = '0'*40
            variants.append(('source-head-drift-rejected', changed_capsule))
            changed_capsule = copy.deepcopy(value)
            changed_capsule['objects'][0]['payload_base64'] = 'YQ=='
            variants.append(('source-payload-tamper-rejected', changed_capsule))
            changed_capsule = copy.deepcopy(value)
            changed_capsule['objects'] = [o for o in changed_capsule['objects']
                                          if o['sha1'] != SOURCE_TREE]
            variants.append(('missing-source-root-tree-rejected', changed_capsule))
            for label, value in variants:
                (temporary_root/'capsule.json').write_text(json.dumps(value))
                denied(label, lambda: integrity.load_portable_git_source_capsule(
                    temporary_root, 'capsule.json'))
    return {
        'schema':'qikvrt_ietf_main_successor_verification_v1',
        'result':'PASS_BOUNDED_MAIN_SUCCESSOR_FIXITY_PROVENANCE_AND_SEMANTICS',
        'subject':{'repository':'ingolf-lohmann/qik-vrt','head':head,'tree':tree,
                   'checkout_head':checkout,'byte_identical_pr_merge_projection':projection,
                   'candidate_worktree':candidate_worktree,'base':BASE},
        'changed_paths':changed,'source_bound_imports':35,'source_capsule_objects':len(capsule.objects),
        'semantic_negative_controls':semantic['semantic_negative_controls'],
        'successor_negative_controls':controls,'derivation_operations':semantic['derivation_operations'],
        'rendered_paragraphs_checked':semantic['rendered_paragraphs_checked'],
        'html_fragment_links_resolved':semantic['html_fragment_links_resolved'],
        'xml_txt_byte_exact':True,'server_html_full_byte_identity':False,'server_html_body_byte_exact':True,
        'fresh_renderer_executed':False,'fresh_public_provider_readback_performed':False,
        'historical_protected_collective_artifacts_checked_as_current_worktree':False,
        'predecessor_evidence_transfer':False,'merge_or_publication_performed':False,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate-worktree', action='store_true')
    parser.add_argument('--negative-controls', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.candidate_worktree, args.negative_controls), sort_keys=True))
