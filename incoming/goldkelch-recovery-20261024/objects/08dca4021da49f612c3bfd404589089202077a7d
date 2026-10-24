#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check package fixity, source closure and denied submission boundaries."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
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

def content_checks(m):
    """Check the complete translation partition and preserved source dispositions.

    Structural/fixity checks support the recorded editorial review; they do not
    prove semantic equivalence of unrestricted natural-language statements.
    """
    mapping = json.loads((HERE / 'TRANSLATION_MAP.json').read_text())
    matrix = json.loads((HERE / 'CLAIM_MATRIX.json').read_text())
    correspondence = json.loads((HERE / 'CLAIM_CORRESPONDENCE_EN.json').read_text())
    assert mapping['complete_english_version'] and mapping['historical_state_preserved']
    assert mapping['new_trials_or_kernel_proofs'] is False
    assert mapping['predecessor_evidence_transfer'] is False
    assert mapping['human_acceptance'] == 'PENDING'
    total = 0
    def blocks(text):
        cuts = [0] + [x.start() for x in re.finditer(r'\\(?:chapterpage|subsection\*?)\{', text) if x.start()] + [len(text)]
        return [text[a:b] for a, b in zip(cuts, cuts[1:])]
    for file in mapping['files']:
        original = ROOT / file['source_repository_path']
        successor = HERE / file['english']['path']
        for path, recorded in [(original, file['source']), (successor, file['english'])]:
            assert all(identity(path)[k] == recorded[k] for k in identity(path))
        old, new = original.read_text(), successor.read_text()
        aa, bb = blocks(old), blocks(new)
        assert len(aa) == len(bb) == len(file['ordered_blocks'])
        assert file['complete_partition'] is True
        assert file['source_block_count'] == file['english_block_count'] == len(aa)
        for i, (source, english, binding) in enumerate(zip(aa, bb, file['ordered_blocks'])):
            assert binding['index'] == i
            assert hashlib.sha256(source.encode()).hexdigest() == binding['source_text_sha256']
            assert hashlib.sha256(english.encode()).hexdigest() == binding['english_text_sha256']
        assert re.findall(r'\\chapterpage\{([^}]+)\}', old) == file['chapter_anchors'] == re.findall(r'\\chapterpage\{([^}]+)\}', new)
        references = lambda s: [x.replace('–', '--').replace('−', '--') for x in re.findall(r'\\src\{([^}]+)\}', s)]
        assert references(old) == references(new)
        assert set(re.findall(r'\b[0-9a-f]{40,64}\b', old)) <= set(re.findall(r'\b[0-9a-f]{40,64}\b', new))
        total += len(aa)
    assert total == 94 and len(mapping['files']) == 7
    rows = re.findall(r'^(C\d\d) & \\code\{([^}]+)\} & (.*?) \\\\\s*$', (HERE / 'claim-scope.tex').read_text(), re.M)
    assert len(matrix['claims']) == len(correspondence['claims']) == len(rows) == 30
    counts = {}
    for original, english, row in zip(matrix['claims'], correspondence['claims'], rows):
        expected_row = english['english_statement_tex'] + r' \newline\emph{Scope:} ' + english['english_scope_tex']
        assert row == (original['claim_id'], original['classification'], expected_row)
        for field in ['claim_id', 'classification', 'status', 'sources', 'proof_refs']:
            assert original[field] == english[field]
        assert original['statement'] == english['frozen_source_statement']
        assert original['boundary'] == english['frozen_source_boundary']
        raw = json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
        assert hashlib.sha256(raw).hexdigest() == english['source_claim_sha256']
        assert english['source_disposition_preserved'] and english['new_proof_or_empirical_status_inferred'] is False
        counts[original['classification']] = counts.get(original['classification'], 0) + 1
    assert counts == {'NORMATIVE': 4, 'SOURCE_BOUND': 10, 'INTERPRETATIVE': 9, 'OPEN': 5, 'EMPIRICALLY_EVIDENCED': 2}
    assert m['title'] == m['arxiv_metadata_candidate']['title']
    assert m['abstract'] == m['arxiv_metadata_candidate']['abstract']
    assert m['title'].isascii() and m['abstract'].isascii() and 500 < len(m['abstract']) <= 1920
    assert m['arxiv_metadata_candidate']['language'] == 'en'
    assert 'historical' in (HERE / 'orientation.tex').read_text()
    assert 'without repeating timing trials' in (HERE / 'claim-scope.tex').read_text()
    old_measurements = (ROOT / m['predecessor']['package'] / 'measurements.tex').read_text()
    new_measurements = (HERE / 'measurements.tex').read_text()
    def numeric_rows(text, german):
        result = []
        for line in text.splitlines():
            if re.match(r'^\d[\d.,]* & \d+\\%', line):
                cells = [c.strip() for c in line.split('&')[:5]]
                result.append([int(re.sub(r'[.,]', '', cells[0])), int(cells[1].removesuffix(r'\%'))] + [float(x.replace(',', '.') if german else x) for x in cells[2:]])
        return result
    assert len(numeric_rows(old_measurements, True)) == 9
    assert numeric_rows(old_measurements, True) == numeric_rows(new_measurements, False)
    return {'complete_partition_blocks': total, 'tex_inputs': 7, 'claims': 30, 'classifications': counts,
            'numeric_median_table_rows_preserved': 9, 'source_reference_order_preserved': True,
            'historical_identifiers_preserved': True, 'title_and_abstract_bound': True,
            'formal_proved_claims': 0, 'natural_language_semantic_equivalence_formally_proved': False}

def successor_bindings(m):
    provenance = json.loads((HERE / 'SOURCE_PROVENANCE.json').read_text())
    assert provenance['candidate_id'] == m['candidate_id'] == HERE.name
    assert provenance['source'] == m['source']
    assert provenance['scientific_proof_or_test_status_transferred'] is False
    for item in provenance['inputs'] + provenance['protected_original_artifacts']:
        assert all(identity(ROOT / item['path'])[k] == item[k] for k in identity(ROOT / item['path']))
    for path, item in m['artifact_bindings'].items():
        assert all(identity(HERE / path)[k] == item[k] for k in identity(HERE / path)), path
    validation = json.loads((HERE / 'CONTENT_VALIDATION.json').read_text())
    assert validation['state'] == 'PASS_CANDIDATE_CONTENT_CHECKS_WITH_RECORDED_EDITORIAL_LIMITS'
    for path, item in validation['checked_artifacts'].items():
        assert all(identity(HERE / path)[k] == item[k] for k in identity(HERE / path)), path
    receipt = json.loads((HERE / 'STAGING_RETURN_RECEIPT.json').read_text())
    assert receipt['candidate_id'] == HERE.name and receipt['predecessor']['head'] == m['predecessor']['head']
    files = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert {x['path'] for x in receipt['returned_artifacts']} == files - {'STAGING_RETURN_RECEIPT.json', 'SHA256SUMS'}
    assert {line.split('  ', 1)[1] for line in (HERE / 'SHA256SUMS').read_text().splitlines()} == files - {'SHA256SUMS'}
    return content_checks(m)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--negative-controls', action='store_true')
    args = p.parse_args()
    name = 'arxiv_submission_manifest.json' if (HERE / 'arxiv_submission_manifest.json').exists() else 'SUBMISSION_MANIFEST.json'
    m = json.loads((HERE / name).read_text())
    boundaries(m)
    content = successor_bindings(m)
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
                      'negative_controls': controls, 'content_checks': content,
                      'predecessor_evidence_transfer': False, 'publication_or_scientific_proof_claimed': False}))

if __name__ == '__main__':
    main()
