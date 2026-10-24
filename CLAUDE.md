# Claude repository instructions

Read the root file `AI` first. Then load `AI_CONTEXT.json` and follow its
`required_read_order` exactly.

## Native Mesh access and GitHub access

A missing Claude-account GitHub connection prevents that account's GitHub
mutations. It does not prove that the native Mesh is unavailable. The existing
S1 launcher supports `adapter: "none"`; native Mesh peers use separately admitted
private peer keys and exact source pins. Run the existing read-only
`python3 -B tools/qikvrt_self_host.py mesh-contract` and read
`runtime/self-host/README.md#native-mesh-entry-and-github-identity`.

Keep source reading, local work, native peer admission, proposal arrival,
execution and independent effect readback separate. Preserve unsent local
commits and their full identities. Use an existing admitted Mesh transfer when
callable; do not ask the Principal to relay files or repeatedly request a GitHub
login. A missing native endpoint or private peer binding is an explicit open
gate. Never manufacture credentials, assume another client's identity, weaken
admission or claim a joined peer from a source check.

The repository, not conversation memory, is the project authority. Symmetric
canonicality between the declared repositories exists only for verified equal
scope and bytes. Preserve the architecture/implementation licensing boundary;
do not infer open-source rights for the implementation from an open
architecture specification.
