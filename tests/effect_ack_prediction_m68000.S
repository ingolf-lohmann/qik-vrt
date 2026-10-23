/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Linux m68k syscall ABI for QEMU user emulation; no guest libc or Atari ROM. */
    .text
    .globl _start
    .type _start,@function
_start:
    jsr main
    move.l %d0,%d1
    moveq #1,%d0
    trap #0

    .globl qikvrt_prediction_write
    .type qikvrt_prediction_write,@function
qikvrt_prediction_write:
    movem.l %d2-%d3,-(%sp)
    move.l 12(%sp),%d2
    move.l 16(%sp),%d3
    moveq #1,%d1
    moveq #4,%d0
    trap #0
    movem.l (%sp)+,%d2-%d3
    rts
    .section .note.GNU-stack,"",@progbits
