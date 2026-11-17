/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt/codec_native.h"
#include "qikvrt/sha256.h"
#include "qikvrt/standpoint_signature_v1.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>

static unsigned long get32(const unsigned char *p)
{
    return ((unsigned long)p[0]<<24)|((unsigned long)p[1]<<16)
        |((unsigned long)p[2]<<8)|p[3];
}
static void put32(unsigned char *p,unsigned long n)
{
    unsigned int i;for(i=0;i<4;i++)p[i]=(unsigned char)(n>>(24-8*i));
}
static void put64(unsigned char *p,unsigned long n)
{
    memset(p,0,4);put32(p+4,n);
}
static int read_exact(FILE *f,unsigned char *p,size_t n)
{
    size_t got;while(n){got=fread(p,1,n,f);if(!got)return 0;p+=got;n-=got;}return 1;
}
static int write_exact(FILE *f,const unsigned char *p,size_t n)
{
    size_t got;while(n){got=fwrite(p,1,n,f);if(!got)return 0;p+=got;n-=got;}return 1;
}
static void digest(const void *p,size_t n,unsigned char out[32])
{
    qikvrt_sha256 s;qikvrt_sha256_init(&s);qikvrt_sha256_update(&s,p,n);
    qikvrt_sha256_final(&s,out);
}
static int profile_valid(unsigned long limit)
{
    return CHAR_BIT==8 && sizeof(size_t)>=4 && UINT_MAX>=16777217UL
        && limit<=QIKVRT_NATIVE_LIMIT;
}
int qikvrt_codec_encode(FILE *in,FILE *out,int level,unsigned long block,
                       unsigned long limit,const char **error)
{
    unsigned char header[416],frame[41],footer[49];
    unsigned char *raw=0,*packed=0,*payload;
    unsigned long total=0,blocks=0,stored;
    size_t count,take;
    uLongf capacity,packed_size;
    qikvrt_sha256 wire;
    int ok=0,method;
#define FAIL_ENCODE(s) do{*error=(s);goto done;}while(0)
    if(!profile_valid(limit)||block<4096UL||block>16777216UL
       ||(level!=0&&level!=6)) { *error="UNSUPPORTED_NATIVE_PROFILE";return 0; }
    raw=(unsigned char *)malloc((size_t)block);
    capacity=compressBound((uLong)block);
    packed=(unsigned char *)malloc((size_t)capacity);
    if(!raw||!packed) FAIL_ENCODE("ALLOCATION_FAILED");
    memcpy(header,"QIKVRTC\0",8);header[8]=1;header[9]=0;
    header[10]=1;header[11]=160;put32(header+12,block);
    memcpy(header+16,qikvrt_standpoint_signature_v1,400);
    qikvrt_sha256_init(&wire);qikvrt_sha256_update(&wire,header,416);
    if(!write_exact(out,header,416)) FAIL_ENCODE("OUTPUT_IO");
    for(;;) {
        count=0;
        while(count<(size_t)block) {
            take=fread(raw+count,1,(size_t)block-count,in);
            if(!take) {if(ferror(in)) FAIL_ENCODE("INPUT_IO");break;}
            count+=take;
        }
        if(!count)break;
        if((unsigned long)count>limit-total) FAIL_ENCODE("OUTPUT_LIMIT_EXCEEDED");
        method=0;payload=raw;stored=(unsigned long)count;
        if(level) {
            packed_size=capacity;
            if(compress2(packed,&packed_size,raw,(uLong)count,level)!=Z_OK)
                FAIL_ENCODE("ZLIB_ENCODE_FAILED");
            if(packed_size<(uLong)count) {
                method=1;payload=packed;stored=(unsigned long)packed_size;
            }
        }
        frame[0]=(unsigned char)method;put32(frame+1,(unsigned long)count);
        put32(frame+5,stored);digest(raw,count,frame+9);
        qikvrt_sha256_update(&wire,frame,41);
        qikvrt_sha256_update(&wire,payload,(size_t)stored);
        if(!write_exact(out,frame,41)||!write_exact(out,payload,(size_t)stored))
            FAIL_ENCODE("OUTPUT_IO");
        total+=(unsigned long)count;blocks++;
    }
    footer[0]=255;put64(footer+1,total);put64(footer+9,blocks);
    qikvrt_sha256_update(&wire,footer,17);qikvrt_sha256_final(&wire,footer+17);
    if(!write_exact(out,footer,49)||fflush(out)) FAIL_ENCODE("OUTPUT_IO");
    ok=1;
done:
    free(raw);free(packed);return ok;
#undef FAIL_ENCODE
}
int qikvrt_codec_decode(FILE *in,FILE *out,unsigned long limit,const char **error)
{
    unsigned char header[416],frame[41],footer[49],hash[32];
    unsigned char *raw=0,*packed=0;
    unsigned long block,total=0,blocks=0,length,stored;
    qikvrt_sha256 wire;
    z_stream z;
    int method,short_block=0,ok=0,status;
#define FAIL_DECODE(s) do{*error=(s);goto done;}while(0)
    if(!profile_valid(limit)){*error="UNSUPPORTED_NATIVE_PROFILE";return 0;}
    if(!read_exact(in,header,416)){*error="TRUNCATED_HEADER";return 0;}
    if(memcmp(header,"QIKVRTC\0",8)||header[8]!=1||header[9]!=0
       ||header[10]!=1||header[11]!=160) {*error="UNSUPPORTED_HEADER";return 0;}
    if(memcmp(header+16,qikvrt_standpoint_signature_v1,400)) {
        *error="SIGNATURE_MISMATCH";return 0;
    }
    block=get32(header+12);
    if(block<4096UL||block>16777216UL){*error="BLOCK_LIMIT_EXCEEDED";return 0;}
    raw=(unsigned char *)malloc((size_t)block+1);
    packed=(unsigned char *)malloc((size_t)block);
    if(!raw||!packed) FAIL_DECODE("ALLOCATION_FAILED");
    qikvrt_sha256_init(&wire);qikvrt_sha256_update(&wire,header,416);
    for(;;) {
        method=fgetc(in);
        if(method==255) {
            footer[0]=255;if(!read_exact(in,footer+1,48))FAIL_DECODE("TRUNCATED_FOOTER");
            qikvrt_sha256_update(&wire,footer,17);qikvrt_sha256_final(&wire,hash);
            if(get32(footer+1)||get32(footer+9)||get32(footer+5)!=total
               ||get32(footer+13)!=blocks||memcmp(hash,footer+17,32))
                FAIL_DECODE("FOOTER_MISMATCH");
            if(fgetc(in)!=EOF)FAIL_DECODE("TRAILING_INPUT");
            if(ferror(in))FAIL_DECODE("INPUT_IO");
            if(fflush(out))FAIL_DECODE("OUTPUT_IO");
            ok=1;break;
        }
        if((method!=0&&method!=1)||short_block)FAIL_DECODE("UNKNOWN_METHOD_OR_BLOCK_ORDER");
        frame[0]=(unsigned char)method;
        if(!read_exact(in,frame+1,40))FAIL_DECODE("TRUNCATED_BLOCK");
        length=get32(frame+1);stored=get32(frame+5);
        if(!length||length>block||!stored||stored>length
           ||(!method&&stored!=length)||(method&&stored>=length))
            FAIL_DECODE("NONCANONICAL_BLOCK_LENGTHS");
        if(length>limit-total)FAIL_DECODE("OUTPUT_LIMIT_EXCEEDED");
        if(!read_exact(in,packed,(size_t)stored))FAIL_DECODE("TRUNCATED_PAYLOAD");
        if(!method)memcpy(raw,packed,(size_t)length);
        else {
            memset(&z,0,sizeof(z));z.next_in=packed;z.avail_in=(uInt)stored;
            z.next_out=raw;z.avail_out=(uInt)(length+1);
            if(inflateInit(&z)!=Z_OK)FAIL_DECODE("ZLIB_INIT_FAILED");
            status=inflate(&z,Z_FINISH);
            if(status!=Z_STREAM_END||z.total_in!=stored||z.total_out!=length) {
                inflateEnd(&z);FAIL_DECODE("INVALID_ZLIB_TERMINATION");
            }
            if(inflateEnd(&z)!=Z_OK)FAIL_DECODE("ZLIB_END_FAILED");
        }
        digest(raw,(size_t)length,hash);
        if(memcmp(hash,frame+9,32))FAIL_DECODE("BLOCK_HASH_MISMATCH");
        qikvrt_sha256_update(&wire,frame,41);
        qikvrt_sha256_update(&wire,packed,(size_t)stored);
        if(!write_exact(out,raw,(size_t)length))FAIL_DECODE("OUTPUT_IO");
        total+=length;blocks++;short_block=(length<block);
    }
done:
    free(raw);free(packed);return ok;
#undef FAIL_DECODE
}
