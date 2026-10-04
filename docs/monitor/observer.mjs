import {readFileSync} from 'node:fs';
const PAGE=readFileSync(new URL('./index.html',import.meta.url),'utf8');
// Copyright 2026 Ingolf Lohmann. Implemented with OpenAI Codex.
// Reuses the GitHub REST observation contract of docs/monitor/index.html,
// source ingolf-lohmann/qik-vrt @ 93be182a277f29fcb1ffb5d4ace0483f6c29dc58.
// Observer is read-only; status success is never promoted to EFFECT_ACK_DONE.
const VERSION='2026-10-04.7';
const CACHE_ORIGIN='https://qikvrt-monitor.invalid';
let REPOS=[
 {name:'ingolf-lohmann/qik-vrt',role:'Persönlicher Knoten',branch:'main'},
 {name:'Goldkelch/qik-vrt',role:'Authority',branch:'main'}
];
export function configureRepositories(repos){
 if(!Array.isArray(repos)||!repos.length||repos.length>10||repos.some(r=>!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(r.name)||r.branch!=='main'))throw new Error('Invalid public repository configuration');
 REPOS=repos;
}
export function invalidateRepository(repo){for(const key of memory.keys())if(key.startsWith(repo+'/'))memory.delete(key)}
const CAUSES={
 push:['Code geändert','Push','Der Head ist dem Push-Lauf zugeordnet.'],
 pull_request:['Pull Request','PR-Ereignis','PR und Head stammen aus dem GitHub-Lauf.'],
 pull_request_target:['Pull Request','PR im Basiskontext','Dieser Lauf verwendet den Basiskontext.'],
 workflow_dispatch:['Dispatch','UI oder API','GitHub unterscheidet in dieser Laufantwort nicht zwischen UI und API.'],
 schedule:['Zeitplan','Zeitplan','Zeitgesteuerter GitHub-Workflow.'],
 workflow_run:['Folgeworkflow','Anderer Workflow','Der konkrete Vorgängerlauf ist in dieser API-Antwort nicht ausgewiesen.'],
 issue_comment:['Kommentar','Issue- oder PR-Kommentar','Der konkrete Kommentar wird dem Lauf in dieser API-Antwort nicht zugeordnet.'],
 issues:['Issue','Issue-Ereignis','Die konkrete Issue-Aktion ist hier nicht ausgewiesen.'],
 repository_dispatch:['Externes Signal','Repository-Dispatch','Ein API-Signal; seine individuelle Nutzlast ist hier nicht ausgewiesen.'],
 pull_request_review:['Review','PR-Review','Review-Ereignis laut GitHub.'],
 release:['Release','Release-Ereignis','Release-Ereignis laut GitHub.'],
 merge_group:['Merge Queue','Merge-Gruppe','Prüfung einer Merge-Gruppe laut GitHub.']
};
const memory=new Map(),inflight=new Map();
function iso(ms=Date.now()){return new Date(ms).toISOString()}
function ghurl(value){try{const u=new URL(value);return u.protocol==='https:'&&u.hostname==='github.com'?u.href:null}catch{return null}}
function integer(v){return Number.isSafeInteger(v)&&v>=0?v:null}
export function normalizeRun(r,repo){
 const event=typeof r.event==='string'?r.event:'unknown';
 const c=CAUSES[event]||['Weitere Auslöser',event,'GitHub-Ereignis: '+event];
 const sha=/^[a-f0-9]{40}$/.test(r.head_sha||'')?r.head_sha:null;
 const path=typeof r.path==='string'?r.path.split('@')[0]:null;
 const state=r.conclusion==='action_required'||r.status==='action_required'?'action_required':r.status==='completed'?(r.conclusion||'unknown'):(r.status||'unknown');
 return {id:r.id,repo,name:r.name||r.display_title||'Workflow',title:r.display_title||r.name||'Workflow',
 state,status:r.status,conclusion:r.conclusion,event,cause:{category:c[0],label:c[1],detail:c[2],evidence:'github.run.event'},
 actor:r.actor?.login||null,triggering_actor:r.triggering_actor?.login||null,branch:r.head_branch||null,sha,
 attempt:r.run_attempt||1,run_number:r.run_number,created_at:r.created_at,updated_at:r.updated_at,started_at:r.run_started_at,
 url:ghurl(r.html_url),commit_url:sha?'https://github.com/'+repo+'/commit/'+sha:null,
 workflow_url:sha&&path?.startsWith('.github/workflows/')?'https://github.com/'+repo+'/blob/'+sha+'/'+path:null,
 prs:Array.isArray(r.pull_requests)?r.pull_requests.filter(p=>Number.isSafeInteger(p.number)).map(p=>({
 number:p.number,url:'https://github.com/'+repo+'/pull/'+p.number,head_sha:p.head?.sha||null})):[]};
}
export function normalizeEvent(e,repo){
 const p=e.payload||{},target=p.pull_request||p.issue||{};
 let title=e.type||'Ereignis',detail=p.action||'',category='Weitere Auslöser';
 let url=ghurl(p.comment?.html_url||p.review?.html_url||target.html_url||p.release?.html_url);
 if(e.type==='PushEvent'){category='Code geändert';title='Push';detail=(p.ref||'').replace('refs/heads/','');
 if(/^[a-f0-9]{40}$/.test(p.head||''))url='https://github.com/'+repo+'/commit/'+p.head}
 else if(e.type==='PullRequestEvent'){category='Pull Request';title='PR #'+target.number}
 else if(e.type==='IssueCommentEvent'){category='Kommentar';title='Kommentar · #'+target.number}
 else if(e.type==='IssuesEvent'){category='Issue';title='Issue #'+target.number}
 else if(/Review/.test(e.type||'')){category='Review';title='Review · PR #'+target.number}
 else if(e.type==='CreateEvent'||e.type==='DeleteEvent'){category='Code geändert';title=e.type==='CreateEvent'?'Angelegt':'Entfernt';detail=(p.ref_type||'')+' · '+(p.ref||'')}
 else if(e.type==='ReleaseEvent'){category='Release';title=p.release?.name||'Release'}
 return {id:e.id,repo,type:e.type,title,detail,category,actor:e.actor?.login||null,at:e.created_at,url:url||'https://github.com/'+repo};
}
async function edgeCache(){
 if(typeof caches==='undefined')return null;
 try{return await caches.open('qikvrt-activity-v2')}catch{return null}
}
async function cached(key){
 const local=memory.get(key);
 if(local&&Date.parse(local.next_attempt_at)>Date.now())return local;
 const cache=await edgeCache();
 if(cache){try{
 const r=await cache.match(new Request(CACHE_ORIGIN+'/__cache/github/'+encodeURIComponent(key)));
 if(r){const v=await r.json();memory.set(key,v);return v}}catch{}}
 return local||null;
}
async function saveCache(key,v){
 memory.set(key,v);
 const cache=await edgeCache();
 if(cache)await cache.put(new Request(CACHE_ORIGIN+'/__cache/github/'+encodeURIComponent(key)),
 new Response(JSON.stringify(v),{headers:{'content-type':'application/json','cache-control':'public, max-age=86400'}}));
}
export async function githubSource(repo,path,interval,env={}){
 const key=repo+path,prior=await cached(key);
 if(prior&&Date.parse(prior.next_attempt_at)>Date.now())return prior;
 if(inflight.has(key))return inflight.get(key);
 const task=(async()=>{
 const at=iso(),headers={Accept:'application/vnd.github+json','User-Agent':'QIK-VRT-public-activity','X-GitHub-Api-Version':'2026-03-10'};
 if(prior?.etag)headers['If-None-Match']=prior.etag;
 let value;
 try{
 const response=await fetch('https://api.github.com/repos/'+repo+path,{headers,signal:AbortSignal.timeout(12000)});
 const reset=Number(response.headers.get('x-ratelimit-reset')),remaining=response.headers.get('x-ratelimit-remaining');
 const retryAfter=Number(response.headers.get('retry-after'));
 const rate={remaining:remaining===null?null:Number(remaining),reset_at:reset?iso(reset*1000):null};
 if(response.status===304&&prior?.data!==undefined&&prior?.data!==null){
 value={...prior,observed_at:at,attempted_at:at,error:null,rate,http_status:304,next_attempt_at:iso(Date.now()+interval*1000)};
 }else if(response.ok){
 const body=await response.json();
 if(body?.private===true)throw new Error('Private Repository-Daten werden nicht öffentlich ausgegeben.');
 if(/\/jobs\?/.test(path)){
 if(!Array.isArray(body.jobs)||integer(body.total_count)===null)throw new Error('Ungültige GitHub-Schrittantwort.');
 }else if(path.startsWith('/actions/runs')&&(!Array.isArray(body.workflow_runs)||integer(body.total_count)===null))throw new Error('Ungültige GitHub-Laufantwort.');
 if(path.startsWith('/branches/')&&!/^[a-f0-9]{40}$/.test(body?.commit?.sha||''))throw new Error('Ungültige GitHub-Branchantwort.');
 if(path.startsWith('/events')&&!Array.isArray(body))throw new Error('Ungültige GitHub-Ereignisantwort.');
 value={data:body,observed_at:at,attempted_at:at,error:null,rate,etag:response.headers.get('etag'),http_status:response.status,next_attempt_at:iso(Date.now()+interval*1000)};
 }else{
 const retry=response.status===404?3600:response.status===429||rate.remaining===0?
 Math.max(60,retryAfter||0,reset?reset-Date.now()/1000+5:interval):interval;
 const message=response.status===404?'Nicht öffentlich auffindbar oder nicht zugänglich (HTTP 404).':
 response.status===429||rate.remaining===0?'GitHub-Rate-Limit erreicht.':'GitHub meldet HTTP '+response.status;
 value={data:prior?.data??null,observed_at:prior?.observed_at??null,attempted_at:at,error:{status:response.status,message},rate,
 http_status:response.status,etag:prior?.etag||null,next_attempt_at:iso(Date.now()+retry*1000)};
 }
 }catch(error){
 value={data:prior?.data??null,observed_at:prior?.observed_at??null,attempted_at:at,
 error:{status:null,message:String(error.message||error)},rate:prior?.rate||null,etag:prior?.etag||null,http_status:null,next_attempt_at:iso(Date.now()+interval*1000)};
 }
 try{await saveCache(key,value)}catch{memory.set(key,value)}
 return value;
 })();
 inflight.set(key,task);try{return await task}finally{inflight.delete(key)}
}
function evidence(s,path,repo,interval){return {endpoint:'https://api.github.com/repos/'+repo+path,interval_seconds:interval,
 observed_at:s.observed_at,attempted_at:s.attempted_at,next_attempt_at:s.next_attempt_at,error:s.error,http_status:s.http_status,rate:s.rate,
 stale:!!s.error||!s.observed_at||Date.now()-Date.parse(s.observed_at)>(interval+30)*1000}}
