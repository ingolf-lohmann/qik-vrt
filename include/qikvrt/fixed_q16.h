/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation contribution: OpenAI Codex. */
#ifndef QIKVRT_FIXED_Q16_H
#define QIKVRT_FIXED_Q16_H

/* Raw signed Q16.16 values. A long may be wider, but the value range is fixed. */
#define QIKVRT_Q16_MIN (-2147483647L - 1L)
#define QIKVRT_Q16_MAX 2147483647L
#define QIKVRT_Q16_ONE 65536L

typedef enum qikvrt_q16_status {
    QIKVRT_Q16_OK = 0,
    QIKVRT_Q16_INVALID_ARGUMENT = 1,
    QIKVRT_Q16_OVERFLOW = 2
} qikvrt_q16_status;

/* Failures leave *result unchanged. Multiplication truncates toward zero.
 * No floating point, signed overflow, signed shift or 64-bit type is needed.
 * These are arithmetic operations, not authorization or an EFFECT_ACK gate.
 */
qikvrt_q16_status qikvrt_q16_add(long a, long b, long *result);
qikvrt_q16_status qikvrt_q16_mul(long a, long b, long *result);

#endif
