/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
 * Hosted C90 adapter; the core itself does not depend on stdio or files. */
#include "qikvrt_transputer.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
static unsigned char body[QIKVRT_MAX_MESSAGE+1U],workspace[QIKVRT_WIRE_MAX_FRAME];
static int hex(const char *s,unsigned char *out) {
    unsigned int i,a,b;
    if(strlen(s)!=64)return 0;
    for(i=0;i<32;++i) {
        a=(unsigned int)(unsigned char)s[2*i];b=(unsigned int)(unsigned char)s[2*i+1];
        if(a>='0' && a<='9')a-='0';else if(a>='a' && a<='f')a=a-'a'+10;else return 0;
        if(b>='0' && b<='9')b-='0';else if(b>='a' && b<='f')b=b-'a'+10;else return 0;
        out[i]=(unsigned char)(a*16U+b);
    }return 1;
}
static int emit(void *context,const unsigned char *frame,unsigned int n) {
    FILE *stream=(FILE *)context;return fwrite(frame,1,n,stream)==n;
}
int main(int argc,char **argv) {
    unsigned char source[32],destination[32],subject[32],route[QIKVRT_ROUTE_BYTES],payload[4096];
    qikvrt_receiver rx;qikvrt_wire_frame key;
    unsigned int n,length,frames;int status,complete=0;FILE *file;qikvrt_u32 wide;
    unsigned char input[14],output[6];
    unsigned int j,k,v;
#ifdef _WIN32
    if(_setmode(_fileno(stdin),_O_BINARY)==-1 ||
       _setmode(_fileno(stdout),_O_BINARY)==-1)return 4;
#endif
    if(argc<2)return 2;
    if(strcmp(argv[1],"evaluate")==0 && argc==3) {
        if(strlen(argv[2])!=28U)return 2;
        for(j=0;j<14U;++j) {
            v=0;
            for(k=0;k<2U;++k) {
                n=(unsigned int)(unsigned char)argv[2][j*2U+k];
                if(n>='0' && n<='9')n-='0';
                else if(n>='a' && n<='f')n=n-'a'+10U;
                else return 2;
                v=v*16U+n;
            }
            input[j]=(unsigned char)v;
        }
        qikvrt_evaluate_bytes(input,output);
        for(j=0;j<6U;++j)if(printf("%02x",(unsigned int)output[j])<0)return 4;
        return puts("")>=0 && fflush(stdout)==0 ? 0:4;
    }
    if(strcmp(argv[1],"roundtrip")==0) {
        n=(unsigned int)fread(workspace,1,sizeof(workspace),stdin);
        if(!qikvrt_wire_decode(workspace,n,&key,payload,sizeof(payload)))return 3;
        if(!qikvrt_wire_encode(&key,payload,workspace,sizeof(workspace),&length))return 3;
        return emit(stdout,workspace,length) && fflush(stdout)==0 ? 0:4;
    }
    if(argc<5 || !hex(argv[2],source) || !hex(argv[3],destination) || !hex(argv[4],subject))return 2;
    if(strcmp(argv[1],"send")==0 && argc==7) {
        if(strlen(argv[5])!=1 || argv[5][0]<'1' || argv[5][0]>'3')return 2;
        file=fopen(argv[6],"rb");if(!file)return 4;
        n=(unsigned int)fread(body,1,sizeof(body),file);status=ferror(file);fclose(file);
        if(status || n>QIKVRT_MAX_MESSAGE)return 4;
        if(!qikvrt_route(route,source,destination,subject,1,4,(unsigned char)(argv[5][0]-'0'),body,n))return 3;
        memset(&key,0,sizeof(key));key.type=1;key.session_id=8;key.nonce=9;key.message_id=10;
        if(!qikvrt_send(route,body,n,&key,workspace,sizeof(workspace),emit,stdout))return 4;
        return fflush(stdout)==0 ? 0:4;
    }
    if(strcmp(argv[1],"receive")==0 && argc==5) {
        if(!qikvrt_receiver_init(&rx,body,QIKVRT_MAX_MESSAGE,source,destination,subject,1,4))return 3;
        for(frames=0;frames<64;++frames) {
            n=(unsigned int)fread(workspace,1,84,stdin);
            if(n==0 && feof(stdin))break;
            if(n!=84)return 3;
            wide=qikvrt_get32(workspace+44);if(wide>4096U)return 3;
            length=(unsigned int)wide+4U;
            if(fread(workspace+84,1,length,stdin)!=length)return 3;
            status=qikvrt_receive(&rx,workspace,84U+length);if(!status)return 3;
            if(status==2)complete=1;
        }
        if(!complete || frames==64 || ferror(stdin))return 3;
        n=qikvrt_receiver_length(&rx);return fwrite(body,1,n,stdout)==n && fflush(stdout)==0 ? 0:4;
    }
    return 2;
}
