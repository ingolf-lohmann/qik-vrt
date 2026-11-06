<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# TinyFish to original Mega-ST Universal Terminal/Transputer — controlled cutover

**Status: SOURCE CANDIDATE, NOT DEPLOYED OR ADMITTED.** Owner authorization 2026-11-06.
The target for QIK-VRT is **https://raumzeitterminal.de**. The repository's
original EAP/ledger, authorized principal and approved execution policy remain
in force. This migration does not modify the ChatGPT TinyFish plugin or claim
an alternative ChatGPT browser capability.

## Evidence already found

- The Owner's connected OneDrive includes ISO files
  `qikvrt-megast-amd64_20260919.iso` and
  `qikvrt-megast-amd64_20260921.iso` (each 1,654,456,320 bytes),
  plus `qikvrt-megast-2fdcf8d2` chunk archives. Source presence is not a
  live boot attestation or authenticated guest readback.
- The Authority repository has `deploy/universal-terminal/compose.yaml`,
  `deploy/universal-terminal/nginx.conf`, `src/qikvrt_temdd_event_ledger.py`,
  `interfaces/devops-terminal-v1.json` and the browser/noVNC carrier.
- Its mesh health defines `qikvrt_cloud_transputer_mesh_health_v1`,
  terminal/gateway/m68k/live_sse roles and exact HEAD/TREE.
- The last independently observed public target returned HTTP 525 and
  `native_available=false`; this is an unadmitted *production* link, not proof
  that a separate VirtualBox VM never booted.
- Original Firefox entrypoint:
  `/qik-vrt/mesh/v1/terminal/vnc.html?autoconnect=true`.
  This is a **human browser surface**, not a generic website-automation API.

## Security-critical discovered gap

The existing reference terminal entrypoint starts x11vnc with `-nopw` if
`QIKVRT_VNC_PASSWORD_FILE` is missing. The reference nginx gateway exposes
`/qik-vrt/mesh/v1/terminal/` without declaring an authentication challenge.
**Do not expose this reference gateway to the public Internet or forward
personal logged-in sessions through it without a hardened authenticated
origin/identity boundary.** The read-only negative probe
`tools/qikvrt_megast_native_browser_probe.py` intentionally classifies an
anonymous HTTP 200 on the VNC HTML path as `ANONYMOUS_BROWSER_EXPOSURE` and
rejects cutover. A local loopback configuration is different from a secured
public interface.

## Required original two-sided bridge

1. Independently read the *actual running* Atari Mega ST / emulator guest:
   hypervisor VM ID and host, booted guest build, guest boot attestation,
   network attachment, original ISO/package digest, independent guest readback
   and exact Source HEAD/TREE. A container's m68k role alone is insufficient.
2. Route guest `m68k`/native adapter to the **existing** original TEMDD
   Universal Terminal/Transputer and its EAP service, not a second effect
   writer, synthetic mesh ID or replacement journal.
3. On the original admitted S1 host, bind the real OS secret-store/SSO session,
   mTLS daemon identity, exact EAP config and native journal; confirm
   `ADMITTED_MESH_RUNTIME_ENDPOINT` by authenticated readback.
4. Repair the original exact-domain HTTPS/origin TLS (HTTP 525), then put the
   Firefox/noVNC websocket behind strong session authentication, CSRF/origin
   controls, revocation and encrypted transport. Never publish a VNC session
   with anonymous access or a reusable bearer in a public URL.
5. Verify exact same HEAD/TREE and repository/PR on the public mesh-health and
   native `/api/temdd/subject` readbacks. Read back capabilities and a
   *separately authenticated* browser session. A public GET cannot attest
   login, transport consent or EAP acceptance.
6. LinkedIn and IONOS can then be used with **provider consent through the
   native Firefox session**. Do not copy TinyFish cookies, credentials, or
   provider login state across browsers. Each original provider callback
   needs its own verified origin, scope and subject.
7. Sign in with Apple authenticates **identity only**. iCloud Drive document
   access requires a separately admitted Apple OS File Provider / selected-file
   bridge on an Apple device; Linux Firefox in the Atari-bridge VM cannot
   confer broad Apple Drive privileges.
8. For every browser-initiated protected operation, use original QIK-VRT
   EAP prepare -> authorized commit -> original ledger/provider/guest readback.
   Ambiguous commit = readback first, no retry. A VNC click or OAuth callback
   alone does not grant `EFFECT_ACK_DONE`.
9. Only after functional equivalence (navigation, login, revocation, narrowly
   authorized action and replay), provenance, authorization, security testing,
   CI/governance and original productive readback can the **QIK-VRT-side**
   TinyFish handoff be retired. Keep historical TinyFish evidence intact.
   This does not uninstall a user-connected ChatGPT plugin.

## Repeatable bounded read-only diagnostic

```sh
python3 -B tools/qikvrt_megast_native_browser_probe.py \
  --expected-head <exact-authority-or-deployment-commit> \
  --expected-tree <exact-tree> \
  --expected-pr <original-terminal-bound-PR>
```

For an original host-local, independently authorized test only:

```sh
python3 -B tools/qikvrt_megast_native_browser_probe.py \
  --origin http://127.0.0.1:8080 --allow-loopback \
  --expected-head <head> --expected-tree <tree> --expected-pr <pr>
```

Both forms perform **GET only**, with no cookies, bearer or forwarded session.
A successful `PUBLIC_TRANSPORT_OBSERVED_ONLY` result means no more than
anonymous health, exact terminal subject, EAP discovery and denied anonymous
browser page. It **never** changes the provider router, deploys the original
guest, authenticates a browser, reads private credential files, or grants
productive EAP.

## Required negative controls

- HTTP 525 / TLS failure, stale HEAD/TREE, mismatched PR, missing m68k role.
- Public anonymous browser HTTP 200, redirect, or other missing access gate.
- Unadmitted origin and credential-bearing URL; no secret export.
- Original host not admitted, VM guest not independently attested, provider
  consent absent, owner session revoked, iCloud selected-file grant absent.
- Interrupted EAP commit, no original ledger readback, changed policy/expiry.

**Acceptance:** native browser instead of TinyFish in QIK-VRT only when the
original VM guest + terminal + domain + auth + EAP effect are separately
proven. Until then `CUTOVER=HOLD`, `EFFECT_ACK_DONE=false` for this scope.

## Historical source-preserving security overlay

The source recovery receipts pin the original `nginx.conf`, `mesh-index.html`,
and `tests/test_qikvrt_temdd_public_proxy.py` byte-for-byte. They are
restored without modifications. Use only this *explicit*, separate Gateway
override for the newly gated terminal cutover:

```sh
docker compose -f deploy/universal-terminal/compose.yaml \
  -f deploy/universal-terminal/compose.native-cutover.yaml config
```

The overlay launches `native-cutover-gateway.sh` which uses
`nginx-native-cutover.conf` and denies anonymous browser HTML and websocket
at the gateway with HTTP 403. It is an opt-in, locally testable candidate;
no deployment, original VM attestation, live SSO, provider login, or EAP
effect is implied. Historical/legacy Gateway without this override is
**not certified for public personal-browser access**.