async function observe(repo,env,fast=240){
 // Unauthenticated available repo: 45 Actions + 4 events + 2 branch calls/hour per edge.
 // An unavailable branch is retried only once/hour; UI Refresh respects source cache.
 const slow=1800;
 const branchPath='/branches/'+repo.branch,branch=await githubSource(repo.name,branchPath,slow,env);
 const sources={branch:evidence(branch,branchPath,repo.name,slow)};
 if(!branch.data&&branch.error)return {...repo,availability:'unavailable',sources,head:null,tree:null,active_total:null,queued_total:null,runs:[],events:[],coverage:{}};
 const specs=[['recent','/actions/runs?per_page=100',fast],['active','/actions/runs?status=in_progress&per_page=100',fast],
 ['queued','/actions/runs?status=queued&per_page=100',fast],['events','/events?per_page=100',900]];
 const entries=await Promise.all(specs.map(async([name,path,seconds])=>{
 const s=await githubSource(repo.name,path,seconds,env);sources[name]=evidence(s,path,repo.name,seconds);return [name,s]}));
 const by=Object.fromEntries(entries),seen=new Map();
 for(const name of ['recent','active','queued'])for(const r of by[name].data?.workflow_runs||[]){
 const old=seen.get(r.id);if(!old||Date.parse(r.updated_at)>=Date.parse(old.updated_at))seen.set(r.id,r)}
 return {...repo,availability:Object.values(sources).every(s=>!s.error)?'available':'partial',sources,
 head:branch.data?.commit?.sha||null,tree:branch.data?.commit?.commit?.tree?.sha||null,
 active_total:sources.active.stale?null:integer(by.active.data?.total_count),queued_total:sources.queued.stale?null:integer(by.queued.data?.total_count),
 recent_ids:(by.recent.data?.workflow_runs||[]).map(r=>r.id),
 runs:[...seen.values()].map(r=>normalizeRun(r,repo.name)).sort((a,b)=>Date.parse(b.created_at)-Date.parse(a.created_at)),
 events:(Array.isArray(by.events.data)?by.events.data:[]).map(e=>normalizeEvent(e,repo.name)),
 coverage:{recent_limit:100,active_limit:100,queued_limit:100,active_truncated:(by.active.data?.total_count||0)>100,queued_truncated:(by.queued.data?.total_count||0)>100}};
}
export async function snapshot(env={}){
 const heads=await Promise.all(REPOS.map(r=>githubSource(r.name,'/branches/'+r.branch,1800,env)));
 const fast=heads.filter(s=>s.data).length>1?480:240;
 return {schema:'qikvrt-public-activity/v1',version:VERSION,generated_at:iso(),mode:'public_rest',refresh_interval_seconds:fast,diagnostics:DIAGNOSTICS,delivery:{periodic_polling:false,webhook_registered:false,push_verified:false,mode:'on_demand'},
 repositories:await Promise.all(REPOS.map(r=>observe(r,env,fast))),boundaries:{
 observer:'GitHub REST GET',scope:'Configured public repositories',workflow_success_is_effect_ack_done:false,
 actor_is_verified_human_or_model_identity:false,workflow_parent_inferred_from_time:false,events_api_latency_seconds:[30,21600]}};
}
export async function runDetails(repo,id,env={}){
 if(!REPOS.some(r=>r.name===repo)||!Number.isSafeInteger(id)||id<=0)throw new Error('Unzulässiger Lauf.');
 const path='/actions/runs/'+id+'/jobs?per_page=100';
 const source=await githubSource(repo,path,240,env);
 return {repo,run_id:id,source:evidence(source,path,repo,240),total_count:integer(source.data?.total_count),
 jobs:(source.data?.jobs||[]).map(j=>({id:j.id,name:j.name,status:j.status,conclusion:j.conclusion,
 url:ghurl(j.html_url),started_at:j.started_at,completed_at:j.completed_at,
 steps:(j.steps||[]).map(s=>({name:s.name,status:s.status,conclusion:s.conclusion,number:s.number}))}))};
}
const DIAGNOSTICS=[{"repository": "ingolf-lohmann/qik-vrt", "run_id": 37201459352, "job_id": 111433843449, "head": "93be182a277f29fcb1ffb5d4ace0483f6c29dc58", "tree": "25e36016536b45701abdc699c586394f53c69aa6", "observed_at": "2026-10-04T12:15:22Z", "kind": "verified_execution_failure", "expected": "Erfolgreicher Authority-Readback vor der Watchdog-Analyse", "actual": "Authority-Readback mit HTTP 404 abgebrochen; Ausführung beendet, Disposition HOLD", "cause": "Goldkelch/qik-vrt ist auf dem vom Watchdog verwendeten Authority-Lesepfad nicht zugänglich.", "uncertainty": "HTTP 404 unterscheidet fehlendes Repository und fehlende Zugriffsrechte nicht.", "stage": "AUTHORITY_READBACK", "http_status": 404, "disposition": "HOLD", "next_step": "Den bestehenden Authority-Lesepfad wiederherstellen und den exakten Arbeitsstand erneut beobachten.", "run_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/37201459352", "job_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/37201459352/job/111433843449", "artifact_url": "https://github.com/ingolf-lohmann/qik-vrt/actions/runs/37201459352/artifacts/11302996750", "artifact_sha256": "1365b2aaf9d4300056b6e5f10d74770cbca2e16c0dd3870372bea30603f56ce6", "receipt_fingerprint": "54f90255e3a31c7f27fd6e87e3644310b84508cbe21e5595b12599fedd8318af"}];
const SECURITY={'X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin',
 'Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self' https://chatgpt.com; base-uri 'none'; form-action 'none'",
 'Permissions-Policy':'camera=(), microphone=(), geolocation=()'};
