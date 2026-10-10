// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Test contribution: OpenAI Codex.
// Reuses #476's pinned Playwright/Chromium and loopback browser-test pattern.
// This server is an inert test fixture: it has no provider, storage or executor.
import assert from 'node:assert/strict';
import {test} from 'node:test';
import http from 'node:http';
import {readFileSync, mkdirSync, writeFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {snapshot, sourceFailure} from './react-feedback.test.mjs';

const here=fileURLToPath(new URL('.',import.meta.url));
const root=resolve(here,'../..');
const lock=JSON.parse(readFileSync(new URL('./browser-tests/BROWSER_LOCK.json',import.meta.url)));
const require=createRequire(resolve(process.env.QIKVRT_MONITOR_PLAYWRIGHT_ROOT || resolve(here,'browser-tests'),'package.json'));
const {chromium}=require('playwright');
assert.equal(require('playwright/package.json').version,lock.playwright);
const assets=['index-react.html','react-runtime.js','client-replica.js','mesh-react.js','mesh-react.css'];
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const git=(...args)=>execFileSync('git',args,{cwd:root,encoding:'utf8'}).trim();
const output=resolve(process.env.QIKVRT_MONITOR_BROWSER_REPORT || resolve(root,'.qikvrt/runtime/react-feedback-browser'));
mkdirSync(output,{recursive:true});

test('fresh real ReactDOM monitor: fixture 404, alert, raw diagnostics, siblings and recovery',async()=>{
  const sourceHead=git('rev-parse','HEAD'),sourceTree=git('rev-parse','HEAD^{tree}');
  if(process.env.QIKVRT_EXPECTED_HEAD)assert.equal(sourceHead,process.env.QIKVRT_EXPECTED_HEAD);
  if(process.env.CI)assert.equal(git('status','--porcelain','--untracked-files=all'),'','exact-head browser gate requires a clean checkout');
  const requests=[],streams=new Set(),results=[];
  let current=snapshot(),activityStatus=200;
  const server=http.createServer((request,response)=>{
    const url=new URL(request.url,'http://fixture.invalid');
    if(url.pathname.startsWith('/api/')){
      requests.push({path:url.pathname,method:request.method});
      if(url.pathname==='/api/stream'){
        response.writeHead(200,{'content-type':'text/event-stream','cache-control':'no-store'});
        response.write('event: snapshot\ndata: '+JSON.stringify(current)+'\n\n');
        streams.add(response);request.on('close',()=>streams.delete(response));return;
      }
      const value=url.pathname==='/api/activity' ? (activityStatus===200 ? current : {error:'fixture failure'}) :
        url.pathname==='/api/runtime' ? {node_id:'SYNTHETIC_RUNTIME',source_repository:'ingolf-lohmann/qik-vrt'} : {state:'UNKNOWN'};
      response.writeHead(url.pathname==='/api/activity' ? activityStatus : 200,{'content-type':'application/json'});
      response.end(JSON.stringify(value));return;
    }
    const name=['/mesh','/node','/'].includes(url.pathname) ? 'index-react.html' : url.pathname.slice(1);
    if(!assets.includes(name)){response.writeHead(404);response.end();return;}
    response.writeHead(200,{'content-type':name.endsWith('.html')?'text/html':name.endsWith('.css')?'text/css':'text/javascript',
      'content-security-policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'"});
    response.end(readFileSync(resolve(here,name)));
  });
  await new Promise(done=>server.listen(0,'127.0.0.1',done));
  const origin='http://127.0.0.1:'+server.address().port;
  let browser;
  try{
    browser=await chromium.launch({headless:true,executablePath:process.env.QIKVRT_MONITOR_CHROMIUM || undefined,args:['--no-sandbox']});
    assert.equal(browser.version(),lock.chromium_version);
    for(const width of [390,1280]){
      const page=await browser.newPage({viewport:{width,height:900}}),errors=[];
      page.on('pageerror',error=>errors.push(error.message));
      await page.goto(origin+'/mesh');
      const authority=page.locator('article').filter({has:page.getByRole('heading',{name:'Goldkelch/qik-vrt',exact:true})});
      await authority.getByText('Die angefragte Quelle ist derzeit nicht lesbar.',{exact:true}).waitFor();
      for(const label of ['Zustand','Auswirkung','Belegter Status / Unsicherheit','Zuständiger Akteur','Nächster REST-Schritt','Reparaturfortschritt'])
        assert.equal(await authority.locator('dt').filter({hasText:label}).count(),1);
      assert.match(await authority.innerText(),/nicht geklärt/);
      assert.match(await authority.innerText(),/Reparaturstart.*nicht belegt/);
      await authority.getByText('Technische Details: HTTP 404',{exact:true}).click();
      const raw=authority.getByLabel('Kopierbare Fehlerdiagnose');
      await raw.focus();assert.equal(await raw.evaluate(element=>document.activeElement===element),true);
      assert.equal(await raw.evaluate(element=>getComputedStyle(element).userSelect),'text');
      const diagnostic=JSON.parse(await raw.innerText());
      assert.equal(diagnostic.status,404);assert.equal(diagnostic.original_error,'404 Not Found; remaining=56');
      assert.equal(diagnostic.cause_established,false);assert.equal(sha(diagnostic.response_body),diagnostic.response_sha256);
      assert.equal(await page.getByText('SYNTHETIC_SIBLING',{exact:true}).count(),1);
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
      await page.screenshot({path:resolve(output,'authority-404-'+width+'.png'),fullPage:true});
      // A failed activity fetch must expose the same alert contract as #482,
      // while successful runtime/terminal siblings remain visible.
      activityStatus=404;await page.getByRole('button',{name:'Readback erneuern'}).click();
      await page.getByRole('alert').waitFor();assert.match(await page.getByRole('alert').innerText(),/Readback offen/);
      assert.equal(await page.getByText('SYNTHETIC_RUNTIME',{exact:true}).count(),1);
      activityStatus=200;await page.getByRole('button',{name:'Readback erneuern'}).click();
      await page.getByRole('alert').waitFor({state:'detached'});
      assert.deepEqual(errors,[]);results.push({width,groups:5,labels:6,alert:true,raw_diagnostic_copyable:true,recovery:true,page_errors:errors});
      await page.close();
    }
    const page=await browser.newPage();await page.goto(origin+'/node?repository=Goldkelch/qik-vrt');
    await page.getByText('Die angefragte Quelle ist derzeit nicht lesbar.',{exact:true}).waitFor();
    assert.equal(await page.locator('article').count(),1);assert.equal(await page.getByText('SYNTHETIC_SIBLING',{exact:true}).count(),0);
    await page.goto(origin+'/index-react.html?view=node&repository=Goldkelch/qik-vrt');
    await page.getByText('Die angefragte Quelle ist derzeit nicht lesbar.',{exact:true}).waitFor();
    assert.equal(await page.locator('article').count(),1);await page.close();
    assert.ok(requests.every(r=>r.method==='GET'));
    writeFileSync(resolve(output,'react-feedback-browser.json'),JSON.stringify({schema:'qikvrt-react-feedback-browser-witness/v1',
      source_head:sourceHead,source_tree:sourceTree,worktree_clean:git('status','--porcelain','--untracked-files=all')==='',
      source_digests:Object.fromEntries(assets.map(name=>[name,sha(readFileSync(resolve(here,name)))])),
      browser:browser.version(),playwright:lock.playwright,results,node_view_filtered:true,static_entry_filtered:true,requests,
      scope:'LINUX_LOOPBACK_CAPTURED_404_REPLAY_REAL_REACTDOM',predecessor_evidence_transfer:false,
      provider_readback:false,provider_404_repaired:false,public_deployment:false,human_comprehension:'NOT_MEASURED',EFFECT_ACK_DONE:false},null,2)+'\n');
  }finally{
    await browser?.close();for(const response of streams)response.destroy();
    await new Promise(done=>server.close(done));
  }
});
