#!/usr/bin/env python3
"""Read-only GitHub event bridge; native command admission remains fail-closed."""
import json,os,time,hashlib,urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
REPO="ingolf-lohmann/qik-vrt"
TOKEN=os.environ.get("QIKVRT_GITHUB_TOKEN","")
SESSION=os.environ.get("QIKVRT_TERMINAL_SESSION_TOKEN","")
def fetch(path):
 if not TOKEN: raise RuntimeError("GITHUB_TOKEN_NOT_CONFIGURED")
 req=urllib.request.Request("https://api.github.com/repos/"+REPO+path,headers={"Authorization":"Bearer "+TOKEN,"Accept":"application/vnd.github+json","User-Agent":"qikvrt-terminal-bridge"})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def snapshot():
 pr=fetch("/pulls/653");issue=fetch("/issues/651")
 runs=fetch("/actions/runs?per_page=100").get("workflow_runs",[])
 runs=[r for r in runs if r.get("head_sha")==pr["head"]["sha"]]
 return {"type":"snapshot","subject":"issue/651","head_sha":pr["head"]["sha"],"tree_sha":None,"stage":"ci","status":"OBSERVED","evidence_url":pr["html_url"],"runs":runs,"issue":{"number":issue["number"],"state":issue["state"]},"pr":{"number":pr["number"],"merged":pr["merged"]},"effect":{"status":"UNVERIFIED"}}
class Handler(BaseHTTPRequestHandler):
 protocol_version="HTTP/1.1"
 def sendjson(self,status,obj):
  data=json.dumps(obj).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
 def auth(self):
  import hmac
  return bool(SESSION and hmac.compare_digest(self.headers.get("Authorization",""),"Bearer "+SESSION))
 def do_GET(self):
  if self.path=="/":
   data=(Path(__file__).parent/"index.html").read_bytes();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
  if self.path=="/v1/devops/snapshot":
   try:self.sendjson(200,snapshot())
   except Exception as e:self.sendjson(503,{"error":str(e)})
   return
  if self.path=="/v1/devops/events":
   if not self.auth():self.sendjson(401,{"error":"SESSION_REQUIRED"});return
   self.send_response(200);self.send_header("Content-Type","text/event-stream");self.send_header("Cache-Control","no-cache");self.send_header("Connection","close");self.end_headers()
   try:
    prev=None
    for _ in range(30):
     try:
      data=snapshot();digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
      if digest!=prev:self.wfile.write(("id: "+digest+"\ndata: "+json.dumps(data)+"\n\n").encode());prev=digest
      else:self.wfile.write(b": keepalive\n\n")
      self.wfile.flush()
     except Exception as e:self.wfile.write(("event: diagnostic\ndata: "+json.dumps({"error":str(e)})+"\n\n").encode());self.wfile.flush()
     time.sleep(2)
   except (BrokenPipeError,ConnectionResetError):pass
   self.close_connection=True;return
  self.sendjson(404,{"error":"NOT_FOUND"})
 def do_POST(self):
  if self.path!="/v1/devops/commands":self.sendjson(404,{"error":"NOT_FOUND"});return
  if not self.auth():self.sendjson(401,{"error":"SESSION_REQUIRED"});return
  if not os.environ.get("QIKVRT_TERMINAL_ORIGIN") or self.headers.get("Origin")!=os.environ["QIKVRT_TERMINAL_ORIGIN"]:self.sendjson(403,{"error":"ORIGIN_NOT_ADMITTED"});return
  self.sendjson(503,{"admission":"BLOCKED","error":"ORIGINAL_TERMINAL_TRANSPUTER_ADAPTER_NOT_ADMITTED"})
 def log_message(self,*args):pass
if __name__=="__main__":
 host=os.environ.get("QIKVRT_TERMINAL_BIND","127.0.0.1")
 if host!="127.0.0.1":raise SystemExit("Loopback only; use HTTPS reverse proxy")
 ThreadingHTTPServer((host,int(os.environ.get("QIKVRT_TERMINAL_PORT","8765"))),Handler).serve_forever()
