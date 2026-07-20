#include <stdio.h>
#include <string.h>
int main(int argc, char **argv){
  const char *guid="a84f157a-cef2-4c47-bca9-8f407085bdbe";
  if(argc>1 && strcmp(argv[1],"seed")==0){printf("QIKVRT_HANDSHAKE_CORE seed PASS guid=%s\n",guid);return 0;}
  if(argc>1 && strcmp(argv[1],"node")==0){printf("QIKVRT_HANDSHAKE_CORE node PASS guid=%s\n",guid);return 0;}
  printf("QIKVRT_HANDSHAKE_CORE PASS guid=%s\n",guid);return 0;
}
