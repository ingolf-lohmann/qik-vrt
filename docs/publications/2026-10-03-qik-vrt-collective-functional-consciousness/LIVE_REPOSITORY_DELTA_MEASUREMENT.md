# QIK-VRT Live Repository Delta Measurement and Open-Work Application

Date: 2026-10-03
Subject main: 8704969da54ed9c0ad08d4540ea89aee15d85ae2
Subject tree: 6969b7ae162447c12d2f7c3429c4d4521b00c33d

## 1. Live repository measurement

A fresh recursive Git tree readback of Mirror main contains:

- 4,381 total tree entries
- 3,928 blob/file entries
- 399,659,748 total blob bytes represented by the tree listing

The live measurement compares two repository reconciliation strategies:

CONTROL:
- treat the repository as if all 3,928 files require subject comparison.

DELTA TREATMENT:
- use Git history and exact-head provenance to restrict semantic comparison to files actually changed by the work unit;
- mandatory global gates remain mandatory and are not elided.

This is a live structural workload measurement on the actual current QIK-VRT repository. It is not yet an Authority↔Mirror end-to-end wall-clock benchmark.

## 2. Current active frontier

Against current Mirror main, the recent active PRs have these exact delta sizes:

| PR | Topic | Changed files | Full-scan comparisons | Delta comparisons | Comparison work avoided |
|---|---|---:|---:|---:|---:|
| #447 | functional consciousness publication | 12 | 3,928 | 12 | 99.69% |
| #446 | Authority URL readback | 15 | 3,928 | 15 | 99.62% |
| #445 | chat/interruption continuity | 6 | 3,928 | 6 | 99.85% |
| #444 | Authority installation/routing | 34 | 3,928 | 34 | 99.13% |
| #443 | persistence variance benchmark | 35 | 3,928 | 35 | 99.11% |
| #442 | exact-owner publication carrier | 39 | 3,928 | 39 | 99.01% |
| #441 | recursive HALT/capability | 17 | 3,928 | 17 | 99.57% |
| #440 | governance enforcement gap | 3 | 3,928 | 3 | 99.92% |
| #439 | source-bound claim verifier | 20 | 3,928 | 20 | 99.49% |
| #438 | Windows 11 AMD64 product witness | 26 | 3,928 | 26 | 99.34% |
| #437 | Mesh recovery / CQF / Authority manifestation | 91 | 3,928 | 91 | 97.68% |

Median active-frontier delta = 20 files, or 0.509% of the repository file set.
Median structural comparison reduction = 99.49%.
The median full-tree/delta ratio is 196.4:1.

## 3. Interpretation

This live repository observation confirms the mechanism identified by the deterministic microbenchmark at the structural-work level:

FULL_REDISCOVERY is unnecessary when:
1. the predecessor subject is exact-head/tree bound;
2. the successor delta is content-addressable;
3. unchanged state is retained rather than re-derived;
4. global invariants are re-run only where the contract requires global scope.

This DOES NOT imply a 196x end-to-end wall-time speedup. GitHub API latency, CI startup, mandatory global tests, network transport, serialized repository writes, Authority credential routing and external Effect-Readback remain outside the changed-file comparison count.

## 4. Outstanding live distributed experiment

The originally requested live Authority↔Mirror wall-time A/B experiment remains blocked by the current Authority read path:

- generic read of Goldkelch/qik-vrt: HTTP/API 404 from the currently exposed connector path;
- PR #446 independently classifies the native execution edge as lacking credential delivery for the Authority readback runner.

Therefore:

ALGORITHMIC_MICROBENCHMARK = PASS
LIVE_REPOSITORY_DELTA_REDUCTION = PASS
LIVE_DISTRIBUTED_AUTHORITY_MIRROR_SPEEDUP = HOLD_AUTHORITY_READBACK_UNAVAILABLE

No predecessor or proxy evidence is promoted into the missing live-distributed result.

## 5. Application to open work

The new default work rule is:

OBSERVE EXACT SUBJECT
→ COMPUTE EXACT DELTA
→ CLASSIFY AFFECTED INVARIANTS
→ REUSE UNCHANGED PROVENANCE AS HISTORY, NOT AS SUCCESSOR PASS
→ RUN REQUIRED GLOBAL GATES
→ READ BACK EFFECT
→ CONTINUE

This changes prioritization:

### P0 — unlock reciprocal live cognition
1. #446 Authority URL/readback credential delivery boundary.
2. #444 Authority installation/routing exact-path closure.
3. #437 Mesh recovery / Authority manifestation where it supplies the reciprocal carrier.
4. #441 recursive capability-bound continuation, because measurement must continue after intermediate observations.

### P1 — product and measurement closure
5. #438 Windows 11 AMD64 product-target witness.
6. #443 persistence variance diagnosis, because it currently limits generalized parallel-speedup claims.
7. #445 interruption continuity, because preserved state is part of functional self-continuity.

### P2 — governance and proof compression
8. #440 smallest governance enforcement gap.
9. #439 source-bound claim/invariant verifier.
10. #442 publication-carrier closure.
11. #447 publication, IETF companion, truthfulness and consciousness claims after measurement boundaries are final.

The older backlog SHOULD be processed by exact-delta classification rather than chronological full re-analysis. Historical PRs whose intended effect is already present on current main should be classified as SUPERSEDED_OR_ALREADY_INTEGRATED rather than re-executed.

## 6. Forecast rule

Calendar forecasts are now calculated from blocker topology rather than PR count.

A work unit whose remaining blocker is:
- exact-head rebase + green existing gates: hours to 1 day;
- one missing authorized carrier / credential route: 1-3 days after carrier availability, otherwise unbounded;
- external physical witness: dependent on hardware access, not inferable from CI;
- external publication moderation/review: external schedule, not under QIK-VRT control.

The delta-memory result reduces expected analysis/reconciliation cost, but does not shorten external or authorization-limited critical paths.

q.e.d.
Ingolf Lohmann
