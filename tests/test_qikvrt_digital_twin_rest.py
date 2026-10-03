#!/usr/bin/env python3
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
if __name__=="__main__": unittest.main(verbosity=2)
