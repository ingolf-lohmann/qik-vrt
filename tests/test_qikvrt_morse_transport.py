# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
"""Byte properties, cross-language vectors and actual original S1 processes."""
from __future__ import annotations
import base64
import hashlib
import http.client
import json
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from src import qikvrt_morse_transport as morse
from tests import test_self_host_temdd as fixtures

ROOT = Path(__file__).resolve().parents[1]


class CodecTests(unittest.TestCase):
    def test_all_byte_values_unicode_case_punctuation_and_line_endings_survive(self):
        values = [b'', bytes(range(256)), b'Alles q.e.d.\r\nA!\x00\xff',
                  'Grüße – Ingolf ♾️'.encode(), 'e\u0301'.encode(), 'é'.encode(),
                  b'\r\n\r\n\n\r', bytes(range(256)) * 64]
        for raw in values:
            with self.subTest(bytes=len(raw)):
                frame = morse.encode(raw)
                self.assertEqual(morse.decode(frame), raw)
                self.assertEqual(set(frame) - set('.- '), set())
        self.assertNotEqual(morse.encode('é'.encode()), morse.encode('e\u0301'.encode()))

    def test_every_single_valid_token_substitution_is_rejected(self):
        tokens = morse.encode(b'case!\x00\xff').split(' ')
        for n, token in enumerate(tokens):
            changed = tokens.copy(); changed[n] = morse.CODES[(morse.CODES.index(token) + 1) % 16]
            with self.subTest(token=n), self.assertRaises(morse.MorseError):
                morse.decode(' '.join(changed))

    def test_malformed_frames_have_explicit_errors(self):
        frame = morse.encode(b'A')
        for bad in ['', '.-', frame + ' ', ' ' + frame, frame.replace(' ', '  ', 1),
                    frame.replace(' ', '\n', 1), frame + ' invalid', ' '.join(frame.split(' ')[:-1])]:
            with self.subTest(value=bad[:25]), self.assertRaises(morse.MorseError): morse.decode(bad)

    def test_limits_and_base64_are_checked_without_normalization(self):
        self.assertEqual(morse.unbase64('YQ=='), b'a')
        for bad in ['YQ===', 'YQ', 'Y Q==', '!!!!', 10]:
            with self.subTest(value=bad), self.assertRaises(ValueError): morse.unbase64(bad)
        with self.assertRaises(morse.MorseError): morse.encode(b'x' * (morse.MAX_BYTES + 1))
        with self.assertRaises(morse.MorseError): morse.encode('not bytes')

    def test_browser_and_python_use_identical_frames_in_both_directions(self):
        rng = random.Random(578)
        values = [b'', bytes(range(256)), b'Alles q.e.d.\r\n\x00\xff', 'e\u0301é♾️'.encode(), b'x' * morse.MAX_BYTES]
        values += [rng.randbytes(n) for n in (1, 2, 3, 17, 43, 256, 1023)]
        vectors = [{'hex':raw.hex(),'frame':morse.encode(raw)} for raw in values]
        script = """
const fs=require('node:fs'),m=require('./docs/terminal/morse/codec.js');
(async()=>{let out=[];for(const v of JSON.parse(fs.readFileSync(0,'utf8'))){
const raw=Uint8Array.from(Buffer.from(v.hex,'hex'));const frame=await m.encode(raw);
if(frame!==v.frame)throw Error('cross-language frame mismatch');
out.push({hex:m.hex(await m.decode(v.frame)),frame});}
process.stdout.write(JSON.stringify(out));})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        r = subprocess.run(['node','-e',script],cwd=ROOT,input=json.dumps(vectors),text=True,capture_output=True,timeout=20)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout),vectors)

    def test_file_cli_roundtrip_and_rejection_preserve_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'input.bin';frame=root/'frame.morse';result=root/'result.bin'
            source.write_bytes(bytes(range(256))+b'\r\nCase!')
            command=[sys.executable,str(ROOT/'src/qikvrt_morse_transport.py')]
            a=subprocess.run(command+['encode',str(source),str(frame)],capture_output=True)
            b=subprocess.run(command+['decode',str(frame),str(result)],capture_output=True)
            self.assertEqual((a.returncode,b.returncode),(0,0));self.assertEqual(result.read_bytes(),source.read_bytes())
            self.assertNotEqual(subprocess.run(command+['decode',str(frame),str(result)],capture_output=True).returncode,0)
            self.assertEqual(result.read_bytes(),source.read_bytes())


class NativeMorseHTTPTests(unittest.TestCase):
    """Reuse actual original monolithic carrier fixtures; never mock admission."""
    setUpClass = fixtures.OwnerRESTMonolithTests.__dict__['setUpClass']
    tearDownClass = fixtures.OwnerRESTMonolithTests.__dict__['tearDownClass']
    setUp = fixtures.OwnerRESTMonolithTests.setUp
    save_config = fixtures.OwnerRESTMonolithTests.save_config
    start = fixtures.OwnerRESTMonolithTests.start
    stop = fixtures.OwnerRESTMonolithTests.stop
    get = fixtures.OwnerRESTMonolithTests.get
    sql = fixtures.OwnerRESTMonolithTests.sql
    command = fixtures.OwnerRESTMonolithTests.command

    def exchange(self, method, path, body=None, prepared=None, extra=None):
        headers = {'Authorization':'Bearer '+self.owner_token.read_text(), 'QIKVRT-Owner':'owner:fixture',
                   'QIKVRT-Subject':json.dumps(self.request['subject'])}
        raw = None
        if method == 'POST':
            raw = json.dumps(body).encode(); headers['Content-Type']='application/json'
            headers['Effect-Ack-Request']='v=1, mode=prepare'
            if prepared is not None:
                sf = lambda b: ':'+base64.b64encode(b).decode()+':'
                headers['Effect-Ack-Request']='v=1, mode=commit, hash='+sf(bytes.fromhex(prepared['record_hash']))+', token='+sf(prepared['commit_token'].encode())
        if extra:
            for k,v in extra.items():
                if v is None: headers.pop(k,None)
                else: headers[k]=v
        c=http.client.HTTPConnection('127.0.0.1',self.config['terminal_port'],timeout=10)
        try:
            c.request(method,path,body=raw,headers=headers);r=c.getresponse();payload=r.read()
            result=json.loads(payload) if r.getheader('Content-Type','').startswith('application/json') else payload
            return r.status,result,dict(r.getheaders())
        finally:c.close()

    def value(self, raw=b'Alles q.e.d.\r\n\x00\xff', operation='encode'):
        return {'schema':'qikvrt-morse-request/v1','request_id':'morse:actual-http-fixture',
                'subject':self.request['subject'],'operation':operation,
                'data':base64.b64encode(raw).decode() if operation=='encode' else morse.encode(raw)}

    def committed(self, raw=b'Alles q.e.d.\r\n\x00\xff', operation='encode'):
        value=self.value(raw,operation)
        code,p,_=self.exchange('POST','/api/owner/morse/prepare',value);self.assertEqual(code,200,p)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        code,r,_=self.exchange('POST','/api/owner/morse/commit',value,p);self.assertEqual(code,200,r)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(2,)])
        return value,p,r

    def test_real_downloads_match_original_bytes_and_persisted_receipt(self):
        self.start();raw=bytes(range(256))+'Grüße ♾️'.encode();value,p,r=self.committed(raw)
        result=r['execution']['payload']['result']
        self.assertEqual(result['payload_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertFalse(r['EFFECT_ACK_DONE']);self.assertTrue(r['independent_sqlite_readback'])
        for kind,expected in [('data',raw),('morse',morse.encode(raw).encode())]:
            code,body,headers=self.exchange('GET','/api/owner/morse/download/'+value['request_id']+'/'+kind)
            self.assertEqual(code,200,body);self.assertEqual(body,expected)
            self.assertIn('attachment;',headers['Content-Disposition'])
            self.assertEqual(headers['Content-Digest'],'sha-256=:'+base64.b64encode(hashlib.sha256(body).digest()).decode()+':')
        code,receipt,_=self.exchange('GET','/api/owner/morse/download/'+value['request_id']+'/receipt')
        self.assertEqual(code,200);self.assertEqual(receipt,r)
        code,asset,_=self.exchange('GET','/morse/');self.assertEqual(code,200);self.assertIn(b'codec.js',asset)

    def test_decode_result_survives_sigkill_and_lost_reply_without_duplicate_events(self):
        self.start();value,p,r=self.committed(operation='decode')
        original_rows=self.sql('SELECT seq,body,native_digest,body_digest FROM events')
        self.stop(abrupt=True);self.start()
        code,cold,_=self.exchange('GET','/api/owner/morse/receipts/'+value['request_id'])
        self.assertEqual(code,200,cold);self.assertEqual(cold,r)
        code,replay,_=self.exchange('POST','/api/owner/morse/commit',value,p)
        self.assertEqual(code,200,replay);self.assertEqual(replay,r)
        self.assertEqual(self.sql('SELECT seq,body,native_digest,body_digest FROM events'),original_rows)
        self.assertNotIn(self.owner_token.read_text(),json.dumps(self.sql('SELECT value FROM meta'))+json.dumps(r))

    def test_largest_morse_request_keeps_native_event_bounds_and_download_bytes(self):
        self.start();raw=bytes(range(256))*64
        value,p,r=self.committed(raw,operation='decode')
        code,body,_=self.exchange('GET','/api/owner/morse/download/'+value['request_id']+'/data')
        self.assertEqual(code,200,body);self.assertEqual(body,raw)
        for row in self.sql('SELECT body FROM events'):
            self.assertLessEqual(len(row[0].encode()),65536)

    def test_corruption_wrong_identity_and_replay_conflict_add_no_effect(self):
        self.start();bad=self.value(operation='decode')
        bad['data']=bad['data'][:-1]+('-' if bad['data'][-1]=='.' else '.')
        code,result,_=self.exchange('POST','/api/owner/morse/prepare',bad)
        self.assertEqual(code,409,result);self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
        value,p,r=self.committed();before=self.sql('SELECT body FROM events')
        changed=self.value(b'changed')
        self.assertEqual(self.exchange('POST','/api/owner/morse/prepare',changed)[0],409)
        self.assertEqual(self.exchange('GET','/api/owner/morse/download/'+value['request_id']+'/data',extra={'Authorization':None})[0],401)
        self.assertEqual(self.exchange('GET','/api/owner/morse/receipts/'+value['request_id'],extra={'QIKVRT-Subject':'{}'})[0],409)
        self.assertEqual(self.exchange('GET','/api/owner/morse/receipts/'+value['request_id'],extra={'Origin':'https://other.invalid'})[0],403)
        self.assertEqual(self.sql('SELECT body FROM events'),before)

    def test_prepared_input_is_not_a_result_and_tampered_bytes_are_not_downloaded(self):
        self.start();value=self.value();code,p,_=self.exchange('POST','/api/owner/morse/prepare',value)
        self.assertEqual(code,200,p)
        self.assertEqual(self.exchange('GET','/api/owner/morse/receipts/'+value['request_id'])[0],409)
        code,r,_=self.exchange('POST','/api/owner/morse/commit',value,p);self.assertEqual(code,200,r)
        with sqlite3.connect(self.volume/'temdd/events.sqlite3') as db:
            row=db.execute('SELECT body FROM events WHERE seq=2').fetchone()[0];body=json.loads(row)
            body['payload']['result']['payload_b64']=base64.b64encode(b'tampered').decode()
            db.execute('UPDATE events SET body=? WHERE seq=2',(json.dumps(body),))
        code,result,_=self.exchange('GET','/api/owner/morse/download/'+value['request_id']+'/data')
        self.assertEqual(code,409,result)


if __name__ == '__main__':unittest.main()
