# QIK-VRT Copilot instructions

Before generating or modifying project content, read the root file `AI`, parse
`AI_CONTEXT.json`, and follow its `required_read_order`.

Repository evidence is authoritative over chat or model memory. Preserve
provenance, effect boundaries, tests, hashes, and the explicit licensing split:
freely available architecture does not automatically license the concrete
implementation as open source. Treat symmetric canonicality as verified only
for byte-equivalent declared scope.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
