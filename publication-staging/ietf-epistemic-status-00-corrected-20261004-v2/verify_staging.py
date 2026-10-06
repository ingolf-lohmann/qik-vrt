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
import xml.etree.ElementTree as ET

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

def validate_xml(root):
    """Check the corrected normative profile, without claiming interoperability."""
    sections = {s.findtext('name'): s for s in root.findall('./middle/section')}
    text = ' '.join(root.itertext())
    assert not re.search(r'\b(?:PROVED|OBSERVED)\b', text), 'undeclared status alias'
    expected = ['FORMAL_PROVED', 'EMPIRICALLY_EVIDENCED', 'SOURCE_BOUND', 'INTERPRETATIVE', 'NORMATIVE', 'PREDICTED', 'OPEN']
    assert [x.text for x in sections['Epistemic Status Vocabulary'].findall('./dl/dt')] == expected
    invariant = sections['Introduction'].findtext('sourcecode')
    assert 'ASSERT_AS_FORMAL_PROVED(C) implies VALID_BOUND_FORMAL_PROOF(C)' in invariant
    assert 'C MUST NOT be classified as FORMAL_PROVED.' in invariant
    proof = ' '.join(sections['Introduction'].itertext())
    assert all(x in proof for x in ['checked proof artifact', 'exact formal proposition', 'claim_id', 'formal model', 'bound assumptions', 'proof-checking environment', 'external-world correspondence'])
    vocabulary = ' '.join(sections['Epistemic Status Vocabulary'].itertext())
    assert all(x in vocabulary for x in ['refinement MUST bind its parent status', 'retain all evidence conditions', 'MUST NOT replace or relax', 'do not form a universal ranking'])
    normative = ' '.join(sections['Normative Invariants'].itertext())
    assert 'MUST NOT be represented as EMPIRICALLY_EVIDENCED' in normative
    assert all(x in normative for x in ['checked proof artifact', 'exact formal proposition', 'claim scope', 'model', 'assumptions', 'proof-checking environment'])
    binding = ' '.join(sections['Claim Binding'].itertext())
    assert all(x in binding for x in ['MUST bind at least claim_id, claim_scope', 'claim_id MUST resolve the exact proposition', 'claim_scope MUST state', 'relation to this exact proposition and scope', 'MUST resolve the checked proof', 'formal model', 'assumptions', 'proof-checking environment', 'refinement MUST additionally bind its parent status', 'unchanged evidence conditions'])
    assert re.search(r'claim_id,\s*claim_scope,', sections['Claim Binding'].findtext('sourcecode'))
    assert [x.attrib['target'] for x in sections['Conventions and Definitions'].findall('.//xref')] == ['RFC2119', 'RFC8174']
    relationship = ' '.join(sections['Relationship to EFFECT_ACK'].itertext())
    assert sections['Relationship to EFFECT_ACK'].find('t/xref').attrib['target'] == 'I-D.lohmann-qikvrt-effect-ack-03'
    assert all(x in relationship for x in ['does not change its five-state version-1 wire contract', 'informative work in progress', 'not additional EFFECT_ACK version-1 enum values', 'not an implicit identical registration', 'no new mandatory wire member or protocol dependency'])
    assert 'Security Considerations' in sections
    security = ' '.join(sections['Security Considerations'].itertext())
    assert 'MUST fail closed' in security and 'MUST NOT be converted into a stronger claim status' in security
    reference = root.find("./back/references/reference[@anchor='I-D.lohmann-qikvrt-effect-ack-03']")
    assert reference is not None
    assert root.find('./back/references[2]/name').text == 'Informative References'
    assert reference.find('front/date').attrib == {'year': '2026', 'month': 'August', 'day': '2'}
    assert reference.find('seriesInfo').attrib['value'] == 'draft-lohmann-qikvrt-effect-ack-03'
    return expected

