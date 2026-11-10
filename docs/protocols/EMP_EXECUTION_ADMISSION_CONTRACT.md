# EMP Mandatory Execution Admission and Continuation Contract

Status: normative implementation requirement; production conformance NOT YET VERIFIED.
Owner authorization: 2026-11-10. Related: #729, #730.

## Admission
Every accepted objective MUST atomically persist: objective ID, principal authorization, measurable acceptance predicate, policy version, exact authority repository HEAD/TREE, state, priority, next_action, executor, writer epoch, idempotency key, dependency/unblocking predicate, journal sequence and readback pointer.
An issue or backlog entry alone MUST NOT satisfy execution admission.

## Conditional progress requirement
For each authorized nonterminal objective, a repository-native controller MUST either:
1. dispatch an eligible safe step immediately and persist dispatch evidence; or
2. persist BLOCKED with concrete external cause, unblock predicate, owner-visible escalation and event-driven re-entry.
No silent idle, orphaned queue item, unbounded backlog wait or infinite ineffective retries. BLOCKED is not COMPLETE.

## Event-driven transition
On workflow completion, check completion, review, PR update, authorization change or dependency unblock: acquire fenced single-writer lease; read exact HEAD/TREE and journal; independently check EAP predicate; diagnose CI/CD failures using TEMDD; select highest-priority authorized ready action; execute; journal attempted and observed effect; independently read back; persist next state. Duplicate events MUST be idempotent. No client timers or chat session dependency.

## Priority and safety
P0 safety and liveness repair precedes ordinary work, but MUST NOT bypass authorization, CI, review, governance, host identity, patent disclosure or human revocation. Independent ready work MUST proceed despite blocked sibling objectives.

## Required conformance tests
Admission without next_action rejected; duplicate event exactly one effect; stale writer rejected; failed CI yields TEMDD and eligible successor; blocked external approval records event re-entry; independent sibling proceeds; cancellation stops effects; EAP verification alone permits VERIFIED; crash/replay recovers idempotently.

## Evidence
Issue creation, PR creation, commit, schedule or API success do not establish desired effect. EFFECT_ACK_DONE remains false without independent EAP verification. This is a specification, not proof of a running controller.
