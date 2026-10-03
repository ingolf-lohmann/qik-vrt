#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify exact candidate bytes and the deliberately closed production boundary."""
from pathlib import Path
import copy, hashlib, json, sys, tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.qikvrt_zenodo_machine_proof import ProofGateError, identity, validate_bundle
from tools import qikvrt_zenodo_publish as publisher

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
    names = [Path(p).name for p in planned]
    assert len(names) == len(set(names)), 'Duplicate public upload filenames'
    metadata = json.loads((HERE / 'ZENODO_METADATA.json').read_text())
    assert publisher._validate_metadata(metadata) == metadata
    canonical_metadata = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    metadata_sha256 = hashlib.sha256(canonical_metadata).hexdigest()
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
    # A prospective authorization cannot authorize today's false-valued bundle
    # and remain bound to the bytes of a later true-valued bundle. This probe
    # computes digests only; it creates no authorization or alternate bundle.
    prospective = copy.deepcopy(bundle)
    prospective['completion_claims']['zenodo_upload_authorized'] = True
    prospective_raw = (json.dumps(prospective, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    bundle_sha256 = identity(BUNDLE)['sha256']
    prospective_sha256 = hashlib.sha256(prospective_raw).hexdigest()
    assert bundle_sha256 != prospective_sha256
    return {'schema':'qikvrt_prepublication_verification_result_v1','candidate_byte_bindings':'PASS','claim_matrix_bidirectional_projection':'PASS','source_references':'PASS','changed_content_return_chain':'PASS','fileset_closure':'PASS','unique_upload_filenames':'PASS','canonical_metadata_sha256':metadata_sha256,'negative_controls':cases,'production_gate':'HOLD','production_error':observed,'upload_authorized':False,'external_publication_effect':'NONE','authorization_transition':{'state':'HOLD_AUTHORIZATION_FLAG_CHANGES_APPROVED_BUNDLE_HASH','bundle_hash_changes_when_flag_changes':True,'prospective_bytes_materialized':False,'authorization_created':False,'authorization_consumed':False},'verification_scope':'Repository-native validator validates byte identities, claim/source disposition and return chain before rejecting the unauthorized flag. Exact fileset closure, unique public filenames and canonical metadata are checked independently. The hash transition is a digest-only negative control; no live or predecessor gates transferred.'}

if __name__ == '__main__':
    print(json.dumps(verify(),ensure_ascii=False,indent=2,sort_keys=True))
