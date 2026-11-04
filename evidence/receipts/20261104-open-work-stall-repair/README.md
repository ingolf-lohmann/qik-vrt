# Open-work stall repair: source-bound evidence

Owner: Ingolf Lohmann. Requirement/authorization: current chat, 4 November 2026;
exact original wording and SHA-256 retained in the existing watchdog work unit.
Implementation and isolated verification: OpenAI Codex.

The frozen predecessor is ed22c8ab5bf8d963d2718f43192f4e7320424f6f,
tree ecb6ca0ca7f71de87a66b5f78135972e8f5a338e, existing PR #686.
before-after.json re-executes that unchanged predecessor and the candidate with
the same isolated inputs: the old code remains SAFE_PROGRESS after four
five-minute observations without a useful transition, and calls an inactive
runner quiescent without reading open work. The candidate detects both cases.

watchdog-tests.txt: 52 passed. continuation-tests.txt: 49 passed.
The tests include the actual consumer shell, original admission/readback guard,
malicious analysis text retained as data, wrong producer binding, bounded open
work pagination, missing/stale inventory, observer failure, cumulative progress,
identical retry and a newly executed step. Both YAML files parse and all ten
embedded Bash blocks pass syntax checking. source-checks.json binds exact bytes.

These are local, isolated source checks. The working snapshot is partial; full
make test was not run here. Native full CI and governance must run on the actual
new commit; no predecessor result is promoted to native exact-head acceptance.
No host, DNS, TLS, publication or productive EFFECT_ACK effect is asserted.

Integrity metadata is updated incrementally from the exact predecessor manifest
Git blob 6d43db120884a3b3e3b157176ad097f8c3e37f3f. Unchanged entries retain their
source-bound digests. Changed/new files are hashed from their actual bytes using
the unchanged generator's classifications and content-tree definition; counts,
the complete index and detached manifest digest are regenerated canonically.
This does not claim a fresh local hash of absent unchanged files. The native
integrity verifier must independently verify the complete checkout.
