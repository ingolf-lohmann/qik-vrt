/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
/* Reuse the existing independently restated C oracle, not a new RTL oracle. */
#define main effect_ack_reference_main
#include "test_effect_ack_core.c"
#undef main

int main(void)
{
    unsigned long mask;
    int decision;
    qikvrt_effect_ack_input input;
    for (mask = 0UL; mask < (1UL << 19); mask += 1UL) {
        for (decision = 0; decision < 5; decision += 1) {
            input = input_from_mask(mask, (qikvrt_effect_ack_decision)decision);
            (void)printf("%lu %d %d\n", mask, decision,
                (int)expected_state_oracle(&input));
        }
    }
    return 0;
}
