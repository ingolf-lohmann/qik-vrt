// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex.
// Standalone configuration of the existing monitor, not another controller.
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {resolve, join} from 'node:path';
import {createMonitor, providerFetch, VERSION} from './server.mjs';

const root = process.env.QIKVRT_NODE_PACKAGE;
const configBytes = readFileSync(process.env.QIKVRT_NODE_CONFIG);
const config = JSON.parse(configBytes);
const hash = value => createHash('sha256').update(value).digest('hex');
const rawManifest = readFileSync(join(root, 'MANIFEST.json'));
const manifest = JSON.parse(rawManifest);
const pin = process.env.QIKVRT_NODE_MANIFEST_SHA256;
if (hash(rawManifest) !== pin || hash(configBytes) !== process.env.QIKVRT_NODE_CONFIG_SHA256 ||
    manifest.runtime.node.version !== process.version ||
    manifest.runtime.node.executable_sha256 !== hash(readFileSync(process.execPath)) ||
    manifest.source_head !== config.source_head || manifest.source_tree !== config.source_tree) throw Error('EXACT_RUNTIME_BINDING_MISMATCH');
for (const [name, entry] of Object.entries(manifest.files)) {
  if (hash(readFileSync(join(root, name))) !== entry.sha256) throw Error('RUNTIME_ARTIFACT_DRIFT');
}
const realFetch = globalThis.fetch;
// The standalone source is local. Railway is never a source for this profile.
// A denied request throws before transport; the regression counts attempts.
globalThis.fetch = providerFetch(config.adapter, realFetch);
const files = new Map([
  ['/assets/css/qikvrt-mesh-react.css', ['docs/monitor/mesh-react.css', 'text/css']],
  ['/assets/js/qikvrt-mesh-react.js', ['docs/monitor/mesh-react.js', 'text/javascript']],
  ['/assets/js/qikvrt-mesh-file-codec.js', ['docs/monitor/mesh-file-codec.js', 'text/javascript']],
  ['/assets/js/qikvrt-mesh-file-client.js', ['docs/monitor/mesh-file-client.js', 'text/javascript']],
  ['/assets/js/qikvrt-mesh-file-view.js', ['docs/monitor/mesh-file-view.js', 'text/javascript']],
  ['/assets/js/qikvrt-react-runtime.js', ['docs/monitor/react-runtime.js', 'text/javascript']],
  ['/scheibenhard-original.html', ['docs/monitor/scheibenhard-original.html', 'text/html']],
  ['/assets/css/qikvrt.css', ['docs/assets/css/qikvrt.css', 'text/css']],
  ['/assets/css/qikvrt-terminal.css', ['docs/assets/css/qikvrt-terminal.css', 'text/css']],
  ['/assets/js/qikvrt-repository-terminal.js', ['docs/assets/js/qikvrt-repository-terminal.js', 'text/javascript']],
  ['/assets/js/qikvrt-local-engine.js', ['docs/assets/js/qikvrt-local-engine.js', 'text/javascript']],
  ['/publications/index.json', ['docs/publications/index.json', 'application/json']],
]);
const documents = new Set(['AI','STATUS.md','README.md','docs/ARCHITECTURE.md','docs/BOUNDARIES.md',
  'docs/PRIVACY_PRESERVING_INTERACTION_ARCHIVE.md','.well-known/qik-vrt-self-disclosure.json']);
function reply(response, code, body, type = 'application/json', method = 'GET') {
  response.writeHead(code, {'content-type': type + '; charset=utf-8', 'cache-control': 'no-store',
    'x-content-type-options': 'nosniff', 'content-security-policy': "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"});
  response.end(method === 'HEAD' ? undefined : type === 'application/json' && !Buffer.isBuffer(body) ? JSON.stringify(body) : body);
}
const binding = () => ({schema: 'qikvrt-self-host-runtime/v1', package_version: manifest.package_version,
  source_repository: manifest.source_repository, source_head: manifest.source_head, source_tree: manifest.source_tree,
  manifest_sha256: pin, config_sha256: hash(configBytes), node_id: config.node_id, adapter: config.adapter,
  runtime: manifest.runtime, artifact_files_sha256: Object.fromEntries(Object.entries(manifest.files).map(([p,e]) => [p,e.sha256])),
  monitor_version: VERSION, volume_binding_sha256: hash(readFileSync(join(config.state_dir, 'binding.json'))),
  storage_scope: 'CONFIGURED_LOCAL_FILESYSTEM; HOST_PERSISTENCE_NOT_ATTESTED',
  terminal_scope: manifest.terminal_scope, terminal_profile:config.terminal_profile || 'reference',
  native_terminal_daemon_available:manifest.native_terminal_daemon_included === true && ['temdd','firefox'].includes(config.terminal_profile),
  browser_startup_verified:config.terminal_profile === 'firefox',
  local_url:'http://127.0.0.1:'+config.port+'/client',
  terminal_opening:config.terminal_profile === 'firefox' ? 'EXPLICIT_FIREFOX_PROFILE' : 'ON_DEMAND_URL',
  deployment_object:process.env.QIKVRT_MONOLITH_MODE === 'SQLITE_CARRIER_V1' ? 'NATIVE_SQLITE_CARRIER_AND_LEDGER' : 'SEALED_DIRECTORY',
  mobile_runtime_verified:false,
  public_routing_verified: false, effect_ack_done: false});
