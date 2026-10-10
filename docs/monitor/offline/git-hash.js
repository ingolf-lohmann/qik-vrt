// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright 2026 Ingolf Lohmann. Git-object interoperability, not signatures.
const encoder=new TextEncoder();
export class SHA1 {
  constructor(){this.state=new Uint32Array([0x67452301,0xefcdab89,0x98badcfe,0x10325476,0xc3d2e1f0]);this.buffer=new Uint8Array(64);this.used=0;this.bytes=0;this.words=new Uint32Array(80);this.finished=false;}
  block(bytes,offset=0){const w=this.words;for(let i=0;i<16;i++)w[i]=(bytes[offset+i*4]<<24)|(bytes[offset+i*4+1]<<16)|(bytes[offset+i*4+2]<<8)|bytes[offset+i*4+3];const rot=(v,n)=>(v<<n)|(v>>>(32-n));for(let i=16;i<80;i++)w[i]=rot(w[i-3]^w[i-8]^w[i-14]^w[i-16],1);
    let [a,b,c,d,e]=this.state;for(let i=0;i<80;i++){const f=i<20?(b&c)|(~b&d):i<40?b^c^d:i<60?(b&c)|(b&d)|(c&d):b^c^d;const k=i<20?0x5a827999:i<40?0x6ed9eba1:i<60?0x8f1bbcdc:0xca62c1d6;const t=(rot(a,5)+f+e+k+w[i])>>>0;e=d;d=c;c=rot(b,30);b=a;a=t;}for(const [i,v]of [a,b,c,d,e].entries())this.state[i]=(this.state[i]+v)>>>0;
  }
  update(bytes){if(this.finished)throw Error('HASH_ALREADY_FINALIZED');this.bytes+=bytes.length;let at=0;if(this.used){const n=Math.min(64-this.used,bytes.length);this.buffer.set(bytes.subarray(0,n),this.used);this.used+=n;at=n;if(this.used===64){this.block(this.buffer);this.used=0;}}
    for(;at+64<=bytes.length;at+=64)this.block(bytes,at);if(at<bytes.length){this.buffer.set(bytes.subarray(at),0);this.used=bytes.length-at;}return this;
  }
  hex(){if(this.finished)throw Error('HASH_ALREADY_FINALIZED');const length=this.bytes;this.update(new Uint8Array([128]));while(this.used!==56)this.update(new Uint8Array([0]));const tail=new Uint8Array(8),view=new DataView(tail.buffer);view.setUint32(0,Math.floor(length/536870912));view.setUint32(4,(length*8)>>>0);this.update(tail);this.finished=true;return [...this.state].map(v=>v.toString(16).padStart(8,'0')).join('');}
}
export const gitBlobHasher=length=>new SHA1().update(encoder.encode('blob '+length+'\0'));
export function gitTree(files){const root=new Map();for(const file of files){let node=root;const parts=file.path.split('/');for(const part of parts.slice(0,-1)){if(node.has(part)&&!(node.get(part)instanceof Map))throw Error('FILE_DIRECTORY_CONFLICT');if(!node.has(part))node.set(part,new Map());node=node.get(part);}const leaf=parts.at(-1);if(node.has(leaf))throw Error('FILE_DIRECTORY_CONFLICT');node.set(leaf,file);}
  const compare=(a,b)=>{for(let i=0;i<Math.min(a.length,b.length);i++)if(a[i]!==b[i])return a[i]-b[i];return a.length-b.length;};
  const visit=node=>{const rows=[];for(const [name,value]of node){const dir=value instanceof Map,hash=dir?visit(value):value.git_blob_sha1,prefix=encoder.encode((dir?'40000':value.mode)+' '+name+'\0'),raw=new Uint8Array(prefix.length+20);raw.set(prefix);raw.set(Uint8Array.from(hash.match(/../g),h=>parseInt(h,16)),prefix.length);rows.push({order:encoder.encode(name+(dir?'/':'')),raw});}rows.sort((a,b)=>compare(a.order,b.order));const length=rows.reduce((n,r)=>n+r.raw.length,0),hash=new SHA1().update(encoder.encode('tree '+length+'\0'));for(const row of rows)hash.update(row.raw);return hash.hex();};return visit(root);
}
