#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify exact candidate bytes and the deliberately closed production boundary."""
from pathlib import Path
import copy, json, sys, tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_zenodo_machine_proof import ProofGateError, identity, validate_bundle

HERE = Path(__file__).resolve().parent
REL = HERE.relative_to(ROOT).as_posix() + '/'
BUNDLE = HERE / 'MACHINE_PROOF_BUNDLE.json'
EXPECTED_BLOCK = 'proof bundle does not authorize the exact Zenodo upload'

def inspect_production(value):
    scratch = ROOT / '.qikvrt' / 'evidence'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', dir=scratch, encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False)
        stream.flush()
        try:
            validate_bundle(ROOT, Path(stream.name))
        except ProofGateError as exc:
            return str(exc)
    raise AssertionError('Unauthorized preparation passed the production gate')

def verify():
    bundle = json.loads(BUNDLE.read_text())
    assert bundle['completion_claims']['zenodo_upload_authorized'] is False
    observed = inspect_production(bundle)
    assert observed == EXPECTED_BLOCK, observed
    matrix = json.loads((HERE / 'CLAIM_MATRIX.json').read_text())
    assert len(matrix['claims']) == matrix['claim_count'] == len(bundle['claims']) == 18
    assert not any(c['classification'] == 'FORMAL_PROVED' for c in bundle['claims'])
    planned = json.loads((HERE / 'ZENODO_FILESET.json').read_text())['paths']
    assert set(planned) == {c['path'] for c in bundle['candidate']['files']} | {a['path'] for a in bundle['artifacts']} | {REL+'MACHINE_PROOF_BUNDLE.json'}
    assert len(planned) == len(set(planned))
    for item in bundle['candidate']['files'] + bundle['artifacts']:
        observed_id = identity(ROOT/item['path'])
        for key in ('sha256','git_blob_sha1'):
            assert item[key] == observed_id[key], item['path']
        if 'bytes' in item: assert item['bytes'] == observed_id['bytes']
    pdf = ROOT / bundle['candidate']['primary_document_path']
    assert identity(pdf)['sha256'] in (HERE/'ARTICLE.md').read_text()
    assert pdf.read_bytes().startswith(b'%PDF-')
    assert not (HERE/'OWNER_ZENODO_AUTHORIZATION.json').exists()
    assert not (HERE/'publish-request.json').exists()
    cases = []
    for name, mutate, expected in [
        ('PDF_HASH_TAMPER', lambda b: b['candidate']['files'][0].update(sha256='0'*64), 'SHA-256 mismatch'),
        ('CLAIM_OMISSION', lambda b: b['claims'].pop(), 'bidirectionally'),
        ('SOURCE_HASH_TAMPER', lambda b: b['artifacts'][0].update(sha256='0'*64), 'SHA-256 mismatch'),
        ('OPEN_CLAIM_PROMOTION', lambda b: next(c for c in b['claims'] if c['classification']=='OPEN').update(publication_wording='ESTABLISHED_WITHIN_SCOPE'), 'disposition inconsistent'),
    ]:
        changed = copy.deepcopy(bundle)
        mutate(changed)
        error = inspect_production(changed)
        assert expected in error, (name,error)
        cases.append({'test_id':name,'result':'REJECTED_AS_EXPECTED','observed_error':error})
    return {'schema':'qikvrt_prepublication_verification_result_v1','candidate_byte_bindings':'PASS','claim_matrix_bidirectional_projection':'PASS','source_references':'PASS','changed_content_return_chain':'PASS','fileset_closure':'PASS','negative_controls':cases,'production_gate':'HOLD','production_error':observed,'upload_authorized':False,'external_publication_effect':'NONE','verification_scope':'Repository-native validator reached only its final authorization flag after validating byte identities, claim/source disposition and return chain; no live or predecessor gates transferred.'}

if __name__ == '__main__':
    print(json.dumps(verify(),ensure_ascii=False,indent=2,sort_keys=True))
