/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * Copyright 2026 Ingolf Lohmann. C90 isolated admission reducer.
 * Not a productive EAP carrier or VPN endpoint. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#define QIK_MAX 128
#define QIK_DIGEST 64
struct qik_state { unsigned long sequence; char digest[QIK_DIGEST+1]; int observed; int acknowledged; };
static int hex64(const char *p) { int i; if (strlen(p)!=QIK_DIGEST) return 0; for(i=0;i<QIK_DIGEST;i++) if(!((p[i]>='0'&&p[i]<='9')||(p[i]>='a'&&p[i]<='f'))) return 0; return 1; }
static int step(struct qik_state *s,const char *op,const char *digest) {
 if (!hex64(digest)) return 0;
 if(strcmp(op,"PROPOSE")==0) { if(s->digest[0]!=0 || s->observed || s->acknowledged) return 0; strcpy(s->digest,digest); s->sequence++; return 1; }
 if(strcmp(op,"OBSERVE")==0) { if(s->digest[0]==0 || strcmp(s->digest,digest)!=0 || s->observed) return 0; s->observed=1; s->sequence++; return 1; }
 if(strcmp(op,"ACKNOWLEDGE")==0) { if(!s->observed || s->acknowledged || strcmp(s->digest,digest)!=0) return 0; s->acknowledged=1; s->sequence++; return 1; }
 return 0;
}
int main(void) {
 struct qik_state s; char line[QIK_MAX],op[32],digest[QIK_DIGEST+1],extra[2]; int n;
 memset(&s,0,sizeof(s));
 while(fgets(line,sizeof(line),stdin)!=NULL) {
  if(strchr(line,'\n')==NULL && !feof(stdin)) { int c; while((c=getchar())!='\n'&&c!=EOF) {} puts("REJECT oversized"); continue; }
  n=sscanf(line,"%31s %64s %1s",op,digest,extra);
  if(n!=2 || !step(&s,op,digest)) { puts("REJECT"); continue; }
  printf("ACCEPT %lu %s\n",s.sequence,op);
 }
 printf("STATE %lu %d %d\n",s.sequence,s.observed,s.acknowledged);
 return 0;
}
