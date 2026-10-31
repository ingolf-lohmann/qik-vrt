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

## Release trust-root continuation

Predecessor: PR #658, commit `6d79d07124f6579d3f6e5939fdcc77aa5c1f3fd4`, tree `b69f2028eddd16720d9eb05fe3b835fa12f98884`.

Codex extended the existing Node WebCrypto harness under the Owner's continuation authorization. It now evaluates the unchanged trust-root binding, helpers and `verifyRelease` source in a fresh VM for each key input, without replacing identifiers in the tested function. Five executable negative controls cover a missing key, an actual P-384 public key, an actual ephemeral P-256 private JWK, an empty private `d` field, and a wrong key type. Every case must raise `RELEASE_TRUST_ROOT_MISSING` with **zero key imports and zero asset fetches**. No private JWK is written to disk or logged.

The client now rejects the presence of `d`, including an empty field. The valid signed release, altered manifest, altered asset, unsafe paths, invalid metadata and foreign signing-key controls remain in the same harness. These are isolated verifier execution tests; browser rendering, built-HTML trust-root pinning, rollback protection, the Lean implementation adapter, Main integration and production acceptance remain open under the gates above.

Reproduction: `node tests/mini_internet/web/release_contract.test.cjs`. The existing Mini-Internet workflow checks the updated application SHA-256 and executes this harness. Its result is scoped to the exact tested commit; a local run alone is not native CI acceptance.

The predecessor's CI run `41213767517`, job `124573941493`, failed the repository-wide workflow runtime-pin gate: this newly added workflow still used `actions/setup-python@v5`, and the active Python-action inventory had increased from 56 to 57. The step's green conclusion was masked by `continue-on-error`; its raw log records `FULL_TEST_OUTCOME: failure`. The workflow now reuses the repository's reviewed checkout/Python/Node action pins, explicitly selects Node 24 for WebCrypto, and registers that added site in the existing action inventory and tool-cache authority. No failing assertion or required gate is removed.

Local validation: `make test` exited 0 (2,259 reported Python test executions); the separate Mini-Internet Python suite passed 14 tests; the C90 reducer passed 6 tests and its mathematical verifier accepted the valid certificate and rejected the invalid certificate. The Node verifier controls and the 12 workflow-pin tests passed. A temporary mutant restoring the old truthiness-only private-field check was rejected by the executable test (expected exit 1). Tool-cache coverage remained 44/44. These results are local empirical test evidence, not a new Lean-kernel proof.

Retained raw logs, the failed predecessor CI log, tool versions, source hashes and an internal SHA-256 index are packaged in [`PR658_RELEASE_KEY_LOCAL_VALIDATION.zip`](../../evidence/mini-internet/PR658_RELEASE_KEY_LOCAL_VALIDATION.zip). The package explicitly records that some initial bootstrap console chunks were not saved; it does not claim a complete raw session transcript. The existing integrity generator also includes the predecessor's ten Mini-Internet files that were missing from its stored inventory. No unmodified source file is changed for this repair.
