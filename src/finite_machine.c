/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#include "qikvrt/finite_machine.h"
#include <stdlib.h>
#include <string.h>

typedef struct cell {
    struct cell *left,*right;
    unsigned char bit;
} cell;
typedef struct {
    unsigned int next;
    unsigned char write,move;
} transition;

static cell *new_cell(unsigned char bit)
{
    cell *c=(cell *)malloc(sizeof(cell));
    if(c){c->left=0;c->right=0;c->bit=bit;}
    return c;
}
int qikvrt_binary_machine(FILE *program,const char *input,unsigned long max_steps,
                          unsigned long max_cells,FILE *output,const char **error)
{
    unsigned char header[10],record[4];
    transition *table=0,t;
    unsigned int states,state=0;
    unsigned long i,count=0,steps=0;
    size_t length=strlen(input);
    long position=0;
    cell *left=0,*head=0,*tail=0,*next;
    int ok=0;
#define FAIL_MACHINE(s) do{*error=(s);goto done;}while(0)
    if(max_steps>10000000UL||!max_cells||max_cells>1000000UL
       ||length>max_cells||strspn(input,"01")!=length)
        FAIL_MACHINE("MACHINE_INPUT_OR_BUDGET_INVALID");
    if(fread(header,1,10,program)!=10||memcmp(header,"QIKTM01\0",8))
        FAIL_MACHINE("MACHINE_HEADER_INVALID");
    states=((unsigned int)header[8]<<8)|header[9];
    if(!states||states>4096)FAIL_MACHINE("MACHINE_STATE_LIMIT");
    table=(transition *)malloc((size_t)states*2*sizeof(*table));
    if(!table)FAIL_MACHINE("ALLOCATION_FAILED");
    for(i=0;i<(unsigned long)states*2;i++) {
        if(fread(record,1,4,program)!=4)FAIL_MACHINE("MACHINE_PROGRAM_TRUNCATED");
        table[i].next=((unsigned int)record[0]<<8)|record[1];
        table[i].write=record[2];table[i].move=record[3];
        if((table[i].next!=65535U&&table[i].next>=states)
           ||record[2]>1||record[3]>2)FAIL_MACHINE("MACHINE_TRANSITION_INVALID");
    }
    if(fgetc(program)!=EOF||ferror(program))FAIL_MACHINE("MACHINE_TRAILING_OR_IO");
    for(i=0;i<(length?length:1);i++) {
        next=new_cell(length?(unsigned char)(input[i]-'0'):0);
        if(!next)FAIL_MACHINE("ALLOCATION_FAILED");
        if(tail){tail->right=next;next->left=tail;}else left=next;
        tail=next;count++;
    }
    head=left;
    while(state!=65535U) {
        if(steps>=max_steps)FAIL_MACHINE("MACHINE_STEP_BUDGET_EXCEEDED");
        t=table[(unsigned long)state*2+head->bit];
        head->bit=t.write;
        if(t.move!=1) {
            next=t.move?head->right:head->left;
            if(!next) {
                if(count>=max_cells)FAIL_MACHINE("MACHINE_CELL_BUDGET_EXCEEDED");
                next=new_cell(0);if(!next)FAIL_MACHINE("ALLOCATION_FAILED");
                if(t.move){head->right=next;next->left=head;}
                else {head->left=next;next->right=head;left=next;}
                count++;
            }
            head=next;position+=t.move?1:-1;
        }
        state=t.next;steps++;
    }
    if(fprintf(output,"{\"schema\":\"qikvrt-binary-machine-result/v1\",\"state\":65535,\"steps\":%lu,\"head\":%ld,\"cells\":%lu,\"tape\":\"",steps,position,count)<0)
        FAIL_MACHINE("MACHINE_OUTPUT_IO");
    for(head=left;head;head=head->right)if(fputc('0'+head->bit,output)==EOF)
        FAIL_MACHINE("MACHINE_OUTPUT_IO");
    if(fputs("\"}\n",output)==EOF||fflush(output))FAIL_MACHINE("MACHINE_OUTPUT_IO");
    ok=1;
done:
    while(left){next=left->right;free(left);left=next;}
    free(table);return ok;
#undef FAIL_MACHINE
}