async function routes(request, response, url) {
  if (url.pathname === '/api/webhooks/github' && config.adapter === 'none') {
    reply(response, 409, {error:'GITHUB_ADAPTER_NOT_SELECTED', effect_ack_done:false}); return true;
  }
  const owned = ['/','/index.html','/api/runtime','/api/terminal','/api/repository','/AI/','/terminal/','/mesh','/node','/client'].includes(url.pathname) || files.has(url.pathname) ||
    (config.adapter === 'none' && url.pathname === '/api/run');
  if (!owned) return false;
  if (!['GET','HEAD'].includes(request.method)) { reply(response,405,{error:'READ_ONLY_ROUTE'}); return true; }
  if (['/','/index.html','/mesh','/node','/client'].includes(url.pathname)) reply(response,200,readFileSync(join(root,'docs/monitor/index-react.html'),'utf8').replace('MONITOR_VERSION',VERSION),'text/html',request.method);
  else if (url.pathname === '/api/runtime') reply(response,200,binding(),'application/json',request.method);
  else if (url.pathname === '/api/terminal') {
    const token = readFileSync(config.terminal_token_file,'utf8').trim();
    const native = ['temdd','firefox'].includes(config.terminal_profile);
    const observed = await fetch('http://127.0.0.1:'+config.terminal_port+(native?'/api/temdd/subject':'/terminal/state'),
      {headers:{Authorization:'Bearer '+token},signal:AbortSignal.timeout(3000)});
    if (!observed.ok) throw Error('LOCAL_TERMINAL_READBACK_FAILED');
    const state = await observed.json();
    if (native) {
      if (state.subject?.repository !== manifest.source_repository || state.subject?.head !== manifest.source_head ||
          state.subject?.tree !== manifest.source_tree || state.subject?.pr !== config.subject_pr ||
          !/^[a-f0-9]{32}$/.test(state.ledger_id || '') || state.dod !== false || state.evidence_transfer !== 'DENY') {
        throw Error('LOCAL_NATIVE_TERMINAL_BINDING_MISMATCH');
      }
      reply(response,200,{schema:'qikvrt-self-host-terminal/v1',state:'NATIVE_TEMDD_READY',
        node_id:config.node_id,manifest_sha256:pin,config_sha256:hash(configBytes),subject:state.subject,
        ledger_id:state.ledger_id,native_source:'RECOVERED_HISTORICAL_ORIGINAL',public_effects:'READ_ONLY',
        durable_input:config.owner_rest_grants?.length ? 'AUTHENTICATED_OWNER_REST_PREPARE_COMMIT' : 'EXISTING_OWNER_UNIX_INGRESS',
        owner_rest_input_enabled:!!config.owner_rest_grants?.length,
        owner_rest_base_url:config.owner_rest_grants?.length ? 'http://127.0.0.1:'+config.terminal_port+'/api/owner' : null,
        unix_ingress_enabled:config.unix_ingress !== false,
        public_event_bodies:false,effect_ack_done:false},'application/json',request.method);
      return true;
    }
    if (state.runtime_binding?.manifest_sha256 !== pin || state.runtime_binding?.config_sha256 !== hash(configBytes) ||
        state.runtime_binding?.node_id !== config.node_id) throw Error('LOCAL_TERMINAL_BINDING_MISMATCH');
    // Personal input/records and credentials do not cross the public boundary.
    reply(response,200,{schema:'qikvrt-self-host-terminal/v1',state:'REFERENCE_HTTP_READY',
      node_id:config.node_id,manifest_sha256:pin,config_sha256:hash(configBytes),
      public_effects:'READ_ONLY',durable_input:'OWNER_UNIX_DAEMON_NOT_STARTED_IN_REFERENCE_PROFILE',effect_ack_done:false},'application/json',request.method);
  } else if (url.pathname === '/api/run') reply(response,503,{error:'GITHUB_ADAPTER_NOT_SELECTED'},'application/json',request.method);
  else if (url.pathname === '/api/repository') {
    const path = url.searchParams.get('path') || '';
    if (url.searchParams.get('repository') !== manifest.source_repository) reply(response,409,{error:'PACKAGED_REPOSITORY_SCOPE_REQUIRED'});
    else if (path === '') reply(response,200,{visibility:'public-source-export',updated_at:null,source_semantics:'IMMUTABLE_PACKAGED_SOURCE; NOT_REMOTE_MAIN'},'application/json',request.method);
    else if (path === '/commits/main') reply(response,200,{sha:manifest.source_head,commit:{tree:{sha:manifest.source_tree}},source_semantics:'IMMUTABLE_PACKAGED_SOURCE; NOT_REMOTE_MAIN'},'application/json',request.method);
    else {
      const match = /^\/contents\/(.+)\?ref=main$/.exec(path);
      if (!match || !documents.has(match[1])) reply(response,404,{error:'FIXED_PUBLIC_DOCUMENT_REQUIRED'});
      else {
        const raw = readFileSync(join(root,match[1]));
        const blob = createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
        reply(response,200,{content:raw.toString('base64'),encoding:'base64',sha:blob},'application/json',request.method);
      }
    }
  } else if (files.has(url.pathname)) {
    const [path,type] = files.get(url.pathname);
    reply(response,200,readFileSync(join(root,path)),type,request.method);
  } else {
    const html = readFileSync(join(root,'docs/terminal/index.html'),'utf8').replace('data-qikvrt-source="github"','data-qikvrt-source="node"');
    reply(response,200,html,'text/html',request.method);
  }
  return true;
}
const repositories = [{name:manifest.source_repository,role:'Packaged source',branch:'main'}];
const env = {QIKVRT_MONITOR_SOURCE_HEAD:manifest.source_head,QIKVRT_MONITOR_SOURCE_TREE:manifest.source_tree,
  QIKVRT_MONITOR_SOURCE_REPOSITORY:manifest.source_repository,QIKVRT_MONITOR_NODE_ID:config.node_id,
  QIKVRT_MESH_WORK_PEERS:JSON.stringify(config.mesh_work_peers || []),
  QIKVRT_MONITOR_STATE_DIR:join(config.state_dir,'monitor'),QIKVRT_MONITOR_REPOSITORIES:JSON.stringify(repositories)};
