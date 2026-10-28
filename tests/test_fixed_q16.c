/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. */
#include <assert.h>
#include <limits.h>
#include "qikvrt/fixed_q16.h"

int main(void)
{
    long result;
    result = 12345L;
    assert(qikvrt_q16_mul(98304L, -32768L, &result) == QIKVRT_Q16_OK);
    assert(result == -49152L);
    assert(qikvrt_q16_mul(-1L, 1L, &result) == QIKVRT_Q16_OK);
    assert(result == 0L);
    assert(qikvrt_q16_mul(QIKVRT_Q16_MIN, QIKVRT_Q16_ONE, &result)
           == QIKVRT_Q16_OK);
    assert(result == QIKVRT_Q16_MIN);
    assert(qikvrt_q16_mul(QIKVRT_Q16_MAX, QIKVRT_Q16_ONE, &result)
           == QIKVRT_Q16_OK);
    assert(result == QIKVRT_Q16_MAX);
    result = 12345L;
    assert(qikvrt_q16_mul(QIKVRT_Q16_MIN, -QIKVRT_Q16_ONE, &result)
           == QIKVRT_Q16_OVERFLOW);
    assert(result == 12345L);
    assert(qikvrt_q16_add(QIKVRT_Q16_MAX, 1L, &result)
           == QIKVRT_Q16_OVERFLOW);
    assert(result == 12345L);
    assert(qikvrt_q16_add(QIKVRT_Q16_MIN, -1L, &result)
           == QIKVRT_Q16_OVERFLOW);
    assert(result == 12345L);
    assert(qikvrt_q16_add(QIKVRT_Q16_MIN, QIKVRT_Q16_MAX, &result)
           == QIKVRT_Q16_OK);
    assert(result == -1L);
    assert(qikvrt_q16_add(0L, 0L, 0) == QIKVRT_Q16_INVALID_ARGUMENT);
    assert(qikvrt_q16_mul(0L, 0L, 0) == QIKVRT_Q16_INVALID_ARGUMENT);
#if LONG_MAX > 2147483647L
    result = 12345L;
    assert(qikvrt_q16_mul(2147483648L, 0L, &result)
           == QIKVRT_Q16_OVERFLOW);
    assert(qikvrt_q16_add(0L, -2147483649L, &result)
           == QIKVRT_Q16_OVERFLOW);
    assert(result == 12345L);
#endif
    return 0;
}
