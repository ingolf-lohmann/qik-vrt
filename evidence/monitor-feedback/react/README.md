<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann. Documentation contribution: OpenAI Codex. -->

# React source successor: captured Authority HTTP 404

This delta targets `docs/monitor/mesh-react.js` in PR #476, starting at commit
`b9e03ef678f1304c6cada3cfc37b311b7faea5b9`, tree
`29f40e2318869f107d4688d3b5401a2e5c1b0633`. Its draft base remains that
candidate branch. No #468/#474 merge, main integration or public delivery is
performed by this source successor.

The semantic reference is #468 at
`a4dc05c1fcef9390538a664eba75899f3a649582`. Only its captured HTTP observation
is copied as an input, byte for byte: Git blob
`d2263805ead86bc88192a502ed85b6462c435413`, SHA-256
`7fe62ee41e0fa286ce515dca1bd0decb48fe2f8315c0d8f3c30c03285f488eec`.
Neither its passing tests nor storage, Origin, self-host or deployment evidence
is transferred. The baseline React source is also preserved byte for byte:
blob `d0a3232ec1353a4a00e8a4ae958470985120637e`, SHA-256
`8e250ad9c3c256ab5ab154bdc055b70ee0f33e300d5650ca16a1c6900c80bfe9`.

## What is rendered

The `/mesh` and scoped `/node` routes now render the repository source error
instead of an unqualified availability code. Failed terminal REST requests use
the same feedback component. Six labels expose the five explanation groups
from #468; actor and next step are displayed separately:

| Group | Authority-404 feedback |
| --- | --- |
| State | The requested source is currently unreadable. |
| Impact | No complete repository/workflow state; no inference about node runtime. |
| Observed status and uncertainty | HTTP 404; absent source versus inaccessible source is unresolved. |
| Actor and next REST step | Repository maintainers check the exact endpoint and read access, then manually renew the readback. |
| Repair progress | No repair start is evidenced by this monitor. |

Native `details`/`summary` retains a focusable, selectable JSON diagnostic.
Original error, actual bound HTTP status, endpoint, observation time, provider
request ID, quota/reset/retry headers and optional captured response remain
available. Missing fields stay null. The production observer's existing
shorter error contract is supported without inventing headers or a response.
Credential redaction is applied to individual strings before JSON serialization;
redaction does not corrupt the diagnostic's JSON syntax. Provider text is passed
as React text, never as markup.

Successful REST siblings are processed even when `/api/activity` fails.
Earlier source data is explicitly stale while a read fails. A successful
activity snapshot cannot erase a failed runtime readback. The inherited age
clock and event stream remain; this delta adds no scheduler, polling request,
automatic provider retry, credential input or repair executor.

## Reproduce the comparison

Use the already declared Node 24 and repository React 19.2.6 bundle:

```sh
python3 -B tools/qikvrt_tool_cache.py verify
node --test docs/monitor/react-feedback.test.mjs
node docs/monitor/react-feedback.test.mjs --feedback-report /tmp/react-authority-404.json
make repository-monitor-test
```

The report is `authority-404-before-after.json`. The test rejects drift in that
report, the emitter, the baseline blob or the exact observation digest. The
same captured provider status, text and headers are projected into a controlled
`repositories[].sources.branch` input for both actual React source emitters.
The existing `client-replica.js` independently accepts a digest-bound synthetic
activity envelope. Synthetic sibling and runtime responses are identical.
No S1/SQLite/storage system executes in this test; the file-view component is
an explicit inert placeholder.

The structural coverage is **0/5 to 5/5**. Both sides issue three identical
terminal GET requests and establish one controlled event stream. The tests
use the existing real React `createElement` with controlled hooks, timers and
I/O in Node vm; they do not use ReactDOM, a browser DOM or human participants.

Fourteen focused tests cover the exact replay, evidence drift, node/mesh
projection, cause/actor/progress boundaries, the observer-native error shape,
successful sibling isolation, multiple independent HTTP failures, 403 rate
limits, network/JSON failures, stale data and recovery, independent runtime
failure retention, malformed stream data, credential redaction/text safety,
unchanged workflow machine status, root preparation and offline no-fetch.
They run through the existing monitor test target and package script; no new
pipeline or dependency is introduced.

## Evidence limits

**Human comprehension: NOT_MEASURED, zero participants.** Understanding rates,
clarification counts and response times remain null. Automated field coverage
is not a measured improvement in human understanding. ReactDOM interaction,
screenreader and real-device checks are not established by this replay.

The cause of the provider 404 and a runtime repair remain unproved. Existing
storage/component links on the entry page are historical source content, not
acceptance evidence for this delta. Its parent remains a candidate dependency.
Main integration, native review, public delivery, all-node propagation and
general EFFECT_ACK_DONE require their own fresh evidence.

Provenance: `state/work_units/REACT_AUTHORITY404_FEEDBACK_20261006_V1.json`.
