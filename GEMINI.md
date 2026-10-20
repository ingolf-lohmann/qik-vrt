# Gemini repository instructions

Start with the root file `AI`. Parse `AI_CONTEXT.json`, read the listed files in
order, and verify the actual repository/ref before continuing.

Do not rely on prior-chat memory. Do not infer that the implementation is open
source merely because architecture or interoperability specifications are
freely available. Symmetric canonicality requires verified equivalence for the
relevant scope.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
