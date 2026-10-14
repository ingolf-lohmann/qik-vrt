# QIKVRT AI Terminal for Firefox

This directory is the Firefox reference client for the QIK-VRT EFFECT_ACK HTTP terminal profile.

## What it is

The client is a Manifest V3 WebExtension rather than a forked Firefox binary. That is intentional: it preserves compatibility with normal Firefox releases while adding the QIKVRT terminal as an isolated, reviewable adapter.

When installed, the content script is injected on the configured QIKVRT AI surfaces and presents a source-bound terminal with repository observation, text input, explicit microphone recording, explicit camera preview/snapshot, Prepare/Commit gating and local personalization.

## Repository binding and entrypoints

`policy/CANONICAL_UPSTREAM_REMOTE_V1.json` selects `ingolf-lohmann/qik-vrt`
as Authority and `Goldkelch/qik-vrt` as Mirror. The background observer always
reads the Authority's current Main HEAD, TREE and workflows through GitHub's
read-only REST API, including when the terminal is opened on a Mirror page.
An Authority read failure remains HOLD; it never selects the Mirror as fallback.

Content scripts support the Owner's GitHub `/blob/main/AI*` entrypoint and
`https://ingolf-lohmann.github.io/qik-vrt/*`. The existing Goldkelch GitHub
`/blob/main/AI*` and `https://goldkelch.github.io/qik-vrt/*` entrypoints remain
available as Mirror surfaces. An allowed address is not proof that it is
currently published, synchronized or accepted for production.

The GitHub host permission uses one Owner-named entry for the shared
`github.com` origin; a second Mirror-named permission adds no host capability.
Only the Owner's project Pages origin is added. Injection remains restricted
by the four content-script matches; other repositories and GitHub pages are
not terminal entrypoints. API observation and the two existing loopback
backend permissions remain unchanged. Host permissions do not authenticate
an account or authorize repository writes or protected effects.

## Security boundary

- Public GitHub observation is read-only.
- The reference EFFECT_ACK bridge is loopback-only on port 8771.
- Audio/video access requires an explicit browser permission and user gesture.
- Captured media remains local until explicit Prepare.
- Prepare never authorizes or executes the protected effect.
- Commit remains disabled until the exact full responsibility record has been re-fetched and validated as `EFFECT_ACK_DONE`.
- Commit transports token and record hash only through the specified `Effect-Ack-Request` Structured Field.
- The exact prepared text/audio/video payload is frozen and reused for Commit.
- The reference backend has `external_effect = NONE`.

## Development loading

Requires Firefox 158 or later.

Firefox can load the unpacked reference client for development and verification:

1. Open `about:debugging#/runtime/this-firefox`.
2. Select **Load Temporary Add-on**.
3. Select this directory's `manifest.json`.
4. Open the configured QIKVRT AI page.

A temporary development load is not an AMO signature or distribution approval.

## Reproducible package artifact

The repository workflow `.github/workflows/qikvrt_effect_ack_http_terminal.yml` creates a deterministic file-set ZIP with the `.xpi` suffix and a SHA-256 sidecar after all syntax, RFCXML and E2E checks have passed. The workflow artifact is a verification/build artifact; normal persistent Firefox installation can still require Mozilla signing or an appropriate managed/development configuration.

## Counterpart

Run the loopback reference bridge from the repository root:

```text
python3 -B src/qikvrt_effect_ack_http_terminal.py --host 127.0.0.1 --port 8771
```

The bridge demonstrates the complete local prepare/commit/reobserve shape but deliberately cannot perform repository writes, releases, deployments, publication or actuator effects.

## Existing S1 container installation gate

The existing QIKVRT CI job `s1_firefox_extension` reuses the exact PR457
OCI archive from run 38475417828 without rebuilding its runtime. The current
candidate XPI remains source-bound and requires Firefox 158.0. The existing
S1 launcher now offers `firefox-extension-check --extension-xpi <exact.xpi>
--output <disposable-evidence-directory>`. The probe reads the installed Debian
package, actual executable version and live AddonManager/WebExtensionPolicy
state before and after a process restart. A copied archive or temporary install
cannot satisfy activation. Missing, incompatible or disabled add-ons hold admission.

Default signing policy and the existing isolated ESR reference exception are
separate observations. Neither changes production policy. Native run 38586572118
(source 04c705b96d7dfc77e3d6e1b5af892094f7a8b404) directly confirms
installed package 153.4.0esr-1~deb12u1 and live browser version 153.4.0.
The exact candidate XPI (SHA-256
1f5f583181d6134584f98bf6b59848d4542176d624d97709fa915b9934e2c46c)
is inactive both before and after restart. Default signing policy removes it;
the explicit ESR reference retains the exact bytes but AddonManager reports
isCompatible=false, appDisabled=true, isActive=false and userDisabled=true.
WebExtensionPolicy is inactive and no extension background is registered.
The existing image also lacks the XPI at the checked bootstrap-profile path.
The native gate correctly holds at HOLD_FIREFOX_BELOW_OWNER_MINIMUM.
The existing work unit retains the byte-verified original artifact and all four
observations; unchanged image/XPI/probe failure inputs do not trigger a repeat. The supported forward route is Mozilla's official Release package
158 or newer on the retained Debian base, with a Mozilla-signed self-distributed
XPI and the same persistent activation/restart gate. This route is proposed,
not an installed upgrade or a signing receipt. The ESR exception cannot substitute
for signing on Release. Never lower the owner's minimum to make a test green.

Primary provider sources (current package listings are not image readback):
https://packages.debian.org/bookworm/firefox-esr
https://product-details.mozilla.org/1.0/firefox_versions.json
https://support.mozilla.org/en-US/kb/install-firefox-linux
https://www.firefox.com/en-US/firefox/158.0/releasenotes/
https://www.firefox.com/en-US/firefox/158.0/system-requirements/
https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/

Installation acceptance, protected Main integration and productive delivery
on https://raumzeitterminal.de/ remain distinct obligations.
