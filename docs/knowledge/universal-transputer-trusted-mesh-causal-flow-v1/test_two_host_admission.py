#!/usr/bin/env python3
"""Remote host prerequisite tests; never claims a second deployed host."""
import socket
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mtls_transport import Refusal, is_loopback_binding, require_remote_target, serve, request, round_trip, replay_round_trip

HEAD='a'*40

def fake_resolution(*addresses):
    return lambda host, port, type: [(socket.AF_INET, socket.SOCK_STREAM,0,'',(ip,8443)) for ip in addresses]

class RemoteTestAdmission(unittest.TestCase):
    def test01_ipv4_loopback_is_local(self):
        self.assertTrue(is_loopback_binding('127.0.0.1'))

    def test02_ipv6_loopback_is_local(self):
        self.assertTrue(is_loopback_binding('::1'))

    def test03_nonloopback_not_automatically_admitted(self):
        self.assertFalse(is_loopback_binding('0.0.0.0'))
        with self.assertRaisesRegex(Refusal,'REMOTE_TEST_BIND_REQUIRES_EXPLICIT_ADMISSION'):
            serve(host='0.0.0.0',port=8443,ca='none',cert='none',key='none',state='/tmp',source_head=HEAD,admitted=True)

    def test04_remote_bind_without_admission_fails(self):
        with self.assertRaisesRegex(Refusal,'REMOTE_TEST_BIND_REQUIRES_EXPLICIT_ADMISSION'):
            serve(host='0.0.0.0',port=8443,ca='none',cert='none',key='none',state='/tmp',source_head=HEAD,admitted=False,remote_test_bind=True)

    def test05_external_target_loopback_rejected(self):
        with self.assertRaisesRegex(Refusal,'REMOTE_ADDRESS_NOT_INDEPENDENT'):
            require_remote_target('node-b.example.test',resolve=fake_resolution('127.0.0.1'))

    def test06_dns_mixed_loopback_and_public_rejected(self):
        with self.assertRaisesRegex(Refusal,'REMOTE_ADDRESS_NOT_INDEPENDENT'):
            require_remote_target('node-b.example.test',resolve=fake_resolution('203.0.113.22','127.0.0.1'))

    def test07_external_target_public_address_is_only_routing_prerequisite(self):
        self.assertIsNone(require_remote_target('node-b.example.test',resolve=fake_resolution('203.0.113.22')))

    def test08_external_target_missing_dns_fails(self):
        def fail(*args,**kwargs): raise socket.gaierror('not found')
        with self.assertRaisesRegex(Refusal,'REMOTE_DNS_UNAVAILABLE'):
            require_remote_target('node-b.example.test',resolve=fail)

    def test09_url_in_host_rejected(self):
        with self.assertRaisesRegex(Refusal,'REMOTE_HOST_NOT_ADMITTED'):
            require_remote_target('https://node-b.example.test',resolve=fake_resolution('203.0.113.22'))
        with self.assertRaisesRegex(Refusal,'INVALID_REMOTE_HOST'):
            request(host='https://node-b.example.test',port=8443,ca='none',cert=None,key=None,method='GET',path='/health')

    def test10_external_round_trip_rejects_local_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(Refusal,'REMOTE_HOST_NOT_ADMITTED'):
                round_trip(root=Path(tmp)/'sender',port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='a',kind='CLAIM',payload=b'a',host='localhost',require_external_route=True)
            self.assertFalse((Path(tmp)/'sender'/'outbox.json').exists())

    def test11_replay_requires_persisted_sender_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(Refusal,'OUTBOX_NOT_READABLE'):
                replay_round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='missing')

    def test12_replay_refuses_wrong_source_head(self):
        from two_way_reference import Sender
        with tempfile.TemporaryDirectory() as tmp:
            s=Sender(Path(tmp),node_id='node-a',receiver='node-b',source_head=HEAD)
            s.prepare(event_id='claim-1',kind='CLAIM',raw=b'a')
            with self.assertRaisesRegex(Refusal,'EXACT_PERSISTED_EVENT_NOT_FOUND'):
                replay_round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head='b'*40,event_id='claim-1')

    def test13_replay_refuses_local_when_remote_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(Refusal,'REMOTE_HOST_NOT_ADMITTED'):
                replay_round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='claim-1',host='localhost',require_external_route=True)

    def test14_invalid_exact_head_rejected_before_bind(self):
        with self.assertRaisesRegex(Refusal,'INVALID_EXACT_SOURCE_HEAD'):
            serve(host='127.0.0.1',port=8443,ca='none',cert='none',key='none',state='/tmp',source_head='not-a-commit',admitted=True)

    def test15_bad_event_id_rejected_before_sender_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(Refusal,'INVALID_ROUND_TRIP_IDENTITY'):
                round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='../admin',kind='CLAIM',payload=b'data')
            self.assertFalse((Path(tmp)/'outbox.json').exists())

    def test16_remote_health_cannot_claim_effect_ack_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('mtls_transport.require_remote_target'):
                with patch('mtls_transport.request',return_value=(200,{'server':'node-b','ready':True,'effect_ack_done':True,'scope':'EXPERIMENTAL_REMOTE_TEST_NOT_MESH_ADMITTED'})):
                    with self.assertRaisesRegex(Refusal,'REMOTE_IDENTITY_OR_READINESS_NOT_VERIFIED'):
                        round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='a',kind='CLAIM',payload=b'a',host='node-b.example.test',require_external_route=True)
            self.assertFalse((Path(tmp)/'outbox.json').exists())

    def test17_remote_health_wrong_node_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('mtls_transport.require_remote_target'):
                with patch('mtls_transport.request',return_value=(200,{'server':'imposter','ready':True,'effect_ack_done':False,'scope':'EXPERIMENTAL_REMOTE_TEST_NOT_MESH_ADMITTED'})):
                    with self.assertRaisesRegex(Refusal,'REMOTE_IDENTITY_OR_READINESS_NOT_VERIFIED'):
                        round_trip(root=Path(tmp),port=8443,ca='none',cert='none',key='none',head=HEAD,event_id='a',kind='CLAIM',payload=b'a',host='node-b.example.test',require_external_route=True)

if __name__=='__main__':unittest.main(verbosity=2)
