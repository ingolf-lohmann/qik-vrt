# QIK-VRT regulatory evidence — node rollout and persistence checklist

**Status:** NOT DEPLOYED TO NODES · node inventory and acknowledgements not verified  
**Date:** 2026-10-21

## Purpose

This procedure defines how the QIK-VRT EU AI Act / EN 18286 assessment is to be propagated to explicitly authorized mesh nodes without claiming delivery, synchronization, adoption, or conformity prematurely.

The QIK-VRT multi-node architecture restricts discovery to the declared registry and queued requests. It prohibits global scanning, self-propagation, and writes to foreign repositories. This document does not authorize or perform a write to any node repository or runtime.

## Authoritative assessment artifacts

- Root entry point: EU_AI_ACT_COMPLIANCE_STATUS.md
- Assessment and QMS gap register: docs/regulatory/EN_18286_2026_QMS_READINESS.md
- This node procedure: docs/regulatory/NODE_ROLLOUT_CHECKLIST.md

The exact source commit and content hashes must be recorded from GitHub API responses after the pull request is reviewed and merged. Until then, this branch is a proposal, not the canonical default-branch policy.

## Node-by-node workflow

For each node explicitly declared in the authorized registry:

1. **Resolve identity:** record canonical repository owner/name, node identifier, default branch, and the registry row that authorizes the connection. Do not infer nodes from search results or repository names.
2. **Check authority:** verify that the declared workflow permits this specific artifact and target. If authority or write permission is absent, stop with HOLD.
3. **Deliver through the node's approved mechanism:** use a node-specific pull request or other already-authorized update path. Do not push directly to a foreign repository merely because it is connected.
4. **Verify immutable identity:** record source commit, target commit, exact paths, blob SHA or SHA-256 for every artifact, and the API response establishing the operation.
5. **Read back:** fetch each file from the target repository's intended branch/ref and recompute or compare its digest. A successful write response alone is not a read-back.
6. **Obtain node acknowledgement:** require a node-bound receipt identifying the node, artifact version/hash, observed target ref, read-back result, responsible principal, timestamp, and status.
7. **Keep states distinct:** DELIVERED, READ_BACK_VERIFIED, NODE_ACKNOWLEDGED, IMPLEMENTED, and CONFORMITY_REVIEWED are different states. No state implies the next.
8. **Record exceptions:** preserve API status and exact error text, mark HOLD, and do not claim completion or retry a side effect without the approved reconciliation procedure.

## Per-node evidence record

Create one record per authorized node with these fields:

| Field | Required value |
|---|---|
| Node ID | Exact ID from authorized registry |
| Repository | owner/name |
| Authorization source | Registry path and row / receipt |
| Target ref | Branch or immutable ref |
| Source commit | Actual observed SHA |
| Target commit | Actual observed SHA |
| Artifact hashes | Actual SHA-256 or Git blob SHA per file |
| Delivery API response | Endpoint, HTTP status, timestamp, response identifier |
| Read-back | Retrieved ref, hash comparison and result |
| Node acknowledgement | Receipt ID and authenticated source |
| Implementation verification | Tests/procedure evidence, or OPEN |
| Conformity review | Reviewer, scope, decision, date, or OPEN |
| Current state | HOLD / DELIVERED / READ_BACK_VERIFIED / NODE_ACKNOWLEDGED / IMPLEMENTED / CONFORMITY_REVIEWED |

Do not store secrets, tokens, biometric data, or personal data in receipts. Use a signed or otherwise authenticated receipt where the established node protocol supports it; do not describe an unauthenticated hash as an identity signature.

## Rollout acceptance rule

The rollout is complete only for the finite, explicitly authorized node set whose per-node evidence records pass all required read-back and acknowledgement checks. The registry is open-ended, so no claim about every possible future node is valid. Until the authorized inventory and node receipts are inspected, the global state remains NOT_DEPLOYED_TO_NODES.

## Repository governance

The canonical QIK-VRT repository rules remain controlling. In particular, this procedure does not override the existing multi-node boundary, acceptance order, or authorization checks. A merged document is a policy artifact; it is not evidence that any remote node runtime has loaded it or operates an Article 17 quality-management process.