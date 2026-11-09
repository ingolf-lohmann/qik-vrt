#!/usr/bin/env python3
"""mTLS dual-process test of *local* transport, not two physical hosts."""
import copy
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest

from mtls_transport import request, round_trip
from two_way_reference import Sender, observation, Refusal, ZERO, digest, canonical

HEAD = 'a' * 40


def cmd(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def make_ca(root: Path, name: str):
    ca = root / f'{name}-ca.pem'
    key = root / f'{name}-ca-key.pem'
    cmd('openssl','req','-x509','-newkey','rsa:2048','-sha256','-nodes','-days','1',
        '-keyout',str(key),'-out',str(ca),'-subj',f'/CN={name}-test-ca',
        '-addext','basicConstraints=critical,CA:TRUE',
        '-addext','keyUsage=critical,keyCertSign,cRLSign')
    return ca,key


def make_cert(root: Path, ca: Path, ca_key: Path, name: str, server=False):
    key = root / f'{name}-key.pem'
    csr = root / f'{name}-csr.pem'
    crt = root / f'{name}-crt.pem'
    ext = root / f'{name}-ext.cnf'
    ext.write_text('subjectAltName=DNS:localhost\nextendedKeyUsage='+('serverAuth' if server else 'clientAuth')+'\n')
    cmd('openssl','req','-new','-newkey','rsa:2048','-nodes','-keyout',str(key),
        '-out',str(csr),'-subj',f'/CN={name}')
    cmd('openssl','x509','-req','-in',str(csr),'-CA',str(ca),'-CAkey',str(ca_key),
        '-CAcreateserial','-out',str(crt),'-days','1','-sha256','-extfile',str(ext))
    return crt,key


class MTLSRoundTrip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)
        cls.ca, cls.ca_key=make_ca(cls.root,'trusted')
        cls.server_crt,cls.server_key=make_cert(cls.root,cls.ca,cls.ca_key,'localhost',True)
        cls.client_crt,cls.client_key=make_cert(cls.root,cls.ca,cls.ca_key,'node-a')
        cls.intruder_crt,cls.intruder_key=make_cert(cls.root,cls.ca,cls.ca_key,'intruder')
        cls.bad_ca,cls.bad_ca_key=make_ca(cls.root,'untrusted')
        cls.bad_crt,cls.bad_key=make_cert(cls.root,cls.bad_ca,cls.bad_ca_key,'untrusted-client')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.r=tempfile.TemporaryDirectory()
        self.tmp=Path(self.r.name)
        with socket.socket() as s:
            s.bind(('127.0.0.1',0)); self.port=s.getsockname()[1]
        self.start_server()

    def tearDown(self):
        self.stop_server()
        self.r.cleanup()

    def start_server(self,admitted=True):
        cmdline=[sys.executable, str(Path(__file__).with_name('mtls_transport.py')),
          'server','--ca',str(self.ca),'--cert',str(self.server_crt),
          '--key',str(self.server_key),'--state',str(self.tmp/'receiver'),
          '--head',HEAD,'--port',str(self.port)]
        if admitted: cmdline.append('--admitted')
        self.proc=subprocess.Popen(cmdline,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        import select
        ready,_,_=select.select([self.proc.stdout],[],[],4)
        if not ready:
            self.stop_server()
            raise RuntimeError('TEST_SERVER_START_TIMEOUT')
        if self.proc.stdout.readline().strip()!=b'READY':
            self.stop_server()
            raise RuntimeError('TEST_SERVER_START_FAILED')

    def stop_server(self):
        if getattr(self,'proc',None) and self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.communicate()

    def call(self, method, path, data=None, cert=None, key=None, ca=None):
        return request(port=self.port,ca=str(ca or self.ca),
                       cert=str(cert or self.client_crt) if cert is not False else None,
                       key=str(key or self.client_key) if cert is not False else None,
                       method=method,path=path,data=data)

    def make_event(self, **kw):
        return observation(sender=kw.get('sender','node-a'), receiver='node-b',
                           source_head=kw.get('head',HEAD), sequence=kw.get('seq',1),
                           event_id=kw.get('id','claim-1'),kind=kw.get('kind','CLAIM'),
                           raw=kw.get('raw',b'hello\x00world'),previous=kw.get('previous',ZERO))

    def test01_mtls_authenticated_independent_process_roundtrip(self):
        ret=round_trip(root=self.tmp/'sender',port=self.port,ca=str(self.ca),
                       cert=str(self.client_crt),key=str(self.client_key),head=HEAD,
                       event_id='claim-1',kind='CLAIM',payload=b'hello\x00world')
        self.assertTrue(ret['receipt_verified']);self.assertFalse(ret['effect_ack_done'])
        self.assertTrue((self.tmp/'receiver'/'received.json').is_file())
        self.assertTrue((self.tmp/'sender'/'outbox.json').is_file())
        self.assertNotEqual(os.getpid(),self.proc.pid)

    def test02_second_event_counterevidence(self):
        sender=Sender(self.tmp/'sender',node_id='node-a',receiver='node-b',source_head=HEAD)
        e=sender.prepare(event_id='claim-1',kind='CLAIM',raw=b'original')
        self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        sender.verify_return(e,lambda id:self.call('GET','/v1/receipts/'+id)[1]['receipt'])
        e2=sender.prepare(event_id='counter-2',kind='COUNTER_EVIDENCE',raw=b'counterexample')
        self.assertEqual(self.call('POST','/v1/events',e2)[0],200)
        sender.verify_return(e2,lambda id:self.call('GET','/v1/receipts/'+id)[1]['receipt'])
        events=json.loads((self.tmp/'receiver'/'received.json').read_text())['events']
        self.assertEqual([e['event']['kind'] for e in events],['CLAIM','COUNTER_EVIDENCE'])

    def test03_no_client_cert_refused_by_tls(self):
        with self.assertRaises((ssl.SSLError,OSError)):
            self.call('GET','/health',cert=False)

    def test04_untrusted_client_ca_refused_by_tls(self):
        with self.assertRaises((ssl.SSLError,OSError)):
            self.call('GET','/health',cert=self.bad_crt,key=self.bad_key)

    def test05_untrusted_server_ca_refused_by_tls(self):
        with self.assertRaises((ssl.SSLError,OSError)):
            self.call('GET','/health',ca=self.bad_ca)

    def test06_wrong_cn_same_ca_refused_by_application(self):
        code,data=self.call('GET','/health',cert=self.intruder_crt,key=self.intruder_key)
        self.assertEqual(code,403);self.assertFalse(data['effect_ack_done'])

    def test07_missing_admission_refuses_before_write(self):
        self.stop_server();self.start_server(admitted=False)
        code,data=self.call('POST','/v1/events',self.make_event())
        self.assertEqual(code,409);self.assertEqual(data['error'],'NOT_ADMITTED')
        self.assertFalse((self.tmp/'receiver'/'received.json').exists())

    def test08_sequence_gap_refused(self):
        code,data=self.call('POST','/v1/events',self.make_event(seq=2))
        self.assertEqual(code,409);self.assertIn('SEQUENCE_GAP',data['error'])

    def test09_wrong_head_refused(self):
        code,data=self.call('POST','/v1/events',self.make_event(head='b'*40))
        self.assertEqual(code,409);self.assertEqual(data['error'],'WRONG_SOURCE_HEAD')

    def test10_digest_mutation_refused(self):
        e=self.make_event();e['payload_sha256']='f'*64
        code,data=self.call('POST','/v1/events',e)
        self.assertEqual(code,409);self.assertEqual(data['error'],'PAYLOAD_DIGEST_MISMATCH')

    def test11_unacknowledged_readback_is_not_effect(self):
        code,data=self.call('GET','/v1/receipts/missing')
        self.assertEqual(code,404);self.assertFalse(data['effect_ack_done'])

    def test12_restart_replays_once(self):
        e=self.make_event()
        code,r=self.call('POST','/v1/events',e)
        self.assertEqual(code,200)
        self.stop_server();self.start_server()
        code,after=self.call('GET','/v1/receipts/claim-1')
        self.assertEqual(code,200);self.assertEqual(after['receipt'],r['receipt'])
        self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        self.assertEqual(len(json.loads((self.tmp/'receiver'/'received.json').read_text())['events']),1)

    def test13_duplicate_id_different_payload_refused(self):
        e=self.make_event();self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        f=self.make_event(raw=b'other')
        code,data=self.call('POST','/v1/events',f)
        self.assertEqual(code,409);self.assertEqual(data['error'],'DUPLICATE_ID_CHANGED_CONTENT')

    def test14_tampered_receipt_ledger_fails_cold_read(self):
        e=self.make_event();self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        path=self.tmp/'receiver'/'received.json';s=json.loads(path.read_text())
        s['events'][0]['receipt']['effect_ack_done']=True
        path.write_text(json.dumps(s))
        code,data=self.call('GET','/v1/receipts/claim-1')
        self.assertEqual(code,409);self.assertEqual(data['error'],'RECEIPT_BINDING_MISMATCH')

    def test15_noncanonical_post_refused(self):
        # valid JSON, but bytes not canonical: must not silently reinterpret signatures.
        import http.client
        ctx=ssl.create_default_context(cafile=str(self.ca))
        ctx.load_cert_chain(str(self.client_crt),str(self.client_key))
        c=http.client.HTTPSConnection('localhost',self.port,context=ctx,timeout=3)
        body=b' {"hello":"world"} '
        try:
            c.request('POST','/v1/events',body=body,headers={'Content-Type':'application/json'})
            res=c.getresponse();self.assertEqual(res.status,409)
            self.assertEqual(json.loads(res.read())['error'],'NONCANONICAL_EVENT')
        finally:c.close()

    def test16_stale_predecessor_hash_refused(self):
        e=self.make_event();self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        nxt=self.make_event(seq=2,id='counter-2',kind='COUNTER_EVIDENCE')
        self.assertEqual(self.call('POST','/v1/events',nxt)[1]['error'],'STALE_PREVIOUS_RECEIPT')

    def test17_second_process_is_persistent_not_in_memory(self):
        e=self.make_event();self.assertEqual(self.call('POST','/v1/events',e)[0],200)
        old_pid=self.proc.pid;self.stop_server();self.start_server()
        self.assertNotEqual(old_pid,self.proc.pid)
        self.assertEqual(self.call('GET','/v1/receipts/claim-1')[0],200)


if __name__=='__main__':unittest.main(verbosity=2)
