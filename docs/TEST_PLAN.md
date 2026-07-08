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

# Testplan V2.2

1. ZIP-Integrität und keine Duplikatpfade.
2. SHA256SUMS vollständig und passend.
3. ANSI-C/POSIX-Build mit `cc -std=c89 -pedantic -Wall -Wextra`.
4. Dokument-Verifier: 44 Artikel und Kernbegriffe.
5. Repository-Verifier: Verfassung, Multicast-Protokoll, Ontologie, Formalmodell.
6. POSIX Content Gates.
7. Boundary Gates.
8. Hash Gates.
9. Multicast-Selftest: Payload, zuständige Empfängergruppe, Zustellung, Rückkopplung, Spur.
10. Ontologie-Selftest: Unterschied, Information, Kausalität, Traceability.
11. JSON-/JSONL-Parse.
12. No false final pass / no traceability no final pass.

## V2.3 tests
- Build ANSI-C/POSIX verifier.
- Run document verifier.
- Run repository verifier with governance docs.
- Run multicast, ontology, governance selftests.
- Run POSIX governance gate test.
- Verify hashes, JSON, ZIP integrity.


## V2.5 Active Tests

- build ANSI-C/POSIX verifier.
- run `--selftest-active`.
- run `tests/test_active_layer.sh`.
- verify active-layer docs, gates and manifest.
- reject any final active status without authorization, multicast, ontology, governance, audit and nonregression gates.


## V2.7 Bootstrapper Tests
- Build ANSI-C/POSIX with bootstrap CLI.
- `--selftest-bootstrap` validates GUID, service gates and authorized network login gates.
- `--bootstrap <repo-root>` creates `qikvrt/runtime/REPOSITORY_GUID.txt`.
- Second `--bootstrap` call reuses the same GUID.
- Bootstrap ledger records `BOOTSTRAP_GUID_READY`.
- Acceptance suite includes `tests/test_bootstrapper.sh`.


## V2.8 Autonomous Discovery Tests

- Build ANSI-C/POSIX verifier.
- Run `--selftest-autonomous-discovery`.
- Verify impossibility boundary for global discovery without seed/endpoint/registry/routable multicast/scanning.
- Verify authorized seed peer or local multicast listener path.
- Verify no third-party service dependency for local operation.
- Verify no global address scanning and no unauthorized probing.
- Verify persistent operation and peer-requestable sanity selftest.


## V2.10 Real GitHub Seed Integration

V2.10 defines `https://github.com/Goldkelch/qik-vrt` as the real, tested initial seed. Acceptance requires live seed reachability evidence, raw `MANIFEST.json` validation, REST/TCPIP capability manifest validation, no global address scanning, no unauthorized probing, and persisted reference results. The runtime sanity path is implemented by `--selftest-real-github-seed-integration` and `--validate-github-seed-manifest`. V2.10 is the minimal regression point for this capability.


## V2.10.3 Windows Shell ZIP compatibility tests

- `--selftest-windows-shell-zip` validates the Windows Shell ZIP compatibility contract.
- `tests/test_windows_shell_zip.sh` verifies documentation, gates, and runtime selftest.
- Release packaging uses explicit directory entries and DOS attributes to address `FEHLER_ENTPACKT_ABER_LEER`.


---
QIKVRT License Footer — Author / Urheber: Ingolf Lohmann. Rights holder / Rechteinhaber: Ingolf Lohmann or a legal entity designated by him. License: Software: Apache-2.0; Non-software/docs: CC BY-NC-ND 4.0 unless otherwise stated. QIKVRT traceability and nonregression rules apply.

<!-- QIKVRT-DE-EN-DOC-FOOTER
Deutsch: Ende des zweisprachig anschlussfähigen QIK-VRT-Dokuments. Keine finale Behauptung ohne Traceability, Tests und Evidence.
English: End of bilingual-accessible QIK-VRT document. No final claim without traceability, tests, and evidence.
QIKVRT: NO_TRACEABILITY_NO_FINAL_PASS.
-->
