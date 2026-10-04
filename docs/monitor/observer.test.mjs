import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
import worker,{normalizeRun,normalizeEvent,githubSource,snapshot,runDetails} from './observer.mjs';
const realFetch=globalThis.fetch,realNow=Date.now,realCaches=globalThis.caches;
const cacheStore=new Map();let cacheOpened=0;
globalThis.caches={get default(){throw new Error('This Worker is not permitted to access the default cache.')},
 async open(name){assert.equal(name,'qikvrt-activity-v2');cacheOpened++;return {
 async match(request){return cacheStore.get(request.url)?.clone()},
 async put(request,response){cacheStore.set(request.url,response.clone())}}}};
let now=Date.now();Date.now=()=>now;
let calls=0;
try{
 const raw={id:1,name:'Workflow <script>',display_title:'Activity',status:'completed',conclusion:'action_required',
 event:'workflow_run',actor:{login:'origin'},triggering_actor:{login:'rerunner'},run_attempt:2,
 head_sha:'a'.repeat(40),head_branch:'feature',path:'.github/workflows/test.yml',
 html_url:'https://github.com/test/repo/actions/runs/1',pull_requests:[{number:42}]};
 const run=normalizeRun(raw,'test/repo');
 assert.equal(run.state,'action_required');assert.equal(run.triggering_actor,'rerunner');
 assert.match(run.cause.detail,/nicht ausgewiesen/);assert.equal(run.cause.evidence,'github.run.event');
 assert.equal(run.prs[0].url,'https://github.com/test/repo/pull/42');
 assert.equal(normalizeRun({...raw,html_url:'javascript:alert(1)'},'test/repo').url,null);
 const event=normalizeEvent({id:'2',type:'IssueCommentEvent',actor:{login:'owner'},
 payload:{issue:{number:42},comment:{html_url:'https://github.com/test/repo/issues/42#comment'}},created_at:'2026-10-04T10:00:00Z'},'test/repo');
 assert.equal(event.category,'Kommentar');assert.match(event.url,/#comment/);
 globalThis.fetch=async()=>{calls++;return new Response(JSON.stringify({value:'exact-data',total_count:0,workflow_runs:[]}),{headers:{etag:'one','x-ratelimit-remaining':'58'}})};
 const first=await githubSource('test/cache','/actions/runs',240);
 const second=await githubSource('test/cache','/actions/runs',240);
 assert.equal(calls,1);assert.equal(first.observed_at,second.observed_at);
 now+=241000;
 globalThis.fetch=async()=>new Response(JSON.stringify({message:'rate limited'}),{status:403,
 headers:{'x-ratelimit-remaining':'0','x-ratelimit-reset':String(Math.floor(now/1000)+3600)}});
 const failed=await githubSource('test/cache','/actions/runs',240);
 assert.equal(failed.observed_at,first.observed_at);assert.deepEqual(failed.data,first.data);
 assert.equal(failed.error.status,403);assert.ok(Date.parse(failed.next_attempt_at)>now+3500000);
 now+=3606000;
 globalThis.fetch=async()=>new Response(null,{status:304});
 const revalidated=await githubSource('test/cache','/actions/runs',240);
 assert.equal(revalidated.error,null);assert.deepEqual(revalidated.data,first.data);
 assert.notEqual(revalidated.observed_at,first.observed_at);
 assert.equal((await worker.fetch(new Request('https://test/api/activity',{method:'POST'}),{})).status,405);
 // Missing Authority must not erase the independently successful personal repository.
 const sha='b'.repeat(40);
 globalThis.fetch=async url=>{
  if(url.includes('Goldkelch'))return new Response('{}',{status:404});
  if(url.includes('/branches/'))return Response.json({commit:{sha,commit:{tree:{sha:'c'.repeat(40)}}}});
  if(url.includes('/events'))return Response.json([]);
  const rawRun={...raw,id:3,event:'push',status:'completed',conclusion:'success',head_sha:sha,
   created_at:'2026-10-04T10:00:00Z',updated_at:'2026-10-04T10:01:00Z'};
  return Response.json({total_count:url.includes('status=')?0:1,workflow_runs:url.includes('status=')?[]:[rawRun]});
 };
 const state=await snapshot({});
 assert.equal(state.repositories[0].availability,'available');
 assert.equal(state.repositories[1].availability,'unavailable');
 assert.equal(state.repositories[1].active_total,null);
 assert.equal(state.repositories[0].runs[0].cause.label,'Push');
 assert.equal(state.boundaries.workflow_parent_inferred_from_time,false);
 assert.ok(cacheOpened>0);assert.ok(cacheStore.size>0);
 assert.equal(state.delivery.periodic_polling,false);
 assert.equal(state.delivery.push_verified,false);
 assert.equal((await worker.fetch(new Request('https://test/api/run?repo=foreign/repo&id=1'),{})).status,400);
 assert.equal((await worker.fetch(new Request('https://test/api/run?repo=ingolf-lohmann/qik-vrt&id=-1'),{})).status,400);
 // Actual failure steps remain separate from a verified root-cause diagnosis.
 globalThis.fetch=async()=>Response.json({total_count:1,jobs:[{id:11,name:'Job <script>',status:'completed',conclusion:'failure',
 html_url:'javascript:alert(1)',private_token:'must-not-be-exported',
 steps:[{number:4,name:'Read <Authority>',status:'completed',conclusion:'failure'}]}]});
 const steps=await runDetails('ingolf-lohmann/qik-vrt',900001);
 assert.equal(steps.jobs[0].url,null);assert.equal(steps.jobs[0].steps[0].conclusion,'failure');
 assert.equal(steps.jobs[0].private_token,undefined);
 // Execute the actual page script against a small DOM adapter, including failure paths.
 const root=await worker.fetch(new Request('https://test/'),{});
 const html=await root.text(),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
 const elements=new Map(),buttons=[],relativeNodes=[],clockTimers=[],visibilityListeners=[];let networkTimers=0,clientReads=0;
 function element(id){if(!elements.has(id))elements.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,disabled:false,
 addEventListener(){},setAttribute(){},scrollIntoView(){},classList:{contains(){return false}}});return elements.get(id)}
 for(const s of ['all','live','waiting','attention','success'])buttons.push({...element(s),dataset:{filter:s}});
 const context={document:{getElementById:element,querySelectorAll(selector){return selector==='[data-relative-at]'?relativeNodes:selector==='details'||selector==='details[open]'?[]:buttons},addEventListener(name,callback){if(name==='visibilitychange')visibilityListeners.push(callback)},hidden:false},
 location:{origin:'https://test'},URL,Intl,Date,AbortSignal,Set,
 setTimeout(){networkTimers++;return 1},clearTimeout(){},setInterval(callback,delay){clockTimers.push({callback,delay})},matchMedia(){return{matches:true}},
 fetch:async()=>{clientReads++;throw new Error('Deliberate API outage')}};
 context.QikvrtReplica={create(){return {id:'test-instance',sequence:0,node_sequence:0,transport:'disconnected',status(){return {label:'test',detail:'test'}}}}};context.EventSource=class {addEventListener(){} close(){}};vm.createContext(context);vm.runInContext(script,context);
 await new Promise(resolve=>setImmediate(resolve));
 assert.match(element('global-error').innerHTML,/keine Aktivitäten/);
 assert.equal(element('count-running').textContent,'—');
 assert.equal(networkTimers,0);
 context.data=state;context.observationFailed=false;vm.runInContext('render()',context);
 assert.equal(String(element('count-success').textContent),'1');
 assert.match(element('runs').innerHTML,/Workflow &lt;script&gt;/);
 assert.doesNotMatch(element('runs').innerHTML,/<script>/);
 assert.match(element('runs').innerHTML,/Push/);
 assert.equal(String(element('count-running').textContent),'0');
 assert.match(element('expectation-status').innerHTML,/HTTP 404/);
 assert.match(element('expectation-status').innerHTML,/AUTHORITY_READBACK/);
 assert.match(element('expectation-status').innerHTML,/GitHub-Webhooks noch nicht angeschlossen/);
 assert.match(element('expectation-status').innerHTML,/37201459352/);
 // Time advances without another source read or replacing an opened detail subtree.
 assert.equal(clockTimers.length,1);assert.equal(clockTimers[0].delay,1000);
 const detailBefore=element('runs').innerHTML,expectationBefore=element('expectation-status').innerHTML;
 const initialReads=clientReads,snapshotBefore=JSON.stringify(context.data),clockStart=now;
 const relative={dataset:{relativeAt:new Date(now-3000).toISOString(),relativePrefix:'vor ',relativeSuffix:''},textContent:''};
 relativeNodes.push(relative);clockTimers[0].callback();assert.equal(relative.textContent,'vor 3 s');
 now+=1000;clockTimers[0].callback();assert.equal(relative.textContent,'vor 4 s');
 assert.equal(clientReads,initialReads);assert.equal(JSON.stringify(context.data),snapshotBefore);
 assert.equal(element('runs').innerHTML,detailBefore);assert.equal(element('expectation-status').innerHTML,expectationBefore);
 now+=270000;clockTimers[0].callback();
 assert.equal(element('count-running').textContent,'—');assert.match(element('connection').innerHTML,/Veraltete/);
 assert.equal(element('runs').innerHTML,detailBefore);assert.equal(clientReads,initialReads);
 now=clockStart;visibilityListeners[0]();assert.equal(relative.textContent,'vor 3 s');
 assert.equal(clientReads,initialReads);assert.equal(String(element('count-running').textContent),'0');
 context.observationFailed=true;clockTimers[0].callback();
 assert.equal(element('count-running').textContent,'—');assert.match(element('connection').innerHTML,/Verbindung unterbrochen/);
 context.observationFailed=false;
 context.steps=steps;
 const renderedSteps=vm.runInContext('jobsHTML(steps)',context);
 assert.match(renderedSteps,/Read &lt;Authority&gt;/);assert.doesNotMatch(renderedSteps,/<script>/);
 const oldQueue=normalizeRun({...raw,id:9,event:'pull_request',status:'queued',conclusion:null,
  created_at:new Date(now-86400000*10).toISOString(),updated_at:new Date(now-86400000*9).toISOString()},'ingolf-lohmann/qik-vrt');
 context.data=JSON.parse(JSON.stringify(state));context.data.repositories[0].runs.push(oldQueue);
 vm.runInContext('render()',context);
 assert.match(element('note-waiting').textContent,/1 Queue-Läufe > 1 h/);
 assert.match(element('runs').innerHTML,/9 Tage.*ohne Änderung/);
 assert.match(element('runs').innerHTML,/data-relative-at=/);
 // A retained latest-list running row cannot override the independent active-total readback.
 context.data.repositories[0].runs[0].state='in_progress';vm.runInContext('render()',context);
 assert.equal(String(element('count-running').textContent),'0');
 context.data=state;
 vm.runInContext("choose('attention')",context);assert.equal(element('runs-empty').hidden,false);
 vm.runInContext("choose('all'); document.getElementById('search').value='no-such-workflow'; renderRuns()",context);
 assert.equal(element('runs-empty').hidden,false);
 assert.doesNotMatch(html,/import\('\/observer.js'\)/);
 assert.match(html,/new EventSource/);
 assert.equal(networkTimers,0);
 const proof=await (await worker.fetch(new Request('https://test/api/diagnostics'),{})).json();
 assert.equal(proof[0].run_id,37201459352);assert.equal(proof[0].http_status,404);
 assert.ok(html.includes('id="client-instance"'));
 assert.ok(html.includes('<details class="panel" id="workflows">'));
 console.log('PASS: ticking ages and stale-status expiry preserve details without source reads; exact causal evidence, source-bound counters, queues, no polling, safe job steps, attribution, rate/cache recovery, read-only routes.');
}finally{globalThis.fetch=realFetch;Date.now=realNow;globalThis.caches=realCaches}
