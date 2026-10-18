<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
# Firefox / Argon: bounded integration review, 2026-10-14

Prepared by Codex in response to Ingolf Lohmann's request to address practical
Firefox/Argon tests, licensing and QIK-VRT integration. Human authorization,
AI-generated implementation, technical tests and production acceptance remain
separate. No third-party contract was accepted, no subscription ordered and no
model request sent in this run.

## Reuse and subject

Extends the existing PersonalRuntime and HTTP terminal from PR 462,
base d0477150b4cc0b2516c2579d70da9ed71c60e048,
tree 8721a0f4e42b2045261ad7250a553bcc50dbb4ac.
No second server, duplicated extension or provider SDK is introduced.
The candidate is opt-in; provider changes cannot reuse a differently bound
SQLite state directory. Pending intent is durable before each inference;
ambiguous outcomes block repeat generation. Model output never grants effects.

## Rights / entitlement disposition

* Firefox extension installed separately from an official Firefox download:
  preferred distribution proposal. No Mozilla trademark permission is inferred
  for a modified branded browser bundle or paid distribution bundle.
* Firefox Enterprise: optional evaluation only. Public deployment summaries do
  not grant Admin Console redistribution or customer sublicensing rights.
  Price, concrete contract, platform support and distribution grant remain OPEN.
* Gemini API: review is OPEN_FOR_LIVE_USE. Current terms describe professional/
  business developer purposes and require Paid Services when API clients are
  made available to users in the EEA, Switzerland or UK. A personal consumer
  assistant must not be presumed eligible merely because API access exists.
  Bind the intended use and applicable customer agreement before live enablement.
* No Google model weights or server runtime are redistributed. The local code
  retains QIK-VRT's existing per-file licensing; this is not a commercial grant.
* store=false disables stored Interaction objects; it is not a zero-retention
  or EU-only-processing assurance. No Grounding with Google Search is enabled.

## Runtime observations and remaining acceptance

Local checks use CPython 3.12.14 rather than the lock's 3.12.13. The unchanged
cache-contract checker passes for its 14 declared components, but this does not
attest complete boot readiness or the pinned runtime profile on this host.
13 original PersonalRuntime tests and 10 added Gemini controls passed with
technical transports. The original terminal's 7 contract/loopback tests are
also executed. These are not user trials or authenticated provider evidence.

Firefox 158.0 Linux x86_64 was downloaded from Mozilla and matched its published
SHA512SUMS. An incomplete libxul.so extraction was repaired from the same
verified archive. `firefox --version` then returned Mozilla Firefox 158.0.
The actual headless launch reported `writing /proc/self/uid_map: EPERM` and
repeated content-process exits. WebDriver BiDi did not yield a usable session.
The browser was stopped; no sandbox was disabled. Therefore DOM/UI, extension
installation, browser restart and authenticated browser/Argon behaviour remain
UNVERIFIED. No downgrade is proposed.

GEMINI_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY and the local pairing token were
not supplied to this process. No secret values were read or persisted. Inspect
the existing authorized executor/secret binding for live testing; never copy
keys into Git, chat, ordinary artifacts or command-line arguments.

Acceptance still requires a sandbox-capable host, authorized Paid-Service
credential binding, same-subject Firefox DOM and restart checks, an actual
Argon reply plus independent HTTP readback, and rights approval for the exact
distribution unit. No current Main integration or EFFECT_ACK_DONE is claimed.

## Primary sources checked 2026-10-14

https://www.mozilla.org/en-US/foundation/trademarks/distribution-policy/

https://www.firefox.com/en-US/firefox/enterprise/158.0/releasenotes/

https://www.firefox.com/_documents/7/Shared_Responsibility_Summary_Firefox_Enterprise.pdf

https://ai.google.dev/gemini-api/terms

https://ai.google.dev/gemini-api/docs/interactions-overview

https://ai.google.dev/gemini-api/docs/latest-model

https://archive.mozilla.org/pub/firefox/releases/158.0/SHA512SUMS