export default{async fetch(request,env){
 const path=new URL(request.url).pathname;
 if(!['GET','HEAD'].includes(request.method))return new Response('Read-only observer',{status:405,headers:{...SECURITY,Allow:'GET, HEAD'}});
 if(path==='/api/activity')return new Response(request.method==='HEAD'?null:JSON.stringify(await snapshot(env)),{headers:{...SECURITY,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
 if(path==='/api/run'){
 const params=new URL(request.url).searchParams,repo=params.get('repo'),rawId=params.get('id');
 if(!REPOS.some(r=>r.name===repo)||!/^[1-9][0-9]{0,15}$/.test(rawId||'')||!Number.isSafeInteger(Number(rawId)))return new Response('Unzulässiger Lauf',{status:400,headers:SECURITY});
 return new Response(request.method==='HEAD'?null:JSON.stringify(await runDetails(repo,Number(rawId),env)),{headers:{...SECURITY,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
 }
 if(path==='/api/diagnostics')return new Response(request.method==='HEAD'?null:JSON.stringify(DIAGNOSTICS),{headers:{...SECURITY,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
 if(path==='/health')return Response.json({status:'ok',version:VERSION},{headers:{...SECURITY,'cache-control':'no-store'}});
 if(path==='/favicon.ico')return new Response(null,{status:204});
 if(path!=='/')return new Response('Not found',{status:404,headers:SECURITY});
 return new Response(request.method==='HEAD'?null:PAGE,{headers:{...SECURITY,'content-type':'text/html; charset=utf-8','cache-control':'no-cache'}});
}};


export {DIAGNOSTICS,SECURITY};