if (config.adapter === 'github' && config.github_webhook_secret_file) env.QIKVRT_GITHUB_WEBHOOK_SECRET = readFileSync(config.github_webhook_secret_file,'utf8').trim();
if(config.mesh_file){env.QIKVRT_MESH_FILE=join(config.state_dir,config.mesh_file);
  env.QIKVRT_MESH_FILE_TOKEN=readFileSync(config.terminal_token_file,'utf8').trim();
  env.QIKVRT_MESH_FILE_ALLOWED_ORIGINS=JSON.stringify(config.mesh_file_allowed_origins||[]);}
const monitor = createMonitor({env,repositories,handleRequest:routes,
  ...(config.adapter === 'none' ? {observe:async()=>({schema:'qikvrt-public-activity/v1',version:VERSION,
    generated_at:new Date().toISOString(),mode:'local_packaged_source',repositories:[],delivery:{periodic_polling:false},
    local_runtime:binding(),boundaries:{workflow_success_is_effect_ack_done:false,remote_repository_observed:false}})} : {}),
});
monitor.server.listen(config.port,config.host,() => {
  console.log(JSON.stringify({state:['temdd','firefox'].includes(config.terminal_profile)?'SELF_HOST_NATIVE_READY':'SELF_HOST_REFERENCE_READY',source_head:manifest.source_head,
    source_tree:manifest.source_tree,manifest_sha256:pin,config_sha256:hash(configBytes),node_id:config.node_id,
    adapter:config.adapter,local_url:'http://127.0.0.1:'+config.port+'/client',
    terminal_opening:config.terminal_profile === 'firefox' ? 'EXPLICIT_FIREFOX_PROFILE' : 'ON_DEMAND_URL',
    effect_ack_done:false}));
});
for (const s of ['SIGINT','SIGTERM']) process.on(s,()=>{monitor.server.closeAllConnections();monitor.server.close(()=>process.exit(0));});
