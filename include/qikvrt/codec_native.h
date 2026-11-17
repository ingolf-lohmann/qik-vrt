/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_CODEC_NATIVE_H
#define QIKVRT_CODEC_NATIVE_H
#include <stdio.h>
/* Existing QIKVRTC V1 wire contract. Caller stages the sink until success.
 * This portable profile has an explicit 2^31-1 byte total-output ceiling.
 * level=0 selects RAW, level=6 selects the existing balanced zlib profile. */
#define QIKVRT_NATIVE_LIMIT 2147483647UL
int qikvrt_codec_encode(FILE *,FILE *,int,unsigned long,unsigned long,const char **);
int qikvrt_codec_decode(FILE *,FILE *,unsigned long,const char **);
#endif
