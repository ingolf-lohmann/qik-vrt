// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Test contribution: OpenAI Codex.
// Actual React elements and client-replica acceptance; controlled hooks/I/O.
// This is a source replay, not a ReactDOM/browser, storage or human study.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import vm from 'node:vm';
import {readFileSync, writeFileSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';

const here=new URL('.',import.meta.url), evidence=new URL('../../evidence/monitor-feedback/react/',here);
const read=url=>readFileSync(url,'utf8'), sha=value=>createHash('sha256').update(value).digest('hex');
const observationBytes=read(new URL('authority-404-observation.json',evidence));
const observation=JSON.parse(observationBytes), runtimeSource=read(new URL('react-runtime.js',here));
const baselineSource=read(new URL('baseline-mesh-react.js',evidence)), candidateSource=read(new URL('mesh-react.js',here));
const replicaSource=read(new URL('client-replica.js',here));
const version='2026-10-04.9', at=observation.observed_at;

test('static React prerequisite closure matches its locked production sources and MIT license',()=>{
  const lock=JSON.parse(read(new URL('REACT_LOCK.json',here))), bytes=Buffer.from(runtimeSource);
  assert.equal(bytes.length,lock.bundle.bytes);assert.equal(sha(bytes),lock.bundle.sha256);
  assert.equal(sha(read(new URL('REACT_LICENSE.txt',here))),lock.license.sha256);
  for(const source of lock.sources){
    const marker=Buffer.from('factories['+JSON.stringify(source.module)+']=function(module,exports,require){\n');
    const start=bytes.indexOf(marker);assert.ok(start>=0,source.module);
    assert.equal(sha(bytes.subarray(start+marker.length,start+marker.length+source.bytes)),source.sha256,source.module);
  }
});

test('static monitor dependency closure has no storage or onboarding requirement',()=>{
  const shell=read(new URL('index-react.html',here));
  for(const match of shell.matchAll(/(?:<script[^>]*src|<link[^>]*href)="([^"]+)"/g)){
    if(match[1].startsWith('#'))continue;
    assert.doesNotThrow(()=>read(new URL(match[1],here)),match[1]);
  }
  assert.doesNotMatch(candidateSource+shell,/QikvrtMeshFileView|mesh-file-|sqlite|PersonalEntry|componentEvidence/i);
});

function sourceFailure(status=observation.status, extra={}) {
  return {endpoint:observation.url,observed_at:null,attempted_at:at,stale:true,http_status:status,
    rate:{remaining:Number(observation.headers['x-ratelimit-remaining'])},
    error:{status,message:status===404?'404 Not Found; remaining=56':'HTTP '+status,
      diagnostic:{source_url:observation.url,method:observation.method,observed_at:at,phase:'HTTP',status,
        status_text:observation.status_text,original_error:status===404?'404 Not Found; remaining=56':'HTTP '+status,
        provider_request_id:observation.headers['x-github-request-id'],
        rate_limit_remaining:observation.headers['x-ratelimit-remaining'],rate_limit_reset:observation.headers['x-ratelimit-reset'],
        retry_after:observation.headers['retry-after'],response_body:observation.response_body,response_sha256:observation.response_sha256,...extra}}};
}
function snapshot(source=sourceFailure(), sequence=1) {
  const value={schema:'qikvrt-public-activity/v1',version,generated_at:at,repositories:[
    {name:'Goldkelch/qik-vrt',availability:source.error?'unavailable':'available',sources:{branch:source},runs:[]},
    {name:'ingolf-lohmann/qik-vrt',availability:'available',sources:{branch:{endpoint:'https://api.github.com/repos/ingolf-lohmann/qik-vrt',
      observed_at:at,attempted_at:at,stale:false,error:null}},recent:{runs:[{id:1,repository:'ingolf-lohmann/qik-vrt',
        name:'SYNTHETIC_SIBLING',state:'success',head_sha:'1'.repeat(40),updated_at:at}]}}]};
  value.replication={epoch:'CONTROLLED_REACT_FIXTURE',sequence,node_id:'SYNTHETIC_NODE',source_head:'2'.repeat(40),digest:sha(JSON.stringify(value))};
  return value;
}

