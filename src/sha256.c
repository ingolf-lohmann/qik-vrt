/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt/sha256.h"
#include <string.h>
#define WORD(x) ((x) & 0xffffffffUL)
#define ROT(x,n) (WORD((x) >> (n)) | WORD((x) << (32 - (n))))
static const unsigned long k[64] = {
    0x428a2f98UL,0x71374491UL,0xb5c0fbcfUL,0xe9b5dba5UL,
    0x3956c25bUL,0x59f111f1UL,0x923f82a4UL,0xab1c5ed5UL,
    0xd807aa98UL,0x12835b01UL,0x243185beUL,0x550c7dc3UL,
    0x72be5d74UL,0x80deb1feUL,0x9bdc06a7UL,0xc19bf174UL,
    0xe49b69c1UL,0xefbe4786UL,0x0fc19dc6UL,0x240ca1ccUL,
    0x2de92c6fUL,0x4a7484aaUL,0x5cb0a9dcUL,0x76f988daUL,
    0x983e5152UL,0xa831c66dUL,0xb00327c8UL,0xbf597fc7UL,
    0xc6e00bf3UL,0xd5a79147UL,0x06ca6351UL,0x14292967UL,
    0x27b70a85UL,0x2e1b2138UL,0x4d2c6dfcUL,0x53380d13UL,
    0x650a7354UL,0x766a0abbUL,0x81c2c92eUL,0x92722c85UL,
    0xa2bfe8a1UL,0xa81a664bUL,0xc24b8b70UL,0xc76c51a3UL,
    0xd192e819UL,0xd6990624UL,0xf40e3585UL,0x106aa070UL,
    0x19a4c116UL,0x1e376c08UL,0x2748774cUL,0x34b0bcb5UL,
    0x391c0cb3UL,0x4ed8aa4aUL,0x5b9cca4fUL,0x682e6ff3UL,
    0x748f82eeUL,0x78a5636fUL,0x84c87814UL,0x8cc70208UL,
    0x90befffaUL,0xa4506cebUL,0xbef9a3f7UL,0xc67178f2UL
};
static void transform(qikvrt_sha256 *s)
{
    unsigned long w[64], a,b,c,d,e,f,g,h,x,y,u,v;
    unsigned int i;
    for (i=0;i<16;i++) {
        const unsigned char *p=s->block+4*i;
        w[i]=((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)
            |((unsigned long)p[2]<<8)|p[3];
    }
    for (i=16;i<64;i++) {
        x=w[i-15]; y=w[i-2];
        u=ROT(x,7)^ROT(x,18)^(x>>3);
        v=ROT(y,17)^ROT(y,19)^(y>>10);
        w[i]=WORD(w[i-16]+u+w[i-7]+v);
    }
    a=s->state[0];b=s->state[1];c=s->state[2];d=s->state[3];
    e=s->state[4];f=s->state[5];g=s->state[6];h=s->state[7];
    for (i=0;i<64;i++) {
        u=WORD(h+(ROT(e,6)^ROT(e,11)^ROT(e,25))
            +((e&f)^((~e)&g))+k[i]+w[i]);
        v=WORD((ROT(a,2)^ROT(a,13)^ROT(a,22))+((a&b)^(a&c)^(b&c)));
        h=g;g=f;f=e;e=WORD(d+u);d=c;c=b;b=a;a=WORD(u+v);
    }
    s->state[0]=WORD(s->state[0]+a);s->state[1]=WORD(s->state[1]+b);
    s->state[2]=WORD(s->state[2]+c);s->state[3]=WORD(s->state[3]+d);
    s->state[4]=WORD(s->state[4]+e);s->state[5]=WORD(s->state[5]+f);
    s->state[6]=WORD(s->state[6]+g);s->state[7]=WORD(s->state[7]+h);
}
void qikvrt_sha256_init(qikvrt_sha256 *s)
{
    static const unsigned long initial[8]={0x6a09e667UL,0xbb67ae85UL,
        0x3c6ef372UL,0xa54ff53aUL,0x510e527fUL,0x9b05688cUL,
        0x1f83d9abUL,0x5be0cd19UL};
    memcpy(s->state,initial,sizeof(initial));
    s->used=0;s->bytes_lo=0;s->bytes_hi=0;
}
void qikvrt_sha256_update(qikvrt_sha256 *s,const void *data,size_t count)
{
    const unsigned char *p=(const unsigned char *)data;
    size_t take;
    unsigned long old=s->bytes_lo;
    /* Callers supply bounded blocks smaller than 2^32 bytes. */
    s->bytes_lo=WORD(old+(unsigned long)count);
    if (s->bytes_lo<old) s->bytes_hi=WORD(s->bytes_hi+1);
    while (count) {
        take=64-s->used;if(take>count) take=count;
        memcpy(s->block+s->used,p,take);s->used+=take;p+=take;count-=take;
        if(s->used==64) {transform(s);s->used=0;}
    }
}
void qikvrt_sha256_final(qikvrt_sha256 *s,unsigned char digest[32])
{
    unsigned long hi=WORD((s->bytes_hi<<3)|(s->bytes_lo>>29));
    unsigned long lo=WORD(s->bytes_lo<<3);
    unsigned int i;
    s->block[s->used++]=128;
    if(s->used>56) {
        memset(s->block+s->used,0,64-s->used);transform(s);s->used=0;
    }
    memset(s->block+s->used,0,56-s->used);
    for(i=0;i<4;i++) {
        s->block[56+i]=(unsigned char)(hi>>(24-8*i));
        s->block[60+i]=(unsigned char)(lo>>(24-8*i));
    }
    transform(s);
    for(i=0;i<32;i++) digest[i]=(unsigned char)(s->state[i/4]>>(24-8*(i%4)));
    memset(s,0,sizeof(*s));
}
