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

# Requirements

## Normative Anforderungen

REQ-001: Das Repository muss die Verfassung der Nachvollziehbarkeit vollständig mit 44 Artikeln enthalten.
REQ-002: Das Repository muss Q, I, K, V, R, T definieren.
REQ-003: Das Repository muss Ereignis, Darstellung und Deutung trennen.
REQ-004: Das Repository muss Herkunftsklärung, Spur, Prüfung und Gegenprüfung verlangen.
REQ-005: Das Repository muss Verantwortung in Netzwerken adressieren.
REQ-006: Das Repository muss Schutz vor falscher Gewissheit enthalten.
REQ-007: Das Repository muss Schutz vor Verharmlosung enthalten.
REQ-008: Das Repository muss Schutz bei Gefahr und Verhältnismäßigkeit enthalten.
REQ-009: Das Repository muss Innenraum, Selbstbestimmung und Manipulationsgrenzen enthalten.
REQ-010: Das Repository muss technische Systeme, Algorithmen, Plattformen und Institutionen erfassen.
REQ-011: Das Repository muss Korrektur und Nichtregression enthalten.
REQ-012: Das Repository muss Beweisgrade und Aussageklassen enthalten.
REQ-013: Das Repository muss Datenschutz, Privatsphäre und Missbrauchsgrenzen enthalten.
REQ-014: Das Repository muss technische Mindeststandards und algorithmische Rechenschaft enthalten.
REQ-015: Das Repository muss Machtasymmetrien und vulnerable Personen adressieren.
REQ-016: Das Repository muss Notfallprinzip, Dokumentationsstandard, Fehlerkultur und Sanktionen enthalten.
REQ-017: Das Repository muss Recht auf Vergessen und Recht auf Gedächtnis ausbalancieren.
REQ-018: Das Repository muss interdisziplinäre Prüfung, Bildung und internationale Dimension enthalten.
REQ-019: Das Repository muss Sicherheits- und Missbrauchsgrenze enthalten.
REQ-020: Das Repository muss Revision und Weiterentwicklung enthalten.

## Technische Anforderungen

REQ-T001: ANSI-C-Quelle muss mit POSIX `cc` baubar sein.
REQ-T002: Verifier muss ohne externe Bibliotheken laufen.
REQ-T003: Tests müssen mit POSIX `sh` ausführbar sein.
REQ-T004: ZIP muss keine Directory-Entries enthalten.
REQ-T005: ZIP darf keine doppelten Pfade enthalten.
REQ-T006: Root `SHA256SUMS.txt` muss alle relevanten Dateien abdecken.
REQ-T007: Interne Gates müssen maschinenlesbar sein.
REQ-T008: Manifest muss Status, Grenzen, Version und Artefakte enthalten.
REQ-T009: Keine absoluten lokalen Pfade dürfen im Repository liegen.
REQ-T010: Kein falscher FINAL-PASS ohne Traceability.


## V2.2 Multicast- und Ontologie-Anforderungen

REQ-M001: Das Repository muss Multicast als strenges Zustellmodell definieren: Sender, Payload, zuständige Empfängergruppe, Zustellung, Rückkopplung, Spur.

REQ-M002: Das Repository muss einen ANSI-C-Multicast-Selftest enthalten, der erfolgreiche Zustellung an alle zuständigen Knoten, Rückkopplung und Traceability prüft.

REQ-M003: Das Repository muss verhindern, dass Multicast nur als lose Metapher geführt wird.

REQ-O001: Das Repository muss die Ontologie des Unterschieds als unterste Schicht dokumentieren.

REQ-O002: Das Repository muss die Kette Unterschied -> Information -> Kausalität -> Verantwortung -> Verifikation -> Rückkopplung -> Traceability dokumentieren und testen.

REQ-O003: Kein Final-Pass, wenn Unterschied, Information, Zustellgruppe, Rückkopplung oder Traceability fehlen.

## V2.3 constitutional-governance requirements

- REQ-G001: Implement the constitution upward into a governance process covering intake, assertion classes, evidence, roles, multicast delivery, privacy, proportionality, emergency, correction, sanctions, revision, and misuse prevention.
- REQ-G002: Implement assertion/evidence-class requirements so claims cannot move to final status without classification and counter-check.
- REQ-G003: Implement constitutional boundaries as machine-readable gates.
- REQ-G004: Provide ANSI-C governance selftest.
- REQ-G005: Provide POSIX governance acceptance test.
- REQ-G006: Maintain V2.1 minimal regression and V2.2 multicast/ontology gates.


