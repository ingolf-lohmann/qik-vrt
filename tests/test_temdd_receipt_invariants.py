#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""TEMDD readback must reject forged effect elevation even if row digests match."""
import json
from pathlib import Path
import tempfile
import unittest

from src.qikvrt_temdd_event_ledger import Ledger, Hold, SCHEMA, digest


class TemddReceiptInvariantTests(unittest.TestCase):
    def test_recomputed_row_digest_cannot_escalate_native_receipt(self):
        subject = {
            'repository': 'ingolf-lohmann/qik-vrt',
            'pr': 1,
            'head': 'a' * 40,
            'tree': 'b' * 40,
        }
        event = {
            'schema': SCHEMA,
            'kind': 'EFFECT',
            'subject': subject,
            'provenance': {'source': 'transputer', 'native_event_id': 'receipt-test:1'},
            'observed_at': '2026-11-06T14:00:00Z',
            'message': 'An event is evidence of persistence, not effect authorization',
            'payload': {'effect_ack_done': True},
        }
        with tempfile.TemporaryDirectory() as path:
            ledger = Ledger(Path(path), subject)
            try:
                receipt = ledger.append(event)
                self.assertIs(receipt['dod'], False)
                self.assertEqual(receipt['evidence_transfer'], 'DENY')
                self.assertEqual(ledger.replay(0), [receipt])
                stored = json.loads(ledger.db.execute(
                    'SELECT body FROM events WHERE seq = 1').fetchone()[0])
                for field, value in (
                    ('dod', True),
                    ('evidence_transfer', 'ALLOW'),
                    ('payload_digest', '0' * 64),
                    ('schema', 'forged_temdd_event_v1'),
                ):
                    with self.subTest(field=field):
                        forged = dict(stored, **{field: value})
                        ledger.db.execute(
                            'UPDATE events SET body=?, body_digest=? WHERE seq=1',
                            (json.dumps(forged, sort_keys=True, separators=(',', ':'),
                                        ensure_ascii=False), digest(forged)))
                        ledger.db.commit()
                        with self.assertRaisesRegex(Hold, 'LEDGER_READBACK_MISMATCH'):
                            ledger.replay(0)
                        ledger.db.execute(
                            'UPDATE events SET body=?, body_digest=? WHERE seq=1',
                            (json.dumps(stored, sort_keys=True, separators=(',', ':'),
                                        ensure_ascii=False), digest(stored)))
                        ledger.db.commit()
                self.assertEqual(ledger.replay(0), [receipt])
            finally:
                ledger.close()


if __name__ == '__main__':
    unittest.main()
