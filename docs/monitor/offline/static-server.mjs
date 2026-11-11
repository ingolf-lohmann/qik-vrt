// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann.
// Static assets only: no token, executor, persistence server or repository write.
import {createServer as createHttpServer} from 'node:http';
import {createServer as createHttpsServer} from 'node:https';
import {readFile,stat} from 'node:fs/promises';
import {dirname,resolve,sep,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url));
const types={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.svg':'image/svg+xml','.webmanifest':'application/manifest+json','.txt':'text/plain;charset=utf-8','.json':'application/json;charset=utf-8'};
const handler=async(req,res)=>{try{if(!['GET','HEAD'].includes(req.method))throw Error('METHOD');const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(pathname.includes('\0')||pathname.includes('\\'))throw Error('PATH');const file=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));if(!file.startsWith(root+sep)||!['.html','.js','.css','.svg','.webmanifest','.txt','.json'].includes(extname(file))||!(await stat(file)).isFile())throw Error('PATH');const data=await readFile(file);res.writeHead(200,{'content-type':types[extname(file)],'cache-control':'no-store','x-content-type-options':'nosniff','content-length':data.length});res.end(req.method==='HEAD'?undefined:data);}catch{res.writeHead(404,{'content-type':'text/plain'});res.end('Not found');}};
const certPath=process.env.QIKVRT_TLS_CERT;
const keyPath=process.env.QIKVRT_TLS_KEY;
if (Boolean(certPath)!==Boolean(keyPath)) throw Error('TLS_CERT_AND_KEY_REQUIRED_TOGETHER');
const tls=Boolean(certPath);
const server=tls?createHttpsServer({cert:await readFile(certPath),key:await readFile(keyPath)},handler):createHttpServer(handler);
const port=Number(process.env.PORT||(tls?8443:8765));
if (!Number.isInteger(port)||port<1||port>65535) throw Error('INVALID_PORT');
// Without TLS, bind only to loopback: no accidental public plaintext deployment.
const host=process.env.QIKVRT_BIND_HOST||(tls?'0.0.0.0':'127.0.0.1');
if (!tls&&!['127.0.0.1','::1','localhost'].includes(host)) throw Error('PUBLIC_HTTP_FORBIDDEN');
server.listen(port,host,()=>process.stdout.write(`QIKVRT_STATIC_READY ${tls?'HTTPS':'HTTP_LOOPBACK'}\n`));
