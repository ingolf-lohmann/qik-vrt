// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Authority-only read-only inventory contract; no external effects.
import assert from 'node:assert/strict';
import test from 'node:test';
import {readOpenPullRequests,normalizeRun} from './observer.mjs';
const sha=n=>n.toString(16).padStart(40,'0');
const pr=n=>({number:n,head:{sha:sha(n)},state:'open',draft:false});
const fake=values=>async url=>{
 const page=Number(new URL(url).searchParams.get('page')),value=values[page-1];
 if(value instanceof Error)throw value;
 return value===403?new Response('{}',{status:403}):Response.json(value||[]);
};
test('PR inventory traverses all pages, not only the first 100',async()=>{
 const result=await readOpenPullRequests({fetchImpl:fake([Array.from({length:100},(_,i)=>pr(i+1)),[pr(101),pr(102)]])});
 assert.equal(result.complete,true);assert.equal(result.items.length,102);assert.equal(result.pages.length,2);
 assert.equal(result.items[101].head_sha,sha(102));assert.equal(result.error,null);
});
test('GitHub 403 leaves partial inventory explicitly incomplete',async()=>{
 const result=await readOpenPullRequests({fetchImpl:fake([Array.from({length:100},(_,i)=>pr(i+1)),403])});
 assert.equal(result.complete,false);assert.equal(result.items.length,100);assert.equal(result.error.code,'HTTP_403');
});
test('aborted transport is not a successful empty list',async()=>{
 const fail=new Error('abort');fail.name='AbortError';
 const result=await readOpenPullRequests({fetchImpl:fake([fail])});
 assert.equal(result.complete,false);assert.equal(result.error.code,'ABORTED');
});
test('conflicting duplicate PR cannot silently replace head',async()=>{
 const result=await readOpenPullRequests({fetchImpl:fake([Array.from({length:100},(_,i)=>pr(i+1)),[pr(1)]])});
 assert.equal(result.complete,false);assert.equal(result.error.code,'DUPLICATE_PR_ACROSS_PAGES');
});
test('page cap is fail-closed',async()=>{
 const result=await readOpenPullRequests({fetchImpl:fake([Array.from({length:100},(_,i)=>pr(i+1))]),maxPages:1});
 assert.equal(result.complete,false);assert.equal(result.error.code,'PAGE_LIMIT_EXHAUSTED');
});
test('existing workflow normalization keeps action_required distinct from failure',()=>{
 const run=normalizeRun({id:1,event:'pull_request',status:'completed',conclusion:'action_required',head_sha:sha(9)},'ingolf-lohmann/qik-vrt');
 assert.equal(run.state,'action_required');assert.notEqual(run.state,'failure');
});
