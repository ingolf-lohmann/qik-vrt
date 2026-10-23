<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# /AI bootstrap review — issue 585

Principal: Ingolf Lohmann. Direct repair/delegation instruction: 23 October 2026.
Analysis and implementation: OpenAI Codex. The supplied Copilot feedback is a
set of hypotheses; this review does not attribute Codex's implementation to Copilot.

Starting Authority main: `a8017ab67824f01ec4d215cf7af83b8b0779283c`.
Starting tree: `94317a4da76fac49b63bb129badcbbd21471c092`.
Starting /AI blob: `11372e99b0fc506e6eeb5ced36c99181cea1541b`.

| Reported concern | Observed source and disposition |
| --- | --- |
| Numbering jumps from 2 to 5 | Disproved for this source: /AI's BOOT SEQUENCE contains steps 1 through 10. |
| Backslashes in Python paths | Disproved for this source: both executable paths have ordinary underscores. Rendering excerpts are not raw-source evidence. |
| Bootloader loads competing authority | No instruction download or task executor was found in the inspected bootloader path. A concrete ordering defect was reproduced: modified `ai_handoff.py` executed before integrity rejected its changed bytes. Integrity now precedes dependent executable gates. The verifier and trusted host environment remain trust roots. |
| Meaning of authorized task | The existing client receipt checks declared consistency, not authentication. /AI and AI_CONTEXT now say this explicitly and point to the existing Principal, executor/writer, exact-subject and governance admission contracts. Boot readiness and `--task` grant no task authority. No new authenticator or replacement executor is introduced. |
| Reproducibility requirements | /AI and AI_CONTEXT now expose the orchestration minimum, host tools, existing per-profile version authorities, check-only behavior and PASS/CONTINUE/BLOCK boundaries. Missing profile tools do not become task readiness. |

The two new real-child-process regression controls first failed against the
original ordering: the changed handoff wrote its outside marker before the
integrity failure; the clean-path control also observed handoff before integrity.
Both pass after the bounded ordering repair. The clean-path control retains
CONTINUE for profile exit 20; its fixture does not claim productive execution.

Validation commands are `make ai-runtime-contract`,
`python3 -B tools/ai_runtime_bootloader.py --profile all --json`,
`python3 -B tools/ai_collective_bootstrap_extension.py --json`,
`python3 -B tools/qikvrt_integrity.py verify`, and the full `make test`.
Final execution results belong to the exact candidate's PR/CI readback; their
presence here is not a claim that every external runtime is available.

## Copilot platform admission

The documented issue-create request with assignee `copilot-swe-agent[bot]`
was rejected by GitHub HTTP 422: `assignees copilot cannot be assigned to this issue`.
The failed request created no issue. The repair obligation was then persisted as
ordinary issue 585, without claiming a Copilot session. The callable connector
does not expose Agent Tasks POST or the optional `agent_assignment` object.
This result proves neither an absent subscription nor absent original-host
credentials. An unchanged assignment is not retried.

The independently documented Copilot PR-review operation is the next bounded
candidate. A request, assignment, queue entry or ordinary issue-processor run
must not be reported as an admitted Copilot coding session or a completed fix.
Use the actual platform response and review/session identity for any such claim.

No billing change, permission expansion, new timer or substitute executor is
part of this correction. Protected Main integration, peer adoption and useful
delivery at `https://raumzeitterminal.de/` require separate fresh evidence.
Neither these controls nor a Copilot review establishes universal error freedom.
