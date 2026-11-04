# Complete run inventory within the existing job-readback budget

Source repair for [issue #682](https://github.com/ingolf-lohmann/qik-vrt/issues/682),
based on Main `e1ac5f52896b494eb9051f704a42d4554d4b7139`, tree
`22095e5fb54a0e864660b5140829cb0ab78f826a`.

The original Actions run `41759139590`, attempt 1, observed head
`c6083135f3cb2723e849d7b4f9d7dee89898e5c6`. Artifact `13288684528`
has ZIP SHA-256
`8c28964fe5e2ee70e4b822e43fb9ff5f763bfc629d90b9dde097f3a248514971`.
Its original 310-byte `job-readback-budget.json` is retained here as
`job-readback-budget.original.json`. The unchanged legacy CLI policy reproduces
it byte-for-byte with exit 2: 100 returned of 213 reported runs. The failure was
at `JOBS_BUDGET_PREFLIGHT`; deadlock analysis was skipped. No journal gap, CAS
failure or productive runtime defect is inferred from that observation.

`predecessor-regression.txt` records the new three-page regression (trailing whitespace normalized) against the
unmodified predecessor workflow/controller: expected collection success fails
with exit 2. `targeted-tests.txt` records the first candidate c5429262 with 165 passing executions of the repaired
watchdog, executor-contract and seed-workflow tests. The workflow body is actually
executed against isolated REST fixtures, including 213 metadata entries over
three pages and exactly 11 required jobs GETs. This fixture is not a recovered
complete historical 213-run provider snapshot.

The successor paginates all metadata, selects every active run and the latest
run per workflow, retains the 20-request ceiling, verifies complete job responses,
and binds analysis to its exact inventory/plan. Older terminal jobs are explicitly
unobserved. Regression cases retain incomplete-inventory HOLD, 20/21 boundaries,
HTTP403 stop behavior, invalid identities/pages/jobs, and latest-gate decision
parity with a full job-input observation.

Full-suite and native exact-head results must be bound to the final candidate
tree in the PR/CI readback; this directory alone does not claim those effects.
Main integration, original-host HTTPS recovery, authenticated peer execution and
the universal productive-effect thesis remain separate evidence obligations.
`EFFECT_ACK_DONE=false`.

Human requirement and authorization: Ingolf Lohmann.
Implementation and bounded verification: OpenAI Codex.

The combined successor in PR #684 retains source parent
`8fbc9df0107987dff0f4287320f9eb938bbf2f84` from overlapping PR #683,
including its bounded page collectors, numeric ordering, original work unit and
byte-identical `READBACK_AND_TESTS.zip` (SHA-256
`4c29c610cea56a359d84403c8a26c9ade14c3a6241a7012ff7cc0af503b18421`).
It retains the strict inventory-bound analysis and legacy budget policy from
parent `c54292622335b43f112f82dc54e3ef695eaf7653`.

`predecessor-convergence-counterexample.json` records an isolated unknown-job-status
case accepted as READY/SUCCESS by 8fbc9df0. The combined collector rejects it;
the gate evaluator also marks malformed or active jobs untrusted.
`convergence-targeted-tests.txt` records 169 passing targeted executions, including
job continuation pages within a total budget of 20, a ten-page run limit, numeric
latest-run ordering, malformed-list rejection and analysis-time identity drift.
`convergence-replay.json` reruns the archived REST inputs through the combined
source: all 356 metadata entries, four run pages, 13 job pages, analysis reached,
and the real recorded executed-gate failure retained. This is recorded-data replay,
not a fresh provider observation. Final full-suite/native acceptance must refer
to the combined successor; neither predecessor's checks transfer to it.
