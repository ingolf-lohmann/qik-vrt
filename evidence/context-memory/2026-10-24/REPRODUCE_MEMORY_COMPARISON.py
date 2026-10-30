# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Diagnostic reproduction only; not a runtime executor.
from pathlib import Path
import copy,gc,hashlib,importlib.util,json,platform,sys,tempfile,time,tracemalloc
WORK=Path(__file__).resolve().parent;ROOT=WORK.parents[2];sys.path.insert(0,str(ROOT/'src'))
import qikvrt_temdd_event_ledger as candidate
raw=(WORK/'TEMDD_BASELINE_SOURCE.py').read_bytes()
assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='372701f5071146d5583dc78c69399f3a6d008d88', 'BASELINE_SOURCE_CHANGED'
assert not (WORK/'MEMORY_COMPARISON_REPRODUCED.json').exists(), 'CREATE_ONLY_DIAGNOSTIC_OUTPUT_EXISTS'
spec=importlib.util.spec_from_file_location('qikvrt_temdd_baseline',WORK/'TEMDD_BASELINE_SOURCE.py');baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
trials=[]
subject={'repository':'ingolf-lohmann/qik-vrt','pr':598,'head':'a1a2204f429bcab7a184afaf51a57b7de03d4ee7','tree':'184adc9c40b27cce1be4995d2eae895d3fbbd2ee'}
for count in [64,1024]:
 with tempfile.TemporaryDirectory(prefix='qikvrt-temdd-memory-fixture-')as td:
  ledger=candidate.Ledger(td,subject)
  try:
   for n in range(count):
    ledger.append({'schema':candidate.SCHEMA,'kind':'OBSERVE','subject':subject,'provenance':{'source':'transputer','native_event_id':'memory-fixture:'+str(n)},'observed_at':'2026-10-24T00:00:00Z','message':'Fresh diagnostic fixture; no productive execution or effect grant','payload':{'text':'\u00e4\\\"\n'+'x'*4096,'ordinal':n}})
   expected=None
   for repeat in range(3):
    order=['baseline','streaming']if repeat%2==0 else ['streaming','baseline']
    for arm in order:
     gc.collect();tracemalloc.start();start=time.perf_counter_ns()
     try:
      result=(baseline.Ledger.history_frontier(ledger)if arm=='baseline'else ledger.history_frontier())
      elapsed=time.perf_counter_ns()-start;_,peak=tracemalloc.get_traced_memory()
     finally:tracemalloc.stop()
     if expected is None:expected=result
     assert result==expected,'FRONTIER_HASH_CHANGED'
     trials.append({'events':count,'payload_chars_per_event':4100,'repeat':repeat,'arm':arm,'elapsed_ns':elapsed,'peak_python_allocation_bytes':peak,'frontier_sha256':result})
  finally:ledger.close()
summary={}
for count in [64,1024]:
 summary[str(count)]={arm:max(t['peak_python_allocation_bytes']for t in trials if t['events']==count and t['arm']==arm)for arm in ['baseline','streaming']}
def identity(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
report={'schema':'qikvrt_temdd_streaming_memory_comparison_v1','artifact_class':'OPERATIONAL_DIAGNOSTIC_NOT_SCIENTIFIC_PUBLICATION','baseline_main':'a1a2204f429bcab7a184afaf51a57b7de03d4ee7','source_path':'src/qikvrt_temdd_event_ledger.py','baseline_source':identity(WORK/'TEMDD_BASELINE_SOURCE.py'),'candidate_source':identity(ROOT/'src/qikvrt_temdd_event_ledger.py'),'python':platform.python_version(),'platform':platform.platform(),'order':'alternating matched arms on the same original SQLite fixture','trials':trials,'summary_maximum_python_allocation_bytes':summary,'all_frontiers_byte_compatible':True,'limitations':['Python traced allocation peak, not process RSS or SQLite C allocation','Local deterministic fixture; no productive-host OOM diagnosis','No widening of writer admission or replacement of original journal','ChatGPT model context and account storage quotas remain external provider limits'],'effect_ack_done':False}
(WORK/'MEMORY_COMPARISON_REPRODUCED.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary))
