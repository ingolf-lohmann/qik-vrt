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

# Autonomous Internet Discovery and Persistent Operation

## Purpose

This layer specifies autonomous repository discovery and persistent operation after bootstrap.
It is intentionally constrained by the Verfassung der Nachvollziehbarkeit.

## impossibility boundary

A repository cannot prove global self-discovery in the entire public Internet without at least one of the following: prior peer knowledge, reachable endpoint publication, DNS/registry/rendezvous, DHT-like infrastructure, routable multicast, or active address-space scanning.

Because unauthorized Internet-wide scanning and probing are forbidden, QIKVRT rejects magical service-free global discovery claims.

## Authorized discovery model

Autonomous Internet Discovery is valid only through authorized mechanisms:

- no third-party service required for local operation;
- authorized seed peer manifest when crossing network boundaries;
- reachable endpoint declared by the node itself;
- local multicast only where routing and policy explicitly allow it;
- no global address scanning;
- no unauthorized probing;
- opt-in peer manifests;
- append-only audit ledger;
- watchdog keepalive;
- sanity selftest requestable by authorized peers.

## Persistent operation

A repository may operate durably when GUID, manifest, service startup, keepalive, sanity selftest, damage containment, and audit ledger are all present.

## Runtime sanity checks

The runtime SHALL regularly execute:

- document verifier;
- repository verifier;
- multicast selftest;
- ontology selftest;
- governance selftest;
- active layer selftest;
- watchdog selftest;
- bootstrapper selftest;
- TCP/IP autonomy selftest;
- damage containment selftest;
- autonomous discovery selftest.

## Final-pass rule

No final pass without autonomous discovery gates. No final pass if the claim requires impossible global discovery without seed, endpoint, registry, routable multicast, or scanning.

## Boundary

QIKVRT permits autonomous operation. QIKVRT does not permit uncontrolled self-propagation, surveillance, unauthorized probing, destructive remote mutation, or Internet-wide scanning.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
