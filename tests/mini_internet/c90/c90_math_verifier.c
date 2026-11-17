/* ISO C90 finite-state refinement checker; NOT a Lean proof checker.
 * Input: n (1..256), forward[n], backward[n], schedule[n], inverse_schedule[n].
 * Checks two-sided inverse and schedule bijection; then verifies that
 * consolidation of the distributed forward computation equals sequential.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX_STATES 256
static int read_value(FILE *f, int n, int *v) {
    long x;
    if (fscanf(f, "%ld", &x) != 1 || x < 0 || x >= n) return 0;
    *v = (int)x;
    return 1;
}
static int read_map(FILE *f, int n, int *a) {
    int i;
    for (i = 0; i < n; ++i) if (!read_value(f, n, &a[i])) return 0;
    return 1;
}
static int verify(int n, const int *f, const int *b, const int *s, const int *t) {
    int i, arrival, original;
    for (i = 0; i < n; ++i) {
        if (b[f[i]] != i || f[b[i]] != i) return 0;
        if (t[s[i]] != i || s[t[i]] != i) return 0;
    }
    for (original = 0; original < n; ++original) {
        arrival = t[original];
        if (f[s[arrival]] != f[original]) return 0;
        if (b[f[s[arrival]]] != original) return 0;
    }
    return 1;
}
static int selftest(void) {
    int f[3] = {1,2,0}, b[3] = {2,0,1};
    int s[3] = {2,0,1}, t[3] = {1,2,0};
    if (!verify(3,f,b,s,t)) return 1;
    b[0] = 0;
    if (verify(3,f,b,s,t)) return 2;
    b[0] = 2;
    s[1] = 2;
    if (verify(3,f,b,s,t)) return 3;
    return 0;
}
int main(int argc, char **argv) {
    FILE *in;
    int n, f[MAX_STATES], b[MAX_STATES], s[MAX_STATES], t[MAX_STATES];
    int extra;
    if (argc == 2 && strcmp(argv[1], "--selftest") == 0) {
        if (selftest() != 0) { fputs("SELFTEST FAIL\n",stderr); return 1; }
        puts("SELFTEST PASS"); return 0;
    }
    if (argc != 2) { fputs("usage: c90_math_verifier certificate.txt\n",stderr); return 2; }
    in = fopen(argv[1], "r");
    if (!in) { perror("certificate"); return 2; }
    if (fscanf(in,"%d",&n) != 1 || n < 1 || n > MAX_STATES ||
        !read_map(in,n,f) || !read_map(in,n,b) ||
        !read_map(in,n,s) || !read_map(in,n,t) ||
        fscanf(in,"%d",&extra) == 1) {
        fclose(in); fputs("REJECT malformed certificate\n",stderr); return 1;
    }
    fclose(in);
    if (!verify(n,f,b,s,t)) { fputs("REJECT inverse/consolidation\n",stderr); return 1; }
    puts("VERIFIED finite-state reversible consolidation (NOT Lean proof)");
    return 0;
}