async function replay(source, options={}) {
  const requests=[],states=new Map(),effects=[],streams=[],timers=[],storage=new Map(),pendingTasks=new Set();
  let component=null,slot=0,root=null,tree=null,dirty=true;
  const context=vm.createContext({console,performance,URL,TextEncoder,Uint8Array,AbortSignal,crypto:webcrypto,
    setTimeout,clearTimeout, Date:class extends Date {
      constructor(...values){super(...(values.length?values:[at]));} static now(){return Date.parse(at);}
    }});
  // Use the existing, lock-bound React.createElement, not a hand-built element stub.
  vm.runInContext(runtimeSource,context,{filename:'react-runtime.js'});
  assert.equal(context.QikvrtReact.React.version,'19.2.6');
  function hook(initial) {
    const key=component+':'+slot++;
    if(!states.has(key))states.set(key,typeof initial==='function'?initial():initial);
    return [states.get(key),value=>{states.set(key,typeof value==='function'?value(states.get(key)):value);dirty=true;}];
  }
  const React={...context.QikvrtReact.React,useState:hook,useRef:initial=>hook(()=>({current:initial}))[0],
    useEffect:effect=>{const key=component+':'+slot++;if(!states.has(key)){states.set(key,true);effects.push(effect);}}};
  function resolve(element,path='root') {
    if(Array.isArray(element))return element.map((child,i)=>resolve(child,path+':'+i));
    if(element==null||typeof element!=='object')return element;
    if(typeof element.type==='function') {
      const prior=component,priorSlot=slot;component=path+':'+element.type.name;slot=0;
      const child=element.type(element.props);component=prior;slot=priorSlot;return resolve(child,path+':component');
    }
    return {...element,props:{...element.props,children:resolve(element.props.children,path+':children')}};
  }
  class EventSource {
    static CLOSED=2;
    constructor(url){this.url=url;this.listeners={};this.readyState=1;streams.push(this);}
    addEventListener(name,listener){this.listeners[name]=listener;}close(){this.readyState=2;}
  }
  const responses={
    '/api/activity':()=>options.activity??snapshot(options.source??sourceFailure()),
    '/api/runtime':()=>({node_id:'SYNTHETIC_RUNTIME',source_repository:'ingolf-lohmann/qik-vrt'}),
    '/api/terminal':()=>({state:'UNKNOWN'})};
  Object.assign(context,{
    QikvrtReact:{React,ReactDOM:{createRoot:()=>({render:element=>{root=element;}})}},
    QikvrtMeshFileView:()=>null,EventSource,
    document:{documentElement:{dataset:{qikvrtMonitorVersion:version,qikvrtOffline:options.offline?'true':'false'}},
      hidden:false,getElementById:()=>({}),addEventListener(){},removeEventListener(){}},
    window:{addEventListener(){},removeEventListener(){}},location:{pathname:new URL('http://localhost'+(options.path??'/mesh')).pathname,href:'http://localhost'+(options.path??'/mesh')},
    sessionStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value)},
    setInterval:(callback,ms)=>{timers.push({callback,ms});return timers.length;},clearInterval(){},
    fetch:async(path,init)=>{
      requests.push({path,method:init.method??'GET',credentials:init.credentials??null});
      const failure=options.failures?.[path];
      if(failure?.network)throw TypeError(failure.network);
      const status=failure?.status??200;
      return {ok:status>=200&&status<300,status,statusText:failure?.statusText??'OK',
        headers:{get:name=>failure?.headers?.[name]??null},json:async()=>{
          if(failure?.json)throw SyntaxError(failure.json);return responses[path]();
        }};
    }});
  vm.runInContext(replicaSource,context,{filename:'client-replica.js'});
  const create=context.QikvrtReplica.create;
  context.QikvrtReplica.create=options=>{
    const replica=create(options),accept=replica.accept.bind(replica);
    replica.accept=value=>{const task=accept(value);pendingTasks.add(task);task.finally(()=>pendingTasks.delete(task));return task;};
    return replica;
  };
  vm.runInContext(source,context,{filename:'mesh-react.js'});
  async function settle() {
    for(let i=0;i<24;i++) {
      if(dirty){dirty=false;tree=resolve(root);while(effects.length)effects.shift()();}
      await new Promise(resolve=>setImmediate(resolve));
      await Promise.all([...pendingTasks]);
    }
    if(dirty){dirty=false;tree=resolve(root);}
    assert.equal(dirty,false,'controlled render settled');return tree;
  }
  await settle();
  return {get tree(){return tree;},requests,streams,timers,settle,
    refresh:async()=>{const button=nodes(tree).find(node=>node.type==='button'&&text(node)==='Readback erneuern');await button.props.onClick();await settle();},
    snapshot:async value=>{streams[0].listeners.snapshot({data:JSON.stringify(value)});await settle();}};
}
function nodes(value) {
  if(Array.isArray(value))return value.flatMap(nodes);
  if(!value||typeof value!=='object')return [];
  return [value,...nodes(value.props?.children)];
}
function text(value) {
  if(Array.isArray(value))return value.map(text).join('');
  return value&&typeof value==='object'?text(value.props?.children):value==null?'':String(value);
}
function explanations(tree) {
  const result={};
  for(const dl of nodes(tree).filter(node=>node.type==='dl')) {
    const children=nodes(dl.props.children).filter(node=>['dt','dd'].includes(node.type));
    for(let i=0;i<children.length;i+=2)result[text(children[i])]=text(children[i+1]);
  }
  return result;
}
function coverage(values) {
  return [!!values.Zustand,!!values.Auswirkung,!!values['Belegter Status / Unsicherheit'],
    !!(values['Zuständiger Akteur']&&values['Nächster REST-Schritt']),!!values.Reparaturfortschritt].filter(Boolean).length;
}
const diagnoses=tree=>nodes(tree).filter(node=>node.type==='pre'&&node.props['aria-label']==='Kopierbare Fehlerdiagnose').map(node=>JSON.parse(text(node)));

