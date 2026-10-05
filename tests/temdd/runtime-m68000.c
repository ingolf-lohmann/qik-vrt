/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
 * TEMDD v0.1 executable M68000 backend differential test. */
#include <stdio.h>
#include <limits.h>
extern int temdd_transition_call(int event);
int main(void) {
    int event;
    for (event = 0; event < 512; ++event) {
        int expected = event == 1 ? 1 : (event == 2 ? 2 : 0);
        int observed = temdd_transition_call(event);
        if (observed != expected) return 1;
    }
    if (temdd_transition_call(-1) != 0 || temdd_transition_call(INT_MIN) != 0 ||
        temdd_transition_call(INT_MAX) != 0) return 2;
    puts("TEMDD_M68000_EXECUTED vectors=515");
    return 0;
}
