/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
/* C90 computation core; this filesystem adapter is explicitly POSIX/Linux.
 * No shell, network, credentials, process executor or automatic payload run. */
#define _POSIX_C_SOURCE 200809L
#include "qikvrt/codec_native.h"
#include "qikvrt/sha256.h"
#include "qikvrt/finite_machine.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <zlib.h>

static int number(const char *s,unsigned long *value)
{
    char *end;
    if(!s[0]||strspn(s,"0123456789")!=strlen(s))return 0;
    errno=0;*value=strtoul(s,&end,10);
    return !errno && !*end && *value<=QIKVRT_NATIVE_LIMIT;
}
static int hash_file(FILE *f,unsigned char hash[32])
{
    unsigned char data[16384];size_t n;qikvrt_sha256 sha;
    qikvrt_sha256_init(&sha);
    while((n=fread(data,1,sizeof(data),f))!=0)qikvrt_sha256_update(&sha,data,n);
    if(ferror(f))return 0;
    qikvrt_sha256_final(&sha,hash);return 1;
}
static int copy_self(FILE *out,const char **error)
{
    FILE *self;
    unsigned char footer[56],buf[16384],hash[32];
    unsigned long offset,length,left;long end;size_t n;
    unsigned int i;
    qikvrt_sha256 sha;
    self=fopen("/proc/self/exe","rb");
    if(!self){*error="LINUX_SELF_IMAGE_UNAVAILABLE";return 0;}
    if(fseek(self,0,SEEK_END)||(end=ftell(self))<56
       ||fseek(self,-56L,SEEK_END)||fread(footer,1,56,self)!=56
       ||memcmp(footer,"QIKSFX1\0",8))goto bad;
    for(i=8;i<12;i++)if(footer[i])goto bad;
    for(i=16;i<20;i++)if(footer[i])goto bad;
    offset=0;length=0;
    for(i=12;i<16;i++)offset=(offset<<8)|footer[i];
    for(i=20;i<24;i++)length=(length<<8)|footer[i];
    if(!offset||length<22||offset>QIKVRT_NATIVE_LIMIT||length>QIKVRT_NATIVE_LIMIT
       ||offset>(unsigned long)end-56||length>(unsigned long)end-56-offset
       ||fseek(self,(long)offset,SEEK_SET))goto bad;
    left=length;qikvrt_sha256_init(&sha);
    while(left) {
        n=left>sizeof(buf)?sizeof(buf):(size_t)left;
        if(fread(buf,1,n,self)!=n)goto bad;
        if(left==length && memcmp(buf,"PK\003\004",4))goto bad;
        qikvrt_sha256_update(&sha,buf,n);
        if(fwrite(buf,1,n,out)!=n)goto bad;
        left-=(unsigned long)n;
    }
    qikvrt_sha256_final(&sha,hash);
    if(memcmp(hash,footer+24,32))goto bad;
    fclose(self);return 1;
bad:
    fclose(self);*error="SELF_EXTRACT_PAYLOAD_MISMATCH";return 0;
}
int main(int argc,char **argv)
{
    FILE *in=0,*out=0;
    const char *error="INVALID_ARGUMENTS",*destination=0;
    char *temporary=0;
    unsigned char hash[32];
    unsigned long block=262144UL,limit=QIKVRT_NATIVE_LIMIT;
    struct stat destination_info;
    unsigned int i;
    int fd=-1,ok=0,level=0,mode=0;
    if(argc==2 && !strcmp(argv[1],"--version")) {
        printf("QIKVRT native codec V1; C90; POSIX/Linux adapter; zlib=%s\n",zlibVersion());
        return 0;
    }
    if(argc==6 && !strcmp(argv[1],"machine")) {
        unsigned long steps,cells;
        if(!number(argv[4],&steps)||!number(argv[5],&cells))goto done;
        in=fopen(argv[2],"rb");
        if(!in){error="INPUT_IO";goto done;}
        ok=qikvrt_binary_machine(in,argv[3],steps,cells,stdout,&error);
        goto done;
    }
    if(argc==3 && !strcmp(argv[1],"sha256")) {
        in=fopen(argv[2],"rb");
        if(!in || !hash_file(in,hash))goto done;
        for(i=0;i<32;i++)printf("%02x",(unsigned int)hash[i]);
        printf("\n");
        if(fflush(stdout)){error="HASH_OUTPUT_IO";goto done;}
        ok=1;goto done;
    }
    if(argc>=5 && argc<=7 && !strcmp(argv[1],"encode")) {
        if(strcmp(argv[2],"raw")&&strcmp(argv[2],"balanced"))goto done;
        level=!strcmp(argv[2],"balanced")?6:0;
        if(argc>=6&&!number(argv[5],&block))goto done;
        if(argc==7&&!number(argv[6],&limit))goto done;
        mode=1;destination=argv[4];in=fopen(argv[3],"rb");
    } else if((argc==4||argc==5)&&!strcmp(argv[1],"decode")) {
        if(argc==5&&!number(argv[4],&limit))goto done;
        mode=2;destination=argv[3];in=fopen(argv[2],"rb");
    } else if(argc==3&&!strcmp(argv[1],"extract")) {
        mode=3;destination=argv[2];
    } else goto done;
    if(mode!=3&&!in){error="INPUT_IO";goto done;}
    if(strlen(destination)>1048576UL){error="OUTPUT_PATH_LIMIT";goto done;}
    if(lstat(destination,&destination_info)==0) {
        if(!S_ISREG(destination_info.st_mode)){error="UNSAFE_OUTPUT_TYPE";goto done;}
    } else if(errno!=ENOENT){error="OUTPUT_PATH_IO";goto done;}
    temporary=(char *)malloc(strlen(destination)+32);
    if(!temporary){error="ALLOCATION_FAILED";goto done;}
    strcpy(temporary,destination);strcat(temporary,".qikvrt-XXXXXX");
    fd=mkstemp(temporary);
    if(fd<0){error="OUTPUT_STAGE_IO";goto done;}
    out=fdopen(fd,"w+b");
    if(!out){close(fd);error="OUTPUT_STAGE_IO";goto done;}
    if(mode==1)ok=qikvrt_codec_encode(in,out,level,block,limit,&error);
    else if(mode==2)ok=qikvrt_codec_decode(in,out,limit,&error);
    else ok=copy_self(out,&error);
    if(!ok)goto done;
    if(in){fclose(in);in=0;}
    if(fflush(out)||fsync(fileno(out))){ok=0;error="OUTPUT_FLUSH_IO";goto done;}
    if(fclose(out)){out=0;ok=0;error="OUTPUT_CLOSE_IO";goto done;}out=0;
    if(rename(temporary,destination)){ok=0;error="OUTPUT_COMMIT_IO";goto done;}
done:
    if(in)fclose(in);
    if(out)fclose(out);
    if(temporary){if(!ok)unlink(temporary);free(temporary);}
    if(!ok)fprintf(stderr,"QIKVRT_NATIVE_BLOCK: %s\n",error);
    return ok?0:2;
}
