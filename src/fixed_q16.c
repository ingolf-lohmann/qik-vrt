/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. */
#include "qikvrt/fixed_q16.h"

static int raw_valid(long value)
{
    return value >= QIKVRT_Q16_MIN && value <= QIKVRT_Q16_MAX;
}

static unsigned long magnitude(long value)
{
    /* Also valid for the most negative long on a 32-bit implementation. */
    return value < 0L ? (unsigned long)(-(value + 1L)) + 1UL
                     : (unsigned long)value;
}

qikvrt_q16_status qikvrt_q16_add(long a, long b, long *result)
{
    if (result == 0) {
        return QIKVRT_Q16_INVALID_ARGUMENT;
    }
    if (!raw_valid(a) || !raw_valid(b)
        || (b > 0L && a > QIKVRT_Q16_MAX - b)
        || (b < 0L && a < QIKVRT_Q16_MIN - b)) {
        return QIKVRT_Q16_OVERFLOW;
    }
    *result = a + b;
    return QIKVRT_Q16_OK;
}

qikvrt_q16_status qikvrt_q16_mul(long a, long b, long *result)
{
    unsigned long x, y, x0, x1, y0, y1, limit, high, value, term;
    int negative;

    if (result == 0) {
        return QIKVRT_Q16_INVALID_ARGUMENT;
    }
    if (!raw_valid(a) || !raw_valid(b)) {
        return QIKVRT_Q16_OVERFLOW;
    }
    negative = (a < 0L) != (b < 0L);
    x = magnitude(a);
    y = magnitude(b);
    x0 = x & 65535UL;
    x1 = x >> 16;
    y0 = y & 65535UL;
    y1 = y >> 16;
    limit = negative ? 2147483648UL : 2147483647UL;

    /* floor(|a*b| / 2^16), with each partial product within unsigned long.
     * Guard every accumulation before it can exceed the semantic limit.
     */
    high = x1 * y1;
    if (high > (limit >> 16)) {
        return QIKVRT_Q16_OVERFLOW;
    }
    value = high << 16;
    term = x1 * y0;
    if (term > limit - value) {
        return QIKVRT_Q16_OVERFLOW;
    }
    value += term;
    term = x0 * y1;
    if (term > limit - value) {
        return QIKVRT_Q16_OVERFLOW;
    }
    value += term;
    term = (x0 * y0) >> 16;
    if (term > limit - value) {
        return QIKVRT_Q16_OVERFLOW;
    }
    value += term;

    if (negative && value == 2147483648UL) {
        *result = QIKVRT_Q16_MIN;
    } else {
        *result = negative ? -(long)value : (long)value;
    }
    return QIKVRT_Q16_OK;
}
