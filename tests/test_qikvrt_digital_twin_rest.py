#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import dataclasses,json,threading,unittest,urllib.request,urllib.error
from http.server import ThreadingHTTPServer
from src.qikvrt_digital_twin_rest import Store,handler
from src.qikvrt_siemens_reference_integration import TwinState,commit_simulated,prepare,reobserve
class T(unittest.TestCase):
 @classmethod
 def setUpClass(c):
  c.store=Store(TwinState("reference-train-001",7,1200.0,22.0,41.5),"a"*40,"b"*40)
  c.s=ThreadingHTTPServer(("127.0.0.1",0),handler(c.store)); c.t=threading.Thread(target=c.s.serve_forever,daemon=True); c.t.start()
  c.base=f"http://127.0.0.1:{c.s.server_port}"
 @classmethod
 def tearDownClass(c): c.s.shutdown(); c.s.server_close()
 def setUp(self):
  with self.store.lock:
   self.store.state=TwinState("reference-train-001",7,1200.0,22.0,41.5)
   self.store.last_receipt=None
 def req(self,path,body=None):
  data=None if body is None else json.dumps(body).encode()
  q=urllib.request.Request(self.base+path,data=data,headers={"Content-Type":"application/json"})
  try:r=urllib.request.urlopen(q); return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_contract_and_distinct_poles(self):
  code,v=self.req("/api/digital-twin/v1/state"); self.assertEqual(code,200)
  self.assertEqual(v["authority_subject"],"a"*40); self.assertEqual(v["mirror_subject"],"b"*40)
  self.assertFalse(v["pole_equality_claim"]); self.assertFalse(v["effect_ack_done"])
 def test_transition_and_readback(self):
  code,v=self.req("/api/digital-twin/v1/transitions",{"expected_version":7,"target_velocity_mps":23})
  self.assertEqual(code,200); self.assertTrue(v["receipt"]["effect_ack"]); self.assertFalse(v["receipt"]["physical_effect_ack"])
  self.assertEqual(v["state"]["version"],8)
 def test_stale_write_holds(self):
  code,v=self.req("/api/digital-twin/v1/transitions",{"expected_version":6,"target_velocity_mps":24})
  self.assertEqual(code,409); self.assertEqual(v["state"],"HOLD")
 def test_reobserve_rejects_uncommanded_velocity(self):
  before=TwinState("reference-train-001",7,1200.0,22.0,41.5)
  after,effect=commit_simulated(before,prepare(before,target_velocity_mps=23.0))
  wrong=dataclasses.replace(after,velocity_mps=before.velocity_mps)
  self.assertFalse(reobserve(before,wrong,effect)["effect_ack"])
 def test_reobserve_rejects_different_twin_or_unpreserved_state(self):
  before=TwinState("reference-train-001",7,1200.0,22.0,41.5)
  after,effect=commit_simulated(before,prepare(before,target_velocity_mps=23.0))
  for wrong in (
   dataclasses.replace(after,twin_id="reference-train-002"),
   dataclasses.replace(after,position_m=1201.0),
   dataclasses.replace(after,temperature_c=42.0),
  ):
   with self.subTest(wrong=wrong): self.assertFalse(reobserve(before,wrong,effect)["effect_ack"])

# The reflexive fixture uses the canonical broker against a separate persistent
# bare Git repository. No mocked 'persisted=true' flag substitutes for bytes.
import base64
import copy
import os
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from tests import test_qikvrt_authority_transition as authority_tests
from tests.test_qikvrt_github_authority_provider import GitProviderFixture
from src.qikvrt_github_api_shim import GitHubAuthorityProvider
from tools.qikvrt_authority_transition import AuthorityControlPlane, TransitionError
from tools.qikvrt_seed_common import canonical_json_bytes
from src.qikvrt_siemens_reference_integration import digest


