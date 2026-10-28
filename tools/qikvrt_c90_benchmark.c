/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. */
#include <errno.h>
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "qikvrt/fixed_q16.h"

static int vectors(void)
{
    char line[160], op, *at, *end;
    long a, b, result;
    qikvrt_q16_status status;
    while (fgets(line, sizeof(line), stdin) != 0) {
        at = line;
        while (isspace((unsigned char)*at)) {
            ++at;
        }
        op = *at++;
        if (strchr(line, '\n') == 0 || (op != 'A' && op != 'M')
            || !isspace((unsigned char)*at)) {
            return 2;
        }
        errno = 0;
        a = strtol(at, &end, 10);
        if (errno != 0 || end == at || !isspace((unsigned char)*end)) {
            return 2;
        }
        at = end;
        errno = 0;
        b = strtol(at, &end, 10);
        if (errno != 0 || end == at) {
            return 2;
        }
        while (isspace((unsigned char)*end)) {
            ++end;
        }
        if (*end != '\0') {
            return 2;
        }
        result = 12345L;
        status = op == 'A' ? qikvrt_q16_add(a, b, &result)
                           : qikvrt_q16_mul(a, b, &result);
        if (printf("%d %ld\n", (int)status, result) < 0) {
            return 3;
        }
    }
    return ferror(stdin) ? 3 : 0;
}

int main(int argc, char **argv)
{
    unsigned long count, i, checksum;
    char *end;
    long a, b, c, product, result;
    clock_t start, finish;
    if (argc == 2 && strcmp(argv[1], "--vectors") == 0) {
        return vectors();
    }
    if (argc != 2) {
        return 2;
    }
    errno = 0;
    count = strtoul(argv[1], &end, 10);
    if (errno != 0 || *end != '\0' || argv[1][0] < '0'
        || argv[1][0] > '9' || count < 1UL || count > 100000000UL) {
        return 2;
    }
    checksum = 0UL;
    start = clock();
    if (start == (clock_t)-1) {
        return 4;
    }
    for (i = 0UL; i < count; ++i) {
        a = (long)(i & 65535UL);
        b = (long)((i * 251UL + 17UL) & 65535UL);
        c = (long)((i * 17UL) & 65535UL) - 32768L;
        if (qikvrt_q16_mul(a, b, &product) != QIKVRT_Q16_OK
            || qikvrt_q16_add(product, c, &result) != QIKVRT_Q16_OK) {
            return 5;
        }
        checksum = (checksum + (unsigned long)result) & 4294967295UL;
    }
    finish = clock();
    if (finish == (clock_t)-1 || finish <= start) {
        return 4;
    }
    printf("{\"iterations\":%lu,\"checksum\":%lu,\"clock_ticks\":%lu,"
           "\"clocks_per_second\":%lu}\n", count, checksum,
           (unsigned long)(finish - start), (unsigned long)CLOCKS_PER_SEC);
    return ferror(stdout) ? 3 : 0;
}
