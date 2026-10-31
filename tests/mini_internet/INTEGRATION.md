# Independently implemented mini-internet evidence — integration contract

This bundle was independently implemented and executed by a separate AI system, not copied from the earlier assistant's local fixture. The delivered archive contains source, PKI setup, a React client, C90 verifier, evidence JSON, four certificates, screenshot, SHA256SUMS and two logs ending `RESULT PASS 33 / 33`.

## Reproducible native job

Use an isolated, disposable Linux runner with `iptables`, Python 3.12+, NumPy, Playwright/Chromium, esbuild and React 19. Explicitly grant `CAP_NET_ADMIN` only to the dedicated runner/network namespace. No external routes, host credentials, production DNS or secrets.

1. Verify every ZIP entry against SHA256SUMS, rejecting missing, duplicate and unhashed entries.
2. Extract into a new disposable directory. Do not execute archive-supplied code before validating its provenance and contents.
3. Run `./setup_pki.sh` to generate ephemeral certificates.
4. Build `web/app.jsx` with the declared React 19 toolchain and esbuild. Record exact lockfiles and dependency digests.
5. Run `python3 mini_internet.py` in the isolated network namespace and assert 33/33 on each of two fresh runs; archive new evidence, not the original bundled logs.
6. Compile `c90_math_verifier.c` with `-std=c90 -pedantic -Wall -Wextra -Werror`; verify all four newly generated certificates.
7. Run independent browser readback and negative tests for modified assets, forged signatures, unauthorized publishing and missing observation.
8. Bind the complete CI evidence to commit/tree, source ZIP SHA256, dependency lock, runner identity and test execution ID.

## Admission

The independently produced 33/33 logs are accepted as historical evidence of the isolated fixture. They are **not** evidence that this repository's CI ran those exact tests or that `raumzeitterminal.de` received a production EAP effect. No claim of current production deployment is made.

No `math_gate.py` verdict may authorize a write until the trusted Lean verifier executable and its subject are pinned and non-bypassable; in particular, `/bin/true` must be rejected. Fail closed.

Owner: Ingolf Lohmann. Preserve original third-party licensing and source provenance.
