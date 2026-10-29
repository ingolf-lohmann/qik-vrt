<!-- SPDX-License-Identifier: CC-BY-NC-ND-4.0 -->
<!-- Copyright 2026 Ingolf Lohmann. -->

# Production Environment readback and original material

The existing `production-environment` GET observes GitHub metadata under the
original live SSO session and protected Authority credential. It does not need
the five local host values to inspect the existing `qikvrt-production` inventory.
It still requires the authenticated Owner/admin, fixed repository, current Main,
existing Environment and original journal binding. No anonymous read is added.

After the remote reads, the existing process material resolver is an optional
comparison. If those values are missing or invalid, the receipt retains remote
presence observations, reports `material_state`, omits unverified `value_matches`
claims and does not derive an independent pin from GitHub metadata. The UI keeps
the handoff disabled. Validated local material reports `LOCALLY_VALIDATED`;
this describes validation of process inputs, not their original acquisition.

POST still validates all five original values before any GitHub call or handoff
journal mutation. Source, Owner/admin, Environment protections, sealed-box
encryption, durable pre-write intent and uncertain-result readback guards remain.

This repairs the readback deadlock, not the production bootstrap. The original
material source must actually be admitted and connected. SSO authentication,
GitHub secret metadata and fixture tests cannot supply or attest those values.
The existing consumer is `.github/workflows/qikvrt_ci.yml#container_deploy`;
original contract 114100762 and protected host provenance remain applicable.
Production acceptance requires actual job delivery followed by authenticated
`GET /v1.45/info` and independent identity/package-pin readback before restart.
No production toggle, replacement credential source or host is introduced.
