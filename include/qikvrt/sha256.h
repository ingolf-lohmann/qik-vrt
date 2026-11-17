/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_SHA256_H
#define QIKVRT_SHA256_H
#include <stddef.h>
typedef struct {
    unsigned long state[8], bytes_lo, bytes_hi;
    unsigned char block[64];
    size_t used;
} qikvrt_sha256;
void qikvrt_sha256_init(qikvrt_sha256 *s);
void qikvrt_sha256_update(qikvrt_sha256 *s, const void *data, size_t count);
void qikvrt_sha256_final(qikvrt_sha256 *s, unsigned char digest[32]);
#endif
