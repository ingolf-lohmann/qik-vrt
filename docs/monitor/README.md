<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0; Copyright 2026 Ingolf Lohmann. -->
# React monitor integration from PR #482

The initial integration was a linear successor of `main`
`71f8c15319bf79456ac177d80941b4f59d372996`.
It reuses only the dependencies needed by the monitor portion of #476, then
applies equivalent source changes from the two #482 commits. Neither original
branch is merged or retargeted. The existing `index.html` remains available.

| Dependency inspected on #476 | Integration decision | Reason |
| --- | --- | --- |
| `mesh-react.js` | Monitor App and formatting helpers only | `/mesh` and `/node` feedback rendering and existing readback contract |
| `client-replica.js` | Exact source bytes | Snapshot digest, version, ordering and event acceptance |
| `react-runtime.js`, `REACT_LICENSE.txt`, React lock | Exact bundle/license; lock relocated here | Actual React 19.2.6 / ReactDOM 19.2.6 / Scheduler 0.27.0 with production-source digest checks |
| `index-react.html`, `mesh-react.css` | Static resource paths and monitor CSS only | Complete renderable local resource closure without storage assets |
| PersonalEntry, Origin, SQLite, mesh-file codec/client/store/view | Excluded | Personal onboarding and file access are separate scopes, not prerequisites of feedback |
| Self-Host packaging, native runtime, providers, deployment and supervisors | Excluded | They are not part of the requested React source integration |
| #476/#482 receipts, integrity files and work units | Excluded | Current integrity and the comparison are generated again; original results cannot accept a successor |

Open `index-react.html?view=mesh` or
`index-react.html?view=node&repository=Goldkelch/qik-vrt` on a static host.
The client also recognizes existing host routes `/mesh` and `/node`. Static
relative resources make the shell independent of a Self-Host package. The host
still has to provide the existing `/api/activity`, `/api/runtime`,
`/api/terminal`, `/api/stream` contract. This change adds no API host, executor,
storage, polling scheduler or deployment. Missing API replies are visibly
classified rather than represented as a working runtime. A loopback test host
is only an inert test fixture, not a production server.

Run `make monitor-test` for locked dependency checks and the 14 retained
feedback controls (16 tests total). They include captured Authority-404
`0/5 → 5/5` explanation coverage, status/cause uncertainty, actors, REST steps,
repair progress, selectable raw JSON, `role=alert`, sibling success, several
failures, stale/recovery, redaction and stream errors.

The existing HTTP/Firefox workflow is extended with a separate exact-head
ReactDOM browser job. It reuses #476's Playwright 1.62.1 SRI package lock and
Chrome for Testing 151.0.7922.34 archive lock, without its storage or Origin
runtime. The browser loads the actual static resource closure, tests both
390/1280 px widths, checks all six labels, focusable and selectable raw
diagnostics, the alert contract, sibling visibility, recovery and `/node`
filtering, and writes a new HEAD/TREE/source-digest-bound witness. This is a
Linux desktop loopback witness, not a live provider readback or mobile study.

The canonical `make test`, fresh candidate CI, adaptive-runtime checks, HTTP
terminal checks and unchanged main-based code-owner selector remain required.
Trusted-main native rules/reviews are a distinct gate; a successful selector
is not native approval. No governance policy is weakened by this delta.

Human comprehension is `NOT_MEASURED` (zero participants). The provider 404's
cause and repair remain unestablished. Main merge and public delivery require
their own fresh observations. Provenance:
`state/work_units/REACT_FEEDBACK_MAIN_INTEGRATION_20261007_V1.json`.

## Current-main forward update on 7 October 2026

The successor work unit
`state/work_units/REACT_FEEDBACK_CURRENT_MAIN_20261007_V2.json` binds a
history-preserving merge of current `main`
`3d6148513b289005e71c73bae12de26f5f42f445` into PR #483. Both original
parents and all three React integration commits remain in the history.
The six node-lifecycle paths are inherited exclusively from current Main and
are absent from the React PR delta against that Main. Every existing React
asset, test, dependency lock and workflow byte remains identical to the
previous candidate `60cae7aa7a9818b7446cef8b5cc1c3ea9c3ac6af`.

The unchanged Main review executor and promotion evaluator require the
observed PR base SHA to equal current Main (`BASE_DRIFT` otherwise). A
conflict-free source merge alone was insufficient: the canonical repository
manifest failed deterministic regeneration on the combined tree. Only this
README, the successor work unit and freshly generated integrity outputs are
added to the combined source tree. The initial work unit remains immutable
historical provenance. Fresh exact-head and ReactDOM results must bind the
containing successor commit/tree; earlier results do not accept it.
