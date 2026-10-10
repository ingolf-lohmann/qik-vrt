<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0
     Copyright 2026 Ingolf Lohmann. Documentation contribution: OpenAI Codex. -->

# First monitor feedback implementation: Authority HTTP 404

The observed case is a public, credential-free GET of
`https://api.github.com/repos/Goldkelch/qik-vrt` on 6 October 2026 at
17:17:52.884228 UTC. The response is HTTP 404, with provider request ID
`4FA4:3818E4:63C8922:145808DE:6AC52D40`. This establishes an unreadable
source for that request. It does not establish deletion, account suspension,
missing credentials, a failed node runtime, or the provider's underlying cause.

## Exact baseline and changed runtime

`baseline-index.html` is the unchanged source from PR #468 HEAD
`cf5e10162c946df70d5d8547d58ad311ac29a0b3`, TREE
`1ae1a72040364dc2c0aa62925b6774685f508b9d`, Git blob
`0e3f2303c0bab85ca40faf9922514e031e7bd2b6`. Its original licensing follows
the source repository's per-file authorities; retaining these bytes creates
no new grant.

The executed emitter is the existing `docs/monitor/index.html`. Both that
PR head and the reobserved `main` (`79ddba3b6d0970203053b2719c41e9410276741c`)
contain this HTML monitor. `docs/monitor/mesh-react.js` belongs to the separate
React candidate line and is absent from both trees. This first implementation
therefore improves an executable existing monitor without importing the
unrelated storage, self-hosting, Origin, or React candidate stack. React
adoption and the deployed public Mesh Monitor are separate open scopes.

## Comparable before and after

The captured HTTP status, status text and headers are replayed through the
actual inline JavaScript from both HTML files. Successful sibling responses
are synthetic, identical on both sides, and explicitly not live node evidence.

| Dimension | Before | After |
| --- | --- | --- |
| Visible error | `404 Not Found; remaining=56` | The source is currently unreadable; the Repository readback remains open. |
| Impact | No explanation; a failed repository prevents rendering its successful sibling. | No complete fresh Repository/workflow state; the successful sibling remains visible. No runtime state is inferred. |
| Cause | No explanation. | HTTP 404 observed; missing source versus visibility/access remains unknown. |
| Next action | None. | Repository maintainers check the exact REST address and read access; refresh after resolving the obstacle. |
| Repair progress | None. | No repair start is evidenced by this monitor. |
| Diagnostics | Status/status text/quota in raw text. | Original message, status, source URL, method, observation time, provider request ID and quota/retry headers in native, copyable details. |

The deterministic comparison is `authority-404-before-after.json`. It binds
the source digests, capture digest, emitted messages and diagnostics. The
existing test module also rejects a stale comparison after an emitter changes.

Reproduce without network or package installation, using the declared Node
24 runtime and Python test runner:

```sh
python3 -B tools/qikvrt_tool_cache.py verify
python3 -B tests/test_human_machine_interface_adaptation.py --feedback-report /tmp/qikvrt-feedback-comparison.json
python3 -B -m unittest -v tests.test_human_machine_interface_adaptation
make test
```

Existing CI provisions Node 24 through the existing locked setup-node action
and executes this module through `ai-runtime-contract`. There is no added
pipeline, scheduler, npm package or browser dependency.

## Runtime validation and measurement are distinct

The automated structural measure changes from **0/5 to 5/5 explicitly present
explanation fields**. The original error and technical bindings survive.
Both sides issue eight identical GETs in the replay. Failure isolation improves:
the successful sibling is rendered after the change. These are emitter and
diagnostic measurements, not human comprehension measurements.

The 13 monitor regression tests cover the real 404 replay, rate-limited and
non-rate-limited 403, 401, 429, 502, network failures, JSON/shape failures,
simultaneous request failures, stale-data retention, recovery, deduplication,
concurrent refresh, secret redaction, escaped markup, credential separation,
unchanged workflow machine states, and byte-bound evidence. Seven existing
interface-policy tests remain in the same module (20 tests total).

**Human comprehension is NOT_MEASURED: zero participants.** Understanding
rates, clarification counts and time to identify the next action remain null.
No readability score or modeled reviewer answer is used as participant data.
The evaluation matrix and the work unit retain this boundary separately from
`runtime_feedback_changes_implemented=true` for this candidate HTML surface.

A subsequent human comparison must use the same captured case and record
participant attribution/consent, presentation order, language and method.
Ask the participant to identify (1) the observed state, (2) its impact,
(3) whether the cause is known, (4) the next action and actor, and (5) whether
a repair actually started. Record the actual responses, any clarification
requests, and measured response times. Keep uncertain answers and order effects;
a single participant is only a bounded observation, not population evidence.

## Remaining boundaries

The HTML uses native `details`/`summary`, a focusable diagnostic block and a
polite status region. Automated execution verifies emitted markup and text;
it does not establish keyboard, screenreader or real-device conformance.
A local headless browser launch was unavailable because the environment had
no corresponding browser executable. Browser interaction verification remains
open; no cloud-browser session or login was used.

The runtime fault behind the provider's 404 is not repaired by changing its
presentation. Main integration, native human review, deployment, React
projection, all-node propagation and EFFECT_ACK_DONE are not established.
The old head's remote checks are historical; the new head requires its own
remote readback. See the bound work unit
`state/work_units/MONITOR_HTTP404_HUMAN_FEEDBACK_20261006_V1.json`.
