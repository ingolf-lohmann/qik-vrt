# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import hashlib,json,tempfile,threading,unittest,sys,types,subprocess
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from src import qikvrt_personal_retrieval as retrieval
from src import qikvrt_personal_assistant as personal
from src import qikvrt_effect_ack_http_terminal as terminal
from tests.test_qikvrt_personal_assistant import TransportDouble,KEY,TOKEN

def source(identity,text):
    return {"id":identity,"text":text,"sha256":hashlib.sha256(text.encode()).hexdigest()}

class Encoder:
    def __init__(self):self.calls=[]
    def encode_document(self,values):self.calls.append(values);return values
    def encode_query(self,values):return values
    def similarity(self,queries,docs):return [[float(queries[0] in doc) for doc in docs]]

class LocalRetrievalTests(unittest.TestCase):
    def setUp(self):self.encoder=Encoder();self.engine=retrieval.LocalRetrieval(self.encoder)
    def test_cli_cannot_enable_retrieval_outside_personal_auth_boundary(self):
        script=Path(personal.__file__).with_name('qikvrt_effect_ack_http_terminal.py')
        result=subprocess.run([sys.executable,str(script),'--personal-retrieval-model-dir','/unadmitted/model'],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Personal arguments require --personal-state-dir',result.stderr)
    def test_source_identity_hash_and_test_evidence_are_preserved(self):
        rows=[source('b','other'),source('a','needle')]
        result=self.engine.search('needle',rows,1)
        self.assertEqual(result['results'][0]['source_id'],'a')
        self.assertEqual(result['results'][0]['source_sha256'],rows[1]['sha256'])
        self.assertEqual(result['evidence_class'],'TEST_DOUBLE_NOT_MODEL_INFERENCE')
        self.assertFalse(result['field_values_extracted']);self.assertFalse(result['productive_acceptance'])
    def test_changed_source_fails_before_model_call(self):
        row=source('a','original');row['text']='modified'
        with self.assertRaises(retrieval.RetrievalUnavailable):self.engine.search('query',[row])
        self.assertEqual(self.encoder.calls,[])
    def test_duplicate_ids_unknown_fields_and_unbounded_inputs_rejected(self):
        for rows in [[source('a','x'),source('a','y')],[dict(source('a','x'),path='/private')],[source('a','x'*513)]]:
            with self.assertRaises(retrieval.RetrievalUnavailable):self.engine.search('query',rows)
        for limit in [True,0,9]:
            with self.assertRaises(retrieval.RetrievalUnavailable):self.engine.search('query',[source('a','x')],limit)
        self.assertEqual(self.encoder.calls,[])
    def test_source_order_does_not_change_request_identity(self):
        rows=[source('z','x'),source('a','x')]
        a=self.engine.search('none',rows);b=self.engine.search('none',list(reversed(rows)))
        self.assertEqual(a,b);self.assertEqual(a['results'][0]['source_id'],'a')
    def test_nonfinite_scores_and_exceptions_fail_closed_without_echo(self):
        self.encoder.similarity=lambda q,d:[[float('nan')]]
        with self.assertRaises(retrieval.RetrievalUnavailable):self.engine.search('q',[source('a','x')])
        def fail(q,d):raise RuntimeError('private user text')
        self.encoder.similarity=fail
        with self.assertRaisesRegex(retrieval.RetrievalUnavailable,'^LOCAL_RETRIEVAL_INFERENCE_FAILED$'):
            self.engine.search('q',[source('a','x')])
    def test_model_factory_rejects_missing_or_wrong_bytes_before_import(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises((OSError,retrieval.RetrievalUnavailable)):retrieval.LocalRetrieval.from_directory(root)
    def test_model_factory_exact_files_hashes_offline_options_and_load_change(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);root=base/'model';root.mkdir();data=b'fixed model bytes'
            (root/'model.bin').write_bytes(data)
            lock={'model':retrieval.MODEL,'revision':retrieval.REVISION,'files':[{'file':'model.bin','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
            manifest=base/'lock.json';manifest.write_text(json.dumps(lock));calls=[]
            def load(path,**kwargs):calls.append((path,kwargs));return Encoder()
            with patch.object(retrieval,'LOCK',manifest),patch.dict(sys.modules,{'sentence_transformers':types.SimpleNamespace(MultiVectorEncoder=load)}):
                engine=retrieval.LocalRetrieval.from_directory(root)
                self.assertEqual(engine.evidence_class,'LOCAL_MODEL_INFERENCE')
                self.assertEqual(calls[0][1],{'device':'cpu','trust_remote_code':False,'local_files_only':True})
                (root/'extra.py').write_text('not admitted')
                with self.assertRaisesRegex(retrieval.RetrievalUnavailable,'FILE_SET_MISMATCH'):retrieval.LocalRetrieval.from_directory(root)
                (root/'extra.py').unlink();(root/'model.bin').write_bytes(b'changed')
                with self.assertRaisesRegex(retrieval.RetrievalUnavailable,'BYTES_MISMATCH'):retrieval.LocalRetrieval.from_directory(root)
                (root/'model.bin').write_bytes(data);(base/'alias').symlink_to(root,target_is_directory=True)
                with self.assertRaises(retrieval.RetrievalUnavailable):retrieval.LocalRetrieval.from_directory(base/'alias')
                def changed(path,**kwargs):
                    (root/'model.bin').write_bytes(b'changed during load');return Encoder()
                with patch.dict(sys.modules,{'sentence_transformers':types.SimpleNamespace(MultiVectorEncoder=changed)}):
                    with self.assertRaisesRegex(retrieval.RetrievalUnavailable,'CHANGED_DURING_LOAD'):retrieval.LocalRetrieval.from_directory(root)
    def test_authenticated_same_origin_route_never_calls_generator(self):
        with tempfile.TemporaryDirectory() as root:
            transport=TransportDouble()
            runtime=personal.PersonalRuntime(root+'/private','test',KEY,TOKEN,transport=transport,retrieval_engine=self.engine)
            server=ThreadingHTTPServer(('127.0.0.1',0),personal.personal_handler(terminal.Handler,runtime))
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            base='http://127.0.0.1:'+str(server.server_port)
            body={'query':'needle','sources':[source('a','needle')],'limit':1,'confirmed':True}
            def call(token=TOKEN,origin=base,payload=body):
                req=Request(base+'/personal/search',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'Origin':origin})
                return json.load(urlopen(req,timeout=3))
            try:
                self.assertEqual(call()['results'][0]['source_id'],'a')
                for kwargs in [{'token':'wrong'},{'origin':'https://evil.test'},{'payload':dict(body,confirmed=False)},{'payload':dict(body,unknown=True)}]:
                    with self.assertRaises(HTTPError):call(**kwargs)
                self.assertEqual(transport.requests,[])
                self.assertEqual(runtime.sessions(),[])
                runtime.native_terminal=object()
                def denied(*args):raise personal.CapabilityBlock('NATIVE_BINDING_REQUIRED')
                runtime.read_terminal_transition=denied
                before=len(self.encoder.calls)
                with self.assertRaises(HTTPError):call()
                self.assertEqual(len(self.encoder.calls),before)
                runtime.native_terminal=None
            finally:server.shutdown();server.server_close();worker.join();runtime.close()

if __name__=='__main__':unittest.main()
