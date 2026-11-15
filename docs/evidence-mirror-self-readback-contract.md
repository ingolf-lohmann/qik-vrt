# QIK-VRT evidence-mirror self-readback contract

Status: normative TEMDD/IaC integration requirement; **not** proof of deployed code, CI, EAP, or productive effect.
Authority: `ingolf-lohmann/qik-vrt`. Existing read-only mirror: `https://qik-vrt-evidenzleitstand.vercel.app/`.
This URL is an observation source, **not** a deployment target, independent writer, second authority, or new controller.

## Fail-closed invariant
A mirror observation can inform the repository's next permitted action, but cannot authorize it:
`NEXT_STATE_ALLOWED = AUTHORITY_EXACT_HEAD_VERIFIED && ADMISSION && CI_AND_INTEGRITY_GATES && PRINCIPAL_AUTHORIZATION && WRITER_FENCING && INDEPENDENT_EFFECT_ACK`.
A green subset is not a green production gate. An empty, stale, missing, or contradictory mirror readback must be classified UNKNOWN/OPEN and never silently promoted to VERIFIED.

## Synchronous observation contract
1. Read the authority's current exact commit HEAD and TREE directly; bind the observation to a timestamp, source, and method.
2. Fetch the existing mirror using read-only GET, with bounded timeout and explicit error capture. Do not mutate, dispatch, or deploy through the mirror.
3. Extract only actually present values: mirror's reported HEAD/TREE, evidence categories, CI/checks, PR/reviews, manifest/digests, runtime/mesh/TLS, ACK/EAP, and observation timestamp. Missing values remain UNKNOWN.
4. Compare each mirror subject against the same exact authority HEAD/TREE and independently read GitHub/Originalhost evidence. A browser's initial `UNKNOWN` or `Noch kein Leselauf` is not a successful readback.
5. Persist a content-addressed receipt with source URL, retrieval time, authority SHA/TREE, mirror-reported SHA/TREE (if present), raw response digest, comparison outcome, and independent corroboration. Do not treat browser-local hash chaining as host authentication.
6. Classify CONFIRMED / OPEN / UNKNOWN / CLAIMED separately. A verified negative HTTP/TLS readback is a confirmed failure, not an admitted effect.
7. Feed only grounded deltas into the existing TEMDD repair inbox and synchronous DevOps ring. Use the existing one-writer, exact-head fenced successor mechanism; do not create timers, a parallel controller, or a Vercel write path.
8. Reobserve the same exact subject after a permitted correction. Keep `CONTINUATION_REQUIRED=true` and `EFFECT_ACK_DONE=false` until independent EAP evidence proves the effect.

## Acceptance / negative regressions
- Mirror unreachable, 404/5xx, malformed, or no browser-side read: UNKNOWN; no admission.
- Mirror reports stale/mismatched HEAD or TREE: drift incident; no promotion.
- Mirror shows green UI while exact-head CI is absent, pending, or failing: CI gate remains OPEN/BLOCKED.
- Browser-local journal digest exists without authenticated Originalhost receipt: EAP remains unverified.
- Repeated identical mirror snapshot without progress: emit deterministic no-delta TEMDD event, not a fabricated successful transition.
- Two writers or expired lease: reject the attempted effect.
- Successful independent readback for the authorized exact subject: advance only the verified gate, not all seven DoD gates.

## Integration boundary
Implement via existing repository IaC, tests, CI, and reflexive watchdog paths after reviewing the current exact HEAD. This document records the contract only; no integration, CI dispatch, Sites write, merge, or deployment is asserted by its presence.
