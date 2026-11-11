# QIK-VRT Passive Mirror Admission v1

**Owner:** Ingolf Lohmann  
**Authority:** `ingolf-lohmann/qik-vrt`  
**Status:** Normative target contract; runtime implementation and deployment are not yet verified.

## Purpose

Provide one Authority-controlled HTTPS entrypoint for people and external AI clients to discover the public QIK-VRT Trusted Mesh information and, if they choose, request registration as a passive read-only client.

## Important distinction

A click on a GitHub `blob` or `raw` URL is not a callback to the Authority. GitHub page views are not a reliable, client-attributable admission signal. Therefore the canonical repository entry `/AI` must link to a separately deployed Authority-controlled HTTPS onboarding page if click telemetry and registration are required.

A page view may be counted only to the extent the hosting platform exposes privacy-minimized aggregate telemetry. A client becomes registrable only after an explicit, informed consent action submits an admission request.

## Client role

`PASSIVE_READER` means a client instance with read-only access to public repository content and explicitly published mesh documents. It is not the Git repository Mirror `Goldkelch/qik-vrt`, not an Authority peer, and not a writer or executor.

No repository credentials, private records, write capability, execution capability, or policy-mutation authority are granted by this role.

## Admission lifecycle

`UNOBSERVED → ENTRY_REQUEST_OBSERVED → CONSENT_PRESENTED → CONSENTED_ADMISSION_REQUEST → AUTHORITY_REVIEW_PENDING → PASSIVE_READER_ADMITTED`

Suspension and revocation remain available. A page view alone never creates membership. Authority admission must produce a durable receipt bound to the exact Authority head and tree, followed by independent readback.

## Privacy and security

- Explain the fields and retention period before consent.
- Do not use hidden fingerprinting or collect raw IP addresses, full user-agent strings, cross-site identifiers, credentials, provider secrets, or conversation content.
- Treat client type and provider identity as self-asserted until independently verified.
- Validate HTTPS origin and CSRF protections; enforce rate limits, request-size limits, and replay protection.
- Support withdrawal. Keep public responses free of private registry data.
- On ambiguity, unavailable Authority, failed durability, or conflicting identity: `HOLD`.

## Runtime work still required

1. Identify and verify the Owner-controlled public HTTPS host.
2. Deploy a consent page and Authority admission endpoint.
3. Persist consented requests in the Authority registry and independently read them back.
4. Issue exact-head/tree-bound read-only admission receipts.
5. Enforce read-only access in the serving layer.
6. Test privacy, abuse controls, replay, withdrawal, failure and external delivery.
7. Verify the deployed endpoint with a fresh external request.

## No false completion claims

This contract is a repository-side specification. It does not itself implement the endpoint, record page views, register clients, issue credentials, or prove public deployment. A GitHub link alone cannot guarantee that every click is reported.