export async function comparison() {
  const before=await replay(baselineSource),after=await replay(candidateSource);
  return {schema:'qikvrt-react-monitor-feedback-comparison/v1',case_id:'AUTHORITY_REPOSITORY_HTTP_404',
    method:'Captured provider status/text/headers projected into a controlled repository source; actual React 19.2.6 elements and client-replica digest acceptance in Node vm, controlled hooks and I/O. Synthetic sibling and runtime held equal. No ReactDOM/browser or storage execution.',
    baseline:{commit:'b9e03ef678f1304c6cada3cfc37b311b7faea5b9',tree:'29f40e2318869f107d4688d3b5401a2e5c1b0633',
      source_blob:'d0a3232ec1353a4a00e8a4ae958470985120637e',source_sha256:sha(baselineSource)},
    candidate_source_sha256:sha(candidateSource),observation_sha256:sha(observationBytes),
    explanation_groups:['Zustand','Auswirkung','Belegter Status / Unsicherheit','Zuständiger Akteur + nächster REST-Schritt','Reparaturfortschritt'],
    before:{explicit_required_explanation_fields:coverage(explanations(before.tree)),authority_feedback:text(nodes(before.tree).find(node=>node.type==='article'&&text(node).includes('Goldkelch/qik-vrt')))},
    after:{explicit_required_explanation_fields:coverage(explanations(after.tree)),explanations:explanations(after.tree),diagnostics:diagnoses(after.tree)},
    automated_measurements:{requests_before:before.requests,requests_after:after.requests,streams_before:before.streams.length,streams_after:after.streams.length,
      original_error_retained:diagnoses(after.tree)[0].original_error==='404 Not Found; remaining=56',
      successful_sibling_visible_before:text(before.tree).includes('SYNTHETIC_SIBLING'),successful_sibling_visible_after:text(after.tree).includes('SYNTHETIC_SIBLING')},
    human_comprehension:{state:'NOT_MEASURED',participants:0,understanding_rate_before:null,understanding_rate_after:null,
      clarification_requests:null,time_to_identify_next_action_ms:null,comprehension_improvement_measured:false},
    boundaries:{controlled_replay_is_live_deployment:false,automated_field_presence_is_human_comprehension:false,
      provider_404_cause_established:false,runtime_fault_repaired:false,storage_stack_test_evidence_transferred:false,
      predecessor_evidence_transfer:false,main_integrated:false,public_delivered:false,EFFECT_ACK_DONE:false}};
}

