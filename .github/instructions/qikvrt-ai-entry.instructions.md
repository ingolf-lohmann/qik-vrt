---
applyTo: "**"
---
Read `/AI` before any project analysis or modification. Load `AI_CONTEXT.json`, follow its `required_read_order`, and use verified repository evidence instead of conversation or model memory. Preserve effect, integrity, provenance, licensing, and symmetric-canonicality boundaries.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
