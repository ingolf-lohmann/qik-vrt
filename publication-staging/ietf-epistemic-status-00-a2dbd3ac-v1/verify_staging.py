#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check package fixity, source closure and denied submission boundaries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools import qikvrt_integrity as integrity

def identity(p):
    b = p.read_bytes()
    return {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()}

def boundaries(m):
    assert m['schema'] in ['qikvrt_arxiv_submission_manifest_v1', 'qikvrt_ietf_draft_candidate_v1']
    assert all(v is False for v in m['effects'].values()), 'forbidden publication/effect flag'
    assert m['authorization_boundary']['current_authorization_state'] == 'STAGING_ONLY_NOT_AN_UPLOAD_DECISION'
    if m['schema'] == 'qikvrt_ietf_draft_candidate_v1':
        assert m['datatracker_submission_performed'] is False and m['submitted'] is False and m['published'] is False
        assert m['consensus'] is False
    else:
        assert m['claim_boundaries']['formal_proved_claim_count'] == 0
        assert m['arxiv_metadata_candidate']['server_build_verified'] is False

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--negative-controls', action='store_true')
    args = p.parse_args()
    name = 'arxiv_submission_manifest.json' if (HERE / 'arxiv_submission_manifest.json').exists() else 'SUBMISSION_MANIFEST.json'
    m = json.loads((HERE / name).read_text())
    boundaries(m)
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        expected, path = line.split('  ', 1)
        pp = Path(path)
        assert not pp.is_absolute() and '..' not in pp.parts
        assert identity(HERE / pp)['sha256'] == expected, path
    receipt = json.loads((HERE / 'STAGING_RETURN_RECEIPT.json').read_text())
    for item in receipt['returned_artifacts']:
        observed = identity(HERE / item['path'])
        assert all(observed[k] == item[k] for k in observed), item['path']
    for item in receipt['protected_original_artifacts']:
        observed = identity(ROOT / item['path'])
        assert all(observed[k] == item[k] for k in observed), item['path']
    cap_path = HERE / 'SOURCE_GIT_CAPSULE.json'
    assert all(identity(cap_path)[k] == m['portable_source_binding'][k] for k in identity(cap_path))
    cap = integrity.load_portable_git_source_capsule(ROOT, str(cap_path.relative_to(ROOT)))
    integrity.cross_check_portable_git_source_capsule(ROOT, cap)
    assert cap.commit_sha1 == 'a2dbd3ac25c2935a022ea8ef54d95912e34035f7'
    controls = []
    if args.negative_controls:
        changed = copy.deepcopy(m)
        changed['effects']['arxiv_submission'] = True
        try:
            boundaries(changed)
        except AssertionError:
            controls.append('forbidden-submission-flag-rejected')
        else:
            raise AssertionError('forbidden submission accepted')
        value = json.loads((HERE / 'SOURCE_GIT_CAPSULE.json').read_text())
        variants = []
        changed = copy.deepcopy(value)
        changed['authority_source']['commit_sha1'] = '0' * 40
        variants.append(('changed-source-head-rejected', changed))
        changed = copy.deepcopy(value)
        changed['objects'][0]['payload_base64'] = 'YQ=='
        variants.append(('tampered-object-payload-rejected', changed))
        changed = copy.deepcopy(value)
        changed['objects'] = [o for o in changed['objects'] if o['sha1'] != cap.root_tree_sha1]
        variants.append(('missing-root-tree-rejected', changed))
        transient = ROOT / '.qikvrt/runtime'
        transient.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=transient, prefix='staging-negative-') as d:
            path = Path(d) / 'invalid-capsule.json'
            for label, changed in variants:
                path.write_text(json.dumps(changed))
                try:
                    integrity.load_portable_git_source_capsule(ROOT, str(path.relative_to(ROOT)))
                except ValueError:
                    controls.append(label)
                else:
                    raise AssertionError(label + ' was accepted')
        assert len(controls) == 4
    print(json.dumps({'scope': 'staging package only', 'result': 'PASS_FIXITY_SOURCE_CLOSURE_AND_NO_SUBMISSION_FLAGS',
                      'manifest': name, 'manifest_sha256': identity(HERE / name)['sha256'],
                      'source_head': cap.commit_sha1, 'source_tree': cap.root_tree_sha1,
                      'negative_controls': controls, 'publication_or_scientific_proof_claimed': False}))

if __name__ == '__main__':
    main()