test('same captured Authority 404: actual React sources change 0/5 to 5/5, equal requests and raw binding',async()=>{
  const report=await comparison();assert.equal(report.before.explicit_required_explanation_fields,0);
  assert.equal(report.after.explicit_required_explanation_fields,5);
  assert.deepEqual(report.automated_measurements.requests_before,report.automated_measurements.requests_after);
  assert.equal(report.automated_measurements.requests_after.length,3);
  assert.equal(report.automated_measurements.streams_after,1);
  const d=report.after.diagnostics[0];assert.equal(d.source_url,observation.url);assert.equal(d.status,404);
  assert.equal(d.original_error,'404 Not Found; remaining=56');assert.equal(d.provider_request_id,observation.headers['x-github-request-id']);
  assert.equal(d.observed_at,at);assert.equal(d.response_body,observation.response_body);assert.equal(d.response_sha256,observation.response_sha256);
  assert.equal(sha(d.response_body),observation.response_sha256);assert.equal(d.cause_established,false);
  assert.equal(report.automated_measurements.successful_sibling_visible_after,true);
  assert.equal(report.human_comprehension.state,'NOT_MEASURED');assert.equal(report.human_comprehension.participants,0);
});
test('comparison and exact capture cannot silently drift',async()=>{
  const report=await comparison();if (!process.argv.includes('--feedback-report')) assert.deepEqual(JSON.parse(read(new URL('authority-404-before-after.json',evidence))),report);
  assert.equal(sha(observationBytes),'7fe62ee41e0fa286ce515dca1bd0decb48fe2f8315c0d8f3c30c03285f488eec');
  assert.equal(createHash('sha1').update('blob '+Buffer.byteLength(baselineSource)+'\0').update(baselineSource).digest('hex'),'d0a3232ec1353a4a00e8a4ae958470985120637e');
});
test('node and mesh reuse the same 404 language with copyable, focusable native details',async()=>{
  const node=await replay(candidateSource,{path:'/node?repository=Goldkelch/qik-vrt'});
  assert.equal(coverage(explanations(node.tree)),5);
  const pre=nodes(node.tree).find(n=>n.type==='pre');assert.equal(pre.props.tabIndex,0);
  assert.ok(nodes(node.tree).some(n=>n.type==='details'));assert.equal(diagnoses(node.tree)[0].status,404);
  assert.equal(node.requests.length,3);
});
test('404 cause, responsible actor, endpoint and lack of a repair start are explicit',async()=>{
  const result=await replay(candidateSource),e=explanations(result.tree);
  assert.match(e['Belegter Status / Unsicherheit'],/fehlt.*nicht sichtbar.*nicht geklärt/);
  assert.equal(e['Zuständiger Akteur'],'Repository-Verantwortliche');assert.ok(e['Nächster REST-Schritt'].includes(observation.url));
  assert.match(e.Reparaturfortschritt,/Reparaturstart.*nicht belegt/);assert.match(e.Auswirkung,/kein Betriebszustand/);
});
test('observer-native error without extended capture retains exact message and unknown request ID',async()=>{
  const source={endpoint:observation.url,http_status:404,attempted_at:at,observed_at:null,stale:true,
    rate:{remaining:56,reset_at:'2026-10-06T18:00:00Z'},error:{status:404,message:'Nicht öffentlich auffindbar oder nicht zugänglich (HTTP 404).'}};
  const result=await replay(candidateSource,{source}),d=diagnoses(result.tree)[0];
  assert.equal(d.original_error,source.error.message);assert.equal(d.provider_request_id,null);assert.equal(d.observed_at,at);
  assert.equal(d.rate_limit_remaining,56);assert.equal(d.rate_limit_reset,source.rate.reset_at);
});
test('activity HTTP failure does not hide successful runtime and terminal siblings',async()=>{
  const result=await replay(candidateSource,{failures:{'/api/activity':{status:404,statusText:'Not Found',headers:observation.headers}}});
  assert.equal(coverage(explanations(result.tree)),5);assert.ok(text(result.tree).includes('SYNTHETIC_RUNTIME'));
  assert.equal(diagnoses(result.tree)[0].original_error,'/api/activity: HTTP 404');
  const alert=nodes(result.tree).find(node=>node.props.role==='alert');assert.ok(alert,'existing browser alert contract retained');
  assert.match(text(alert),/Readback offen/);
});
test('all rejected REST responses remain separate, not a flattened error chain',async()=>{
  const result=await replay(candidateSource,{failures:{'/api/activity':{status:404},'/api/runtime':{status:502},'/api/terminal':{status:401}}});
  assert.deepEqual(diagnoses(result.tree).map(d=>d.status),[404,502,401]);assert.equal(result.requests.length,3);
});
test('rate-limited 403 differs from other 403, with no invented cause or retry',async()=>{
  const rate=await replay(candidateSource,{source:sourceFailure(403,{rate_limit_remaining:'0',retry_after:'60'})});
  assert.match(explanations(rate.tree).Zustand,/begrenzt/);assert.match(explanations(rate.tree)['Nächster REST-Schritt'],/Retry-After/);
  const denied=await replay(candidateSource,{source:sourceFailure(403,{rate_limit_remaining:'56'})});
  assert.match(explanations(denied.tree).Zustand,/abgewiesen/);assert.match(explanations(denied.tree)['Belegter Status / Unsicherheit'],/nicht geklärt/);
  assert.equal(rate.requests.length,3);assert.equal(rate.timers.filter(t=>t.ms!==1000).length,0);
});
test('network and JSON failures distinguish absent HTTP from a received response',async()=>{
  const source={endpoint:observation.url,error:null,observed_at:at,stale:false};
  const network=await replay(candidateSource,{source,failures:{'/api/runtime':{network:'Failed to fetch'}}});
  assert.equal(diagnoses(network.tree)[0].status,null);assert.match(explanations(network.tree).Zustand,/keine HTTP-Antwort/);
  const json=await replay(candidateSource,{source,failures:{'/api/runtime':{json:'Unexpected token',status:200}}});
  assert.equal(diagnoses(json.tree)[0].phase,'JSON');assert.equal(diagnoses(json.tree)[0].status,200);
  assert.match(explanations(json.tree)['Belegter Status / Unsicherheit'],/JSON.*ungeklärt/);
});
test('last good repository data is stale during error, recovery does not claim runtime repair',async()=>{
  const previous={...sourceFailure(),observed_at:'2026-10-06T16:00:00Z'};
  const result=await replay(candidateSource,{source:previous});assert.match(explanations(result.tree).Auswirkung,/veraltet/);
  await result.snapshot(snapshot({endpoint:observation.url,error:null,observed_at:at,stale:false},2));
  assert.equal(diagnoses(result.tree).length,0);assert.match(text(result.tree),/Repository-Lesepfad beobachtet/);
  assert.doesNotMatch(text(result.tree),/Runtime-Reparatur.*bestätigt/);
});
test('snapshot success does not erase a failed runtime REST readback; manual retry clears it',async()=>{
  const failures={'/api/runtime':{status:502}},result=await replay(candidateSource,{failures});
  await result.snapshot(snapshot(sourceFailure(),2));assert.ok(diagnoses(result.tree).some(d=>d.source_url==='/api/runtime'));
  delete failures['/api/runtime'];await result.refresh();assert.equal(diagnoses(result.tree).some(d=>d.source_url==='/api/runtime'),false);
});
test('malformed stream data preserves other failures and reports unbound evaluation status',async()=>{
  const result=await replay(candidateSource,{failures:{'/api/runtime':{status:502}}});
  result.streams[0].listeners.snapshot({data:'not json'});await result.settle();
  const stream=diagnoses(result.tree).find(d=>d.source_url==='/api/stream');assert.equal(stream.phase,'EVALUATION');assert.equal(stream.status,null);
  assert.ok(diagnoses(result.tree).some(d=>d.source_url==='/api/runtime'));
});
test('credential redaction and React text boundaries preserve safe raw diagnostic text',async()=>{
  const source=sourceFailure(404,{original_error:'<script>alert(1)</script> Bearer hidden ghp_secret token?access_token=private'});
  const result=await replay(candidateSource,{source}),raw=text(result.tree);assert.doesNotMatch(raw,/Bearer hidden|ghp_secret|access_token=private/);
  assert.match(raw,/\[REDACTED\]/);assert.ok(nodes(result.tree).every(n=>!n.props.dangerouslySetInnerHTML));
  assert.ok(diagnoses(result.tree)[0].original_error.includes('<script>alert(1)</script>'));
});
test('workflow machine status and static monitor fallback remain visible; offline causes no fetch',async()=>{
  const result=await replay(candidateSource);assert.ok(nodes(result.tree).some(n=>n.type==='td'&&text(n)==='success'));
  const root=await replay(candidateSource,{path:'/'});assert.match(text(root.tree),/Das Mesh im aktuellen Nachweisstand/);assert.doesNotMatch(text(root.tree),/SQLite|Einrichtungsvorschau/);
  const offline=await replay(candidateSource,{path:'/',offline:true});assert.equal(offline.requests.length,0);assert.equal(offline.streams.length,0);
});

export {snapshot, sourceFailure};

const reportIndex=process.argv.indexOf('--feedback-report');
if(reportIndex>=0)writeFileSync(process.argv[reportIndex+1],JSON.stringify(await comparison(),null,2)+'\n');