class TwinGitProviderFixture(GitProviderFixture):
 def __init__(self,node,destination,source_subject):
  super().__init__(node,destination)
  self.source_subject=copy.deepcopy(source_subject)
  self.object_posts=0
  self.wrong_bytes=False
  self.stop_after_object=None
  self.wrong_receipt_tree=False
  self.wrong_receipt_parents=False
  self.truncated_tree=False
 def git(self,*args,raw=None,env=None):
  return subprocess.check_output(['git','-C',str(self.repository),*args],input=raw,env=env,timeout=10)
 def request(self,method,suffix,payload=None,*,admission=None):
  if method=='POST' and suffix!='git/refs':
   self.calls.append((method,suffix)); self.object_posts+=1
   if suffix=='git/blobs':
    sha=self.git('hash-object','-w','--stdin',raw=base64.b64decode(payload['content'])).decode().strip()
   elif suffix=='git/trees':
    raw=''.join(f"{e['mode']} {e['type']} {e['sha']}\t{e['path']}\n" for e in payload['tree']).encode()
    sha=self.git('mktree',raw=raw).decode().strip()
   elif suffix=='git/commits':
    env=dict(os.environ)
    for actor in ('author','committer'):
     for key in ('name','email','date'):
      env[f'GIT_{actor.upper()}_{key.upper()}']=payload[actor][key]
    parents=[x for p in payload['parents'] for x in ('-p',p)]
    sha=self.git('commit-tree',payload['tree'],*parents,'-F','-',raw=payload['message'].encode(),env=env).decode().strip()
   else: raise AssertionError(suffix)
   if self.stop_after_object==suffix: raise TransitionError('fixture transport interruption after object')
   return 201,{'sha':sha}
  if method=='GET' and suffix.startswith('pulls/'):
   self.calls.append((method,suffix)); return 200,{'number':self.source_subject['pr'],'state':'open',
    'head':{'sha':self.source_subject['head'],'repo':{'full_name':self.source_subject['repository']}}}
  if method=='GET' and suffix.startswith('git/commits/'):
   self.calls.append((method,suffix)); sha=suffix.rsplit('/',1)[1]
   lines=self.git('show','-s','--format=%T%n%P',sha).decode().splitlines()
   return 200,{'sha':sha,'tree':{'sha':'0'*40 if (self.wrong_tree or (self.wrong_receipt_tree and sha!=self.source_subject['head'])) else lines[0]},
    'parents':[] if (self.wrong_receipt_parents and sha!=self.source_subject['head']) else [{'sha':p} for p in lines[1].split()]}
  if method=='GET' and suffix.startswith('git/trees/'):
   self.calls.append((method,suffix)); sha=suffix.rsplit('/',1)[1]; entries=[]
   for line in self.git('ls-tree','-z',sha).split(b'\0'):
    if not line: continue
    head,path=line.split(b'\t'); mode,kind,object_id=head.decode().split()
    entries.append({'path':path.decode(),'mode':mode,'type':kind,'sha':object_id})
   return 200,{'sha':sha,'tree':entries,'truncated':self.truncated_tree}
  if method=='GET' and suffix.startswith('git/blobs/'):
   self.calls.append((method,suffix)); sha=suffix.rsplit('/',1)[1]; raw=self.git('cat-file','blob',sha)
   if self.wrong_bytes: raw+=b' '
   return 200,{'sha':sha,'encoding':'base64','size':len(raw),'content':base64.b64encode(raw).decode()}
  return super().request(method,suffix,payload,admission=admission)


