#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann. Public-read implementation: OpenAI Codex.
"""Existing repository disclosure, including a bounded anonymous projection."""
import argparse
import copy
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DISCLOSURE_PATH = '.well-known/qik-vrt-self-disclosure.json'
DOC = ROOT / DISCLOSURE_PATH
PUBLIC_MAX_BYTES = 64 * 1024
SOURCE_BASE = 'https://raw.githubusercontent.com/ingolf-lohmann/qik-vrt/main/'
PUBLIC_ONBOARDING = {
    'schema': 'qikvrt_public_onboarding_v1',
    'authority_repository': 'https://github.com/ingolf-lohmann/qik-vrt',
    'principal': 'Ingolf Lohmann',
    'repository_sources': {
        'ai': SOURCE_BASE + 'AI',
        'ai_context': SOURCE_BASE + 'AI_CONTEXT.json',
        'agent_protocol': SOURCE_BASE + 'AGENTS.md',
        'api_contract': SOURCE_BASE + 'api/qikvrt_github_api.openapi.yaml',
    },
    'runtime_endpoints': {
        'self_disclosure': {
            'method': 'GET', 'path': '/' + DISCLOSURE_PATH,
            'authentication_required': False,
        },
        'health': {
            'method': 'GET', 'path': '/health',
            'authentication_required': False,
        },
    },
    'authorization': {
        'public_read': 'NONE',
        'protected_read': 'SCOPED_AUTHENTICATION_REQUIRED',
        'effects': 'AUTHENTICATION_AUTHORIZATION_AND_ADMISSION_REQUIRED',
    },
}
# This version has no admitted production-variable read. A local environment
# value or static document cannot attest remote production configuration.
PUBLIC_PRODUCTION_STATUS = {
    'schema': 'qikvrt_public_production_status_v1',
    'publish_enabled': 'UNKNOWN',
    'deploy_enabled': 'UNKNOWN',
    'host_binding': 'UNKNOWN',
    'observed_at': None,
    'evidence': None,
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate disclosure field')
        result[key] = value
    return result


def public_document(raw):
    """Allowlisted static projection; never reads credentials or providers.

    The digest binds source bytes, not a running host or a variable read.
    Observed statuses require a separate validated evidence contract.
    """
    if not isinstance(raw, bytes) or len(raw) > PUBLIC_MAX_BYTES:
        raise ValueError('invalid disclosure size or encoding')
    document = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
    if (not isinstance(document, dict)
            or document.get('schema') != 'qikvrt_repository_self_disclosure_v1'
            or document.get('onboarding') != PUBLIC_ONBOARDING
            or document.get('production_status') != PUBLIC_PRODUCTION_STATUS):
        raise ValueError('public disclosure contract unavailable')
    capability_ids = {
        'repository_state_read', 'transactional_workflow_verification',
        'content_disposition_evidence', 'authority_mirror_traceability',
        'publication_overview_discovery', 'anonymous_onboarding_read',
    }
    entries = document.get('capabilities')
    if not isinstance(entries, list):
        raise ValueError('public capabilities unavailable')
    capabilities = [
        {'id': entry['id'], 'machine_readable': entry.get('machine_readable') is True}
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get('id'), str)
        and entry['id'] in capability_ids
    ]
    return {
        'schema': 'qikvrt_public_self_disclosure_v1',
        'capabilities': capabilities,
        'onboarding': copy.deepcopy(PUBLIC_ONBOARDING),
        'production_status': copy.deepcopy(PUBLIC_PRODUCTION_STATUS),
        'source': {
            'kind': 'STATIC_REPOSITORY_DOCUMENT',
            'path': DISCLOSURE_PATH,
            'sha256': hashlib.sha256(raw).hexdigest(),
        },
        'completion_claims': {
            'pass': False, 'final_pass': False, 'effect_ack_done': False,
        },
        'ordinary_release': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['show', 'capabilities', 'status', 'public'])
    args = parser.parse_args()
    raw = DOC.read_bytes()
    if args.command == 'public':
        out = public_document(raw)
    else:
        document = json.loads(raw)
        if args.command == 'show':
            out = document
        elif args.command == 'capabilities':
            out = {'schema': document['schema'], 'capabilities': document['capabilities']}
        else:
            out = {key: document[key] for key in
                   ('schema', 'service', 'state', 'completion_claims')}
    print(json.dumps(out, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
