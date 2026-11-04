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
with exit 2. `targeted-tests.txt` records 165 passing executions of the repaired
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
