# QIK-VRT Lossless Framing and Effect Acknowledgement — Publication Candidate

**Author / Product Owner:** Ingolf Lohmann  
**Status:** Research and protocol candidate; not an IETF submission, RFC, production approval, or verified physical-universality proof.  
**Source authority:** https://github.com/ingolf-lohmann/qik-vrt  
**Related implementation:** PR #712, `tools/qikvrt_lossless_eap_codec.py`  
**Prior publication to reconcile:** https://zenodo.org/records/21888130 (bibliographic record referenced; contents not independently reviewed in this change).

## Abstract

This document proposes a bounded lossless binary frame and an application-level effect-acknowledgement boundary. It distinguishes representation of arbitrary finite byte strings, transmission over physical media, authorized access to protected resources, and independent verification of effects. The `001` and `100` symbols are protocol conventions rather than physical constants. A reference implementation and regression tests are supplied in the QIK-VRT Authority repository.

## 1. Scope and limits

Any finite byte string can be framed and recovered exactly if the frame is delivered intact and the decoder follows the specification. This does **not** imply that the source information is known, that a protected endpoint is accessible, that a physical system is controllable, or that an effect occurred. Physical interfaces require suitable transducers, energy, timing and calibration. SHA-256 is an integrity check in this framing format, **not** authentication against an active adversary.

## 2. Reference wire image (candidate version 0)

```
offset  width       field
0       3 octets    ASCII "001" (hex 30 30 31)
3       8 octets    unsigned payload length, network byte order
11      32 octets   SHA-256 digest of payload
43      N octets    opaque payload, 0 <= N <= 16777216
43+N    3 octets    ASCII "100" (hex 31 30 30)
```

The markers are **three ASCII octets each**, not three physical bits. The separate illustrative byte `00100000` equals hex `20` and is not the same as the ASCII start marker. A future bit-level wire profile MUST be separately specified before any claim of bit-level interoperability.

A decoder MUST reject an invalid start marker, oversized declared payload, invalid end marker, digest mismatch, and truncated frame on end-of-stream. Implementations SHOULD bound buffered input and enforce transport-specific timeouts. The current reference decoder limits declared payload length but does not yet enforce an independent total-buffer bound for hostile arbitrary chunks.

## 3. Streaming

A stream is a concatenation of complete frames. The receiver MAY receive any subdivision of octets, including one octet per chunk. A successful frame decode establishes only payload recovery and digest consistency. It is **not** an effect acknowledgement.

## 4. Effect acknowledgement (EAP) boundary

A successful effect receipt requires: an authorized request, a uniquely identified operation, verified execution, and independent observation of the resulting effect. A robust production profile MUST bind the receipt cryptographically to request ID, authenticated principal, payload digest, execution identity, outcome, and verifier; MUST provide replay protection, durable state transitions, idempotency rules, writer fencing, and auditability. The PR #712 helper only accepts externally supplied booleans and therefore does **not** implement trusted EAP.

The reverse symbol `100` is a frame delimiter only; it MUST NOT be interpreted as `EFFECT_ACK_DONE`.

## 5. Security considerations

Framing and hashing do not defeat encryption, firewalls, VPN access controls, or authorization requirements. Never expose private keys or protected content in public evidence. Require authenticated transport, authorization, replay protection, input limits, resource quotas, and independent verifier identity for a production EAP profile.

## 6. IANA considerations

This candidate requests no IANA registrations.

## 7. Interoperability and falsifiable tests

1. Roundtrip every possible single-octet value and arbitrary binary sequences.
2. Decode concatenated frames across all chunk boundaries.
3. Reject truncation, digest corruption, and oversized lengths.
4. Show equivalent decoded payload over two distinct media adapters; compare digests.
5. Produce a signed, independently checked effect receipt for a controlled actuator.
6. Verify that unauthorized and unobserved effects never yield `EFFECT_ACK_DONE`.

Tests 1–3 are represented by candidate repository tests but their execution status must be verified. Tests 4–6 require additional implementation and experimental evidence.

## 8. Publication and provenance

Keep research hypotheses, formal theorems, software tests, simulations and physical measurements as separate evidence classes. Before Zenodo deposit, reconcile this candidate with the owner's earlier published works, rights, citations and version lineage. Before an IETF Internet-Draft submission, convert the protocol specification to RFCXML v3, add full mandatory boilerplate and references, run xml2rfc/idnits validation, and obtain independent protocol/security review. The draft does not update or replace any existing RFC.

## References

- QIK-VRT Authority repository: https://github.com/ingolf-lohmann/qik-vrt
- Earlier QIK-VRT-related Zenodo record (content not reviewed here): https://zenodo.org/records/21888130
- IETF Internet-Draft author resources: https://authors.ietf.org/
- IETF Datatracker: https://datatracker.ietf.org/
