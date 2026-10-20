# Claude repository instructions

Read the root file `AI` first. Then load `AI_CONTEXT.json` and follow its
`required_read_order` exactly.

The repository, not conversation memory, is the project authority. Symmetric
canonicality between the declared repositories exists only for verified equal
scope and bytes. Preserve the architecture/implementation licensing boundary;
do not infer open-source rights for the implementation from an open
architecture specification.

Session rule contract: `python3 -B tools/ai_handoff.py --session-contract`.
For every current session use the shared /AI rule set and a version-2 receipt:
`python3 -B tools/ai_handoff.py --client-receipt RECEIPT --require-session-contract`.
Capabilities are local observations; they do not change rules or revoke grants.
Retain unavailable Mesh nodes as OPEN until their original authenticated ACK and application readback.
