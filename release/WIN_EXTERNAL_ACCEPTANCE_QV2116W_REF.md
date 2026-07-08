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

# QIKVRT Windows External Acceptance Evidence Reference

Version: v2.11.7 Windows final-gate aggregation repair
Source package tested externally: qv2116w
Evidence files:
- qikvrt/evidence/WIN_ACCEPTANCE_RESULT_EXTERNAL_20260707.tsv
- qikvrt/evidence/WIN_ACCEPTANCE_RESULT_EXTERNAL_20260707.json

External runner context:
- Windows PowerShell 5.1.26100.8737
- Repository root: %QIKVRT_NODE_ROOT%
- Timestamp window: 2026-07-07T15:47:17Z to 2026-07-07T15:50:35Z

Hard PASS evidence:
- Windows acceptance runner started
- Required root files present
- Max relative path length = 65
- SHA256SUMS ok=120
- JSON parse ok=33
- JSONL parse ok=18
- Live fetch MANIFEST.json: HTTP 200, bytes=15168, sha256=8d4946c2dd632a345dd4a345542d15d11802c5552cdb6a309056af35d7e103e2
- Live fetch REST/TCPIP manifest: HTTP 200, bytes=1052, sha256=154c505660431dc41fe6072809ab69702202a2f417129083deb0a35a16abe7b1
- Zig compiler bootstrap via winget succeeded after non-linkable LLVM clang fallback
- C build PASS via zigcc
- Repository verifier PASS: checks=510 failures=0 articles=44
- Root layout validation PASS
- Live GitHub seed manifest validation PASS
- Static live evidence validation PASS
- All C selftests PASS: multicast, ontology, governance, active layer, watchdog, bootstrap, TCP/IP autonomy, damage containment, autonomous discovery, GitHub seed discovery, real GitHub seed integration, ZIP layout, Windows Shell ZIP, short path, live evidence, claim matrix.

Non-final recovered audit events:
- LLVM clang was present but non-linkable because stdio.h was not found.
- Primary compiler candidate phase blocked before Zig bootstrap.
- These are preserved as audit events but superseded by later Zig build PASS.

Final-gate repair:
The Windows acceptance runner must not treat recovered intermediate compiler attempt BLOCK records as final acceptance failure when all required final gates subsequently reach PASS. v2.11.7 therefore evaluates final acceptance by required final gates, while preserving failed attempts in the ledger.

Status:
WINDOWS_EXTERNAL_ACCEPTANCE_EVIDENCE = PASS
WINDOWS_FINAL_AGGREGATION_REPAIR_REQUIRED = PASS
NO_FALSE_PASS = PRESERVED


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
