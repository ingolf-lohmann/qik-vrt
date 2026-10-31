# Static Terminal DevOps Client — admission and acceptance

The static HTML client is a single file; no npm, CDN or browser token is required. It may read public GitHub CI evidence. The server-side bridge is a separate stdlib Python component.

## Security and evidence boundaries

- The read-only snapshot endpoint reports the exact PR HEAD and associated CI runs.
- The SSE endpoint is an authenticated event stream; it never claims native EFFECT from GitHub workflow success.
- The command endpoint **must reject** mutations until the original Universal Terminal and Universal Transputer have been authenticated, bound, and admitted with native effect/readback. `503 ORIGINAL_TERMINAL_TRANSPUTER_ADAPTER_NOT_ADMITTED` is the intentional safe default.
- Never ship a browser-side GitHub token or a hardcoded production credential. Loopback server must be placed behind an authenticated HTTPS reverse proxy; verify Origin and session.
- Native admission, command persistence, issue event, PR handoff, CI, Main merge, and productive effect each need their own exact readback.
- No client or external timer may be the authoritative executor; GitHub issue/workflow events remain the repository-native causal triggers.

## Acceptance still required

1. Persist static `index.html` and bridge source on this branch and run browser and Python tests.
2. Wire authenticated command ingress through the original admitted Terminal/Transputer, not a substitute.
3. Demonstrate command → issue → native workflow → PR → CI → merge → effect evidence with immutable IDs.
4. Serve the client on the approved domain after TLS and host/SSO acceptance.

A published interface contract is not a claim of deployed runtime availability.

## CI observability failure disposition (2026-10-31)

The GitHub job-log retrieval for run `41173758338`, job `124456950864`, returned `404 BlobNotFound` while the job was `in_progress`. This is an **observation transport failure**, not a test verdict. The observer must:

1. Preserve the original HTTP status and diagnostic, the run ID, job ID, and exact HEAD without marking the CI as passed or failed.
2. Query the GitHub run and job/step endpoints independently as the authoritative live status fallback.
3. Reattempt archived log retrieval only after the job has reached a terminal state; if still unavailable, record a distinct `LOG_ARCHIVE_UNAVAILABLE` defect with the provider response.
4. Require successful exact-HEAD native CI and an accessible audit/terminal disposition before accepting the tested fixpoint. A log-fetch error cannot be silently ignored or repaired by claiming the tests succeeded.

This fallback is read-only, event/readback driven, and does not schedule a timer. It does not repair GitHub's upstream log archive; provider-side repair requires an independently confirmed failure after job completion.
