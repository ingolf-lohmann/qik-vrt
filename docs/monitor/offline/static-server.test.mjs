// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Regression: a public plaintext fallback must never silently replace HTTPS.
import {test} from 'node:test';
import {spawn} from 'node:child_process';
import {strict as assert} from 'node:assert';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
const server=join(dirname(fileURLToPath(import.meta.url)),'static-server.mjs');
async function run(env) {
  return new Promise((resolve,reject)=>{
    const child=spawn(process.execPath,[server],{env:{...process.env,...env},stdio:['ignore','pipe','pipe']});
    let output='';
    const timeout=setTimeout(()=>{child.kill();reject(Error('server did not terminate'))},3000);
    child.stdout.on('data',b=>output+=b);
    child.stderr.on('data',b=>output+=b);
    child.on('error',reject);
    child.on('exit',code=>{clearTimeout(timeout);resolve({code,output})});
  });
}
test('reject incomplete TLS configuration',async()=>{
  const r=await run({QIKVRT_TLS_CERT:'/missing/cert',QIKVRT_TLS_KEY:''});
  assert.notEqual(r.code,0);
  assert.match(r.output,/TLS_CERT_AND_KEY_REQUIRED_TOGETHER/);
});
test('reject public plaintext binding',async()=>{
  const r=await run({QIKVRT_TLS_CERT:'',QIKVRT_TLS_KEY:'',QIKVRT_BIND_HOST:'0.0.0.0'});
  assert.notEqual(r.code,0);
  assert.match(r.output,/PUBLIC_HTTP_FORBIDDEN/);
});
test('reject invalid port',async()=>{
  const r=await run({QIKVRT_TLS_CERT:'',QIKVRT_TLS_KEY:'',QIKVRT_BIND_HOST:'127.0.0.1',PORT:'70000'});
  assert.notEqual(r.code,0);
  assert.match(r.output,/INVALID_PORT/);
});
