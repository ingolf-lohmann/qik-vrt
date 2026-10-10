#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Repository discovery and read-only, exact-byte owner acceptance readback."""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / '.well-known' / 'qik-vrt-self-disclosure.json'
SEAL_PATH = 'state/owner_acceptance/SEED_MCP_GOVERNANCE_SEAL_20261010_V1.json'
NON_CLAIMS = ('independent_review', 'native_code_owner_enforcement',
              'successor_acceptance', 'main_merge', 'mesh_activation',
              'delivery_verified', 'effect_ack_done')


def validate_owner_seal(raw, binding):
    """Validate a pinned receipt; attribution is not identity authentication."""
    if (not isinstance(binding, dict) or binding.get('path') != SEAL_PATH
            or not isinstance(raw, bytes) or len(raw) > 65536
            or hashlib.sha256(raw).hexdigest() != binding.get('sha256')):
        raise ValueError('OWNER_SEAL_BYTES_NOT_BOUND')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('OWNER_SEAL_DUPLICATE_FIELD')
            result[key] = value
        return result
    receipt = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(receipt, dict):
        raise ValueError('OWNER_SEAL_INVALID_RECORD')
    subject = receipt.get('subject', {})
    claims = receipt.get('claims', {})
    if (receipt.get('schema') != 'qikvrt_versioned_owner_seal_acceptance_v1'
            or receipt.get('status') != 'ACCEPTED'
            or receipt.get('accepted_by') != 'Ingolf Lohmann'
            or receipt.get('evidence_kind') != 'ATTRIBUTED_USER_DECLARATION'
            or receipt.get('roles') != ['CREATOR', 'CODE_OWNER', 'PRODUCT_OWNER']
            or any(not isinstance(receipt.get(key), str) or not receipt[key].strip()
                   for key in ('statement', 'persistence_authorization', 'recorded_at_utc'))
            or not isinstance(subject, dict)
            or subject.get('repository') != 'ingolf-lohmann/qik-vrt'
            or any(not isinstance(subject.get(key), str) or not re.fullmatch('[0-9a-f]{40}', subject[key]) for key in ('head', 'tree'))
            or not isinstance(claims, dict)
            or set(claims) != set(NON_CLAIMS)
            or any(claims[key] is not False for key in NON_CLAIMS)):
        raise ValueError('OWNER_SEAL_INVALID_BOUNDARY')
    return receipt


def owner_seal(root=ROOT):
    disclosure = json.loads((root / '.well-known/qik-vrt-self-disclosure.json').read_bytes())
    binding = disclosure['bindings']['owner_seal_acceptance']
    receipt = validate_owner_seal((root / SEAL_PATH).read_bytes(), binding)
    return {'binding': binding, 'receipt': receipt}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['show', 'capabilities', 'status', 'owner-seal'])
    args = parser.parse_args()
    try:
        disclosure = json.loads(DOC.read_bytes())
        seal = owner_seal()
        if args.command == 'show':
            out = disclosure
        elif args.command == 'capabilities':
            out = {'schema': disclosure['schema'], 'capabilities': disclosure['capabilities'], 'owner_seal_acceptance': seal}
        elif args.command == 'owner-seal':
            out = seal
        else:
            out = {key: disclosure[key] for key in ('schema', 'service', 'state', 'completion_claims')}
            out['owner_seal_acceptance'] = seal
        print(json.dumps(out, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print('OWNER_SEAL_READBACK_BLOCKED', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
