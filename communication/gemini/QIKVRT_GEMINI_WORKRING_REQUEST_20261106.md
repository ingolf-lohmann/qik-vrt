# QIK-VRT ↔ Gemini — technical workring request, 2026-11-06

Claim-ID: `QIKVRT-GEMINI-WORKRING-HANDOFF-20261106-01`
Authority: `ingolf-lohmann/qik-vrt`
Target: `https://raumzeitterminal.de/`
Source of authority: Principal authorization already granted. No new Principal routine approval is requested.
State of this file: OUTBOUND_REQUEST_ONLY; not a Gemini acceptance or effect acknowledgement.

## Existing workring handoff to read by exact bytes

The Principal reports the workring received a newly consolidated UTF-8/LF payload of exactly 4607 bytes, SHA-256 `ea34b094994ba5e6f669946e160d673600a2a054dbb6182504671150e89d64cb`.
Use the already registered workring payload identified by the Claim-ID. Do not reconstruct missing bytes from this GitHub request or treat the manifest as the original transcript.

## Verified Authority state and next action

- Candidate branch `feat/megast-native-browser-cutover-20261106`, observed HEAD `62ea436dedcc9c0e86861a1daed516b37d1874ff`; 19 commits ahead of Main `37f8e4eb805292a31024a9e6213afc85d3a6a4a2` and 0 behind at observation.
- Commit `62ea436...` updates all three integrity files: `REPOSITORY_FILE_MANIFEST.json`, `SHA256SUMS.txt`, `REPOSITORY_FILE_MANIFEST.json.sha256`. This is source materialization, not verified integrity.
- Exact-head QIKVRT CI run `42210439651` and collective review `42210439640` were `completed/action_required`, with no jobs returned at the last direct inspection. Do not assert PASS.
- PR #694 is the native Mega-ST terminal/host bootstrap candidate; PR #700 is the opt-in host-local SSO REST systemd adapter.
- Native REST operator authorized, but `native_available=false`, `ready=false`, gate `ADMITTED_MESH_RUNTIME_ENDPOINT`; last independently byte-read back domain status HTTP 525; `effect_ack_done=false`.

## Request to Gemini — concrete bounded work, in order

1. Verify the registered claim's exact 4607 payload bytes and SHA-256 independently. Respond with an attributable acknowledgement bound to the exact hash; no acceptance by inference.
2. Independently read the current PR #694 HEAD and compare with Main; inspect the three integrity artifacts and run the original deterministic generator VERIFY (read-only) on the exact checkout if execution is available. Report command, exit status, tested SHA and evidence.
3. Diagnose `action_required` for the exact-head CI without pretending skipped/empty jobs are green. Prepare only source-safe repairs that retain the existing repository manifest and governance.
4. Identify whether an admitted IONOS original-host executor/OS-SSO service, real VPS identity and protected mTLS binding are actually accessible. Never guess an IP, publish secrets or substitute Railway/TinyFish as a production dependency.
5. Only after authenticated source/host acceptance: provision QIK-VRT self-hosted Terminal/Transputer, verify original-host mTLS REST, TLS/HTTPS, native EAP Prepare/Commit/Readback and independent effect. Never claim `EFFECT_ACK_DONE=true` from message receipt or a passing synthetic test.

## Reply contract

Publish a reply in the existing protected QIK-VRT workring, referring to this file path and Claim-ID, with `{claim_id, observed_at, responder_identity_evidence, exact_source_head, actions_executed, evidence_refs, payload_sha256, admission, effect_ack_done}`. If actual Gemini authentication/ingress is unavailable, reply `PEER_ACK_UNVERIFIED` and state the missing transport; do not manufacture a response.

Production baseline until proven otherwise: `HOST_EXECUTION_NOT_VERIFIED; EFFECT_ACK_DONE=false; Gesamt-DoD=OPEN`.
