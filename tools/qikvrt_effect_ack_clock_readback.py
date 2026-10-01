#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check coherent carrier telemetry; V1 cannot attest an unbound physical board."""
import argparse
import json
from pathlib import Path

FIELDS = {'schema', 'nonce', 'epoch', 'evaluated', 'witnessed', 'fault',
          'witness_fault', 'reset_seen', 'state', 'snapshot_epoch', 'snapshot_cycle'}


def verify_readback(value, *, nonce, epoch, expected_count):
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError('missing or unexpected readback fields')
    if value['schema'] != 'qikvrt_effect_ack_clock_readback_v1':
        raise ValueError('readback schema mismatch')
    for key in FIELDS - {'schema'}:
        if type(value[key]) is not int or not 0 <= value[key] < 2**64:
            raise ValueError('noncanonical unsigned field: ' + key)
    if any(type(x) is not int or not 0 < x < 2**64 for x in (nonce, epoch, expected_count)):
        raise ValueError('fresh caller binding required')
    if (value['nonce'], value['epoch'], value['evaluated']) != (nonce, epoch, expected_count):
        raise ValueError('stale challenge, epoch or observation window')
    if value['evaluated'] != value['witnessed']:
        raise ValueError('coverage disagreement')
    if any(value[x] != 0 for x in ('fault', 'witness_fault', 'reset_seen')):
        raise ValueError('latched clock/reset fault')
    if value['snapshot_epoch'] != epoch or value['snapshot_cycle'] != expected_count - 1:
        raise ValueError('snapshot/coverage binding mismatch')
    if value['state'] > 4:
        raise ValueError('invalid state')
    return {'schema': 'qikvrt_effect_ack_clock_readback_disposition_v1',
            'telemetry_consistent': True, 'physical_clock_verified': False,
            'ordinary_release': False, 'effect_ack_done': False,
            'state': 'HOLD_PHYSICAL_BINDING_OPEN',
            'reason': 'No authenticated board adapter, pin/timing/programmer or independent oscillator witness is bound in V1.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('readback', type=Path)
    parser.add_argument('--nonce', type=int, required=True)
    parser.add_argument('--epoch', type=int, required=True)
    parser.add_argument('--expected-count', type=int, required=True)
    args = parser.parse_args()
    try:
        def unique(pairs):
            result = {}
            for key, val in pairs:
                if key in result: raise ValueError('duplicate JSON key')
                result[key] = val
            return result
        result = verify_readback(json.loads(args.readback.read_text(), object_pairs_hook=unique),
                                 nonce=args.nonce, epoch=args.epoch, expected_count=args.expected_count)
        code = 20
    except (OSError, ValueError) as exc:
        result = {'state': 'BLOCK', 'reason': str(exc), 'ordinary_release': False,
                  'physical_clock_verified': False, 'effect_ack_done': False}
        code = 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
