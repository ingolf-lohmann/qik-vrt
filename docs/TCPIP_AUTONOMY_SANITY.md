<!-- QIKVRT-DE-EN-DOC-HEADER
Deutsch: Dieses Dokument ist Teil des QIK-VRT-Repositories und ist zweisprachig anschlussfähig zu führen. Maßgeblich sind Urheberschaft, Lizenz, Traceability, Requirements, Tests und Nichtregression.
English: This document is part of the QIK-VRT repository and must remain bilingual-accessible. Authorship, license, traceability, requirements, tests, and non-regression are mandatory.
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
Software license / Software-Lizenz: Apache-2.0 unless otherwise stated.
Documentation license / Dokumentationslizenz: CC BY-NC-ND 4.0 unless otherwise stated.
-->

---
QIKVRT-Artifact: license-header
Version: 2.13.4
Author / Urheber: Ingolf Lohmann
Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him.
License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated.
Traceability: QIKVRT Verfassung der Nachvollziehbarkeit; no final pass without evidence.
---

# TCP/IP Autonomy Sanity Layer

This layer proves bounded autonomy for QIKVRT repositories inside an authorized TCP/IP peer network. It is not self-propagation and it is not Internet scanning.

## Scope

- loopback TCP/IP runtime proof in the selftest.
- authorized selftest request from an opt-in peer.
- peer-requestable sanity check with traceable response.
- No unauthorized scanning.
- No remote mutation.
- no surveillance instrument.
- no exploit or intrusion behavior.

## Protocol

A peer may request `QIKVRT_SELFTEST_SANITY` only if the peer is opt-in, authorized, traceable and listed in an approved manifest. The response reports PASS or FAIL, never modifies the remote peer and never probes beyond the authorized endpoint.

## Damage path

If the requested selftest fails or a node disappears, the local node records quarantine-required status, sends an authorized multicast notice to responsible peers and opens root-cause review. The objective is damage containment: isolate, circle in, and remediate by documented local owner action, not by unilateral remote mutation.

## Runtime usage

The CLI command `--selftest-tcpip-autonomy` is suitable as recurring sanity check. External schedulers may run it periodically. Other QIKVRT repositories may request the same test through an authorized peer channel.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