def content_checks(m):
    derivation = json.loads((HERE / 'DERIVATION_MAP.json').read_text())
    source = ROOT / derivation['source_repository_path']
    xml_path = HERE / 'draft-lohmann-qikvrt-epistemic-status-00.xml'
    for path, item in [(source, derivation['source']), (xml_path, derivation['successor'])]:
        assert all(identity(path)[k] == item[k] for k in identity(path))
    reconstructed = source.read_text()
    for operation in derivation['operations']:
        expected_occurrences = 2 if operation['index'] == 2 else operation['count']
        assert reconstructed.count(operation['from']) == expected_occurrences
        reconstructed = reconstructed.replace(operation['from'], operation['to'], operation['count'])
    assert reconstructed == xml_path.read_text()
    root = ET.fromstring(reconstructed)
    statuses = validate_xml(root)
    original = ET.fromstring(source.read_text())
    old_sections = {s.findtext('name'): s for s in original.findall('./middle/section')}
    new_sections = {s.findtext('name'): s for s in root.findall('./middle/section')}
    for section in ['Non-Goals', 'IANA Considerations']:
        assert list(old_sections[section].itertext()) == list(new_sections[section].itertext())
    old_security = next(s for name, s in old_sections.items() if name.startswith('Security'))
    assert [x.text for x in old_security.findall('t')] == [x.text for x in new_sections['Security Considerations'].findall('t')]
    xml2rfc = json.loads((HERE / 'RENDER_VALIDATION.json').read_text())
    assert all(x['warning_count'] == x['errors'] == 0 for x in xml2rfc['validation']['diagnostics'].values())
    assert xml2rfc['validation']['expected_warning_ids'] == []
    assert all(xml2rfc['validation'][x]['repeat_render_byte_identical'] for x in ['txt', 'html'])
    from html.parser import HTMLParser
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids = []; self.links = []; self.text = []
        def handle_starttag(self, tag, attrs):
            values = dict(attrs)
            if 'id' in values: self.ids.append(values['id'])
            if tag == 'a' and values.get('href', '').startswith('#'): self.links.append(values['href'][1:])
        def handle_data(self, data): self.text.append(data)
    parser = Parser(); parser.feed((HERE / 'draft-lohmann-qikvrt-epistemic-status-00.html').read_text()); parser.close()
    assert len(parser.ids) == len(set(parser.ids)), 'duplicate HTML IDs'
    assert set(parser.links) - {''} <= set(parser.ids), 'unresolved HTML fragment'
    normalize = lambda text: re.sub(r'\s+', ' ', text).strip()
    html = normalize(' '.join(parser.text))
    txt = normalize((HERE / 'draft-lohmann-qikvrt-epistemic-status-00.txt').read_text())
    # Full paragraph/sourcecode rendering is required in HTML; selected critical
    # phrases are additionally checked in paginated TXT without footer artifacts.
    paragraphs = root.findall('./front/abstract/t') + root.findall('./middle/section/t') + root.findall('./middle/section/ul/li') + root.findall('./middle/section/dl/dt') + root.findall('./middle/section/dl/dd')
    for node in paragraphs:
        fragments = [normalize(x) for x in node.itertext() if normalize(x)]
        assert all(x in html for x in fragments), fragments
    for output in [html, txt]:
        assert all(x in output for x in statuses + ['ASSERT_AS_FORMAL_PROVED(C)', 'claim_scope', 'Security Considerations', 'RFC2119', 'RFC8174', 'I-D.lohmann-qikvrt-effect-ack-03'])
    controls = []
    for label, before, after in [('formal-status-alias-rejected', 'ASSERT_AS_FORMAL_PROVED', 'ASSERT_AS_PROVED'), ('missing-scope-binding-rejected', 'MUST bind at least claim_id, claim_scope', 'MUST bind at least claim_id')]:
        try: validate_xml(ET.fromstring(reconstructed.replace(before, after)))
        except AssertionError: controls.append(label)
        else: raise AssertionError('semantic boundary accepted: ' + label)
    return {'seven_statuses': statuses, 'derivation_operations': len(derivation['operations']),
            'exact_proposition_scope_proof_model_assumptions_checker_bound': True,
            'refinement_retains_parent_conditions': True, 'rfc_xrefs_resolve': True,
            'effect_ack_03_reference_informative': True, 'effect_ack_v1_wire_unchanged': True,
            'non_goals_and_security_text_preserved': True, 'html_fragment_links_resolved': len(parser.links),
            'rendered_paragraphs_checked': len(paragraphs), 'warning_count_per_mode': 0,
            'semantic_negative_controls': controls, 'interoperability_or_deployment_conformance_proved': False}

def successor_bindings(m):
    provenance = json.loads((HERE / 'SOURCE_PROVENANCE.json').read_text())
    assert provenance['candidate_id'] == m['candidate_id'] == HERE.name
    assert provenance['source'] == m['source']
    assert provenance['frozen_source_xml_preserved_byte_exact'] is True
    for item in provenance['inputs'] + provenance['protected_original_artifacts']:
        assert all(identity(ROOT / item['path'])[k] == item[k] for k in identity(ROOT / item['path']))
    for path, item in m['artifacts'].items():
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
