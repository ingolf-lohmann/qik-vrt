# QIK-VRT repository entry

Read `/AI` first. Then load `AI_CONTEXT.json`, follow `required_read_order`, verify the actual repository and Git ref, and work only from verified repository state. Preserve all effect, integrity, provenance, licensing, and symmetric-canonicality gates.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
