# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard

## Purpose

Every state-changing repository operation MUST expose a compact progress view to the human operator while external commands, builds, proof checks, integrity materialization, or publication steps are running.

## Required fields

```text
Repository: <owner/name>
Operation: <precise operation>

[██████████░░░░░░░░░░] 50%

✓ completed gate
🔄 running gate
⏳ pending gate
✗ failed gate

STATUS = IN_PROGRESS | PASS | BLOCK | FAIL | TIMEOUT
```

The percentage is relative progress over declared gates, not an elapsed-time prediction. A gate contributes only after verifiable completion. Terminal PASS is forbidden while any required gate remains pending, running, failed, or unverified.

## Interaction cycle

1. Declare operation and gates before the first remote write.
2. Update the view after every observable state transition.
3. Distinguish repository CI, formal proof, integrity, review, and merge states.
4. On failure, identify the exact blocking gate and continue with repair when authorized.
5. End with a terminal state and immutable evidence identifiers.

## Improvement rule

Each run MAY emit machine-readable timing and cache metrics. Later workflow revisions MAY improve gate ordering, cache keys, messages, or polling intervals only when they preserve fail-closed semantics and do not weaken proof, integrity, provenance, or review gates.

## Non-deception rule

A visual progress value never proves correctness. Correctness is established only by referenced gates and evidence.
