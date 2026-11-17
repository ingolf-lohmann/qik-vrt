/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex. */
#ifndef QIKVRT_FINITE_MACHINE_H
#define QIKVRT_FINITE_MACHINE_H
#include <stdio.h>
/* Side-effect-free, resource-bounded binary Turing-table reference profile.
 * Output is emitted only after HALT; neither host execution nor Mesh admission. */
int qikvrt_binary_machine(FILE *,const char *,unsigned long,unsigned long,FILE *,const char **);
#endif
