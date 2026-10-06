// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0; Copyright 2026 Ingolf Lohmann.
// Static assets only: no token, executor, persistence server or repository write.
import {createServer} from 'node:http';
import {readFile,stat} from 'node:fs/promises';
import {dirname,resolve,sep,extname} from 'node:path';
import {fileURLToPath} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url));
const types={'.html':'text/html;charset=utf-8','.js':'text/javascript;charset=utf-8','.css':'text/css;charset=utf-8','.svg':'image/svg+xml','.webmanifest':'application/manifest+json','.txt':'text/plain;charset=utf-8','.json':'application/json;charset=utf-8'};
createServer(async(req,res)=>{try{if(!['GET','HEAD'].includes(req.method))throw Error('METHOD');const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);if(pathname.includes('\0')||pathname.includes('\\'))throw Error('PATH');const file=resolve(root,'.'+pathname+(pathname.endsWith('/')?'index.html':''));if(!file.startsWith(root+sep)||!['.html','.js','.css','.svg','.webmanifest','.txt','.json'].includes(extname(file))||!(await stat(file)).isFile())throw Error('PATH');const data=await readFile(file);res.writeHead(200,{'content-type':types[extname(file)],'cache-control':'no-store','x-content-type-options':'nosniff','content-length':data.length});res.end(req.method==='HEAD'?undefined:data);}catch{res.writeHead(404,{'content-type':'text/plain'});res.end('Not found');}}).listen(Number(process.env.PORT||8765),'0.0.0.0',()=>process.stdout.write('QIKVRT_STATIC_READY\n'));