class ReflexiveTwinTests(unittest.TestCase):
 def setUp(self):
  fixture=authority_tests.AuthorityTransitionTests()
  fixture.setUp(); self.addCleanup(fixture.doCleanups)
  self.fixture=fixture; self.cp=fixture.cp
  self.permit=fixture.activate()
  binding=self.cp.readback(authority_tests.NEW_TOKEN)['state']['binding']
  self.subject={k:binding[k] for k in ('repository','head','tree')}; self.subject['pr']=436
  self.remote=TwinGitProviderFixture(fixture.node,fixture.root/'twin-provider.git',self.subject)
  self.adapter=GitHubAuthorityProvider(self.cp,self.subject['repository']); self.adapter._request=self.remote.request
  self.store=self.new_store()
 def new_store(self):
  adapter=GitHubAuthorityProvider(AuthorityControlPlane(self.cp.path),self.subject['repository'])
  adapter._request=self.remote.request
  return Store(TwinState('reference-train-001',7,1200.0,22.0,41.5),'a'*40,'b'*40,
   writer=adapter,writer_capability=authority_tests.NEW_TOKEN,permit=self.permit,repository_subject=self.subject)
 def request(self,key='effect:1',version=7,state=None,predecessor=None):
  state=state or self.store.state
  return {'expected_version':version,'target_velocity_mps':23.0,'binding':{
   **self.subject,'effect_id':key,'expected_predecessor_effect_id':predecessor,'expected_state_sha256':digest(dataclasses.asdict(state))}}
 def apply(self,request=None,store=None):
  request=request or self.request(); store=store or self.store
  return store.apply(request['expected_version'],request['target_velocity_mps'],request['binding'])
 def journal(self,key='effect:1'):
  with self.cp.transaction() as db:
   return db.execute('SELECT status FROM provider_effects WHERE id=?',('twin:'+key,)).fetchone()[0]
 def server(self,store=None,abort_response=False):
  base=handler(store or self.store)
  if abort_response:
   class Abort(base):
    def sendj(h,code,obj):
     if h.command=='POST' and code==200:
      h.connection.shutdown(socket.SHUT_RDWR); h.close_connection=True; return
     return super().sendj(code,obj)
   base=Abort
  server=ThreadingHTTPServer(('127.0.0.1',0),base)
  threading.Thread(target=server.serve_forever,daemon=True).start()
  self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
  return f'http://127.0.0.1:{server.server_port}'
 def http(self,url,body=None):
  request=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(request,timeout=10) as response: return response.status,json.load(response)
  except urllib.error.HTTPError as error:
   with error: return error.code,json.load(error)
 def test_real_http_same_result_in_initiator_and_repository_and_successor(self):
  base=self.server(); code,out=self.http(base+'/api/digital-twin/v1/transitions',self.request())
  self.assertEqual(code,200); self.assertTrue(out['repository_effect_verified']); self.assertFalse(out['effect_ack_done'])
  self.assertEqual(out['effect_state'],'EFFECT_ACK_CONTINUE')
  receipt=out['repository_receipt']; raw=self.remote.git('show',receipt['ref']+':QIKVRT_API_EFFECT.json')
  self.assertEqual(raw,canonical_json_bytes(out['api_result']))
  self.assertEqual(base64.b64decode(out['api_result_bytes_b64']),raw)
  self.assertEqual(json.loads(raw)['request'],self.request(state=TwinState('reference-train-001',7,1200.0,22.0,41.5)))
  self.assertEqual(self.journal(),'VERIFIED')
  request=self.request('effect:2',8,predecessor='effect:1'); request['target_velocity_mps']=24.0
  second=self.apply(request)
  parents=self.remote.git('show','-s','--format=%P',second['repository_receipt']['commit']).decode().split()
  self.assertIn(receipt['commit'],parents); self.assertIn(self.subject['head'],parents)
  self.assertEqual(self.remote.posts,2)
  self.assertNotIn(authority_tests.NEW_TOKEN.encode(),raw)
 def test_stale_head_tree_pr_and_repository_never_call_writer(self):
  for key,value in (('head','0'*40),('tree','0'*40),('pr',435),('repository','Goldkelch/qik-vrt')):
   with self.subTest(key=key):
    request=self.request(); request['binding'][key]=value
    with self.assertRaisesRegex(ValueError,'STALE_REPOSITORY_SUBJECT'): self.apply(request)
  self.assertEqual(self.remote.calls,[])
 def test_live_pr_or_tree_drift_rejected_before_any_post(self):
  for drift in ('head','tree'):
   with self.subTest(drift=drift):
    store=self.new_store()
    self.remote.source_subject['head']='0'*40 if drift=='head' else self.subject['head']
    self.remote.wrong_tree=drift=='tree'
    with self.assertRaises(TransitionError): self.apply(store=store)
  self.assertEqual(self.remote.posts,0); self.assertEqual(self.remote.object_posts,0)
 def test_replay_and_different_content_reuse_are_readback_only(self):
  self.apply(); calls=(self.remote.posts,self.remote.object_posts)
  for request in (self.request(),self.request('effect:1',8,predecessor='effect:1')):
   with self.assertRaises((ValueError,TransitionError)): self.apply(request)
  self.assertEqual((self.remote.posts,self.remote.object_posts),calls)
  restarted=self.new_store(); out=restarted.recover('effect:1')
  self.assertEqual(restarted.state.version,8); self.assertEqual(self.remote.posts,1)
  self.assertFalse(out['effect_ack_done'])
 def test_concurrent_writers_and_versions_admit_at_most_one(self):
  stores=[self.new_store(),self.new_store()]; barrier=threading.Barrier(2)
  def race(index):
   barrier.wait(timeout=10)
   try: return self.apply(self.request(f'effect:{index+1}'),stores[index])
   except (ValueError,RuntimeError): return None
  with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(race,(0,1)))
  self.assertEqual(sum(out is not None for out in results),1); self.assertEqual(self.remote.posts,1)
 def test_native_cas_conflict_cannot_launder_matching_competitor(self):
  self.remote.before_post=lambda payload:self.remote.git('update-ref',payload['ref'],payload['sha'])
  with self.assertRaisesRegex(TransitionError,'CAS_REJECTED'): self.apply()
  self.assertEqual(self.journal(),'REJECTED')
  with self.assertRaises(TransitionError): self.new_store().recover('effect:1')
  self.assertEqual(self.store.state.version,7); self.assertEqual(self.remote.posts,1)
 def test_provider_transport_abort_after_effect_recovers_get_only(self):
  def abort(): raise TransitionError('fixture lost transport after ref CAS')
  self.remote.after_post=abort
  with self.assertRaises(TransitionError): self.apply()
  self.assertEqual(self.journal(),'PENDING'); self.assertEqual(self.store.state.version,7)
  self.remote.after_post=None; mutations=(self.remote.posts,self.remote.object_posts)
  restarted=self.new_store(); out=restarted.recover('effect:1')
  self.assertEqual(restarted.state.version,8); self.assertTrue(out['repository_receipt']['fresh_byte_readback'])
  self.assertEqual((self.remote.posts,self.remote.object_posts),mutations)
  self.assertEqual(self.journal(),'VERIFIED')
 def test_http_transport_abort_after_durable_effect_does_not_repeat(self):
  base=self.server(abort_response=True)
  with self.assertRaises((OSError,ConnectionError)): self.http(base+'/api/digital-twin/v1/transitions',self.request())
  self.assertEqual(self.journal(),'VERIFIED'); self.assertEqual(self.remote.posts,1)
  restarted=self.new_store(); recovery_url=self.server(restarted)+'/api/digital-twin/v1/receipts/effect:1'
  code,out=self.http(recovery_url)
  self.assertEqual(code,200); self.assertEqual(restarted.state.version,8); self.assertEqual(self.remote.posts,1)
  self.assertFalse(out['effect_ack_done'])
 def test_wrong_byte_readback_keeps_pending_and_fences_new_effects_and_takeover(self):
  self.remote.wrong_bytes=True
  base=self.server(); code,out=self.http(base+'/api/digital-twin/v1/transitions',self.request())
  self.assertEqual(code,409); self.assertFalse(out['effect_ack_done']); self.assertEqual(self.journal(),'PENDING')
  self.assertEqual(self.store.state.version,7)
  with self.assertRaises((ValueError,TransitionError)): self.apply(self.request('effect:2'))
  with self.assertRaises(TransitionError): self.new_store().recover('effect:1')
  observation=self.cp.observe(self.fixture.competitor,self.fixture.manifest,authority_tests.COMPETITOR_TOKEN)
  with self.assertRaisesRegex(TransitionError,'unresolved provider effect'):
   self.cp.takeover(self.fixture.competitor,self.fixture.manifest,authority_tests.COMPETITOR_TOKEN,observation)
  mutations=(self.remote.posts,self.remote.object_posts); self.remote.wrong_bytes=False
  self.new_store().recover('effect:1')
  self.assertEqual((self.remote.posts,self.remote.object_posts),mutations)
 def test_ambiguous_object_write_without_ref_never_blindly_retries(self):
  self.remote.stop_after_object='git/blobs'
  with self.assertRaises(TransitionError): self.apply()
  self.remote.stop_after_object=None
  with self.assertRaises(TransitionError): self.new_store().recover('effect:1')
  with self.assertRaises(TransitionError): self.apply(store=self.new_store())
  self.assertEqual(self.remote.object_posts,1); self.assertEqual(self.remote.posts,0)
  self.assertEqual(self.journal(),'PENDING')
 def test_old_writer_permit_cannot_enter_reflexive_broker(self):
  self.store.permit=self.fixture.old_permit; self.store.writer_capability=authority_tests.OLD_TOKEN
  with self.assertRaises(TransitionError): self.apply()
  self.assertEqual(self.remote.calls,[])
 def test_duplicate_nonfinite_and_unknown_request_fields_fail_without_effect(self):
  base=self.server()
  for body in ({**self.request(),'extra':True},{**self.request(),'expected_version':True},
               {**self.request(),'target_velocity_mps':float('nan')}):
   code,out=self.http(base+'/api/digital-twin/v1/transitions',body)
   self.assertEqual(code,409); self.assertFalse(out['effect_ack_done'])
  self.assertEqual(self.remote.object_posts,0); self.assertEqual(self.remote.posts,0)


 def test_stale_durable_predecessor_after_restart_never_mutates(self):
  self.apply(); mutations=(self.remote.posts,self.remote.object_posts)
  restarted=self.new_store()
  with self.assertRaisesRegex(TransitionError,'STALE_TWIN_PREDECESSOR_CAS'):
   self.apply(self.request('effect:2',state=restarted.state),restarted)
  self.assertEqual((self.remote.posts,self.remote.object_posts),mutations)
  restarted.recover('effect:1')
  request=self.request('effect:2',8,state=restarted.state,predecessor='effect:1')
  request['binding']['expected_state_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'STALE_EXACT_TWIN_STATE'):self.apply(request,restarted)
 def test_wrong_commit_parents_and_truncated_tree_never_ack(self):
  for flag in ('wrong_receipt_tree','wrong_receipt_parents','truncated_tree'):
   with self.subTest(flag=flag):
    if self.remote.posts:
     setattr(self.remote,flag,True)
     with self.assertRaises(TransitionError):self.new_store().recover('effect:1')
    else:
     self.remote.after_post=lambda:setattr(self.remote,flag,True)
     with self.assertRaises(TransitionError):self.apply()
    self.assertEqual(self.store.state.version,7);self.assertEqual(self.journal(),'PENDING')
    setattr(self.remote,flag,False)
  self.remote.after_post=None;self.new_store().recover('effect:1')
  self.assertEqual(self.remote.posts,1)
 def test_actual_transport_uses_the_same_locked_intent_for_every_object(self):
  import io
  from src import qikvrt_github_api_shim as shim
  adapter=self.store.writer
  adapter._request=GitHubAuthorityProvider._request.__get__(adapter)
  def open_request(request,timeout):
   suffix=request.full_url.split('/qik-vrt/',1)[1]
   payload=None if request.data is None else json.loads(request.data)
   status,body=self.remote.request(request.get_method(),suffix,payload)
   response=io.BytesIO(canonical_json_bytes(body));response.status=status;response.geturl=lambda:request.full_url
   return response
  env={'GITHUB_TOKEN':'github-fixture-token-abcdefghijklmnopqrstuvwxyz','QIKVRT_GITHUB_TOKEN_EXPIRES_UTC':'2099-01-01T00:00:00Z'}
  with mock.patch.dict(os.environ,env),mock.patch.object(shim.urllib.request,'build_opener') as opener:
   opener.return_value.open.side_effect=open_request
   out=self.apply();self.assertTrue(out['repository_effect_verified'])
   self.assertFalse(out['effect_ack_done']);self.assertEqual(self.remote.object_posts,3);self.assertEqual(self.remote.posts,1)
   for suffix in ('git/blobs','git/trees','git/commits','git/refs'):
    with self.assertRaises(TransitionError):adapter._request('POST',suffix,{})


if __name__ == "__main__":
 unittest.main(verbosity=2)
