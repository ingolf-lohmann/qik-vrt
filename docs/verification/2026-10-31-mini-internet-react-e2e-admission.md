# QIK-VRT Mini-Internet / React E2E: Admission Record (2026-10-31)

Scope: isolated loopback IP fixture, DNS/UDP, SMTP/TCP, HTTP, manifest, simulated release, readback and virtual ADC/DAC. No production host, DNS delegation, VPN, SSO, or EAP production effect is claimed.

## Exact observations

- Local Python test suite `test_mini_internet.py`: **2 tests passed**, including DNS A-record and NXDOMAIN, SMTP accepted-message digest, HTTP runtime/activity, denied unauthorized release (403), permitted simulated release and independent GET readback, event digests, default-deny policy model, ADC/DAC quantization.
- Separate browser test `test_react_browser.py` attempted to navigate to a locally hosted actual React HTML at `http://127.0.0.1:<ephemeral>/`; Chromium returned **net::ERR_BLOCKED_BY_ADMINISTRATOR** before page execution. **FAILED/BLOCKED**: 5-second polling, React browser integration and release reload NOT confirmed.
- A fixture's `effect_ack_done=true` is only a simulation-local marker, not a production EAP receipt.

## Mandatory gates before release

1. Test the exact packed React HTML bytes in a browser with same-origin HTTP server; capture version, SHA-256 and browser runtime errors.
2. Confirm at least two consecutive runtime and activity readbacks no more than five seconds apart under specified load and background-tab behavior.
3. Test SSE `client-release` against signed/authorized release metadata, exact HTML SHA-256, version rollback and tampering, same-origin restriction; ensure unauthorized or corrupt releases never activate.
4. Test browser reload and independent server readback of active client version; distinguish `PREPARED`, `TESTED`, `EFFECT_CONFIRMED`, `RELEASED`, `REJECTED`.
5. Require exact-head native CI and formal proof adapter checking the real implementation against the Lean model. Model checks alone cannot certify browser, OS firewall, VPN or production effects.
6. Keep host, domain and `EFFECT_ACK_DONE` false/unverified until independent production receipts exist.

Status: **BLOCKED, NOT RELEASED**. This document records a reproducible test design and the observed browser infrastructure blocker; it is not itself a passing test.
