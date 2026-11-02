// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Derived from the Owner-supplied devops.html, SHA-256 6d43e51f2666c4222ce09ae438a309329f99d0aa871cb80f0c769e1b1ab69a0b.

(function(root){
 'use strict';
 const SHA=/^[a-f0-9]{40}$/, REPO=/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/;
 const STATES=new Set(['success','failure','cancelled','timed_out','skipped','neutral','action_required','in_progress','queued','waiting','requested','pending']);
 function iso(value){const n=typeof value==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)?Date.parse(value):NaN;return Number.isFinite(n)?new Date(n).toISOString():null;}
 function safeInt(n,min=0){return Number.isSafeInteger(n)&&n>=min;}
 function fresh(s,now){const t=iso(s?.observed_at);return Boolean(t&&!s.error&&!s.stale&&now-Date.parse(t)>=-5000&&now-Date.parse(t)<=Math.min(900,Math.max(1,s.interval_seconds||240)+30)*1000);}
 function link(value,repo,id){try{const u=new URL(value);return u.protocol==='https:'&&u.hostname==='github.com'&&!u.username&&!u.password&&!u.search&&!u.hash&&u.pathname==='/'+repo+'/actions/runs/'+id?u.href:null;}catch{return null;}}
 function endpoint(value,repo){try{const u=new URL(value);if(u.origin!=='https://api.github.com'||u.username||u.password||u.hash||u.pathname!=='/repos/'+repo+'/actions/runs')return '';for(const [key,v] of u.searchParams){if(!['head_sha','page','per_page','status'].includes(key)||key==='head_sha'&&!SHA.test(v)||['page','per_page'].includes(key)&&!/^\d{1,5}$/.test(v)||key==='status'&&!STATES.has(v))return '';}return u.href;}catch{return '';}}
 function run(row,repo,source){
  if(!row||!safeInt(row.id,1)||!safeInt(row.attempt,1)||row.attempt>4294967295||!SHA.test(row.sha||'')||!iso(row.updated_at))return null;
  const state=row.status==='completed'?(STATES.has(row.conclusion)?row.conclusion:'unknown'):(STATES.has(row.status)?row.status:'unknown');
  return {id:row.id,attempt:row.attempt,repo,name:String(row.name||'Workflow').slice(0,500),sha:row.sha,status:row.status==='completed'?'completed':state,conclusion:row.status==='completed'?state:'',state,event:String(row.event||'unknown').slice(0,80),updated_at:iso(row.updated_at),started_at:iso(row.started_at),url:link(row.url,repo,row.id),workflow_url:typeof row.workflow_url==='string'?row.workflow_url:null,source_observed_at:iso(source?.observed_at),source_endpoint:endpoint(source?.endpoint,repo),source_fresh:false};
 }
 function project(data,now=Date.now()){
  if(!data||!['qikvrt-devops-capture/v1','qikvrt-public-activity/v1'].includes(data.schema)||!Array.isArray(data.repositories))throw Error('Ungültige Momentaufnahme.');
  const repos=[],rows=[],warnings=[];
  for(const repo of data.repositories){
   if(!repo||!REPO.test(repo.name||'')||!Array.isArray(repo.runs)||repo.runs.length>10000)throw Error('Ungültiger Repository-Umfang.');
   const source=repo.sources?.recent||{},currentHead=SHA.test(repo.head||'')?repo.head:null;
   const recentFresh=fresh(source,now),headFresh=fresh(repo.sources?.branch,now),by=new Map();
   for(const raw of repo.runs){const r=run(raw,repo.name,source);if(!r){warnings.push('Ungültiger Lauf wurde ausgelassen.');continue;}r.source_fresh=recentFresh;const key=r.id+':'+r.attempt;const old=by.get(key);if(!old||r.updated_at>old.updated_at)by.set(key,r);}
   const valid=[...by.values()];rows.push(...valid);
   const exact=valid.filter(r=>r.sha===currentHead),ci=exact.filter(r=>r.event==='push'&&r.workflow_url==='https://github.com/'+repo.name+'/blob/'+r.sha+'/.github/workflows/qikvrt_ci.yml').sort((a,b)=>b.updated_at.localeCompare(a.updated_at))[0]||null;
   const coverage=repo.coverage||{};
   repos.push({name:repo.name,head:currentHead,tree:SHA.test(repo.tree||'')?repo.tree:null,source,source_fresh:recentFresh,head_fresh:headFresh,head_observed_at:iso(repo.sources?.branch?.observed_at),coverage_complete:coverage.complete===true,reported_total:safeInt(coverage.reported_total)?coverage.reported_total:null,ci,ci_state:ci&&Date.parse(ci.updated_at)<=now+5000&&recentFresh&&headFresh?ci.state:'unknown',run_count:valid.length});
  }
  rows.sort((a,b)=>b.updated_at.localeCompare(a.updated_at)||b.id-a.id);
  const primary=repos.find(r=>r.name==='ingolf-lohmann/qik-vrt')||repos[0]||null;
  const jobsets=Array.isArray(data.job_sets)?data.job_sets:[];
  const bound=primary?.ci?jobsets.find(s=>s.repository===primary.name&&s.run_id===primary.ci.id&&s.attempt===primary.ci.attempt&&s.head===primary.head):null;
  const jobs=(bound?.jobs||[]).filter(j=>safeInt(j.id,1)).map(j=>{const start=iso(j.started_at),end=iso(j.completed_at);const duration=j.conclusion!=='skipped'&&start&&end&&Date.parse(end)>=Date.parse(start)?Math.round((Date.parse(end)-Date.parse(start))/1000):null;return{id:j.id,name:String(j.name||'Job').slice(0,500),state:STATES.has(j.conclusion)?j.conclusion:(STATES.has(j.status)?j.status:'unknown'),duration};});
  const delivery=data.delivery_evidence||{},page=(delivery.pages||[]).find(p=>p.url==='https://raumzeitterminal.de/');
  const domainFresh=page&&fresh({observed_at:page.observed_at,interval_seconds:870},now);
  const domain={state:domainFresh&&safeInt(page.status,100)?(page.status>=400?'failure':'unknown'):'unknown',http_status:page?.status??null,observed_at:page?.observed_at||null,url:delivery.readback_url||null};
  const native=delivery.native||{},nativeFresh=fresh({observed_at:native.observed_at,interval_seconds:870},now);
  return{schema:'qikvrt-devops-projection/v1',repositories:repos,primary,rows,jobs,job_source:bound?{observed_at:iso(bound.observed_at),run_id:bound.run_id,attempt:bound.attempt,head:bound.head}:null,warnings,domain,native:{state:nativeFresh&&native.native_available===false?'blocked':'unknown',reason:native.reason||'Native Runtime nicht abgenommen.'},captured_at:iso(data.captured_at)||iso(data.generated_at),effect_ack_done:false};
 }
 function canonical(v){return v&&typeof v==='object'?Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);}
 async function exportRows(p){
  if(!root.crypto?.subtle)throw Error('SHA-256 für diesen Client nicht verfügbar.');
  const result=[];
  for(const r of p.rows){if(!r.source_observed_at)throw Error('Quellzeit fehlt; Export bleibt gesperrt.');const repo=p.repositories.find(x=>x.name===r.repo);const row={repository:r.repo,run_id:r.id,attempt:r.attempt,run_head:r.sha,repository_head:repo.head||'',repository_head_observed_at:repo.head_observed_at,workflow_name:r.name,event:r.event,status:r.status,conclusion:r.conclusion,source_updated_at:r.updated_at,source_observed_at:r.source_observed_at,started_at:r.started_at,source_url:r.url||'',source_endpoint:r.source_endpoint,source_complete:repo.coverage_complete};const digest=await root.crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(row)));row.projection_sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');result.push(row);}
  return result;
 }
 function escape(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
 root.QikVrtDevops={project,exportRows,canonical,escape,fresh};
})(globalThis);
