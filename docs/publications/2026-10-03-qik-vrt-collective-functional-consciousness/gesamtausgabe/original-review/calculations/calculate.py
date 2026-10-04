from pathlib import Path
import hashlib,json,statistics,subprocess,tempfile,os,sys
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT/'historical_sources/qikvrt_collective_cognition_ab_microbenchmark_20261003.json').read_bytes()
data=json.loads(raw)
recomputed=[]
for c in data['cases']:
 a=statistics.median(c['baseline_samples_s']); b=statistics.median(c['reciprocal_samples_s'])
 assert abs(a-c['baseline_median_s'])<1e-12 and abs(b-c['reciprocal_median_s'])<1e-12
 assert abs(a/b-c['wall_speedup_x'])<1e-12
 assert len(c['baseline_samples_s'])==len(c['reciprocal_samples_s'])==7
 recomputed.append({'N':c['subjects'],'drift':c['mutation_fraction'],'control_ms':a*1000,'delta_ms':b*1000,'speedup':a/b,'comparison_saved_fraction':1-c['reciprocal_comparisons']/c['baseline_comparisons']})
# Independent, isolated demonstrations of two method-boundary failures.
p=subprocess.run([sys.executable,'-c',"import sys;sys.stdout.buffer.write(bytes([255,254,0]))"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=2)
try:
 p.stdout.decode('utf-8'); binary_rejected=False
except UnicodeDecodeError:
 binary_rejected=True
with tempfile.TemporaryDirectory() as tmp:
 def git(*args):
  return subprocess.run(['git','-C',tmp,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=5).stdout
 git('init','-q'); git('config','user.name','Local method control'); git('config','user.email','method-control@example.invalid');git('config','core.filemode','true')
 f=Path(tmp)/'same-content'; f.write_bytes(b'constant\n')
 git('add','same-content');git('commit','-qm','before')
 h0=git('rev-parse','HEAD').decode().strip();f.chmod(0o755);git('add','same-content');git('commit','-qm','mode-only')
 h1=git('rev-parse','HEAD').decode().strip()
 same=git('show',h0+':same-content')==git('show',h1+':same-content')
 changed=git('diff','--no-renames','--name-only',h0,h1).decode().splitlines()
 assert same and changed==['same-content']
linux=[0.349138,0.214989,0.163044]
amdahl=[{'p':p,'s_local':2.5,'s_total':1/((1-p)+p/2.5),'time_saved':p*(1-1/2.5)} for p in [.1,.3,.5,.8]]
result={'kind':'local_arithmetic_and_isolated_method_controls_not_live_distributed_benchmark','source_sha256':hashlib.sha256(raw).hexdigest(),'micro_rows':recomputed,'linux_ratios_of_documented_medians':[linux[0]/x for x in linux],'linux_time_reductions_from_documented_medians':[1-x/linux[0] for x in linux],'amdahl_scenarios_not_measurements':amdahl,'historical_structural_example':{'files':3928,'median_delta':20,'ratio':3928/20,'saved_fraction':1-20/3928},'negative_controls':{'binary_utf8_text_path_rejected':binary_rejected,'mode_only_equal_blob_bytes_but_nonempty_git_diff':same and changed==['same-content']},'scope_limit':'No current Authority fetch, remote mutations, global runtime verification or kernel proof executed.'}
(ROOT/'calculations/RECALCULATIONS_AND_METHOD_CONTROLS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(result,indent=2))
