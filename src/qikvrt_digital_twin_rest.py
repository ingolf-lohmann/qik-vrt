#!/usr/bin/env python3
"""QIK-VRT Digital Twin REST V1: exact-subject, fail-closed reference API."""
from __future__ import annotations
import argparse,json,threading
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from src.qikvrt_siemens_reference_integration import TwinState,observe,prepare,commit_simulated,reobserve,digest

class Store:
 def __init__(self,state,authority_subject,mirror_subject):
  self.state=state; self.authority_subject=authority_subject; self.mirror_subject=mirror_subject
  self.lock=threading.RLock(); self.last_receipt=None
 def snapshot(self):
  with self.lock:
   body=asdict(self.state)
   return {"schema":"qikvrt_digital_twin_rest_v1","state":body,"state_sha256":digest(body),
    "authority_subject":self.authority_subject,"mirror_subject":self.mirror_subject,
    "pole_equality_claim":False,"effect_ack_done":False}
 def apply(self,expected_version,target_velocity_mps):
  with self.lock:
   if expected_version!=self.state.version: raise ValueError("STALE_EXACT_TWIN_VERSION")
   before=self.state; p=prepare(before,target_velocity_mps=target_velocity_mps)
   after,effect=commit_simulated(before,p); receipt=reobserve(before,after,effect)
   if not receipt["effect_ack"]: raise ValueError("POST_EFFECT_READBACK_FAILED")
   self.state=after; self.last_receipt=receipt
   return {"prepared":p,"effect":effect,"receipt":receipt,"state":asdict(after)}

def handler(store):
 class H(BaseHTTPRequestHandler):
  protocol_version="HTTP/1.1"
  def sendj(self,code,obj):
   b=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
   self.send_response(code); self.send_header("Content-Type","application/json")
   self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store")
   self.send_header("X-Content-Type-Options","nosniff"); self.end_headers(); self.wfile.write(b)
  def body(self):
   try:n=int(self.headers.get("Content-Length","0"))
   except ValueError: raise ValueError("INVALID_CONTENT_LENGTH")
   if n<1 or n>16384: raise ValueError("INVALID_BODY_SIZE")
   raw=self.rfile.read(n); v=json.loads(raw)
   if not isinstance(v,dict): raise ValueError("OBJECT_REQUIRED")
   return v
  def do_GET(self):
   p=urlsplit(self.path).path
   if p=="/api/digital-twin/v1": return self.sendj(200,{"schema":"qikvrt_digital_twin_rest_v1","links":{"state":"/api/digital-twin/v1/state","receipt":"/api/digital-twin/v1/receipt","transition":"/api/digital-twin/v1/transitions"},"effect_ack_done":False})
   if p=="/api/digital-twin/v1/state": return self.sendj(200,store.snapshot())
   if p=="/api/digital-twin/v1/receipt":
    return self.sendj(200,{"receipt":store.last_receipt,"effect_ack_done":False})
   return self.sendj(404,{"state":"HOLD","reason":"NOT_FOUND","effect_ack_done":False})
  def do_POST(self):
   if urlsplit(self.path).path!="/api/digital-twin/v1/transitions": return self.sendj(404,{"state":"HOLD","reason":"NOT_FOUND","effect_ack_done":False})
   try:
    v=self.body()
    if set(v)!={"expected_version","target_velocity_mps"}: raise ValueError("CLOSED_REQUEST_SCHEMA")
    out=store.apply(v["expected_version"],float(v["target_velocity_mps"]))
    return self.sendj(200,out)
   except (ValueError,TypeError,json.JSONDecodeError) as e:
    return self.sendj(409,{"state":"HOLD","reason":str(e),"effect_ack_done":False})
  def log_message(self,*a): pass
 return H

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--state",required=True); ap.add_argument("--authority-subject",required=True); ap.add_argument("--mirror-subject",required=True); ap.add_argument("--bind",default="127.0.0.1"); ap.add_argument("--port",type=int,default=8782); ns=ap.parse_args()
 state=TwinState.from_dict(json.load(open(ns.state,encoding="utf-8")))
 ThreadingHTTPServer((ns.bind,ns.port),handler(Store(state,ns.authority_subject,ns.mirror_subject))).serve_forever()
if __name__=="__main__": main()
