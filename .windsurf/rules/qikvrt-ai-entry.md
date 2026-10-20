# QIK-VRT mandatory handoff

Read `/AI` first. Then load `AI_CONTEXT.json`, follow its `required_read_order`, and continue only from verified repository state. Repository evidence overrides conversational memory. Preserve effect, integrity, provenance, licensing, and symmetric-canonicality boundaries.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
