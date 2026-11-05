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

watchdog-tests.txt: 55 passed. continuation-tests.txt: 49 passed.
frozen-apt-tests.txt: 8 passed. specification-tests.txt: 23 passed. Total: 135 targeted tests. A 24-case matrix
checks that open work never permits silent idle. The original Docker RUN shell
was executed with isolated APT/dpkg fixtures: valid input proceeds; update,
plan, byte and installed-version faults stop at their actual boundary. Eight
real official Debian archives were independently size/SHA256 checked.
apt-transport-repair.json preserves the two distinct native failures and their
causal transport correction. Parent a000c5fe native S1 and core jobs succeeded;
its 769740368-byte combined artifact exceeds the existing readback limit.
The successor invokes these guard cases from the existing native Make target
and preserves unchanged original carrier and new image in separate artifacts.
The native observer also exposed a client scope omission after its 22-request
budget HOLD causally recovered to 20. An unchanged original client rejects the
same bound retry input; the successor admits only the pinned read-only verifier
and rejects wrong source, attempt, workflow, recipe, approval, unchanged/bad
budget and productive/current-specification substitutions. The original budget
and all full-currentness publication/deployment gates remain intact.
The next native attempt encountered installation rate403 at BASELINE_READBACK.
A later exact-subject successful GITHUB_TOKEN carrier API step provides a
bounded read-only retry prerequisite; it does not accept the failed observer.
The client now checks original failed attempt/log/receipt, later successful
native run/job/mandatory carrier step, frozen CI/carrier sources, one-hour
freshness and the unchanged complete job budget. Wrong or stale evidence and
all productive/currentness substitutions remain denied. Its D3 predecessor
rejects the identical real recovery input. D3 S1 artifact and OCI bytes were
independently read and every referenced OCI blob/source label verified.
Native exact-head acceptance and independent byte readback must run anew.
All 43 Bash blocks of the modified CI workflow pass syntax checking.
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