## V2.5 Active Layer Requirements

REQ-A001: Active discovery must be opt-in and authorized.
REQ-A002: The system must forbid unauthorized scanning and self-propagation.
REQ-A003: The active layer may operate locally and emit audit events.
REQ-A004: Self-evolution may generate proposals, not silent final mutations.
REQ-A005: Cognitive improvement must be metric-based, reversible and nonregressive.


## V2.5 Watchdog Requirements

REQ-WD-001: Repository network keepalive requires explicit opt-in peer manifests.
REQ-WD-002: Runtime selftests must validate authorized heartbeat, interval, stale/lost node detection, traceability and privacy-preserved location hints.
REQ-WD-003: Lost-node events must be persisted in an append-only ledger with last_seen_epoch, observed_epoch and lost_since_epoch when data allows.
REQ-WD-004: Unauthorized scanning, unauthorized probing, self-propagation, surveillance use, silent node-loss deletion and exact personal location collection without explicit lawful authorization are BLOCK.
REQ-WD-005: Reference test results for integration, acceptance, performance, security and watchdog selftests must be persisted in the release report.

## V2.7 Bootstrapper Requirements

- REQ-B001: Das Repository muss einen ANSI-C/POSIX-Bootstrapper enthalten.
- REQ-B002: Der Bootstrapper muss bei erster Ausführung eine GUID erzeugen.
- REQ-B003: Die GUID muss im lokalen Repository persistiert werden.
- REQ-B004: Folgeausführungen müssen dieselbe GUID wiederverwenden.
- REQ-B005: Höhere Services dürfen erst nach GUID-Persistenz starten.
- REQ-B006: Netzwerk-Login darf nur über autorisierte Manifestlogik erfolgen.
- REQ-B007: Bootstrap-Ereignisse müssen auditierbar geloggt werden.
- REQ-B008: Kein unautorisiertes Scanning, keine Selbstverbreitung, keine Überwachungsfunktion, keine stille Selbstmutation.


## V2.7 TCP/IP autonomy and containment requirements

REQ-TCP-001: Repository must provide a runtime TCP/IP loopback selftest proving authorized selftest request/response.
REQ-TCP-002: Peer-requestable selftests must require opt-in authorization, traceability and no remote mutation.
REQ-TCP-003: Runtime sanity checks must be callable from CLI for periodic use.
REQ-TCP-004: Failed or missing peer selftests must create quarantine-required status, not destructive remote repair.
REQ-TCP-005: Damage containment must emit authorized multicast notice to responsible nodes.
REQ-TCP-006: No unauthorized scanning, no self-propagation, no surveillance use, no remote side effects without authorization.

## V2.9 GitHub Seed Discovery Requirements

REQ-GSD-001: The repository must define `https://github.com/Goldkelch/qik-vrt` as the single initial seed for Internet discovery.
REQ-GSD-002: Discovery must be modelled as graph reachability from the GitHub seed.
REQ-GSD-003: Every discoverable peer must provide repository GUID and peer manifest.
REQ-GSD-004: The implementation must not perform global address scanning or unauthorized probing.
REQ-GSD-005: Peer-requestable sanity selftests and watchdog keepalive remain mandatory.
REQ-GSD-006: No final pass without GitHub seed discovery gates.


## V2.10 Real GitHub Seed Integration

V2.10 defines `https://github.com/Goldkelch/qik-vrt` as the real, tested initial seed. Acceptance requires live seed reachability evidence, raw `MANIFEST.json` validation, REST/TCPIP capability manifest validation, no global address scanning, no unauthorized probing, and persisted reference results. The runtime sanity path is implemented by `--selftest-real-github-seed-integration` and `--validate-github-seed-manifest`. V2.10 is the minimal regression point for this capability.


## V2.10.3 ZIP compatibility requirement

A release archive must be compatible with the owner Windows Shell ZIP extraction path. If `archiv_report.tsv` reports `FEHLER_ENTPACKT_ABER_LEER`, the release is blocked until corrected.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
