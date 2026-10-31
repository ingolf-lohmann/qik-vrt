# P0 #651 — causal admission regression contract

This test-first contract captures the observed failure in run 41167846458 attempt 2.

## RED (observed)
- Existing evidence branch for issue #650 had unchanged request/context/processor fingerprint.
- Existing review handoff failed with PR_CREATION_NOT_PERMITTED.
- A matching draft PR #652 was subsequently created for the same exact commit/tree.
- Native replay returned NOOP_UNCHANGED_CAUSAL_INPUT and skipped the review handoff.
- GitHub concluded success despite no verified handoff.

## Required GREEN
1. Same semantic request + same processor fingerprint + missing/failed review handoff MUST NOT become DONE or successful no-op.
2. A matching review PR at the exact immutable branch HEAD must be independently read back; its creation is a new causal capability observation.
3. Handoff recovery must not rerun compilation or rewrite the branch when only review admission changes.
4. No matching PR + unchanged capability must remain explicitly BLOCKED, not success.
5. Ambiguous PR writes must be read back before any retry; never duplicate PRs.
6. Persist exact HEAD/TREE, error class, capability/readback state and owner-action requirement.
7. Run fault injection for denied token, restored capability, missing PR, stale head, duplicate PR, interrupted notification, and replay.
8. Native CI must bind TESTED_SUBJECT and enforce regression tests before merge; effect acknowledgement remains separate.

## Clean Code boundaries
Separate deterministic issue compilation, causal work admission, review-handoff admission, notification and completion predicates. Avoid mixing source-input equality with external effect state. Preserve existing evidence and governance gates.

This document is a regression specification, NOT a passing test or production repair.
