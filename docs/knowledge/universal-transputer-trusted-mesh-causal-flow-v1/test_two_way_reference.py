#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from two_way_reference import Refusal, Receiver, Sender, observation, digest, canonical

HEAD = 'a' * 40

class TwoNodeProof(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory()
        root=Path(self.td.name)
        self.a=Sender(root/'sender',node_id='node-a',receiver='node-b',source_head=HEAD)
        self.b=Receiver(root/'receiver',node_id='node-b',accepted_sender='node-a',expected_head=HEAD)

    def tearDown(self): self.td.cleanup()

    def event(self, id='claim-1', raw=b'original\x00bytes'):
        return self.a.prepare(event_id=id,kind='CLAIM',raw=raw)

    def round_trip(self, e):
        self.b.accept(e)
        return self.a.verify_return(e,self.b.read_receipt)

    def test_a_verified_roundtrip_preserves_raw_bytes(self):
        e=self.event()
        r=self.round_trip(e)
        self.assertTrue(r['receipt_verified'])
        self.assertFalse(r['effect_ack_done'])
        self.assertEqual(digest(b'original\x00bytes'),r['payload_sha256'])
        self.assertEqual(len(json.loads(self.b.ledger.read_text())['events']),1)

    def test_b_restart_and_replay_preserve_ledger(self):
        e=self.event()
        first=self.b.accept(e)
        reread=Receiver(self.b.root,node_id='node-b',accepted_sender='node-a',expected_head=HEAD)
        self.assertEqual(reread.accept(e),first)
        self.assertEqual(reread.read_receipt('claim-1'),first)
        self.assertEqual(len(json.loads(self.b.ledger.read_text())['events']),1)

    def test_c_counterevidence_retained_with_separate_receipt(self):
        e=self.event()
        self.round_trip(e)
        reply=self.a.prepare(event_id='counter-2',kind='COUNTER_EVIDENCE',raw=b'counterexample')
        self.round_trip(reply)
        state=json.loads(self.b.ledger.read_text())
        self.assertEqual([v['event']['kind'] for v in state['events']],['CLAIM','COUNTER_EVIDENCE'])
        self.assertNotEqual(state['events'][0]['receipt'],state['events'][1]['receipt'])

    def test_d_missing_event_is_rejected_without_file_write(self):
        e=self.event()
        e['sequence']=2
        with self.assertRaisesRegex(Refusal,'SEQUENCE_GAP'):
            self.b.accept(e)
        self.assertFalse(self.b.ledger.exists())

    def test_e_duplicate_id_changed_bytes_is_rejected(self):
        e=self.event()
        self.b.accept(e)
        changed=copy.deepcopy(e)
        changed['payload_base64']='aGVsbG8='
        changed['payload_sha256']=digest(b'hello')
        with self.assertRaisesRegex(Refusal,'DUPLICATE_ID_CHANGED_CONTENT'):
            self.b.accept(changed)

    def test_f_wrong_source_head_fails(self):
        e=self.event()
        e['source_head']='b'*40
        with self.assertRaisesRegex(Refusal,'WRONG_SOURCE_HEAD'):
            self.b.accept(e)

    def test_g_stale_receipt_fails_even_with_valid_seq(self):
        e=self.event()
        self.round_trip(e)
        next_e=self.a.prepare(event_id='claim-2',kind='CLAIM',raw=b'second')
        next_e['previous_receipt_sha256']='0'*64
        with self.assertRaisesRegex(Refusal,'STALE_PREVIOUS_RECEIPT'):
            self.b.accept(next_e)

    def test_h_missing_admission_fails_no_effect(self):
        self.b.admission=False
        with self.assertRaisesRegex(Refusal,'NOT_ADMITTED'):
            self.b.accept(self.event())
        self.assertFalse(self.b.ledger.exists())

    def test_i_unacknowledged_execution_does_not_fabricate_ack(self):
        e=self.event()
        with self.assertRaisesRegex(Refusal,'RECEIPT_NOT_FOUND'):
            self.a.verify_return(e,self.b.read_receipt)
        self.assertFalse(self.b.ledger.exists())

    def test_j_corrupted_receiver_ledger_is_refused(self):
        e=self.event()
        self.round_trip(e)
        s=json.loads(self.b.ledger.read_text())
        s['events'][0]['receipt']['effect_ack_done']=True
        self.b.ledger.write_text(json.dumps(s))
        with self.assertRaisesRegex(Refusal,'RECEIPT_BINDING_MISMATCH'):
            self.b.read_receipt('claim-1')

    def test_k_wrong_receiver_is_refused(self):
        e=self.event()
        e['receiver']='node-x'
        with self.assertRaisesRegex(Refusal,'INVALID_SOURCE_IDENTITY'):
            self.b.accept(e)

    def test_l_payload_mutation_without_hash_update_is_refused(self):
        e=self.event()
        e['payload_base64']='aGVsbG8='
        with self.assertRaisesRegex(Refusal,'PAYLOAD_DIGEST_MISMATCH'):
            self.b.accept(e)

    def test_m_false_effect_ack_cannot_be_changed_by_sender(self):
        e=self.event()
        self.b.accept(e)
        fake=copy.deepcopy(self.b.read_receipt(e['event_id']))
        fake['effect_ack_done']=True
        with self.assertRaisesRegex(Refusal,'RECEIPT_BINDING_MISMATCH'):
            self.a.verify_return(e,lambda _:fake)

    def test_n_replay_does_not_advance_sequence_or_receipt(self):
        e=self.event()
        r1=self.b.accept(e)
        r2=self.b.accept(e)
        self.assertEqual(r1,r2)
        s=json.loads(self.b.ledger.read_text())
        self.assertEqual(len(s['events']),1)
        self.assertEqual(s['last_receipt_sha256'],digest(canonical(r1)))

if __name__=='__main__':unittest.main(verbosity=2)
