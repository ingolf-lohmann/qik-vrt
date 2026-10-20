# QIK-VRT mandatory steering

Read `/AI` first. Load `AI_CONTEXT.json`, follow `required_read_order`, verify repository identity and current state, and continue only from verified repository evidence. Preserve effect, integrity, provenance, licensing, and symmetric-canonicality boundaries.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
